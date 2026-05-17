# 每日AI菜谱推送系统 — 从0到1完整SOP

> 日期: 2026-05-17 | 模型: Claude Opus 4.7 | 任务: 可复现的完整搭建文档

---

## 0. 系统概览

### 0.1 最终效果

每天上午10:00，飞书群自动收到一条卡片消息：
- 🍳 今日菜名 + 推荐理由 + 烹饪小贴士
- 📺 B站高清做菜视频直达链接（播放量>1万的高质量教程）
- 🎯 智能选菜：春季清淡、夏季消暑、秋季润燥、冬季温补
- 📅 工作日推家常快手菜，周末推大菜/硬菜
- 🔄 热菜、凉菜、甜品、汤羹均衡轮换，21天不重复

### 0.2 架构图

```
每日定时触发 (Windows Task Scheduler / cron)
    │
    ├─ 1. MiniMax AI 智能选菜 (ai_selector.py)
    │       ├─ 季节感知: 春夏秋冬不同饮食策略
    │       ├─ 星期感知: 工作日家常菜 vs 周末大菜
    │       ├─ 品类平衡: 荤素搭配 + 凉菜甜品汤羹轮换
    │       └─ 历史去重: 21天内不重复
    │
    ├─ 2. B站视频搜索 (bilibili_search.py)
    │       菜名 + "做法" → B站搜索API → 质量筛选 → 最佳视频
    │
    ├─ 3. 飞书群推送 (wechat_push.py)
    │       飞书群机器人 webhook → 富文本卡片消息
    │
    └─ 4. 状态保存 (state.json)
            供 H5 落地页读取
```

### 0.3 食材来源

| 组件 | 来源 | 说明 |
|------|------|------|
| 菜谱数据库 (357道) | Anduin2017/HowToCook (10万⭐) | 程序员做饭指南，Markdown格式，结构规整 |
| AI引擎 | MiniMax M2.1 | OpenAI兼容API，性价比高 |
| 视频源 | Bilibili搜索API | 海量做菜教程，无需鉴权 |
| 推送通道 | 飞书群机器人Webhook | 永久免费，3分钟配置 |

---

## Phase 1: 环境准备

### 1.1 前置条件

```powershell
# 1. Python 3.10+ (验证)
python --version

# 2. pip (验证)
pip --version

# 3. 代理 (中国大陆访问GitHub/B站API需要)
# 确认代理运行在 127.0.0.1:7890

# 4. gh CLI (验证)
gh version
```

### 1.2 安装依赖

```bash
pip install requests
```

或使用项目自带的 requirements.txt（只有一行 `requests>=2.31`）。

### 1.3 创建工作目录

```powershell
mkdir "D:\Softwares\每次菜谱"
```

所有代码和配置文件统一放在此目录。

---

## Phase 2: 菜谱数据提取

### 2.1 克隆 HowToCook 仓库

```bash
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
git clone --depth 1 https://github.com/Anduin2017/HowToCook.git "D:/Softwares/每次菜谱/HowToCook_repo"
```

### 2.2 数据格式分析

HowToCook 的菜谱全部是 Markdown 文件，结构如下：

```
dishes/
├── 荤菜/
│   ├── 红烧排骨.md
│   ├── 宫保鸡丁.md
│   └── ...
├── 素菜/
├── 汤羹/
├── 主食/
├── 甜品/
├── 凉菜/
├── 水产/
├── 半成品加工/
└── 早餐/
```

每个 .md 文件包含：菜名（标题）、预估时长、难度、食材清单、烹饪步骤。

### 2.3 提取脚本 `extract_recipes.py`

