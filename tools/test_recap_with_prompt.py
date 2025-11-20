"""
测试大盘复盘功能 - 使用 prompt 文件夹下的系统提示词
完整流程：获取数据 → 使用系统提示词生成复盘 → 显示结果
"""

import sys
import os
import json

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import logger


def load_system_prompt():
    """加载系统提示词"""
    prompt_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'prompt',
        'system_prompt.md'
    )
    
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        logger.info(f"✅ 系统提示词加载成功: {prompt_path}")
        return content
    except Exception as e:
        logger.error(f"❌ 加载系统提示词失败: {e}")
        return None


def fetch_market_data():
    """获取市场数据"""
    logger.info("=" * 60)
    logger.info("步骤 1/3: 获取市场数据")
    logger.info("=" * 60)
    
    from data_sources.fetch_real_data import fetch_all_market_data
    
    data = fetch_all_market_data(save_to_file=True)
    
    if data:
        logger.info("✅ 市场数据获取成功")
        
        # 显示关键数据
        if 'price' in data:
            btc = data['price'].get('btc', {})
            eth = data['price'].get('eth', {})
            logger.info(f"  BTC: ${btc.get('price')} ({btc.get('change'):+.2f}%)")
            logger.info(f"  ETH: ${eth.get('price')} ({eth.get('change'):+.2f}%)")
        
        if 'global' in data:
            global_data = data['global']
            logger.info(f"  总市值: ${global_data.get('market_cap'):,.0f}")
            logger.info(f"  BTC 占比: {global_data.get('btc_dominance'):.2f}%")
        
        if 'fear_greed' in data:
            fg = data['fear_greed']
            logger.info(f"  恐惧贪婪指数: {fg.get('value')} ({fg.get('classification')})")
        
        return data
    else:
        logger.error("❌ 市场数据获取失败")
        return None


def build_user_prompt(market_data):
    """构建用户提示词（将市场数据作为用户输入）"""
    
    # 格式化市场数据为易读的文本
    user_prompt = f"""请根据以下市场数据生成今日 Web3 大盘复盘 Twitter Thread：

## 市场数据 (Data Timestamp: {market_data.get('timestamp')})

### 价格数据
"""
    
    if 'price' in market_data:
        btc = market_data['price'].get('btc', {})
        eth = market_data['price'].get('eth', {})
        user_prompt += f"""
- BTC 价格: ${btc.get('price')}
- BTC 24h 涨跌: {btc.get('change'):+.2f}%
- BTC 24h 交易量: ${btc.get('volume'):,.0f}

- ETH 价格: ${eth.get('price')}
- ETH 24h 涨跌: {eth.get('change'):+.2f}%
- ETH 24h 交易量: ${eth.get('volume'):,.0f}
"""
    
    if 'global' in market_data:
        global_data = market_data['global']
        user_prompt += f"""
### 全球市场数据
- 总市值: ${global_data.get('market_cap'):,.0f}
- 24h 市值变化: {global_data.get('change'):+.2f}%
- BTC 市值占比: {global_data.get('btc_dominance'):.2f}%
"""
    
    if 'fear_greed' in market_data:
        fg = market_data['fear_greed']
        user_prompt += f"""
### 市场情绪
- 恐惧贪婪指数: {fg.get('value')} ({fg.get('classification')})
"""
    
    if 'liquidation' in market_data:
        liq = market_data['liquidation']
        user_prompt += f"""
### 爆仓数据
- 24h 总爆仓: ${liq.get('total_24h'):,.0f}
- 多头爆仓: ${liq.get('long_24h'):,.0f}
- 空头爆仓: ${liq.get('short_24h'):,.0f}
"""
    
    if 'l2' in market_data:
        l2 = market_data['l2']
        user_prompt += f"""
### Layer 2 生态
- L2 总锁仓量 (TVL): ${l2.get('total_tvl'):,.0f}
- 24h TVL 变化: {l2.get('tvl_change'):+.2f}%
"""
    
    user_prompt += """

请生成一个包含 4-5 条推文的 Twitter Thread，每条推文不超过 280 字符。
"""
    
    return user_prompt


