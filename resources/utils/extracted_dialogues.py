import os
from PIL import Image
# from manga_ocr import MangaOcr
import pytesseract

# 1. Manga-OCRの初期化（初回実行時に自動でAIモデルがダウンロードされます）
# print("Manga-OCRを起動中...（初回は数分かかります）")
# mocr = MangaOcr()

print("Tesseract OCR (英語モード) で処理を開始します...")

# 2. 画像が保存されているフォルダを指定
# image_folder = "webtoon_images"
image_folder = "/mnt/comfy_data/output/webtoon/switchon2/ch003/separated"
output_file = "extracted_dialogues.txt"

# 3. フォルダ内の画像をループ処理してテキストを抽出
with open(output_file, "w", encoding="utf-8") as f:
    for filename in sorted(os.listdir(image_folder)):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            img_path = os.path.join(image_folder, filename)
            print(f"処理中: {filename}")
            
            try:
                # 画像を読み込んでOCR実行
                img = Image.open(img_path)
                
                #text = mocr(img)
                # lang='eng' を指定して英語として認識させる
                text = pytesseract.image_to_string(img, lang='eng')
                
                # 前後の余計な空白を削除
                text = text.strip()
                
                # 結果をファイルに書き出し
                f.write(f"--- 【ファイル名: {filename}】 ---\n")
                f.write(f"{text}\n\n")
            except Exception as e:
                print(f"エラー（{filename}）: {e}")

print(f"完了しました！結果は {output_file} に保存されました。")