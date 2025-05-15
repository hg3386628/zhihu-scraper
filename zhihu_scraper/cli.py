"""
命令行接口 - 提供命令行工具入口
"""

import asyncio
import argparse
from zhihu_scraper import ZhihuBrowserScraper

def main():
    """主函数：解析命令行参数并启动爬虫"""
    parser = argparse.ArgumentParser(description='知乎问题爬虫 - 支持AI代理和手动浏览器两种模式')
    parser.add_argument('question_id', type=str, help='知乎问题ID（例如：https://www.zhihu.com/question/12345中的12345）')
    parser.add_argument('--output', type=str, default='output', help='输出目录，默认为output')
    parser.add_argument('--api-key', type=str, help='API密钥（用于AI代理模式，如不提供将尝试从环境变量加载）')
    parser.add_argument('--model', type=str, default='auto', help='AI模型名称，默认为auto（自动选择，会根据可用的API密钥选择模型）')
    parser.add_argument('--cookie', type=str, help='知乎Cookie（可选，用于获取登录后才能看到的内容）')
    parser.add_argument('--manual', action='store_true', help='使用手动浏览器模式（更可靠但较慢）')
    
    args = parser.parse_args()
    
    # 初始化爬虫
    scraper = ZhihuBrowserScraper(
        api_key=args.api_key,
        model_name=args.model,
        zhihu_cookie=args.cookie
    )
    
    # 运行爬虫
    asyncio.run(scraper.scrape_question(args.question_id, args.output, args.manual))

if __name__ == "__main__":
    main() 