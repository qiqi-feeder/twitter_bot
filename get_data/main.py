import asyncio
import os
import time
import math
import numpy as np
import httpx
import pandas as pd
import pytz
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ==========================================
# 1. 基础配置
# ==========================================
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_DATASETS_OFFLINE'] = '1'

# 路径配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "my_local_model")
DB_PATH = os.path.join(BASE_DIR, "crypto_db")
SESSION_PATH = os.path.join(BASE_DIR, "crypto_session")

CN_TZ = pytz.timezone("Asia/Shanghai")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-75dfc7ad5ffa44f0ad1a0cd96fbed486")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
TG_API_ID = int(os.getenv("TG_API_ID", 35900060))
TG_API_HASH = os.getenv("TG_API_HASH", "4ac1483bc4e3cb1a4e2514f483bdaec4")

# 服务器通常无需代理
PROXY_URL = None
TG_PROXY = None

TARGET_CHANNELS = [
    "cointelegraph", "WatcherGuru", "coingeckonews", "telonews_cn",
    "btcnewsdaily", "NewListingsFeed", "coinpowernews", "news_crypto", "ZoomerfiedNews"
]

try:
    from twitter.api_client import twitter_client
except ImportError:
    twitter_client = None
    print("⚠️ 未找到 twitter.api_client")

client_ds = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    http_client=httpx.Client(proxy=PROXY_URL)
)

# ==========================================
# 2. 核心逻辑：权重与分类
# ==========================================

CATEGORY_SCORES = {
    "政府": 5000, "政府、监管部门": 5000,
    "交易所": 4000, "交易所（项目方、官方公告）": 4000,
    "金融": 3000, "金融机构、传统公司": 3000,
    "链上": 2000, "链上数据（行情统计平台）": 2000,
    "媒体": 1000, "媒体转述内容（间接消息源）": 1000,
    "其他": 500
}

def get_base_score(category_name):
    if not category_name: return 500
    if category_name in CATEGORY_SCORES: return CATEGORY_SCORES[category_name]
    if "政府" in category_name or "监管" in category_name: return 5000
    if "交易所" in category_name or "项目方" in category_name: return 4000
    if "金融" in category_name or "机构" in category_name: return 3000
    if "链上" in category_name: return 2000
    if "媒体" in category_name: return 1000
    return 500

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

# ==========================================
# 3. 抓取模块 (8小时版)
# ==========================================

async def update_database():
    print("🚀 启动抓取任务 (最近 8 小时)...")
    tg_client = TelegramClient(SESSION_PATH, TG_API_ID, TG_API_HASH, proxy=TG_PROXY)
    await tg_client.start()

    db_client = chromadb.PersistentClient(path=DB_PATH)
    emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=MODEL_PATH)
    collection = db_client.get_or_create_collection(name="crypto_news_vfinal", embedding_function=emb_fn)

    # 【关键修改】只抓取过去 8 小时的消息
    cutoff = datetime.now(timezone.utc) - timedelta(hours=8)

    total_new = 0
    for channel in TARGET_CHANNELS:
        try:
            entity = await tg_client.get_entity(channel)
            msgs = await tg_client.get_messages(entity, limit=50) # 8小时内通常不会超过50条/频道

            for m in msgs:
                if not m.text or m.date < cutoff or len(m.text) < 20: continue

                doc_id = f"{channel}_{m.id}"
                if collection.get(ids=[doc_id])['ids']: continue

                cat_key = deepseek_classify(m.text)
                full_names = {
                    "政府": "政府、监管部门", "交易所": "交易所（项目方、官方公告）",
                    "金融": "金融机构、传统公司", "链上": "链上数据（行情统计平台）",
                    "媒体": "媒体转述内容（间接消息源）"
                }
                full_cat_name = full_names.get(cat_key, cat_key)

                v = m.views or 0
                r = sum([re.count for re in m.reactions.results]) if m.reactions else 0

                collection.upsert(
                    documents=[m.text],
                    metadatas=[{
                        "source": channel, "timestamp": int(m.date.timestamp()),
                        "category": full_cat_name, "views": v, "reactions": r
                    }],
                    ids=[doc_id]
                )
                total_new += 1
        except Exception as e:
            print(f"❌ 频道 {channel} 报错: {e}")

    print(f"🏁 抓取完成，本轮新增 {total_new} 条。")
    await tg_client.disconnect()

