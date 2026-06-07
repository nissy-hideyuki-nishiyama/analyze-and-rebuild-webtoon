#!/usr/bin/env python3
import argparse
import yaml
import json
from sentence_transformers import SentenceTransformer, util
import torch


def load_config(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_categories(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_keywords(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)  # dict: {keyword: count}
    

def build_category_vectors(model, categories: dict):
    """
    categories:
      expression:
        - smile
        - angry
      action:
        - run
        - jump
    """
    category_vectors = {}
    for cat, words in categories.items():
        vec = model.encode(words, convert_to_tensor=True)
        category_vectors[cat] = vec.mean(dim=0)
    return category_vectors


def classify_keyword(model, category_vectors, keyword: str):
    kw_vec = model.encode(keyword, convert_to_tensor=True)
    scores = {
        cat: util.cos_sim(kw_vec, vec).item()
        for cat, vec in category_vectors.items()
    }
    best_cat = max(scores, key=scores.get)
    return best_cat, scores


def main():
    parser = argparse.ArgumentParser(description="Keyword classifier")
    parser.add_argument("--config", required=True, help="Path to config YAML")
    args = parser.parse_args()

    # Load config
    config = load_config(args.config)
    mode_name = config.get("mode_name", "default")
    categories_dict_path = config["categories_dict_path"]
    input_keyword_path = config["input_keyword_path"]
    output_path = config["output_path"]

    print(f"[INFO] Mode: {mode_name}")
    print(f"[INFO] Loading categories from: {categories_dict_path}")
    print(f"[INFO] Loading keywords from: {input_keyword_path}")

    # Load data
    categories = load_categories(categories_dict_path)
    keywords_dict = load_keywords(input_keyword_path)

    # Load model
    print("[INFO] Loading embedding model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    # Build category vectors
    category_vectors = build_category_vectors(model, categories)

    # Classify
    results = {}
    for kw, count in keywords_dict.items():
        label, score = classify_keyword(model, category_vectors, kw)
        results[kw] = {
            "category": label,
            "count": count,
            "scores": score
        }

    # Output JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"[INFO] Classification complete. Output saved to: {output_path}")


if __name__ == "__main__":
    main()
