/**
 * 文章管理模块
 * 负责文章列表、搜索、选择和下载功能
 */

class ArticleManager {
    constructor(app) {
        this.app = app;
    }
    
    async loadArticles(page = 1, search = '', keyword = '') {
        try {
            const params = new URLSearchParams({
                page: page,
                per_page: this.app.articlesPerPage,
                search: search,
                keyword: keyword
            });
            
            const response = await fetch(`/api/articles?${params}`);
            const result = await response.json();
            
            if (result.success) {
                this.app.currentArticles = result.articles;
                this.app.currentPage = result.page;
                this.app.totalPages = Math.ceil(result.total / result.per_page);
                
                this.displayArticles(this.app.currentArticles);
                this.updatePagination();
                // 从文章数据中提取关键词
                const keywords = [...new Set(result.articles.map(article => article.keyword).filter(k => k))];
                this.updateKeywordFilter(keywords);
            } else {
                this.app.addLog('error', `加载文章失败: ${result.error}`);
            }
        } catch (error) {
            this.app.addLog('error', `网络错误: ${error.message}`);
        }
    }
    
    displayArticles(articles) {
        const container = document.getElementById('articlesList');
        
        if (articles.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-5">
                    <i class="bi bi-file-text" style="font-size: 3rem;"></i>
                    <p class="mt-3">暂无文章数据，请先进行关键词搜索</p>
                </div>
            `;
            return;
        }
        
        const articlesHtml = articles.map(article => this.createArticleCard(article)).join('');
        container.innerHTML = articlesHtml;
        this.updateSelectionToolbar();
    }
    
    createArticleCard(article) {
        const isSelected = this.app.selectedArticles.has(article.id);
        const downloadedBadge = article.status === 'downloaded' ? 
            '<span class="tag" style="background: #28a745; color: white;">已下载</span>' : '';
        
        return `
            <div class="article-card ${isSelected ? 'selected' : ''}" data-id="${article.id}">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <div class="article-title">${article.title}</div>
                        <div class="article-meta">
                            <span><i class="bi bi-person"></i> ${article.authors || '未知作者'}</span>
                            <span class="ms-3"><i class="bi bi-journal"></i> ${article.journal || '未知期刊'}</span>
                            <span class="ms-3"><i class="bi bi-calendar"></i> ${article.publish_date || '未知日期'}</span>
                        </div>
                        <div class="article-tags">
                            <span class="tag keyword">${article.keyword}</span>
                            ${downloadedBadge}
                        </div>
                        ${article.abstract ? `<div class="article-abstract">${article.abstract}</div>` : ''}
                    </div>
                    <div class="ms-3">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" ${isSelected ? 'checked' : ''} 
                                   onchange="articleManager.toggleSelection(${article.id})">
                        </div>
                    </div>
                </div>
                <div class="mt-2">
                    <a href="${article.url}" target="_blank" class="btn btn-outline-primary btn-sm">
                        <i class="bi bi-link-45deg"></i> 查看原文
                    </a>
                    <button class="btn btn-success btn-sm ms-2" onclick="articleManager.downloadSingle(${article.id})">
                        <i class="bi bi-download"></i> 下载
                    </button>
                </div>
            </div>
        `;
    }
    
    updatePagination() {
        const pagination = document.getElementById('articlesPagination');
        
        if (this.app.totalPages <= 1) {
            pagination.innerHTML = '';
            return;
        }
        
        let paginationHtml = '';
        
        // 上一页
        if (this.app.currentPage > 1) {
            paginationHtml += `<li class="page-item">
                <a class="page-link" href="#" onclick="articleManager.loadArticles(${this.app.currentPage - 1})">上一页</a>
            </li>`;
        }
        
        // 页码
        const startPage = Math.max(1, this.app.currentPage - 2);
        const endPage = Math.min(this.app.totalPages, this.app.currentPage + 2);
        
        for (let i = startPage; i <= endPage; i++) {
            paginationHtml += `<li class="page-item ${i === this.app.currentPage ? 'active' : ''}">
                <a class="page-link" href="#" onclick="articleManager.loadArticles(${i})">${i}</a>
            </li>`;
        }
        
        // 下一页
        if (this.app.currentPage < this.app.totalPages) {
            paginationHtml += `<li class="page-item">
                <a class="page-link" href="#" onclick="articleManager.loadArticles(${this.app.currentPage + 1})">下一页</a>
            </li>`;
        }
        
        pagination.innerHTML = paginationHtml;
    }
    
    updateKeywordFilter(keywords) {
        const select = document.getElementById('keywordFilter');
        const currentValue = select.value;
        
        select.innerHTML = '<option value="">所有关键词</option>';
        keywords.forEach(keyword => {
            select.innerHTML += `<option value="${keyword}" ${keyword === currentValue ? 'selected' : ''}>${keyword}</option>`;
        });
    }
    
    searchArticles() {
        const search = document.getElementById('articleSearch').value;
        const keyword = document.getElementById('keywordFilter').value;
        this.loadArticles(1, search, keyword);
    }
    
    toggleSelection(articleId) {
        if (this.app.selectedArticles.has(articleId)) {
            this.app.selectedArticles.delete(articleId);
        } else {
            this.app.selectedArticles.add(articleId);
        }
        this.updateSelectionToolbar();
        
        // 更新文章卡片样式
        const card = document.querySelector(`[data-id="${articleId}"]`);
        if (card) {
            card.classList.toggle('selected', this.app.selectedArticles.has(articleId));
        }
    }
    
    selectAll() {
        this.app.currentArticles.forEach(article => {
            this.app.selectedArticles.add(article.id);
        });
        this.displayArticles(this.app.currentArticles);
    }
    
    clearSelection() {
        this.app.selectedArticles.clear();
        this.displayArticles(this.app.currentArticles);
    }
    
    updateSelectionToolbar() {
        const toolbar = document.getElementById('selectionToolbar');
        const countSpan = document.getElementById('selectedCount');
        
        if (this.app.selectedArticles.size > 0) {
            toolbar.style.display = 'block';
            countSpan.textContent = `已选择 ${this.app.selectedArticles.size} 篇文章`;
        } else {
            toolbar.style.display = 'none';
        }
    }
    
    async downloadSelected() {
        if (this.app.selectedArticles.size === 0) {
            this.app.addLog('error', '请先选择要下载的文章');
            return;
        }
        
        const articleIds = Array.from(this.app.selectedArticles);
        
        try {
            const response = await fetch('/api/articles/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    article_ids: articleIds,
                    max_workers: parseInt(document.getElementById('maxWorkers').value)
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.app.addLog('info', `已启动下载任务，共 ${articleIds.length} 篇文章`);
                this.clearSelection();
                downloadManager.loadTasks();
                
                // 切换到下载管理标签
                const downloadTab = document.getElementById('download-tab');
                downloadTab.click();
            } else {
                this.app.addLog('error', `启动下载失败: ${result.error}`);
            }
        } catch (error) {
            this.app.addLog('error', `网络错误: ${error.message}`);
        }
    }
    
    async downloadSingle(articleId) {
        try {
            const response = await fetch('/api/articles/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    article_ids: [articleId],
                    max_workers: 1
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.app.addLog('info', '已启动单篇文章下载');
                downloadManager.loadTasks();
            } else {
                this.app.addLog('error', `启动下载失败: ${result.error}`);
            }
        } catch (error) {
            this.app.addLog('error', `网络错误: ${error.message}`);
        }
    }
}

// 全局文章管理器实例