# ==========================================
# 4. 排序与生成 (8小时版)
# ==========================================

def get_top_news_items(limit=3):
    print("📊 计算权重排名 (最近 8 小时数据)...")
    db_client = chromadb.PersistentClient(path=DB_PATH)
    emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=MODEL_PATH)
    collection = db_client.get_or_create_collection(name="crypto_news_vfinal", embedding_function=emb_fn)

    # 【关键修改】只从数据库检索最近 8 小时的数据
    start_time = int((datetime.now() - timedelta(hours=8)).timestamp())
    now_ts = datetime.now().timestamp()

    results = collection.get(where={"timestamp": {"$gte": start_time}})

    if not results['ids']:
        print("📭 最近 8 小时无数据。")
        return []

    scored_items = []
    for i in range(len(results['ids'])):
        doc = results['documents'][i]
        meta = results['metadatas'][i]

        cat = meta.get('category', '其他')
        base_score = get_base_score(cat)

        views = meta.get('views', 0)
        reactions = meta.get('reactions', 0)
        engagement_score = np.log1p(views) * 2 + reactions * 0.5

        ts = meta.get('timestamp', 0)
        hours_passed = (now_ts - ts) / 3600
        if hours_passed < 0: hours_passed = 0
        decay_factor = 0.97 ** hours_passed # 8小时内衰减影响很小，但保留

        final_score = (base_score + engagement_score) * decay_factor

        scored_items.append({
            "score": final_score,
            "text": doc,
            "category": cat
        })
    
    # 记录日志 (可选)
    try:
        df = pd.DataFrame(scored_items)
        if not df.empty:
            log_dir = os.path.join(BASE_DIR, "logs")
            if not os.path.exists(log_dir): os.makedirs(log_dir)
            df.sort_values("score", ascending=False).to_excel(
                os.path.join(log_dir, f"rank_8h_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"), index=False
            )
    except: pass

    scored_items.sort(key=lambda x: x["score"], reverse=True)
    if scored_items:
        # 返回前 limit 个
        top_items = scored_items[:limit]
        print(f"🏆 本时段 Top {len(top_items)}:")
        for idx, item in enumerate(top_items, 1):
            print(f"   {idx}. [{item['category']}] {item['score']:.2f}分")
        return top_items
    return []

def generate_tweet_content(news_items):
    # 确保传入的是列表
    if not isinstance(news_items, list):
        news_items = [news_items]
    
    # 提取所有分类作为标签候选
    categories = list(set([item['category'].split('、')[0] for item in news_items]))
    tags = " ".join([f"#{c}" for c in categories[:3]]) # 最多取3个标签
    
    # 构建新闻内容摘要
    news_content = ""
    for i, item in enumerate(news_items, 1):
        news_content += f"{i}. [{item['category']}] {item['text'][:200]}...\n"

    prompt = (
        f"你是加密货币推特大V，风格犀利、简洁。\n"
        f"请根据以下 {len(news_items)} 条高权重热门资讯写一条中文推文（Thread）：\n\n"
        f"{news_content}\n"
        f"要求：\n"
        f"1. **综合分析**：不要简单拼接，要找到这些新闻背后的市场情绪或关联。\n"
        f"2. **标签**：文末包含 {tags} 等标签。\n"
        f"3. **Emoji**：适当使用 Emoji 增加活力（不限数量）。\n"
        f"4. **长度**：不受字数限制，以内容质量为主，可以说透问题。\n"
    )
    try:
        r = client_ds.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        return None

def post_tweet_direct(text):
    if not twitter_client: return
    try:
        print(f"🚀 发送中 (长: {len(text)})...")
        res = twitter_client.post_tweet(text)
        if isinstance(res, dict) and (res.get("success") or "data" in res):
            print("✅ 成功:", res.get("tweet_url", "OK"))
        else:
            print("❌ 失败:", res)
    except Exception as e:
        print(f"❌ 异常: {e}")

# 导入配置加载器和历史记录管理器
import sys
import uuid
# 确保项目根目录在 path 中
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from utils.config_loader import config_loader
from history.history_manager import history_manager

