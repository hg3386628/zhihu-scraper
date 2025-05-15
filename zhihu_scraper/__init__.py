"""
知乎问题爬虫包

支持AI代理和手动浏览器两种模式爬取知乎问题及回答
"""

__version__ = "0.1.0"

from zhihu_scraper.scraper import ZhihuBrowserScraper

__all__ = ["ZhihuBrowserScraper"] 