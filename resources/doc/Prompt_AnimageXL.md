# Animagine-xl-4.0 のプロンプトについて考察する
StabledifussionのAnimagine-xl-4.0を1週間程、試して分かったことをメモ書きする

## 目的
- Animagine-xl-4.0 で目的のキャラクターが好みのポーズの画像を作成する
- これを実現するための個人的な考察
- [cagliostrolab/animagine-xl-4.0](https://huggingface.co/cagliostrolab/animagine-xl-4.0https://huggingface.co/cagliostrolab/animagine-xl-4.0)

## 概要
1. Stablediffusion の仕組み
2. Animagine-xl-4.0のプロンプト構造とモデル
3. Empty Latent Imageと画面サイズ、ポーズへの影響
4. TBD

## 1. Stablediffusionの仕組み
- インターネット上の画像ファイルを収集して、各画像ファイルにメタ情報タグを埋め込む
  - このメタ情報タグには、下記の要素が含まれている(推察)
    - キャラクタの性別と人数(1girl|1boy|1other)
    - 対象年齢(rating: safe, sensitive, nsfw, explicit)
    - 品質(masterpiece, best quality, low quality, worst quality)
    - スコア(high score, great score, good score, average score, bad score, low score)
    - etc
- これを収集した画像ファイルはもちろん、モデルで生成した画像ファイルにも繰り返し行い、学習モデルの強化を実施する
- 画像生成する入力ファイルとして、JSON形式ファイルが使われる
  ‐ JSONファイルはKEY&VALUEの情報を格納しているので、出力したい画像ファイルの仕様がある(推測)
    - 例: 
    ```bash
    object: 1girl
    rating: safe
    backgroud: arena in school
    quality: masterpiece
    score level: high score
    ```
- 画像を生成する場合はモデルがもっている画像コレクションから入力情報に適合した画像を選択し、それらを分解して、融合して、新しい画像を生成する
- 2000年代初頭にPhotoshopではやったアイコラ画像の高機能版が現在の生成AIと考えらえる。

## 2. Animagine-xl-4.0のプロンプト構造とモデル
- Animagine-xl-4.0 の学習データでは、各画像ファイルに下記のメタ情報タグが含まれている(推測)
  - キャラクタの性別と人数(1girl|1boy|1other)
  - キャラクター名(charactor_name: pikachu)
  - 作品名(from_whitch_series: pokemon)
  - 対象年齢(ratng: safe, sensitive, nsfw, explicit)
  - 品質(masterpiece, best quality, low quality, worst quality)
  - スコア(high score, great score, good score, average score, bad score, low score)
  - 年代(year 2025, year {n})
  - etc
    - full body
    - smile face
- Animagine-xl-4.0 のプロンプト構造は下記と定義されており、より意図した画像を生成したい場合は従う必要がある
```bash
1girl/1boy/1other, character name, from which series, rating, everything else in any order and end with quality enhancement
```
  - 最低限、「1girl/1boy/1other, character name, from which series, rating, 」は必須要素なので必ず記載する必要がある

## 3. Empty Latent Imageの画面サイズ、ポーズ・構図への影響
- 画面サイズによって、キャラクターのポーズは制限を受ける
  ‐ 例: 
    - 画面サイズ: 640 X 1536, プロンプト: full body の場合、垂直に立つポーズの構図
    - 画面サイズ: 832 X 1216, プロンプト: full body の場合、屈んで膝を抱えるようなポーズの構図
  - 「full body」というキーワードが、上半身および下半身がすべて構図に収まっているポーズとモデルが判断するため、おのずと画面サイズによって、ポーズが固定化してしまう(推測)

## 4. TBD
