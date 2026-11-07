#!/usr/bin/env python3

import argparse
from pathlib import Path
import sys

try:
    import yaml
except ImportError:
    print("PyYAML is required. Install it with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if not isinstance(config, dict):
        raise ValueError("YAML configuration file must contain a mapping at the top level.")
    return config


def resolve_input_directory(config: dict) -> Path:
    if "input_directory" in config:
        return Path(config["input_directory"])
    raise KeyError("YAML configuration must include 'input_directory'")


def resolve_output_directory(config: dict) -> Path:
    if "output_directory" in config:
        return Path(config["output_directory"])
    raise KeyError("YAML configuration must include 'output_directory'")


def resolve_output_file(config: dict) -> Path:
    if "output_file" in config:
        return Path(config["output_file"])
    raise KeyError("YAML configuration must include 'output_file'")


def parse_replaced_list(items: list) -> dict[str, str]:
    """リスト形式の置換定義を辞書に変換するヘルパー関数"""
    replaced = {}
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict) and len(item) == 1:
                key, value = next(iter(item.items()))
                replaced[key] = value
    return replaced


def parse_string_list(items: list) -> set[str]:
    """リスト形式の文字列定義をセットに変換するヘルパー関数"""
    result = set()
    if isinstance(items, list):
        for item in items:
            if isinstance(item, str):
                result.add(item)
    return result

def load_tag_categories(config: dict) -> dict[str, set[str]]:
    """tag_categories.yaml を読み込んで {カテゴリ名: タグのセット} を返す"""
    categories = {}
    cat_path_str = config.get("tag_categories_path")
    if cat_path_str:
        cat_path = Path(cat_path_str)
        if cat_path.exists():
            try:
                raw_data = load_config(cat_path)
                for cat_name, tags in raw_data.items():
                    if isinstance(tags, list):
                        categories[cat_name] = set(tags)
            except Exception as e:
                print(f"Warning: Failed to load tag_categories.yaml: {e}", file=sys.stderr)
        else:
            print(f"Warning: Tag categories file not found at '{cat_path_str}'", file=sys.stderr)
    return categories


def resolve_sub_category_deleted_tags(
    config_dict: dict,
    tag_categories: dict[str, set[str]]
) -> set[str]:
    """指定された deleted_sub_categories から削除対象タグの集合を生成"""
    deleted_from_cats = set()
    target_sub_cats = parse_string_list(config_dict.get("deleted_sub_categories", []))
    for sub_cat in target_sub_cats:
        if sub_cat in tag_categories:
            deleted_from_cats.update(tag_categories[sub_cat])
    return deleted_from_cats

def resolve_replaced_strings(config: dict) -> dict[str, str]:
    return parse_replaced_list(config.get("replaced_string", []))


def resolve_deleted_strings(config: dict) -> set[str]:
    return parse_string_list(config.get("deleted_string", []))


def resolve_deleted_prefixes(config: dict) -> set[str]:
    return parse_string_list(config.get("deleted_prefixes", []))


def resolve_deleted_suffixes(config: dict) -> set[str]:
    return parse_string_list(config.get("deleted_suffixes", []))


def resolve_chapters_config(config: dict) -> dict[str, dict]:
    """話数（サブディレクトリ名）ごとのオーバーライド設定を取得"""
    chapters = {}
    raw_chapters = config.get("chapters", {})
    if isinstance(raw_chapters, dict):
        for ch_name, ch_conf in raw_chapters.items():
            if isinstance(ch_conf, dict):
                chapters[ch_name] = {
                    "replaced": parse_replaced_list(ch_conf.get("replaced_string", [])),
                    "deleted": parse_string_list(ch_conf.get("deleted_string", [])),
                    "prefixes": parse_string_list(ch_conf.get("deleted_prefixes", [])),
                    "suffixes": parse_string_list(ch_conf.get("deleted_suffixes", [])),
                    "sub_categories": parse_string_list(ch_conf.get("deleted_sub_categories", [])),
                }
    return chapters


def resolve_scan_subdir(config: dict) -> bool:
    return config.get("scan_subdir", False)


def gather_text_files(directory: Path, scan_subdir: bool) -> list[Path]:
    if not directory.exists() or not directory.is_dir():
        raise FileNotFoundError(f"Directory not found: {directory}")
    files = []
    if scan_subdir:
        for entry in directory.rglob("*"):
            if entry.is_file():
                files.append(entry)
    else:
        for entry in sorted(directory.iterdir()):
            if entry.is_file():
                files.append(entry)
    return sorted(files)


