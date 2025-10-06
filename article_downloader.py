"""
文章下载模块 - 批量下载PDF/CAJ文件
"""
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List

from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import Config
from utils import Logger, WebDriverManager, FileManager, wait_with_random_delay


class ArticleDownloader:
    """文章下载器"""
    
    def __init__(self):
        self.logger = Logger.setup_logger(self.__class__.__name__)
        self.file_manager = FileManager()
        Config.ensure_directories()
    
    def download_from_link_file(self, link_file: Path) -> None:
        """
        从链接文件下载文章
        
        Args:
            link_file: 包含文章链接的文件路径
        """
        if not link_file.exists():
            self.logger.error(f"链接文件不存在: {link_file}")
            return
        
        # 解析文件名获取期刊名和年份
        try:
            base_name = link_file.stem  # 去掉.txt后缀
            if '_' in base_name:
                name_part, year_part = base_name.rsplit('_', 1)
                year = year_part
            else:
                name_part = base_name
                year = "unknown"
        except Exception as e:
            self.logger.error(f"解析文件名失败 {link_file}: {e}")
            return
        
        # 加载链接
        links = self.file_manager.load_links_from_file(link_file)
        if not links:
            self.logger.warning(f"文件 {link_file} 中没有找到有效链接")
            return
        
        self.logger.info(f"开始下载 {name_part} {year}，共 {len(links)} 篇文章")
        
        # 创建下载目录
        download_dir = Config.SAVE_DIR / name_part / str(year)
        self.file_manager.ensure_directory(download_dir)
        
        # 执行下载
        self._download_articles(name_part, year, links, download_dir)
    
    def _download_articles(self, name: str, year: str, links: List[str], 
                          download_dir: Path) -> None:
        """下载文章列表"""
        driver_manager = WebDriverManager(str(download_dir))
        driver = None
        
        success_count = 0
        failed_links = []
        
        try:
            for idx, link in enumerate(links):
                # 批次处理：每处理一定数量重启浏览器
                if idx % Config.BATCH_SIZE == 0:
                    if driver:
                        driver.quit()
                    
                    self.logger.info(f"{name} {year}: 处理进度 {idx}/{len(links)}，重启浏览器")
                    driver = driver_manager.create_driver()
                    driver_manager.simulate_human_behavior(driver)
                    wait_with_random_delay(2.0, 4.0)
                
                # 尝试下载单篇文章
                if self._download_single_article(driver, link, idx, name, year):
                    success_count += 1
                else:
                    failed_links.append(link)
                
                wait_with_random_delay(0.5, 1.5)
            
            # 重试失败的文章
            if failed_links:
                self.logger.info(f"{name} {year}: 重试 {len(failed_links)} 篇失败的文章")
                retry_success = self._retry_failed_downloads(
                    driver_manager, failed_links, name, year, download_dir
                )
                success_count += retry_success
        
        except Exception as e:
            self.logger.error(f"下载过程中发生错误: {e}")
        
        finally:
            if driver:
                driver.quit()
        
        failed_count = len(links) - success_count
        self.logger.info(f"{name} {year} 下载完成: 成功 {success_count}，失败 {failed_count}")
    
    def _download_single_article(self, driver, link: str, index: int, 
                                name: str, year: str) -> bool:
        """
        下载单篇文章
        
        Returns:
            bool: 下载成功返回True，失败返回False
        """
        for attempt in range(1, Config.MAX_RETRIES + 1):
            try:
                # 访问文章页面
                driver.get(link)
                wait_with_random_delay(0.8, 1.5)
                
                # 尝试执行重定向脚本
                try:
                    driver.execute_script("redirectNewLink()")
                except Exception:
                    pass
                
                # 刷新页面确保加载完整
                for _ in range(2):
                    driver.refresh()
                    wait_with_random_delay(0.8, 1.2)
                    try:
                        driver.execute_script("redirectNewLink()")
                    except Exception:
                        pass
                
                wait_with_random_delay(0.5, 1.0)
                
                # 选择下载按钮
                css_selector = '.btn-dlpdf a' if Config.FILE_TYPE == 'pdf' else '.btn-dlcaj a'
                
                download_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, css_selector))
                )
                
                # 点击下载
                ActionChains(driver).move_to_element(download_button).click(download_button).perform()
                
                # 切换到新窗口
                driver.switch_to.window(driver.window_handles[-1])
                
                # 等待页面加载
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'html'))
                )
                
                # 检查是否遇到验证码
                if "拼图校验" in driver.page_source:
                    self.logger.warning(f"{name} {year} 第{index+1}篇: 遇到验证码 (尝试 {attempt})")
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                    
                    if attempt < Config.MAX_RETRIES:
                        # 等待并刷新页面
                        wait_with_random_delay(2.0, 4.0)
                        for _ in range(4):
                            driver.refresh()
                            wait_with_random_delay(0.8, 1.2)
                    continue
                else:
                    self.logger.info(f"{name} {year} 第{index+1}篇: 下载成功 (尝试 {attempt})")
                    driver.switch_to.window(driver.window_handles[0])
                    return True
            
            except Exception as e:
                self.logger.warning(f"{name} {year} 第{index+1}篇: 下载失败 (尝试 {attempt}): {e}")
                wait_with_random_delay(1.0, 2.0)
        
        self.logger.error(f"{name} {year} 第{index+1}篇: 所有尝试均失败")
        return False
    
    def _retry_failed_downloads(self, driver_manager: WebDriverManager, 
                               failed_links: List[str], name: str, year: str,
                               download_dir: Path) -> int:
        """重试失败的下载"""
        driver = driver_manager.create_driver()
        retry_success = 0
        
        try:
            driver_manager.simulate_human_behavior(driver)
            
            for idx, link in enumerate(failed_links):
                if idx % Config.BATCH_SIZE == 0 and idx > 0:
                    driver.quit()
                    driver = driver_manager.create_driver()
                    driver_manager.simulate_human_behavior(driver)
                
                if self._download_single_article(driver, link, idx, name, year):
                    retry_success += 1
                
                wait_with_random_delay(1.0, 2.0)
        
        except Exception as e:
            self.logger.error(f"重试下载时发生错误: {e}")
        
        finally:
            if driver:
                driver.quit()
        
        return retry_success
    
    def download_all_link_files(self, max_workers: int = None) -> None:
        """
        批量处理所有链接文件
        
        Args:
            max_workers: 最大并发数，默认使用配置值
        """
        max_workers = max_workers or Config.MAX_WORKERS
        
        # 查找所有txt文件
        link_files = list(Config.LINK_DIR.glob("*.txt"))
        
        if not link_files:
            self.logger.error(f"在 {Config.LINK_DIR} 中未找到链接文件")
            return
        
        self.logger.info(f"找到 {len(link_files)} 个链接文件，开始批量下载")
        
        # 使用线程池处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.download_from_link_file, file): file 
                for file in link_files
            }
            
            for future in as_completed(futures):
                file = futures[future]
                try:
                    future.result()
                    self.logger.info(f"完成处理文件: {file.name}")
                except Exception as e:
                    self.logger.error(f"处理文件 {file.name} 时发生错误: {e}")
        
        self.logger.info("所有文件处理完成")


def main():
    """主函数"""
    downloader = ArticleDownloader()
    downloader.download_all_link_files()


if __name__ == "__main__":
    main()