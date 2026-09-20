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

画像ファイルを確認できるファイルマネージャーにて、吹き出しのみのコマ、擬音語のみのコマ、風景コマなど不要なコマの画像ファイルを確認し、それを削除する

## 4. これらをチャプターまたは話数毎にディレクトリを分けて実施する

ComfyUIで実施する
CropMultImagesFromImages_SAM2SEG ワークフローを利用する

## 5. 再分割された画像ファイルを、画像タグ抽出プログラムに読み込ませて、各画像ファイル毎にテキストプロンプト(danboo形式のテキストファイル)を出力する

```bash_old
ComfyUIで実施する -> 5.1. コンソールでタグ付けを行う を参照
i2promptonly ワークフローを利用する
```

### 5.1. コンソールでタグ付けを行う

```bash
cd $PROJECT_ROOTDIR

# Pythonの仮想環境を構築
python3 -m venv .venv
source .venv/bin/activate

# Kohya_ssの tag_images_by_wd14_tagger.py をダウンロードする
git clone https://github.com/kohya-ss/sd-scripts.git

# 環境構築
cd sd-scripts
# 必要なpythonモジュールを導入する
pip install -r requirements.txt
pip install torch torchvision pillow pandas tqdm huggingface_hub
# GPU(CUDA)を使用する場合:
pip install onnxruntime-gpu
# CPUのみの場合:
# pip install onnxruntime

# 再帰的にサブディレクトリ内の画像ファイルに対して、タグ付けを行う
python3 finetune/tag_images_by_wd14_tagger.py --onnx --repo_id SmilingWolf/wd-eva02-large-tagger-v3 --model_dir /mnt/ssd-data/common/comfy_data/models/wd14_tagger_models --general_threshold 0.25 --character_threshold 0.85 --batch_size 1 --caption_extension .txt  --frequency_tags --always_first_tags "1boy,1girl,2boys,2girls,3boys,3girls,4girls" --undesired_tags "speech_bubble,thought_bubble,english_text,korean_text,thai_text,bangs,censor,blank_censor,light_censor,bar_censor,sound_effects,invisible_penis" --recursive /mnt/comfy_data/output/webtoon/Never_Just_Friends/separated \
--output_path /mnt/comfy_data/output/webtoon/Never_Just_Friends/prompts/prompts_all.json # 1ファイルで出力される

# 各画像ディレクトリに作成されたタグファイルをプロンプトディレクトリにコピーし、元のプロンプトを削除する。入力ディレクトリに移動して、下記のコマンドを実行する
cd /mnt/comfy_data/output/webtoon/Never_Just_Friends/separated
find . -type f -name "*.txt" -exec rsync -R {} /mnt/comfy_data/output/webtoon/Never_Just_Friends/prompts/original \; -exec rm {} \;

# (オプション)生成されたJSONファイル(/mnt/comfy_data/output/webtoon/Never_Just_Friends/prompts/prompts_all.json)を所定の書式のテキストファイルに変換する
python3 convert_json_to_tags.py /mnt/comfy_data/output/webtoon/Never_Just_Friends/prompts/prompts_all.json
cat /mnt/comfy_data/output/webtoon/Never_Just_Friends/prompts/prompts_all.txt

```

## 6. テキストプロンプトをキーワードリスト生成プログラムに読み込ませて、キーワードの出現回数を計算させ、辞書順にキーワードと出現回数を出力する

```bash
cd utils
python3 make_strings_list.py ./config/make_strings_list.yaml
```

## 7. キーワードと出現回数のテキストをキーワード分類プログラムに読み込ませて、各キーワードを分類する

```bash
cd utils
python3 classify.py --config ./config/classify/classify_config.yaml
```

## 8. 分類毎にキーワードを出現回数の多い順またはキーワード名の辞書順にソートして出力する

```bash
cd utils
# カテゴリ辞書チューニング用ファイルを出力する
python3 keywords_to_yaml.py --config ./config/keywords_to_yaml_for_tunning_dict_config.yaml
# キャラクタ変換用設定プロンプトの設定ファイルを作成する際に、資材とするファイルを出力する
python3 keywords_to_yaml.py --config ./config/keywords_to_yaml_for_convert_config.yaml
```

## キャラクター変換用プロンプトの設定ファイルを作成するための事前準備

### 9.1. (オプション) キーワードに対するカテゴリー辞書のチューニング

- 設定ファイル(keywords_to_yaml_config.yaml)で指定したカテゴリーに関するキーワードが出力されている
- キーワードが分類と一致しない場合、一致しなかったキーワードをこのカテゴリー辞書の該当するカテゴリーに登録する
- 次回以降、キーワードの分類の精度が上がる

```bash
vim ./config/classify/categories.yaml
```

### 9.2. 変換および削除候補のキーワードリストを作成する

