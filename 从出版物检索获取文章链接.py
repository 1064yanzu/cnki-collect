import logging
import os
import time
from typing import List, Tuple

import pandas as pd
import undetected_chromedriver as uc
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from seleniumwire import webdriver

# 配置
DEBUG = True
CHROME_DRIVER_PATH = r'C:\Program Files\chromedriver-win64\chromedriver.exe'
SAVE_DIR = 'saves'
LINK_DIR = 'links'
EXCEL_FILE = '测试期刊.xls'
YEAR_RANGE = [2014, 2022]

# 配置日志记录
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def ensure_directory_exists(directory: str) -> None:
    """
    确保指定目录存在，若不存在则创建。
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
        logging.debug(f"目录 {directory} 创建成功。")
    else:
        logging.debug(f"目录 {directory} 已存在。")


def load_chrome_driver(use_undetected: bool = True) -> webdriver.Chrome:
    """
    加载ChromeDriver，并配置相关选项。

    :param use_undetected: 如果为True，则使用 undetected_chromedriver，否则使用常规 webdriver.Chrome。
    :return: Chrome WebDriver 实例。
    """
    service = Service(CHROME_DRIVER_PATH)
    options = webdriver.ChromeOptions()

    if use_undetected:
        driver_instance = uc.Chrome(options=options)
    else:
        driver_instance = webdriver.Chrome(service=service, options=options)
    driver_instance.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver_instance


def process_journal(name: str, issn: str, year_range: List[int]) -> None:
    """
    根据期刊名称和ISSN检索期刊，并收集指定年份的文章链接，将链接保存到文件中。

    :param name: 期刊名称
    :param issn: 期刊 ISSN
    :param year_range: [起始年份, 结束年份]
    """
    driver = load_chrome_driver(use_undetected=True)
    try:
        driver.get('https://navi.cnki.net/')
        time.sleep(0.5)
        logging.info(f"正在检索期刊: {name}，ISSN: {issn}，年份范围: {year_range[0]}-{year_range[1]}")

        # 选择检索方式为ISSN
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

        # 点击搜索按钮
        button_element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "btnSearch"))
        )
        button_element.click()

        # 等待页面加载完成并点击第一个期刊
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".re_bookCover"))
        ).click()

        time.sleep(0.5)
        # 切换到新打开的窗口
        driver.switch_to.window(driver.window_handles[-1])

        # 遍历指定年份，收集期刊文章链接
        for year in range(year_range[0], year_range[1] + 1):
            logging.info(f"正在检索 {name} {year} 年的期刊链接")
            year_id = f"{year}_Year_Issue"
            year_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, year_id))
            )
            # 展开年份下拉
            dt_element = WebDriverWait(year_element, 10).until(
                EC.element_to_be_clickable((By.TAG_NAME, "dt"))
            )
            dt_element.click()

            issue_elements = year_element.find_elements(By.CSS_SELECTOR, "dd a")
            all_links: List[str] = []
            for issue_element in issue_elements:
                # 等待期号链接可用
                WebDriverWait(driver, 10).until(lambda d: issue_element.is_enabled() and issue_element.is_displayed())
                issue_element.click()
                time.sleep(0.5)

                link_elements = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#CataLogContent span.name a"))
                )
                for link_element in link_elements:
                    link = link_element.get_attribute("href")
                    if link:
                        all_links.append(link)
                time.sleep(0.5)

            # 保存链接到文件
            output_file = os.path.join(LINK_DIR, f"{name}_{year}.txt")
            with open(output_file, 'w', encoding='utf-8') as f:
                for link in all_links:
                    f.write(link + '\n')
            logging.info(f"保存链接到文件: {output_file}")

    except Exception as e:
        logging.error(f"处理期刊 {name} 时发生错误: {e}", exc_info=True)
    finally:
        driver.quit()
        logging.debug("驱动已关闭。")


def load_journal_list(excel_file: str) -> List[Tuple[str, str]]:
    """
    从 Excel 文件中加载期刊列表。请修改这里的数据加载，根据你组织的待爬列表而定。

    :param excel_file: Excel 文件路径
    :return: 包含 (期刊名称, ISSN) 元组的列表
    """
    try:
        df = pd.read_excel(excel_file, header=None)
        journal_list = [(str(row[0]).strip(), str(row[1]).strip()) for row in df.values if pd.notna(row[0])]
        logging.debug(f"加载期刊数量: {len(journal_list)}")
        return journal_list
    except Exception as e:
        logging.error(f"读取Excel文件 {excel_file} 失败: {e}")
        return []


def main() -> None:
    """
    主函数：确保目录存在、加载期刊列表，并依次处理每个期刊。
    """
    ensure_directory_exists(SAVE_DIR)
    ensure_directory_exists(LINK_DIR)

    journals = load_journal_list(EXCEL_FILE)
    for name, issn in journals:
        process_journal(name, issn, YEAR_RANGE)
        time.sleep(2)


if __name__ == "__main__":
    main()
