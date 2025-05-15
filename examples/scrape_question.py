#!/usr/bin/env python
"""
知乎问题爬虫示例脚本

演示如何使用zhihu_scraper包抓取知乎问题及其回答
"""

import asyncio
import os
from dotenv import load_dotenv
from zhihu_scraper import ZhihuBrowserScraper

# 加载环境变量
load_dotenv()

async def main():
    # 从环境变量中获取API密钥和知乎Cookie
    api_key = os.getenv("OPENAI_API_KEY")  # 也可以使用DEEPSEEK_API_KEY等
    zhihu_cookie = os.getenv("ZHIHU_COOKIE_FULL")
    
    # 初始化爬虫 (可选参数)
    scraper = ZhihuBrowserScraper(
        api_key=api_key,       # API密钥，不提供则尝试从环境变量获取
        model_name="gpt-4o",   # 使用的语言模型，默认gpt-4o
        zhihu_cookie=zhihu_cookie  # 知乎Cookie
    )
    
    # 知乎问题ID (可以是完整URL或纯数字ID)
    question_id = "537377466"  # 例如: "为什么中国高铁不跨海运行？"
    
    # 设置输出目录
    output_dir = "output"
    
    # 使用手动浏览器模式 (更可靠但较慢)
    manual_mode = True
    
    # 开始抓取
    print(f"开始抓取知乎问题: {question_id}")
    try:
        result = await scraper.scrape_question(
            question_id=question_id,
            output_dir=output_dir,
            manual_mode=manual_mode
        )
        print(f"抓取完成，共获取到 {result} 个回答")
        print(f"数据已保存到 {os.path.join(output_dir, question_id)} 目录")
    except Exception as e:
        print(f"抓取过程中出错: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 