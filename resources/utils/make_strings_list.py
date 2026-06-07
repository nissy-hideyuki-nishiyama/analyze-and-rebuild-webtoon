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
    for key in ("directory", "dir", "input_directory", "input_dir"):
        if key in config:
            return Path(config[key])
    raise KeyError(
        "YAML configuration must include one of: directory, dir, input_directory, input_dir"
    )


def resolve_output_path(config: dict, input_dir: Path) -> Path:
    if "output_file" in config:
        return Path(config["output_file"])
    if "output" in config:
        return Path(config["output"])
    return input_dir / "strings_count.txt"


def resolve_extensions(config: dict) -> list[str] | None:
    if "extensions" in config:
        exts = config["extensions"]
        if isinstance(exts, str):
            return [exts.lstrip(".")]
        if isinstance(exts, list):
            return [str(ext).lstrip(".") for ext in exts]
        raise ValueError("extensions must be a string or a list of strings")
    return None


def resolve_scan_subdir(config: dict) -> bool:
    return config.get("scan_subdir", False)


def gather_text_files(directory: Path, extensions: list[str] | None, scan_subdir: bool) -> list[Path]:
    if not directory.exists() or not directory.is_dir():
        raise FileNotFoundError(f"Directory not found: {directory}")

    files = []
    if scan_subdir:
        for entry in directory.rglob("*"):
            if entry.is_file():
                if extensions is None or entry.suffix.lstrip(".").lower() in [ext.lower() for ext in extensions]:
                    files.append(entry)
    else:
        for entry in sorted(directory.iterdir()):
            if entry.is_file():
                if extensions is None or entry.suffix.lstrip(".").lower() in [ext.lower() for ext in extensions]:
                    files.append(entry)
    # print(f"{sorted(files)}")
    return sorted(files)


def count_strings(files: list[Path]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for file_path in files:
        with file_path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                fields = line.rstrip("\n").split(",")
                for field in fields:
                    text = field.strip()
                    counts[text] = counts.get(text, 0) + 1
    return counts


def write_output(output_path: Path, counts: dict[str, int]) -> None:
    ordered = {key: counts[key] for key in sorted(counts)}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            ordered,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Count comma-separated strings in text files under a directory defined by a YAML config."
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
        output_path = resolve_output_path(config, input_dir)
        extensions = resolve_extensions(config)
        scan_subdir = resolve_scan_subdir(config)
        files = gather_text_files(input_dir, extensions, scan_subdir)
        counts = count_strings(files)
        write_output(output_path, counts)
        print(f"Processed {len(files)} file(s). Output written to: {output_path}")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
