"""
生成每日复盘内容
使用 LLM 基于真实数据生成高质量复盘 Thread
"""

import json
import os
from typing import List, Optional
from datetime import datetime
from utils.logger import logger


class RecapGenerator:
    """复盘内容生成器"""
    
    def __init__(self):
        self.template_path = 'templates/recap_template.md'
        self.market_data_path = 'data/market.json'
    
    def load_template(self) -> str:
        """加载复盘模板"""
        if not os.path.exists(self.template_path):
            raise FileNotFoundError(f"模板文件不存在: {self.template_path}")
        
        with open(self.template_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def load_market_data(self) -> dict:
        """加载市场数据"""
        if not os.path.exists(self.market_data_path):
            raise FileNotFoundError(f"市场数据文件不存在: {self.market_data_path}")
        
        with open(self.market_data_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def generate_recap_thread(self, custom_prompt: Optional[str] = None) -> List[str]:
        """
        生成复盘 Thread
        
        Args:
            custom_prompt: 自定义提示词（可选）
            
        Returns:
            推文列表（Thread）
        """
        try:
            # 加载模板和数据
            template = self.load_template()
            market_data = self.load_market_data()
            
            logger.info("开始生成每日复盘 Thread...")
            logger.info(f"市场数据时间戳: {market_data.get('timestamp')}")
            
            # 延迟导入 LLM 客户端
            try:
                from llm.llm_client import llm_client
            except ImportError as e:
                logger.error(f"导入 LLM 客户端失败: {e}")
                return []

            if not llm_client.client:
                logger.error("LLM 客户端未初始化")
                return []

            # 构造 prompt
            user_prompt = self._build_prompt(template, market_data, custom_prompt)

            # 调用 LLM 生成内容
            try:
                response = llm_client.client.chat.completions.create(
                    model=llm_client.openai_config.get('model', 'gpt-4'),
                    messages=[
                        {
                            "role": "system",
                            "content": template
                        },
                        {
                            "role": "user",
                            "content": user_prompt
                        }
                    ],
                    max_tokens=2000,
                    temperature=0.7
                )
            except Exception as e:
                logger.error(f"调用 LLM API 失败: {e}")
                return []
            
            # 提取生成的内容
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content.strip()
                
                # 将内容拆分为 Thread（按段落或特定标记）
                thread = self._split_into_thread(content)
                
                logger.info(f"复盘 Thread 生成成功，共 {len(thread)} 条推文")
                return thread
            else:
                logger.error("LLM 返回空响应")
                return []
                
        except Exception as e:
            logger.error(f"生成复盘 Thread 失败: {e}")
            return []
    
    def _build_prompt(self, template: str, market_data: dict, custom_prompt: Optional[str]) -> str:
        """构造 LLM prompt"""
        
        prompt = f"""
以下是今天的全部真实市场数据：

```json
{json.dumps(market_data, indent=2, ensure_ascii=False)}
```

请根据上述模板的结构生成每日复盘 Twitter Thread。

**重要提醒：**
1. 所有数字必须**完全使用我提供的数据**
2. 不得编造、推测或推断任何新数字
3. 不得更改 market.json 中的任何数值
4. 只进行语言加工和专业分析

请生成 5 条推文组成的 Thread，每条推文之间用 "---TWEET---" 分隔。
"""
        
        if custom_prompt:
            prompt += f"\n\n额外要求：{custom_prompt}"
        
        return prompt
    
    def _split_into_thread(self, content: str) -> List[str]:
        """将生成的内容拆分为 Thread"""
        
        # 尝试按分隔符拆分
        if '---TWEET---' in content:
            tweets = [t.strip() for t in content.split('---TWEET---') if t.strip()]
        elif '\n\n\n' in content:
            # 按三个换行符拆分
            tweets = [t.strip() for t in content.split('\n\n\n') if t.strip()]
        else:
            # 按段落拆分（两个换行符）
            tweets = [t.strip() for t in content.split('\n\n') if t.strip()]
        
        # 移除长度限制，允许发长推文 (Twitter Blue)
        processed_tweets = tweets
        
        return processed_tweets


def generate_daily_recap(custom_prompt: Optional[str] = None) -> List[str]:
    """
    生成每日复盘 Thread
    
    Args:
        custom_prompt: 自定义提示词（可选）
        
    Returns:
        推文列表（Thread）
    """
    generator = RecapGenerator()
    return generator.generate_recap_thread(custom_prompt)


if __name__ == '__main__':
    # 测试生成
    thread = generate_daily_recap()
    for i, tweet in enumerate(thread, 1):
        print(f"\n=== Tweet {i} ===")
        print(tweet)
        print(f"Length: {len(tweet)} characters")

