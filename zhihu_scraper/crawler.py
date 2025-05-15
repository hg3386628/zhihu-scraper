"""
爬虫核心功能 - 处理数据抓取和存储
"""

import asyncio
import os
import time
import random
import platform
import json
from datetime import datetime

try:
    from browser_use import Agent, Browser, BrowserConfig
    browser_use_available = True
except ImportError:
    browser_use_available = False

async def scrape_question(self, question_id, output_dir='output', manual_mode=False):
    """抓取知乎问题的回答"""
    # 根据模式选择方法
    if manual_mode:
        print("使用手动浏览器模式爬取数据（更可靠但较慢）...")
        result = await self._launch_browser_manually(question_id, output_dir)
        if result is not None:
            return result
        
        print("手动浏览器方法失败，尝试使用AI代理方法...")
    
    # 使用AI代理方法
    print("使用AI代理模式爬取数据...")
    
    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # 为当前问题创建专属文件夹
    question_dir = os.path.join(output_dir, str(question_id))
    if not os.path.exists(question_dir):
        os.makedirs(question_dir)
    
    # 构建知乎问题URL
    url = f"https://www.zhihu.com/question/{question_id}"
    
    # 设置任务描述 - 增强指导性内容以实现更好的隐蔽性
    task = f"""
    请访问知乎问题链接 {url} 并执行以下任务：
    1. 获取问题标题和描述
    2. 获取所有回答（需要向下滚动加载全部回答）
    3. 对于每个回答，提取：
       - 作者名称
       - 点赞数和评论数
       - 回答内容（完整的文字和图片链接）
       - 回答创建时间
    4. 将所有信息保存为Markdown格式，存储在 {question_dir} 目录下
    5. 对回答按照点赞数排序
    
    注意：
    - 知乎页面可能需要登录，如果遇到登录提示，请尝试关闭登录弹窗继续浏览
    - 请依赖页面上的文本描述和标签进行操作
    - 如果遇到403错误或访问被限制，请等待1-2分钟后重试
    - 必须实现真实的人类浏览行为以避免被检测，请通过以下方式隐藏自己：
    
    【隐蔽操作详细指南】:
    1. 首次访问行为:
       - 直接访问问题页面
       - 模拟几次随机鼠标移动和短暂停顿
    
    2. 浏览行为模拟:
       - 使用类似人类的滚动模式，切勿直接滚到底部
       - 每次滚动距离约300-700像素，而非整页
       - 滚动后停留5-15秒，模拟阅读内容
       - 偶尔进行短距离上下滚动，表现出对内容的关注
    
    3. 交互行为:
       - 点击任何按钮前，先将鼠标移动到按钮位置停留0.5-1秒
       - 移动鼠标时使用自然曲线而非直线路径（注意：在macOS上需特别注意鼠标移动的自然性）
       - 点击后等待不同的时间(3-7秒)再执行下一操作
       - 偶尔在无关紧要区域进行随机点击
    
    4. 节奏控制:
       - 保持不规则的操作节奏，避免机械性定时操作
       - 加载更多内容前先停顿模拟阅读
       - 整个浏览过程中偶尔停顿10-20秒不进行任何交互

    5. 页面处理:
       - 如果出现登录提示，等待2-3秒再尝试关闭弹窗
       - 遇到验证码挑战时，暂停并详细描述看到的内容
       - 如果页面加载太慢，等待8-12秒再重试
    """
    
    # 如果有cookie，添加登录操作指导
    if self.zhihu_cookie:
        task += f"""
        您可以使用以下cookie进行登录以获取更完整的内容。请仔细按步骤操作：
        
        步骤：
        1. 首先打开一个新标签页，并导航到 https://zhihu.com
        2. 等待页面完全加载，然后仔细观察是否有登录窗口
        3. 如果网页显示为登录页面，使用开发者工具(按F12或右键检查)打开控制台(Console)
        4. 在控制台中执行以下操作:
           
           // 设置cookie
           document.cookie = "{self.zhihu_cookie}";
           
           // 等待3-5秒后运行下面的脚本设置localStorage和必要的认证信息
           localStorage.setItem('LOGIN_STATUS', '1');
           
           // 如果cookie中包含z_c0，提取并设置到localStorage
           const z_c0Match = "{self.zhihu_cookie}".match(/z_c0=([^;]+)/);
           if (z_c0Match) {{
               localStorage.setItem('z_c0', z_c0Match[1]);
           }}
           
           // 设置XSRF Token
           const xsrfToken = Math.random().toString(36).slice(2);
           document.cookie = `_xsrf=${{xsrfToken}};domain=.zhihu.com;path=/`;
           localStorage.setItem('_xsrf', xsrfToken);
           
           console.log("已完成登录设置");
           
        5. 等待3-5秒钟，不要立即刷新
        6. 然后刷新页面，检查是否成功登录（页面顶部应显示个人头像）
        7. 如果登录成功，再访问问题页面: {url}
        8. 如果遇到任何验证码或安全提示，请描述您看到的内容
        """
    
    try:
        # 先确保所有Chromium实例已关闭
        if platform.system() == "Darwin":  # macOS
            try:
                os.system("pkill -f 'Chromium'")
                time.sleep(2)  # 等待进程完全关闭
            except:
                pass
        elif platform.system() == "Windows":
            try:
                os.system("taskkill /f /im chromium.exe")
                time.sleep(2)
            except:
                pass
        elif platform.system() == "Linux":
            try:
                os.system("pkill -f chromium")
                time.sleep(2)
            except:
                pass
        
        # 用户数据目录 - 使用固定目录以保持会话
        user_data_dir = os.path.expanduser("~/zhihu-browser-profile")
        os.makedirs(user_data_dir, exist_ok=True)
        print(f"使用持久化配置目录: {user_data_dir}")
        
        # 如果有cookie，准备将cookie保存到本地文件
        if self.zhihu_cookie:
            cookie_file = os.path.join(user_data_dir, "cookies.json")
            try:
                # 解析cookie为json格式
                cookie_data = []
                for cookie_str in self.zhihu_cookie.split(';'):
                    if '=' in cookie_str:
                        name, value = cookie_str.strip().split('=', 1)
                        if name and value:
                            cookie_data.append({
                                "name": name,
                                "value": value,
                                "domain": ".zhihu.com", 
                                "path": "/",
                                "secure": True,
                                "httpOnly": name in ["z_c0", "SESSIONID"]
                            })
                
                # 保存cookie到文件
                with open(cookie_file, 'w') as f:
                    json.dump(cookie_data, f)
                print(f"已保存cookie到: {cookie_file}")
            except Exception as e:
                print(f"保存cookie失败: {str(e)}")
        
        # 始终使用Chromium浏览器
        print("使用Chromium浏览器配置")
        
        # 添加自定义js代码以注入反检测脚本
        init_js_code = """
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
        
        # 随机化窗口大小
        width = 1920 + random.randint(-100, 100)
        height = 1080 + random.randint(-50, 50)
            
        # 创建增强的浏览器配置
        browser_config = BrowserConfig(
            headless=False,
            persistent_context_dir=user_data_dir,  # 使用持久化配置目录
            viewport_width=width,
            viewport_height=height,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chromium/136.0.0.0 Safari/537.36",
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            extra_browser_args=[
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-site-isolation-trials",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                f"--window-size={width},{height}"
            ],
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
            },
            init_js=init_js_code  # 添加自定义JS脚本注入
        )
        print(f"启动Chromium，用户数据目录: {user_data_dir}")
        
        # 创建浏览器实例
        browser = Browser(config=browser_config)
        
        # 创建agent配置参数
        agent = Agent(
            task=task,
            llm=self.llm,
            browser=browser
        )
        
        # 运行agent
        try:
            result = await agent.run()
            # 关闭浏览器
            await browser.close()
            return result
        except Exception as e:
            print(f"AI代理运行失败: {str(e)}")
            # 如果出错，确保关闭浏览器
            try:
                await browser.close()
            except:
                pass
            raise e
            
    except Exception as e:
        # 如果使用增强配置失败，尝试使用最基本的配置或回退到手动模式
        print(f"AI代理模式初始化失败 (原因: {str(e)})")
        
        # 尝试使用手动模式作为备选方案
        print("由于AI代理模式失败，自动切换到手动浏览器模式...")
        return await self._launch_browser_manually(question_id, output_dir) 