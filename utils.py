"""
工具类 - 提供通用功能函数
"""
import logging
import os
import random
import sys
import time
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import undetected_chromedriver as uc

from config import Config


class Logger:
    """日志管理类"""
    
    @staticmethod
    def setup_logger(name: str = __name__, level: int = None) -> logging.Logger:
        """设置日志记录器（控制台 + 按天滚动文件）"""
        if level is None:
            level = logging.DEBUG if Config.DEBUG else logging.INFO
        
        logger = logging.getLogger(name)
        logger.setLevel(level)
        
        # 避免重复添加handler
        if not logger.handlers:
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
            
            # 控制台输出
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setFormatter(formatter)
            logger.addHandler(stream_handler)
            
            # 文件输出（按天滚动）
            try:
                Config.ensure_directories()
                from logging.handlers import TimedRotatingFileHandler
                log_file = Config.LOG_DIR / 'cnki.log'
                file_handler = TimedRotatingFileHandler(str(log_file), when='midnight', backupCount=7, encoding='utf-8')
                file_handler.setLevel(level)
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
            except Exception as e:
                logger.warning(f"文件日志初始化失败: {e}")
        
        return logger

class WebDriverManager:
    """WebDriver管理类"""
    
    def __init__(self, download_dir: Optional[str] = None):
        self.download_dir = download_dir
        self.logger = Logger.setup_logger(self.__class__.__name__)
    
    def create_driver(self) -> webdriver.Chrome:
        """创建Chrome WebDriver实例"""
        try:
            # 首先尝试使用系统安装的ChromeDriver
            chrome_driver_path = Config.get_chrome_driver_path_dynamic()
            if chrome_driver_path and os.path.exists(chrome_driver_path):
                self.logger.info(f"使用系统ChromeDriver: {chrome_driver_path}")
                service = Service(chrome_driver_path)
                options = Config.get_chrome_options(self.download_dir)
                driver = webdriver.Chrome(service=service, options=options)
            else:
                # 使用undetected-chromedriver自动管理
                self.logger.info("使用undetected-chromedriver自动管理ChromeDriver")
                options = uc.ChromeOptions()
                
                # 设置下载目录
                if self.download_dir:
                    prefs = {
                        "download.default_directory": self.download_dir,
                        "download.prompt_for_download": False,
                        "download.directory_upgrade": True,
                        "safebrowsing.enabled": True
                    }
                    options.add_experimental_option("prefs", prefs)
                
                # 添加其他选项
                if Config.HEADLESS:
                    options.add_argument('--headless')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-gpu')
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)
                
                # 创建undetected-chromedriver实例
                driver = uc.Chrome(options=options, version_main=None)
            
            # 绕过webdriver检测
            driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            
            self.logger.info("Chrome WebDriver创建成功")
            return driver
            
        except Exception as e:
            self.logger.error(f"创建WebDriver失败: {e}")
            self.logger.info("正在尝试使用undetected-chromedriver自动下载ChromeDriver...")
            try:
                # 最后的备用方案：强制使用undetected-chromedriver
                options = uc.ChromeOptions()
                if Config.HEADLESS:
                    options.add_argument('--headless')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                
                driver = uc.Chrome(options=options)
                self.logger.info("使用undetected-chromedriver创建WebDriver成功")
                return driver
            except Exception as e2:
                self.logger.error(f"所有方法都失败了: {e2}")
                raise
    
    def simulate_human_behavior(self, driver: webdriver.Chrome) -> None:
        """模拟人类浏览行为，降低被检测风险"""
        try:
            self.logger.debug("开始模拟人类浏览行为")
            
            # 访问首页
            driver.get('https://kns.cnki.net/kns8s/defaultresult/index')
            time.sleep(random.uniform(1, 1.5))
            
            # 进行一次搜索
            driver.get('https://kns.cnki.net/kns8s/defaultresult/index?kw=学术研究')
            time.sleep(random.uniform(1, 1.5))
            
            # 尝试翻页
            try:
                next_button = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, 'PageNext'))
                )
                if 'disabled' not in next_button.get_attribute('class'):
                    next_button.click()
                    time.sleep(random.uniform(0.5, 1))
            except Exception:
                pass
            
            # 访问一篇文章
            test_url = ('https://kns.cnki.net/kcms2/article/abstract?v='
                       'jNHD1hIvxn3V4QTDlEMKElsHKaTntLnuqQcAeWVTldLPFBn7iT-1Tm4UqqAiMvAE'
                       'yHpC5baI1wNaLNYpxJrWNLLA-qwDCdqTs7Q_qbXKpcOcTkzjDVW1nndiqngcWd2E'
                       'QjyOwhwnX44UVtGVXou0tJJ1uxIBDd_iR7mmJhaA88A=&uniplatform=NZKPT')
            driver.get(test_url)
            
            # 多次刷新页面
            for _ in range(random.randint(3, 6)):
                driver.refresh()
                time.sleep(random.uniform(0.2, 0.5))
            
            self.logger.debug("人类浏览行为模拟完成")
            
        except Exception as e:
            self.logger.warning(f"模拟人类行为时出错: {e}")


class FileManager:
    """文件管理类"""
    
    def __init__(self):
        self.logger = Logger.setup_logger(self.__class__.__name__)
    
    def ensure_directory(self, directory: Path) -> None:
        """确保目录存在"""
        try:
            directory.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"目录确认存在: {directory}")
        except Exception as e:
            self.logger.error(f"创建目录失败 {directory}: {e}")
            raise
    
    def save_links_to_file(self, links: list, filepath: Path, 
                           names: list = None, years: list = None) -> None:
        """保存链接到文件"""
        try:
            self.ensure_directory(filepath.parent)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                if names and years:
                    # 带名称和年份的格式
                    for link, name, year in zip(links, names, years):
                        f.write(f'{name} -||- {year} -||- {link}\n')
                else:
                    # 仅链接格式
                    for link in links:
                        f.write(f'{link}\n')
            
            self.logger.info(f"链接已保存到: {filepath}")
            
        except Exception as e:
            self.logger.error(f"保存链接失败 {filepath}: {e}")
            raise
    
    def load_links_from_file(self, filepath: Path) -> list:
        """从文件加载链接"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
            
            # 检查是否是带格式的链接文件
            if lines and ' -||- ' in lines[0]:
                # 提取链接部分
                links = [line.split(' -||- ')[-1] for line in lines]
            else:
                links = lines
            
            self.logger.info(f"从 {filepath} 加载了 {len(links)} 个链接")
            return links
            
        except Exception as e:
            self.logger.error(f"加载链接失败 {filepath}: {e}")
            return []
    
    def save_json(self, data: dict, filepath: Path) -> None:
        """保存 JSON 文件（UTF-8，带缩进）"""
        try:
            self.ensure_directory(filepath.parent)
            with open(filepath, 'w', encoding='utf-8') as f:
                import json
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.logger.info(f"JSON 导出完成: {filepath}")
        except Exception as e:
            self.logger.error(f"保存 JSON 失败 {filepath}: {e}")
            raise
    
    def save_csv(self, rows: list, headers: list, filepath: Path) -> None:
        """保存 CSV 文件（UTF-8）"""
        try:
            import csv
            self.ensure_directory(filepath.parent)
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                for row in rows:
                    writer.writerow(row)
            self.logger.info(f"CSV 导出完成: {filepath}")
        except Exception as e:
            self.logger.error(f"保存 CSV 失败 {filepath}: {e}")
            raise


def wait_with_random_delay(min_seconds: float = 0.5, max_seconds: float = 2.0) -> None:
    """随机延时等待"""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)