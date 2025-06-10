"""
浏览器控制模块 - 负责浏览器的初始化和基本操作
"""

import os
import re
import random
import asyncio
import json
import time
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
    width = 1920 + random.randint(-150, 150)
    height = 1080 + random.randint(-80, 80)
    
    # 随机化语言和UA，避免固定特征
    languages = ["zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7", 
                "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7,zh-CN;q=0.6", 
                "zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7,en-US;q=0.6"]
    
    user_agents = [
        f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{110+random.randint(0,8)}.0.0.0 Safari/537.36",
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{110+random.randint(0,8)}.0.0.0 Safari/537.36",
        f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.{random.randint(0,5)} Safari/605.1.15"
    ]
    
    selected_ua = random.choice(user_agents)
    selected_lang = random.choice(languages)
    
    # 增强的浏览器启动参数，移除明显的自动化特征
    browser_args = [
        # 禁用自动化检测
        '--disable-blink-features=AutomationControlled',
        # 禁用站点隔离（可能会暴露自动化特征）
        '--disable-features=IsolateOrigins',
        # 窗口大小
        f'--window-size={width},{height}',
        # 禁用默认浏览器检查
        '--no-default-browser-check',
        # 禁用首次运行体验
        '--no-first-run',
        # 随机化字体渲染
        f'--font-render-hinting={random.choice(["none", "medium", "full"])}',
        # 禁用用户代理客户端提示
        '--disable-features=UserAgentClientHint',
        # 添加一些随机参数增加随机性
        f'--renderer-process-limit={4+random.randint(1,4)}'
    ]
    
    # 增强版的反检测JS代码，对抗知乎的自动化检测
    anti_detection_js = """
    // 覆盖navigator.webdriver
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
        configurable: true
    });
    
    // 添加更完整的Chromium浏览器特有属性
    window.chrome = {
        runtime: {
            connect: function() {},
            sendMessage: function() {},
            onMessage: {
                addListener: function() {},
                removeListener: function() {}
            }
        },
        loadTimes: function() { 
            return {
                firstPaintTime: Date.now() - Math.floor(Math.random() * 2000),
                requestTime: Date.now() - Math.floor(Math.random() * 3000)
            }; 
        },
        csi: function() { 
            return {
                startE: Date.now() - Math.floor(Math.random() * 1000),
                onloadT: Date.now() - Math.floor(Math.random() * 3000)
            }; 
        },
        app: {
            isInstalled: false,
            getDetails: function() {},
            getIsInstalled: function() { return false; }
        }
    };
    
    // 覆盖Permissions API
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
        Promise.resolve({state: Notification.permission}) :
        parameters.name === 'clipboard-read' ?
        Promise.resolve({state: 'prompt'}) :
        parameters.name === 'clipboard-write' ?
        Promise.resolve({state: 'granted'}) :
        originalQuery(parameters)
    );
    
    // 增强版WebGL指纹随机化
    const getParameterBackup = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) {
            return 'Intel Inc.';
        }
        if (parameter === 37446) {
            return 'Intel Iris Pro Graphics';
        }
        if (parameter === 35661) {
            return Math.floor(Math.random() * 10) + 20; // 随机化 MAX_VERTEX_TEXTURE_IMAGE_UNITS
        }
        if (parameter === 34076) {
            return Math.floor(Math.random() * 5) + 10; // 随机化 MAX_COMBINED_TEXTURE_IMAGE_UNITS
        }
        return getParameterBackup.apply(this, [parameter]);
    };
    
    // 增强版canvas指纹随机化
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
                data[i] = data[i] + Math.floor(Math.random() * 6) - 3;     // R
                data[i+1] = data[i+1] + Math.floor(Math.random() * 6) - 3; // G
                data[i+2] = data[i+2] + Math.floor(Math.random() * 6) - 3; // B
            }
            
            ctx.putImageData(imageData, 0, 0);
            return origToDataURL.apply(canvas, arguments);
        }
        
        return origToDataURL.apply(this, arguments);
    };
    
    // 增强版AudioContext指纹随机化
    const audioContext = window.AudioContext || window.webkitAudioContext;
    if (audioContext) {
        const origGetChannelData = AudioBuffer.prototype.getChannelData;
        AudioBuffer.prototype.getChannelData = function() {
            const channelData = origGetChannelData.apply(this, arguments);
            
            // 只在可能是指纹采集的情况下修改
            if (channelData.length > 20) {
                // 添加微小噪点
                const noise = 0.0001;
                const originalData = new Float32Array(channelData);
                for (let i = 0; i < Math.min(channelData.length, 500); i++) {
                    channelData[i] = originalData[i] + (Math.random() * noise * 2 - noise);
                }
            }
            
            return channelData;
        };
    }
    
    // 随机化硬件并发数
    Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => Math.min(8 + Math.floor(Math.random() * 4), 16),
        configurable: true
    });
    
    // 随机化设备内存大小
    Object.defineProperty(navigator, 'deviceMemory', {
        get: () => Math.min(8 + Math.floor(Math.random() * 8), 16),
        configurable: true
    });
    
    // 模拟电池API以增加真实性
    if (navigator.getBattery) {
        navigator.getBattery = function() {
            return Promise.resolve({
                charging: Math.random() > 0.3,
                chargingTime: Math.floor(Math.random() * 3000),
                dischargingTime: Math.floor(Math.random() * 10000),
                level: Math.random() * 0.7 + 0.3,
                onchargingchange: null,
                onchargingtimechange: null,
                ondischargingtimechange: null,
                onlevelchange: null
            });
        };
    }
    
    // 随机化外接设备
    if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
        const originalEnumerateDevices = navigator.mediaDevices.enumerateDevices;
        navigator.mediaDevices.enumerateDevices = function() {
            return originalEnumerateDevices.apply(this, arguments)
                .then(devices => {
                    if (devices.length > 0) {
                        return devices;
                    } else {
                        // 如果没有设备，模拟一些常见设备
                        return [
                            { deviceId: 'default', kind: 'audioinput', label: 'Default Audio Device', groupId: 'default' },
                            { deviceId: 'default', kind: 'audiooutput', label: 'Default Audio Device', groupId: 'default' }
                        ];
                    }
                });
        };
    }
    
    // 植入一些随机历史记录以模拟正常用户
    if (window.history && window.history.length < 3) {
        Object.defineProperty(window.history, 'length', {
            get: () => 2 + Math.floor(Math.random() * 5)
        });
    }
    
    // 混淆屏幕/窗口大小
    Object.defineProperty(screen, 'availWidth', { get: () => window.innerWidth });
    Object.defineProperty(screen, 'availHeight', { get: () => window.innerHeight });
    """
    
    # 检查是否存在持久化用户目录
    user_data_dir = getattr(self, 'user_data_dir', None)
    if user_data_dir and os.path.exists(user_data_dir):
        print(f"使用持久化浏览器配置目录: {user_data_dir}")
        use_persistent_context = True
    else:
        print("未找到持久化配置目录，使用临时浏览器上下文")
        use_persistent_context = False
    
    # 自定义浏览器启动参数，模拟真实Chromium浏览器
    async with async_playwright() as p:
        try:
            answers = []
            
            # 使用持久化上下文模式
            if use_persistent_context:
                print("使用持久化浏览器上下文模式...")
                # 直接使用持久化上下文启动，保留所有cookie和存储
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    headless=False,
                    slow_mo=50 + random.randint(0, 100),
                    args=browser_args,
                    viewport={"width": width, "height": height},
                    user_agent=selected_ua,
                    locale="zh-CN",
                    timezone_id="Asia/Shanghai",
                    accept_downloads=True,
                    extra_http_headers={
                        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                        "accept-encoding": "gzip, deflate, br, zstd",
                        "accept-language": selected_lang,
                        "cache-control": "max-age=" + str(random.randint(0, 300)),
                        "sec-ch-ua": '"Chromium";v="' + str(110 + random.randint(0, 10)) + '", "Not.A/Brand";v="' + str(8 + random.randint(0, 10)) + '"',
                        "sec-ch-ua-mobile": "?0",
                        "sec-ch-ua-platform": '"macOS"',
                        "sec-fetch-dest": "document",
                        "sec-fetch-mode": "navigate",
                        "sec-fetch-site": "none",
                        "sec-fetch-user": "?1",
                        "upgrade-insecure-requests": "1"
                    }
                )
                browser = None  # 持久化上下文模式中不需要独立browser对象
                
            else:
                # 非持久化模式，标准浏览器启动
                print("使用非持久化浏览器模式...")
                browser = await p.chromium.launch(
                    headless=False,
                    slow_mo=100 + random.randint(0, 150),
                    args=browser_args
                )
                
                # 创建上下文，更完整的浏览器环境配置
                context = await browser.new_context(
                    viewport={"width": width, "height": height},
                    user_agent=selected_ua,
                    locale="zh-CN",
                    timezone_id="Asia/Shanghai",
                    accept_downloads=True,
                    extra_http_headers={
                        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                        "accept-encoding": "gzip, deflate, br, zstd",
                        "accept-language": selected_lang,
                        "cache-control": "max-age=" + str(random.randint(0, 300)),
                        "sec-ch-ua": '"Chromium";v="' + str(110 + random.randint(0, 10)) + '", "Not.A/Brand";v="' + str(8 + random.randint(0, 10)) + '"',
                        "sec-ch-ua-mobile": "?0",
                        "sec-ch-ua-platform": '"macOS"',
                        "sec-fetch-dest": "document",
                        "sec-fetch-mode": "navigate",
                        "sec-fetch-site": "none",
                        "sec-fetch-user": "?1",
                        "upgrade-insecure-requests": "1"
                    }
                )
                
                # 设置cookies (仅在非持久化模式时)
                if len(cookies) > 0:
                    await context.add_cookies(cookies)
                    print("非持久化模式：应用临时cookie")
            
            # 创建新页面
            page = await context.new_page()
            
            # 注入JS脚本来模拟真实浏览器环境，隐藏自动化特征
            await page.add_init_script(anti_detection_js)
            
            # 模拟人类行为函数 - 增强版
            async def simulate_human_behavior(page):
                # 随机的鼠标移动
                for i in range(random.randint(3, 7)):
                    x = random.randint(100, width - 200)
                    y = random.randint(100, height - 200)
                    # 增加移动步数和随机性
                    await page.mouse.move(x, y, steps=25 + random.randint(0, 20))
                    await asyncio.sleep(0.3 + random.random() * 0.7)
                
                # 随机滚动
                for i in range(random.randint(2, 5)):
                    scroll_y = random.randint(100, 500)
                    await page.evaluate(f"window.scrollBy(0, {scroll_y})")
                    await asyncio.sleep(0.5 + random.random() * 1.5)
                
                # 随机点击页面空白处
                if random.random() > 0.7:  # 30%概率执行
                    try:
                        click_x = random.randint(50, width - 100)
                        click_y = random.randint(200, 500)
                        await page.mouse.click(click_x, click_y)
                    except:
                        pass
                
                # 随机的短暂停顿
                await asyncio.sleep(1 + random.random() * 3)
            
            # 先访问知乎首页，模拟正常浏览路径
            try:
                # 先访问知乎主页，然后再去问题页面，更符合正常用户行为
                print("先访问知乎首页...")
                await page.goto("https://www.zhihu.com", wait_until="domcontentloaded")
                await asyncio.sleep(2 + random.random() * 3)
                
                # 模拟人类行为
                await simulate_human_behavior(page)
                
                # 随机等待一段时间
                wait_time = 2 + random.random() * 3
                print(f"等待 {wait_time:.2f} 秒...")
                await asyncio.sleep(wait_time)
                
                # 再访问问题页面
                print(f"正在打开问题页面: {question_url}")
                await page.goto(question_url, wait_until="domcontentloaded")
                
                # 等待页面加载完成
                await asyncio.sleep(2 + random.random() * 3)
                
                # 模拟人类浏览行为
                await simulate_human_behavior(page)
                
                # 收集回答数据
                question_title = await page.title()
                print(f"问题标题: {question_title}")
                
                # 滚动加载更多回答
                for i in range(random.randint(4, 8)):
                    # 随机滚动距离
                    scroll_distance = random.randint(800, 1500)
                    await page.evaluate(f"window.scrollBy(0, {scroll_distance})")
                    
                    # 随机等待加载
                    await asyncio.sleep(1 + random.random() * 2)
                    
                    # 尝试点击展开回答
                    expand_buttons = await page.query_selector_all("button.ContentItem-expandButton")
                    if expand_buttons and random.random() > 0.3:  # 70%概率点击展开
                        button_to_click = random.choice(expand_buttons)
                        try:
                            await button_to_click.click()
                            await asyncio.sleep(0.5 + random.random() * 1)
                        except:
                            pass
                
                # 收集页面上的回答元素
                answer_elements = await page.query_selector_all(".AnswerItem")
                print(f"找到 {len(answer_elements)} 个回答")
                answers = answer_elements
                
            except Exception as e:
                print(f"浏览过程中发生错误: {str(e)}")
                answers = []
                
        finally:
            # 确保关闭浏览器
            try:
                if browser:
                    await browser.close()
                else:
                    await context.close()
            except:
                pass
        
        return len(answers) 