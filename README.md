# 知乎问题爬虫

一个强大的知乎问题爬虫工具，支持AI代理和手动浏览器两种模式，能够高效抓取知乎问题及其所有回答。使用先进的浏览器自动化和反检测技术，有效绕过知乎的防爬机制。

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 功能特点

- **双模式爬取**
  - 🤖 **AI代理模式**: 利用大型语言模型控制浏览器（基于browser-use库）
  - 🌐 **手动浏览器模式**: 直接使用Playwright控制浏览器，更可靠但较慢
- **多种LLM支持**
  - 支持OpenAI、DeepSeek、Anthropic Claude、Google Gemini等多种模型
  - 自动适配可用的API密钥
- **登录支持**
  - 通过Cookie实现登录，获取完整内容（包括登录后才能查看的内容）
  - 智能Cookie处理，自动生成必要参数
- **高级反检测**
  - 内置多种浏览器指纹伪装技术
  - 模拟人类行为的浏览模式
  - WebGL、Canvas、AudioContext等多维度指纹修改
- **数据存储**
  - 自动保存为Markdown格式
  - 按点赞数排序，便于查找高质量内容
  - 智能合并多个回答，减少文件数量
- **用户友好**
  - 支持命令行和API两种使用方式
  - 详细的日志输出，便于排查问题

## 系统要求

- **Python 3.11+** (browser-use库的要求)
- **操作系统**: Windows、macOS或Linux
- **内存**: 建议4GB以上
- **网络**: 稳定的互联网连接
- **存储**: 取决于抓取内容的多少

## 安装方法

### 方法1: 通过pip安装（推荐）

```bash
# 安装基本依赖
pip install zhihu-scraper

# 安装AI代理模式所需的额外依赖
pip install zhihu-scraper[ai]

# 安装Playwright浏览器
playwright install
```

### 方法2: 从源码安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/zhihu-scraper.git
cd zhihu-scraper

# 安装依赖
pip install -e .  # 安装基本依赖
pip install -e ".[ai]"  # 安装AI代理模式所需的额外依赖

# 安装Playwright浏览器
playwright install
```

## 配置环境

创建`.env`文件并配置以下参数（可选但推荐）:

```ini
# API密钥（选择一个配置）
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# ANTHROPIC_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# GOOGLE_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 知乎Cookie（可选，但推荐提供以获取更完整内容）
ZHIHU_COOKIE_FULL=z_c0=xxxxxxx; _xsrf=xxxxxxx; SESSIONID=xxxxxxx
# 或者仅提供z_c0(身份认证核心)
# ZHIHU_COOKIE_Z_C0=xxxxxxx

# 禁用telemetry（可选）
ANONYMIZED_TELEMETRY=false
```

## 使用方法

### 命令行使用

```bash
# 基本用法（使用AI代理模式）
zhihu-scraper 537377466

# 使用手动浏览器模式（更可靠但较慢）
zhihu-scraper 537377466 --manual

# 指定API密钥和模型
zhihu-scraper 537377466 --api-key sk-xxx --model gpt-4o

# 使用DeepSeek模型
zhihu-scraper 537377466 --model deepseek-chat --api-key sk-xxx

# 指定输出目录
zhihu-scraper 537377466 --output ./my_data

# 使用Cookie进行登录
zhihu-scraper 537377466 --cookie "z_c0=xxx; _xsrf=xxx"
```

### 代码中使用

```python
import asyncio
from zhihu_scraper import ZhihuBrowserScraper

async def main():
    # 初始化爬虫
    scraper = ZhihuBrowserScraper(
        api_key="sk-xxx",  # API密钥(AI代理模式需要)
        model_name="gpt-4o",  # 使用的模型
        zhihu_cookie="z_c0=xxx; _xsrf=xxx"  # 可选Cookie
    )
    
    # 抓取问题
    result = await scraper.scrape_question(
        question_id="537377466",  # 可以是URL或ID
        output_dir="output",
        manual_mode=False  # 使用AI代理模式
    )
    
    print(f"共获取到 {result} 个回答")

if __name__ == "__main__":
    asyncio.run(main())
```

## 输出结果

抓取的内容将保存在指定的输出目录中（默认为`output/问题ID/`），包括：

```
output/537377466/
├── 问题详情.md           # 问题标题和描述
├── 回答集合_01.md        # 第1-10个回答
├── 回答集合_02.md        # 第11-20个回答
└── ...                  # 更多回答文件
```

## 常见问题

### 1. API密钥错误

问题: 出现`API密钥无效`或`未找到API密钥`错误。
解决: 确保在`.env`文件或命令行参数中提供了有效的API密钥。不同的模型需要不同的API密钥。

### 2. 安装依赖失败

问题: 安装时出现`Could not find a version that satisfies the requirement`。
解决: 确保Python版本≥3.11，可以使用`python --version`查看版本。

### 3. 无法获取登录后内容

问题: 只能获取未登录可见的内容。
解决: 提供有效的知乎Cookie，至少包含`z_c0`参数。

### 4. 浏览器启动失败

问题: 出现`Browser launch failed`错误。
解决: 运行`playwright install`安装浏览器，或确保系统中有可用的Chromium浏览器。

## 开发与贡献

欢迎贡献代码和提出建议:

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 格式化代码
black zhihu_scraper
isort zhihu_scraper
```

## 项目结构

```
zhihu-scraper/
├── zhihu_scraper/          # 主包目录
│   ├── __init__.py         # 包初始化文件
│   ├── scraper.py          # 爬虫核心类
│   ├── browser.py          # 浏览器操作模块
│   ├── crawler.py          # 爬取功能实现
│   ├── utils.py            # 工具函数
│   ├── cli.py              # 命令行接口
│   └── tests/              # 测试目录
├── examples/               # 示例脚本
├── .gitignore              # Git忽略配置
├── .env.example            # 环境变量示例
├── requirements.txt        # 依赖列表
├── setup.py                # 安装配置
└── README.md               # 项目说明
```

## 法律声明

- 本工具仅供学习和研究使用，请遵守知乎的使用条款和robots.txt规则
- 使用本工具抓取的内容，版权归原作者所有
- 请勿用于商业用途或大规模爬取
- 使用频率过高可能导致IP被限制，请合理控制爬取频率

## 许可证

[MIT License](LICENSE) © 2023
