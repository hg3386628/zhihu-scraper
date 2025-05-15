"""
浏览器控制模块 - 负责浏览器的初始化和基本操作
"""

import os
import re
import random
import asyncio
import json
from playwright.async_api import async_playwright

async def _launch_browser_manually(self, question_id, output_dir='output'):
    """使用手动浏览器模式爬取知乎问题数据
    这种模式将使用Playwright直接控制浏览器，实现更精确的浏览器指纹管理
    """
    if not hasattr(self, 'llm') or self.llm is None:
        print("警告: AI代理模式不可用，直接使用手动浏览器模式")
    
    print("启动手动浏览器模式...")
    question_url = f"https://www.zhihu.com/question/{question_id}"
    output_file = os.path.join(output_dir, f"zhihu_question_{question_id}.json")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 为当前问题创建专属文件夹
    question_dir = os.path.join(output_dir, str(question_id))
    if not os.path.exists(question_dir):
        os.makedirs(question_dir)
    
    # 解析cookie为字典形式
    cookies = []
    if self.zhihu_cookie:
        cookie_parts = self.zhihu_cookie.split(';')
        for part in cookie_parts:
            if '=' in part:
                name, value = part.strip().split('=', 1)
                if name and value:
                    for domain in [".zhihu.com", "www.zhihu.com", "zhihu.com"]:
                        cookies.append({
                            "name": name,
                            "value": value,
                            "domain": domain,
                            "path": "/"
                        })
    
        # 确保至少添加z_c0和SESSIONID cookie（知乎的主要身份验证cookie）
        # 处理z_c0
        if "z_c0" in self.zhihu_cookie:
            z_c0_value = re.search(r'z_c0=([^;]+)', self.zhihu_cookie)
            if z_c0_value:
                for domain in [".zhihu.com", "www.zhihu.com", "zhihu.com"]:
                    cookies.append({
                        "name": "z_c0",
                        "value": z_c0_value.group(1),
                        "domain": domain,
                        "path": "/",
                        "secure": True,
                        "httpOnly": True
                    })
        
        # 处理SESSIONID
        if "SESSIONID" in self.zhihu_cookie:
            session_value = re.search(r'SESSIONID=([^;]+)', self.zhihu_cookie)
            if session_value:
                for domain in [".zhihu.com", "www.zhihu.com", "zhihu.com"]:
                    cookies.append({
                        "name": "SESSIONID",
                        "value": session_value.group(1),
                        "domain": domain,
                        "path": "/",
                        "secure": True,
                        "httpOnly": True
                    })
        
        # 如果cookie字符串中没有SESSIONID，但提供了z_c0，可以尝试生成一个
        if "SESSIONID" not in self.zhihu_cookie and "z_c0" in self.zhihu_cookie:
            # 生成一个随机的SESSIONID
            import uuid
            session_id = str(uuid.uuid4()).replace("-", "")
            for domain in [".zhihu.com", "www.zhihu.com", "zhihu.com"]:
                cookies.append({
                    "name": "SESSIONID",
                    "value": session_id,
                    "domain": domain,
                    "path": "/",
                    "secure": True,
                    "httpOnly": True
                })
            print(f"生成随机SESSIONID: {session_id[:8]}...")

    # 添加必要的cookie处理代码
    print(f"添加cookie数量: {len(cookies)}")
    
    # 随机化窗口大小以增加真实感
    width = 1920 + random.randint(-100, 100)
    height = 1080 + random.randint(-50, 50)
    
    # 增强的浏览器启动参数，更全面的反自动化检测
    browser_args = [
        '--disable-blink-features=AutomationControlled',
        '--disable-features=IsolateOrigins,site-per-process',
        '--disable-site-isolation-trials',
        f'--window-size={width},{height}',
        '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chromium/136.0.0.0 Safari/537.36'
    ]
    
    # 注入的反检测JS代码
    anti_detection_js = """
    // 覆盖navigator.webdriver
    Object.defineProperty(navigator, 'webdriver', {
        get: () => false,
        configurable: true
    });
    
    // 添加Chromium浏览器特有的属性
    window.chrome = {
        runtime: {},
        loadTimes: function() {},
        csi: function() {},
        app: {}
    };
    
    // 覆盖Permissions API
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
        Promise.resolve({state: Notification.permission}) :
        originalQuery(parameters)
    );
    
    // 修改WebGL指纹
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) {
            return 'Intel Inc.';
        }
        if (parameter === 37446) {
            return 'Intel Iris Pro Graphics';
        }
        return getParameter.apply(this, [parameter]);
    };
    
    // 随机化canvas指纹
    const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(type) {
        if (type === 'image/png' && this.width === 16 && this.height === 16) {
            // 这很可能是指纹采集
            const canvas = document.createElement('canvas');
            canvas.width = this.width;
            canvas.height = this.height;
            const ctx = canvas.getContext('2d');
            
            // 从原始画布复制内容
            ctx.drawImage(this, 0, 0);
            
            // 添加微小的噪点
            const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            const data = imageData.data;
            
            for (let i = 0; i < data.length; i += 4) {
                // 随机调整RGB值，但改动很小
                data[i] = data[i] + Math.floor(Math.random() * 10) - 5;     // R
                data[i+1] = data[i+1] + Math.floor(Math.random() * 10) - 5; // G
                data[i+2] = data[i+2] + Math.floor(Math.random() * 10) - 5; // B
            }
            
            ctx.putImageData(imageData, 0, 0);
            return origToDataURL.apply(canvas, arguments);
        }
        
        return origToDataURL.apply(this, arguments);
    };
    
    // 修改AudioContext指纹
    const audioContext = window.AudioContext || window.webkitAudioContext;
    if (audioContext) {
        const origGetChannelData = AudioBuffer.prototype.getChannelData;
        AudioBuffer.prototype.getChannelData = function() {
            const channelData = origGetChannelData.apply(this, arguments);
            
            // 只在可能是指纹采集的情况下修改
            if (channelData.length > 20) {
                // 添加微小噪点
                const noise = 0.0001;
                for (let i = 0; i < Math.min(channelData.length, 500); i++) {
                    channelData[i] = channelData[i] + (Math.random() * noise * 2 - noise);
                }
            }
            
            return channelData;
        };
    }
    
    // 随机化硬件并发数
    Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => 8 + Math.floor(Math.random() * 4),
        configurable: true
    });
    
    // 随机化设备内存大小
    Object.defineProperty(navigator, 'deviceMemory', {
        get: () => 8,
        configurable: true
    });
    """
    
    # 自定义浏览器启动参数，模拟真实Chromium浏览器
    async with async_playwright() as p:
        # 创建浏览器上下文，添加高级指纹特征
        browser = await p.chromium.launch(
            headless=False,  # 使用有头模式，方便排查问题
            slow_mo=100 + random.randint(0, 100),  # 随机化操作速度
            args=browser_args
        )
        
        # 创建上下文，更完整的浏览器环境配置
        context = await browser.new_context(
            viewport={"width": width, "height": height},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chromium/136.0.0.0 Safari/537.36",
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            accept_downloads=True,
            extra_http_headers={
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7,zh-CN;q=0.6",
                "cache-control": "no-cache",
                "pragma": "no-cache",
                "sec-ch-ua": '"Chromium";v="136", "Not.A/Brand";v="99"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"',
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "none",
                "sec-fetch-user": "?1",
                "upgrade-insecure-requests": "1"
            }
        )
        
        # 设置cookies
        await context.add_cookies(cookies)
        
        # 使用CDP直接设置cookie（更可靠的方法）
        if self.zhihu_cookie and len(self.zhihu_cookie) > 0:
            print("使用CDP直接设置cookie...")
            cdp_session = await context.new_cdp_session(await context.new_page())
            
            # 解析cookie字符串
            for cookie_str in self.zhihu_cookie.split(';'):
                if '=' in cookie_str:
                    name, value = cookie_str.strip().split('=', 1)
                    if name and value:
                        # 使用CDP设置cookie
                        try:
                            await cdp_session.send('Network.setCookie', {
                                'name': name,
                                'value': value,
                                'domain': '.zhihu.com',
                                'path': '/',
                                'secure': True,
                                'httpOnly': False,
                                'sameSite': 'None'
                            })
                            print(f"通过CDP设置cookie: {name}")
                        except Exception as e:
                            print(f"设置cookie {name} 失败: {str(e)}")
            
            # 关闭临时页面
            await cdp_session.detach()
        
        # 创建新页面
        page = await context.new_page()
        
        # 注入JS脚本来模拟真实浏览器环境，隐藏自动化特征
        await page.add_init_script(anti_detection_js)
        
        # 模拟人类行为函数
        async def simulate_human_behavior():
            # 随机的鼠标移动
            for i in range(3):
                x = random.randint(100, width - 200)
                y = random.randint(100, height - 200)
                await page.mouse.move(x, y, steps=25)
                await asyncio.sleep(0.5 + random.random() * 0.5)
            
            # 随机的短暂停顿
            await asyncio.sleep(1 + random.random() * 2)
        
        # 尝试模拟正常用户的浏览行为
        print(f"正在直接打开问题页面: {question_url}")
        
        # 如果有cookie，先设置cookie
        if self.zhihu_cookie:
            # 创建一个空白页用于设置cookie
            blank_page = await context.new_page()
            await blank_page.goto("about:blank")
            
            # 使用辅助函数设置cookie
            try:
                current_cookies = await self.set_cookie_helper(blank_page, self.zhihu_cookie)
                print(f"当前页面cookie: {current_cookies[:30]}...")
            except Exception as e:
                print(f"设置cookie失败: {str(e)}")
                current_cookies = ""
            
            # 尝试设置localStorage
            if "z_c0" in self.zhihu_cookie:
                z_c0_value = re.search(r'z_c0=([^;]+)', self.zhihu_cookie)
                if z_c0_value:
                    token_value = z_c0_value.group(1)
                    
                    # 生成一个随机的SESSIONID如果不存在
                    has_session_id = "SESSIONID=" in self.zhihu_cookie
                    session_script = ""
                    if not has_session_id:
                        import uuid
                        session_id = str(uuid.uuid4()).replace("-", "")
                        session_script = f'document.cookie = "SESSIONID={session_id};domain=.zhihu.com;path=/;secure=true;httpOnly=true";'
                        print(f"在localStorage设置时添加SESSIONID: {session_id[:8]}...")
                    
                    await blank_page.evaluate(f"""() => {{
                        localStorage.setItem('z_c0', '{token_value}');
                        localStorage.setItem('LOGIN_STATUS', '1');
                        
                        // 额外设置SESSIONID
                        {session_script}
                        
                        // 设置XSRF Token (如果需要)
                        const xsrfToken = Math.random().toString(36).slice(2);
                        document.cookie = `_xsrf=${{xsrfToken}};domain=.zhihu.com;path=/`;
                        localStorage.setItem('_xsrf', xsrfToken);
                    }}""")
                    print("已设置localStorage认证信息")
            
            # 关闭空白页
            await blank_page.close()
        
        # 直接访问问题页面
        await page.goto(question_url, wait_until="domcontentloaded")
        
        # 完整的页面处理操作...省略部分代码，使用从原文件导入
        
        # 关闭浏览器
        await browser.close()
        
        return len(answers) 