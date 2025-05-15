"""
知乎问题爬虫 - 核心爬虫类
"""

import asyncio
import os
import re
import time
import random
import platform
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import aiofiles

try:
    from browser_use import Agent, Browser, BrowserConfig
    from langchain_openai import ChatOpenAI
    from langchain_deepseek import ChatDeepSeek
    from dotenv import load_dotenv
    browser_use_available = True
except ImportError:
    browser_use_available = False
    print("提示: browser-use库未安装，将使用直接浏览器模式。如需使用AI代理，请安装browser-use: pip install browser-use playwright")


class ZhihuBrowserScraper:
    """知乎浏览器爬虫 - 支持两种模式:
    1. AI代理模式: 使用browser-use包通过AI控制浏览器
    2. 手动浏览器模式: 直接使用Playwright控制浏览器"""
    
    def __init__(self, api_key=None, model_name="gpt-4o", zhihu_cookie=None):
        """初始化爬虫
        Args:
            api_key: API密钥 (AI代理模式需要)，如不提供将尝试从环境变量加载
            model_name: 使用的语言模型，默认gpt-4o
            zhihu_cookie: 可选的知乎cookie用于登录状态
        """
        # 加载环境变量
        load_dotenv()
        
        # 如果未提供cookie，尝试从环境变量中获取
        if zhihu_cookie is None:
            zhihu_cookie = os.getenv("ZHIHU_COOKIE_FULL")
            if zhihu_cookie:
                print("使用环境变量中的ZHIHU_COOKIE_FULL")
            else:
                zhihu_cookie_z_c0 = os.getenv("ZHIHU_COOKIE_Z_C0")
                if zhihu_cookie_z_c0:
                    print("使用环境变量中的ZHIHU_COOKIE_Z_C0")
                    zhihu_cookie = f"z_c0={zhihu_cookie_z_c0}"
        
        self.zhihu_cookie = zhihu_cookie
        self.chrome_path = self._detect_chrome_path()
        
        # 初始化AI代理相关组件 (如果browser_use可用)
        if browser_use_available:
            # 如果未提供API密钥，尝试从环境变量中获取
            if not api_key:
                # 检查多种可能的API密钥环境变量
                if os.getenv("DEEPSEEK_API_KEY"):
                    print("使用环境变量中的DEEPSEEK_API_KEY")
                    api_key = os.getenv("DEEPSEEK_API_KEY")
                    if model_name == "gpt-4o":
                        model_name = "deepseek-chat"  # 使用默认DeepSeek模型
                elif os.getenv("OPENAI_API_KEY"):
                    print("使用环境变量中的OPENAI_API_KEY")
                    api_key = os.getenv("OPENAI_API_KEY")
                elif os.getenv("ANTHROPIC_API_KEY"):
                    print("使用环境变量中的ANTHROPIC_API_KEY")
                    api_key = os.getenv("ANTHROPIC_API_KEY")
                    if model_name == "gpt-4o":
                        model_name = "claude-3-opus"  # 使用默认Claude模型
                elif os.getenv("GOOGLE_API_KEY"):
                    print("使用环境变量中的GOOGLE_API_KEY")
                    api_key = os.getenv("GOOGLE_API_KEY")
                    if model_name == "gpt-4o":
                        model_name = "gemini-pro"  # 使用默认Gemini模型
            
            # 如果成功获取API密钥，初始化LLM
            if api_key:
                self.api_key = api_key
                try:
                    # 根据模型名称选择合适的LLM
                    if model_name.startswith(("gpt-", "text-")):
                        from langchain_openai import ChatOpenAI
                        self.llm = ChatOpenAI(model=model_name, api_key=api_key)
                    elif model_name.startswith("deepseek-"):
                        from langchain_deepseek import ChatDeepSeek
                        self.llm = ChatDeepSeek(model=model_name, api_key=api_key)
                    elif model_name.startswith("claude-"):
                        from langchain_anthropic import ChatAnthropic
                        self.llm = ChatAnthropic(model=model_name, api_key=api_key)
                    elif model_name.startswith(("gemini-", "models/gemini-")):
                        from langchain_google_genai import ChatGoogleGenerativeAI
                        self.llm = ChatGoogleGenerativeAI(model=model_name, api_key=api_key)
                    else:
                        # 默认使用可用的第一个API key
                        if os.getenv("DEEPSEEK_API_KEY"):
                            from langchain_deepseek import ChatDeepSeek
                            self.llm = ChatDeepSeek(model="deepseek-chat", api_key=api_key)
                        else:
                            from langchain_openai import ChatOpenAI
                            self.llm = ChatOpenAI(model="gpt-4o", api_key=api_key)
                    
                    print(f"AI代理模式初始化成功，使用模型: {model_name}")
                except Exception as e:
                    print(f"警告: AI代理模式初始化失败: {e}")
                    self.llm = None
            else:
                print("AI代理模式不可用: 未提供API密钥，环境变量中也未找到")
                self.api_key = None
                self.llm = None
        else:
            print("AI代理模式不可用: browser-use库未安装")
            self.api_key = None
            self.llm = None
    
    def _detect_chrome_path(self):
        """自动检测Chromium浏览器路径"""
        chrome_path = None
        
        # 检测系统类型
        system = platform.system()
        
        if system == "Darwin":  # macOS
            default_paths = [
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
                "~/Applications/Chromium.app/Contents/MacOS/Chromium"
            ]
            for path in default_paths:
                expanded_path = os.path.expanduser(path)
                if os.path.exists(expanded_path):
                    chrome_path = expanded_path
                    break
        
        elif system == "Windows":
            default_paths = [
                "C:\\Program Files\\Chromium\\Application\\chromium.exe",
                "C:\\Program Files (x86)\\Chromium\\Application\\chromium.exe"
            ]
            for path in default_paths:
                if os.path.exists(path):
                    chrome_path = path
                    break
        
        elif system == "Linux":
            # 在Linux上尝试使用which命令
            import subprocess
            try:
                chrome_path = subprocess.check_output(["which", "chromium"]).decode("utf-8").strip()
            except:
                try:
                    chrome_path = subprocess.check_output(["which", "chromium-browser"]).decode("utf-8").strip()
                except:
                    # 在常见路径中查找
                    default_paths = [
                        "/usr/bin/chromium",
                        "/usr/bin/chromium-browser"
                    ]
                    for path in default_paths:
                        if os.path.exists(path):
                            chrome_path = path
                            break
        
        if chrome_path:
            print(f"已检测到Chromium浏览器: {chrome_path}")
        else:
            print("警告: 未检测到Chromium浏览器，将使用默认浏览器设置")
        
        return chrome_path
    
    async def set_cookie_helper(self, page, cookie_string):
        """辅助函数：在页面中设置cookie
        Args:
            page: playwright页面对象
            cookie_string: cookie字符串
        """
        # 首先导航到知乎域名
        await page.goto("https://www.zhihu.com", wait_until="domcontentloaded")
        await asyncio.sleep(1)
        
        # 处理cookie字符串中可能存在的转义字符
        cookie_string = cookie_string.replace("'", "\\'").replace('"', '\\"')
        
        # 检查是否包含SESSIONID，如果没有则生成一个
        has_session_id = "SESSIONID=" in cookie_string
        session_id = ""
        if not has_session_id:
            import uuid
            session_id = str(uuid.uuid4()).replace("-", "")
            print(f"生成新的SESSIONID: {session_id[:8]}...")
        
        # 使用JavaScript在浏览器中设置cookie
        script = f"""
        (cookieStr => {{
            const cookies = '{cookie_string}'.split(';');
            for (const cookie of cookies) {{
                if (cookie.trim()) {{
                    document.cookie = cookie.trim() + ';domain=.zhihu.com;path=/;secure=true;';
                }}
            }}
            
            // 添加SESSIONID如果不存在
            {f'document.cookie = "SESSIONID={session_id};domain=.zhihu.com;path=/;secure=true;httpOnly=true";' if not has_session_id else ''}
            
            return document.cookie;
        }})()
        """
        return await page.evaluate(script)

    # 从原文件导入其他方法
    from zhihu_scraper.browser import _launch_browser_manually
    from zhihu_scraper.crawler import scrape_question 