import asyncio
import os
import sys
import pandas as pd
import numpy as np
import re
import httpx
import math
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_distances
from openai import OpenAI
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# ensure project root is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

# Import Config
try:
    from get_data.main import TARGET_CHANNELS, TG_API_ID, TG_API_HASH, SESSION_PATH, TG_PROXY
    print(f"✅ Successfully imported config from main.py")
except ImportError as e:
    print(f"❌ Failed to import from get_data.main: {e}")
    sys.exit(1)

# DeepSeek Config
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-75dfc7ad5ffa44f0ad1a0cd96fbed486")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
PROXY_URL = None 

client_ds = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    http_client=httpx.Client(proxy=PROXY_URL)
)

# V3.2 Scores
CATEGORY_SCORES = {
    "政府": 300, "政府、监管部门": 300,
    "交易所": 250, "交易所（项目方、官方公告）": 250,
    "金融": 200, "金融机构、传统公司": 200,
    "链上": 150, "链上数据（行情统计平台）": 150,
    "媒体": 100, "媒体转述内容（间接消息源）": 100,
    "其他": 50
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
请你综合所有信息，去除重复内容，去除广告（如giveaway、注册链接），保留所有关键事实（数字、人名、机构名、时间），
将它们“融合”成一篇**客观、精炼、信息密度大**的中文新闻快讯。
字数控制在 150 字以内。不要带任何前缀（如"融合报道："），直接输出正文。

【输入素材】：
{combined_text[:1500]} 

【输出】："""

    try:
        response = client_ds.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3, # Slightly creative but factual
            timeout=30
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ Fusion failed: {e}")
        return base_text # Fallback to base text

async def fetch_rank_fuse():
    # 1. Fetch (Modified to 12 Hours as requested)
    cutoff_date = datetime.now(timezone.utc) - timedelta(hours=12)
    print(f"🕒 Fetching messages since: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S UTC')} (12h window)")

    client = TelegramClient(SESSION_PATH, TG_API_ID, TG_API_HASH, proxy=TG_PROXY)
    await client.start()

    all_messages = []
    print(f"🚀 Starting fetch for {len(TARGET_CHANNELS)} channels...")
    
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
                    "Forwards": message.forwards or 0,
                    "Url": f"https://t.me/{channel}/{message.id}"
                })
        except Exception: pass
    
    await client.disconnect()
    
    if not all_messages:
        print("Empty.")
        return

    df = pd.DataFrame(all_messages)
    
    # 2. Preprocess
    noise_mask = (df['Text'].str.len() > 600) & (df['Text'].str.contains('快讯|总结|今日|收听', regex=True))
    df = df[~noise_mask].reset_index(drop=True)
    df['Cleaned_Text'] = df['Text'].apply(clean_template_noise)
    
    # 3. Cluster
    print(f"🧠 Clustering {len(df)} items...")
    vectorizer = TfidfVectorizer(max_features=5000, analyzer='char', ngram_range=(2, 3))
    X = vectorizer.fit_transform(df['Cleaned_Text'])
    distance_matrix = cosine_distances(X)
    
    db = DBSCAN(eps=0.30, min_samples=1, metric='precomputed')
    db.fit(distance_matrix)
    df["Cluster_ID"] = db.labels_
    
    # 4. Group & Filter Multi-source (>2)
    grouped = df.groupby("Cluster_ID")
    events = []
    
    print("📊 Ranking & Fusing Multi-source Events...")
    
    for cluster_id, group in grouped:
        # User Requirement: Source Count > 2
        source_channels = group['Channel'].unique()
        source_count = len(source_channels)
        
        if source_count < 2: 
            continue
            
        # Get representative text (Longest) for Classification fallback
        rep_idx = group['Text'].str.len().idxmax()
        rep_text = group.loc[rep_idx, 'Text']
        
        # Calculate Aggregated Stats
        total_views = group['Views'].sum()
        total_reactions = group['Reactions'].sum()
        total_forwards = group['Forwards'].sum() if 'Forwards' in group.columns else 0
        latest_ts = group['Date (UTC)'].max().timestamp()
        
        # 5. Classify
        category = deepseek_classify(rep_text)
        base_score = get_base_score(category)
        
        # 6. Scoring Logic v3.2
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
        if hours_passed < 0: hours_passed = 0
        decay_factor = 0.95 ** hours_passed
        
        final_score = (adjusted_base + heat_score + quality_score) * decay_factor
        
        # 7. LLM FUSION ⚡️
        print(f"   ⚡️ Fusing Event ID {cluster_id} (Sources: {source_count})...")
        other_texts = group[group.index != rep_idx]['Text'].tolist()
        
        # Prepare comparison data
        limit_other_texts = other_texts[:5] 
        combined_inputs = f"[Source 1 - Main]: {rep_text}\n"
        for i, txt in enumerate(limit_other_texts):
            combined_inputs += f"[Source {i+2}]: {txt}\n"

        # Limit fusion inputs to top 5 to avoid token overflow
        fused_summary = deepseek_fuse_event(rep_text, limit_other_texts)
        
        events.append({
            "Cluster_ID": cluster_id,
            "Size": source_count,
            "Category": category,
            "Score": final_score,
            "Fused_Summary": fused_summary, # The LLM Result
            "Original_Representative": rep_text, # The main original text (Full)
            "All_Input_Texts": combined_inputs, # All texts fed to LLM
            "Base_Score": adjusted_base, 
            "Heat_Score": heat_score, 
            "Quality_Score": quality_score, 
            "Total_Views": total_views,
            "Total_Reactions": total_reactions,
            "Total_Forwards": total_forwards,
            "Sources": ", ".join(source_channels),
            "Latest_Date": group['Date (UTC)'].max()
        })
        
    if not events:
        print("No events with > 2 sources found.")
        return

    # 8. Sort & Export relative to tools/output
    events_df = pd.DataFrame(events)
    events_df = events_df.sort_values(by="Score", ascending=False)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"fused_events_{timestamp}.xlsx"
    # Ensure tools/output exists (though we made it with mkdir)
    output_dir = os.path.join(current_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    
    filepath = os.path.join(output_dir, output_filename)
    
    events_df.to_excel(filepath, index=False)
    print(f"🏆 Saved {len(events_df)} Fused Events to: {filepath}")
    
    # Print Top 3
    print("\n🏆 Top 3 Fused Events:")
    for i, row in events_df.head(3).iterrows():
        print(f"{i+1}. [{row['Category']}] Score: {row['Score']:.1f} | Sources: {row['Size']}")
        print(f"   📝 {row['Fused_Summary']}")
        print(f"   -------------------")

if __name__ == "__main__":
    asyncio.run(fetch_rank_fuse())
