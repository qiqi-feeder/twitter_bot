#!/usr/bin/env python3
"""
官方Gemini API测试脚本 - 文本转图像提示词 + 双模型对比
"""

import os
import json
import time
import threading
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    print("⚠️  未找到GOOGLE_API_KEY环境变量")
    exit(1)

print(f"✅ API密钥: {API_KEY[:5]}...{API_KEY[-4:]}\n")

# 路径配置
PROJECT_ROOT = Path(__file__).parent.parent
HISTORY_FILE = PROJECT_ROOT / "data" / "history.json"
OUTPUT_DIR = Path(__file__).parent / "test_output"
OUTPUT_DIR.mkdir(exist_ok=True)


def load_latest_article():
    """从history.json加载最新文章"""
    print("📖 加载最新文章...")
    
    if not HISTORY_FILE.exists():
        print(f"❌ 找不到历史文件: {HISTORY_FILE}")
        return None
    
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)
        
        if not history:
            print("❌ 历史记录为空")
            return None
        
        latest = history[0]
        content = latest.get('content', '')
       
        if not content:
            print("❌ 最新文章无内容")
            return None
        
        print(f"✅ 加载文章: {latest.get('title', 'Unknown')}")
        print(f"   内容长度: {len(content)} 字符\n")
        return content[:2000]
        
    except Exception as e:
        print(f"❌ 加载失败: {e}")
        return None


def generate_cover_prompt(article_content: str) -> dict:
    """使用gemini-3-flash-preview生成专业封面图提示词（JSON格式）"""
    print("🧠 步骤1: 生成封面图提示词 (gemini-3-flash-preview)...")
    
    system_instruction = """你是一个"新闻封面图提示词生成器"。
输入：一段当天日报（可能包含多条新闻摘要、标题、要点）。
输出：用于图像生成模型的单条英文提示词（prompt），用于生成一张 16:9 高质量黑白封面插画。
使用场景：用 gemini-3-pro-image-preview 生成封面图。
强制要求：输出必须只包含两个字段（JSON），不要包含任何解释性文字。

主题提炼与隐喻生成规则：

从日报中选择"最适合画成封面"的 1 个主题（优先：宏观趋势/科技/社会心理/经济变化/安全/注意力与信息过载；回避：血腥事故现场、未成年人、极端仇恨符号、明确政治宣传）。

把主题转成一个"象征性场景"（allegory）：用 1 个主角 + 1 个核心道具/空间 + 2–4 个外部威胁或对立元素来表现冲突。

场景必须"可读、单幅画讲清楚"，避免拼贴多新闻。

不要让模型在画面中出现可读文字；标题由后处理叠加。

风格（必须严格保持）：

Black-and-white only; high-contrast monochrome.

Intaglio etching / woodcut engraving / Victorian-era book illustration aesthetic.

Dense cross-hatching + stippling; crisp linework; no blur.

Dark humor + surreal symbolism, but not cute/cartoon.

No photorealism, no modern UI screenshots, no gradients except the title fade area.

构图与画面结构（必须严格保持）：

Aspect ratio: 16:9 horizontal cover illustration.

One clear focal point (main subject) slightly left-of-center.

Depth: foreground hint + midground action + background texture.

The entire frame should be highly detailed with dense cross-hatching and intricate linework.

约束/禁止项（必须写进 prompt）：

"NO readable text, NO letters, NO words, NO watermarks, NO logos, NO signatures, NO QR codes."

"No color. No photorealism. No modern brand marks."

Avoid depicting identifiable real persons; use generic silhouettes.

输出格式（必须严格遵守）：
只输出 JSON：

prompt: 一条英文 prompt（150–280 词），包含：主题隐喻、场景要素、构图要求、风格、留白区要求、禁止项。

negative_prompt: 一条英文 negative prompt（可短），进一步强调禁止项与避免的风格漂移。

不要输出代码块，不要输出多余字段，不要输出解释。

示例输出格式（注意：不要复用示例内容，只复用格式）：
{
"prompt": "...",
"negative_prompt": "..."
}

现在开始：基于我提供的日报文本生成封面图 prompt。"""

    try:
        client = genai.Client(api_key=API_KEY)
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=f"{system_instruction}\n\n日报文本：\n<<<\n{article_content}\n>>>"
        )
        
        result_text = response.text.strip()
        
        # 尝试解析JSON
        # 移除可能的markdown代码块标记
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()
        
        prompt_data = json.loads(result_text)
        
        print(f"✅ 提示词已生成:")
        print(f"   主提示词: {prompt_data.get('prompt', '')[:100]}...")
        print(f"   负面提示词: {prompt_data.get('negative_prompt', '')[:80]}...\n")
        
        return prompt_data
        
    except json.JSONDecodeError as e:
        print(f"⚠️  JSON解析失败: {e}")
        print(f"   原始输出: {result_text[:200]}...")
        # 返回备用提示词
        fallback = {
            "prompt": "A surreal black and white engraving showing abstract cryptocurrency market volatility. Central figure: lone trader silhouette standing before cascading data streams. Dense cross-hatching, Victorian woodcut style. 16:9 horizontal. Entire frame highly detailed. NO text, NO letters, NO logos. High contrast monochrome only.",
            "negative_prompt": "color, photorealism, text, letters, words, logos, watermarks, signatures, modern UI, cartoon, cute style"
        }
        print(f"   使用备用提示词\n")
        return fallback
        
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        fallback = {
            "prompt": "Surreal black and white financial landscape. Monochrome engraving style. 16:9 cover. Upper-right empty. NO text.",
            "negative_prompt": "color, text, photorealism"
        }
        print(f"   使用简化备用\n")
        return fallback


