/**
 * 搜索管理模块
 * 负责关键词搜索和搜索历史功能
 */

class SearchManager {
    constructor(app) {
        this.app = app;
        // 确保DOM加载完成后再加载文献类型
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.loadLiteratureTypes();
            });
        } else {
            this.loadLiteratureTypes();
        }
    }
    
    async loadLiteratureTypes() {
        try {
            const response = await fetch('/api/literature/types');
            const result = await response.json();
            
            if (result.success) {
                this.displayLiteratureTypes(result.types, result.default);
            } else {
                this.app.addLog('error', `加载文献类型失败: ${result.error}`);
            }
        } catch (error) {
            this.app.addLog('error', `网络错误: ${error.message}`);
        }
    }
    
    displayLiteratureTypes(types, defaultType) {
        const select = document.getElementById('literatureType');
        
        if (!select) {
            console.warn('文献类型选择器元素未找到，稍后重试...');
            // 延迟重试
            setTimeout(() => {
                this.displayLiteratureTypes(types, defaultType);
            }, 500);
            return;
        }
        
        const optionsHtml = types.map(type => 
            `<option value="${type.key}" ${type.key === defaultType ? 'selected' : ''}>${type.name}</option>`
        ).join('');
        
        select.innerHTML = optionsHtml;
    }
    
    async startKeywordSearch() {
        const keywordsText = document.getElementById('keywords').value;
        const keywords = keywordsText.split('\n').filter(k => k.trim());
        
        if (keywords.length === 0) {
            this.app.addLog('error', '请输入至少一个关键词');
            return;
        }
        
        const literatureType = document.getElementById('literatureType').value;
        const literatureTypeName = document.getElementById('literatureType').selectedOptions[0].text;
        
        const data = {
            keywords: keywords,
            result_count: parseInt(document.getElementById('resultCount').value),
            literature_type: literatureType
        };
        
        await this.startTask('/api/keyword/scrape', data, `关键词搜索 (${literatureTypeName})`);
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
        
        const historyHtml = history.map(item => {
            // 获取文献类型显示名称
            const literatureTypeDisplay = this.getLiteratureTypeDisplay(item.literature_type);
            
            return `
                <div class="search-history-item">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <div class="d-flex align-items-center mb-2">
                                <div class="fw-bold me-2">${item.search_query}</div>
                                ${literatureTypeDisplay ? `<span class="badge bg-secondary">${literatureTypeDisplay}</span>` : ''}
                            </div>
                            <div class="text-muted small">
                                搜索时间: ${new Date(item.created_at).toLocaleString()}
                            </div>
                            <div class="text-muted small">
                                结果数量: ${item.result_count} 篇文章
                            </div>
                            <div class="text-muted small">
                                搜索类型: ${item.search_type === 'keyword' ? '关键词搜索' : '期刊搜索'}
                            </div>
                        </div>
                        <div class="ms-3">
                            <button class="btn btn-outline-primary btn-sm" onclick="searchManager.searchAgain('${item.search_query}', '${item.literature_type || ''}')">
                                <i class="bi bi-arrow-repeat"></i> 重新搜索
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
        container.innerHTML = historyHtml;
    }
    
    getLiteratureTypeDisplay(literatureType) {
        const typeMap = {
            'journal': '期刊论文',
            'thesis': '学位论文',
            'conference': '会议论文',
            'newspaper': '报纸文章',
            'book': '图书',
            'standard': '标准',
            'patent': '专利',
            'yearbook': '年鉴'
        };
        return typeMap[literatureType] || literatureType;
    }
    
    searchAgain(keyword, literatureType = '') {
        document.getElementById('keywords').value = keyword;
        
        // 设置文献类型
        if (literatureType) {
            const literatureTypeSelect = document.getElementById('literatureType');
            if (literatureTypeSelect) {
                literatureTypeSelect.value = literatureType;
            }
        }
        
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