def run_once():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 8小时任务启动...")
    
    # 1. 抓取数据
    asyncio.run(update_database())
    
    # 2. 生成内容 (Top 3 聚合)
    top_items = get_top_news_items(limit=3)
    if not top_items: return
    
    # 3. 检查配置
    config = config_loader.get_config()
    twitter_config = config.get('twitter', {})
    enable_auto_post = twitter_config.get('enable_auto_post', False)
    
    print(f"\n--- 正在聚合前 {len(top_items)} 条热门资讯 ---")
    
    tweet = generate_tweet_content(top_items)
    if not tweet: return
    
    print("🐦 内容生成完成:\n", tweet)
    
    # 4. 记录历史
    job_id = f"auto_{int(time.time())}_{str(uuid.uuid4())[:8]}"
    mode = 'live' if enable_auto_post else 'test'
    status = 'pending'
    
    history_manager.add_record(
        job_id=job_id,
        content=tweet,
        scheduled_time=datetime.now().isoformat(),
        status=status,
        source='auto',
        mode=mode
    )
    
    # 5. 执行发送 (如果启用)
    if enable_auto_post:
        print("🚀 自动发送已启用，正在去推特...")
        try:
            res = twitter_client.post_tweet(tweet)
            
            if isinstance(res, dict) and (res.get("success") or "data" in res):
                tweet_url = res.get("tweet_url") or res.get("url")
                print("✅ 发送成功:", tweet_url)
                history_manager.update_status(job_id, 'sent', tweet_url=tweet_url)
            else:
                error_msg = str(res)
                print("❌ 发送失败:", error_msg)
                history_manager.update_status(job_id, 'failed', error=error_msg)
                
        except Exception as e:
            error_msg = str(e)
            print(f"❌ 发送异常: {e}")
            history_manager.update_status(job_id, 'failed', error=error_msg)
    else:
        print("🛑 自动发送已禁用 (Dry-Run)，仅保存记录。")
        history_manager.update_status(job_id, 'sent')

if __name__ == "__main__":
    run_once()
# import asyncio
# import os
# import time
# import math
# import requests
# import numpy as np
# import httpx
# import pytz
# from datetime import datetime, timedelta, timezone
# from telethon import TelegramClient
# import chromadb
# from chromadb.utils import embedding_functions
# from sklearn.cluster import DBSCAN
# from openai import OpenAI

# # =====================================================
# # 1. 基础配置
# # =====================================================
# os.environ['TRANSFORMERS_OFFLINE'] = '1'
# os.environ['HF_DATASETS_OFFLINE'] = '1'

# CN_TZ = pytz.timezone("Asia/Shanghai")

# DEEPSEEK_API_KEY = "sk-75dfc7ad5ffa44f0ad1a0cd96fbed486"
# DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# PROXY_URL = None
# TG_PROXY = None

# TG_API_ID = 35900060
# TG_API_HASH = "4ac1483bc4e3cb1a4e2514f483bdaec4"

# MODEL_PATH = "/var/www/myproject/twitter_bot-main/my_local_model"

# TARGET_CHANNELS = [
#     "cointelegraph", "WatcherGuru", "coingeckonews", "telonews_cn",
#     "btcnewsdaily", "NewListingsFeed", "coinpowernews", "news_crypto", "ZoomerfiedNews"
# ]

# CATEGORY_MAP = {
#     "政府": {"full_name": "政府、监管部门", "stars": 4},
#     "交易所": {"full_name": "交易所", "stars": 3},
#     "金融": {"full_name": "金融机构", "stars": 3},
#     "媒体": {"full_name": "媒体", "stars": 2},
#     "链上": {"full_name": "链上数据", "stars": 2}
# }

# client_ds = OpenAI(
#     api_key=DEEPSEEK_API_KEY,
#     base_url=DEEPSEEK_BASE_URL,
#     http_client=httpx.Client(proxy=PROXY_URL)
# )

# # =====================================================
# # 2. 工具函数
# # =====================================================
# def get_current_window():
#     now = datetime.now(CN_TZ)
#     if now.hour < 8:
#         start = now.replace(hour=0, minute=0, second=0)
#     elif now.hour < 16:
#         start = now.replace(hour=8, minute=0, second=0)
#     else:
#         start = now.replace(hour=16, minute=0, second=0)
#     end = start + timedelta(hours=8)
#     return int(start.timestamp()), int(end.timestamp())


