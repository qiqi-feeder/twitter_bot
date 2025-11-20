"""
测试每日大盘复盘功能
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import logger


def test_fetch_data():
    """测试数据获取"""
    logger.info("=" * 60)
    logger.info("测试 1: 获取市场数据")
    logger.info("=" * 60)
    
    from data_sources.fetch_real_data import fetch_all_market_data
    
    data = fetch_all_market_data(save_to_file=True)
    
    if data:
        logger.info("✅ 市场数据获取成功")
        logger.info(f"数据时间戳: {data.get('timestamp')}")
        
        # 显示关键数据
        if 'price' in data:
            btc = data['price'].get('btc', {})
            eth = data['price'].get('eth', {})
            logger.info(f"BTC: ${btc.get('price')} ({btc.get('change')}%)")
            logger.info(f"ETH: ${eth.get('price')} ({eth.get('change')}%)")
        
        if 'global' in data:
            global_data = data['global']
            logger.info(f"总市值: ${global_data.get('market_cap'):,}")
            logger.info(f"BTC 占比: {global_data.get('btc_dominance')}%")
        
        if 'fear_greed' in data:
            fg = data['fear_greed']
            logger.info(f"恐惧贪婪指数: {fg.get('value')} ({fg.get('classification')})")
        
        return True
    else:
        logger.error("❌ 市场数据获取失败")
        return False


def test_generate_recap():
    """测试复盘内容生成"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 2: 生成复盘内容")
    logger.info("=" * 60)
    
    from recap.generate_summary import generate_daily_recap
    
    thread = generate_daily_recap()
    
    if thread:
        logger.info(f"✅ 复盘 Thread 生成成功，共 {len(thread)} 条推文")
        
        for i, tweet in enumerate(thread, 1):
            logger.info(f"\n--- Tweet {i}/{len(thread)} ---")
            logger.info(tweet)
            logger.info(f"长度: {len(tweet)} 字符")
        
        return True
    else:
        logger.error("❌ 复盘 Thread 生成失败")
        return False


def test_full_workflow():
    """测试完整工作流（不发布）"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 3: 完整工作流（不发布）")
    logger.info("=" * 60)
    
    # 1. 获取数据
    logger.info("步骤 1/2: 获取市场数据...")
    if not test_fetch_data():
        return False
    
    # 2. 生成内容
    logger.info("\n步骤 2/2: 生成复盘内容...")
    if not test_generate_recap():
        return False
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ 完整工作流测试成功！")
    logger.info("=" * 60)
    
    return True


def main():
    """主函数"""
    logger.info("开始测试每日大盘复盘功能...")
    
    try:
        # 测试完整工作流
        success = test_full_workflow()
        
        if success:
            logger.info("\n✅ 所有测试通过！")
            logger.info("\n提示：")
            logger.info("1. 数据已保存到 data/market.json")
            logger.info("2. 如需发布到 Twitter，请使用 API 接口: POST /recap/manual")
            logger.info("3. 或在配置文件中启用定时任务")
        else:
            logger.error("\n❌ 测试失败，请检查日志")
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

