/**
 * 下载管理模块
 * 负责下载任务的管理和监控
 */

class DownloadManager {
    constructor(app) {
        this.app = app;
    }
    
    async loadTasks() {
        try {
            const response = await fetch('/api/download/tasks');
            const result = await response.json();
            
            if (result.success) {
                this.displayTasks(result.data);
            } else {
                this.app.addLog('error', `加载下载任务失败: ${result.error}`);
            }
        } catch (error) {
            this.app.addLog('error', `网络错误: ${error.message}`);
        }
    }
    
    displayTasks(tasks) {
        const container = document.getElementById('downloadTasksList');
        
        if (tasks.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-5">
                    <i class="bi bi-download" style="font-size: 3rem;"></i>
                    <p class="mt-3">暂无下载任务</p>
                </div>
            `;
            return;
        }
        
        const tasksHtml = tasks.map(task => this.createTaskCard(task)).join('');
        container.innerHTML = tasksHtml;
    }
    
    createTaskCard(task) {
        const statusClass = task.status === 'completed' ? 'success' : 
                          task.status === 'failed' ? 'danger' : 'primary';
        const statusText = task.status === 'completed' ? '已完成' : 
                         task.status === 'failed' ? '失败' : '进行中';
        
        const progressBar = task.status === 'running' ? `
            <div class="progress mt-2">
                <div class="progress-bar" role="progressbar" 
                     style="width: ${(task.completed_articles / task.total_articles * 100).toFixed(1)}%">
                    ${(task.completed_articles / task.total_articles * 100).toFixed(1)}%
                </div>
            </div>
        ` : '';
        
        return `
            <div class="card mb-3">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <h6 class="card-title">下载任务 #${task.id}</h6>
                            <p class="card-text">
                                <span class="badge bg-${statusClass}">${statusText}</span>
                                <span class="ms-2">文章数量: ${task.total_articles}</span>
                                ${task.status === 'running' ? `<span class="ms-2">已完成: ${task.completed_articles}</span>` : ''}
                            </p>
                            <p class="card-text">
                                <small class="text-muted">创建时间: ${new Date(task.created_at).toLocaleString()}</small>
                                ${task.completed_at ? `<br><small class="text-muted">完成时间: ${new Date(task.completed_at).toLocaleString()}</small>` : ''}
                            </p>
                            ${progressBar}
                        </div>
                        <div class="ms-3">
                            <button class="btn btn-outline-info btn-sm" onclick="downloadManager.viewTaskDetails(${task.id})">
                                <i class="bi bi-eye"></i> 详情
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    async viewTaskDetails(taskId) {
        try {
            const response = await fetch(`/api/download/task/${taskId}`);
            const result = await response.json();
            
            if (result.success) {
                const task = result.data;
                alert(`任务详情:\n状态: ${task.status}\n总文章数: ${task.total_articles}\n已完成: ${task.completed_articles}\n创建时间: ${new Date(task.created_at).toLocaleString()}`);
            } else {
                this.app.addLog('error', `获取任务详情失败: ${result.error}`);
            }
        } catch (error) {
            this.app.addLog('error', `网络错误: ${error.message}`);
        }
    }
    
    async startDownload() {
        const data = {
            max_workers: parseInt(document.getElementById('maxWorkers').value)
        };
        
        try {
            this.app.addLog('info', '正在启动下载任务...');
            
            const response = await fetch('/api/download/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.app.addLog('success', '下载任务已启动');
                this.loadTasks();
            } else {
                this.app.addLog('error', `启动下载失败: ${result.error}`);
            }
        } catch (error) {
            this.app.addLog('error', `网络错误: ${error.message}`);
        }
    }
    
    async stopDownload() {
        try {
            const response = await fetch('/api/download/stop', {
                method: 'POST'
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.app.addLog('info', '下载任务已停止');
                this.loadTasks();
            } else {
                this.app.addLog('error', `停止下载失败: ${result.error}`);
            }
        } catch (error) {
            this.app.addLog('error', `网络错误: ${error.message}`);
        }
    }
}