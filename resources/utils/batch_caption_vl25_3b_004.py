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
# 生成時間: 1分
# DEFAULT_PROMPT = (
#     "Describe the manga panel in simple detail. "
#     "Include the composition, characters gender only, facial expression, pose, gaze, camera angle, viewer's perspective,"
#     "background, and panel atmosphere. "
#     "Answer in natural English."
# )
# 生成時間: 10秒弱
# D

# System プロンプト（最優先ルール）
SYSTEM_PROMPT = (
    "You are a strict manga captioning assistant. "
    "STRICT RULE: Never describe character physical features, hair color, hair style, eye color, breast size, or clothing, clothing color. "
    "Refer to characters ONLY as 'a man', 'a woman', 'a boy', or 'a girl'. "
    "Ignore clothes, color of clothes, hair style, hair color, eye color, and outfit completely."
)

# User プロンプト（Few-Shot 例示付き）
DEFAULT_PROMPT = """Describe this manga panel in natural English following the rules.

[BAD EXAMPLE - DO NOT DO THIS]
"A woman with short brown hair wearing a pink shirt is lying down. on a dark green surface. She appears to be in distress. A speech bubble says 'Then, check for yourself.' The camera angle is... "

[GOOD EXAMPLE - FOLLOW THIS STYLE]
"A woman is lying on her stomach on a dark green surface. She appears to be in distress. The camera angle is..."

Now describe the given manga panel. 
Include:
- Composition, camera angle, viewer's perspective, and panel atmosphere
- Character facial expressions, poses, and gaze (NO clothes, NO hair color/style, NO physical features)
- Light source position and lighting direction (e.g., light from above, backlighting, side lighting, light from the front)
- Shadows and shading on the character or environment (e.g., deep shadows on the face, harsh highlights, soft ambient shading)
- Background elements and speech text if any.

REMEMBER: NO clothing, NO hair color/style/length, NO physical body features, No any text or speech bubbles, No onomatopoeia, No sound effect string. """

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

        # system ロールを追加して強力に制約をかける
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
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
            ),
            images=[image],
            return_tensors="pt",
        )

        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # 入力トークン長を取得（入力文の出力混入を防止）
        input_len = inputs["input_ids"].shape[1]

        generated_ids = self.model.generate(
            **inputs,
            max_new_tokens=150,
            do_sample=False,
        )

        # 生成部分のみをデコード
        caption = self.processor.decode(
            generated_ids[0][input_len:],
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
    