def generate_image_with_timeout(model_name: str, prompt: str, output_filename: str, timeout_sec: int = 180) -> bool:
    """
    带超时的图像生成（使用线程控制）
    timeout_sec: 超时时间（秒），Flash模型约60-90秒，Pro模型可能需要更长
    """
    print(f"\n🖌️  模型: {model_name}")
    print(f"   提示词: {prompt[:60]}...")
    
    result = {"success": False, "error": None, "image_bytes": None, "elapsed": 0}
    
    def _generate():
        try:
            client = genai.Client(api_key=API_KEY)
            
            contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
            config = types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
                image_config=types.ImageConfig(
                    image_size="2K",
                    # 5:2 比例配置（宽:高 = 2.5:1）
                    # 注意：API可能不直接支持自定义比例，生成后裁剪
                ),
            )
            
            start = time.time()
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )
            result["elapsed"] = time.time() - start
            
            # 提取图像数据
            image_bytes = None
            for cand in (getattr(response, "candidates", None) or []):
                content = getattr(cand, "content", None)
                if not content:
                    continue
                for part in (getattr(content, "parts", None) or []):
                    inline = getattr(part, "inline_data", None)
                    if inline:
                        data = getattr(inline, "data", None)
                        if data and not image_bytes:
                            image_bytes = data
            
            if image_bytes:
                result["image_bytes"] = image_bytes
                result["success"] = True
            else:
                result["error"] = "响应无图像数据"
                
        except Exception as e:
            result["error"] = str(e)
    
    # 在线程中运行，带超时控制
    print(f"   ⏳ 生成中 (超时: {timeout_sec}秒)...")
    thread = threading.Thread(target=_generate, daemon=True)
    thread.start()
    thread.join(timeout=timeout_sec)
    
    if thread.is_alive():
        print(f"   ⏱️  超时 ({timeout_sec}秒)")
        print(f"   💡 提示: {model_name} 可能需要更长时间或有配额限制")
        return False
    
    if result["success"] and result["image_bytes"]:
        from PIL import Image, ImageOps
        import io
        
        # 加载图像
        img = Image.open(io.BytesIO(result["image_bytes"]))
        
        # 1. 转换为黑白（灰度）
        img_bw = img.convert('L')  # 转为灰度
        
        # 2. 增强对比度，使其更接近纯黑白
        img_bw = ImageOps.autocontrast(img_bw, cutoff=2)
        
        # 3. 裁剪/调整为16:9比例（封面图标准）
        width, height = img_bw.size
        target_ratio = 16 / 9  # 1.778
        current_ratio = width / height
        
        if current_ratio > target_ratio:
            # 图像太宽，裁剪左右
            new_width = int(height * target_ratio)
            left = (width - new_width) // 2
            img_bw = img_bw.crop((left, 0, left + new_width, height))
        elif current_ratio < target_ratio:
            # 图像太高，裁剪上下
            new_height = int(width / target_ratio)
            top = (height - new_height) // 2
            img_bw = img_bw.crop((0, top, width, top + new_height))
        
        # 保存处理后的图像
        output_path = OUTPUT_DIR / output_filename
        img_bw.save(output_path, format="JPEG", quality=95)
        
        final_width, final_height = img_bw.size
        actual_ratio = final_width / final_height
        
        print(f"   ✅ 已保存: {output_path.name}")
        print(f"   ⏱️  耗时: {result['elapsed']:.1f}秒")
        print(f"   📦 大小: {len(result['image_bytes']) / 1024:.0f} KB")
        print(f"   📐 尺寸: {final_width}x{final_height} (比例 {actual_ratio:.2f}:1 ≈ 16:9)")
        print(f"   🎨 效果: 黑白对比增强")
        return True
    else:
        print(f"   ❌ 失败: {result.get('error', '未知错误')}")
        return False


