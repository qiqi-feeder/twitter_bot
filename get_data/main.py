import asyncio
import os
import sys
import time
import math
import numpy as np
import httpx
import pandas as pd
import pytz
import re
import uuid
import json
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_distances
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ==========================================
# 1. 基础配置
# ==========================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from utils.config_loader import config_loader
from history.history_manager import history_manager

try:
    from twitter.api_client import twitter_client
except ImportError:
    twitter_client = None
    print("⚠️ 未找到 twitter.api_client")

CN_TZ = pytz.timezone("Asia/Shanghai")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-75dfc7ad5ffa44f0ad1a0cd96fbed486")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
TG_API_ID = int(os.getenv("TG_API_ID", 35900060))
TG_API_HASH = os.getenv("TG_API_HASH", "4ac1483bc4e3cb1a4e2514f483bdaec4")
SESSION_PATH = os.path.join(BASE_DIR, "crypto_session")
PROXY_URL = None
TG_PROXY = None

TARGET_CHANNELS = [
    # "NewListingsFeed",
    # "coinpowernews",
    "news_crypto",
    "ZoomerfiedNews",
    "cointelegraph",
    "WatcherGuru",
    # "coingeckonews",
    "telonews_cn",
    "btcnewsdaily",
    "theblockbeats",
    "wublock",
    "TechFlowDaily",
    "ChannelPANews",
    "CoinDeskGlobal",
    "the_block_crypto",
]

client_ds = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    http_client=httpx.Client(proxy=PROXY_URL)
)

# ==========================================
# 2. 核心逻辑：权重与分类 (V3.2)
# ==========================================

CATEGORY_SCORES = {
    "政府": 300, "政府、监管部门": 300,
    "交易所": 250, "交易所（项目方、官方公告）": 250,
    "金融": 200, "金融机构、传统公司": 200,
    "链上": 150, "链上数据（行情统计平台）": 150,
    "媒体": 100, "媒体转述内容（间接消息源）": 100,
    "其他": 50
}

# 映射 Category 到早报栏目
SECTION_MAP = {
    "政府": "━━ 一、精选头条 ━━",
    "金融": "━━ 一、精选头条 ━━",
    "交易所": "━━ 二、项目动态 ━━",
    "链上": "━━ 二、项目动态 ━━",
    "媒体": "━━ 三、市场观察 ━━",
    "其他": "━━ 三、市场观察 ━━"
}

def get_base_score(category_name):
    if not category_name: return 50
    if category_name in CATEGORY_SCORES: return CATEGORY_SCORES[category_name]
    if "政府" in category_name or "监管" in category_name: return 300
    if "交易所" in category_name or "项目方" in category_name: return 250
    if "金融" in category_name or "机构" in category_name: return 200
    if "链上" in category_name: return 150
    if "媒体" in category_name: return 100
    return 50

def deepseek_classify(text):
    prompt = f"""你是一个加密货币新闻分类专家。请根据内容，仅从以下五个关键词中选出一个返回：
    - '媒体' (据消息称、报道称)
    - '链上' (数据显示、资金流入)
    - '交易所' (官方宣布、项目方、上币公告)
    - '金融' (某公司、银行、ETF机构)
    - '政府' (监管机构、SEC、胜诉、政策)
    内容：{text[:300]}"""
    try:
        response = client_ds.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            timeout=15
        )
        res = response.choices[0].message.content.strip()
        for key in ["政府", "交易所", "金融", "链上", "媒体"]:
            if key in res: return key
        return "其他"
    except:
        return "其他"

def clean_template_noise(text):
    if not isinstance(text, str): return ""
    text = re.sub(r'\[.*?\]\(http.*?\)', '', text)
    text = text.replace('|', '')
    text = re.sub(r'@\w+', '', text)
    return text.strip()

