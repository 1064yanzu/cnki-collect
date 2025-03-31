import os
import random
import time
import sys
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains

# 全局配置
DEBUG = True
HEADLESS = False
CHROME_DRIVER_PATH = r'C:\Program Files\chromedriver-win64\chromedriver.exe'  # 请根据实际情况修改
SAVE_DIR = 'saves'
LINK_DIR = 'links'
FILE_TYPE = 'pdf'  # 可选 'pdf' 或 'caj'
MAX_WORKERS = 2         # 同时处理的任务数
BATCH_SIZE = 45         # 每下载 BATCH_SIZE 篇文章休息一次
MAX_RETRIES = 3         # 最大重试次数

# 日志配置
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def ensure_directory(directory: str) -> None:
    """确保目录存在，不存在则创建。"""
    if not os.path.exists(directory):
        os.makedirs(directory)
        logging.debug(f"Directory created: {directory}")

def load_chrome_driver(download_dir: str = None) -> webdriver.Chrome:
    """
    加载并配置一个新的 ChromeDriver 实例
    :param download_dir: 指定下载目录（绝对路径）
    :return: 配置好的 WebDriver 实例
    """
    options = webdriver.ChromeOptions()
    service = Service(CHROME_DRIVER_PATH)
    if HEADLESS:
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--disable-images')
        options.add_argument('--disable-extensions')
        options.add_argument('--window-size=1920x1080')
    prefs = {
        "download.default_directory": os.path.abspath(download_dir) if download_dir else os.path.abspath(SAVE_DIR),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
        "safebrowsing.enabled": False,
    }
    options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def simulate_human_behavior(driver: webdriver.Chrome) -> None:
    """
    模拟人类行为闲逛，降低被网站检测为机器人的风险
    """
    try:
        driver.get('https://kns.cnki.net/kns8s/defaultresult/index')
        time.sleep(random.uniform(1, 1.5))
        driver.get('https://kns.cnki.net/kns8s/defaultresult/index?kw=丁真')
        time.sleep(random.uniform(1, 1.5))
        try:
            next_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, 'PageNext'))
            )
            if 'disabled' not in next_button.get_attribute('class'):
                next_button.click()
        except Exception as e:
            logging.debug(f"Page next click failed in human behavior simulation: {e}")
        el = ('https://kns.cnki.net/kcms2/article/abstract?v='
              'jNHD1hIvxn3V4QTDlEMKElsHKaTntLnuqQcAeWVTldLPFBn7iT-1Tm4UqqAiMvAEyHpC5baI1wNaLNYpxJrWNLLA-'
              'qwDCdqTs7Q_qbXKpcOcTkzjDVW1nndiqngcWd2EQjyOwhwnX44UVtGVXou0tJJ1uxIBDd_iR7mmJhaA88A=&uniplatform=NZKPT')
        driver.get(el)
        for _ in range(24):
            driver.refresh()
            time.sleep(random.uniform(0.18, 0.4))
    except Exception as e:
        logging.error(f"Error in human behavior simulation: {e}")

