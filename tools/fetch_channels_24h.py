import asyncio
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
import re
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_distances

# ensure project root is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

# Try importing configuration from get_data/main.py
try:
    from get_data.main import TARGET_CHANNELS, TG_API_ID, TG_API_HASH, SESSION_PATH, TG_PROXY, MODEL_PATH
    print(f"✅ Successfully imported config from main.py")
    print(f"📋 Target Channels ({len(TARGET_CHANNELS)}): {TARGET_CHANNELS}")
    print(f"🧠 Model Path: {MODEL_PATH}")
except ImportError as e:
    print(f"❌ Failed to import from get_data.main: {e}")
    sys.exit(1)

async def fetch_data():
    # Define time window (Last 24 hours)
    cutoff_date = datetime.now(timezone.utc) - timedelta(hours=24)
    print(f"🕒 Fetching messages since: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")

    client = TelegramClient(SESSION_PATH, TG_API_ID, TG_API_HASH, proxy=TG_PROXY)
    
    try:
        await client.start()
    except Exception as e:
        print(f"❌ Failed to connect to Telegram: {e}")
        return

    all_messages = []
    stats = []

    print(f"🚀 Starting fetch for {len(TARGET_CHANNELS)} channels...")
    print("-" * 50)

    for channel in TARGET_CHANNELS:
        msg_count = 0
        status = "✅ OK"
        try:
            entity = await client.get_entity(channel)
            async for message in client.iter_messages(entity, limit=None):
                if message.date < cutoff_date:
                    break
                
                if not message.text or len(message.text.strip()) < 10:
                    continue
                
                msg_date = message.date.astimezone(timezone.utc).replace(tzinfo=None)
                
                # Clean text for display/processing
                clean_text = message.text.replace('\n', ' ').strip()
                
                all_messages.append({
                    "Channel": channel,
                    "ID": message.id,
                    "Date (UTC)": msg_date,
                    "Text": message.text, 
                    "CleanText": clean_text,
                    "Views": message.views or 0,
                    "Forwards": message.forwards or 0,
                    "Url": f"https://t.me/{channel}/{message.id}"
                })
                msg_count += 1
                
        except Exception as e:
            status = f"❌ Error: {str(e)}"
        
        stats.append({"Channel": channel, "Count": msg_count, "Status": status})
        print(f"   👉 {channel:<20} : {msg_count} msgs | {status}")

    await client.disconnect()

    if not all_messages:
        print("⚠️ No messages found in the last 24 hours.")
        return

    # Convert to DataFrame for preprocessing
    df = pd.DataFrame(all_messages)
    
    print("-" * 50)
    print(f"🧹 Preprocessing (Original: {len(df)} rows)...")

    # 1. Preprocessing (The "Physical Cut")
    # Filter out "Daily Summary" noise rows
    noise_mask = (df['Text'].str.len() > 600) & (df['Text'].str.contains('快讯|总结|今日|收听', regex=True))
    removed_count = noise_mask.sum()
    
    if removed_count > 0:
        df = df[~noise_mask]
        print(f"✂️ Removed {removed_count} 'Daily Summary' noise rows.")
    
    # CRITICAL: Reset index to align with distance matrix
    df = df.reset_index(drop=True)
    
    if df.empty:
        print("⚠️ All messages were filtered out as noise.")
        return

    # 1.5 Template Cleaning (Regex)
    def clean_template_noise(text):
        if not isinstance(text, str): return ""
        # Remove Markdown Links: [Text](URL)
        text = re.sub(r'\[.*?\]\(http.*?\)', '', text)
        # Remove Separators: |
        text = text.replace('|', '')
        # Remove Handles: @WatcherGuru
        text = re.sub(r'@\w+', '', text)
        # Remove extra whitespace
        return text.strip()

    print(f"� Applying Template Cleaning (Regex)...")
    df['Cleaned_Text'] = df['Text'].apply(clean_template_noise)

    print(f"�🧠 Clustering {len(df)} items using TF-IDF + Cosine Distance...")
    
    # 2. Vectorization & Distance Calculation
    try:
        # Use TfidfVectorizer on Cleaned_Text
        # Using analyzer='char' as generic fallback for Chinese without Jieba
        # ngram_range=(2,3) to capture some semantic meaning in characters
        print("   • Vectorizing (TF-IDF char-level)...")
        vectorizer = TfidfVectorizer(
            max_features=5000, 
            analyzer='char',
            ngram_range=(2, 3) 
        )
        
        # KEY CHANGE: fit_transform on Cleaned_Text
        X = vectorizer.fit_transform(df['Cleaned_Text'])
        
        # Compute Cosine Distance Matrix (1 - cosine_similarity)
        print("   • Computing Cosine Distance Matrix...")
        distance_matrix = cosine_distances(X)
        
        # 3. Clustering (DBSCAN)
        print("   • Running DBSCAN (eps=0.30, min=1)...")
        # min_samples=1 ensures NO noise points (-1). Isolated points become their own cluster.
        db = DBSCAN(eps=0.30, min_samples=1, metric='precomputed')
        db.fit(distance_matrix)
        labels = db.labels_
        
        # Assign labels
        df["Cluster_ID"] = labels
        df.rename(columns={"Cluster_ID": "Optimized_Cluster_ID"}, inplace=True)
            
    except Exception as e:
        print(f"❌ Clustering failed: {e}")
        df["Optimized_Cluster_ID"] = -1

    # Calculate Cluster Sizes
    cluster_counts = df['Optimized_Cluster_ID'].value_counts().to_dict()
    df['Cluster_Size'] = df['Optimized_Cluster_ID'].map(cluster_counts)
    
    # Sort: First by Cluster Size (descending), then ID, then Date
    df = df.sort_values(by=["Cluster_Size", "Optimized_Cluster_ID", "Date (UTC)"], ascending=[False, True, False])
    
    # Generate filename
    output_dir = os.path.join(current_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"telegram_clustered_v2_{timestamp}.xlsx"
    filepath = os.path.join(output_dir, filename)
    
    try:
        # Reorder columns
        cols = ["Optimized_Cluster_ID", "Cluster_Size", "Channel", "Date (UTC)", "Text", "Views", "Url"]
        existing_cols = df.columns.tolist()
        final_cols = cols + [c for c in existing_cols if c not in cols and c != "CleanText"]
        
        df[final_cols].to_excel(filepath, index=False)
        print(f"💾 Data saved to: {filepath}")
        
        # Print Clustering Summary
        total_clusters = len(cluster_counts)
        single_item_clusters = sum(1 for size in cluster_counts.values() if size == 1)
        
        print(f"\n🧩 Clustering Summary (min_samples=1, NO NOISE):")
        print(f"   Total Messages: {len(df)}")
        print(f"   Total Distinct Events: {total_clusters}")
        print(f"   Multi-source Events: {total_clusters - single_item_clusters}")
        print(f"   Single-source (Alpha?): {single_item_clusters}")
        print(f"   Top 5 Clusters:")
        print(df['Optimized_Cluster_ID'].value_counts().head(5))
        
        # Verify no -1
        if -1 in df['Optimized_Cluster_ID'].values:
            print("⚠️ Warning: Noise (-1) still detected. Check DBSCAN logic.")
        else:
            print("✅ Verified: No noise (-1) labels.")
        
    except Exception as e:
        print(f"❌ Error saving Excel: {e}")

    # Print Summary Table
    print("\n📊 Channel Statistics:")
    print(f"{'Channel':<20} | {'Count':<6} | {'Status'}")
    print("-" * 40)
    for s in stats:
        print(f"{s['Channel']:<20} | {s['Count']:<6} | {s['Status']}")
    print("-" * 40)

if __name__ == "__main__":
    asyncio.run(fetch_data())
