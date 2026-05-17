#!/usr/bin/env python3
"""
AI-driven daily recipe selector powered by MiniMax.
Implements: seasonal awareness, weekday vs weekend, category balancing.
"""
import json
import random
import re
import requests
from datetime import datetime

from config import (
    RECIPES_JSON, HISTORY_FILE, STATE_FILE,
    AI_BASE_URL, AI_API_KEY, AI_MODEL, PROXIES,
)


def load_recipes():
    return json.loads(RECIPES_JSON.read_text(encoding="utf-8"))


def load_history():
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    return []


def save_history(entry):
    history = load_history()
    history.append(entry)
    if len(history) > 180:
        history = history[-180:]
    HISTORY_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ── Seasonal & weekday logic ──

def _season_prompt(month):
    """Return seasonal cooking guidance based on month."""
    if month in [3, 4, 5]:
        return (
            "现在是春季。春季饮食要点：清淡养肝，多吃绿叶蔬菜、芽菜、春笋、韭菜等时令食材。"
            "推荐：凉拌菜、清炒时蔬、蒸菜、春卷。避免过于油腻和辛辣。"
        )
    elif month in [6, 7, 8]:
        return (
            "现在是夏季。夏季饮食要点：清凉消暑，开胃爽口。多吃瓜果类(冬瓜、丝瓜、苦瓜)、"
            "凉拌菜、汤羹类。推荐：凉面、拍黄瓜、酸辣菜、绿豆汤、冰粉等甜品。"
            "避免重油重辣和长时间炖煮。"
        )
    elif month in [9, 10, 11]:
        return (
            "现在是秋季。秋季饮食要点：润燥养肺，滋阴补气。多吃梨、百合、银耳、山药、"
            "南瓜、菌菇。推荐：炖菜、煲汤、红烧、焖煮。适合进补但不要过于油腻。"
        )
    else:  # 12, 1, 2
        return (
            "现在是冬季。冬季饮食要点：温补暖身，御寒驱寒。多吃羊肉、牛肉、萝卜、白菜、"
            "根茎类蔬菜。推荐：火锅、炖菜、煲仔菜、红烧、烤制。适当进补，汤羹要热乎。"
        )


def _weekday_strategy(weekday, is_holiday=False):
    """
    Return cooking strategy by weekday.
    周一~周五: 家常快手菜 (30分钟内, 简单易做)
    周六~周日: 大菜/硬菜 (可复杂, 适合家人聚餐)
    """
    if is_holiday:
        return (
            "今天是节假日，推荐做一道大菜/硬菜！可以是复杂的荤菜、海鲜、或需要长时间炖煮的菜肴。"
            "适合全家聚餐，有仪式感的菜。难度可以高一点。"
        )

    if weekday in [5, 6]:  # Saturday(5), Sunday(6)
        return (
            "今天是周末！推荐做一道有份量的「大菜」或「硬菜」。可以是："
            "红烧、糖醋、烤制、清蒸整鱼、炖汤、卤味、烤箱菜。"
            "难度可以高一些(3-5星)，时间可以长一点。适合家人一起享受。"
        )
    else:  # Monday-Friday
        return (
            "今天是工作日，推荐一道「家常快手菜」。要求："
            "1. 做法简单(难度1-3星)，30分钟内能完成"
            "2. 食材家常，容易买到"
            "3. 可以是热菜为主，搭配一道凉菜或甜品"
            "4. 营养均衡，荤素搭配合理"
            "5. 下饭！下饭！下饭！"
        )


def _category_balance_hint(history):
    """Analyze recent history to suggest category balancing."""
    recent = [h for h in history[-14:]]
    cat_counts = {}
    for h in recent:
        cat = h.get("category", "")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    hints = []
    # Check for overcooked categories
    for cat, count in cat_counts.items():
        if count >= 5:
            hints.append(f"最近{cat}吃得太频繁({count}次)，今天避免选{cat}")

    # Check for neglected categories
    all_cats = {"荤菜", "素菜", "汤羹", "主食", "甜品", "凉菜", "海鲜", "半成品加工"}
    for cat in all_cats:
        if cat not in cat_counts or cat_counts[cat] == 0:
            hints.append(f"已经很久没吃{cat}了，今天可以考虑{cat}")

    # Ensure variety: need hot dishes, cold dishes, desserts in rotation
    if "甜品" not in cat_counts or cat_counts.get("甜品", 0) <= 1:
        hints.append("最近甜品/点心偏少，可以穿插一道甜品类")
    if "汤羹" not in cat_counts or cat_counts.get("汤羹", 0) <= 1:
        hints.append("最近汤羹偏少，可以搭配一道汤")

    return "\n".join(hints[:5]) if hints else ""


