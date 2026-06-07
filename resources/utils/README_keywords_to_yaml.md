# Keywords to YAML Converter

JSONファイルから分類済みキーワードをYAML形式で出力するPythonスクリプト

## 概要

JSONファイルのキーワード分類データを YAML 形式で出力します。
- 出現回数でフィルタリング
- 出現回数またはキーワード名でソート
- 特定カテゴリのみの出力に対応

## 入力ファイル形式

JSONファイル（key:キーワード）:
```json
{
  "キーワード": {
    "category": "分類名",
    "count": 出現回数,
    "scores": { ... }
  },
  ...
}
```

## 出力ファイル形式

YAML形式（カテゴリ > キーワードリスト）:
```yaml
action:
  - sex
  - cum
  - lying
  ...
effect:
  - "!"
  - "!!"
  ...
```

## インストール

### 必要なパッケージ

```bash
pip install pyyaml
```

## 使用方法

```bash
python3 keywords_to_yaml.py --config <設定ファイルのパス>
```

例:
```bash
python3 keywords_to_yaml.py --config config/keywords_to_yaml_config.yaml
```

## 設定ファイル

YAML形式の設定ファイル `config/keywords_to_yaml_config.yaml` で動作を制御します。

### 設定パラメータ

| パラメータ | 必須 | デフォルト | 説明 |
|-----------|------|----------|------|
| `input_filepath` | ○ | - | 入力JSONファイルのパス |
| `output_filepath` | ○ | - | 出力YAMLファイルのパス |
| `minimum_count_to_output` | - | 1 | 出力対象の最小出現回数 |
| `sort_by` | - | count_desc | ソート方法: `count_desc` (出現回数降順) または `keyword_dict` (キーワード辞書順) |
| `output_categories_list` | - | (全カテゴリ) | 出力対象のカテゴリリスト（省略時は全カテゴリ出力） |

### 設定ファイルの例

#### 全カテゴリ、出現回数5以上、出現回数降順でソート
```yaml
input_filepath: ./classify/classified_keywords_example.json
output_filepath: ./output/keywords_output.yaml
minimum_count_to_output: 5
sort_by: count_desc
```

#### 特定カテゴリのみ出力（キーワード辞書順）
```yaml
input_filepath: ./classify/classified_keywords_example.json
output_filepath: ./output/keywords_output_filtered.yaml
minimum_count_to_output: 5
sort_by: keyword_dict
output_categories_list:
  - expression
  - effect
  - action
```

## 実行例

### 基本実行（全カテゴリ、出現回数降順）
```bash
python3 keywords_to_yaml.py --config config/keywords_to_yaml_config.yaml
```

出力例:
```
入力ファイルを読み込み中: ./classify/classified_keywords_Read_I_Became_a_Pornhwa_NPC_002.json
キーワードをフィルター中 (最小出現回数: 5)
キーワードをソート中 (sort_by: count_desc)
YAML形式で出力中: ./output/keywords_output.yaml
✓ YAML出力ファイルを保存しました: ./output/keywords_output.yaml
✓ 処理完了: 18 カテゴリ, 1284 キーワード
```

## エラーハンドリング

- 入力ファイルが見つからない場合: エラーメッセージを表示して終了
- JSON形式エラー: 解析失敗時はエラーメッセージを表示
- YAML形式エラー: 設定ファイルの解析失敗時はエラーメッセージを表示
- sort_by値が不正: 'count_desc' または 'keyword_dict' で指定可能

## パフォーマンス

- 1,000個以上のキーワード、複数カテゴリを含む大規模JSONファイルでも高速処理
- 出力YAMLの圧縮率が高いため、ファイルサイズは入力JSONの1/3程度

## 開発者向け情報

### 関数一覧

- `load_config()`: YAML設定ファイルの読み込み
- `load_keywords_json()`: JSON入力ファイルの読み込み
- `filter_and_group_keywords()`: キーワードのフィルタリングとカテゴリごとのグループ化
- `sort_keywords()`: キーワードのソート（2種類のソート方法に対応）
- `create_yaml_structure()`: YAML出力用の辞書構造作成
- `save_yaml()`: YAML形式でのファイル保存

### ソート方法の詳細

#### count_desc（出現回数降順）
1. 出現回数が多い順
2. 同じ出現回数の場合はキーワード名の辞書順

#### keyword_dict（キーワード辞書順）
1. キーワード名をアルファベット順でソート

## ライセンス

MIT License
