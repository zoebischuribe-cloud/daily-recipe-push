#!/usr/bin/env python3
"""
Push daily recipe to WeChat.

Backends:
  wecomchan  — 企业微信应用消息 (推荐, 永久免费)
  wxpusher   — WxPusher (免费, 开源)
  pushplus   — PushPlus (收费, 已弃用)
  serverchan — Server酱 (有免费额度)

推荐 wecomchan: 注册企业微信 → 创建应用 → 家人扫码 → 永久免费推送
"""
import json, time
import requests
from config import (
    WECOM_CORPID, WECOM_AGENTID, WECOM_SECRET,
    FEISHU_WEBHOOK,
    WXPUSHER_TOKEN, WXPUSHER_TOPIC_ID,
    PUSHPLUS_TOKEN, SERVERCHAN_KEY,
    PUSH_BACKEND,
)

PROXIES = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}

# ---------- WeCom 应用消息 (WeCom酱: 开源免费, 推送到个人微信) ----------

def _wecom_access_token():
    """Get WeCom access_token (cached in memory for 7200s)."""
    cache_file = __import__('tempfile').gettempdir() + '/wecom_token_cache.json'
    try:
        c = json.load(open(cache_file))
        if c.get('ts', 0) > time.time() - 7100:
            return c.get('token')
    except:
        pass

    url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
    r = requests.get(url, params={
        "corpid": WECOM_CORPID, "corpsecret": WECOM_SECRET
    }, proxies=PROXIES, timeout=15)
    data = r.json()
    token = data.get("access_token", "")
    if token:
        json.dump({"token": token, "ts": time.time()}, open(cache_file, 'w'))
    return token


def push_via_wecomchan(title, content, video_url):
    """
    WeCom酱: 通过企业微信应用发送消息到个人微信.
    需要配置: WECOM_CORPID, WECOM_AGENTID, WECOM_SECRET
    接收方需在「企业微信插件」扫码关注.
    """
    if not all([WECOM_CORPID, WECOM_AGENTID, WECOM_SECRET]):
        print("  WeCom酱 未配置 (需要 CORPID/AGENTID/SECRET), 跳过")
        return False

    token = _wecom_access_token()
    if not token:
        print("  WeCom酱: 获取 access_token 失败")
        return False

    # 文本卡片消息
    text = f"{title}\n\n{content}\n\n👉 教程视频: {video_url}"

    try:
        r = requests.post(
            "https://qyapi.weixin.qq.com/cgi-bin/message/send",
            params={"access_token": token},
            json={
                "touser": "@all",
                "agentid": int(WECOM_AGENTID),
                "msgtype": "textcard",
                "textcard": {
                    "title": title,
                    "description": content.replace("**", "").replace("*", ""),
                    "url": video_url,
                    "btntxt": "查看教程视频",
                },
            },
            proxies=PROXIES,
            timeout=15,
        )
        data = r.json()
        errcode = data.get("errcode", -1)
        print(f"  WeCom酱: errcode={errcode} {data.get('errmsg', '')}")
        return errcode == 0
    except Exception as e:
        print(f"  WeCom酱 error: {e}")
        return False


# ---------- 飞书群机器人 (推荐: 最简单, 永久免费) ----------

def push_via_feishu(title, content, video_url):
    """
    飞书群机器人 webhook:
    1. 飞书建群, 拉家人进群
    2. 群设置 → 群机器人 → 添加自定义机器人 → 复制 webhook URL
    3. 把 URL 填到 FEISHU_WEBHOOK 环境变量

    消息格式: 富文本卡片, 带视频链接按钮
    """
    if not FEISHU_WEBHOOK:
        print("  飞书 webhook 未配置, 跳过")
        return False

    # Build a nice card
    card = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "red"
            },
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": content}},
                {"tag": "hr"},
                {
                    "tag": "action",
                    "actions": [{
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "📺 查看做菜视频"},
                        "type": "primary",
                        "url": video_url
                    }]
                }
            ]
        }
    }

    try:
        r = requests.post(
            FEISHU_WEBHOOK,
            json=card,
            proxies=PROXIES,
            timeout=15,
        )
        data = r.json()
        code = data.get("code", -1)
        print(f"  飞书: code={code} {data.get('msg', '')}")
        return code == 0
    except Exception as e:
        print(f"  飞书 error: {e}")
        return False


# ---------- WxPusher (开源免费, 推送到个人微信) ----------