def pick_with_ai(recipes, history, notes=""):
    """Use MiniMax AI to intelligently pick today's dish."""
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d %A")
    month = now.month
    weekday = now.weekday()  # 0=Mon, 6=Sun

    recent_names = [h["dish"] for h in history[-21:]]
    recent_dishes = [
        f"{h['dish']}[{h.get('category', '')}]" for h in history[-14:]
    ]

    # Build pool: random subset so prompt fits context
    pool = random.sample(recipes, min(80, len(recipes)))
    pool_text = "\n".join(
        f"- {r['name']} [{r['category']}] 难度{'★'*r['difficulty']}"
        for r in pool
    )

    season = _season_prompt(month)
    strategy = _weekday_strategy(weekday)
    balance = _category_balance_hint(history)

    system_prompt = (
        "你是一位经验丰富的中国家庭烹饪顾问。你的任务是根据当前季节、星期几、"
        "已吃过的菜和历史偏好，从菜谱库中为家人挑选今天最适合做的一道菜。\n\n"
        "核心规则：\n"
        "1. 绝对不能选最近21天内已吃过的菜\n"
        "2. 荤素搭配要合理，不能连续太多天荤菜\n"
        "3. 难度要轮换，不能天天高难度\n"
        "4. 必须严格考虑季节因素\n"
        "5. 工作日优先家常快手菜，周末优先大菜/硬菜\n"
        "6. 热菜、凉菜、甜品、汤羹要均衡轮换\n\n"
        f"{season}\n\n{strategy}\n\n"
        "返回纯JSON（不要markdown代码块，不要解释）：\n"
        '{"dish": "菜名(必须是菜谱库中的)", "reason": "推荐理由(50字内,亲切口吻,说明为什么今天适合做这道菜)", '
        '"tip": "做这道菜的关键小贴士(30字内,一两句话点出关键技巧)", '
        '"pairing": "建议搭配的凉菜或汤(15字内,可选)"}'
    )

    user_prompt = (
        f"今天是 {today_str}\n"
        f"最近21天已吃(绝对不要选)：{', '.join(recent_names) if recent_names else '无(刚开始)'}\n"
        f"最近14天详情：{', '.join(recent_dishes) if recent_dishes else '无'}\n"
        f"品类平衡建议：\n{balance}\n"
        f"{notes}\n"
        f"──── 请从以下菜谱库中选择一道 ────\n{pool_text}"
    )

    try:
        resp = requests.post(
            f"{AI_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {AI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": AI_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.9,
                "max_tokens": 500,
            },
            proxies=PROXIES,
            timeout=45,
        )
        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        # MiniMax returns thinking in <think>...</think> tags, strip them
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        # Also strip markdown code fences
        content = re.sub(r'```(?:json)?\s*', '', content)
        content = re.sub(r'```\s*$', '', content)

        # Extract JSON
        json_match = re.search(r'\{[^{}]*"dish"\s*:\s*"[^"]+"[^{}]*\}', content)
        if not json_match:
            json_match = re.search(r'\{[^}]+\}', content)
        if json_match:
            result = json.loads(json_match.group(0))
            return (
                result.get("dish", ""),
                result.get("reason", ""),
                result.get("tip", ""),
                result.get("pairing", ""),
            )
    except Exception as e:
        print(f"  AI selection failed: {e}")

    return None, None, None, None


