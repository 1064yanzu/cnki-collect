"""
数据库模型 - 管理文章元数据、搜索历史等
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from config import Config
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Config.BASE_DIR / 'data.db'
        self.db_path = Path(db_path)
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 文章表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT UNIQUE NOT NULL,
                    abstract TEXT,
                    authors TEXT,
                    journal TEXT,
                    publish_date TEXT,
                    keywords TEXT,
                    source_type TEXT,  -- 'keyword_search' 或 'journal_scrape'
                    file_path TEXT,
                    download_status TEXT DEFAULT 'pending',  -- 'pending', 'downloading', 'completed', 'failed'
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 搜索历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    search_type TEXT NOT NULL,  -- 'keyword' 或 'journal'
                    search_query TEXT NOT NULL,
                    result_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'completed',  -- 'running', 'completed', 'failed'
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 用户收藏表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS favorites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (article_id) REFERENCES articles (id)
                )
            ''')
            
            # 下载任务表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS download_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_ids TEXT NOT NULL,  -- JSON数组存储文章ID列表
                    total_count INTEGER NOT NULL,
                    completed_count INTEGER DEFAULT 0,
                    failed_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',  -- 'pending', 'running', 'completed', 'failed', 'paused'
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 任务管理表 - 支持各种类型的任务状态管理
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_type TEXT NOT NULL,  -- 'keyword_search', 'journal_scrape', 'download'
                    task_name TEXT NOT NULL,  -- 任务名称/描述
                    parameters TEXT,  -- JSON格式的任务参数
                    status TEXT DEFAULT 'pending',  -- 'pending', 'running', 'completed', 'failed', 'paused'
                    progress INTEGER DEFAULT 0,  -- 进度百分比 (0-100)
                    current_step TEXT,  -- 当前执行步骤描述
                    total_items INTEGER DEFAULT 0,  -- 总项目数
                    processed_items INTEGER DEFAULT 0,  -- 已处理项目数
                    failed_items INTEGER DEFAULT 0,  -- 失败项目数
                    result_data TEXT,  -- JSON格式的结果数据
                    error_message TEXT,  -- 错误信息
                    can_resume BOOLEAN DEFAULT 1,  -- 是否支持恢复
                    resume_data TEXT,  -- JSON格式的恢复数据
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP
                )
            ''')
            
            # 标签表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    color TEXT DEFAULT '#007bff',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 文章标签关联表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS article_tags (
                    article_id INTEGER NOT NULL,
                    tag_id INTEGER NOT NULL,
                    PRIMARY KEY (article_id, tag_id),
                    FOREIGN KEY (article_id) REFERENCES articles (id),
                    FOREIGN KEY (tag_id) REFERENCES tags (id)
                )
            ''')
            
            conn.commit()
            logger.info("数据库初始化完成")
    
    def add_article(self, title: str, url: str, **kwargs) -> int:
        """添加文章记录"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 检查是否已存在
            cursor.execute('SELECT id FROM articles WHERE url = ?', (url,))
            existing = cursor.fetchone()
            if existing:
                return existing[0]
            
            # 插入新记录
            fields = ['title', 'url']
            values = [title, url]
            placeholders = ['?', '?']
            
            for key, value in kwargs.items():
                if key in ['abstract', 'authors', 'journal', 'publish_date', 'keywords', 'source_type']:
                    fields.append(key)
                    values.append(value)
                    placeholders.append('?')
            
            query = f'''
                INSERT INTO articles ({', '.join(fields)})
                VALUES ({', '.join(placeholders)})
            '''
            
            cursor.execute(query, values)
            article_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"添加文章: {title} (ID: {article_id})")
            return article_id
    
    def get_articles(self, limit: int = 100, offset: int = 0, 
                    search_query: str = None, source_type: str = None) -> List[Dict]:
        """获取文章列表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = 'SELECT * FROM articles WHERE 1=1'
            params = []
            
            if search_query:
                query += ' AND (title LIKE ? OR abstract LIKE ? OR keywords LIKE ?)'
                search_pattern = f'%{search_query}%'
                params.extend([search_pattern, search_pattern, search_pattern])
            
            if source_type:
                query += ' AND source_type = ?'
                params.append(source_type)
            
            query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            articles = [dict(row) for row in cursor.fetchall()]
            
            return articles
    
    def get_articles_count(self, search_query: str = None, source_type: str = None) -> int:
        """获取文章总数"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            query = 'SELECT COUNT(*) FROM articles WHERE 1=1'
            params = []
            
            if search_query:
                query += ' AND (title LIKE ? OR abstract LIKE ? OR keywords LIKE ?)'
                search_pattern = f'%{search_query}%'
                params.extend([search_pattern, search_pattern, search_pattern])
            
            if source_type:
                query += ' AND source_type = ?'
                params.append(source_type)
            
            cursor.execute(query, params)
            return cursor.fetchone()[0]
    
    def update_article_status(self, article_id: int, status: str, file_path: str = None):
        """更新文章下载状态"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if file_path:
                cursor.execute('''
                    UPDATE articles 
                    SET download_status = ?, file_path = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, file_path, article_id))
            else:
                cursor.execute('''
                    UPDATE articles 
                    SET download_status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, article_id))
            
            conn.commit()
    
    def add_search_history(self, search_type: str, search_query: str, result_count: int = 0) -> int:
        """添加搜索历史"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO search_history (search_type, search_query, result_count)
                VALUES (?, ?, ?)
            ''', (search_type, search_query, result_count))
            
            history_id = cursor.lastrowid
            conn.commit()
            
            return history_id
    
    def get_search_history(self, limit: int = 50) -> List[Dict]:
        """获取搜索历史"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM search_history 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def create_download_task(self, article_ids: List[int]) -> int:
        """创建下载任务"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO download_tasks (article_ids, total_count)
                VALUES (?, ?)
            ''', (json.dumps(article_ids), len(article_ids)))
            
            task_id = cursor.lastrowid
            conn.commit()
            
            return task_id
    
    def update_download_task(self, task_id: int, completed_count: int = None, 
                           failed_count: int = None, status: str = None):
        """更新下载任务状态"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if completed_count is not None:
                updates.append('completed_count = ?')
                params.append(completed_count)
            
            if failed_count is not None:
                updates.append('failed_count = ?')
                params.append(failed_count)
            
            if status is not None:
                updates.append('status = ?')
                params.append(status)
            
            if updates:
                updates.append('updated_at = CURRENT_TIMESTAMP')
                params.append(task_id)
                
                query = f'UPDATE download_tasks SET {", ".join(updates)} WHERE id = ?'
                cursor.execute(query, params)
                conn.commit()
    
    def get_download_tasks(self) -> List[Dict]:
        """获取所有下载任务"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM download_tasks ORDER BY created_at DESC')
            tasks = []
            for row in cursor.fetchall():
                task = dict(row)
                task['article_ids'] = json.loads(task['article_ids'])
                tasks.append(task)
            return tasks
    
    def get_download_task(self, task_id: int) -> Optional[Dict]:
        """获取下载任务信息"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM download_tasks WHERE id = ?', (task_id,))
            row = cursor.fetchone()
            
            if row:
                task = dict(row)
                task['article_ids'] = json.loads(task['article_ids'])
                return task
            
            return None
    
    # 任务管理方法
    def create_task(self, task_type: str, task_name: str, parameters: dict = None, 
                   total_items: int = 0, can_resume: bool = True) -> int:
        """创建新任务"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO tasks (task_type, task_name, parameters, total_items, can_resume)
                VALUES (?, ?, ?, ?, ?)
            ''', (task_type, task_name, json.dumps(parameters) if parameters else None, 
                  total_items, can_resume))
            
            task_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"创建任务: {task_name} (ID: {task_id})")
            return task_id
    
    def update_task_status(self, task_id: int, status: str, progress: int = None,
                          current_step: str = None, processed_items: int = None,
                          failed_items: int = None, error_message: str = None,
                          result_data: dict = None, resume_data: dict = None):
        """更新任务状态"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            updates = ['status = ?', 'updated_at = CURRENT_TIMESTAMP']
            params = [status]
            
            if progress is not None:
                updates.append('progress = ?')
                params.append(progress)
            
            if current_step is not None:
                updates.append('current_step = ?')
                params.append(current_step)
            
            if processed_items is not None:
                updates.append('processed_items = ?')
                params.append(processed_items)
            
            if failed_items is not None:
                updates.append('failed_items = ?')
                params.append(failed_items)
            
            if error_message is not None:
                updates.append('error_message = ?')
                params.append(error_message)
            
            if result_data is not None:
                updates.append('result_data = ?')
                params.append(json.dumps(result_data))
            
            if resume_data is not None:
                updates.append('resume_data = ?')
                params.append(json.dumps(resume_data))
            
            # 设置开始时间和完成时间
            if status == 'running':
                updates.append('started_at = CURRENT_TIMESTAMP')
            elif status in ['completed', 'failed']:
                updates.append('completed_at = CURRENT_TIMESTAMP')
            
            params.append(task_id)
            query = f'UPDATE tasks SET {", ".join(updates)} WHERE id = ?'
            cursor.execute(query, params)
            conn.commit()
    
    def get_task(self, task_id: int) -> Optional[Dict]:
        """获取任务信息"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
            row = cursor.fetchone()
            
            if row:
                task = dict(row)
                # 解析JSON字段
                if task['parameters']:
                    task['parameters'] = json.loads(task['parameters'])
                if task['result_data']:
                    task['result_data'] = json.loads(task['result_data'])
                if task['resume_data']:
                    task['resume_data'] = json.loads(task['resume_data'])
                return task
            
            return None
    
    def get_tasks(self, status: str = None, task_type: str = None, limit: int = 100) -> List[Dict]:
        """获取任务列表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = 'SELECT * FROM tasks WHERE 1=1'
            params = []
            
            if status:
                query += ' AND status = ?'
                params.append(status)
            
            if task_type:
                query += ' AND task_type = ?'
                params.append(task_type)
            
            query += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            tasks = []
            for row in cursor.fetchall():
                task = dict(row)
                # 解析JSON字段
                if task['parameters']:
                    task['parameters'] = json.loads(task['parameters'])
                if task['result_data']:
                    task['result_data'] = json.loads(task['result_data'])
                if task['resume_data']:
                    task['resume_data'] = json.loads(task['resume_data'])
                tasks.append(task)
            
            return tasks
    
    def get_resumable_tasks(self) -> List[Dict]:
        """获取可恢复的任务"""
        return self.get_tasks(status='paused')
    
    def pause_task(self, task_id: int, resume_data: dict = None):
        """暂停任务"""
        self.update_task_status(task_id, 'paused', resume_data=resume_data)
        logger.info(f"任务已暂停: {task_id}")
    
    def resume_task(self, task_id: int):
        """恢复任务"""
        task = self.get_task(task_id)
        if task and task['can_resume'] and task['status'] == 'paused':
            self.update_task_status(task_id, 'pending')
            logger.info(f"任务已恢复: {task_id}")
            return task
        return None

# 全局数据库实例
db = DatabaseManager()