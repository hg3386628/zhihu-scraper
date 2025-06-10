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
    1. AI代理模式: 使用browser-use包通过AI控制浏览器，支持手动登录并保存状态
    2. 手动浏览器模式: 直接使用Playwright控制浏览器"""
    
    def __init__(self, api_key=None, model_name="gpt-4o", zhihu_cookie=None, user_data_dir=None):
        """初始化爬虫
        Args:
            api_key: API密钥 (AI代理模式需要)，如不提供将尝试从环境变量加载
            model_name: 使用的语言模型，默认gpt-4o
            zhihu_cookie: 可选的知乎cookie用于登录状态
            user_data_dir: 浏览器数据存储目录，用于保存登录状态，默认为~/zhihu-browser-profile
        """
        # 加载环境变量
        load_dotenv()
        
        # 设置浏览器持久化目录（固定使用zhihu-browser-profile）
        self.user_data_dir = os.path.expanduser("~/zhihu-browser-profile")
        os.makedirs(self.user_data_dir, exist_ok=True)
        print(f"使用浏览器持久化目录: {self.user_data_dir}")
        
        # 初始化浏览器实例为None，将在需要时创建
        self.browser = None
        
        self.zhihu_cookie = zhihu_cookie
        self.chrome_path = self._detect_chrome_path()
        
        # 初始化AI代理相关组件 (如果browser_use可用)
        if browser_use_available:
            # 如果未提供API密钥，尝试从环境变量中获取
            if not api_key:
                # API密钥和模型选择的映射关系
                api_key_map = {
                    "DEEPSEEK_API_KEY": {"default_model": "deepseek-chat"},
                    "OPENAI_API_KEY": {"default_model": "gpt-4o"},
                    "ANTHROPIC_API_KEY": {"default_model": "claude-3-opus"},
                    "GOOGLE_API_KEY": {"default_model": "gemini-pro"}
                }
                
                # 检查环境变量中的API密钥
                for env_key, config in api_key_map.items():
                    if os.getenv(env_key):
                        print(f"使用环境变量中的{env_key}")
                        api_key = os.getenv(env_key)
                        # 如果使用默认模型名称，则替换为对应服务的默认模型
                        if model_name == "gpt-4o" and env_key != "OPENAI_API_KEY":
                            model_name = config["default_model"]
                        break
            
            # 如果成功获取API密钥，初始化LLM
            if api_key:
                self.api_key = api_key
                # 模型前缀与对应LLM类的映射
                model_map = {
                    ("gpt-", "text-"): {"import": "from langchain_openai import ChatOpenAI", "class": "ChatOpenAI"},
                    ("deepseek-",): {"import": "from langchain_deepseek import ChatDeepSeek", "class": "ChatDeepSeek"},
                    ("claude-",): {"import": "from langchain_anthropic import ChatAnthropic", "class": "ChatAnthropic"},
                    ("gemini-", "models/gemini-"): {"import": "from langchain_google_genai import ChatGoogleGenerativeAI", "class": "ChatGoogleGenerativeAI"}
                }
                
                try:
                    # 根据模型名称选择合适的LLM
                    llm_config = None
                    
                    # 检查模型名称前缀
                    for prefixes, config in model_map.items():
                        if any(model_name.startswith(prefix) for prefix in prefixes):
                            llm_config = config
                            break
                    
                    # 如果没有匹配的前缀，使用默认LLM
                    if llm_config is None:
                        # 默认使用可用的第一个API key对应的默认模型
                        if os.getenv("DEEPSEEK_API_KEY"):
                            llm_config = model_map[("deepseek-",)]
                            model_name = "deepseek-chat"
                        else:
                            llm_config = model_map[("gpt-", "text-")]
                            model_name = "gpt-4o"
                    
                    # 执行导入
                    exec(llm_config["import"])
                    
                    # 创建LLM实例
                    self.llm = eval(f"{llm_config['class']}(model=model_name, api_key=api_key)")
                    
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
    
    async def manual_login(self, timeout=300):
        """打开浏览器并等待用户手动登录知乎
        Args:
            timeout: 等待登录的最大时间（秒），默认5分钟
        
        Returns:
            bool: 登录是否成功
        """
        print("启动浏览器，请在打开的窗口中手动登录知乎...")
        
        # 随机化窗口大小
        width = 1920 + random.randint(-100, 100)
        height = 1080 + random.randint(-50, 50)
        
        # 创建增强的浏览器启动参数
        browser_args = [
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-site-isolation-trials",
            f"--window-size={width},{height}"
        ]
        
        async with async_playwright() as p:
            # 使用持久化目录启动浏览器
            browser = await p.chromium.launch_persistent_context(
                self.user_data_dir,
                headless=False,
                slow_mo=50,
                args=browser_args,
                viewport={"width": width, "height": height},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
                locale="zh-CN",
                timezone_id="Asia/Shanghai"
            )
            
            # 创建页面
            page = await browser.new_page()
            
            # 访问知乎登录页
            await page.goto("https://www.zhihu.com/signin", wait_until="domcontentloaded")
            print("已打开知乎登录页，请手动登录...")
            
            # 等待用户登录
            try:
                # 等待直到URL变为知乎主页或包含feed的页面，表示登录成功
                await page.wait_for_url(lambda url: 
                    ("www.zhihu.com/" in url and "/signin" not in url) or 
                    "www.zhihu.com/feed" in url or
                    "www.zhihu.com/search" in url,
                    timeout=timeout * 1000
                )
                
                # 等待几秒，确保cookie已保存
                await asyncio.sleep(5)
                
                print("登录成功! 登录状态已保存到持久化目录")
                
                # 获取当前的cookies
                cookies = await browser.cookies()
                has_z_c0 = any(cookie["name"] == "z_c0" for cookie in cookies)
                
                if has_z_c0:
                    print("成功获取身份验证Cookie(z_c0)")
                else:
                    print("警告：未找到身份验证Cookie(z_c0)，可能登录未完成")
                    
                # 关闭浏览器
                await browser.close()
                return has_z_c0
            
            except Exception as e:
                print(f"等待登录超时或发生错误: {str(e)}")
                await browser.close()
                return False

    # 从原文件导入其他方法
    from zhihu_scraper.browser import _launch_browser_manually
    from zhihu_scraper.crawler import scrape_question
    
    # 导入_convert_to_markdown方法
    from zhihu_scraper.crawler import _convert_to_markdown
    
    async def close_browser(self):
        """关闭浏览器实例，释放资源"""
        # 由于已改为使用Playwright持久化上下文，该方法不再需要特别操作
        print("使用持久化浏览器上下文模式，不需要手动关闭浏览器")
        # 如果需要清理资源，可以在这里添加相关代码
        pass 