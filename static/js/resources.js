/**
 * 资源中心管理器：加载并展示链接、下载、导出、日志文件
 */
class ResourceManager {
  constructor(app) {
    this.app = app;
    this.init();
  }

  init() {
    const refreshBtn = document.getElementById('refreshResourcesBtn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.loadAll());
    }
  }

  // 在切换到资源中心时加载
  onShow() {
    this.loadAll();
  }

  async loadAll() {
    await Promise.all([
      this.loadLinkFiles(),
      this.loadDownloadFiles(),
      this.loadExportFiles(),
      this.loadLogFiles(),
    ]);
  }

  async loadLinkFiles() {
    const container = document.getElementById('linkFilesList');
    if (!container) return;
    try {
      const res = await fetch('/api/files/links');
      const data = await res.json();
      if (!data.success) throw new Error(data.error || '加载失败');
      this.renderFileList(container, data.data, { icon: 'bi-link-45deg' });
    } catch (err) {
      this.renderError(container, err.message);
    }
  }

  async loadDownloadFiles() {
    const container = document.getElementById('downloadFilesList');
    if (!container) return;
    try {
      const res = await fetch('/api/files/downloads');
      const data = await res.json();
      if (!data.success) throw new Error(data.error || '加载失败');
      this.renderFileList(container, data.data, { icon: 'bi-download', showRelative: true });
    } catch (err) {
      this.renderError(container, err.message);
    }
  }

  async loadExportFiles() {
    const container = document.getElementById('exportFilesList');
    if (!container) return;
    try {
      const res = await fetch('/api/files/exports');
      const data = await res.json();
      if (!data.success) throw new Error(data.error || '加载失败');
      this.renderFileList(container, data.data, { icon: 'bi-filetype-csv' });
    } catch (err) {
      this.renderError(container, err.message);
    }
  }

  async loadLogFiles() {
    const container = document.getElementById('logFilesList');
    if (!container) return;
    try {
      const res = await fetch('/api/files/logs');
      const data = await res.json();
      if (!data.success) throw new Error(data.error || '加载失败');
      this.renderFileList(container, data.data, { icon: 'bi-journal-text' });
    } catch (err) {
      this.renderError(container, err.message);
    }
  }

  renderFileList(container, files, options = {}) {
    const { icon = 'bi-file-earmark', showRelative = false } = options;
    if (!files || files.length === 0) {
      container.innerHTML = `
        <div class="text-center text-muted py-4">
          <i class="bi ${icon}" style="font-size: 2rem;"></i>
          <p class="mt-2">暂无文件</p>
        </div>`;
      return;
    }

    const list = document.createElement('div');
    list.className = 'list-group';

    files.sort((a, b) => new Date(b.modified) - new Date(a.modified));

    files.forEach(file => {
      const item = document.createElement('a');
      item.className = 'list-group-item list-group-item-action';
      const openUrl = `/api/files/open?path=${encodeURIComponent(file.path)}`;
      item.href = openUrl;
      item.target = '_blank';
      item.rel = 'noopener noreferrer';

      const sizeKB = (file.size / 1024).toFixed(1);
      const extraPath = showRelative && file.relative_path ? ` <span class="text-muted">(${file.relative_path})</span>` : '';

      item.innerHTML = `
        <div class="d-flex w-100 justify-content-between">
          <h6 class="mb-1"><i class="bi ${icon}"></i> ${file.name}${extraPath}</h6>
          <small class="text-muted">${file.modified}</small>
        </div>
        <small class="text-muted">${sizeKB} KB</small>
      `;

      list.appendChild(item);
    });

    container.innerHTML = '';
    container.appendChild(list);
  }

  renderError(container, message) {
    container.innerHTML = `
      <div class="alert alert-danger" role="alert">
        <i class="bi bi-exclamation-triangle"></i> 加载失败：${message}
      </div>`;
  }
}

// 切换到资源中心时触发加载
(function bindResourceTab() {
  const resourcesTabBtn = document.getElementById('resources-tab');
  if (resourcesTabBtn) {
    resourcesTabBtn.addEventListener('shown.bs.tab', () => {
      if (window.resourceManager) {
        window.resourceManager.onShow();
      }
    });
  }
})();