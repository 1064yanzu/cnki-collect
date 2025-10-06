/**
 * 搜索管理模块
 * 负责关键词搜索和搜索历史功能
 */

class SearchManager {
    constructor(app) {
        this.app = app;
    }
    
    async startKeywordSearch() {
        const keywordsText = document.getElementById('keywords').value;
        const keywords = keywordsText.split('\n').filter(k => k.trim());
        
        if (keywords.length === 0) {
            this.app.addLog('error', '请输入至少一个关键词');
            return;
        }
        
        const data = {
            keywords: keywords,
            result_count: parseInt(document.getElementById('resultCount').value)
        };
        
        await this.startTask('/api/keyword/scrape', data, '关键词搜索');
    }
    
    async startTask(url, data, taskName) {
        try {
            this.app.addLog('info', `正在启动${taskName}...`);
            
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.app.addLog('success', `${taskName}已启动`);
            } else {
                this.app.addLog('error', `启动${taskName}失败: ${result.error}`);
            }
        } catch (error) {
            this.app.addLog('error', `网络错误: ${error.message}`);
        }
    }
    
    async loadSearchHistory() {
        try {
            const response = await fetch('/api/search/history');
            const result = await response.json();
            
            if (result.success) {
                this.displaySearchHistory(result.history);
            } else {
                this.app.addLog('error', `加载搜索历史失败: ${result.error}`);
            }
        } catch (error) {
            this.app.addLog('error', `网络错误: ${error.message}`);
        }
    }
    
    displaySearchHistory(history) {
        const container = document.getElementById('searchHistoryList');
        
        if (history.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-5">
                    <i class="bi bi-clock-history" style="font-size: 3rem;"></i>
                    <p class="mt-3">暂无搜索历史</p>
                </div>
            `;
            return;
        }
        
        const historyHtml = history.map(item => `
            <div class="search-history-item">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <div class="fw-bold">${item.keyword}</div>
                        <div class="text-muted small">
                            搜索时间: ${new Date(item.search_time).toLocaleString()}
                        </div>
                        <div class="text-muted small">
                            结果数量: ${item.result_count} 篇文章
                        </div>
                    </div>
                    <div class="ms-3">
                        <button class="btn btn-outline-primary btn-sm" onclick="searchManager.searchAgain('${item.keyword}')">
                            <i class="bi bi-arrow-repeat"></i> 重新搜索
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = historyHtml;
    }
    
    searchAgain(keyword) {
        document.getElementById('keywords').value = keyword;
        const searchTab = document.getElementById('search-tab');
        searchTab.click();
    }
    
    async startJournalScrape() {
        const data = {
            journal_file: document.getElementById('journalFile').value,
            start_year: parseInt(document.getElementById('startYear').value),
            end_year: parseInt(document.getElementById('endYear').value)
        };
        
        await this.startTask('/api/journal/scrape', data, '期刊检索');
    }
}