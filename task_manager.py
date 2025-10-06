"""
任务管理器 - 支持任务中断和恢复
"""
import json
import signal
import threading
import time
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime

from database import db
from utils import Logger


class TaskManager:
    """任务管理器 - 支持任务中断和恢复"""
    
    def __init__(self):
        self.logger = Logger.setup_logger(self.__class__.__name__)
        self.running_tasks: Dict[int, 'Task'] = {}
        self.shutdown_requested = False
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """处理中断信号"""
        self.logger.info(f"收到信号 {signum}，开始优雅关闭...")
        self.shutdown_requested = True
        self.pause_all_tasks()
    
    def create_task(self, task_type: str, task_name: str, task_func: Callable,
                   parameters: dict = None, total_items: int = 0, 
                   can_resume: bool = True) -> int:
        """创建新任务"""
        task_id = db.create_task(task_type, task_name, parameters, total_items, can_resume)
        
        task = Task(
            task_id=task_id,
            task_type=task_type,
            task_name=task_name,
            task_func=task_func,
            parameters=parameters or {},
            total_items=total_items,
            can_resume=can_resume,
            task_manager=self
        )
        
        self.running_tasks[task_id] = task
        return task_id
    
    def start_task(self, task_id: int):
        """启动任务"""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.start()
        else:
            self.logger.error(f"任务不存在: {task_id}")
    
    def pause_task(self, task_id: int):
        """暂停任务"""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.pause()
        else:
            self.logger.error(f"任务不存在: {task_id}")
    
    def resume_task(self, task_id: int):
        """恢复任务"""
        # 从数据库获取任务信息
        task_data = db.get_task(task_id)
        if not task_data:
            self.logger.error(f"任务不存在: {task_id}")
            return False
        
        if task_data['status'] != 'paused':
            self.logger.error(f"任务状态不是暂停状态: {task_data['status']}")
            return False
        
        if not task_data['can_resume']:
            self.logger.error(f"任务不支持恢复: {task_id}")
            return False
        
        # 这里需要根据任务类型重新创建任务实例
        # 实际实现中需要注册任务工厂函数
        self.logger.info(f"恢复任务: {task_id}")
        db.resume_task(task_id)
        return True
    
    def stop_task(self, task_id: int):
        """停止任务"""
        # 如果任务正在运行，停止它
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.stop()
            del self.running_tasks[task_id]
            self.logger.info(f"停止运行中的任务: {task_id}")
            return True
        
        # 如果任务在数据库中，更新其状态
        task_data = db.get_task(task_id)
        if task_data:
            if task_data['status'] in ['pending', 'paused']:
                db.update_task_status(task_id, 'failed', error_message='任务被手动停止')
                self.logger.info(f"停止任务: {task_id}")
                return True
            else:
                self.logger.warning(f"任务状态不允许停止: {task_data['status']}")
                return False
        
        self.logger.error(f"任务不存在: {task_id}")
        return False
    
    def pause_all_tasks(self):
        """暂停所有运行中的任务"""
        for task_id, task in self.running_tasks.items():
            if task.is_running():
                task.pause()
    
    def get_task_status(self, task_id: int) -> Optional[Dict]:
        """获取任务状态"""
        return db.get_task(task_id)
    
    def get_task(self, task_id: int) -> Optional['Task']:
        """获取任务对象"""
        task_data = db.get_task(task_id)
        if task_data:
            # 如果任务正在运行，返回运行中的任务对象
            if task_id in self.running_tasks:
                return self.running_tasks[task_id]
            # 否则创建一个临时的任务对象用于查看状态
            class TaskInfo:
                def __init__(self, data):
                    self.data = data
                def to_dict(self):
                    return self.data
            return TaskInfo(task_data)
        return None
    
    def get_all_tasks(self) -> List[Dict]:
        """获取所有任务"""
        return db.get_tasks()
    
    def get_resumable_tasks(self) -> List[Dict]:
        """获取可恢复的任务"""
        return db.get_resumable_tasks()
    
    def cleanup_completed_tasks(self):
        """清理已完成的任务"""
        for task_id in list(self.running_tasks.keys()):
            task = self.running_tasks[task_id]
            if task.is_completed():
                del self.running_tasks[task_id]


