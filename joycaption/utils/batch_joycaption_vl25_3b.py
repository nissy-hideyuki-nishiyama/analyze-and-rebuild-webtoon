import argparse
from pathlib import Path
from PIL import Image
import torch
from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

# DEFAULT_PROMPT = (
#     "Write a detailed description of this manga panel in natural English. "
#     "Focus on the character's facial expressions, postures, line of sight, "
#     "camera angles, background elements, and any text or speech bubbles if visible."
# )
# 生成時間: 2-3分
DEFAULT_PROMPT = (
    "Describe the manga panel in simple detail. "
    "Include the composition, characters, facial expression, pose, gaze, "
    "background, and panel atmosphere. "
    "Answer in natural English."
)

class QwenVLCaptionPipeline:
    def __init__(
        self,
        # model_dir: str = "Qwen/Qwen2.5-VL-3B-Instruct",
        model_dir: str = "/mnt/ssd-data/common/huggingface/Qwen/Qwen2.5-VL-3B-Instruct",
        device: str = "cuda",
    ):
        self.device = device
        print(f"Loading Qwen2.5-VL on {self.device}...")

        self.processor = AutoProcessor.from_pretrained(model_dir)
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_dir,
            torch_dtype=torch.bfloat16,
            device_map="auto" if device == "cuda" else None,
        ).eval()

        # if device == "cuda":
        #     self.model.to(self.device)

    @torch.no_grad()
    def generate_caption(self, image_path: Path, prompt_text: str) -> str:
        image = Image.open(image_path).convert("RGB")

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt_text},
                ],
            }
        ]

        # Qwen2.5-VLの推奨入力形式
        inputs = self.processor(
            text=self.processor.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            ),
            images=[image],
            return_tensors="pt",
        )

        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # 1枚当たり2－3分かかった
        # generated_ids = self.model.generate(
        #     **inputs,
        #     max_new_tokens=512,
        #     do_sample=True,
        #     temperature=0.6,
        #     top_p=0.9,
        # )
        # 1枚当たり10秒未満であったが、nsfwキーワードが表現できていない
        generated_ids = self.model.generate(
            **inputs,
            max_new_tokens=120,
            do_sample=False,
            # temperature=0.2,
            # top_p=0.8,
        )

        caption = self.processor.decode(
            generated_ids[0],
            skip_special_tokens=True,
        )
        return caption.strip()


def process_directory(root_dir: Path, pipeline: QwenVLCaptionPipeline, overwrite: bool = False):
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
    parser = argparse.ArgumentParser(description="Recursive Manga Captioning via Qwen2.5-VL")
    parser.add_argument("dir", type=str, help="Target root directory containing images")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing txt files")
    args = parser.parse_args()

    target_dir = Path(args.dir).resolve()
    pipeline = QwenVLCaptionPipeline()
    process_directory(target_dir, pipeline, overwrite=args.overwrite)