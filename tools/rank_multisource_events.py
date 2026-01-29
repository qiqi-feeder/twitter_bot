import asyncio
import os
import sys
import pandas as pd
import numpy as np
import re
import httpx
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
PROXY_URL = None # modify if needed based on main.py

client_ds = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    http_client=httpx.Client(proxy=PROXY_URL)
)

# Dynamic Equilibrium Strategy Scores
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
    # Remove Markdown Links
    text = re.sub(r'\[.*?\]\(http.*?\)', '', text)
    # Remove Separators
    text = text.replace('|', '')
    # Remove Handles
    text = re.sub(r'@\w+', '', text)
    return text.strip()

async def fetch_and_rank():
    # 1. Fetch
    cutoff_date = datetime.now(timezone.utc) - timedelta(hours=24)
    print(f"🕒 Fetching messages since: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")

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
    
    # 2. Preprocess (Filter Noise + Clean Template)
    # Filter Daily Summaries
    noise_mask = (df['Text'].str.len() > 600) & (df['Text'].str.contains('快讯|总结|今日|收听', regex=True))
    df = df[~noise_mask].reset_index(drop=True)
    
    # Clean Template
    df['Cleaned_Text'] = df['Text'].apply(clean_template_noise)
    
    # 3. Cluster
    print(f"🧠 Clustering {len(df)} items...")
    vectorizer = TfidfVectorizer(max_features=5000, analyzer='char', ngram_range=(2, 3))
    X = vectorizer.fit_transform(df['Cleaned_Text'])
    distance_matrix = cosine_distances(X)
    
    db = DBSCAN(eps=0.30, min_samples=1, metric='precomputed') # min=1 -> No noise
    db.fit(distance_matrix)
    df["Cluster_ID"] = db.labels_
    
    # 4. Group & Filter Multi-source
    grouped = df.groupby("Cluster_ID")
    events = []
    
    print("📊 Ranking Multi-source Events...")
    
    for cluster_id, group in grouped:
        # We only care about Multi-source (size > 1)
        if len(group) < 2: 
            continue
            
        # Get representative text (Longest)
        rep_text = group.loc[group['Text'].str.len().idxmax(), 'Text']
        
        # Calculate Aggregated Stats
        total_views = group['Views'].sum()
        total_reactions = group['Reactions'].sum()
        total_forwards = group['Forwards'].sum() if 'Forwards' in group.columns else 0
        latest_ts = group['Date (UTC)'].max().timestamp()
        
        # 5. Classify
        category = deepseek_classify(rep_text)
        base_score = get_base_score(category)
        
        # 6. Scoring Logic v3.2 (Forwards Weighted & Keyword Boost)
        # ------------------------------------------------------------------
        # A. Adjusted Base Score (Context & Consensus)
        # Step B: Keyword Boost/Penalty
        keyword_factor = 1.0
        text_lower = rep_text.lower()
        if any(kw in text_lower for kw in ["sec", "approve", "hacked", "listing", "binance", "mainnet"]):
            keyword_factor = 1.2
        if any(kw in text_lower for kw in ["giveaway", "promo", "sign up", "airdrop claim"]):
            keyword_factor = 0.5
            
        # Step C: Source Consensus Multiplier
        # Boosted: 0.15 -> 0.30 per extra source
        # 3 sources: 1 + 0.6 = 1.6x (Significant boost)
        source_count = len(group['Channel'].unique())
        source_multiplier = 1 + 0.30 * (source_count - 1)
        if source_multiplier > 3.0: source_multiplier = 3.0
        
        adjusted_base = base_score * keyword_factor * source_multiplier
        
        # B. Heat Score (Log Volume)
        import math
        heat_score = 40 * math.log10(total_views + 1)
        
        # C. Quality Score (Weighted Interactions)
        # Fix: If likes disabled, weight Forwards heavily (x5)
        weighted_interactions = total_reactions + (total_forwards * 5)
        quality_score = 1500 * (weighted_interactions / (total_views + 50))
        
        # D. Time Decay
        now_ts = datetime.now().timestamp()
        hours_passed = (now_ts - latest_ts) / 3600
        if hours_passed < 0: hours_passed = 0
        decay_factor = 0.95 ** hours_passed
        
        # Final Formula
        final_score = (adjusted_base + heat_score + quality_score) * decay_factor
        # ------------------------------------------------------------------
        
        events.append({
            "Cluster_ID": cluster_id,
            "Size": source_count,
            "Category": category,
            "Score": final_score,
            "Base_Score": adjusted_base, 
            "Heat_Score": heat_score, 
            "Quality_Score": quality_score, 
            "Summary_Text": rep_text,
            "Total_Views": total_views,
            "Total_Reactions": total_reactions,
            "Total_Forwards": total_forwards,
            "Sources": ", ".join(group['Channel'].unique()),
            "Latest_Date": group['Date (UTC)'].max()
        })
        
    if not events:
        print("No multi-source events found.")
        return

    # 7. Sort & Export
    events_df = pd.DataFrame(events)
    events_df = events_df.sort_values(by="Score", ascending=False)
    
    output_dir = os.path.join(current_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ranked_events_{timestamp}.xlsx"
    filepath = os.path.join(output_dir, filename)
    
    events_df.to_excel(filepath, index=False)
    print(f"🏆 Saved {len(events_df)} Ranked Events to: {filepath}")
    
    # Print Top 5
    print("\n🏆 Top 5 Events:")
    for i, row in events_df.head(5).iterrows():
        print(f"{i+1}. [{row['Category']}] Score: {row['Score']:.1f} | Size: {row['Size']} | Views: {row['Total_Views']}")
        print(f"   {row['Summary_Text'][:50]}...")

if __name__ == "__main__":
    asyncio.run(fetch_and_rank())