def get_rules_for_file(
    relative_path: Path,
    base_deleted: set[str],
    base_prefixes: set[str],
    base_suffixes: set[str],
    base_replaced: dict[str, str],
    base_sub_cats: set[str],
    chapters_config: dict[str, dict],
    tag_categories: dict[str, set[str]]
) -> tuple[set[str], set[str], set[str], dict[str, str]]:
    """
    ファイルの相対パスをもとに、該当するチャプター設定があればマージして返す。
    """
    merged_deleted = set(base_deleted)
    merged_prefixes = set(base_prefixes)
    merged_suffixes = set(base_suffixes)
    merged_replaced = dict(base_replaced)
    
    # ベースのサブカテゴリ由来のタグを追加
    for cat_name in base_sub_cats:
        if cat_name in tag_categories:
            merged_deleted.update(tag_categories[cat_name])

    path_parts = relative_path.parts[:-1]  # ファイル名を除いたパス要素

    for part in path_parts:
        if part in chapters_config:
            ch_data = chapters_config[part]
            merged_deleted.update(ch_data["deleted"])
            merged_prefixes.update(ch_data["prefixes"])
            merged_suffixes.update(ch_data["suffixes"])
            merged_replaced.update(ch_data["replaced"])
            
            # チャプター追加分のサブカテゴリ由来のタグを反映
            for cat_name in ch_data["sub_categories"]:
                if cat_name in tag_categories:
                    merged_deleted.update(tag_categories[cat_name])

    return merged_deleted, merged_prefixes, merged_suffixes, merged_replaced


def process_file(
    file_path: Path,
    deleted: set[str],
    prefixes: set[str],
    suffixes: set[str],
    replaced: dict[str, str]
) -> list[str]:
    strings = []
    with file_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            fields = line.rstrip("\n").split(",")
            for field in fields:
                text = field.strip()
                if text:
                    strings.append(text)
    
    # 削除判定（完全一致・サブカテゴリ一致・前方一致・後方一致）
    filtered_strings = []
    for s in strings:
        # 1. 完全一致チェック（直近の deleted リストまたはサブカテゴリ由来のタグ）
        if s in deleted:
            continue
        # 2. 前方一致チェック
        if any(s.startswith(prefix) for prefix in prefixes):
            continue
        # 3. 後方一致チェック
        if any(s.endswith(suffix) for suffix in suffixes):
            continue
        
        filtered_strings.append(s)
    
    # 置換および重複チェック（登録順序を保持したまま一意化）
    processed = []
    for s in filtered_strings:
        target = replaced.get(s, s)
        if target and target not in processed:
            processed.append(target)
            
    return processed


def write_output_line(output_path: Path, file_path_str: str, strings: list[str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    line = f"/* {file_path_str} */ " + ", ".join(strings)
    with output_path.open("a", encoding="utf-8") as f:  # append
        f.write(line + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert prompts in text files based on YAML config with sub-directory overrides and tag categories."
    )
    parser.add_argument(
        "config",
        help="Path to the YAML configuration file.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config)

    try:
        config = load_config(config_path)
        input_dir = resolve_input_directory(config)
        output_dir = resolve_output_directory(config)
        output_file = resolve_output_file(config)
        
        # tag_categories.yaml のロード
        tag_categories = load_tag_categories(config)
        base_sub_cats = parse_string_list(config.get("deleted_sub_categories", []))
        
        base_replaced = resolve_replaced_strings(config)
        base_deleted = resolve_deleted_strings(config)
        base_prefixes = resolve_deleted_prefixes(config)
        base_suffixes = resolve_deleted_suffixes(config)
        
        chapters_config = resolve_chapters_config(config)
        
        scan_subdir = resolve_scan_subdir(config)
        files = gather_text_files(input_dir, scan_subdir)

        # 出力ディレクトリを作成
        output_dir.mkdir(parents=True, exist_ok=True)

        # output_file の親ディレクトリを作成
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # output_file をクリア
        with output_file.open("w", encoding="utf-8") as f:
            pass  # 空にする

        for file_path in files:
            relative_path = file_path.relative_to(input_dir)
            
            # ファイルごとに該当サブディレクトリのルール（サブカテゴリ削除含む）を取得（マージ）
            file_deleted, file_prefixes, file_suffixes, file_replaced = get_rules_for_file(
                relative_path,
                base_deleted,
                base_prefixes,
                base_suffixes,
                base_replaced,
                base_sub_cats,
                chapters_config,
                tag_categories
            )

            processed = process_file(
                file_path, file_deleted, file_prefixes, file_suffixes, file_replaced
            )
            
            # 個別出力
            individual_output = output_dir / relative_path.parent / f"{relative_path.stem}_conv.txt"
            # 親ディレクトリを作成する
            individual_output.parent.mkdir(parents=True, exist_ok=True)
            # 前回、実行時のファイルを空にする初期化を実行する
            with individual_output.open("w", encoding="utf-8") as f:
                pass  # 空にする
            write_output_line(individual_output, str(relative_path), processed)
            
            # 全体出力
            write_output_line(output_file, str(relative_path), processed)

        print(f"Processed {len(files)} file(s). Outputs written to {output_dir} and {output_file}")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())