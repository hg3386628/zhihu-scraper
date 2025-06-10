"""
命令行接口 - 提供命令行工具入口
"""

import os
import asyncio
import argparse
from zhihu_scraper import ZhihuBrowserScraper

def scrape_command(args):
    """爬取问题的子命令"""
    # 初始化爬虫
    scraper = ZhihuBrowserScraper(
        api_key=args.api_key,
        model_name=args.model,
        zhihu_cookie=args.cookie,
        user_data_dir=args.user_data_dir
    )
    
    # 运行爬虫
    asyncio.run(scraper.scrape_question(args.question_id, args.output, args.manual))

async def login_zhihu(timeout=300, user_data_dir=None):
    """手动登录知乎并保存登录状态
    
    Args:
        timeout: 等待登录的最大时间（秒），默认5分钟
        user_data_dir: 浏览器数据存储目录，默认为~/zhihu-browser-profile
    
    Returns:
        bool: 登录是否成功
    """
    
    print("=" * 60)
    print("启动知乎手动登录流程...")
    print("=" * 60)
    print("本程序将打开浏览器窗口，请在其中完成以下操作：")
    print("1. 登录知乎账号（支持账号密码、验证码、扫码等多种方式）")
    print("2. 登录成功后，系统会自动检测并保存登录状态")
    print("3. 登录成功后，可直接关闭浏览器")
    print("=" * 60)
    
    if user_data_dir is None:
        user_data_dir = os.path.expanduser("~/zhihu-browser-profile")
    
    # 创建爬虫实例，不提供任何cookie
    scraper = ZhihuBrowserScraper(zhihu_cookie=None, user_data_dir=user_data_dir)
    
    # 执行手动登录
    login_success = await scraper.manual_login(timeout=timeout)
    
    if login_success:
        print("=" * 60)
        print("登录成功！登录状态已保存到持久化目录")
        print(f"持久化目录: {scraper.user_data_dir}")
        print("下次运行知乎爬虫时将自动使用保存的登录状态")
        print("=" * 60)
    else:
        print("=" * 60)
        print("登录失败或超时，请重试")
        print("=" * 60)
    
    return login_success

def login_command(args):
    """登录知乎的子命令"""
    asyncio.run(login_zhihu(timeout=args.timeout, user_data_dir=args.user_data_dir))

def main():
    """主函数：解析命令行参数并启动相应功能"""
    parser = argparse.ArgumentParser(description='知乎爬虫工具 - 支持登录和爬取问答')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 爬取问题的子命令
    scrape_parser = subparsers.add_parser('scrape', help='爬取知乎问题及回答')
    scrape_parser.add_argument('question_id', type=str, help='知乎问题ID（例如：https://www.zhihu.com/question/12345中的12345）')
    scrape_parser.add_argument('--output', type=str, default='output', help='输出目录，默认为output')
    scrape_parser.add_argument('--api-key', type=str, help='API密钥（用于AI代理模式，如不提供将尝试从环境变量加载）')
    scrape_parser.add_argument('--model', type=str, default='auto', help='AI模型名称，默认为auto（自动选择，会根据可用的API密钥选择模型）')
    scrape_parser.add_argument('--cookie', type=str, help='知乎Cookie（可选，用于获取登录后才能看到的内容）')
    scrape_parser.add_argument('--manual', action='store_true', help='使用手动浏览器模式（更可靠但较慢）')
    scrape_parser.add_argument('--user-data-dir', type=str, default=None, help='浏览器数据存储目录，默认为~/zhihu-browser-profile')
    scrape_parser.set_defaults(func=scrape_command)
    
    # 登录的子命令
    login_parser = subparsers.add_parser('login', help='手动登录知乎并保存登录状态')
    login_parser.add_argument('--timeout', type=int, default=300, help='等待登录的最大时间（秒），默认5分钟')
    login_parser.add_argument('--user-data-dir', type=str, default=None, help='浏览器数据存储目录，默认为~/zhihu-browser-profile')
    login_parser.set_defaults(func=login_command)
    
    args = parser.parse_args()
    
    # 处理默认命令（兼容旧版本）
    if args.command is None:
        # 旧版本兼容：无子命令时默认为爬取问题
        if hasattr(args, 'question_id'):
            scrape_command(args)
        else:
            parser.print_help()
    else:
        args.func(args)

if __name__ == "__main__":
    main() 