"""
期刊检索模块 - 通过ISSN检索期刊文章链接
"""
import time
from pathlib import Path
from typing import List, Tuple

import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import Config
from utils import Logger, WebDriverManager, FileManager, wait_with_random_delay


class JournalScraper:
    """期刊文章链接爬取器"""
    
    def __init__(self):
        self.logger = Logger.setup_logger(self.__class__.__name__)
        self.driver_manager = WebDriverManager()
        self.file_manager = FileManager()
        Config.ensure_directories()
    
    def load_journal_list(self, excel_file: str) -> List[Tuple[str, str]]:
        """
        从Excel文件加载期刊列表
        
        Args:
            excel_file: Excel文件路径
            
        Returns:
            包含(期刊名称, ISSN)元组的列表
        """
        try:
            filepath = Path(excel_file)
            if not filepath.exists():
                self.logger.error(f"Excel文件不存在: {filepath}")
                return []
            
            df = pd.read_excel(filepath, header=None)
            journal_list = [
                (str(row[0]).strip(), str(row[1]).strip()) 
                for row in df.values 
                if pd.notna(row[0]) and pd.notna(row[1])
            ]
            
            self.logger.info(f"成功加载 {len(journal_list)} 个期刊")
            return journal_list
            
        except Exception as e:
            self.logger.error(f"读取Excel文件失败 {excel_file}: {e}")
            return []
    
    def scrape_journal_by_issn(self, name: str, issn: str, 
                              year_range: List[int]) -> None:
        """
        根据期刊ISSN检索并收集文章链接
        
        Args:
            name: 期刊名称
            issn: 期刊ISSN
            year_range: [起始年份, 结束年份]
        """
        driver = self.driver_manager.create_driver()
        
        try:
            self.logger.info(f"开始检索期刊: {name} (ISSN: {issn})")
            
            # 访问CNKI导航页面
            driver.get('https://navi.cnki.net/')
            wait_with_random_delay(0.5, 1.0)
            
            # 选择ISSN检索方式
            select_element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "txt_1_sel"))
            )
            
            option_elements = select_element.find_elements(By.TAG_NAME, "option")
            for option in option_elements:
                if option.text.strip() == "ISSN":
                    option.click()
                    break
            
            # 输入ISSN
            input_element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "txt_1_value1"))
            )
            input_element.clear()
            input_element.send_keys(issn)
            
            # 点击搜索
            search_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "btnSearch"))
            )
            search_button.click()
            
            # 等待搜索结果并点击第一个期刊
            journal_cover = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".re_bookCover"))
            )
            journal_cover.click()
            
            wait_with_random_delay(0.5, 1.0)
            
            # 切换到新窗口
            driver.switch_to.window(driver.window_handles[-1])
            
            # 遍历年份收集链接
            for year in range(year_range[0], year_range[1] + 1):
                self.logger.info(f"正在收集 {name} {year}年 的文章链接")
                links = self._collect_year_links(driver, year)
                
                if links:
                    # 保存链接到文件
                    output_file = Config.LINK_DIR / f"{name}_{year}.txt"
                    self.file_manager.save_links_to_file(links, output_file)
                else:
                    self.logger.warning(f"{name} {year}年 未找到文章链接")
                
                wait_with_random_delay(1.0, 2.0)
        
        except Exception as e:
            self.logger.error(f"处理期刊 {name} 时发生错误: {e}")
        
        finally:
            driver.quit()
            self.logger.debug("WebDriver已关闭")
    
    def _collect_year_links(self, driver, year: int) -> List[str]:
        """收集指定年份的文章链接"""
        try:
            year_id = f"{year}_Year_Issue"
            year_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, year_id))
            )
            
            # 展开年份下拉菜单
            dt_element = WebDriverWait(year_element, 10).until(
                EC.element_to_be_clickable((By.TAG_NAME, "dt"))
            )
            dt_element.click()
            
            # 获取所有期号链接
            issue_elements = year_element.find_elements(By.CSS_SELECTOR, "dd a")
            all_links = []
            
            for issue_element in issue_elements:
                try:
                    # 等待期号链接可用并点击
                    WebDriverWait(driver, 10).until(
                        lambda d: issue_element.is_enabled() and issue_element.is_displayed()
                    )
                    issue_element.click()
                    wait_with_random_delay(0.5, 1.0)
                    
                    # 收集当前期号的文章链接
                    link_elements = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located(
                            (By.CSS_SELECTOR, "#CataLogContent span.name a")
                        )
                    )
                    
                    for link_element in link_elements:
                        link = link_element.get_attribute("href")
                        if link:
                            all_links.append(link)
                    
                    wait_with_random_delay(0.3, 0.8)
                    
                except Exception as e:
                    self.logger.warning(f"处理期号时出错: {e}")
                    continue
            
            return all_links
            
        except Exception as e:
            self.logger.error(f"收集 {year} 年链接时出错: {e}")
            return []
    
    def scrape_all_journals(self, excel_file: str = None, 
                           year_range: List[int] = None) -> None:
        """
        批量处理所有期刊
        
        Args:
            excel_file: Excel文件路径，默认使用配置中的文件
            year_range: 年份范围，默认使用配置中的范围
        """
        excel_file = excel_file or Config.EXCEL_FILE
        year_range = year_range or Config.YEAR_RANGE
        
        journals = self.load_journal_list(excel_file)
        if not journals:
            self.logger.error("未找到期刊列表，请检查Excel文件")
            return
        
        self.logger.info(f"开始处理 {len(journals)} 个期刊，年份范围: {year_range}")
        
        for i, (name, issn) in enumerate(journals, 1):
            self.logger.info(f"处理进度: {i}/{len(journals)}")
            self.scrape_journal_by_issn(name, issn, year_range)
            
            # 期刊间休息
            if i < len(journals):
                wait_with_random_delay(2.0, 4.0)
        
        self.logger.info("所有期刊处理完成")


def main():
    """主函数"""
    scraper = JournalScraper()
    scraper.scrape_all_journals()


if __name__ == "__main__":
    main()