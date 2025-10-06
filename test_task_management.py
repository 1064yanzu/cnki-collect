#!/usr/bin/env python3
"""
任务管理功能测试脚本

测试任务的创建、暂停、恢复和停止功能
"""

import time
import signal
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from task_manager import task_manager, TaskStoppedException
from keyword_scraper import KeywordScraper
from config import Config
from utils import Logger

# 初始化日志
logger = Logger.setup_logger("TaskTest")

def test_basic_task_management():
    """测试基本任务管理功能"""
    logger.info("开始测试基本任务管理功能...")
    
    # 创建一个简单的测试任务
    def simple_task(task, duration=10):
        """简单的测试任务"""
        for i in range(duration):
            task.check_pause_or_stop()
            task.update_progress(
                processed_items=i+1,
                current_step=f"执行步骤 {i+1}/{duration}"
            )
            time.sleep(1)
        return {"completed": True, "steps": duration}
    
    # 创建任务
    task_id = task_manager.create_task(
        task_type='test',
        task_name='简单测试任务',
        task_func=simple_task,
        parameters={'duration': 10},
        total_items=10,
        can_resume=True
    )
    
    logger.info(f"创建任务，ID: {task_id}")
    
    # 启动任务
    task_manager.start_task(task_id)
    
    # 等待3秒后暂停任务
    time.sleep(3)
    logger.info("暂停任务...")
    task_manager.pause_task(task_id)
    
    # 等待2秒后恢复任务
    time.sleep(2)
    logger.info("恢复任务...")
    task_manager.resume_task(task_id)
    
    # 等待任务完成
    task_data = task_manager.get_task_status(task_id)
    while task_data and task_data['status'] in ['running', 'paused']:
        time.sleep(1)
        task_data = task_manager.get_task_status(task_id)
    
    logger.info(f"任务完成，最终状态: {task_data['status'] if task_data else 'None'}")

def test_keyword_search_with_interruption():
    """测试关键词搜索的中断和恢复"""
    logger.info("开始测试关键词搜索的中断和恢复...")
    
    # 创建关键词搜索器
    scraper = KeywordScraper()
    
    # 启动关键词搜索任务
    task_id = scraper.scrape_keyword_with_task("测试关键词", 50)
    logger.info(f"创建关键词搜索任务，ID: {task_id}")
    
    # 等待5秒后暂停任务
    time.sleep(5)
    logger.info("暂停关键词搜索任务...")
    task_manager.pause_task(task_id)
    
    # 等待3秒后恢复任务
    time.sleep(3)
    logger.info("恢复关键词搜索任务...")
    task_manager.resume_task(task_id)
    
    # 监控任务状态
    task_data = task_manager.get_task_status(task_id)
    while task_data and task_data['status'] in ['running', 'paused']:
        logger.info(f"任务状态: {task_data['status']}, 进度: {task_data.get('processed_items', 0)}/{task_data.get('total_items', 0)}")
        time.sleep(2)
        task_data = task_manager.get_task_status(task_id)
    
    logger.info(f"关键词搜索任务完成，最终状态: {task_data['status'] if task_data else 'None'}")

def test_task_stop():
    """测试任务停止功能"""
    logger.info("开始测试任务停止功能...")
    
    def long_running_task(task, duration=30):
        """长时间运行的测试任务"""
        for i in range(duration):
            task.check_pause_or_stop()
            task.update_progress(
                processed_items=i+1,
                current_step=f"长时间任务步骤 {i+1}/{duration}"
            )
            time.sleep(1)
        return {"completed": True, "steps": duration}
    
    # 创建长时间运行的任务
    task_id = task_manager.create_task(
        task_type='long_test',
        task_name='长时间测试任务',
        task_func=long_running_task,
        parameters={'duration': 30},
        total_items=30,
        can_resume=True
    )
    
    logger.info(f"创建长时间任务，ID: {task_id}")
    
    # 启动任务
    task_manager.start_task(task_id)
    
    # 等待5秒后停止任务
    time.sleep(5)
    logger.info("停止任务...")
    task_manager.stop_task(task_id)
    
    # 检查任务状态
    task_data = task_manager.get_task_status(task_id)
    logger.info(f"任务停止后状态: {task_data['status'] if task_data else 'None'}")

def test_resumable_tasks():
    """测试可恢复任务功能"""
    logger.info("开始测试可恢复任务功能...")
    
    # 获取所有可恢复的任务
    resumable_tasks = task_manager.get_resumable_tasks()
    logger.info(f"找到 {len(resumable_tasks)} 个可恢复的任务")
    
    for task_data in resumable_tasks:
        logger.info(f"可恢复任务: {task_data['task_name']} (ID: {task_data['id']}, 状态: {task_data['status']})")

def signal_handler(signum, frame):
    """信号处理器，用于优雅关闭"""
    logger.info("收到中断信号，正在关闭任务管理器...")
    task_manager.pause_all_tasks()
    sys.exit(0)

def main():
    """主测试函数"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=== 任务管理功能测试开始 ===")
    
    try:
        # 测试1: 基本任务管理
        test_basic_task_management()
        time.sleep(2)
        
        # 测试2: 任务停止
        test_task_stop()
        time.sleep(2)
        
        # 测试3: 可恢复任务
        test_resumable_tasks()
        time.sleep(2)
        
        # 测试4: 关键词搜索中断恢复（可选，需要网络）
        # test_keyword_search_with_interruption()
        
        logger.info("=== 所有测试完成 ===")
        
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
    except Exception as e:
        logger.error(f"测试过程中出现错误: {e}")
    finally:
        # 暂停所有任务
        task_manager.pause_all_tasks()

if __name__ == "__main__":
    main()