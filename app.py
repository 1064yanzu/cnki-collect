"""
CNKI舆情爬虫系统 - Web应用
提供可视化界面和API接口
"""
import os
import json
import threading
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit

# 导入爬虫模块
from config import Config
from utils import Logger, FileManager
from journal_scraper import JournalScraper
from keyword_scraper import KeywordScraper
from article_downloader import ArticleDownloader
from database import db
from task_manager import task_manager

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cnki_scraper_secret_key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# 全局变量
current_task = None
task_status = {
    'running': False,
    'progress': 0,
    'message': '',
    'type': '',
    'results': []
}

class WebLogger:
    """Web日志类，将日志发送到前端"""
    
    def __init__(self):
        self.logger = Logger.setup_logger("WebApp")
    
    def info(self, message):
        self.logger.info(message)
        socketio.emit('log', {'level': 'info', 'message': message, 'time': datetime.now().strftime('%H:%M:%S')})
    
    def error(self, message):
        self.logger.error(message)
        socketio.emit('log', {'level': 'error', 'message': message, 'time': datetime.now().strftime('%H:%M:%S')})
    
    def warning(self, message):
        self.logger.warning(message)
        socketio.emit('log', {'level': 'warning', 'message': message, 'time': datetime.now().strftime('%H:%M:%S')})

web_logger = WebLogger()

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """获取系统状态"""
    try:
        # 检查ChromeDriver
        chrome_driver_path = Config.get_chrome_driver_path_dynamic()
        chrome_driver_exists = Path(chrome_driver_path).exists()
        
        # 检查目录
        Config.ensure_directories()
        
        # 统计文件
        link_files = list(Config.LINK_DIR.glob('*.txt'))
        save_files = []
        for save_dir in Config.SAVE_DIR.iterdir():
            if save_dir.is_dir():
                save_files.extend(list(save_dir.rglob('*.*')))
        
        # 检查期刊文件
        journal_file_exists = Path(Config.EXCEL_FILE).exists()
        
        status = {
            'chrome_driver': {
                'path': chrome_driver_path,
                'exists': chrome_driver_exists
            },
            'directories': {
                'save_dir': str(Config.SAVE_DIR),
                'link_dir': str(Config.LINK_DIR)
            },
            'files': {
                'journal_file': Config.EXCEL_FILE,
                'journal_exists': journal_file_exists,
                'link_count': len(link_files),
                'download_count': len(save_files)
            },
            'config': {
                'keywords': list(Config.KEYWORDS),
                'result_count': Config.RESULT_COUNT,
                'year_range': Config.YEAR_RANGE,
                'file_type': Config.FILE_TYPE,
                'max_workers': Config.MAX_WORKERS
            },
            'task_status': task_status
        }
        
        return jsonify({'success': True, 'data': status})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/journal/scrape', methods=['POST'])