# def deepseek_classify(text):
#     prompt = f"选一个关键词返回（媒体/链上/交易所/金融/政府）：\n{text[:300]}"
#     try:
#         r = client_ds.chat.completions.create(
#             model="deepseek-chat",
#             messages=[{"role": "user", "content": prompt}],
#             temperature=0.1
#         )
#         res = r.choices[0].message.content.strip()
#         for k in CATEGORY_MAP:
#             if k in res:
#                 return k
#         return "媒体"
#     except:
#         return "媒体"


# # =====================================================
# # 3. Telegram → ChromaDB
# # =====================================================
# async def update_database():
#     tg = TelegramClient("/var/www/myproject/twitter_bot-main/crypto_session", TG_API_ID, TG_API_HASH, proxy=TG_PROXY)
#     await tg.start()

#     db = chromadb.PersistentClient("./crypto_db")
#     emb = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=MODEL_PATH)
#     col = db.get_or_create_collection("crypto_v_pro", embedding_function=emb)

#     cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

#     for ch in TARGET_CHANNELS:
#         try:
#             entity = await tg.get_entity(ch)
#             msgs = await tg.get_messages(entity, limit=30)
#             for m in msgs:
#                 if not m.text or m.date < cutoff:
#                     continue

#                 cat = deepseek_classify(m.text)
#                 meta = CATEGORY_MAP.get(cat, {"full_name": "其他", "stars": 1})

#                 views = m.views or 0
#                 reactions = sum(r.count for r in m.reactions.results) if m.reactions else 0

#                 col.upsert(
#                     documents=[m.text],
#                     metadatas=[{
#                         "source": ch,
#                         "timestamp": int(m.date.timestamp()),
#                         "category": meta["full_name"],
#                         "stars": meta["stars"],
#                         "views": views,
#                         "reactions": reactions
#                     }],
#                     ids=[f"{ch}_{m.id}"]
#                 )
#         except Exception as e:
#             print(f"❌ {ch} 失败: {e}")

#     await tg.disconnect()


# # =====================================================
# # 4. 聚类 + 打分（8小时窗口）
# # =====================================================
# def calculate_trends(top_n=3):
#     db = chromadb.PersistentClient("/var/www/myproject/twitter_bot-main/crypto_db")
#     emb = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=MODEL_PATH)
#     col = db.get_or_create_collection("crypto_v_pro", embedding_function=emb)

#     start_ts, end_ts = get_current_window()

#     res = col.get(
#         where={
#             "$and": [
#                 {"timestamp": {"$gte": start_ts}},
#                 {"timestamp": {"$lt": end_ts}}
#             ]
#         },
#         include=["documents", "embeddings", "metadatas"]
#     )

#     if not res["ids"]:
#         return []

#     X = np.array(res["embeddings"])
#     labels = DBSCAN(eps=0.42, min_samples=1, metric="cosine").fit(X).labels_

#     trends = []
#     now = time.time()

#     for label in set(labels):
#         idx = np.where(labels == label)[0]
#         metas = [res["metadatas"][i] for i in idx]
#         docs = [res["documents"][i] for i in idx]

#         stars = max(m["stars"] for m in metas)
#         base = stars * 50
#         sources = set(m["source"] for m in metas)
#         rep = len(sources) * 35
#         views = sum(m["views"] for m in metas)
#         reacts = sum(m["reactions"] for m in metas)
#         eng = math.log1p(views) * 5 + reacts * 2

#         latest = max(m["timestamp"] for m in metas)
#         decay = 0.85 ** ((now - latest) / 3600)

#         score = (base + rep + eng) * decay

#         trends.append({
#             "score": score,
#             "summary": max(docs, key=len),
#             "category": metas[0]["category"]
#         })

#     trends.sort(key=lambda x: x["score"], reverse=True)
#     return trends[:top_n]


# # =====================================================
# # 5. 生成推文 + 发送
# # =====================================================
# def generate_tweet(text, category):
#     prompt = (
#         f"你是加密货币推特大V，风格犀利、简洁。\n"
#         f"请根据以下新闻写一条中文推文：\n"
#         f"1. 必须包含 #{category.split('、')[0]} 标签\n"
#         f"2. 只能用 1-2 个Emoji\n"
#         f"3. 【绝对限制】内容必须控制在 110 个汉字以内！\n"  # <--- 缩减到 110
#         f"4. 不要包含任何 URL 链接\n\n"
#         f"新闻内容：\n{text}"
#     )
#     r = client_ds.chat.completions.create(
#         model="deepseek-chat",
#         messages=[{"role": "user", "content": prompt}]
#     )
#     return r.choices[0].message.content.strip()


