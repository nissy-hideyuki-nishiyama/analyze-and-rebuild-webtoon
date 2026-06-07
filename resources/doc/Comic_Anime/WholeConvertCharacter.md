# 収集した Webtoon のキャラクターを他のキャラクターに一括変換する手順

## 作業概要

1. webtoonをwebページ全体を保存した後、画像ファイルのみ所定ディレクトリに移動する
2. 画像ファイルは複数あり、コマの途中で分割されているので、再結合した上で、再度、コマ毎に分割した画像ファイルを出力する
3. 前記の分割は不完全な分割(複数コマが1ファイルに保存されている)であるため、全てのコマ毎画像ファイルをSAMにかけて再分割する
4. これらをチャプターまたは話数毎にディレクトリを分けて実施する
5. 再分割された画像ファイルを、画像タグ抽出プログラムに読み込ませて、各画像ファイル毎にテキストプロンプト(danboo形式のテキストファイル)を出力する
6. テキストプロンプトをキーワードリスト生成プログラムに読み込ませて、キーワードの出現回数を計算させ、辞書順にキーワードと出現回数を出力する
7. キーワードと出現回数のテキストをキーワード分類プログラムに読み込ませて、各キーワードを分類する
8. 分類毎にキーワードをキーワード名でソートして出力する
9. このソートファイルから必要な部分を抜き出して、キャラクター変換用プロンプトの設定ファイルを作成する
10. 生成されたキャラクター変換用プロンプトファイルをComfyUIに読み込ませて、キャラクタ変換した画像ファイルを作成する

## 1. webtoonをwebページ全体を保存した後、画像ファイルのみ所定ディレクトリに移動する

(TBD)

## 2. 画像ファイルは複数あり、コマの途中で分割されているので、再結合した上で、再度、コマ毎に分割した画像ファイルを出力する

```bash
cd analyze-and-rebuild-webtoon
source .venv/bin/activate
cd resources/utils
python3 concate_images.py ./config/concate/concate_xxxx.yaml
```

## 3. 前記の分割は不完全な分割(複数コマが1ファイルに保存されている)であるため、全てのコマ毎画像ファイルをSAMにかけて再分割する
## 4. これらをチャプターまたは話数毎にディレクトリを分けて実施する

ComfyUIで実施する
CropMultImagesFromImages_SAM2SEG ワークフローを利用する

## 5. 再分割された画像ファイルを、画像タグ抽出プログラムに読み込ませて、各画像ファイル毎にテキストプロンプト(danboo形式のテキストファイル)を出力する

ComfyUIで実施する
i2promptonly ワークフローを利用する

## 6. テキストプロンプトをキーワードリスト生成プログラムに読み込ませて、キーワードの出現回数を計算させ、辞書順にキーワードと出現回数を出力する

```bash
cd utils
python3 make_strings_list.py ./config/make_strings_list.yaml
```

## 7. キーワードと出現回数のテキストをキーワード分類プログラムに読み込ませて、各キーワードを分類する

```bash
cd utils
python3 classify.py --config ./config/classify/classyfy_config.yaml
```

## 8. 分類毎にキーワードを出現回数の多い順またはキーワード名の辞書順にソートして出力する

```bash
cd utils
python3 keyword_to_yaml.py --config ./config/keyword_to_yaml_config.yaml
```

## 9. (オプション) 男性キャラのみのコマのプロンプトを置換して、男性キャラを固定化する

- WD1.4 Taggerの特性なのか、男性キャラのみのコマの場合、行頭に、「solo, 」を出力し、行中に「, 1boy, 」を出力する傾向がある
- このため、プロンプトをそのまま使うと男性キャラが安定して出力できないため、これを修正する
- 下記のコマンドを実行して、行頭の「solo, 」を「1boy, solo, 」に置換し、行中の「1boy, 」を「, 」に置換する
```bash
find /path/to/dir -type f -name "*.txt" -exec sed -i -e '1s/^solo, /1boy, solo, /' -e 's/\(.\) 1boy, /\1, /g' {} +
```