- 設定ファイル(keywords_to_yaml_config.yaml)で指定したカテゴリーに関するキーワードが出力されている: resources/utils/output/keywords_output_filtered_Never_Just_Friends_002.yaml
- このファイルの必要な部分を抽出して、11のキャラクター変換用プロンプトの設定ファイルを作成する

```bash
vim ./output/keywords_output_filtered_Never_Just_Friends_002.yaml
```

## 10. (不要になった)(オプション) 男性キャラのみのコマのプロンプトを置換して、男性キャラを固定化する

タグ付けのときに、「--always_first_tags "1boy,1girl,2boys,2girls,3boys,3girls,4girls"」の引数を追加することで、男性キャラ1名の時に「1boy, solo, 」と表示されるようになった

- WD1.4 Taggerの特性なのか、男性キャラのみのコマの場合、行頭に、「solo, 」を出力し、行中に「, 1boy, 」を出力する傾向がある
- このため、プロンプトをそのまま使うと男性キャラが安定して出力できないため、これを修正する
- 下記のコマンドを実行して、行頭の「solo, 」を「1boy, solo, 」に置換し、行中の「1boy, 」を「, 」に置換する
```bash
find /path/to/dir -type f -name "*.txt" -exec sed -i -e '1s/^solo, /1boy, solo, /' -e 's/\(.\) 1boy, /\1, /g' {} +
```

## 11. このソートファイルから必要な部分を抜き出して、キャラクター変換用プロンプトの設定ファイルを作成する

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
# 【話数別（サブディレクトリ別）オーバーライド設定】
# ディレクトリパス内のサブディレクトリ名（例: ep01, chapter_02 など）に一致する設定が上書き・追加される
chapters:
  ch004:
    replaced_string:
      - 1girl: "1girl, Tanamachi Kaoru, Amagami"
      - 2girls: "2girls, Tanamachi Kaoru, Sakurai Rihoko, Amagami"
      - 3girls: "3girls, Tanamachi Kaoru, Sakurai Rihoko, Ayatsuji Tsukasa, Amagami"
      - 4girls: "4girls, Tanamachi Kaoru, Sakurai Rihoko, Ayatsuji Tsukasa, Tanaka Keiko, Amagami"
    deleted_string:
      - censored
  ch011:
    replaced_string:
      - 1girl: "1girl, Sakurai Rihoko, Amagami"
      - 2girls: "2girls, Sakurai Rihoko, Ayatsuji Tsukasa, Amagami"
  ch012:
```

## 12. キャラクタ変換用プロンプトを生成する

下記のいずれかを実施する

### 12.1. キャラクタ変換用プロンプトを生成する

- シリーズ全体でキャラクターを変換したい場合はこちらを実施する
- 1コマ毎に出力されているテキストファイルを1つのテキストに統合するとともに、キャラクタに置換したプロンプトに変換する
- 下記のコマンドを実行する
```bash
cd utils
pytho3 convert_prompts.py config/replace/replace_targets_xxxxx.yaml
```

### 12.2. 話数毎のキャラクタ変換用プロンプトを生成する

- 話数毎に出演しているキャラクターは異なるので、話数毎にキャラクター変換を適応したい場合はこちらを実施する
- 1コマ毎に出力されているテキストファイルを1つのテキストに統合するとともに、キャラクタに置換したプロンプトに変換する
- 下記のコマンドを実行する
```bash
cd utils
pytho3 convert_chapter_prompts.py config/replace/replace_targets_xxxxx.yaml
```


## 13. (オプション)Anima向けに自然言語のプロンプトを生成する

- 画像ファイルを読み込ませて、各画像ファイル毎に自然言語によるプロンプトを生成する
- Animaでは自然言語が利用できるので、これで画像全体の雰囲気やカメラアングル、位置関係など、danbooタグでは表現しづらいものを定義する
```bash
cd utils
# 自然言語プロンプトを画像ファイルと同じディレクトリに作成する
python3 batch_caption_vl25_3b.py --image_dir /mnt/comfy_data/output/webtoon/Never_Just_Friends/separated_nsw02 --config ./config/batch_caption_natural_lang.yaml

# 各画像ディレクトリに作成されたタグファイルをプロンプトディレクトリにコピーし、元のプロンプトを削除する。入力ディレクトリに移動して、下記のコマンドを実行する
cd /mnt/comfy_data/output/webtoon/Never_Just_Friends/separated_nsw02
find . -type f -name "*.txt" -exec rsync -R {} /mnt/comfy_data/output/webtoon/Never_Just_Friends/prompts/natural_lang \; -exec rm {} \;

# (オプション)移動されたテキストファイルの不要な1－5行目を削除する
cd /mnt/comfy_data/output/webtoon/Never_Just_Friends/prompts/natural_lang
find . -type f -name "*.txt" -exec sed -i '1,5d' {} \;
```

## 13. 生成されたキャラクター変換用プロンプトファイルをComfyUIに読み込ませて、キャラクタ変換した画像ファイルを作成する

ComfyUIで実施する
bath_t2i_anima_ ワークフローを利用する
