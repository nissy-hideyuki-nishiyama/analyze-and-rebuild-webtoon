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


def parse_deleted_list(items: list) -> set[str]:
    """リスト形式の削除定義をセットに変換するヘルパー関数"""
    deleted = set()
    if isinstance(items, list):
        for item in items:
            if isinstance(item, str):
                deleted.add(item)
    return deleted


def resolve_replaced_strings(config: dict) -> dict[str, str]:
    return parse_replaced_list(config.get("replaced_string", []))


def resolve_deleted_strings(config: dict) -> set[str]:
    return parse_deleted_list(config.get("deleted_string", []))


def resolve_chapters_config(config: dict) -> dict[str, dict]:
    """話数（サブディレクトリ名）ごとのオーバーライド設定を取得"""
    chapters = {}
    raw_chapters = config.get("chapters", {})
    if isinstance(raw_chapters, dict):
        for ch_name, ch_conf in raw_chapters.items():
            if isinstance(ch_conf, dict):
                chapters[ch_name] = {
                    "replaced": parse_replaced_list(ch_conf.get("replaced_string", [])),
                    "deleted": parse_deleted_list(ch_conf.get("deleted_string", []))
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
    base_replaced: dict[str, str],
    chapters_config: dict[str, dict]
) -> tuple[set[str], dict[str, str]]:
    """
    ファイルの相対パスをもとに、該当するチャプター設定があればマージして返す。
    パス上のサブディレクトリ名（例: ep01/page01.txt の ep01）に一致するか検証。
    """
    merged_deleted = set(base_deleted)
    merged_replaced = dict(base_replaced)

    # 相対パスのすべての親ディレクトリ名を判定対象にする
    path_parts = relative_path.parts[:-1]  # ファイル名を除いたパス要素

    for part in path_parts:
        if part in chapters_config:
            ch_data = chapters_config[part]
            # 削除対象の追加
            merged_deleted.update(ch_data["deleted"])
            # 置換対象の追加・上書き
            merged_replaced.update(ch_data["replaced"])

    return merged_deleted, merged_replaced


def process_file(file_path: Path, deleted: set[str], replaced: dict[str, str]) -> list[str]:
    strings = []
    with file_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            fields = line.rstrip("\n").split(",")
            for field in fields:
                text = field.strip()
                if text:
                    strings.append(text)
    # 削除
    strings = [s for s in strings if s not in deleted]
    
    # 置換および重複チェック（登録順序を保持したまま一意化）
    processed = []
    for s in strings:
        # 置換対象があれば置換後の文字列、なければ元の文字列
        target = replaced.get(s, s)
        
        # 文字列が存在し、かつまだ processed に含まれていなければ追加
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
        description="Convert prompts in text files based on YAML config with sub-directory overrides."
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
        
        base_replaced = resolve_replaced_strings(config)
        base_deleted = resolve_deleted_strings(config)
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
            
            # ファイルごとに該当サブディレクトリのルールを取得（マージ）
            file_deleted, file_replaced = get_rules_for_file(
                relative_path, base_deleted, base_replaced, chapters_config
            )

            processed = process_file(file_path, file_deleted, file_replaced)
            
            # 個別出力
            individual_output = output_dir / relative_path.parent / f"{relative_path.stem}_conv.txt"
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