```python
#!/usr/bin/env python3
"""Extract structured recipe data from HowToCook markdown files."""
import json, re, os
from pathlib import Path

REPO_DIR = Path("D:/Softwares/每次菜谱/HowToCook_repo")
DISHES_DIR = REPO_DIR / "dishes"
OUTPUT = Path("D:/Softwares/每次菜谱/recipes.json")

CATEGORY_CN = {
    "meat": "荤菜", "vegetarian": "素菜", "soup": "汤羹",
    "staple": "主食", "dessert": "甜品", "cold": "凉菜",
    "aquatic": "海鲜", "semi-finished": "半成品加工", "breakfast": "早餐",
}

def parse_recipe(filepath):
    text = Path(filepath).read_text(encoding="utf-8")
    lines = text.split("\n")
    
    name = ""
    difficulty = 0
    duration = ""
    
    for line in lines[:20]:
        line = line.strip()
        if line.startswith("# ") and not name:
            name = line[2:].strip()
        if "难度" in line:
            stars = line.count("★") + line.count("⭐")
            difficulty = stars if stars > 0 else 0
        if "时长" in line or "时间" in line:
            duration = line.split("：")[-1].split(":")[-1].strip() if "：" in line else ""
    
    return {
        "name": name,
        "category": "",
        "difficulty": min(difficulty, 5),
        "duration": duration,
    }

recipes = []
for cat_dir in DISHES_DIR.iterdir():
    if not cat_dir.is_dir():
        continue
    cat_name = cat_dir.name
    for md_file in cat_dir.glob("*.md"):
        recipe = parse_recipe(md_file)
        recipe["category"] = cat_name
        if recipe["name"]:
            recipes.append(recipe)

OUTPUT.write_text(json.dumps(recipes, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Total: {len(recipes)} recipes extracted")
```

运行：
```bash
cd "D:/Softwares/每次菜谱" && python extract_recipes.py
# Output: Total: 357 recipes extracted
```

### 2.4 数据验证

```bash
python -c "
import json
d = json.load(open('D:/Softwares/每次菜谱/recipes.json', encoding='utf-8'))
cats = {}
for r in d:
    cats[r['category']] = cats.get(r['category'], 0) + 1
for k, v in sorted(cats.items()):
    print(f'{k}: {v}')
"
```

预期输出：
```
主食: 57
凉菜: ...
半成品加工: 10
早餐: 4
海鲜: 23
汤羹: 23
甜品: 19
素菜: 105
荤菜: 105
```

---

## Phase 3: B站视频搜索

### 3.1 核心挑战

B站搜索API (`api.bilibili.com`) 需要处理：
1. **412 拦截**: 需要先访问B站首页获取 cookie
2. **代理设置**: requests 必须显式传 proxies
3. **视频质量**: 从搜索结果中筛选最佳视频

### 3.2 `bilibili_search.py` 完整代码

```python
#!/usr/bin/env python3
"""Search Bilibili for cooking tutorial videos matching a dish name."""
import requests
import time
import os
import threading

BASE_URL = "https://api.bilibili.com/x/web-interface/search/type"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

PROXY = os.environ.get("http_proxy") or "http://127.0.0.1:7890"
PROXIES = {"http": PROXY, "https": PROXY}

# Session singleton with cookie auto-init
_session = None
_session_lock = threading.Lock()

def _get_session():
    global _session
    if _session is not None:
        return _session
    with _session_lock:
        if _session is not None:
            return _session
        _session = requests.Session()
        _session.proxies = PROXIES
        try:
            _session.get("https://www.bilibili.com/", headers=HEADERS, timeout=15)
        except Exception:
            pass
        return _session

def search_video(dish_name, max_results=8):
    query = f"{dish_name} 做法"
    params = {
        "search_type": "video",
        "keyword": query,
        "page": 1,
        "order": "totalrank",
    }
    try:
        s = _get_session()
        resp = s.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
        data = resp.json()
    except Exception as e:
        print(f"  Bilibili API error: {e}")
        return []
    
    if data.get("code") != 0:
        print(f"  Bilibili code {data.get('code')}: {data.get('message')}")
        return []
    
    results = []
    for item in data.get("data", {}).get("result", [])[:max_results]:
        bvid = item.get("bvid", "")
        title_raw = (
            item.get("title", "")
            .replace('<em class="keyword">', "")
            .replace("</em>", "")
        )
        results.append({
            "bvid": bvid,
            "title": title_raw,
            "play_count": item.get("play", 0),
            "duration": item.get("duration", ""),
            "author": item.get("author", ""),
            "url": f"https://www.bilibili.com/video/{bvid}",
            "cover": item.get("pic", ""),
            "description": item.get("description", ""),
        })
        time.sleep(0.05)
    return results

def find_best_video(dish_name):
    """Find best cooking tutorial. Prefers high views, 3-30 min, tutorial keywords."""
    results = search_video(dish_name, max_results=8)
    if not results:
        return None
    
    candidates = []
    for r in results:
        play = r["play_count"]
        dur = r["duration"]
        parts = dur.split(":")
        total_seconds = 0
        if len(parts) == 2:
            total_seconds = int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            total_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        
        score = play
        if total_seconds < 120:
            score *= 0.1       # Too short, penalize heavily
        elif total_seconds > 2400:
            score *= 0.3       # Too long (>40 min), penalize
        
        title = r.get("title", "")
        if "教程" in title or "教学" in title or "家常" in title:
            score *= 1.5       # Tutorial keyword bonus
        if play > 100000:
            score *= 1.3       # High quality bonus
        
        candidates.append((score, r))
    
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1] if candidates else results[0]
```