## 10. このソートファイルから必要な部分を抜き出して、キャラクター変換用プロンプトの設定ファイルを作成する

(TBD)

```yaml
input_directory: /mnt/comfy_data/output/webtoon/Teachers_Efforts/prompts
output_directory: /mnt/comfy_data/output/webtoon/Teachers_Efforts/converted_prompts_rurika
output_file: /mnt/comfy_data/output/webtoon/Teachers_Efforts/Sentimental_Graffiti/converted_prompts_rurika.txt
scan_subdir: true  # サブディレクトリも対象にする場合 true
# replace strings
replaced_string:
  - 1boy: "1boy, Aki_Tomoya, 'saenai heroine no sodatekata'"
  - 2boys: "2boy, Aki_Tomoya, faceless_male, 'saenai heroine no sodatekata'"
  # <lora:yamamoto_rurika_ilxl_v1.0>, y_ruruka, short hair, brown hair, brown eyes, <lora:T_nari_ilxl_v3:1.0>, t_n, portrait, Yamamoto_Rurika, 'Sentimental Graffiti'
  - 1girl: "1girl, <lora:yamamoto_rurika_ilxl_v1.0>, y_ruruka, short hair, brown hair, brown eyes, <lora:T_nari_ilxl_v3:1.0>, t_n, portrait, Yamamoto_Rurika, 'Sentimental Graffiti'"
  - 2girls: "2girls, <lora:yamamoto_rurika_ilxl_v1.0>, y_ruruka, short hair, brown hair, brown eyes, <lora:T_nari_ilxl_v3:1.0>, t_n, portrait, Yamamoto_Rurika, 'Sentimental Graffiti', Hyoudou_Mishiru, 'saenai heroine no sodatekata'"
  - 3girls: "3girls, <lora:yamamoto_rurika_ilxl_v1.0>, y_ruruka, short hair, brown hair, brown eyes, <lora:T_nari_ilxl_v3:1.0>, t_n, portrait, Yamamoto_Rurika, 'Sentimental Graffiti', Hyoudou_Mishiru, Sawamura_Spencer_Eriri, twintails, long_hair, 'saenai heroine no sodatekata'"
  - 4girls: "4girls, <lora:yamamoto_rurika_ilxl_v1.0>, y_ruruka, short hair, brown hair, brown eyes, <lora:T_nari_ilxl_v3:1.0>, t_n, portrait, Yamamoto_Rurika, 'Sentimental Graffiti', Hyoudou_Mishiru, Kasumigaoka_Utaha, Sawamura_Spencer_Eriri, twintails, long_hair, 'saenai heroine no sodatekata'"
  - sweat: perspiration
  # outfit
  # r_clothes, blue jacket, long_sleeves, grey mini skirt, white socks, brown footwear
  - black_hoodie: r_clothes, blue jacket, long_sleeves, grey mini skirt, white socks, brown footwear
  - black_cardigan: r_clothes, blue jacket, long_sleeves
  - black_jacket: r_clothes, blue jacket, long_sleeves
  # - black_pants: m_clothes, blazer, red neck ribbon
# deleted strings
deleted_string:
  # outfit
  - black_footwear
  - boots
  - brown_footwear
  - cuffs
  - gloves
  - grey_footwear
  - grey_pants
  - high_heels
  - necktie
```

## 11. キャラクタ変換用プロンプトを生成する

- 1コマ毎に出力されているテキストファイルを1つのテキストに統合するとともに、キャラクタに置換したプロンプトに変換する
- 下記のコマンドを実行する
```bash
pytho3 convert_prompts.py config/replace/replace_targets_xxxxx.yaml
```

## 12. 生成されたキャラクター変換用プロンプトファイルをComfyUIに読み込ませて、キャラクタ変換した画像ファイルを作成する

ComfyUIで実施する
bath_t2i ワークフローを利用する