def generate_recap_with_llm(system_prompt, user_prompt):
    """使用 LLM 生成复盘内容"""
    logger.info("\n" + "=" * 60)
    logger.info("步骤 2/3: 使用 LLM 生成复盘内容")
    logger.info("=" * 60)
    
    try:
        from llm.llm_client import llm_client
        
        if not llm_client.client:
            logger.error("❌ LLM 客户端未初始化")
            return None
        
        logger.info("调用 LLM API...")
        logger.info(f"模型: {llm_client.openai_config.get('model', 'gpt-4')}")
        
        response = llm_client.client.chat.completions.create(
            model=llm_client.openai_config.get('model', 'gpt-4'),
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            max_tokens=2000,
            temperature=0.7
        )
        
        content = response.choices[0].message.content.strip()
        logger.info("✅ LLM 生成成功")
        
        return content
    
    except Exception as e:
        logger.error(f"❌ LLM 生成失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def split_into_thread(content):
    """将生成的内容拆分为 Twitter Thread"""
    # 按空行或特定标记拆分
    tweets = []
    
    # 尝试按 "---" 或空行拆分
    parts = content.split('\n---\n')
    if len(parts) == 1:
        parts = content.split('\n\n')
    
    for part in parts:
        part = part.strip()
        if part and len(part) > 10:  # 忽略太短的片段
            # 如果单条推文超过 280 字符，需要进一步拆分
            if len(part) <= 280:
                tweets.append(part)
            else:
                # 简单拆分：按句子
                sentences = part.split('. ')
                current_tweet = ""
                for sentence in sentences:
                    if len(current_tweet) + len(sentence) + 2 <= 280:
                        current_tweet += sentence + ". "
                    else:
                        if current_tweet:
                            tweets.append(current_tweet.strip())
                        current_tweet = sentence + ". "
                if current_tweet:
                    tweets.append(current_tweet.strip())
    
    return tweets


def display_thread(thread):
    """显示生成的 Thread"""
    logger.info("\n" + "=" * 60)
    logger.info("步骤 3/3: 生成的复盘 Thread")
    logger.info("=" * 60)
    
    logger.info(f"\n共生成 {len(thread)} 条推文:\n")
    
    for i, tweet in enumerate(thread, 1):
        logger.info(f"{'='*60}")
        logger.info(f"Tweet {i}/{len(thread)} (长度: {len(tweet)} 字符)")
        logger.info(f"{'='*60}")
        logger.info(tweet)
        logger.info("")


def main():
    """主函数"""
    logger.info("🚀 开始测试大盘复盘功能（使用 prompt 文件夹）\n")
    
    try:
        # 1. 加载系统提示词
        system_prompt = load_system_prompt()
        if not system_prompt:
            logger.error("无法加载系统提示词，退出")
            sys.exit(1)
        
        # 2. 获取市场数据
        market_data = fetch_market_data()
        if not market_data:
            logger.error("无法获取市场数据，退出")
            sys.exit(1)
        
        # 3. 构建用户提示词
        user_prompt = build_user_prompt(market_data)
        
        # 4. 使用 LLM 生成复盘
        content = generate_recap_with_llm(system_prompt, user_prompt)
        if not content:
            logger.error("无法生成复盘内容，退出")
            sys.exit(1)
        
        # 5. 拆分为 Thread
        thread = split_into_thread(content)
        
        # 6. 显示结果
        display_thread(thread)
        
        # 7. 保存结果
        output_file = 'data/recap_output.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': market_data.get('timestamp'),
                'thread': thread,
                'market_data': market_data
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n✅ 复盘内容已保存到: {output_file}")
        logger.info("\n" + "=" * 60)
        logger.info("✅ 测试完成！")
        logger.info("=" * 60)
        logger.info("\n提示：")
        logger.info("1. 如需发布到 Twitter，请使用: POST /recap/manual")
        logger.info("2. 如需修改系统提示词，请编辑: prompt/system_prompt.md")
        logger.info("3. 生成的内容已保存到: data/recap_output.json")
    
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