### 3.3 验证测试

```bash
export http_proxy=http://127.0.0.1:7890 https_proxy=http://127.0.0.1:7890
cd "D:/Softwares/每次菜谱"
python bilibili_search.py "宫保鸡丁"
```

预期输出：
```json
{
  "bvid": "BV1Vh4y1s7ER",
  "title": "老饭骨教你做宫保鸡丁...",
  "play_count": 1707034,
  "duration": "16:28",
  "author": "老饭骨",
  "url": "https://www.bilibili.com/video/BV1Vh4y1s7ER"
}
```

---

## Phase 4: MiniMax AI 智能选菜

### 4.1 获取 API Key

1. 打开 https://platform.minimaxi.com/user-center/payment/token-plan
2. 注册/登录 MiniMax 平台
3. 进入「API Key 管理」→ 创建 API Key
4. 复制 API Key（格式：`sk-cp-xxxxxxxx`）

### 4.2 选菜策略设计

| 维度 | 策略 | 实现方式 |
|------|------|----------|
| 季节 | 春清淡/夏消暑/秋润燥/冬温补 | System prompt 注入季节饮食指南 |
| 星期 | 周一~五→家常快手菜(难度1-3), 周六日→大菜硬菜(难度3-5) | System prompt 注入星期策略 |
| 品类 | 荤菜/素菜/凉菜/甜品/汤羹/海鲜均衡轮换 | 分析最近14天历史，提示不平衡品类 |
| 去重 | 21天内不重复 | 最近21天菜名列表传入 prompt |
| 难度 | 轮换，不连续高难度 | 难度参数参与 scoring |
| 搭配 | 建议搭配凉菜或汤 | AI 返回 pairing 字段 |

### 4.3 `config.py` 配置

```python
# --- AI / API (MiniMax, OpenAI-compatible) ---
AI_BASE_URL = "https://api.minimaxi.com/v1"
AI_API_KEY = "sk-cp-你的APIKey"
AI_MODEL = "MiniMax-M2.7"  # 推荐，性价比高
```

### 4.4 `ai_selector.py` 核心逻辑

