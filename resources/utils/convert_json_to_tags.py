#!/usr/bin/env python3
"""
Convert JSON format image tagging file to text format.

Input: JSON file with image paths as keys and objects containing "tags" and "image_size"
Output: Text file with format: /* path/filename.txt */ tags
"""

import json
import sys
from pathlib import Path


def convert_json_to_tags(input_file):
    """
    Convert JSON file to tags text format.
    
    Args:
        input_file: Path to input JSON file
    """
    input_path = Path(input_file)
    
    if not input_path.exists():
        print(f"Error: Input file '{input_file}' not found.", file=sys.stderr)
        sys.exit(1)
    
    if not input_path.suffix.lower() == '.json':
        print(f"Error: Input file must be JSON format.", file=sys.stderr)
        sys.exit(1)
    
    # Read JSON file
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON file: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Generate output file path
    output_path = input_path.with_suffix('.txt')
    
    # Process and write output
    with open(output_path, 'w', encoding='utf-8') as f:
        for image_path, metadata in data.items():
            # Extract tags
            tags = metadata.get('tags', '')
            
            # Get last two path components and change extension to .txt
            path_obj = Path(image_path)
            
            # Get the last two parts of the path (e.g., "ch004/0001_0001.txt")
            parts = path_obj.parts
            if len(parts) >= 2:
                # Take last two parts
                relative_path = '/'.join(parts[-2:])
            else:
                # If less than 2 parts, just use the last part
                relative_path = path_obj.name
            
            # Change extension to .txt
            relative_path = Path(relative_path).with_suffix('.txt').as_posix()
            
            # Write in the specified format
            f.write(f"/* {relative_path} */ {tags}\n")
    
    print(f"✓ Successfully converted: {output_path}")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 convert_json_to_tags.py <input_json_file>")
        print("\nExample:")
        print("  python3 convert_json_to_tags.py prompts_all_separated.json")
        sys.exit(1)
    
    convert_json_to_tags(sys.argv[1])