def attempt_download(driver: webdriver.Chrome, link: str, index: int, name: str, year: str) -> bool:
    """
    尝试下载单篇文章，支持重试机制
    :return: 下载成功返回 True，否则返回 False
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            driver.get(link)
            time.sleep(1)
            try:
                driver.execute_script("redirectNewLink()")
            except Exception:
                pass
            for _ in range(2):
                driver.refresh()
                time.sleep(1)
                try:
                    driver.execute_script("redirectNewLink()")
                except Exception:
                    pass
            time.sleep(0.5)
            css_selector = '.btn-dlpdf a' if FILE_TYPE == 'pdf' else '.btn-dlcaj a'
            link_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
            )
            download_link = link_element.get_attribute('href')
            if download_link:
                ActionChains(driver).move_to_element(link_element).click(link_element).perform()
                driver.switch_to.window(driver.window_handles[-1])
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'html'))
                )
                if "拼图校验" in driver.page_source:
                    logging.warning(f"{name} {year} article {index+1}: captcha triggered on attempt {attempt}")
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                    if attempt < MAX_RETRIES:
                        logging.info(f"{name} {year} article {index+1}: retrying (attempt {attempt})")
                        time.sleep(random.uniform(1, 2.5))
                        for _ in range(4):
                            driver.refresh()
                            time.sleep(random.uniform(0.8, 1.0))
                    continue
                else:
                    logging.info(f"{name} {year} article {index+1} downloaded successfully on attempt {attempt}")
                    driver.switch_to.window(driver.window_handles[0])
                    return True
        except Exception as e:
            logging.error(f"{name} {year} article {index+1}: error on attempt {attempt}: {e}")
            time.sleep(random.uniform(2, 4))
    return False

def download_for_year(name: str, year: str, links: list) -> None:
    """
    为指定期刊和年份下载文章，失败的链接会进行二次尝试
    """
    output_dir = os.path.join(SAVE_DIR, name, str(year))
    ensure_directory(output_dir)
    logging.info(f"Starting download for {name} {year}, saving to {output_dir}")

    driver = None
    num_success = 0
    num_skipped = 0
    skipped_links = []
    try:
        for idx, link in enumerate(links):
            if idx % BATCH_SIZE == 0:
                logging.info(f"{name} {year}: processed {idx} articles, taking a break...")
                time.sleep(5)
                if driver:
                    driver.quit()
                driver = load_chrome_driver(download_dir=output_dir)
                simulate_human_behavior(driver)
            if not attempt_download(driver, link, idx, name, year):
                num_skipped += 1
                skipped_links.append(link)
            else:
                num_success += 1

        # 对未下载成功的文章进行重新下载尝试
        if skipped_links:
            logging.info(f"{name} {year}: retrying {len(skipped_links)} skipped articles...")
            for idx, link in enumerate(skipped_links):
                if idx % BATCH_SIZE == 0:
                    logging.info(f"{name} {year}: reprocessing {idx} skipped articles, taking a break...")
                    time.sleep(5)
                    if driver:
                        driver.quit()
                    driver = load_chrome_driver(download_dir=output_dir)
                    simulate_human_behavior(driver)
                if attempt_download(driver, link, idx, name, year):
                    num_success += 1
                    num_skipped -= 1
                else:
                    logging.error(f"{name} {year}: article skipped after retries: {link}")
    except Exception as e:
        logging.error(f"Error processing {name} {year}: {e}")
    finally:
        if driver:
            driver.quit()
    logging.info(f"Finished {name} {year}: Success: {num_success}, Skipped: {num_skipped}")

def process_txt_file(file_path: str) -> None:
    """
    处理 link_dir 目录下的单个 txt 文件，文件名格式要求为：<期刊名>_<年份>.txt
    """
    base_name = os.path.basename(file_path)
    try:
        # 这里假定文件名格式为：name_year.txt，其中 year 为纯数字部分
        name_part, year_part = base_name.rsplit('_', 1)
        year = year_part.split('.')[0]
    except Exception as e:
        logging.error(f"Error parsing file name {base_name}: {e}")
        return
    with open(file_path, 'r', encoding='utf-8') as f:
        links = [line.strip() for line in f if line.strip()]
    logging.info(f"Processing file {base_name} with {len(links)} links")
    download_for_year(name_part, year, links)

def main() -> None:
    """
    主函数：扫描 link_dir 目录中所有 txt 文件，并利用线程池并发处理下载任务
    """
    if not os.path.exists(LINK_DIR):
        logging.error(f"Link directory {LINK_DIR} does not exist")
        return
    txt_files = [os.path.join(LINK_DIR, f) for f in os.listdir(LINK_DIR) if f.endswith('.txt')]
    if not txt_files:
        logging.error("No txt files found in link directory.")
        return
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_txt_file, file): file for file in txt_files}
        for future in as_completed(futures):
            file = futures[future]
            try:
                future.result()
                logging.info(f"Completed processing {file}")
            except Exception as e:
                logging.error(f"Error processing {file}: {e}")

if __name__ == '__main__':
    main()