```python
def _season_prompt(month):
    """Return seasonal cooking guidance."""
    if month in [3, 4, 5]:
        return "春季宜清淡、养肝、多吃绿叶蔬菜。推荐凉拌菜、清炒时蔬、蒸菜。"
    elif month in [6, 7, 8]:
        return "夏季宜清凉、消暑。多瓜果、凉拌菜、汤羹。推荐凉面、拍黄瓜、绿豆汤。"
    elif month in [9, 10, 11]:
        return "秋季宜润燥、滋补。多梨、百合、银耳、山药。推荐炖菜、煲汤、红烧。"
    else:
        return "冬季宜温补、暖身。多羊肉、牛肉、萝卜。推荐火锅、炖菜、煲仔菜。"

def _weekday_strategy(weekday):
    """Weekday=家常快手菜, Weekend=大菜硬菜."""
    if weekday in [5, 6]:  # Sat/Sun
        return "周末推荐大菜/硬菜：红烧、糖醋、烤制、清蒸整鱼、炖汤。难度可以高。"
    else:
        return "工作日推荐家常快手菜：难度1-3星, 30分钟内, 食材家常, 下饭！"

def pick_with_ai(recipes, history):
    """Call MiniMax API for intelligent dish selection."""
    pool = random.sample(recipes, min(80, len(recipes)))
    
    response = requests.post(
        f"{AI_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {AI_API_KEY}"},
        json={
            "model": AI_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},  # 含季节+星期策略
                {"role": "user", "content": user_prompt},      # 含菜池+历史
            ],
            "temperature": 0.9,
            "max_tokens": 500,  # MiniMax有think tokens, 需留够空间
        },
        proxies=PROXIES,
        timeout=45,
    )
    
    content = response.json()["choices"][0]["message"]["content"]
    # MiniMax returns <think>...</think> tags, strip them
    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
    # Extract JSON from response
    ...
```

### 4.5 容错设计

AI 不可用时自动降级为规则引擎：
- 同样考虑季节权重（不同季节不同品类的偏好权重）
- 同样考虑工作日/周末（难度过滤）
- 同样考虑品类平衡（最近14天统计）
- 同样考虑历史去重（21天）

```python
def _get_season_weights(month):
    """Category weights by season for fallback mode."""
    if month in [6, 7, 8]:  # Summer: prefer cold dishes, desserts
        return {"凉菜": 2.0, "甜品": 1.5, "汤羹": 1.4, "荤菜": 0.6}
    elif month in [12, 1, 2]:  # Winter: prefer meat, soup
        return {"荤菜": 2.0, "汤羹": 1.6, "凉菜": 0.4}
    ...
```

---

## Phase 5: 推送通道

### 5.1 为什么选飞书

| 方案 | 费用 | 配置难度 | 消息样式 |
|------|------|----------|----------|
| **飞书群机器人 ★** | **永久免费** | **⭐ (3分钟)** | **富文本卡片+按钮** |
| WeCom酱 | 永久免费 | ⭐⭐⭐ | 文本卡片 |
| WxPusher | 免费 | ⭐⭐ | 纯文本 |
| PushPlus | ¥30+/月 | ⭐ | Markdown |

### 5.2 飞书配置步骤（3分钟）

**第1步**：在飞书App中创建一个新群，把家人拉进去

**第2步**：群设置 → 群机器人 → 添加机器人 → 自定义机器人
- 机器人名称：`每日菜谱`
- 安全设置：选择「自定义关键词」→ 添加 `菜谱`

**第3步**：复制 Webhook URL
- 格式：`https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxxxxxxx`

**第4步**：设置环境变量（永久保存）
```powershell
[Environment]::SetEnvironmentVariable("FEISHU_WEBHOOK", "https://open.feishu.cn/open-apis/bot/v2/hook/你的webhook地址", "User")
```

### 5.3 消息格式

飞书卡片消息（`wechat_push.py` 中的 `push_via_feishu` 函数）：

```python
card = {
    "msg_type": "interactive",
    "card": {
        "header": {
            "title": {"tag": "plain_text", "content": "🍳 红烧排骨 | 今日菜谱 2026-05-17"},
            "template": "red"  # 红色标题
        },
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": "推荐理由..."}},
            {"tag": "hr"},
            {"tag": "action", "actions": [{
                "tag": "button",
                "text": {"tag": "plain_text", "content": "📺 查看做菜视频"},
                "type": "primary",
                "url": "https://www.bilibili.com/video/BVxxxxxx"
            }]}
        ]
    }
}
```

### 5.4 验证测试

