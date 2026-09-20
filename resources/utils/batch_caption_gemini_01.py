import argparse
from pathlib import Path
from PIL import Image
import torch
from transformers import AutoProcessor, Qwen3_5ForConditionalGeneration
import yaml

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def load_prompt_config(config_path: Path) -> tuple[str, str]:
    with config_path.open("r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)

    if not isinstance(config, dict):
        raise ValueError("YAML configuration file must contain a mapping at the top level.")

    prompts = {}
    for key in ("SYSTEM_PROMPT", "DEFAULT_PROMPT"):
        value = config.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"YAML configuration must include non-empty string '{key}'.")
        prompts[key] = value

    return prompts["SYSTEM_PROMPT"], prompts["DEFAULT_PROMPT"]


class QwenVLCaptionPipeline:
    def __init__(
        self,
        system_prompt: str,
        model_dir: str = "/mnt/ssd-data/common/huggingface/huihui-ai/Huihui-Qwen3.5-4B-abliterated",
        device: str = "cuda",
    ):
        self.system_prompt = system_prompt
        self.device = device
        print(f"Loading Qwen-VL {model_dir} on {self.device}...")

        self.processor = AutoProcessor.from_pretrained(model_dir)
        self.model = Qwen3_5ForConditionalGeneration.from_pretrained(
            model_dir,
            torch_dtype=torch.bfloat16,
            device_map="auto" if device == "cuda" else None,
        ).eval()

    @torch.no_grad()
    def generate_caption(self, image_path: Path, wd_tags: str, default_prompt: str) -> str: 
        image = Image.open(image_path).convert("RGB")

        # デフォルトプロンプトにWDタガーの情報を埋め込む
        user_content_text = f"{default_prompt}\n\n[Reference Danbooru Tags from WD-Tagger]:\n{wd_tags}"

        # システムロールとユーザーロールの構築
        messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": user_content_text},
                ],
            },
        ]

        inputs = self.processor(
            text=self.processor.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False, # 安定出力を優先
            ),
            images=[image],
            return_tensors="pt",
        )

        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        input_len = inputs["input_ids"].shape[1]

        # サンプラーパラメータの適用
        generated_ids = self.model.generate(
            **inputs,
            max_new_tokens=512,        # 複数キャラの長文対応
            do_sample=True,
            temperature=0.7,
            top_p=0.80,
            top_k=20,
            repetition_penalty=1.1,    # 言葉のループ・連充を防止
            # presence_penalty=1.5,      # 豊かな表現力を担保
        )

        caption = self.processor.decode(
            generated_ids[0][input_len:],
            skip_special_tokens=True,
        )
        return caption.strip()


def process_directory(
    image_dir: Path,
    tag_dir: Path,
    pipeline: QwenVLCaptionPipeline,
    default_prompt: str,
    overwrite: bool = False,
):
    # 画像ディレクトリから再帰的に画像を取得
    image_paths = [
        p
        for p in image_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    ]
    print(f"Found {len(image_paths)} images in '{image_dir}'.")
    print(f"Reference tags will be read from '{tag_dir}'.")

    for idx, img_path in enumerate(image_paths, 1):
        # 画像ファイルから相対パスを取得し、タグディレクトリ内での対応パスを決定
        relative_path = img_path.relative_to(image_dir)
        wd_txt_path = tag_dir / relative_path.with_suffix(".txt")
        
        # 最終的な出力先（画像と同じディレクトリに .txt を生成）
        output_txt_path = img_path.with_suffix(".txt")

        if output_txt_path.exists() and not overwrite:
            print(f"[{idx}/{len(image_paths)}] Skipping (already exists): {img_path}")
            continue

        # 対応するWDタガーのテキストファイルが存在するかチェック
        if not wd_txt_path.exists():
            print(f"[{idx}/{len(image_paths)}] Warning: Tag file not found at '{wd_txt_path}'. Skipping.")
            continue

        print(f"[{idx}/{len(image_paths)}] Processing: {img_path}")
        try:
            # WDタガーのタグを読み込む
            with open(wd_txt_path, "r", encoding="utf-8") as f:
                wd_tags = f.read().strip()

            # Qwenに画像とWDタグを渡してAnima用プロンプトを生成
            caption = pipeline.generate_caption(img_path, wd_tags, default_prompt)
            
            # 画像の隣に保存
            with open(output_txt_path, "w", encoding="utf-8") as f:
                f.write(caption)
        except Exception as e:
            print(f"Error processing {img_path}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dynamic Multi-Character Captioning via Qwen3.5-VL with WD-Tagger Integration")
    parser.add_argument("--image_dir", required=True, type=Path, help="Target root directory containing images")
    parser.add_argument("--tag_dir", required=True, type=Path, help="Directory containing pre-processed WD-Tagger .txt files")
    parser.add_argument("--config", required=True, type=Path, help="YAML file containing SYSTEM_PROMPT and DEFAULT_PROMPT")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing txt files next to images")
    args = parser.parse_args()

    target_img_dir = args.image_dir.resolve()
    target_tag_dir = args.tag_dir.resolve()
    
    try:
        system_prompt, default_prompt = load_prompt_config(args.config)
    except (FileNotFoundError, OSError, ValueError, yaml.YAMLError) as error:
        parser.error(f"Failed to load prompt configuration '{args.config}': {error}")

    pipeline = QwenVLCaptionPipeline(system_prompt=system_prompt)
    process_directory(target_img_dir, target_tag_dir, pipeline, default_prompt, overwrite=args.overwrite)
