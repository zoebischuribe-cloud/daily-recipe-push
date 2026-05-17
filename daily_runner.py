#!/usr/bin/env python3
"""
Daily Recipe Runner
===================
1. AI picks today's dish
2. Search Bilibili for best video
3. Push to WeChat

Usage:
  python daily_runner.py          # Run once
  python daily_runner.py --dry    # Dry run (no push)
  python daily_runner.py --dish "宫保鸡丁"  # Pick specific dish
"""
import sys, json
import argparse
from datetime import datetime
from pathlib import Path

from ai_selector import pick_dish, load_recipes, load_history
from bilibili_search import find_best_video
from wechat_push import push_daily
from config import STATE_FILE


def main():
    parser = argparse.ArgumentParser(description="每日菜谱推送")
    parser.add_argument("--dry", action="store_true", help="Dry run, no push")
    parser.add_argument("--dish", type=str, help="Force specific dish")
    parser.add_argument("--mock", action="store_true", help="Use smart random (no AI API needed)")
    args = parser.parse_args()

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 每日菜谱启动")

    # 1. Pick dish
    print("\n--- 1. 选菜 ---")
    recipes = load_recipes()

    if args.dish:
        recipe = next((r for r in recipes if r["name"] == args.dish), None)
        if not recipe:
            print(f"未找到: {args.dish}")
            sys.exit(1)
        dish_name = recipe["name"]
        category = recipe["category"]
        difficulty = recipe["difficulty"]
        reason = f"今日指定: {dish_name}"
        tip = "好好享受烹饪的乐趣！"
        entry = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "weekday": datetime.now().strftime("%A"),
            "dish": dish_name,
            "category": category,
            "difficulty": difficulty,
            "reason": reason,
            "tip": tip,
        }
        print(f"  指定菜: {dish_name} [{category}] 难度{'★'*difficulty}")
    else:
        entry = pick_dish()
        dish_name = entry["dish"]
        print(f"  今日推荐: {dish_name} [{entry['category']}] 难度{'★'*entry['difficulty']}")
        print(f"  理由: {entry['reason']}")

    # 2. Search video
    print(f"\n--- 2. 搜索视频 ---")
    video = find_best_video(dish_name)
    if video:
        print(f"  标题: {video['title']}")
        print(f"  UP主: {video['author']}")
        print(f"  播放: {video['play_count']:,}")
        print(f"  时长: {video['duration']}")
        print(f"  链接: {video['url']}")
    else:
        print(f"  未找到视频，将发送无视频推送")

    # 3. Push
    print(f"\n--- 3. 推送 ---")
    if args.dry:
        print("  [DRY RUN] 跳过推送")
        print(f"  将推送: {entry['dish']} → {video['url'] if video else '无视频'}")
    else:
        ok = push_daily(entry, video)
        if ok:
            print("  推送成功！")
        else:
            print("  推送失败 (请检查 token 配置)")
            sys.exit(1)

    # 4. Save state for landing page
    state = {
        "date": entry["date"],
        "dish": entry["dish"],
        "category": entry["category"],
        "difficulty": entry["difficulty"],
        "reason": entry.get("reason", ""),
        "tip": entry.get("tip", ""),
        "bvid": video["bvid"] if video else "",
        "author": video["author"] if video else "",
        "video_title": video["title"] if video else "",
    }
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 完成")


if __name__ == "__main__":
    main()