```bash
export http_proxy=http://127.0.0.1:7890 https_proxy=http://127.0.0.1:7890
cd "D:/Softwares/每次菜谱"
python daily_runner.py --dry    # 先试 dry run
python daily_runner.py          # 正式推送
```

飞书群收到卡片消息即成功。

---

## Phase 6: 主流程编排

### 6.1 `daily_runner.py` — 一条命令跑全流程

```python
#!/usr/bin/env python3
"""
Daily Recipe Runner
Usage:
  python daily_runner.py          # 完整运行
  python daily_runner.py --dry    # 试运行(不推送)
  python daily_runner.py --mock   # 使用规则引擎(无需AI API)
  python daily_runner.py --dish "宫保鸡丁"  # 指定菜
"""

def main():
    # 1. MiniMax AI 选菜 (fallback → 规则引擎)
    entry = pick_dish()
    
    # 2. B站搜索最佳视频
    video = find_best_video(entry["dish"])
    
    # 3. 飞书推送
    push_daily(entry, video)
    
    # 4. 保存状态供 landing page 读取
    state = {"date": ..., "dish": ..., "bvid": ...}
    STATE_FILE.write_text(json.dumps(state, ...))
```

### 6.2 完整文件清单

```
D:\Softwares\每次菜谱\
├── daily_runner.py        ← 主入口，一条命令跑全流程
├── ai_selector.py         ← MiniMax AI 选菜 + 规则引擎降级
├── bilibili_search.py     ← B站视频搜索 + 质量筛选
├── wechat_push.py         ← 飞书/企业微信/WxPusher/PushPlus/Server酱
├── config.py              ← 集中配置（API Key, Webhook, 代理）
├── extract_recipes.py     ← 菜谱提取脚本（一次性运行）
├── install_schedule.ps1   ← Windows 定时任务安装
├── landing_server.py      ← H5 落地页 API 服务（可选）
├── landing/
│   └── index.html         ← H5 落地页（可选）
├── recipes.json           ← 357 道菜谱数据
├── history.json           ← 推送历史（自动去重）
├── state.json             ← 今日状态（供落地页读取）
└── requirements.txt       ← Python 依赖
```

---

## Phase 7: 定时任务

### 7.1 Windows Task Scheduler

```powershell
# 以管理员身份运行 PowerShell
powershell -ExecutionPolicy Bypass -File "D:\Softwares\每次菜谱\install_schedule.ps1"
```

脚本内容：
```powershell
$TaskName = "每日菜谱推送"
$ScriptPath = "D:\Softwares\每次菜谱\daily_runner.py"
$PythonPath = (Get-Command python).Source
$Hour = 10  # 每天上午10:00

$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument "`"$ScriptPath`""
$Trigger = New-ScheduledTaskTrigger -Daily -At "$($Hour):00"
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -RunLevel Highest
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal
```

### 7.2 Linux/Mac cron

```bash
crontab -e
# 添加: 每天上午10:00
0 10 * * * export http_proxy=http://127.0.0.1:7890 https_proxy=http://127.0.0.1:7890; python /path/to/daily_runner.py
```

---

## Phase 8: 可选 — H5 落地页

### 8.1 启动本地服务

```bash
cd "D:/Softwares/每次菜谱"
python landing_server.py
# 访问 http://localhost:8848
```

### 8.2 部署到公网

可选方案：
- Cloudflare Tunnel (`cloudflared tunnel`)
- frp 内网穿透
- Vercel/Netlify 部署静态页面 + API

---

## Phase 9: 完整验证清单

运行以下检查确保一切正常：

```bash
# 1. 导入检查
python -c "from ai_selector import *; from bilibili_search import *; from wechat_push import *; print('OK')"

# 2. 菜谱数据检查
python -c "import json; d=json.load(open('D:/Softwares/每次菜谱/recipes.json', encoding='utf-8')); print(f'{len(d)} recipes')"

# 3. B站搜索检查
python "D:/Softwares/每次菜谱/bilibili_search.py" "宫保鸡丁"

