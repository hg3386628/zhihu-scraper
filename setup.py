from setuptools import setup, find_packages

setup(
    name="zhihu_scraper",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "playwright>=1.20.0",
        "asyncio",
        "aiofiles",
        "beautifulsoup4",
        "python-dotenv",
    ],
    extras_require={
        "ai": ["browser-use", "langchain-openai", "langchain-deepseek", "langchain-anthropic", "langchain-google-genai"],
    },
    entry_points={
        "console_scripts": [
            "zhihu-scraper=zhihu_scraper.cli:main",
        ],
    },
    python_requires=">=3.11",
    author="",
    description="知乎问题爬虫 - 支持AI代理和手动浏览器两种模式",
    keywords="zhihu, scraper, browser, ai",
) 