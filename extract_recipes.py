#!/usr/bin/env python3
"""Extract structured recipe data from HowToCook markdown files."""
import json, re, os, sys
from pathlib import Path

REPO_DIR = Path("D:/Softwares/每次菜谱/HowToCook_repo")
DISHES_DIR = REPO_DIR / "dishes"
OUTPUT = Path("D:/Softwares/每次菜谱/recipes.json")

CATEGORY_CN = {
    "vegetable_dish": "素菜",
    "meat_dish": "荤菜",
    "aquatic": "水产",
    "staple": "主食",
    "soup": "汤羹",
    "dessert": "甜品",
    "drink": "饮品",
    "breakfast": "早餐",
    "condiment": "调料",
    "semi-finished": "半成品",
}


def parse_recipe(filepath, category):
    text = filepath.read_text(encoding="utf-8")
    lines = text.split("\n")

    # Skip reference-only files (just link to another recipe)
    content_preview = text[:200].strip()
    if text.strip().startswith("[") and len(lines) < 5:
        return None

    title = None
    difficulty = 0
    calories = None

    for line in lines[:10]:
        if line.startswith("# "):
            title = line[2:].replace("的做法", "").strip()
        if "难度" in line or "★★" in line:
            difficulty = line.count("★")
        if "卡路里" in line and "大卡" in line:
            m = re.search(r"(\d+)", line)
            if m:
                calories = int(m.group(1))

    if not title:
        title = filepath.stem

    # Find sections
    ingredients = []
    steps = []
    current_section = None
    step_idx = 0

    for line in lines:
        if line.startswith("## "):
            section = line[3:].strip()
            if "原料" in section or "工具" in section:
                current_section = "ingredients"
            elif "操作" in section or "步骤" in section:
                current_section = "steps"
            elif "附加" in section or "参考" in section:
                current_section = None
            else:
                current_section = None
        elif current_section == "ingredients":
            item = line.strip().lstrip("- *").strip()
            if item and not item.startswith("#") and not item.startswith("!"):
                ingredients.append(item)
        elif current_section == "steps":
            m = re.match(r"^\d+\.\s+(.+)", line.strip())
            if m:
                step_idx += 1
                steps.append(m.group(1))
            else:
                stripped = line.strip().lstrip("- *").strip()
                if stripped and step_idx > 0 and not stripped.startswith("#") and not stripped.startswith("!"):
                    steps[-1] += " " + stripped

    # Clean ingredients: remove quantity numbers, keep the ingredient name
    cleaned_ingredients = []
    for ing in ingredients:
        if len(ing) > 2 and len(ing) < 30 and not ing.startswith("http"):
            cleaned_ingredients.append(ing)

    return {
        "name": title,
        "category": CATEGORY_CN.get(category, category),
        "category_key": category,
        "difficulty": difficulty,
        "calories": calories,
        "ingredients": cleaned_ingredients[:15],
        "steps": steps[:20],
    }


def main():
    recipes = []
    failed = 0

    for cat_dir in DISHES_DIR.iterdir():
        if not cat_dir.is_dir() or cat_dir.name == "template":
            continue
        category = cat_dir.name

        for item in cat_dir.iterdir():
            if item.is_file() and item.suffix == ".md":
                r = parse_recipe(item, category)
                if r:
                    recipes.append(r)
                else:
                    failed += 1
            elif item.is_dir():
                md_file = item / f"{item.name}.md"
                if not md_file.exists():
                    md_candidates = list(item.glob("*.md"))
                    md_file = md_candidates[0] if md_candidates else None
                if md_file and md_file.exists():
                    r = parse_recipe(md_file, category)
                    if r:
                        recipes.append(r)
                    else:
                        failed += 1

    recipes.sort(key=lambda r: r["name"])

    OUTPUT.write_text(json.dumps(recipes, ensure_ascii=False, indent=2), encoding="utf-8")

    # Stats
    cats = {}
    for r in recipes:
        cats[r["category"]] = cats.get(r["category"], 0) + 1

    print(f"Total: {len(recipes)} recipes extracted")
    print(f"Failed: {failed}")
    print(f"Categories: {json.dumps(cats, ensure_ascii=False)}")
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    main()