# def post_tweet(text):
#     r = requests.post(
#         "http://localhost:5000/tweet/post",
#         data={"content": text},
#         timeout=15
#     )
#     if r.status_code != 200:
#         raise RuntimeError(r.text)
# from twitter.api_client import twitter_client

# # def post_tweet_direct(text):
# #     try:
# #         r = requests.post(
# #             "http://127.0.0.1:5000/tweet/post",
# #             data={"content": text},
# #             timeout=30  # 增加超时时间
# #         )
# #         r.raise_for_status()
# #         res = r.json()
# #         if res.get("success"):
# #             print("✅ 推文发送成功")
# #         else:
# #             print("❌ 推文发送失败:", res.get("error"))
# #     except requests.exceptions.RequestException as e:
# #         print(f"❌ 发推异常: {e}")
# #     except Exception as e:
# #         print(f"⚠️ 其他异常: {e}")
# def post_tweet_direct(text):
#     try:
#         res = twitter_client.post_tweet(text)
#         if res and isinstance(res, dict):
#             if res.get("success"):
#                 print("✅ 推文发送成功:", res.get("tweet_url"))
#             else:
#                 print("❌ 推文发送失败:", res.get("error"))
#         else:
#             print("❌ 发推返回异常，可能内容太长或内部失败")
#     except Exception as e:
#         print(f"❌ 发推异常: {e}")


# # def post_tweet_direct(text):
# #     try:
# #         res = twitter_client.post_tweet(text)
# #         if res.get("success"):
# #             print("✅ 推文发送成功:", res.get("tweet_url"))
# #         else:
# #             print("❌ 推文发送失败:", res.get("error"))
# #     except Exception as e:
# #         print(f"❌ 发推异常: {e}")


# # =====================================================
# # 6. 主流程（一次 = 8 小时）
# # =====================================================
# # def run_once():
# #     asyncio.run(update_database())

# #     trends = calculate_trends(top_n=3)
# #     if not trends:
# #         print("📭 本窗口无热点")
# #         return

# #     for t in trends:
# #         tweet = generate_tweet(t["summary"], t["category"])
# #         print("🐦 发送推文:\n", tweet)
# #         post_tweet(tweet)
# #         time.sleep(30)
# # =====================================================
# # 6. 主流程（一次 = 8 小时）
# # =====================================================
# def run_once():
#     # 1️⃣ 更新 Telegram 数据库
#     asyncio.run(update_database())

#     # 2️⃣ 计算热点（取前三）
#     trends = calculate_trends(top_n=3)
#     if not trends:
#         print("📭 本窗口无热点")
#         return

#     # 3️⃣ 合并前三热点
#     combined_summary = "\n\n".join([t["summary"] for t in trends])

#     # 4️⃣ 分类
#     main_category = trends[0]["category"]

#     # 5️⃣ 生成推文
#     tweet = generate_tweet(combined_summary, main_category)

#     # 6️⃣ 截断推文，确保 <=280 字
#     if len(tweet) > 280:
#         tweet = tweet[:277] + "…"

#     print("🐦 发送推文:\n", tweet)

#     # 7️⃣ 发推
#     post_tweet_direct(tweet)
# # def run_once():
# #     # 1️⃣ 更新 Telegram 数据库
# #     asyncio.run(update_database())

# #     # 2️⃣ 计算热点（取前三）
# #     trends = calculate_trends(top_n=3)
# #     if not trends:
# #         print("📭 本窗口无热点")
# #         return

# #     # 3️⃣ 内容：合并前三热点
# #     combined_summary = "\n\n".join([t["summary"] for t in trends])

# #     # 4️⃣ 分类：用 Top1 的分类（最稳）
# #     main_category = trends[0]["category"]

# #     # 5️⃣ 生成推文
# #     tweet = generate_tweet(combined_summary, main_category)
# #     print("🐦 发送推文:\n", tweet)

# #     # 6️⃣ 直接发推
# #     post_tweet_direct(tweet)


# # =====================================================
# if __name__ == "__main__":
#     run_once()
