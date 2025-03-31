import os
import time
import logging
from typing import List
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from seleniumwire import webdriver

# 配置
DEBUG = False
CHROME_DRIVER_PATH = r'C:\Program Files\chromedriver-win64\chromedriver.exe'
SAVE_DIR = 'saves'
LINK_DIR = 'links'
KEYWORDS = {'相对论'}  # 待搜索关键词集合
RESULT_COUNT = 60  # 每个关键词搜索结果数量

driver = None

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


def load_chrome_driver() -> webdriver.Chrome:
    """
    初始化并返回 Chrome 驱动实例，同时配置下载目录等参数。
    """
    service = Service(CHROME_DRIVER_PATH)
    options = webdriver.ChromeOptions()

    if not DEBUG:
        options.add_argument('--headless')
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--enable-unsafe-swiftshader")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36")

    # 设置下载目录，并确保目录为绝对路径
    abs_save_dir = os.path.abspath(SAVE_DIR)
    options.add_experimental_option("prefs", {
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
        "safebrowsing.enabled": False,
        "download.default_directory": abs_save_dir,
    })

    driver_instance = webdriver.Chrome(service=service, options=options)
    # 绕过 webdriver 检测
    driver_instance.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver_instance.get('https://kns.cnki.net/kns8s/defaultresult/index')
    driver_instance.refresh()
    return driver_instance


def scrape_keyword(keyword: str, result_count: int) -> None:
    """
    根据关键词爬取搜索结果链接，并保存到指定文件中。

    :param keyword: 搜索关键词
    :param result_count: 需要爬取的结果数量
    """
    url = f'https://kns.cnki.net/kns8s/defaultresult/index?kw={keyword}'
    driver.get(url)
    time.sleep(2)

    links: List[str] = []
    dates: List[str] = []
    names: List[str] = []

    try:
        per_page_div = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'perPageDiv'))
        )
        per_page_div.click()
        # 等待排序列表加载
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'ul.sort-list'))
        )
        # 找到“50”这一分页选项并点击
        page_50_locator = (By.CSS_SELECTOR, 'li[data-val="50"] a')
        page_50 = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(page_50_locator)
        )
        page_50.click()
        time.sleep(2)
    except Exception as e:
        logging.error(f"点击分页选项时出错: {e}")

    while len(links) < result_count:
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        fz14_links = soup.select('.fz14')
        date_cells = soup.select('.date')

        # 遍历当前页面的所有搜索结果
        for link_tag, date_cell, name_tag in zip(fz14_links, date_cells, fz14_links):
            if link_tag.has_attr('href'):
                date_text = date_cell.get_text(strip=True)
                year = date_text.split('-')[0]
                links.append(link_tag['href'])
                dates.append(year)
                names.append(name_tag.get_text(strip=True))

                if len(links) >= result_count:
                    break

        if len(links) < result_count:
            try:
                next_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, 'PageNext'))
                )
                if 'disabled' in next_button.get_attribute('class'):
                    break
                next_button.click()
                time.sleep(1.5)
            except Exception as e:
                logging.error(f"翻页失败: {e}")
                break

    # 保存结果到文件，文件名以关键词命名，后缀设为 .txt
    output_file = os.path.join(LINK_DIR, f"{keyword}.txt")
    with open(output_file, 'w', encoding='utf-8') as file:
        for link, year, name in zip(links, dates, names):
            file.write(f'{name} -||- {year} -||- {link}\n')

    logging.info(f"主题为 {keyword} 的链接已保存到 {output_file}")


def main() -> None:
    """
    主函数：确保目录存在、初始化驱动、依次爬取各关键词，并在结束后关闭驱动。
    """
    global driver
    # 确保保存下载文件和链接文件的目录存在
    ensure_directory_exists(SAVE_DIR)
    ensure_directory_exists(LINK_DIR)

    driver = load_chrome_driver()

    try:
        for keyword in KEYWORDS:
            scrape_keyword(keyword, RESULT_COUNT)
    finally:
        if driver:
            driver.quit()
            logging.info("驱动已关闭。")


if __name__ == "__main__":
    main()
