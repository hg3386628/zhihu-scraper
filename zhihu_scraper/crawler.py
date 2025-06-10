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
from playwright.async_api import async_playwright

try:
    from browser_use import Agent, Browser, BrowserConfig, BrowserContext
    browser_use_available = True
except ImportError:
    browser_use_available = False

async def scrape_question(self, question_id, output_dir='output', manual_mode=False):
    """使用Playwright爬取知乎问题数据
    
    Args:
        question_id: 知乎问题ID
        output_dir: 输出目录
        manual_mode: 是否强制使用手动浏览器模式
    
    Returns:
        成功爬取的答案数量
    """
    
    # 如果未启用AI代理模式或强制使用手动模式，则使用手动浏览器模式
    if manual_mode or not hasattr(self, 'llm') or self.llm is None:
        return await self._launch_browser_manually(question_id, output_dir)
    
    print("启动AI控制浏览器模式...")
    question_url = f"https://www.zhihu.com/question/{question_id}"
    output_file = os.path.join(output_dir, f"zhihu_question_{question_id}.json")
    output_md_file = os.path.join(output_dir, f"zhihu_question_{question_id}.md")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 为当前问题创建专属文件夹
    question_dir = os.path.join(output_dir, str(question_id))
    if not os.path.exists(question_dir):
        os.makedirs(question_dir)
    
    # 准备爬虫任务描述
    task = f"""你是一位资深的网页数据爬虫专家，现在需要你帮我访问并从知乎问题页面提取数据。
   
    5. 然后再访问问题页面: {question_url}
    
    在问题页面上执行以下操作:
    1. 等待页面完全加载（包括问题详情和所有初始可见的回答）
    2. 向下滚动页面至少5次，等待新内容加载
    3. 提取以下信息:
       - 问题标题
       - 问题描述（如果有）
       - 至少前10个回答（包括作者信息、回答内容、点赞数等）
    4. 点击任何需要展开的"阅读全文"按钮
    
    将所提取数据以结构化的JSON格式返回，包含问题信息和回答列表。
    返回结果必须是有效的JSON格式。
    """
    
    # 清除之前可能存在的Chromium进程
    if platform.system() == "Windows":
        try:
            os.system("taskkill /f /im chromium.exe")
            time.sleep(2)
        except:
            pass
    elif platform.system() == "Darwin":  # macOS
        try:
            os.system("pkill -f Chromium")
            time.sleep(2)
        except:
            pass
    elif platform.system() == "Linux":
        try:
            os.system("pkill -f chromium")
            time.sleep(2)
        except:
            pass
    
    # 获取用户数据目录
    user_data_dir = self.user_data_dir
    print(f"使用持久化配置目录: {user_data_dir}")
    
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

    # 使用Playwright的持久化上下文
    async with async_playwright() as p:
        # 创建反检测脚本
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
                const canvas = document.createElement('canvas');
                canvas.width = this.width;
                canvas.height = this.height;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(this, 0, 0);
                const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                const data = imageData.data;
                for (let i = 0; i < data.length; i += 4) {
                    data[i] = data[i] + Math.floor(Math.random() * 10) - 5;
                    data[i+1] = data[i+1] + Math.floor(Math.random() * 10) - 5;
                    data[i+2] = data[i+2] + Math.floor(Math.random() * 10) - 5;
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
                if (channelData.length > 20) {
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
        
        print(f"启动Playwright持久化上下文，用户数据目录: {user_data_dir}")
        
        try:
            # 使用持久化目录启动浏览器
            browser_context = await p.chromium.launch_persistent_context(
                user_data_dir,
                headless=False,
                slow_mo=50,
                args=browser_args,
                viewport={"width": width, "height": height},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
                locale="zh-CN",
                timezone_id="Asia/Shanghai"
            )
            
            # 创建页面
            page = await browser_context.new_page()
            
            # 注入反检测脚本
            await page.add_init_script(init_js_code)
            
            # 访问问题页面
            await page.goto(question_url, wait_until="domcontentloaded")
            print(f"已打开问题页面: {question_url}")
            
            # 等待页面加载
            await asyncio.sleep(5)
            
            # 模拟人类行为 - 向下滚动页面
            for i in range(8):  # 多滚动几次以加载更多内容
                # 随机滚动距离
                scroll_distance = random.randint(800, 1200)
                await page.evaluate(f"window.scrollBy(0, {scroll_distance})")
                # 随机等待时间
                await asyncio.sleep(1 + random.random() * 2)
            
            # 点击所有"阅读全文"按钮
            read_more_selectors = await page.evaluate("""
                () => {
                    // 查找所有按钮
                    const buttons = Array.from(document.querySelectorAll('button'));
                    // 过滤出包含"阅读全文"文本的按钮
                    const readMoreButtons = buttons.filter(btn => 
                        btn.textContent && btn.textContent.trim().includes('阅读全文')
                    );
                    
                    // 返回这些按钮的XPath，以便后续点击
                    return readMoreButtons.map(btn => {
                        // 为每个按钮生成一个唯一的数据标记
                        const id = 'click-' + Math.random().toString(36).substring(2, 10);
                        btn.setAttribute('data-clickid', id);
                        return id;
                    });
                }
            """)
            
            # 点击每个被标记的按钮
            for click_id in read_more_selectors:
                try:
                    # 使用data-clickid属性定位按钮
                    button = await page.query_selector(f'button[data-clickid="{click_id}"]')
                    if button:
                        await button.click()
                        await asyncio.sleep(0.5 + random.random() * 0.5)
                except Exception as e:
                    print(f"点击阅读全文按钮时出错: {str(e)}")
                    pass
            
            # 再次向下滚动，确保内容完全加载
            for i in range(3):
                await page.evaluate(f"window.scrollBy(0, {random.randint(500, 800)})")
                await asyncio.sleep(1 + random.random())
            
            # 提取数据
            result = await page.evaluate("""() => {
                function extractText(element) {
                    return element ? element.textContent.trim() : '';
                }
                
                // 获取问题标题
                const title = document.querySelector('.QuestionHeader-title')?.textContent.trim();
                
                // 获取问题描述
                const description = document.querySelector('.QuestionRichText')?.innerText.trim();
                
                // 获取回答列表
                const answerItems = document.querySelectorAll('.List-item, .AnswerCard');
                const answers = Array.from(answerItems).slice(0, 30).map(item => {
                    // 作者信息
                    const authorElement = item.querySelector('.AuthorInfo-name');
                    const author = authorElement ? {
                        name: authorElement.textContent.trim(),
                        link: authorElement.querySelector('a')?.href
                    } : { name: '匿名用户' };
                    
                    // 回答内容
                    const contentElement = item.querySelector('.RichText');
                    const content = contentElement ? contentElement.innerHTML : '';
                    
                    // 点赞数
                    const upvoteElement = item.querySelector('button[aria-label="赞同"]');
                    const upvoteText = upvoteElement?.textContent.trim().replace(/[^0-9]/g, '');
                    const upvotes = upvoteText ? parseInt(upvoteText) || 0 : 0;
                    
                    // 评论数 - 使用标准的DOM API查找包含"评论"文本的按钮
                    let commentCount = 0;
                    const buttons = item.querySelectorAll('.Button--withIcon.Button--withLabel');
                    for (const btn of buttons) {
                        if (btn.textContent && btn.textContent.includes('评论')) {
                            const commentText = btn.textContent.trim();
                            const match = commentText.match(/\\d+/);
                            if (match) {
                                commentCount = parseInt(match[0]);
                            }
                            break;
                        }
                    }
                    
                    return {
                        author,
                        content,
                        upvotes,
                        comments: commentCount
                    };
                }).filter(answer => answer.content); // 过滤掉没有内容的回答
                
                return {
                    title,
                    description,
                    answers,
                    meta: {
                        crawl_time: new Date().toISOString(),
                        question_id: window.location.href.match(/question\\/(\\d+)/)?.[1],
                        url: window.location.href
                    }
                };
            }""")
            
            # 保存JSON结果
            try:
                # 保存为JSON文件
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"结果已保存到JSON文件: {output_file}")
                
                # 转换为Markdown格式并保存
                md_content = _convert_to_markdown(result, question_id)
                with open(output_md_file, 'w', encoding='utf-8') as f:
                    f.write(md_content)
                print(f"结果已保存到Markdown文件: {output_md_file}")
                
                # 同时在问题专属目录中保存一份
                question_md_file = os.path.join(question_dir, "question.md")
                with open(question_md_file, 'w', encoding='utf-8') as f:
                    f.write(md_content)
                
            except Exception as e:
                print(f"保存结果时出错: {str(e)}")
            
            # 关闭浏览器上下文
            await browser_context.close()
            
            return result
        except Exception as e:
            print(f"爬取过程中出错: {str(e)}")
            # 如果出错，尝试关闭浏览器上下文
            try:
                await browser_context.close()
            except:
                pass
            raise e

def _convert_to_markdown(data, question_id):
    """将知乎问题数据转换为Markdown格式
    
    Args:
        data: 知乎问题数据(JSON格式)
        question_id: 知乎问题ID
        
    Returns:
        Markdown格式的字符串
    """
    try:
        # 如果数据是字符串，尝试解析为JSON
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except:
                # 无法解析为JSON，返回错误信息
                return f"# 无法解析数据\n\n原始数据:\n\n```\n{data}\n```"
        
        # 获取当前时间
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 初始化Markdown内容
        md = []
        
        # 添加标题和元数据
        md.append(f"# {data.get('title', '未知标题')}")
        md.append("")
        md.append(f"问题ID: {question_id}")
        md.append(f"抓取时间: {now}")
        md.append(f"问题链接: https://www.zhihu.com/question/{question_id}")
        md.append("")
        
        # 添加问题描述（如果有）
        description = data.get('description', '')
        if description:
            md.append("## 问题描述")
            md.append("")
            md.append(description)
            md.append("")
        
        # 获取回答列表
        answers = data.get('answers', [])
        if not answers and isinstance(data, list):
            # 如果数据本身是列表，可能直接就是回答列表
            answers = data
        
        # 添加回答
        md.append(f"## 回答 ({len(answers)})")
        md.append("")
        
        # 遍历回答
        for i, answer in enumerate(answers, 1):
            # 获取作者信息
            author = answer.get('author', {})
            if isinstance(author, str):
                author_name = author
            else:
                author_name = author.get('name', '匿名用户')
            
            # 获取回答内容
            content = answer.get('content', '')
            if not content:
                content = answer.get('answer_content', '')
            
            # 获取赞同数
            upvotes = answer.get('upvotes', answer.get('like_count', '未知'))
            
            # 添加回答标题
            md.append(f"### 回答 {i} - {author_name}")
            md.append("")
            md.append(f"👍 点赞数: {upvotes}")
            md.append("")
            md.append(content)
            md.append("")
            md.append("---")
            md.append("")
        
        return "\n".join(md)
    
    except Exception as e:
        return f"# 生成Markdown时出错\n\n错误信息: {str(e)}\n\n原始数据:\n\n```\n{str(data)[:1000]}...\n```" 