def deepseek_fuse_event(base_text, other_texts):
    """
    Fuses multiple source texts into a single coherent narrative using DeepSeek.
    """
    combined_text = f"Source 1: {base_text}\n"
    for i, txt in enumerate(other_texts):
        combined_text += f"Source {i+2}: {txt}\n"
        
    prompt = f"""你是一个专业的加密货币新闻主编。
我将提供关于【同一个事件】的来自【不同信源】的多篇报道。
请你综合所有信息，去除重复内容，去除广告，保留所有关键事实。
将它们“融合”成一篇**客观、精炼、信息密度大**的中文新闻快讯。
字数 150 字以内。不要带任何前缀。

【输入素材】：
{combined_text[:1500]} 

【输出】："""

    try:
        response = client_ds.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            timeout=30
        )
        return response.choices[0].message.content.strip()
    except:
        return base_text

# ==========================================
# 3. 抓取、聚类、融合 (Pipeline)
# ==========================================
async def fetch_rank_fuse_pipeline(limit=6, hours=12):
    # 1. Fetch
    cutoff_date = datetime.now(timezone.utc) - timedelta(hours=hours)
    print(f"🕒 Fetching since: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S UTC')} ({hours}h window)")

    client = TelegramClient(SESSION_PATH, TG_API_ID, TG_API_HASH, proxy=TG_PROXY)
    await client.start()

    all_messages = []
    print(f"🚀 Fetching {len(TARGET_CHANNELS)} channels...")
    
    for channel in TARGET_CHANNELS:
        try:
            entity = await client.get_entity(channel)
            async for message in client.iter_messages(entity, limit=None):
                if message.date < cutoff_date: break
                if not message.text or len(message.text.strip()) < 10: continue
                msg_date = message.date.astimezone(timezone.utc).replace(tzinfo=None)
                all_messages.append({
                    "Channel": channel,
                    "ID": message.id,
                    "Date (UTC)": msg_date,
                    "Text": message.text, 
                    "Views": message.views or 0,
                    "Reactions": sum([r.count for r in message.reactions.results]) if message.reactions else 0,
                    "Forwards": message.forwards or 0
                })
        except: pass
    
    await client.disconnect()
    
    if not all_messages: return []
    df = pd.DataFrame(all_messages)
    
    # 2. Preprocess
    noise_mask = (df['Text'].str.len() > 600) & (df['Text'].str.contains('快讯|总结|今日|收听', regex=True))
    df = df[~noise_mask].reset_index(drop=True)
    df['Cleaned_Text'] = df['Text'].apply(clean_template_noise)
    
    if df.empty: return []

    # 3. Cluster
    try:
        vectorizer = TfidfVectorizer(max_features=5000, analyzer='char', ngram_range=(2, 3))
        X = vectorizer.fit_transform(df['Cleaned_Text'])
        distance_matrix = cosine_distances(X)
        db = DBSCAN(eps=0.30, min_samples=1, metric='precomputed')
        db.fit(distance_matrix)
        df["Cluster_ID"] = db.labels_
    except: return []
    
    # 4. Rank
    grouped = df.groupby("Cluster_ID")
    events = []
    
    print("📊 Ranking Events...")
    
    for cluster_id, group in grouped:
        if len(group) < 2: continue # Consensus Check
            
        rep_idx = group['Text'].str.len().idxmax()
        rep_text = group.loc[rep_idx, 'Text']
        
        total_views = group['Views'].sum()
        total_reactions = group['Reactions'].sum()
        total_forwards = group['Forwards'].sum() if 'Forwards' in group.columns else 0
        latest_ts = group['Date (UTC)'].max().timestamp()
        source_count = len(group['Channel'].unique())

        category = deepseek_classify(rep_text)
        base_score = get_base_score(category)
        
        # Scoring V3.2
        keyword_factor = 1.0
        text_lower = rep_text.lower()
        if any(kw in text_lower for kw in ["sec", "approve", "hacked", "listing", "binance", "mainnet"]):
            keyword_factor = 1.2
        if any(kw in text_lower for kw in ["giveaway", "promo", "sign up", "airdrop claim"]):
            keyword_factor = 0.5
            
        source_multiplier = 1 + 0.30 * (source_count - 1)
        if source_multiplier > 3.0: source_multiplier = 3.0
        
        adjusted_base = base_score * keyword_factor * source_multiplier
        heat_score = 40 * math.log10(total_views + 1)
        weighted_interactions = total_reactions + (total_forwards * 5)
        quality_score = 1500 * (weighted_interactions / (total_views + 50))
        
        now_ts = datetime.now().timestamp()
        hours_passed = (now_ts - latest_ts) / 3600
        decay_factor = 0.95 ** max(hours_passed, 0)
        
        final_score = (adjusted_base + heat_score + quality_score) * decay_factor
        
        events.append({
            "Score": final_score,
            "Category": category,
            "Original_Text": rep_text,
            "Group_Texts": group[group.index != rep_idx]['Text'].tolist(),
            "Source_Count": source_count
        })
        
    if not events: return []
    events = sorted(events, key=lambda x: x["Score"], reverse=True)
    
    # Take Top N candidates
    top_candidates = events[:limit] 
    
    # Fuse them
    print(f"⚡️ Fusing Top {len(top_candidates)} Events...")
    for evt in top_candidates:
        other_texts = evt["Group_Texts"][:5]
        evt["Fused_Text"] = deepseek_fuse_event(evt["Original_Text"], other_texts)
        
    return top_candidates

