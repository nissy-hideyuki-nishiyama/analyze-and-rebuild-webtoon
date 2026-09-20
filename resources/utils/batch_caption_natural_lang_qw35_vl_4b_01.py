import argparse
from pathlib import Path
from PIL import Image
import torch
# from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
from transformers import AutoProcessor, Qwen3_5ForConditionalGeneration
import yaml

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def load_prompt_config(config_path: Path) -> tuple[str, str, dict]:
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

    generation_config = {
        "enable_thinking": config.get("enable_thinking", True),
        "temperature": config.get("temperature", 1.0),
        "top_p": config.get("top_p", 0.95),
        "top_k": config.get("top_k", 20),
        "repetition_penalty": config.get("repetition_penalty", 1.0),
    }

    for key, value in generation_config.items():
        if key == "enable_thinking" and not isinstance(value, bool):
            raise ValueError(f"YAML configuration key '{key}' must be a boolean.")
        if key in {"temperature", "top_p", "repetition_penalty"} and not isinstance(value, (int, float)):
            raise ValueError(f"YAML configuration key '{key}' must be numeric.")
        if key == "top_k" and not isinstance(value, int):
            raise ValueError(f"YAML configuration key '{key}' must be an integer.")

    return prompts["SYSTEM_PROMPT"], prompts["DEFAULT_PROMPT"], generation_config

class QwenVLCaptionPipeline:
    def __init__(
        self,
        system_prompt: str,
        model_dir: str = "/mnt/ssd-data/common/huggingface/huihui-ai/Huihui-Qwen3.5-4B-abliterated",
        device: str = "cuda",
        enable_thinking: bool = True,
        temperature: float = 1.0,
        top_p: float = 0.95,
        top_k: int = 20,
        repetition_penalty: float = 1.5,
    ):
        self.system_prompt = system_prompt
        self.device = device
        self.enable_thinking = enable_thinking
        self.generation_kwargs = {
            "do_sample": True,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "repetition_penalty": repetition_penalty,
        }
        print(f"Loading Qwen-VL {model_dir} on {self.device}...")

        self.processor = AutoProcessor.from_pretrained(model_dir)
        self.model = Qwen3_5ForConditionalGeneration.from_pretrained(
            model_dir,
            torch_dtype=torch.bfloat16,
            device_map="auto" if device == "cuda" else None,
        ).eval()

    @torch.no_grad()
    def generate_caption(self, image_path: Path, prompt_text: str) -> str:
        image = Image.open(image_path).convert("RGB")

        # system ロールを追加して強力に制約をかける
        messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt_text},
                ],
            },
        ]

        inputs = self.processor(
            text=self.processor.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=self.enable_thinking,
            ),
            images=[image],
            return_tensors="pt",
        )

        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # 入力トークン長を取得（入力文の出力混入を防止）
        input_len = inputs["input_ids"].shape[1]

        generated_ids = self.model.generate(
            **inputs,
            max_new_tokens=1500,
            **self.generation_kwargs,
        )

        # 生成部分のみをデコード
        caption = self.processor.decode(
            generated_ids[0][input_len:],
            skip_special_tokens=True,
        )
        return caption.strip()


def process_directory(
    root_dir: Path,
    pipeline: QwenVLCaptionPipeline,
    default_prompt: str,
    overwrite: bool = False,
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
            caption = pipeline.generate_caption(img_path, default_prompt)
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(caption)
        except Exception as e:
            print(f"Error processing {img_path}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Recursive Manga Captioning via Qwen2.5-VL")
    parser.add_argument("--image_dir", required=True, type=Path, help="Target root directory containing images")
    parser.add_argument("--config", required=True, type=Path, help="YAML file containing SYSTEM_PROMPT and DEFAULT_PROMPT")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing txt files")
    args = parser.parse_args()

    target_dir = args.image_dir.resolve()
    try:
        system_prompt, default_prompt, generation_config = load_prompt_config(args.config)
    except (FileNotFoundError, OSError, ValueError, yaml.YAMLError) as error:
        parser.error(f"Failed to load prompt configuration '{args.config}': {error}")

    pipeline = QwenVLCaptionPipeline(system_prompt=system_prompt, **generation_config)
    process_directory(target_dir, pipeline, default_prompt, overwrite=args.overwrite)
    
