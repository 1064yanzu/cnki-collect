# CNKI舆情爬虫系统

一个功能完整的CNKI（中国知网）舆情爬虫系统，支持期刊检索、关键词搜索和文章批量下载。

## 功能特性

- 🔍 **期刊检索**: 通过ISSN批量检索期刊文章链接
- 🔎 **关键词搜索**: 通过关键词搜索相关文章
- 📥 **批量下载**: 自动下载PDF/CAJ格式文章
- 🖥️ **跨平台支持**: 支持macOS、Windows、Linux
- 🛡️ **反检测**: 内置人类行为模拟，降低被封风险
- 📊 **进度跟踪**: 详细的日志记录和进度显示

## 系统要求

- Python 3.8+
- Chrome浏览器
- ChromeDriver

## 安装指南

### 1. 克隆项目
```bash
git clone <项目地址>
cd yuqing_update
```

### 2. 安装Python依赖
```bash
pip install -r requirements.txt
```

### 3. 安装ChromeDriver

#### macOS (推荐使用Homebrew)
```bash
# 使用Homebrew安装
brew install chromedriver

# 或者手动下载
# 1. 访问 https://chromedriver.chromium.org/
# 2. 下载对应版本的ChromeDriver
# 3. 解压并移动到 /usr/local/bin/
```

#### Windows
1. 访问 [ChromeDriver官网](https://chromedriver.chromium.org/)
2. 下载对应Chrome版本的驱动
3. 解压到 `C:\Program Files\chromedriver-win64\`

#### Linux
```bash
# Ubuntu/Debian
sudo apt-get install chromium-chromedriver

# 或者手动安装
wget https://chromedriver.storage.googleapis.com/LATEST_RELEASE
# 下载对应版本并安装到 /usr/local/bin/
```

### 4. 验证安装
```bash
python main.py status
```

## 配置说明

主要配置文件为 `config.py`，可以根据需要修改以下设置：

```python
# 基础配置
DEBUG = True          # 调试模式
HEADLESS = False      # 无头模式（后台运行）

# 搜索配置
KEYWORDS = {'播客'}   # 默认搜索关键词
RESULT_COUNT = 100    # 每个关键词搜索结果数量

# 期刊配置
EXCEL_FILE = 'testing_journals.xls'  # 期刊列表文件
YEAR_RANGE = [2014, 2022]            # 年份范围

# 下载配置
FILE_TYPE = 'pdf'     # 下载文件类型: 'pdf' 或 'caj'
MAX_WORKERS = 2       # 并发下载数
BATCH_SIZE = 45       # 批处理大小
MAX_RETRIES = 3       # 最大重试次数
```

## 使用方法

### 命令行界面

系统提供了统一的命令行界面，支持以下命令：

#### 查看系统状态
```bash
python main.py status
```

#### 期刊检索
```bash
# 使用默认配置
python main.py journal

# 指定参数
python main.py journal -f 期刊列表.xls -s 2020 -e 2023
```

#### 关键词搜索
```bash
# 使用默认关键词
python main.py keyword

# 指定关键词
python main.py keyword -k 播客 人工智能 机器学习 -c 50
```

#### 文章下载
```bash
# 使用默认配置
python main.py download

# 指定并发数
python main.py download -w 3
```

#### 完整流程
```bash
# 运行期刊检索 + 文章下载
python main.py full -f 期刊列表.xls -s 2020 -e 2023 -w 2
```

### 直接调用模块

也可以直接运行各个功能模块：

```bash
# 期刊检索
python journal_scraper.py

# 关键词搜索
python keyword_scraper.py

# 文章下载
python article_downloader.py
```

## 文件结构

```
yuqing_update/
├── main.py                 # 主入口文件
├── config.py              # 配置文件
├── utils.py               # 工具类
├── journal_scraper.py     # 期刊检索模块
├── keyword_scraper.py     # 关键词搜索模块
├── article_downloader.py  # 文章下载模块
├── requirements.txt       # 依赖包列表
├── README.md             # 说明文档
├── testing_journals.xls  # 期刊列表示例
├── saves/                # 下载文件保存目录
└── links/                # 链接文件保存目录
```

## 期刊列表格式

期刊列表Excel文件格式要求：
- 第一列：期刊名称
- 第二列：期刊ISSN

示例：
```
期刊名称          ISSN
计算机学报        0254-4164
软件学报          1000-9825
```

## 输出文件说明

### 链接文件 (links/)
- 格式：`期刊名_年份.txt` 或 `关键词.txt`
- 内容：`文章标题 -||- 年份 -||- 文章链接`

### 下载文件 (saves/)
- 目录结构：`saves/期刊名/年份/`
- 文件格式：PDF或CAJ

## 常见问题

### 1. ChromeDriver路径问题
如果提示找不到ChromeDriver，请：
1. 确认已正确安装ChromeDriver
2. 检查 `config.py` 中的路径设置
3. 确保ChromeDriver版本与Chrome浏览器版本匹配

### 2. 下载失败
可能原因：
- 网络连接问题
- CNKI反爬虫机制
- 文章需要权限访问

解决方案：
- 降低并发数 (`MAX_WORKERS`)
- 增加延时时间
- 检查网络连接

### 3. 验证码问题
系统内置了验证码检测和重试机制，遇到验证码会自动重试。如果频繁出现验证码：
- 降低爬取频率
- 启用人类行为模拟
- 适当增加休息时间

### 4. 内存占用过高
- 启用无头模式 (`HEADLESS = True`)
- 降低批处理大小 (`BATCH_SIZE`)
- 减少并发数 (`MAX_WORKERS`)

## 注意事项

1. **合法使用**: 请遵守CNKI的使用条款，仅用于学术研究目的
2. **频率控制**: 避免过于频繁的请求，以免被封IP
3. **数据备份**: 定期备份重要的链接文件和下载文件
4. **版权尊重**: 下载的文章仅供个人学习研究使用

## 更新日志

### v2.0.0 (当前版本)
- 重构代码架构，提升可维护性
- 添加Mac系统支持
- 统一配置管理
- 改进错误处理和日志记录
- 添加命令行界面
- 优化下载性能

### v1.0.0
- 基础功能实现
- 支持期刊检索和文章下载

## 许可证

本项目仅供学习和研究使用，请遵守相关法律法规和网站使用条款。

## 贡献

欢迎提交Issue和Pull Request来改进项目。

## 联系方式

如有问题或建议，请通过Issue联系。

---

**原始说明**: 本程序使用了 selenium，需要浏览器的 webdriver 才能工作。若出现`ModuleNotFoundError: No module named blinker._saferef` 可能是由于你的 blinker 版本过高，selenium 需要重新安装 blinker==1.7.0 版本。

讲解请看：<https://www.cnblogs.com/ofnoname/p/18751494>
