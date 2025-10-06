/**
 * CNKI舆情爬虫系统 - 前端应用主文件
 * 负责管理整个应用的状态和核心功能
 */

class CNKIApp {
    constructor() {
        this.socket = null;
        this.selectedArticles = new Set();
        this.currentArticles = [];
        this.currentPage = 1;
        this.totalPages = 1;
        this.articlesPerPage = 10;
        
        this.init();
    }
    
    init() {
        this.initWebSocket();
        this.bindEvents();
        this.loadInitialData();
    }
    
    initWebSocket() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('WebSocket连接成功');
        });
        
        this.socket.on('disconnect', () => {
            console.log('WebSocket连接断开');
        });
        
        this.socket.on('task_complete', (data) => {
            this.handleTaskComplete(data);
        });
        
        this.socket.on('log', (data) => {
            this.addLog(data.level, data.message);
        });
        
        this.socket.on('progress', (data) => {
            this.updateProgress(data.progress, data.message);
        });
    }
    
    bindEvents() {
        // 标签切换事件
        document.addEventListener('shown.bs.tab', (event) => {
            const targetId = event.target.getAttribute('data-bs-target');
            this.handleTabSwitch(targetId);
        });
        
        // 搜索事件
        const articleSearch = document.getElementById('articleSearch');
        if (articleSearch) {
            articleSearch.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.searchArticles();
                }
            });
        }
        
        // 关键词筛选事件
        const keywordFilter = document.getElementById('keywordFilter');
        if (keywordFilter) {
            keywordFilter.addEventListener('change', () => {
                this.searchArticles();
            });
        }
    }
    
    loadInitialData() {
        // 初始数据加载将由各个管理器负责
        console.log('CNKIApp初始化完成');
    }
    
    handleTabSwitch(targetId) {
        switch (targetId) {
            case '#articles-panel':
                this.loadArticles();
                break;
            case '#history-panel':
                this.loadSearchHistory();
                break;
            case '#download-panel':
                this.loadDownloadTasks();
                break;
        }
    }
    
    handleTaskComplete(data) {
        this.addLog('success', `任务完成: ${data.type}`);
        
        if (data.type === 'keyword') {
            // 关键词搜索完成，刷新搜索历史和文章列表
            if (searchManager) {
                searchManager.loadSearchHistory();
            }
            if (articleManager) {
                articleManager.loadArticles();
            }
        }
    }
    
    addLog(level, message) {
        const logContainer = document.getElementById('logContainer');
        if (!logContainer) return;
        
        const timestamp = new Date().toLocaleTimeString();
        const logClass = {
            'info': 'text-info',
            'success': 'text-success',
            'error': 'text-danger',
            'warning': 'text-warning'
        }[level] || 'text-muted';
        
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${logClass}`;
        logEntry.innerHTML = `<span class="timestamp">[${timestamp}]</span> ${message}`;
        
        logContainer.appendChild(logEntry);
        logContainer.scrollTop = logContainer.scrollHeight;
        
        // 限制日志条数
        const logs = logContainer.children;
        if (logs.length > 100) {
            logContainer.removeChild(logs[0]);
        }
    }
    
    updateProgress(progress, message) {
        const progressBar = document.querySelector('.progress-bar');
        const progressText = document.getElementById('progressText');
        
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
            progressBar.textContent = `${progress}%`;
        }
        
        if (progressText && message) {
            progressText.textContent = message;
        }
    }
}