# ==========================================
# 4. 生成单条新闻 (Section Based)
# ==========================================
def generate_news_item(fused_text, section):
    """
    Rewrite the input text into a concise news item based on its section.
    """
    system_prompt = f"""
# Role
You are a Professional Crypto News Editor. 
Task: Rewrite the input text into a concise news item based on its section.

# Input
- **Section**: {section}
- **Content**: [See User Input]

# Writing Guidelines

## 1. Section: ━━ 一、精选头条 ━━
- **Style**: Serious, Formal. (Mainstream Media style)
- **Focus**: Key facts and market impact.
- **Title**: Subject + Verb + Result (e.g. "Fed Chair Announces Rate Cut")

## 2. Section: ━━ 二、项目动态 ━━
- **Style**: Direct, Informative.
- **Focus**: What is the update? Who is involved? Money amounts.
- **Title**: Project Name + Specific Update

## 3. Section: ━━ 三、市场观察 ━━
- **Style**: Objective, Data-driven.
- **Focus**: Price action, security alerts, or market sentiment.
- **Title**: Topic + Key Data/Event

# General Constraints
- **Language**: Simplified Chinese.
- **No Fluff**: Delete phrases like "It is worth noting", "According to reports".
- **Format**: Return strict JSON string: {{"title": "...", "body": "..."}}
"""
    
    try:
        response = client_ds.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": fused_text}
            ],
            temperature=0.7,
            response_format={ "type": "json_object" }
        )
        response_str = response.choices[0].message.content.strip()
        if "```json" in response_str:
            response_str = response_str.split("```json")[1].split("```")[0].strip()
        elif "```" in response_str:
             response_str = response_str.split("```")[1].split("```")[0].strip()
            
        return json.loads(response_str)
    except Exception as e:
        print(f"❌ Rewriting failed: {e}")
        return {"title": "Error", "body": fused_text[:100]}

import random

