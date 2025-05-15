"""
工具函数 - 提供各种辅助功能
"""

import os
import re
import random
import platform
import uuid
import json
import time
from datetime import datetime

def parse_question_id(url_or_id):
    """从URL或ID字符串中提取知乎问题ID
    
    Args:
        url_or_id: 知乎问题URL或ID
        
    Returns:
        str: 提取出的问题ID
    """
    # 如果是纯数字，直接返回
    if re.match(r'^\d+$', url_or_id):
        return url_or_id
        
    # 从URL中提取ID
    match = re.search(r'question/(\d+)', url_or_id)
    if match:
        return match.group(1)
    
    # 无法识别的格式
    raise ValueError(f"无法从 '{url_or_id}' 中提取问题ID")

def format_file_size(size_bytes):
    """格式化文件大小为人类可读格式
    
    Args:
        size_bytes: 文件大小（字节）
        
    Returns:
        str: 格式化后的大小字符串
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024 or unit == 'TB':
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024

def ensure_dir(directory):
    """确保目录存在，如不存在则创建
    
    Args:
        directory: 目录路径
        
    Returns:
        str: 创建的目录路径
    """
    os.makedirs(directory, exist_ok=True)
    return directory

def generate_random_id():
    """生成随机ID
    
    Returns:
        str: 随机生成的UUID
    """
    return str(uuid.uuid4())

def parse_votes(votes_str):
    """解析点赞数字符串为整数
    
    Args:
        votes_str: 点赞数字符串，如"1K"、"2.5K"
        
    Returns:
        int: 解析后的点赞数
    """
    if not votes_str or votes_str == '0':
        return 0
    
    if 'K' in votes_str:
        return int(float(votes_str.replace('K', '')) * 1000)
    
    try:
        return int(votes_str)
    except:
        return 0

def get_timestamp():
    """获取当前时间戳
    
    Returns:
        str: 格式化的时间戳字符串
    """
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def kill_browser_processes():
    """根据操作系统类型关闭所有浏览器进程"""
    system = platform.system()
    
    try:
        if system == "Darwin":  # macOS
            os.system("pkill -f 'Chromium'")
        elif system == "Windows":
            os.system("taskkill /f /im chromium.exe")
        elif system == "Linux":
            os.system("pkill -f chromium")
        
        # 等待进程完全关闭
        time.sleep(2)
        print("已关闭所有Chromium浏览器进程")
    except Exception as e:
        print(f"关闭浏览器进程失败: {e}")

def save_json(data, file_path):
    """保存数据为JSON文件
    
    Args:
        data: 要保存的数据
        file_path: 文件路径
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_json(file_path):
    """从JSON文件加载数据
    
    Args:
        file_path: 文件路径
        
    Returns:
        dict: 加载的JSON数据
    """
    if not os.path.exists(file_path):
        return None
        
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f) 