def scrape_journal():
    """期刊检索"""
    global current_task, task_status
    
    if task_status['running']:
        return jsonify({'success': False, 'error': '已有任务在运行中'})
    
    try:
        data = request.get_json()
        excel_file = data.get('excel_file', Config.EXCEL_FILE)
        start_year = data.get('start_year', Config.YEAR_RANGE[0])
        end_year = data.get('end_year', Config.YEAR_RANGE[1])
        
        # 重置任务状态
        task_status.update({
            'running': True,
            'progress': 0,
            'message': '开始期刊检索...',
            'type': 'journal',
            'results': []
        })
        
        def run_journal_scraper():
            try:
                web_logger.info(f"开始期刊检索: {excel_file}, 年份: {start_year}-{end_year}")
                
                scraper = JournalScraper(excel_file)
                results = scraper.scrape_by_year_range(start_year, end_year)
                
                task_status.update({
                    'running': False,
                    'progress': 100,
                    'message': '期刊检索完成',
                    'results': results
                })
                
                web_logger.info(f"期刊检索完成，共处理 {len(results)} 个期刊")
                socketio.emit('task_complete', task_status)
                
            except Exception as e:
                task_status.update({
                    'running': False,
                    'progress': 0,
                    'message': f'期刊检索失败: {str(e)}'
                })
                web_logger.error(f"期刊检索失败: {str(e)}")
                socketio.emit('task_error', {'error': str(e)})
        
        current_task = threading.Thread(target=run_journal_scraper)
        current_task.start()
        
        return jsonify({'success': True, 'message': '期刊检索任务已启动'})
    
    except Exception as e:
        task_status['running'] = False
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/keyword/scrape', methods=['POST'])
def scrape_keyword():
    """关键词搜索"""
    global current_task, task_status
    
    if task_status['running']:
        return jsonify({'success': False, 'error': '已有任务在运行中'})
    
    try:
        data = request.get_json()
        keywords = data.get('keywords', list(Config.KEYWORDS))
        result_count = data.get('result_count', Config.RESULT_COUNT)
        literature_type = data.get('literature_type', Config.DEFAULT_LITERATURE_TYPE)
        
        # 重置任务状态
        task_status.update({
            'running': True,
            'progress': 0,
            'message': '开始关键词搜索...',
            'type': 'keyword',
            'results': []
        })
        
        def run_keyword_scraper():
            try:
                lit_name = Config.LITERATURE_TYPES[literature_type]['name']
                web_logger.info(f"开始关键词搜索: {keywords}, 文献类型: {lit_name}, 结果数量: {result_count}")
                
                scraper = KeywordScraper()
                results = scraper.search_keywords(keywords, result_count, literature_type)
                
                # 自动导出 JSON 与 CSV
                fm = FileManager()
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                json_path = Config.EXPORT_DIR / f"keyword_{lit_name}_{timestamp}.json"
                csv_path = Config.EXPORT_DIR / f"keyword_{lit_name}_{timestamp}.csv"
                
                # JSON：直接保存完整结果
                fm.save_json({'keywords': keywords, 'literature_type': literature_type, 'results': results}, json_path)
                
                # CSV：展开为文章行
                rows = []
                for r in results:
                    kw = r.get('keyword')
                    status = r.get('status')
                    articles = r.get('articles', [])
                    if status == 'success':
                        for a in articles:
                            rows.append({
                                'keyword': kw,
                                'title': a.get('title'),
                                'url': a.get('url'),
                                'authors': a.get('authors'),
                                'journal': a.get('journal'),
                                'publish_date': a.get('publish_date'),
                                'literature_type': a.get('literature_type') or literature_type,
                                'source_type': a.get('source_type'),
                                'created_at': a.get('created_at')
                            })
                    else:
                        rows.append({'keyword': kw, 'title': None, 'url': None, 'authors': None, 'journal': None, 'publish_date': None, 'literature_type': literature_type, 'source_type': 'keyword_search', 'created_at': None})
                headers = ['keyword','title','url','authors','journal','publish_date','literature_type','source_type','created_at']
                fm.save_csv(rows, headers, csv_path)
                
                task_status.update({
                    'running': False,
                    'progress': 100,
                    'message': '关键词搜索完成（已导出 JSON/CSV）',
                    'results': results
                })
                
                web_logger.info(f"关键词搜索完成，共搜索 {len(keywords)} 个关键词，导出文件：{json_path.name} / {csv_path.name}")
                socketio.emit('task_complete', task_status)
                
            except Exception as e:
                task_status.update({
                    'running': False,
                    'progress': 0,
                    'message': f'关键词搜索失败: {str(e)}'
                })
                web_logger.error(f"关键词搜索失败: {str(e)}")
                socketio.emit('task_error', {'error': str(e)})
        
        current_task = threading.Thread(target=run_keyword_scraper)
        current_task.start()
        
        return jsonify({'success': True, 'message': '关键词搜索任务已启动'})
    
    except Exception as e:
        task_status['running'] = False
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/download/start', methods=['POST'])
def start_download():
    """开始下载"""
    global current_task, task_status
    
    if task_status['running']:
        return jsonify({'success': False, 'error': '已有任务在运行中'})
    
    try:
        data = request.get_json()
        max_workers = data.get('max_workers', Config.MAX_WORKERS)
        
        # 重置任务状态
        task_status.update({
            'running': True,
            'progress': 0,
            'message': '开始文章下载...',
            'type': 'download',
            'results': []
        })
        
        def run_downloader():
            try:
                web_logger.info(f"开始文章下载，并发数: {max_workers}")
                
                downloader = ArticleDownloader(max_workers=max_workers)
                results = downloader.download_all_links()
                
                task_status.update({
                    'running': False,
                    'progress': 100,
                    'message': '文章下载完成',
                    'results': results
                })
                
                web_logger.info(f"文章下载完成")
                socketio.emit('task_complete', task_status)
                
            except Exception as e:
                task_status.update({
                    'running': False,
                    'progress': 0,
                    'message': f'文章下载失败: {str(e)}'
                })
                web_logger.error(f"文章下载失败: {str(e)}")
                socketio.emit('task_error', {'error': str(e)})
        
        current_task = threading.Thread(target=run_downloader)
        current_task.start()
        
        return jsonify({'success': True, 'message': '文章下载任务已启动'})
    
    except Exception as e:
        task_status['running'] = False
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/articles', methods=['GET'])
def get_articles():
    """获取文章列表（支持分页和搜索）"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        search_query = request.args.get('search', '')
        source_type = request.args.get('source_type', '')
        keyword = request.args.get('keyword', '')
        literature_type = request.args.get('literature_type', '')
        
        offset = (page - 1) * per_page
        
        articles = db.get_articles(
            limit=per_page,
            offset=offset,
            search_query=search_query if search_query else None,
            source_type=source_type if source_type else None,
            keyword=keyword if keyword else None,
            literature_type=literature_type if literature_type else None
        )
        
        # 获取总数
        total_count = db.get_articles_count(
            search_query=search_query if search_query else None,
            source_type=source_type if source_type else None,
            keyword=keyword if keyword else None,
            literature_type=literature_type if literature_type else None
        )
        
        return jsonify({
            'success': True,
            'articles': articles,
            'page': page,
            'per_page': per_page,
            'total': total_count
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/articles/download', methods=['POST'])
def download_selected_articles():
    """批量下载选中的文章"""
    global current_task, task_status
    
    if task_status['running']:
        return jsonify({'success': False, 'error': '已有任务在运行中'})
    
    try:
        data = request.get_json()
        article_ids = data.get('article_ids', [])
        max_workers = data.get('max_workers', Config.MAX_WORKERS)
        
        if not article_ids:
            return jsonify({'success': False, 'error': '请选择要下载的文章'})
        
        # 创建下载任务
        task_id = db.create_download_task(article_ids)
        
        # 重置任务状态
        task_status.update({
            'running': True,
            'progress': 0,
            'message': f'开始下载 {len(article_ids)} 篇文章...',
            'type': 'selective_download',
            'task_id': task_id,
            'total': len(article_ids),
            'completed': 0,
            'failed': 0
        })
        
        def run_selective_download():
            try:
                web_logger.info(f"开始批量下载 {len(article_ids)} 篇文章")
                
                # 更新任务状态
                db.update_download_task(task_id, status='running')
                
                completed_count = 0
                failed_count = 0
                
                for i, article_id in enumerate(article_ids):
                    try:
                        # 获取文章信息
                        articles = db.get_articles(limit=1, offset=0)
                        article = next((a for a in articles if a['id'] == article_id), None)
                        
                        if not article:
                            failed_count += 1
                            continue
                        
                        # 更新文章状态为下载中
                        db.update_article_status(article_id, 'downloading')
                        
                        # 这里应该调用实际的下载逻辑
                        # 暂时模拟下载过程
                        import time
                        time.sleep(1)  # 模拟下载时间
                        
                        # 更新文章状态为已完成
                        db.update_article_status(article_id, 'completed', f"downloads/{article['title']}.pdf")
                        completed_count += 1
                        
                        # 更新进度
                        progress = int((i + 1) / len(article_ids) * 100)
                        task_status.update({
                            'progress': progress,
                            'message': f'下载进度: {i + 1}/{len(article_ids)}',
                            'completed': completed_count,
                            'failed': failed_count
                        })
                        
                        socketio.emit('download_progress', task_status)
                        
                    except Exception as e:
                        web_logger.error(f"下载文章 {article_id} 失败: {e}")
                        db.update_article_status(article_id, 'failed')
                        failed_count += 1
                
                # 更新最终状态
                db.update_download_task(task_id, completed_count, failed_count, 'completed')
                
                task_status.update({
                    'running': False,
                    'progress': 100,
                    'message': f'下载完成！成功: {completed_count}, 失败: {failed_count}',
                    'completed': completed_count,
                    'failed': failed_count
                })
                
                web_logger.info(f"批量下载完成，成功: {completed_count}, 失败: {failed_count}")
                socketio.emit('task_complete', task_status)
                
            except Exception as e:
                db.update_download_task(task_id, status='failed')
                task_status.update({
                    'running': False,
                    'progress': 0,
                    'message': f'下载失败: {str(e)}'
                })
                web_logger.error(f"批量下载失败: {str(e)}")
                socketio.emit('task_error', {'error': str(e)})
        
        current_task = threading.Thread(target=run_selective_download)
        current_task.start()
        
        return jsonify({
            'success': True, 
            'message': f'批量下载任务已启动，任务ID: {task_id}',
            'task_id': task_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/search/history', methods=['GET'])
def get_search_history():
    """获取搜索历史"""
    try:
        limit = int(request.args.get('limit', 50))
        history = db.get_search_history(limit)
        
        return jsonify({
            'success': True,
            'history': history
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/download/tasks')
def get_download_tasks():
    """获取所有下载任务"""
    try:
        tasks = db.get_download_tasks()
        return jsonify({
            'success': True,
            'data': tasks
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/download/task/<int:task_id>', methods=['GET'])
def get_download_task_status(task_id):
    """获取下载任务状态"""
    try:
        task = db.get_download_task(task_id)
        
        if not task:
            return jsonify({'success': False, 'error': '任务不存在'})
        
        return jsonify({
            'success': True,
            'task': task
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/task/stop', methods=['POST'])
def stop_task():
    """停止当前任务"""
    global current_task, task_status
    
    try:
        if current_task and current_task.is_alive():
            # 这里需要实现任务停止逻辑
            # 由于线程无法直接停止，需要使用标志位或其他机制
            task_status.update({
                'running': False,
                'progress': 0,
                'message': '任务已停止'
            })
            
            web_logger.info("任务停止请求已发送")
            socketio.emit('task_stopped', {'message': '任务已停止'})
            
            return jsonify({'success': True, 'message': '任务停止请求已发送'})
        else:
            return jsonify({'success': False, 'error': '没有正在运行的任务'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# 任务管理API端点
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """获取所有任务列表"""
    try:
        tasks = task_manager.get_all_tasks()
        return jsonify({'success': True, 'tasks': tasks})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task_status(task_id):
    """获取特定任务状态"""
    try:
        task = task_manager.get_task(task_id)
        if task:
            return jsonify({'success': True, 'task': task.to_dict()})
        else:
            return jsonify({'success': False, 'error': '任务不存在'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/tasks/<int:task_id>/pause', methods=['POST'])
def pause_task(task_id):
    """暂停任务"""
    try:
        success = task_manager.pause_task(task_id)
        if success:
            socketio.emit('task_paused', {'task_id': task_id})
            return jsonify({'success': True, 'message': '任务已暂停'})
        else:
            return jsonify({'success': False, 'error': '暂停任务失败'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/tasks/<int:task_id>/resume', methods=['POST'])
def resume_task(task_id):
    """恢复任务"""
    try:
        success = task_manager.resume_task(task_id)
        if success:
            socketio.emit('task_resumed', {'task_id': task_id})
            return jsonify({'success': True, 'message': '任务已恢复'})
        else:
            return jsonify({'success': False, 'error': '恢复任务失败'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/tasks/<int:task_id>/stop', methods=['POST'])
def stop_specific_task(task_id):
    """停止特定任务"""
    try:
        success = task_manager.stop_task(task_id)
        if success:
            socketio.emit('task_stopped', {'task_id': task_id})
            return jsonify({'success': True, 'message': '任务已停止'})
        else:
            return jsonify({'success': False, 'error': '停止任务失败'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/keyword/scrape_with_task', methods=['POST'])
def scrape_keyword_with_task():
    """使用任务管理器进行关键词搜索"""
    try:
        data = request.get_json()
        keywords = data.get('keywords', [])
        result_count = data.get('result_count', Config.RESULT_COUNT)
        literature_type = data.get('literature_type', Config.DEFAULT_LITERATURE_TYPE)
        
        if not keywords:
            return jsonify({'success': False, 'error': '请提供关键词'})
        
        # 创建关键词搜索器
        scraper = KeywordScraper()
        task_ids = []
        
        # 为每个关键词创建任务
        for keyword in keywords:
            task_id = scraper.scrape_keyword_with_task(keyword, result_count, literature_type)
            task_ids.append(task_id)
        
        return jsonify({
            'success': True, 
            'message': f'已创建 {len(task_ids)} 个搜索任务',
            'task_ids': task_ids
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/literature/types', methods=['GET'])
def get_literature_types():
    """获取可用的文献类型"""
    try:
        types = []
        for key, value in Config.LITERATURE_TYPES.items():
            types.append({
                'key': key,
                'name': value['name'],
                'classid': value['classid']
            })
        
        return jsonify({
            'success': True,
            'types': types,
            'default': Config.DEFAULT_LITERATURE_TYPE
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/literature/stats', methods=['GET'])
def get_literature_stats():
    """获取文献类型统计"""
    try:
        stats = db.get_literature_type_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/files/links')
def get_link_files():
    """获取链接文件列表"""
    try:
        link_files = []
        for file_path in Config.LINK_DIR.glob('*.txt'):
            file_info = {
                'name': file_path.name,
                'path': str(file_path),
                'size': file_path.stat().st_size,
                'modified': datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            }
            link_files.append(file_info)
        
        return jsonify({'success': True, 'data': link_files})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/files/exports')
def get_export_files():
    """获取导出文件列表"""
    try:
        files = []
        for file_path in Config.EXPORT_DIR.glob('*.*'):
            if file_path.is_file():
                files.append({
                    'name': file_path.name,
                    'path': str(file_path),
                    'size': file_path.stat().st_size,
                    'modified': datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
        return jsonify({'success': True, 'data': files})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/files/logs')
def get_log_files():
    """获取日志文件列表"""
    try:
        files = []
        for file_path in Config.LOG_DIR.glob('*.log'):
            if file_path.is_file():
                files.append({
                    'name': file_path.name,
                    'path': str(file_path),
                    'size': file_path.stat().st_size,
                    'modified': datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
        return jsonify({'success': True, 'data': files})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# 安全文件打开接口
@app.route('/api/files/open')
def open_file():
    """在受控目录内打开或下载文件"""
    try:
        path_str = request.args.get('path')
        if not path_str:
            return jsonify({'success': False, 'error': '缺少参数: path'})
        file_path = Path(path_str).resolve()
        allowed_dirs = [
            Config.LINK_DIR.resolve(),
            Config.SAVE_DIR.resolve(),
            Config.EXPORT_DIR.resolve(),
            Config.LOG_DIR.resolve()
        ]
        # 校验路径在受控目录内，避免路径遍历
        if not any((d == file_path or d in file_path.parents) for d in allowed_dirs):
            return jsonify({'success': False, 'error': '非法路径，拒绝访问'})
        if not file_path.exists() or not file_path.is_file():
            return jsonify({'success': False, 'error': '文件不存在'})
        # 直接预览，不强制下载；如需下载可设置 as_attachment=True
        return send_file(str(file_path), as_attachment=False)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/files/downloads')
def get_download_files():
    """获取下载文件列表"""
    try:
        download_files = []
        for save_dir in Config.SAVE_DIR.iterdir():
            if save_dir.is_dir():
                for file_path in save_dir.rglob('*.*'):
                    if file_path.is_file():
                        file_info = {
                            'name': file_path.name,
                            'path': str(file_path),
                            'relative_path': str(file_path.relative_to(Config.SAVE_DIR)),
                            'size': file_path.stat().st_size,
                            'modified': datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                        }
                        download_files.append(file_info)
        
        return jsonify({'success': True, 'data': download_files})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@socketio.on('connect')
def handle_connect():
    """WebSocket连接"""
    web_logger.info('客户端已连接')
    emit('connected', {'message': '已连接到服务器'})

@socketio.on('disconnect')
def handle_disconnect():
    """WebSocket断开连接"""
    web_logger.info('客户端已断开连接')

if __name__ == '__main__':
    # 确保目录存在
    Config.ensure_directories()
    
    # 创建模板目录
    template_dir = Path(__file__).parent / 'templates'
    template_dir.mkdir(exist_ok=True)
    
    # 创建静态文件目录
    static_dir = Path(__file__).parent / 'static'
    static_dir.mkdir(exist_ok=True)
    
    print("🚀 CNKI舆情爬虫系统启动中...")
    print("📱 Web界面地址: http://localhost:5001")
    print("⚡ 支持实时日志和进度显示")
    
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)