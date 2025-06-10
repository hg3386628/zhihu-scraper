"""
知乎问题爬虫包

支持AI代理和手动浏览器两种模式爬取知乎问题及回答
"""

__version__ = "0.1.0"

from zhihu_scraper.scraper import ZhihuBrowserScraper

__all__ = ["ZhihuBrowserScraper"]

async def login_zhihu(timeout=300, user_data_dir=None):
    """手动登录知乎并保存登录状态
    
    为方便使用，这里提供一个包级别的登录函数
    
    Args:
        timeout: 等待登录的最大时间（秒），默认5分钟
        user_data_dir: 浏览器数据存储目录，默认为~/zhihu-browser-profile
    
    Returns:
        bool: 登录是否成功
    """
    from zhihu_scraper.cli import login_zhihu as cli_login_zhihu
    return await cli_login_zhihu(timeout=timeout, user_data_dir=user_data_dir)

if __name__ == "__main__":
    import asyncio
    asyncio.run(login_zhihu()) 