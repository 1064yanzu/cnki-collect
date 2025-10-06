"""
关键词搜索模块 - 通过关键词搜索文章链接
"""
import time
from pathlib import Path
from typing import List, Set

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import Config
from utils import Logger, WebDriverManager, FileManager, wait_with_random_delay
from database import db
from task_manager import task_manager, TaskStoppedException


class KeywordScraper:
    """关键词搜索爬取器"""
    
    def __init__(self):
        self.logger = Logger.setup_logger(self.__class__.__name__)
        self.driver_manager = WebDriverManager()
        self.file_manager = FileManager()
        Config.ensure_directories()
    
    def scrape_keyword_with_task(self, keyword: str, result_count: int = None) -> int:
        """
        使用任务管理器搜索关键词（支持中断和恢复）
        
        Args:
            keyword: 搜索关键词
            result_count: 需要收集的结果数量
            
        Returns:
            任务ID
        """
        result_count = result_count or Config.RESULT_COUNT
        
        # 创建任务
        task_id = task_manager.create_task(
            task_type='keyword_search',
            task_name=f'关键词搜索: {keyword}',
            task_func=self._scrape_keyword_task,
            parameters={'keyword': keyword, 'result_count': result_count},
            total_items=result_count,
            can_resume=True
        )
        
        # 启动任务
        task_manager.start_task(task_id)
        return task_id
    
    def _scrape_keyword_task(self, task, keyword: str, result_count: int) -> dict:
        """
        任务函数：搜索关键词
        
        Args:
            task: 任务实例
            keyword: 搜索关键词
            result_count: 需要收集的结果数量
            
        Returns:
            搜索结果统计
        """
        driver = self.driver_manager.create_driver()
        
        try:
            self.logger.info(f"开始搜索关键词: {keyword}，目标数量: {result_count}")
            task.update_progress(current_step="初始化搜索")
            
            # 构建搜索URL
            search_url = f'https://kns.cnki.net/kns8s/defaultresult/index?kw={keyword}'
            driver.get(search_url)
            wait_with_random_delay(1.0, 2.0)
            
            # 检查是否需要暂停或停止
            task.check_pause_or_stop()
            
            # 设置每页显示50条结果
            task.update_progress(current_step="设置页面参数")
            self._set_page_size(driver)
            
            # 收集搜索结果
            task.update_progress(current_step="收集搜索结果")
            links, dates, names, articles_data = self._collect_search_results_with_task(
                driver, result_count, keyword, task
            )
            
            # 保存结果
            if links:
                task.update_progress(current_step="保存搜索结果")
                
                # 保存到文件（保持兼容性）
                output_file = Config.LINK_DIR / f"{keyword}.txt"
                self._save_search_results(output_file, links, dates, names)
                
                # 保存到数据库
                saved_count = 0
                for i, article_data in enumerate(articles_data):
                    try:
                        # 检查是否需要暂停或停止
                        task.check_pause_or_stop()
                        
                        article_id = db.add_article(**article_data)
                        saved_count += 1
                        
                        # 更新进度
                        task.update_progress(
                            processed_items=saved_count,
                            current_step=f"保存文章到数据库 ({saved_count}/{len(articles_data)})"
                        )
                        
                    except Exception as e:
                        task.failed_items += 1
                        self.logger.warning(f"保存文章到数据库失败: {e}")
                
                # 记录搜索历史
                db.add_search_history('keyword', keyword, len(links))
                
                self.logger.info(f"关键词 '{keyword}' 搜索完成，共收集 {len(links)} 个链接，保存到数据库 {saved_count} 条")
                
                return {
                    'keyword': keyword,
                    'total_links': len(links),
                    'saved_count': saved_count,
                    'failed_count': task.failed_items
                }
            else:
                self.logger.warning(f"关键词 '{keyword}' 未找到任何结果")
                return {'keyword': keyword, 'total_links': 0, 'saved_count': 0, 'failed_count': 0}
        
        finally:
            driver.quit()
            self.logger.debug("WebDriver已关闭")
    
    def scrape_keyword(self, keyword: str, result_count: int = None) -> None:
        """
        根据关键词搜索并收集文章链接
        
        Args:
            keyword: 搜索关键词
            result_count: 需要收集的结果数量，默认使用配置值
        """
        result_count = result_count or Config.RESULT_COUNT
        driver = self.driver_manager.create_driver()
        
        try:
            self.logger.info(f"开始搜索关键词: {keyword}，目标数量: {result_count}")
            
            # 构建搜索URL
            search_url = f'https://kns.cnki.net/kns8s/defaultresult/index?kw={keyword}'
            driver.get(search_url)
            wait_with_random_delay(1.0, 2.0)
            
            # 设置每页显示50条结果
            self._set_page_size(driver)
            
            # 收集搜索结果
            links, dates, names, articles_data = self._collect_search_results(driver, result_count, keyword)
            
            # 保存结果
            if links:
                # 保存到文件（保持兼容性）
                output_file = Config.LINK_DIR / f"{keyword}.txt"
                self._save_search_results(output_file, links, dates, names)
                
                # 保存到数据库
                saved_count = 0
                for article_data in articles_data:
                    try:
                        article_id = db.add_article(**article_data)
                        saved_count += 1
                    except Exception as e:
                        self.logger.warning(f"保存文章到数据库失败: {e}")
                
                # 记录搜索历史
                db.add_search_history('keyword', keyword, len(links))
                
                self.logger.info(f"关键词 '{keyword}' 搜索完成，共收集 {len(links)} 个链接，保存到数据库 {saved_count} 条")
            else:
                self.logger.warning(f"关键词 '{keyword}' 未找到任何结果")
        
        except Exception as e:
            self.logger.error(f"搜索关键词 '{keyword}' 时发生错误: {e}")
        
        finally:
            driver.quit()
            self.logger.debug("WebDriver已关闭")
    
    def _set_page_size(self, driver) -> None:
        """设置每页显示数量为50"""
        try:
            # 点击分页设置
            per_page_div = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, 'perPageDiv'))
            )
            per_page_div.click()
            
            # 等待下拉菜单加载
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'ul.sort-list'))
            )
            
            # 选择50条每页
            page_50 = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'li[data-val="50"] a'))
            )
            page_50.click()
            wait_with_random_delay(1.0, 2.0)
            
            self.logger.debug("已设置每页显示50条结果")
            
        except Exception as e:
            self.logger.warning(f"设置分页大小失败: {e}")
    
    def _collect_search_results_with_task(self, driver, target_count: int, keyword: str, task) -> tuple:
        """
        收集搜索结果（支持任务管理）
        
        Args:
            driver: WebDriver实例
            target_count: 需要收集的结果数量
            keyword: 搜索关键词
            task: 任务实例
            
        Returns:
            (links, dates, names, articles_data) 元组
        """
        links = []
        dates = []
        names = []
        articles_data = []
        page_count = 0
        
        while len(links) < target_count:
            try:
                # 检查是否需要暂停或停止
                task.check_pause_or_stop()
                
                page_count += 1
                self.logger.debug(f"正在处理第 {page_count} 页")
                task.update_progress(
                    processed_items=len(links),
                    current_step=f"处理第 {page_count} 页 ({len(links)}/{target_count})"
                )
                
                # 解析当前页面
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
                # 提取文章信息
                fz14_links = soup.select('.fz14')
                date_cells = soup.select('.date')
                
                if not fz14_links:
                    self.logger.warning("当前页面未找到文章链接")
                    break
                
                # 处理当前页面的结果
                for i, (link_tag, date_cell) in enumerate(zip(fz14_links, date_cells)):
                    if len(links) >= target_count:
                        break
                    
                    try:
                        # 检查是否需要暂停或停止
                        task.check_pause_or_stop()
                        
                        if link_tag.has_attr('href'):
                            # 提取基本信息
                            link = link_tag['href']
                            title = link_tag.get_text(strip=True)
                            date_text = date_cell.get_text(strip=True)
                            year = date_text.split('-')[0] if '-' in date_text else date_text
                            
                            # 尝试提取更多元数据
                            article_data = self._extract_article_metadata(soup, i, title, link, date_text, keyword)
                            
                            links.append(link)
                            names.append(title)
                            dates.append(year)
                            articles_data.append(article_data)
                            
                            # 更新进度
                            task.update_progress(
                                processed_items=len(links),
                                current_step=f"收集文章 ({len(links)}/{target_count})"
                            )
                            
                    except TaskStoppedException:
                        raise
                    except Exception as e:
                        task.failed_items += 1
                        self.logger.warning(f"提取文章信息失败: {e}")
                        continue
                
                # 检查是否需要翻页
                if len(links) < target_count:
                    if not self._go_to_next_page(driver):
                        self.logger.info("已到达最后一页或翻页失败")
                        break
                    wait_with_random_delay(1.0, 2.0)
                    
            except TaskStoppedException:
                self.logger.info("任务被停止")
                raise
            except Exception as e:
                task.failed_items += 1
                self.logger.error(f"处理第 {page_count} 页时出错: {e}")
                break
        
        self.logger.info(f"共收集到 {len(links)} 个搜索结果")
        return links, dates, names, articles_data
    
    def _collect_search_results(self, driver, target_count: int, keyword: str = None) -> tuple:
        """收集搜索结果并提取元数据"""
        links = []
        dates = []
        names = []
        articles_data = []
        page_count = 0
        
        while len(links) < target_count:
            page_count += 1
            self.logger.debug(f"正在处理第 {page_count} 页")
            
            # 解析当前页面
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # 提取文章信息
            fz14_links = soup.select('.fz14')
            date_cells = soup.select('.date')
            
            if not fz14_links:
                self.logger.warning("当前页面未找到文章链接")
                break
            
            # 处理当前页面的结果
            for i, (link_tag, date_cell) in enumerate(zip(fz14_links, date_cells)):
                if len(links) >= target_count:
                    break
                
                if link_tag.has_attr('href'):
                    # 提取基本信息
                    link = link_tag['href']
                    title = link_tag.get_text(strip=True)
                    date_text = date_cell.get_text(strip=True)
                    year = date_text.split('-')[0] if '-' in date_text else date_text
                    
                    # 尝试提取更多元数据
                    article_data = self._extract_article_metadata(soup, i, title, link, date_text, keyword)
                    
                    links.append(link)
                    names.append(title)
                    dates.append(year)
                    articles_data.append(article_data)
            
            # 检查是否需要翻页
            if len(links) < target_count:
                if not self._go_to_next_page(driver):
                    self.logger.info("已到达最后一页或翻页失败")
                    break
                wait_with_random_delay(1.0, 2.0)
        
        self.logger.info(f"共收集到 {len(links)} 个搜索结果")
        return links, dates, names, articles_data
    
    def _extract_article_metadata(self, soup, index: int, title: str, url: str, 
                                 publish_date: str, keyword: str = None) -> dict:
        """提取文章元数据"""
        try:
            # 查找当前文章对应的行
            rows = soup.select('tr')
            if index < len(rows):
                row = rows[index]
                
                # 尝试提取作者信息
                authors = ""
                author_cells = row.select('.author, .authors')
                if author_cells:
                    authors = author_cells[0].get_text(strip=True)
                
                # 尝试提取期刊信息
                journal = ""
                journal_cells = row.select('.journal, .source')
                if journal_cells:
                    journal = journal_cells[0].get_text(strip=True)
                
                # 尝试提取摘要（如果有）
                abstract = ""
                abstract_cells = row.select('.abstract, .summary')
                if abstract_cells:
                    abstract = abstract_cells[0].get_text(strip=True)
                
                # 构建文章数据
                article_data = {
                    'title': title,
                    'url': url,
                    'abstract': abstract,
                    'authors': authors,
                    'journal': journal,
                    'publish_date': publish_date,
                    'keywords': keyword if keyword else "",
                    'source_type': 'keyword_search'
                }
                
                return article_data
                
        except Exception as e:
            self.logger.warning(f"提取文章元数据失败: {e}")
        
        # 返回基本数据
        return {
            'title': title,
            'url': url,
            'abstract': "",
            'authors': "",
            'journal': "",
            'publish_date': publish_date,
            'keywords': keyword if keyword else "",
            'source_type': 'keyword_search'
        }
    
    def _go_to_next_page(self, driver) -> bool:
        """翻到下一页"""
        try:
            next_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, 'PageNext'))
            )
            
            # 检查下一页按钮是否可用
            if 'disabled' in next_button.get_attribute('class'):
                return False
            
            next_button.click()
            return True
            
        except Exception as e:
            self.logger.warning(f"翻页失败: {e}")
            return False
    
    def _save_search_results(self, filepath: Path, links: List[str], 
                           dates: List[str], names: List[str]) -> None:
        """保存搜索结果到文件"""
        try:
            self.file_manager.ensure_directory(filepath.parent)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                for name, year, link in zip(names, dates, links):
                    f.write(f'{name} -||- {year} -||- {link}\n')
            
            self.logger.info(f"搜索结果已保存到: {filepath}")
            
        except Exception as e:
            self.logger.error(f"保存搜索结果失败: {e}")
            raise
    
    def scrape_multiple_keywords(self, keywords: Set[str] = None, 
                               result_count: int = None) -> None:
        """
        批量搜索多个关键词
        
        Args:
            keywords: 关键词集合，默认使用配置中的关键词
            result_count: 每个关键词的结果数量
        """
        keywords = keywords or Config.KEYWORDS
        result_count = result_count or Config.RESULT_COUNT
        
        self.logger.info(f"开始批量搜索 {len(keywords)} 个关键词")
        
        for i, keyword in enumerate(keywords, 1):
            self.logger.info(f"搜索进度: {i}/{len(keywords)} - {keyword}")
            self.scrape_keyword(keyword, result_count)
            
            # 关键词间休息
            if i < len(keywords):
                wait_with_random_delay(2.0, 4.0)
        
        self.logger.info("所有关键词搜索完成")
    
    def search_keywords(self, keywords: List[str], result_count: int = None) -> List[dict]:
        """
        搜索关键词并返回结果
        
        Args:
            keywords: 关键词列表
            result_count: 每个关键词的结果数量
            
        Returns:
            List[dict]: 搜索结果列表，每个元素包含关键词和文件信息
        """
        keywords = keywords or list(Config.KEYWORDS)
        result_count = result_count or Config.RESULT_COUNT
        results = []
        
        self.logger.info(f"开始搜索 {len(keywords)} 个关键词")
        
        for i, keyword in enumerate(keywords, 1):
            try:
                self.logger.info(f"搜索进度: {i}/{len(keywords)} - {keyword}")
                
                # 执行单个关键词搜索
                self.scrape_keyword(keyword, result_count)
                
                # 从数据库获取搜索结果
                articles = db.get_articles(
                    search_query=keyword,
                    source_type='keyword_search',
                    limit=result_count
                )
                
                results.append({
                    'keyword': keyword,
                    'articles': articles,
                    'count': len(articles),
                    'status': 'success'
                })
                
                # 关键词间休息
                if i < len(keywords):
                    wait_with_random_delay(2.0, 4.0)
                    
            except Exception as e:
                self.logger.error(f"搜索关键词 '{keyword}' 失败: {e}")
                results.append({
                    'keyword': keyword,
                    'files': [],
                    'status': 'error',
                    'error': str(e)
                })
        
        self.logger.info(f"关键词搜索完成，成功: {sum(1 for r in results if r['status'] == 'success')}/{len(keywords)}")
        return results


def main():
    """主函数"""
    scraper = KeywordScraper()
    scraper.scrape_multiple_keywords()


if __name__ == "__main__":
    main()