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


def resolve_replaced_strings(config: dict) -> dict[str, str]:
    replaced = {}
    if "replaced_string" in config:
        for item in config["replaced_string"]:
            if isinstance(item, dict) and len(item) == 1:
                key, value = next(iter(item.items()))
                replaced[key] = value
    return replaced


def resolve_deleted_strings(config: dict) -> set[str]:
    deleted = set()
    if "deleted_string" in config:
        for item in config["deleted_string"]:
            if isinstance(item, str):
                deleted.add(item)
    return deleted


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


def process_file(file_path: Path, deleted: set[str], replaced: dict[str, str]) -> list[str]:
    strings = []
    with file_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            fields = line.rstrip("\n").split(",")
            for field in fields:
                text = field.strip()
                if text:  # 空文字列は無視？
                    strings.append(text)
    # 削除
    strings = [s for s in strings if s not in deleted]
    # 置換
    processed = []
    for s in strings:
        if s in replaced:
            replacement = replaced[s]
            if replacement:  # 空でない場合
                processed.append(replacement)
            # 空の場合は追加しない
        else:
            processed.append(s)
    return processed


def write_output_line(output_path: Path, file_path_str: str, strings: list[str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    line = f"/* {file_path_str} */ " + ", ".join(strings)
    with output_path.open("a", encoding="utf-8") as f:  # append
        f.write(line + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert prompts in text files based on YAML config."
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
        replaced = resolve_replaced_strings(config)
        deleted = resolve_deleted_strings(config)
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
            processed = process_file(file_path, deleted, replaced)
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