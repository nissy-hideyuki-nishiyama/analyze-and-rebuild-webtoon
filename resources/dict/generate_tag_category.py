#!/usr/bin/env python3
import csv
import json
from pathlib import Path
import yaml

# お手元の selected_tags.csv のパスを指定してください
# (例: ~/.cache/huggingface/hub/... や stable-diffusion-webui/models/Tagger/... など)
CSV_PATH = Path("wd-eva02-large-tagger-v3.csv")  
OUTPUT_JSON_PATH = Path("tag_categories.json")

def create_tag_categories(csv_path: Path, output_yaml: Path):
    if not csv_path.exists():
        print(f"エラー: {csv_path} が見つかりません。")
        return

    categories = {
        "hair_color": [],
        "hair_style": [],
        "eye_color": [],
        "facial_features": [],
        "clothing_and_outfits": []
    }

    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # category == '0' (Generalタグのみ対象)
            if row.get("category") == "0":
                tag = row["name"].strip()

                # --- 判定ルール ---
                # 髪色
                if tag.endswith("_hair") and any(color in tag for color in [
                    "black", "blonde", "blue", "brown", "green", "grey", "orange", 
                    "pink", "purple", "red", "white", "silver", "gradient", "multicolored"
                ]):
                    categories["hair_color"].append(tag)
                
                # 髪型
                elif tag.endswith("_hair") or tag in [
                    "ponytail", "side_ponytail", "twintails", "low_twintails", "braid", 
                    "twin_braids", "bun", "hair_bun", "bob_cut", "hime_cut", "pixie_cut", 
                    "ahoge", "antenna_hair", "drill_hair", "wavy_hair", "curly_hair", 
                    "straight_hair", "messy_hair", "sidelocks", "bangs", "swept_bangs"
                ]:
                    categories["hair_style"].append(tag)

                # 目の色
                elif tag.endswith("_eyes"):
                    categories["eye_color"].append(tag)

                # 肌・身体特徴
                elif tag.endswith("_skin") or tag in [
                    "freckles", "mole", "mole_under_eye", "mole_under_mouth", "blush", "fang", "pointed_ears"
                ]:
                    categories["facial_features"].append(tag)

                # 服装・衣類関連
                elif any(cloth in tag for cloth in [
                    "uniform", "dress", "shirt", "jacket", "coat", "sweater", "hoodie", 
                    "skirt", "pants", "jeans", "shorts", "socks", "shoes", "boots", "sleeves"
                ]):
                    categories["clothing_and_outfits"].append(tag)

    # 重複排除とソート
    for key in categories:
        categories[key] = sorted(list(set(categories[key])))

    # JSONとして出力する
    # with output_json.open("w", encoding="utf-8") as f:
    #     json.dump(categories, f, indent=2, ensure_ascii=False)
    
    # YAMLとして出力
    with output_yaml.open("w", encoding="utf-8") as f:
        yaml.dump(categories, f, allow_unicode=True, sort_keys=False)

    print(f"成功: {output_yaml} を生成しました。")
    for k, v in categories.items():
        print(f" - {k}: {len(v)} 件のタグ")

if __name__ == "__main__":
    create_tag_categories(CSV_PATH, OUTPUT_JSON_PATH)
    