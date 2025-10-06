"""
配置文件 - 统一管理所有配置项
"""
import os
import platform
from pathlib import Path

class Config:
    """统一配置管理类"""
    
    # 基础配置
    DEBUG = True
    HEADLESS = False
    
    # 目录配置
    BASE_DIR = Path(__file__).parent
    SAVE_DIR = BASE_DIR / 'saves'
    LINK_DIR = BASE_DIR / 'links'
    # 新增：日志与导出目录
    LOG_DIR = BASE_DIR / 'logs'
    EXPORT_DIR = BASE_DIR / 'exports'
    
    # ChromeDriver配置 - 自动检测系统类型
    @staticmethod
    def get_chrome_driver_path():
        """根据系统类型返回ChromeDriver路径"""
        system = platform.system().lower()
        
        if system == 'darwin':  # macOS
            # 常见的Mac ChromeDriver路径
            possible_paths = [
                '/usr/local/bin/chromedriver',
                '/opt/homebrew/bin/chromedriver',
                str(Path.home() / 'chromedriver'),
                '/Applications/chromedriver'
            ]
        elif system == 'windows':
            possible_paths = [
                r'C:\Program Files\chromedriver-win64\chromedriver.exe',
                r'C:\chromedriver\chromedriver.exe',
                r'C:\Program Files\chromedriver.exe'
            ]
        else:  # Linux
            possible_paths = [
                '/usr/local/bin/chromedriver',
                '/usr/bin/chromedriver',
                str(Path.home() / 'chromedriver')
            ]
        
        # 检查路径是否存在
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # 如果都不存在，返回默认路径并提示用户
        default_path = possible_paths[0]
        print(f"警告: 未找到ChromeDriver，请确保已安装并位于: {default_path}")
        print("或者手动修改config.py中的CHROME_DRIVER_PATH")
        return default_path
    
    # 在类定义时就获取ChromeDriver路径
    _chrome_driver_path = None
    
    @classmethod
    def get_chrome_driver_path_dynamic(cls):
        """动态获取ChromeDriver路径"""
        if cls._chrome_driver_path is None:
            cls._chrome_driver_path = cls.get_chrome_driver_path()
        return cls._chrome_driver_path
    
    # 搜索配置
    KEYWORDS = {'播客'}  # 默认搜索关键词
    RESULT_COUNT = 100  # 每个关键词搜索结果数量
    
    # 文献类型配置
    LITERATURE_TYPES = {
        'journal': {
            'name': '期刊论文',
            'classid': 'YSTT4HG0',
            'description': '学术期刊发表的论文'
        },
        'thesis': {
            'name': '学位论文',
            'classid': 'LSTPFY1C', 
            'description': '硕士、博士学位论文'
        },
        'conference': {
            'name': '会议论文',
            'classid': 'WD0FTY92',
            'description': '学术会议发表的论文'
        },
        'newspaper': {
            'name': '报纸',
            'classid': 'CCND',
            'description': '报纸文章'
        }
    }
    
    # 默认文献类型
    DEFAULT_LITERATURE_TYPE = 'journal'
    
    # 期刊配置
    EXCEL_FILE = 'testing_journals.xls'  # 期刊列表文件
    YEAR_RANGE = [2014, 2022]  # 年份范围
    
    # 下载配置
    FILE_TYPE = 'pdf'  # 可选 'pdf' 或 'caj'
    MAX_WORKERS = 2  # 并发下载数
    BATCH_SIZE = 45  # 批处理大小
    MAX_RETRIES = 3  # 最大重试次数
    
    @classmethod
    def ensure_directories(cls):
        """确保所有必要目录存在"""
        for directory in [cls.SAVE_DIR, cls.LINK_DIR, cls.LOG_DIR, cls.EXPORT_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_chrome_options(cls, download_dir=None):
        """获取Chrome浏览器选项配置"""
        from selenium import webdriver
        
        options = webdriver.ChromeOptions()
        
        if cls.HEADLESS:
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-software-rasterizer')
            options.add_argument('--disable-images')
            options.add_argument('--disable-extensions')
            options.add_argument('--window-size=1920x1080')
        
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--enable-unsafe-swiftshader")
        options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # 下载配置
        download_path = download_dir or str(cls.SAVE_DIR.absolute())
        prefs = {
            "download.default_directory": download_path,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "safebrowsing.enabled": False,
        }
        options.add_experimental_option("prefs", prefs)
        
        return options