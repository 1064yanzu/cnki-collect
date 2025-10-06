/**
 * 任务管理器
 */
class TaskManager {
    constructor(app) {
        this.app = app;
        this.tasks = [];
        this.refreshInterval = null;
        this.autoRefreshEnabled = true;
    }

    /**
     * 加载所有任务
     */
    async loadTasks() {
        try {
            const response = await fetch('/api/tasks');
            const result = await response.json();
            
            if (result.success) {
                this.tasks = result.tasks;
                this.displayTasks(this.tasks);
                this.updateTaskStats();
            } else {
                this.app.addLog('error', `加载任务失败: ${result.error}`);
            }
        } catch (error) {
            this.app.addLog('error', `网络错误: ${error.message}`);
        }
    }

    /**
     * 显示任务列表
     */
    displayTasks(tasks) {
        const tasksList = document.getElementById('tasksList');
        
        if (!tasks || tasks.length === 0) {
            tasksList.innerHTML = `
                <div class="text-center text-muted py-5">
                    <i class="bi bi-list-task" style="font-size: 3rem;"></i>
                    <p class="mt-3">暂无任务</p>
                </div>
            `;
            return;
        }

        tasksList.innerHTML = tasks.map(task => this.createTaskCard(task)).join('');
    }

    /**
     * 创建任务卡片
     */
    createTaskCard(task) {
        const statusClass = this.getStatusClass(task.status);
        const statusText = this.getStatusText(task.status);
        const progressBar = this.createProgressBar(task);
        const literatureTypeInfo = this.getLiteratureTypeInfo(task);
        
        return `
            <div class="card mb-3">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <h6 class="card-title">
                                <i class="bi ${this.getTaskTypeIcon(task.task_type)}"></i>
                                ${task.task_name}
                            </h6>
                            <p class="card-text">
                                <span class="badge bg-${statusClass}">${statusText}</span>
                                <span class="ms-2">类型: ${this.getTaskTypeText(task.task_type)}</span>
                                ${literatureTypeInfo}
                                ${task.total_items > 0 ? `<span class="ms-2">总数: ${task.total_items}</span>` : ''}
                                ${task.processed_items > 0 ? `<span class="ms-2">已处理: ${task.processed_items}</span>` : ''}
                                ${task.failed_items > 0 ? `<span class="ms-2 text-danger">失败: ${task.failed_items}</span>` : ''}
                            </p>
                            ${task.current_step ? `<p class="card-text"><small class="text-muted">当前步骤: ${task.current_step}</small></p>` : ''}
                            <p class="card-text">
                                <small class="text-muted">创建时间: ${new Date(task.created_at).toLocaleString()}</small>
                                ${task.started_at ? `<br><small class="text-muted">开始时间: ${new Date(task.started_at).toLocaleString()}</small>` : ''}
                                ${task.completed_at ? `<br><small class="text-muted">完成时间: ${new Date(task.completed_at).toLocaleString()}</small>` : ''}
                            </p>
                            ${progressBar}
                            ${task.error_message ? `<div class="alert alert-danger mt-2 mb-0"><small>${task.error_message}</small></div>` : ''}
                        </div>
                        <div class="ms-3">
                            ${this.createTaskActions(task)}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * 获取文献类型信息
     */
    getLiteratureTypeInfo(task) {
        if (task.parameters && task.parameters.literature_type) {
            const literatureTypes = {
                'CJFQ': { name: '期刊', color: 'primary' },
                'CDMD': { name: '学位论文', color: 'success' },
                'CPFD': { name: '会议论文', color: 'info' },
                'CCND': { name: '报纸', color: 'warning' },
                'CYFD': { name: '年鉴', color: 'secondary' },
                'CJFN': { name: '图书', color: 'dark' },
                'SCSF': { name: '标准', color: 'danger' },
                'SCPD': { name: '专利', color: 'light' }
            };
            
            const typeInfo = literatureTypes[task.parameters.literature_type];
            if (typeInfo) {
                return `<span class="ms-2"><span class="badge bg-${typeInfo.color}">${typeInfo.name}</span></span>`;
            }
        }
        return '';
    }

    /**
     * 创建进度条
     */
    createProgressBar(task) {
        if (task.status === 'running' && task.progress !== null && task.progress !== undefined) {
            return `
                <div class="progress mt-2">
                    <div class="progress-bar" role="progressbar" 
                         style="width: ${task.progress}%">
                        ${task.progress}%
                    </div>
                </div>
            `;
        }
        return '';
    }

    /**
     * 创建任务操作按钮
     */
    createTaskActions(task) {
        const actions = [];
        
        if (task.status === 'running') {
            actions.push(`
                <button class="btn btn-warning btn-sm me-1" onclick="taskManager.pauseTask(${task.id})">
                    <i class="bi bi-pause-fill"></i> 暂停
                </button>
            `);
            actions.push(`
                <button class="btn btn-danger btn-sm" onclick="taskManager.stopTask(${task.id})">
                    <i class="bi bi-stop-fill"></i> 停止
                </button>
            `);
        } else if (task.status === 'paused' && task.can_resume) {
            actions.push(`
                <button class="btn btn-success btn-sm me-1" onclick="taskManager.resumeTask(${task.id})">
                    <i class="bi bi-play-fill"></i> 恢复
                </button>
            `);
            actions.push(`
                <button class="btn btn-danger btn-sm" onclick="taskManager.stopTask(${task.id})">
                    <i class="bi bi-stop-fill"></i> 停止
                </button>
            `);
        }
        
        actions.push(`
            <button class="btn btn-outline-info btn-sm" onclick="taskManager.viewTaskDetails(${task.id})">
                <i class="bi bi-eye"></i> 详情
            </button>
        `);
        
        return actions.join('');
    }

    /**
     * 获取状态样式类
     */
    getStatusClass(status) {
        const statusMap = {
            'pending': 'secondary',
            'running': 'primary',
            'paused': 'warning',
            'completed': 'success',
            'failed': 'danger'
        };
        return statusMap[status] || 'secondary';
    }

    /**
     * 获取状态文本
     */
    getStatusText(status) {
        const statusMap = {
            'pending': '等待中',
            'running': '运行中',
            'paused': '已暂停',
            'completed': '已完成',
            'failed': '已失败'
        };
        return statusMap[status] || status;
    }

    /**
     * 获取任务类型图标
     */
    getTaskTypeIcon(taskType) {
        const iconMap = {
            'keyword_search': 'bi-search',
            'journal_scrape': 'bi-journal-text',
            'download': 'bi-download',
            'test': 'bi-gear'
        };
        return iconMap[taskType] || 'bi-list-task';
    }

    /**
     * 获取任务类型文本
     */
    getTaskTypeText(taskType) {
        const typeMap = {
            'keyword_search': '关键词搜索',
            'journal_scrape': '期刊爬取',
            'download': '文件下载',
            'test': '测试任务'
        };
        return typeMap[taskType] || taskType;
    }

    /**
     * 更新任务统计
     */
    updateTaskStats() {
        const stats = {
            running: 0,
            paused: 0,
            completed: 0,
            failed: 0
        };

        this.tasks.forEach(task => {
            if (stats.hasOwnProperty(task.status)) {
                stats[task.status]++;
            }
        });

        document.getElementById('runningTasksCount').textContent = stats.running;
        document.getElementById('pausedTasksCount').textContent = stats.paused;
        document.getElementById('completedTasksCount').textContent = stats.completed;
        document.getElementById('failedTasksCount').textContent = stats.failed;
    }

    /**
     * 暂停任务
     */
    async pauseTask(taskId) {
        try {
            const response = await fetch(`/api/tasks/${taskId}/pause`, {
                method: 'POST'
            });
            const result = await response.json();
            
            if (result.success) {
                this.app.addLog('success', '任务已暂停');
                this.loadTasks(); // 刷新任务列表
            } else {
                this.app.addLog('error', `暂停任务失败: ${result.error}`);
            }
        } catch (error) {
            this.app.addLog('error', `网络错误: ${error.message}`);
        }
    }

    /**
     * 恢复任务
     */
    async resumeTask(taskId) {
        try {
            const response = await fetch(`/api/tasks/${taskId}/resume`, {
                method: 'POST'
            });
            const result = await response.json();
            
            if (result.success) {
                this.app.addLog('success', '任务已恢复');
                this.loadTasks(); // 刷新任务列表
            } else {
                this.app.addLog('error', `恢复任务失败: ${result.error}`);
            }
        } catch (error) {
            this.app.addLog('error', `网络错误: ${error.message}`);
        }
    }

    /**
     * 停止任务
     */
    async stopTask(taskId) {
        try {
            const response = await fetch(`/api/tasks/${taskId}/stop`, {
                method: 'POST'
            });
            const result = await response.json();
            
            if (result.success) {
                this.app.addLog('success', '任务已停止');
                this.loadTasks(); // 刷新任务列表
            } else {
                this.app.addLog('error', `停止任务失败: ${result.error}`);
            }
        } catch (error) {
            this.app.addLog('error', `网络错误: ${error.message}`);
        }
    }

    /**
     * 查看任务详情
     */
    async viewTaskDetails(taskId) {
        try {
            const response = await fetch(`/api/tasks/${taskId}`);
            const result = await response.json();
            
            if (result.success) {
                const task = result.task;
                let details = `任务详情:\n`;
                details += `ID: ${task.id}\n`;
                details += `名称: ${task.task_name}\n`;
                details += `类型: ${this.getTaskTypeText(task.task_type)}\n`;
                details += `状态: ${this.getStatusText(task.status)}\n`;
                
                if (task.parameters && task.parameters.literature_type) {
                    const literatureTypes = {
                        'CJFQ': '期刊', 'CDMD': '学位论文', 'CPFD': '会议论文',
                        'CCND': '报纸', 'CYFD': '年鉴', 'CJFN': '图书',
                        'SCSF': '标准', 'SCPD': '专利'
                    };
                    details += `文献类型: ${literatureTypes[task.parameters.literature_type] || task.parameters.literature_type}\n`;
                }
                
                if (task.parameters && task.parameters.keyword) {
                    details += `关键词: ${task.parameters.keyword}\n`;
                }
                
                if (task.total_items > 0) {
                    details += `总项目数: ${task.total_items}\n`;
                    details += `已处理: ${task.processed_items}\n`;
                    details += `失败数: ${task.failed_items}\n`;
                }
                
                if (task.progress !== null) {
                    details += `进度: ${task.progress}%\n`;
                }
                
                if (task.current_step) {
                    details += `当前步骤: ${task.current_step}\n`;
                }
                
                details += `创建时间: ${new Date(task.created_at).toLocaleString()}\n`;
                
                if (task.started_at) {
                    details += `开始时间: ${new Date(task.started_at).toLocaleString()}\n`;
                }
                
                if (task.completed_at) {
                    details += `完成时间: ${new Date(task.completed_at).toLocaleString()}\n`;
                }
                
                if (task.error_message) {
                    details += `错误信息: ${task.error_message}\n`;
                }
                
                alert(details);
            } else {
                this.app.addLog('error', `获取任务详情失败: ${result.error}`);
            }
        } catch (error) {
            this.app.addLog('error', `网络错误: ${error.message}`);
        }
    }

    /**
     * 暂停所有任务
     */
    async pauseAllTasks() {
        const runningTasks = this.tasks.filter(task => task.status === 'running');
        if (runningTasks.length === 0) {
            this.app.addLog('warning', '没有运行中的任务');
            return;
        }

        for (const task of runningTasks) {
            await this.pauseTask(task.id);
        }
    }

    /**
     * 恢复所有任务
     */
    async resumeAllTasks() {
        const pausedTasks = this.tasks.filter(task => task.status === 'paused' && task.can_resume);
        if (pausedTasks.length === 0) {
            this.app.addLog('warning', '没有可恢复的任务');
            return;
        }

        for (const task of pausedTasks) {
            await this.resumeTask(task.id);
        }
    }

    /**
     * 停止所有任务
     */
    async stopAllTasks() {
        const activeTasks = this.tasks.filter(task => ['running', 'paused'].includes(task.status));
        if (activeTasks.length === 0) {
            this.app.addLog('warning', '没有活动的任务');
            return;
        }

        if (!confirm(`确定要停止 ${activeTasks.length} 个任务吗？`)) {
            return;
        }

        for (const task of activeTasks) {
            await this.stopTask(task.id);
        }
    }

    /**
     * 启动自动刷新
     */
    startAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        this.refreshInterval = setInterval(() => {
            if (this.autoRefreshEnabled) {
                this.loadTasks();
            }
        }, 5000); // 每5秒刷新一次
    }

    /**
     * 停止自动刷新
     */
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    /**
     * 初始化任务管理器
     */
    init() {
        // 当切换到任务管理标签页时加载任务
        const tasksTab = document.getElementById('tasks-tab');
        if (tasksTab) {
            tasksTab.addEventListener('shown.bs.tab', () => {
                this.loadTasks();
                this.startAutoRefresh();
            });
            
            tasksTab.addEventListener('hidden.bs.tab', () => {
                this.stopAutoRefresh();
            });
        }
    }
}