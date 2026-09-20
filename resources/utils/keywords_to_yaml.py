#!/usr/bin/env python3
"""
JSONファイルから分類済みキーワードをYAML形式で出力するスクリプト

JSONファイルのデータ構造：
{
  "キーワード": {
    "category": "分類名",
    "count": 出現回数,
    "scores": { ... }
  },
  ...
}

出力YAML形式：
categories01:
  - keyword01
  - keyword02
"""

import json
import yaml
import argparse
import sys
from pathlib import Path


def load_config(config_file):
    """YAML設定ファイルを読み込む"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        print(f"エラー: 設定ファイル '{config_file}' が見つかりません。", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"エラー: YAML設定ファイルの解析に失敗しました: {e}", file=sys.stderr)
        sys.exit(1)


def load_keywords_json(input_filepath):
    """JSONファイルからキーワードデータを読み込む"""
    try:
        with open(input_filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"エラー: 入力ファイル '{input_filepath}' が見つかりません。", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"エラー: JSON形式の解析に失敗しました: {e}", file=sys.stderr)
        sys.exit(1)


def filter_and_group_keywords(keywords_data, minimum_count, output_categories=None):
    """
    キーワードをフィルターして分類別にグループ化

    Args:
        keywords_data: JSONから読み込んだキーワードデータ
        minimum_count: 出現回数の最小値
        output_categories: 出力対象分類のリスト（Noneなら全分類）

    Returns:
        {
            'category_name': [
                {'keyword': 'kw', 'count': 123},
                ...
            ],
            ...
        }
    """
    grouped = {}

    for keyword, info in keywords_data.items():
        count = info.get('count', 0)
        category = info.get('category')

        # minimum_count条件をチェック
        if count < minimum_count:
            continue

        # output_categories条件をチェック
        if output_categories is not None and category not in output_categories:
            continue

        # カテゴリがなければスキップ
        if not category:
            continue

        # グループに追加
        if category not in grouped:
            grouped[category] = []
        grouped[category].append({'keyword': keyword, 'count': count})

    return grouped


def sort_keywords(grouped_data, sort_by):
    """
    キーワードをソート

    Args:
        grouped_data: カテゴリごとにグループ化されたキーワード
        sort_by: 'count_desc' または 'keyword_dict'
    """
    for category in grouped_data:
        if sort_by == 'count_desc':
            grouped_data[category].sort(
                key=lambda x: (-x['count'], x['keyword'])
            )
        elif sort_by == 'keyword_dict':
            grouped_data[category].sort(
                key=lambda x: x['keyword']
            )


def create_yaml_structure(grouped_data):
    """
    YAML出力用の辞書構造を作成

    カテゴリ > キーワードのリストの形式に変換
    """
    yaml_data = {}
    for category in sorted(grouped_data.keys()):
        yaml_data[category] = [item['keyword'] for item in grouped_data[category]]
    return yaml_data


def save_yaml(yaml_data, output_filepath):
    """YAMLファイルに保存"""
    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            yaml.dump(
                yaml_data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False
            )
        print(f"✓ YAML出力ファイルを保存しました: {output_filepath}")
    except IOError as e:
        print(f"エラー: YAML出力ファイルの保存に失敗しました: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='JSONから分類済みキーワードをYAML形式で出力するスクリプト'
    )
    parser.add_argument(
        '--config',
        required=True,
        help='設定ファイルのパス (YAML形式)'
    )
    args = parser.parse_args()

    # 設定ファイルを読み込む
    config = load_config(args.config)

    # 設定値を取得
    input_filepath = config.get('input_filepath')
    output_filepath = config.get('output_filepath')
    minimum_count = config.get('minimum_count_to_output', 1)
    sort_by = config.get('sort_by', 'count_desc')
    output_categories = config.get('output_categories_list')

    # 設定値のチェック
    if not input_filepath:
        print("エラー: 設定ファイルに 'input_filepath' が指定されていません。", file=sys.stderr)
        sys.exit(1)
    if not output_filepath:
        print("エラー: 設定ファイルに 'output_filepath' が指定されていません。", file=sys.stderr)
        sys.exit(1)
    if sort_by not in ('count_desc', 'keyword_dict'):
        print(f"エラー: sort_by は 'count_desc' または 'keyword_dict' である必要があります。指定値: {sort_by}", file=sys.stderr)
        sys.exit(1)

    # JSONデータを読み込む
    print(f"入力ファイルを読み込み中: {input_filepath}")
    keywords_data = load_keywords_json(input_filepath)

    # キーワードをフィルターしてグループ化
    print(f"キーワードをフィルター中 (最小出現回数: {minimum_count})")
    grouped_data = filter_and_group_keywords(keywords_data, minimum_count, output_categories)

    # ソート
    print(f"キーワードをソート中 (sort_by: {sort_by})")
    sort_keywords(grouped_data, sort_by)

    # YAML構造を作成
    yaml_data = create_yaml_structure(grouped_data)

    # YAML出力ファイルを作成
    print(f"YAML形式で出力中: {output_filepath}")
    save_yaml(yaml_data, output_filepath)

    # 統計情報を表示
    total_keywords = sum(len(keywords) for keywords in yaml_data.values())
    print(f"✓ 処理完了: {len(yaml_data)} カテゴリ, {total_keywords} キーワード")


if __name__ == '__main__':
    main()