def main():
    print("=" * 70)
    print("🚀 官方Gemini API测试 - 文本生成 + 图像模型对比")
    print("=" * 70)
    print()
    
    # 1. 加载文章
    article = load_latest_article()
    if not article:
        print("❌ 无法继续，缺少文章内容")
        return
    
    # 2. 生成专业封面提示词
    prompt_data = generate_cover_prompt(article)
    
    main_prompt = prompt_data.get("prompt", "")
    negative_prompt = prompt_data.get("negative_prompt", "")
    
    if not main_prompt:
        print("❌ 无法生成有效提示词")
        return
    
    # 保存完整提示词到文件
    prompt_file = OUTPUT_DIR / "full_prompt.txt"
    with open(prompt_file, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("完整封面图提示词\n")
        f.write("=" * 70 + "\n\n")
        f.write("【主提示词 (Prompt)】\n")
        f.write(main_prompt + "\n\n")
        f.write("【负面提示词 (Negative Prompt)】\n")
        f.write(negative_prompt + "\n\n")
        f.write("=" * 70 + "\n")
        f.write("提示词结构说明：\n")
        f.write("- 16:9 横版封面插画\n")
        f.write("- 黑白木刻/蚀刻风格\n")
        f.write("- 全画幅高细节，密集交叉线影\n")
        f.write("- 禁止文字、logo、水印\n")
        f.write("=" * 70 + "\n")
    
    print("📝 完整提示词:")
    print("=" * 70)
    print(f"【主提示词】\n{main_prompt}\n")
    print(f"【负面提示词】\n{negative_prompt}")
    print("=" * 70)
    print(f"   已保存至: {prompt_file}\n")
    
    # 3. 双模型对比生成
    print("=" * 70)
    print("🎨 图像模型对比测试")
    print("=" * 70)
    
    # Flash模型：快速
    # Pro模型：质量更高但慢
    models = {
        "gemini-2.0-flash-exp-image-generation": {
            "filename": "flash_cover.jpg",
            "timeout": 120  # 2分钟
        },
        "gemini-3-pro-image-preview": {
            "filename": "pro_cover.jpg",
            "timeout": 240  # 4分钟
        }
    }
    
    results = {}
    for model_name, config in models.items():
        # 使用主提示词生成图像
        success = generate_image_with_timeout(
            model_name, 
            main_prompt,  # 使用JSON中的prompt
            config["filename"],
            config["timeout"]
        )
        results[model_name] = success
        time.sleep(2)  # 请求间隔
    
    # 5. 总结
    print("\n" + "=" * 70)
    print("📊 测试总结")
    print("=" * 70)
    print(f"\n✅ 文本模型: gemini-3-flash-preview")
    print(f"   成功生成视觉概念")
    
    print(f"\n🖼️  图像模型对比:")
    for model, success in results.items():
        status = "✅ 成功" if success else "❌ 失败/超时"
        short_name = model.split("-")[1] + "-" + model.split("-")[2] if "-" in model else model
        print(f"   {short_name:20s}: {status}")
    
    print(f"\n📁 输出目录: {OUTPUT_DIR}")
    
    success_count = sum(1 for s in results.values() if s)
    if success_count == len(results):
        print("\n🎉 所有测试通过！")
    elif success_count > 0:
        print(f"\n⚠️  部分成功 ({success_count}/{len(results)})")
    else:
        print("\n❌ 所有模型均失败")


if __name__ == "__main__":
    main()