def push_via_wxpusher(title, content, video_url):
    """
    WxPusher: https://wxpusher.zjiecode.com/
    免费开源, 需关注公众号获取 UID 和 token.
    """
    if not WXPUSHER_TOKEN:
        print("  WxPusher 未配置, 跳过")
        return False

    body = f"{title}\n\n{content}\n\n👉 {video_url}"

    try:
        r = requests.post(
            "https://wxpusher.zjiecode.com/api/send/message",
            json={
                "appToken": WXPUSHER_TOKEN,
                "content": body,
                "contentType": 1,  # 1=text
                "topicIds": [int(WXPUSHER_TOPIC_ID)] if WXPUSHER_TOPIC_ID else [],
                "uids": [],
            },
            proxies=PROXIES,
            timeout=15,
        )
        data = r.json()
        print(f"  WxPusher: code={data.get('code')} {data.get('msg', '')}")
        return data.get("code") == 1000
    except Exception as e:
        print(f"  WxPusher error: {e}")
        return False


# ---------- PushPlus (收费) ----------

def push_via_pushplus(title, content, video_url):
    if not PUSHPLUS_TOKEN:
        print("  PushPlus token not configured, skipping")
        return False
    body = f"## {title}\n\n{content}\n\n👉 [点击查看做菜视频]({video_url})\n\n---\n*每日菜谱 · AI 为你精选*"
    try:
        resp = requests.post(
            "https://www.pushplus.plus/send",
            json={"token": PUSHPLUS_TOKEN, "title": title, "content": body, "template": "markdown"},
            proxies=PROXIES, timeout=15,
        )
        data = resp.json()
        print(f"  PushPlus: code={data.get('code')}")
        return data.get("code") == 200
    except Exception as e:
        print(f"  PushPlus error: {e}")
        return False


# ---------- Server酱 ----------

def push_via_serverchan(title, content, video_url):
    if not SERVERCHAN_KEY:
        print("  ServerChan key not configured, skipping")
        return False
    full = f"{title}\n\n{content}\n\n{video_url}"
    try:
        resp = requests.post(
            f"https://sctapi.ftqq.com/{SERVERCHAN_KEY}.send",
            json={"title": title, "desp": full},
            proxies=PROXIES, timeout=15,
        )
        data = resp.json()
        print(f"  ServerChan: code={data.get('code')}")
        return data.get("code") == 0
    except Exception as e:
        print(f"  ServerChan error: {e}")
        return False


# ---------- Main ----------

PUSHERS = {
    "feishu":      push_via_feishu,
    "wecomchan":   push_via_wecomchan,
    "wxpusher":    push_via_wxpusher,
    "pushplus":    push_via_pushplus,
    "serverchan":  push_via_serverchan,
}


def push_daily(entry, video_info=None):
    dish = entry["dish"]
    category = entry.get("category", "")
    difficulty = entry.get("difficulty", 0)
    reason = entry.get("reason", "")
    tip = entry.get("tip", "")
    date_str = entry.get("date", "")

    stars = "★" * difficulty + "☆" * (5 - difficulty) if difficulty else ""

    title = f"🍳 {dish} | 今日菜谱 {date_str}"

    parts = [f"{dish} | {category} | {stars}"]
    if reason:
        parts.append(reason)
    if tip:
        parts.append(f"💡 {tip}")

    content = "\n".join(parts)

    video_url = video_info["url"] if video_info else ""
    if video_info:
        content += (
            f"\n\n📺 {video_info.get('title', '教程视频')}"
            f"\nUP主: {video_info.get('author', '')} | "
            f"播放: {video_info.get('play_count', 0):,}"
        )

    print(f"\n{'='*50}")
    print(f"今日推送: {dish}")
    print(f"视频: {video_url}")
    print(f"后端: {PUSH_BACKEND}")
    print(f"{'='*50}")

    pusher = PUSHERS.get(PUSH_BACKEND)
    if pusher:
        return pusher(title, content, video_url)
    else:
        print(f"  未知推送后端: {PUSH_BACKEND}")
        return False


if __name__ == "__main__":
    print(f"当前后端: {PUSH_BACKEND}")
    test_entry = {
        "date": "2026-05-17", "dish": "宫保鸡丁", "category": "荤菜",
        "difficulty": 4, "reason": "经典川菜香辣下饭！",
        "tip": "鸡肉提前腌制更嫩滑",
    }
    test_video = {"url": "https://www.bilibili.com/video/BV1Vh4y1s7ER",
                  "title": "老饭骨教你做宫保鸡丁", "author": "老饭骨", "play_count": 1707034}
    ok = push_daily(test_entry, test_video)
    print(f"\n结果: {'OK' if ok else 'FAILED'}")
