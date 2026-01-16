import chromadb
from chromadb.utils import embedding_functions
from sklearn.cluster import DBSCAN
import numpy as np
import os
import time
import math
from datetime import datetime, timedelta
import pytz

# ================= 配置 (必须与 main.py 一致) =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "crypto_db")
MODEL_PATH = os.path.join(BASE_DIR, "my_local_model") # 确保模型路径正确
COLLECTION_NAME = "crypto_v_pro"

# 必须加载 Transformer 模型才能进行聚类 (这步会有点慢)
print("⏳ 正在加载本地 Embedding 模型 (可能需要几秒钟)...")
os.environ['TRANSFORMERS_OFFLINE'] = '1'
try:
    emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=MODEL_PATH)
except Exception as e:
    print(f"❌ 模型加载失败，请检查路径: {MODEL_PATH}")
    print(e)
    exit()

def debug_calculate_trends():
    print(f"🔍 连接数据库: {DB_PATH}")
    client = chromadb.PersistentClient(path=DB_PATH)
    col = client.get_collection(name=COLLECTION_NAME, embedding_function=emb_fn)

    # 获取过去 24 小时的数据 (模拟当前窗口)
    # 你的 main.py 是按 8 小时窗口切分，这里我们取最近 12 小时方便调试
    now_ts = time.time()
    start_ts = now_ts - (12 * 3600) 

    print("📥 正在读取最近 12 小时的数据...")
    res = col.get(
        where={"timestamp": {"$gte": start_ts}},
        include=["documents", "embeddings", "metadatas"]
    )

    if not res["ids"]:
        print("📭 这段时间内没有数据。")
        return

    embeddings = np.array(res["embeddings"])
    print(f"🔢 获取到 {len(embeddings)} 条数据，正在进行 DBSCAN 聚类...")

    # === 核心逻辑：DBSCAN ===
    # min_samples=2 过滤掉单条孤立新闻
    clustering = DBSCAN(eps=0.42, min_samples=2, metric="cosine").fit(embeddings)
    labels = clustering.labels_

    trends = []
    
    unique_labels = set(labels)
    print(f"🧩 发现 {len(unique_labels) - (1 if -1 in unique_labels else 0)} 个热点聚类 (Label -1 为噪音)")

    for label in unique_labels:
        if label == -1:
            continue # 跳过噪音

        # 提取该聚类的所有新闻
        idx = np.where(labels == label)[0]
        metas = [res["metadatas"][i] for i in idx]
        docs = [res["documents"][i] for i in idx]

        # === 复刻打分公式 ===
        # 1. 基础分
        stars = max(m["stars"] for m in metas)
        base_score = stars * 50
        
        # 2. 来源信誉分 (这是聚类逻辑最强的地方)
        sources = set(m["source"] for m in metas)
        rep_score = len(sources) * 35 
        
        # 3. 互动分
        total_views = sum(m["views"] for m in metas)
        total_reacts = sum(m["reactions"] for m in metas)
        eng_score = math.log1p(total_views) * 5 + total_reacts * 2

        # 4. 时间衰减
        latest_ts = max(m["timestamp"] for m in metas)
        decay = 0.85 ** ((now_ts - latest_ts) / 3600)

        final_score = (base_score + rep_score + eng_score) * decay

        trends.append({
            "score": final_score,
            "summary": docs[0], # 取第一条做预览
            "count": len(docs),
            "sources": list(sources),
            "details": {
                "base": base_score,
                "rep": rep_score,
                "eng": eng_score,
                "decay": decay
            }
        })

    # 排序
    trends.sort(key=lambda x: x["score"], reverse=True)

    print("\n" + "="*50)
    print("🔥 真实算法计算出的 TOP 5 热点")
    print("="*50 + "\n")

    for i, t in enumerate(trends[:5]):
        print(f"🏆 第 {i+1} 名 [总分: {t['score']:.1f}] (聚合了 {t['count']} 条新闻)")
        print(f"📝 摘要: {t['summary'][:60]}...")
        print(f"📢 来源: {', '.join(t['sources'])}")
        print(f"🧮 得分构成: 基础({t['details']['base']}) + 多源信誉({t['details']['rep']}) + 互动({t['details']['eng']:.1f})")
        print(f"📉 时间衰减系数: {t['details']['decay']:.2f}")
        print("-" * 50)

if __name__ == "__main__":
    debug_calculate_trends()