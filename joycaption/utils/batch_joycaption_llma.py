import argparse
from pathlib import Path
from PIL import Image
import torch
import torch.nn as nn
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    # Clipprocessor,
    SiglipImageProcessor,
    SiglipVisionModel,
)

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

# JoyCaption用デフォルトプロンプト（マンガの構図・人物・ポーズ・セリフ用）
DEFAULT_PROMPT = (
    "Write a detailed description of this manga panel in natural English. "
    "Focus on the character's facial expressions, postures, line of sight, "
    "camera angles, background elements, and any text or speech bubbles if visible."
)


# Image Adapterの定義
class ImageAdapter(nn.Module):

  def __init__(
      self,
      input_dim: int,
      output_dim: int,
      ln_eps: float = 1e-6,
  ):
    super().__init__()
    self.linear_1 = nn.Linear(input_dim, output_dim)
    self.act = nn.GELU()
    self.linear_2 = nn.Linear(output_dim, output_dim)
    self.ln1 = nn.LayerNorm(input_dim, eps=ln_eps)
    self.ln2 = nn.LayerNorm(output_dim, eps=ln_eps)

  def forward(self, x: torch.Tensor) -> torch.Tensor:
    x = self.ln1(x)
    x = self.linear_1(x)
    x = self.act(x)
    x = self.ln2(x)
    x = self.linear_2(x)
    return x


class JoyCaptionPipeline:

  def __init__(
      self,
      model_dir: str = "fancyfeast/joycaption-alpha-two",
      device: str = "cuda",
  ):
    self.device = device
    print(f"Loading JoyCaption components on {self.device}...")

    # 1. Vision Tower (SigLIP)
    self.image_processor = SiglipImageProcessor.from_pretrained(
        "google/siglip-so400m-patch14-384"
    )
    self.vision_tower = (
        SiglipVisionModel.from_pretrained("google/siglip-so400m-patch14-384")
        .to(self.device, dtype=torch.bfloat16)
        .eval()
    )

    # 2. Tokenizer & LLM (Llama 3.1 8B Instruct)
    self.tokenizer = AutoTokenizer.from_pretrained(
        "meta-llama/Meta-Llama-3.1-8B-Instruct"
    )
    self.text_model = (
        AutoModelForCausalLM.from_pretrained(
            "meta-llama/Meta-Llama-3.1-8B-Instruct",
            torch_dtype=torch.bfloat16,
            device_map=self.device,
        )
        .eval()
    )

    # 3. Image Adapter
    adapter_path = (
        Path(
            AutoModelForCausalLM.from_pretrained(
                model_dir, subfolder="image_adapter"
            ).config._name_or_path
        )
        if False
        else None
    )

    # Adapter重みの直接ロード
    from huggingface_hub import hf_hub_download

    adapter_file = hf_hub_download(
        repo_id=model_dir, filename="image_adapter.pt"
    )
    self.image_adapter = ImageAdapter(1152, 4096).to(
        self.device, dtype=torch.bfloat16
    )
    self.image_adapter.load_state_dict(
        torch.load(adapter_file, map_location=self.device)
    )
    self.image_adapter.eval()

  @torch.no_grad()
  def generate_caption(self, image_path: Path, prompt_text: str) -> str:
    # 画像前処理
    image = Image.open(image_path).convert("RGB")
    pixel_values = (
        self.image_processor(images=image, return_tensors="pt")
        .pixel_values.to(self.device, dtype=torch.bfloat16)
    )

    # 視覚特徴量の抽出とAdapter変換
    image_forward_out = self.vision_tower(
        pixel_values, output_hidden_states=True
    )
    image_features = image_forward_out.hidden_states[-2]
    embedded_images = self.image_adapter(image_features)

    # プロンプトの構築 (Llama-3 Chat Template)
    messages = [{"role": "user", "content": prompt_text}]
    prompt_formatted = self.tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )

    # トークン化とEmbeddingの合成
    prompt_tokens = self.tokenizer(
        prompt_formatted, return_tensors="pt"
    ).input_ids.to(self.device)
    prompt_embeds = self.text_model.get_input_embeddings()(prompt_tokens)

    # 画像EmbeddingとテキストEmbeddingを結合
    input_embeds = torch.cat([embedded_images, prompt_embeds], dim=1)

    # テキスト生成
    outputs = self.text_model.generate(
        inputs_embeds=input_embeds,
        max_new_tokens=512,
        do_sample=True,
        temperature=0.6,
        top_p=0.9,
    )

    # 応答部分のみ取得
    caption = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
    return caption.strip()


def process_directory(
    root_dir: Path, pipeline: JoyCaptionPipeline, overwrite: bool = False
):
  image_paths = [
      p
      for p in root_dir.rglob("*")
      if p.is_file() and p.suffix.lower() in IMAGE_EXTS
  ]
  print(f"Found {len(image_paths)} images in '{root_dir}'.")

  for idx, img_path in enumerate(image_paths, 1):
    txt_path = img_path.with_suffix(".txt")

    if txt_path.exists() and not overwrite:
      print(f"[{idx}/{len(image_paths)}] Skipping (already exists): {img_path}")
      continue

    print(f"[{idx}/{len(image_paths)}] Processing: {img_path}")
    try:
      caption = pipeline.generate_caption(img_path, DEFAULT_PROMPT)

      with open(txt_path, "w", encoding="utf-8") as f:
        f.write(caption)

    except Exception as e:
      print(f"Error processing {img_path}: {e}")


if __name__ == "__main__":
  print(f"starting")
  parser = argparse.ArgumentParser(
      description="Recursive Manga Captioning via JoyCaption"
  )
  parser.add_argument(
      "dir", type=str, help="Target root directory containing images"
  )
  parser.add_argument(
      "--overwrite", action="store_true", help="Overwrite existing txt files"
  )

  args = parser.parse_args()

  target_dir = Path(args.dir).resolve()
  pipeline = JoyCaptionPipeline()
  process_directory(target_dir, pipeline, overwrite=args.overwrite)