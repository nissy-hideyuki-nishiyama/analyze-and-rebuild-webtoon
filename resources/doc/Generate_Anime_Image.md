# アニメーションまたは漫画の画像生成を考える

## 目次

## 著者のレベル

- 画像生成を開始してから1か月
- Stabledifusion + ComfyUI から画像生成を開始したので、Automatic1111 は触ったことはない。多分、しばらくは飽きるまで ComfyUI で進める
- インフラ系エンジニアよりのシステムアーキテクト？

## 対象範囲

- StableDiffusion + ComfyUI をベースとしたローカルPCを使った画像生成システム
- 画像掲示板サイト danbooru を学習データとして採用した画像生成システム全般

## 画像生成AIの基本

- 既存画像データの学習
  - 画像データに付与されているメタデータ(キャラクタ名や装備品、ポーズ、性別、年齢、背景、アクションなど)を取得し、ベースモデルを作成する
  - **画像データの学習に用いられた画像データに、表示させたいシリーズやキャラクターがないと表示させることは基本できない**
- Loraモデルの追加とは、ベースモデルに埋もれたまたは存在しない、キャラクターや衣装、アクション、ポーズ、アクセサリを特定のキーワードで表示しやすくするための追加学習データ
- danbooru を学習データとした場合、画像の各構成要素(キャラクター、衣装)の呼び出しは、キーワード(例: pikachu)を指定することで生成する画像に追加される

## 生成AIコミュニティについて

- 画像生成AIだけでなく、他の生成AIについても、[Hugging Face](https://huggingface.co/)で各種生成AIのモデルが提供されている。生成AIモデルのgithub版サイト？
- 画像生成AIに特化した [CIVITAI](https://civitai.com/) があり、ここではAIモデルやLoraモデル、また生成した画像を投稿する掲示板機能もある
  - 生成した画像には、その画像を作成した時に **使用したパラメータがメタ情報ファイルで付与** されている。このため、ComfyUIのWEBUIにドラッグ&ドロップすると、ComfyUIのワークフローが作成され、必要なベースモデル、Loraモデル、ツールがインストールされていればその画像を手元で再現できる(Automatic1111では完全再現可能だが、ComfyUIは微妙に異なる)

## 画像生成AIの主な使用用途とニーズの拡大

1. 好きなキャラクターに好みの表情や仕草、挙動をさせた画像を作成したい
2. たくさんの画像を生成し、個人的なライブラリを作りたい、同好の士と共有したい
3. 1-2 を一つずつ手動で実行するのは面倒なので、自動生成して、好みの画像のみを抽出したい。 **Ramdom Prompt** の採用
4. 好みの画像がなかなか作成できないので、空振り率が多いので改善したい。**Lora モデル** の採用 (2025年12月時点)
5. 既存のLoraモデルには目的を達成するには足りないので、 **専用Loraモデル** を作成する
6. 気に入った画像について、さらにリファインして、より好みの画像にしたい。
7. この画像を使って、動画を作成したい。動画生成AIを導入する

## 好みの画像を生成するためには

- 利用する画像生成AIのベースモデル(checkpointsファイル)に、表示させたいキャラクターやシリーズが学習データとして登録されているか確認する。
- ベースモデルのフォーマットを調べて、それに従って、英語のキーワードを調べ、フォーマットに従って、キーワードを並べる
  - 日本語から英語に翻訳するには、Google翻訳などの翻訳サイトを利用する
  - ChatGPT や Gemini などに、下記のように質問して、キーワードをリストアップする
    - 「StableDiffusionを利用して画像生成をしています。XXXXをしているキーワードをリストアップしてください。」
  - CIVITAI の画像掲示板の検索機能を使って、目的の画像を表示させ、生成時のパラメータを確認する。もしくは、その画像をComfyUIに直接、ドラッグ&ドロップして、ワークフローを自動生成し、そこから必要なパラメータを取得する
    - Lora モデルを追加している画像の場合は、それをダウンロード&インストールする必要がある
- ここまでで、画像生成に必要なパラメータ&プロンプトおよびワークフローが準備できているはずなので、画像生成を開始する
- 100枚 画像生成したいなら、100個のジョブを登録する
- たくさんの画像が生成できるが、同じプロンプトなので似たような画像が生成されてすぐに飽きる

## プロンプトの構成要素とは

好みの画像になるようにプロンプトにキーワードを入力するが、属性について考えてみる。下記はAnimage-XLで定義されているキーワード属性である

- メインオブジェクト: 1girl, 1boy, 1other
- キャラクタ名: pikachu
  - Lora モデルを追加して、キャラクタを表示する場合は、利用する Lora モデルのサンプルに従って、髪や目の色、髪型なども追加して記述する
  - 例: <lora:Etsuko-Toyohara_lL_v01:1> etsuko-toyohara, brown hair, short hair, large breasts, brown eyes, bangs
- シリーズ名: pokemon
- レーティング: safe, senstive, nsfw, explicit
- 品質: masterpiece, best quality, low quality, worst quality
- スコア: high score, great score, good score, average score, bad score, low score
- フリーキーワード: **撮影アングルやキャラクタの所作、表情などをキーワードで記載する。下記からは主にここについて記述する**

### フリーキーワードの属性

撮影アングルや所作、表情などがあり、下記のような属性を利用している。
キーワードによっては相反するものがあり、この組み合わせが発生すると破綻した画像が生成される

- キャラクタの容姿に関わるもの
  - 表情(face): slight smile face, pensive face, radiant smile face, sweaty face
    - 目の開閉: open eyes, close eyes, wink eyes
    - 口の開閉: open month, close month, lips
  - 視線: looking at viewer, looking away
  - 服装: shirt, skirt, underwear, swimsuits, socks
    - 着衣: 上記のキーワード, underwear only, completely naked
    - 表示させたい部位: legs, arms, breast, full body
    - アクセサリー: headribon, earring, 
  - ポーズ: standing, open straight legs, crunching, spread legs, lying, bent over
- キャラクタの動作: stand with crossing legs, jumping, sleeping
- 撮影
  - アングル: font angle, front view, back angle, back view, side angle, side view, side angle
  - 視点: viewer from below, looking down, overhead shot
  - 場所: classroom, bedroom, park, garden, street, pool side, beach, forest, river side
  - 時間帯: morning, afternoon, evening, night
  - 天候: sunny, rainy, snowing, cloud sky
- 基本スタイル・画風: anime style, cel shading, retro amine style, concept art, digital painting, watercolor

## 異なる好みの画像を生成する

上記の流れで、動作や表情に変化のある画像を複数作りたいというニーズがでる。ここで、 **Random Prompts** を導入する

 