class Task:
    """任务类"""
    
    def __init__(self, task_id: int, task_type: str, task_name: str, 
                 task_func: Callable, parameters: dict, total_items: int,
                 can_resume: bool, task_manager: TaskManager):
        self.task_id = task_id
        self.task_type = task_type
        self.task_name = task_name
        self.task_func = task_func
        self.parameters = parameters
        self.total_items = total_items
        self.can_resume = can_resume
        self.task_manager = task_manager
        
        self.thread: Optional[threading.Thread] = None
        self.pause_event = threading.Event()
        self.stop_event = threading.Event()
        self.logger = Logger.setup_logger(f"Task-{task_id}")
        
        # 任务状态
        self.processed_items = 0
        self.failed_items = 0
        self.current_step = ""
        self.resume_data = {}
    
    def start(self):
        """启动任务"""
        if self.thread and self.thread.is_alive():
            self.logger.warning("任务已在运行中")
            return
        
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        
        db.update_task_status(self.task_id, 'running')
        self.logger.info(f"任务已启动: {self.task_name}")
    
    def pause(self):
        """暂停任务"""
        if not self.can_resume:
            self.logger.warning("任务不支持暂停")
            return
        
        self.pause_event.set()
        
        # 保存恢复数据
        resume_data = {
            'processed_items': self.processed_items,
            'failed_items': self.failed_items,
            'current_step': self.current_step,
            'custom_data': self.resume_data
        }
        
        db.pause_task(self.task_id, resume_data)
        self.logger.info(f"任务已暂停: {self.task_name}")
    
    def stop(self):
        """停止任务"""
        self.stop_event.set()
        self.pause_event.set()
    
    def is_running(self) -> bool:
        """检查任务是否在运行"""
        return self.thread and self.thread.is_alive() and not self.pause_event.is_set()
    
    def is_paused(self) -> bool:
        """检查任务是否暂停"""
        return self.pause_event.is_set()
    
    def is_completed(self) -> bool:
        """检查任务是否完成"""
        return not (self.thread and self.thread.is_alive())
    
    def update_progress(self, processed_items: int = None, failed_items: int = None,
                       current_step: str = None, progress: int = None):
        """更新任务进度"""
        if processed_items is not None:
            self.processed_items = processed_items
        if failed_items is not None:
            self.failed_items = failed_items
        if current_step is not None:
            self.current_step = current_step
        
        # 计算进度百分比
        if progress is None and self.total_items > 0:
            progress = int((self.processed_items / self.total_items) * 100)
        
        db.update_task_status(
            self.task_id,
            'running',
            progress=progress,
            current_step=current_step,
            processed_items=self.processed_items,
            failed_items=self.failed_items
        )
    
    def check_pause_or_stop(self):
        """检查是否需要暂停或停止"""
        if self.stop_event.is_set():
            raise TaskStoppedException("任务被停止")
        
        if self.pause_event.is_set():
            self.logger.info("任务暂停中...")
            # 等待恢复或停止信号
            while self.pause_event.is_set() and not self.stop_event.is_set():
                time.sleep(0.1)
            
            if self.stop_event.is_set():
                raise TaskStoppedException("任务被停止")
            
            self.logger.info("任务恢复运行")
    
    def _run(self):
        """运行任务"""
        try:
            # 执行任务函数
            result = self.task_func(self, **self.parameters)
            
            # 任务完成
            db.update_task_status(
                self.task_id, 
                'completed',
                progress=100,
                processed_items=self.processed_items,
                failed_items=self.failed_items,
                result_data=result if isinstance(result, dict) else None
            )
            
            self.logger.info(f"任务完成: {self.task_name}")
            
        except TaskStoppedException:
            db.update_task_status(self.task_id, 'failed', error_message="任务被停止")
            self.logger.info(f"任务被停止: {self.task_name}")
            
        except Exception as e:
            error_msg = str(e)
            db.update_task_status(
                self.task_id, 
                'failed',
                error_message=error_msg,
                processed_items=self.processed_items,
                failed_items=self.failed_items
            )
            self.logger.error(f"任务执行失败: {self.task_name}, 错误: {error_msg}")


class TaskStoppedException(Exception):
    """任务停止异常"""
    pass


# 全局任务管理器实例
task_manager = TaskManager()