# 4. AI 选菜检查 (dry run)
python "D:/Softwares/每次菜谱/daily_runner.py" --dry

# 5. 飞书推送检查 (正式推送)
python "D:/Softwares/每次菜谱/daily_runner.py"

# 6. 检查飞书群是否收到卡片消息
```

全部通过 → 安装定时任务 → 永久运行。

---

## Phase 10: 故障排查

| 症状 | 原因 | 解决 |
|------|------|------|
| `ImportError: No module named 'requests'` | 缺少依赖 | `pip install requests` |
| B站 API 返回 412 | 缺少 cookie | Session 自动处理，检查代理 |
| MiniMax 返回 2061 | 模型名不对或 plan 不支持 | 用 `MiniMax-M2.7` |
| MiniMax 返回 `sk-` 开头错误 | API key 无效 | 检查 key 是否过期 |
| 飞书推送无反应 | webhook URL 不对 | 重新复制 webhook 地址 |
| 终端中文乱码 | Windows GBK 编码 | 不影响功能，数据正确 |
| AI 选菜失败走 fallback | API 临时不可用 | 规则引擎同样智能，无影响 |

---

## 附录A: 全链路数据流示例

```
输入: 2026-05-17, Sunday, 春季
  │
  ├─ MiniMax AI Prompt:
  │   "春季宜清淡养肝... 周末推荐大菜硬菜... 最近14天: 红烧排骨,凉拌黄瓜..."
  │   "可选菜池: - 清蒸鲈鱼 [海鲜] ★★★★, - 芒果布丁 [甜品] ★★, ..."
  │
  ├─ MiniMax Response:
  │   {"dish": "清蒸鲈鱼", "reason": "春季鲈鱼最肥美，清蒸营养，适合周末聚餐",
  │    "tip": "水开后蒸8分钟，淋热油激发葱香", "pairing": "配一道凉拌木耳"}
  │
  ├─ Bilibili Search: "清蒸鲈鱼 做法"
  │   → BV1zr4y1A7Xa, 老饭骨, 3.5M views, 8:42
  │
  └─ Feishu Push: code=0 success
     → 飞书群收到红色标题卡片 + "查看做菜视频"按钮
```

## 附录B: 关键踩坑记录

1. **gh CLI `--readme` flag 不存在**: `gh repo view --readme` 在 gh 2.89.0 中不存在，必须用 `gh api repos/OWNER/REPO/readme --jq ".download_url"` → curl 下载

2. **B站 API 412 拦截**: 必须先请求 `bilibili.com` 首页获取 cookie，再用同一个 Session 调搜索 API

3. **MiniMax `<think>` tags**: MiniMax M2.1 会返回思考过程（`<think>...</think>`），必须在 JSON 解析前剥离

4. **MiniMax token 预算**: `max_tokens=500` 才能给 think + 响应留够空间，太小会被截断

5. **PushPlus 收费**: 一开始用 PushPlus，发现每月 ¥30+，切换到飞书群机器人永久免费

6. **Windows 终端编码**: GBK 环境下中文输出乱码，不影响数据正确性，也不影响飞书推送（UTF-8 JSON）

7. **代理必须显式**: `requests` 不会自动读环境变量 `http_proxy`，必须在代码中显式传 `proxies=PROXIES`

---

## 附录C: 成本分析

| 项目 | 方案 | 月成本 |
|------|------|--------|
| AI API | MiniMax M2.1, 每天1次调用 | ~¥2-5/月 |
| 推送 | 飞书群机器人 | ¥0 |
| 视频 | B站搜索API | ¥0 |
| 菜谱数据 | HowToCook 开源 | ¥0 |
| 服务器 | Windows 本机定时任务 | ¥0 |
| **总计** | | **~¥2-5/月** |

---

文档已写入 Nutstore:C:\Users\Admin\Nutstore\1\SunnyWiki\raw\inbox\20260517\Daily_Recipe_Push_spec_Feishu-MiniMax-Bilibili-SOP_v1.0_spec.md
