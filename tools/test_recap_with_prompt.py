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

## 市场数据 (Data Timestamp: {market_data.get('timestamp', 'N/A')})

### 价格数据
"""

    if 'price' in market_data:
        btc = market_data['price'].get('btc', {})
        eth = market_data['price'].get('eth', {})

        btc_price = btc.get('price')
        btc_change = btc.get('change')
        btc_volume = btc.get('volume')
        eth_price = eth.get('price')
        eth_change = eth.get('change')
        eth_volume = eth.get('volume')

        if btc_price is not None:
            user_prompt += f"\n- BTC 价格: ${btc_price:,.2f}"
        if btc_change is not None:
            user_prompt += f"\n- BTC 24h 涨跌: {btc_change:+.2f}%"
        if btc_volume is not None:
            user_prompt += f"\n- BTC 24h 交易量: ${btc_volume:,.0f}"

        user_prompt += "\n"

        if eth_price is not None:
            user_prompt += f"\n- ETH 价格: ${eth_price:,.2f}"
        if eth_change is not None:
            user_prompt += f"\n- ETH 24h 涨跌: {eth_change:+.2f}%"
        if eth_volume is not None:
            user_prompt += f"\n- ETH 24h 交易量: ${eth_volume:,.0f}"

    if 'global' in market_data:
        global_data = market_data['global']
        market_cap = global_data.get('market_cap')
        change = global_data.get('change')
        btc_dominance = global_data.get('btc_dominance')

        user_prompt += "\n\n### 全球市场数据"
        if market_cap is not None:
            user_prompt += f"\n- 总市值: ${market_cap:,.0f}"
        if change is not None:
            user_prompt += f"\n- 24h 市值变化: {change:+.2f}%"
        if btc_dominance is not None:
            user_prompt += f"\n- BTC 市值占比: {btc_dominance:.2f}%"

    if 'fear_greed' in market_data:
        fg = market_data['fear_greed']
        value = fg.get('value')
        classification = fg.get('classification')

        if value is not None and classification:
            user_prompt += f"\n\n### 市场情绪"
            user_prompt += f"\n- 恐惧贪婪指数: {value} ({classification})"

    if 'liquidation' in market_data:
        liq = market_data['liquidation']
        total_24h = liq.get('total_24h')
        long_24h = liq.get('long_24h')
        short_24h = liq.get('short_24h')
        long_short_ratio = liq.get('long_short_ratio')

        # 只有在有实际数据时才添加爆仓板块
        if total_24h or long_24h or short_24h or long_short_ratio:
            user_prompt += "\n\n### 爆仓数据"
            if total_24h:
                user_prompt += f"\n- 24h 总爆仓: ${total_24h:,.0f}"
            if long_24h:
                user_prompt += f"\n- 多头爆仓: ${long_24h:,.0f}"
            if short_24h:
                user_prompt += f"\n- 空头爆仓: ${short_24h:,.0f}"
            if long_short_ratio:
                user_prompt += f"\n- 多空比: {long_short_ratio}"

    if 'l2' in market_data and market_data['l2']:
        l2 = market_data['l2']
        total_tvl = l2.get('total_tvl')
        tvl_change = l2.get('tvl_change')

        if total_tvl or tvl_change:
            user_prompt += "\n\n### Layer 2 生态"
            if total_tvl:
                user_prompt += f"\n- L2 总锁仓量 (TVL): ${total_tvl:,.0f}"
            if tvl_change is not None:
                user_prompt += f"\n- 24h TVL 变化: {tvl_change:+.2f}%"

    if 'macro' in market_data:
        macro = market_data['macro']
        # 只有在有实际数据时才添加宏观板块（非 0 值）
        has_macro_data = any(
            macro.get(key) and macro.get(key) != 0
            for key in ['nasdaq', 'dxy', 'vix', 'us10y', 'gold', 'oil']
        )

        if has_macro_data:
            user_prompt += "\n\n### 宏观市场"
            if macro.get('nasdaq'):
                user_prompt += f"\n- 纳斯达克: {macro['nasdaq']:+.2f}%"
            if macro.get('dxy'):
                user_prompt += f"\n- 美元指数 (DXY): {macro['dxy']:.2f}"
            if macro.get('vix'):
                user_prompt += f"\n- VIX 恐慌指数: {macro['vix']:.2f}"
            if macro.get('us10y'):
                user_prompt += f"\n- 10年美债收益率: {macro['us10y']:.2f}%"
            if macro.get('gold'):
                user_prompt += f"\n- 黄金: {macro['gold']:+.2f}%"
            if macro.get('oil'):
                user_prompt += f"\n- 原油: {macro['oil']:+.2f}%"

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
        logger.info("提示: 如果使用代理，首次调用可能需要较长时间...")

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
            temperature=0.7,
            timeout=120.0  # 增加超时时间到 120 秒
        )

        content = response.choices[0].message.content.strip()
        logger.info("✅ LLM 生成成功")

        return content

    except Exception as e:
        logger.error(f"❌ LLM 生成失败: {e}")
        logger.error("可能的原因:")
        logger.error("1. 代理连接超时 - 请检查代理配置")
        logger.error("2. OpenAI API Key 无效 - 请检查 config.yaml")
        logger.error("3. 网络连接问题 - 请检查网络")
        import traceback
        traceback.print_exc()
        return None


def save_recap_to_file(content, market_data):
    """保存复盘内容到文件"""
    import json
    from datetime import datetime

    # 创建保存目录
    recap_dir = 'data/recaps'
    os.makedirs(recap_dir, exist_ok=True)

    # 生成文件名（使用日期）
    date_str = datetime.now().strftime('%Y-%m-%d')

    # 保存为 JSON 格式
    json_file = os.path.join(recap_dir, f'recap_{date_str}.json')
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'date': date_str,
            'timestamp': market_data.get('timestamp'),
            'content': content,
            'market_data': market_data
        }, f, ensure_ascii=False, indent=2)

    # 保存为纯文本格式（方便阅读）
    txt_file = os.path.join(recap_dir, f'recap_{date_str}.txt')
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write(f"# Web3 每日大盘复盘 - {date_str}\n\n")
        f.write(content)
        f.write(f"\n\n---\n生成时间: {market_data.get('timestamp')}\n")

    # 同时保存到 data/recap_output.json（兼容旧版）
    output_file = 'data/recap_output.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'date': date_str,
            'timestamp': market_data.get('timestamp'),
            'content': content,
            'market_data': market_data
        }, f, ensure_ascii=False, indent=2)

    return json_file, txt_file


def display_recap(content):
    """显示生成的复盘内容"""
    logger.info("\n" + "=" * 60)
    logger.info("步骤 3/3: 生成的复盘内容")
    logger.info("=" * 60)

    logger.info(f"\n内容长度: {len(content)} 字符\n")
    logger.info("=" * 60)
    logger.info(content)
    logger.info("=" * 60)


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

        # 5. 显示结果
        display_recap(content)

        # 6. 保存结果
        json_file, txt_file = save_recap_to_file(content, market_data)

        logger.info(f"\n✅ 复盘内容已保存到:")
        logger.info(f"   - JSON 格式: {json_file}")
        logger.info(f"   - 文本格式: {txt_file}")
        logger.info(f"   - 兼容格式: data/recap_output.json")
        logger.info("\n" + "=" * 60)
        logger.info("✅ 测试完成！")
        logger.info("=" * 60)
        logger.info("\n提示：")
        logger.info("1. 如需发布到 Twitter，请使用: POST /recap/manual")
        logger.info("2. 如需修改系统提示词，请编辑: prompt/system_prompt.md")
        logger.info(f"3. 查看历史复盘: data/recaps/ 目录")
        logger.info(f"4. 查看今日复盘文本: {txt_file}")
    
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

