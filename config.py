#!/usr/bin/env python3
"""Centralized configuration. Edit this file or set environment variables."""
import os
from pathlib import Path

# --- Paths ---
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
RECIPES_JSON = BASE_DIR / "recipes.json"
HISTORY_FILE = BASE_DIR / "history.json"
STATE_FILE = BASE_DIR / "state.json"

# --- AI / API (MiniMax, OpenAI-compatible) ---
# MiniMax API: https://platform.minimaxi.com/user-center/payment/token-plan
AI_BASE_URL = os.environ.get("RECIPE_AI_URL", "https://api.minimaxi.com/v1")
AI_API_KEY = os.environ.get("RECIPE_AI_KEY", "")  # 设置环境变量或在这里填写MiniMax API Key
AI_MODEL = os.environ.get("RECIPE_AI_MODEL", "MiniMax-M2.7")

# --- 飞书 / WeChat Push ---
# 推荐 feishu (飞书群机器人, 最简单, 永久免费)
PUSH_BACKEND = os.environ.get("RECIPE_PUSH_BACKEND", "feishu")

# 飞书群机器人 webhook
FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK", "")  # 飞书群机器人 webhook URL

# WeCom酱 — 注册企业微信 → 创建应用 → 获取三参数
WECOM_CORPID = os.environ.get("WECOM_CORPID", "")
WECOM_AGENTID = os.environ.get("WECOM_AGENTID", "")
WECOM_SECRET = os.environ.get("WECOM_SECRET", "")

# WxPusher (备选) — https://wxpusher.zjiecode.com/ 注册获取
WXPUSHER_TOKEN = os.environ.get("WXPUSHER_TOKEN", "")
WXPUSHER_TOPIC_ID = os.environ.get("WXPUSHER_TOPIC_ID", "")

# PushPlus (收费, 保留兼容)
PUSHPLUS_TOKEN = os.environ.get("PUSHPLUS_TOKEN", "")

# Server酱
SERVERCHAN_KEY = os.environ.get("SERVERCHAN_KEY", "")

# --- Proxy ---
HTTP_PROXY = os.environ.get("http_proxy") or "http://127.0.0.1:7890"
PROXIES = {"http": HTTP_PROXY, "https": HTTP_PROXY}

# --- Schedule ---
PUSH_HOUR = int(os.environ.get("RECIPE_PUSH_HOUR", "10"))