def pick_dish(recipes=None, history=None):
    """
    Main entry: pick today's dish.
    1. Try MiniMax AI for intelligent selection
    2. Fall back to smart random with seasonal/weekday rules
    """
    if recipes is None:
        recipes = load_recipes()
    if history is None:
        history = load_history()

    notes = ""
    dish = reason = tip = pairing = None

    # Try AI first
    if AI_API_KEY:
        print("  调用 MiniMax AI 智能选菜...")
        dish, reason, tip, pairing = pick_with_ai(recipes, history, notes)

    # Fallback: smart rule-based random
    if not dish:
        print("  使用规则引擎智能随机...")
        dish, reason, tip, pairing = _smart_fallback(recipes, history)

    # Find recipe data
    recipe_data = next((r for r in recipes if r["name"] == dish), None)
    if recipe_data is None:
        recipe_data = recipes[0]

    entry = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "weekday": datetime.now().strftime("%A"),
        "dish": dish,
        "category": recipe_data.get("category", ""),
        "difficulty": recipe_data.get("difficulty", 0),
        "reason": reason,
        "tip": tip,
        "pairing": pairing,
    }

    save_history(entry)
    return entry


def _smart_fallback(recipes, history):
    """Rule-based fallback when AI unavailable. Still seasonal + weekday aware."""
    now = datetime.now()
    month = now.month
    weekday = now.weekday()

    recent_names = set(h["dish"] for h in history[-21:])
    recent_cats = [h.get("category", "") for h in history[-14:]]

    available = [r for r in recipes if r["name"] not in recent_names]
    if not available:
        available = recipes

    # Weekday: prefer difficulty 1-3, weekend: prefer 3-5
    if weekday < 5:  # Weekday
        weekday_pool = [r for r in available if r["difficulty"] <= 3]
        if weekday_pool:
            available = weekday_pool
        strategy = "工作日来道快手家常菜"
    else:  # Weekend
        weekend_pool = [r for r in available if r["difficulty"] >= 3]
        if weekend_pool:
            available = weekend_pool
        strategy = "周末了来道硬菜"

    # Category balancing
    cat_counts = {}
    for c in recent_cats:
        cat_counts[c] = cat_counts.get(c, 0) + 1
    dominant_cat = max(cat_counts, key=cat_counts.get) if cat_counts else ""

    if dominant_cat and len(available) > 5:
        other = [r for r in available if r.get("category") != dominant_cat]
        if other:
            available = other

    # Seasonal preference
    season_weights = _get_season_weights(month)
    weighted = []
    for r in available:
        cat = r.get("category", "")
        w = season_weights.get(cat, 1.0)
        weighted.append((w, r))
    weighted.sort(key=lambda x: x[0], reverse=True)

    # Pick from top third
    top_n = max(3, len(weighted) // 3)
    chosen = random.choice(weighted[:top_n])[1]

    season_names = {3: "春天", 4: "春天", 5: "春天",
                    6: "夏天", 7: "夏天", 8: "夏天",
                    9: "秋天", 10: "秋天", 11: "秋天"}
    season = season_names.get(month, "冬天")

    dish_name = chosen["name"]
    reason = f"{season}的{strategy}——{dish_name}，正好适合今天！"
    tip = "用心做好每一餐，家人一定吃得开心！"

    return dish_name, reason, tip, ""


def _get_season_weights(month):
    """Return category preference weights by season."""
    if month in [3, 4, 5]:  # Spring
        return {"素菜": 1.5, "凉菜": 1.3, "汤羹": 1.2, "海鲜": 1.2,
                "荤菜": 0.8, "甜品": 1.0, "主食": 1.0, "半成品加工": 0.7}
    elif month in [6, 7, 8]:  # Summer
        return {"凉菜": 2.0, "甜品": 1.5, "汤羹": 1.4, "素菜": 1.3,
                "海鲜": 0.9, "荤菜": 0.6, "主食": 1.0, "半成品加工": 0.8}
    elif month in [9, 10, 11]:  # Autumn
        return {"汤羹": 1.8, "荤菜": 1.3, "海鲜": 1.3, "素菜": 1.0,
                "甜品": 1.0, "主食": 1.0, "凉菜": 0.7, "半成品加工": 0.8}
    else:  # Winter
        return {"荤菜": 2.0, "汤羹": 1.6, "主食": 1.2, "海鲜": 1.1,
                "甜品": 0.9, "素菜": 0.7, "凉菜": 0.4, "半成品加工": 0.8}


if __name__ == "__main__":
    import sys
    recipes = load_recipes()
    history = load_history()
    result = pick_dish(recipes, history)
    for k, v in result.items():
        print(f"{k}: {v}")