# ==========================================
# 5. 组装早报 (按配额)
# ==========================================
def assemble_daily_briefing(events, title_prefix="币圈早报"):
    print(f"📝 Assembling {title_prefix} from {len(events)} candidates...")
    
    # 1. Bucket events by Section
    # Order matters for the final output
    section_buckets = {
        "━━ 一、精选头条 ━━": [],
        "━━ 二、项目动态 ━━": [],
        "━━ 三、市场观察 ━━": []
    }
    
    # 2. Distribute (High Score First)
    for evt in events:
        category = evt["Category"]
        target_section = SECTION_MAP.get(category, "━━ 三、市场观察 ━━")
        section_buckets[target_section].append(evt)
        
    # 3. Apply Quotas (Soft Limits)
    # Target: Headlines~10, Projects~5, Market~3
    quotas = {
        "━━ 一、精选头条 ━━": 10,
        "━━ 二、项目动态 ━━": 5,
        "━━ 三、市场观察 ━━": 3
    }
    
    # Use Dynamic Title
    current_time_str = datetime.now(CN_TZ).strftime('%Y/%m/%d %H:%M')
    final_text = f"Crypto Market Aggregator | {title_prefix} [{current_time_str}]\n\n"
    
    # 4. Generate Text
    order = ["━━ 一、精选头条 ━━", "━━ 二、项目动态 ━━", "━━ 三、市场观察 ━━"]
    
    for section_name in order:
        candidates = section_buckets[section_name]
        limit = quotas.get(section_name, 5)
        
        # Select Top N by Score first
        selected_items = candidates[:limit]
        
        if not selected_items: continue
        
        # Randomize order within the section
        random.shuffle(selected_items)
        
        final_text += f"{section_name}\n\n"
        
        section_index = 1 # Restart numbering for each section
        
        for evt in selected_items:
            print(f"   ✍️ Rewriting item {section_index} ({section_name})...")
            # Reuse caching if possible? No, we just generate.
            news_json = generate_news_item(evt["Fused_Text"], section_name)
            
            title = news_json.get("title", "")
            body = news_json.get("body", "")
            
            final_text += f"{section_index}、{title}\n{body}\n\n"
            section_index += 1
            
    return final_text

# ==========================================
# 6. 主流程
# ==========================================
def run_once():
    # 1. Determine Title & Window based on Time
    now_cn = datetime.now(CN_TZ)
    if now_cn.hour < 12:
        title = "币圈早报"
    else:
        title = "币圈晚报"
        
    print(f"\n[{now_cn.strftime('%Y-%m-%d %H:%M:%S')}] {title} Task Started...")
    
    # 2. Pipeline Execution (12H Window)
    # Fetch top 30 to ensure we fill the buckets (10+5+3 = 18 total)
    top_events = asyncio.run(fetch_rank_fuse_pipeline(limit=30, hours=12))
    
    if not top_events:
        print("📭 No events found.")
        return
        
    # 3. Assemble Briefing with Dynamic Title
    briefing_text = assemble_daily_briefing(top_events, title_prefix=title)
    
    print("\n" + "="*40)
    print(briefing_text)
    print("="*40 + "\n")
    
    # 3. History & Post
    config = config_loader.get_config()
    twitter_config = config.get('twitter', {})
    enable_auto_post = twitter_config.get('enable_auto_post', False)
    
    job_id = f"briefing_{int(time.time())}_{str(uuid.uuid4())[:8]}"
    mode = 'live' if enable_auto_post else 'test'
    
    history_manager.add_record(
        job_id=job_id,
        content=briefing_text,
        scheduled_time=datetime.now().isoformat(),
        status='pending',
        source='auto_briefing',
        mode=mode
    )
    
    if enable_auto_post:
        print("🚀 Sending to Twitter...")
        try:
            # Twitter Thread check? Or long tweet?
            # Assuming Twitter Premium or thread splitter logic exists in client
            # For now just post as is (api_client usually handles splitting if needed or fails)
            res = twitter_client.post_tweet(briefing_text)
            if isinstance(res, dict) and (res.get("success") or "data" in res):
                print("✅ Sent:", res.get("tweet_url"))
                history_manager.update_status(job_id, 'sent', tweet_url=res.get("tweet_url"))
            else:
                print("❌ Failed:", res)
                history_manager.update_status(job_id, 'failed', error=str(res))
        except Exception as e:
            print(f"❌ Error: {e}")
            history_manager.update_status(job_id, 'failed', error=str(e))
    else:
        print("🛑 Auto-Post OFF.")
        history_manager.update_status(job_id, 'sent')

if __name__ == "__main__":
    run_once()
