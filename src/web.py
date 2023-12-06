from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from datetime import datetime
import os
import time
import re
import json

import requests

from bs4 import BeautifulSoup


os.makedirs('data', exist_ok=True)
# アクセスしてみる
driver = webdriver.Firefox()


def save(
    from_: str,  # yyyymmdd
    to_: str,  # yyyymmdd
    kw: str,
):
    folder_name = f'{from_}_{to_}_{kw}'
    os.makedirs(os.path.join('data', folder_name), exist_ok=True)
    _search_and_save(from_, to_, kw, folder_name)
    _extract_article(folder_name)


def _search_and_save(from_date: datetime, to_date: datetime, kw: str, folder_name: str):
    driver.get("https://archive.chosun.com/pdf/i_service/pdf_SearchList_s.jsp")
    word = driver.find_element(By.ID, 'FV')
    word.send_keys(kw)

    from_ = driver.find_element(By.ID, 'PD_F1')
    from_.send_keys(from_date)

    to_ = driver.find_element(By.ID, 'PD_F2')
    to_.send_keys(to_date)

    radios = driver.find_elements(By.ID, 'PD_TYPE')
    radios[0].click()
    radios[1].click()

    period = driver.find_element(By.ID, 'PD_OP')
    Select(period).select_by_index(0)

    number = driver.find_element(By.ID, 'sRowsperPage')
    Select(number).select_by_index(2)

    driver.execute_script('javascript:fnNavigate();')

    article_links = []

    time.sleep(5)

    # 最後のページを確認しておく
    try:
        pagination_elements = driver.find_element(By.CLASS_NAME, 'paginate').find_elements(By.TAG_NAME, 'a')
        last_page = int(re.search(r'[1-9]+', pagination_elements[-1].get_attribute('href')).group(0))
    except:
        last_page = 1
    print(f'last page: {last_page}')

    for page in range(last_page):
        # 記事を探す
        articles_elements = driver.find_elements(By.CSS_SELECTOR, 'span.list_tit')

        for ele in articles_elements:
            print()
            article_links.append({
                'title': ele.find_element(By.TAG_NAME, 'a').text,
                'link': ele.find_element(By.TAG_NAME, 'a').get_attribute('href'),
            })

        next_page = page + 2
        driver.execute_script(f"javascript:fnClickPageNavigation('{next_page}')")
        time.sleep(1)

    with open(os.path.join('data', folder_name, 'links.json'), 'w') as f:
        json.dump(article_links, f, ensure_ascii=False)


def _extract_article(folder_name):
    with open(os.path.join('data', folder_name, 'links.json'), 'r') as f:
        articles = json.load(f)

    for article in articles:
        res = requests.get(article['link'])
        print(f'processing: {article["title"]}')

        soup = BeautifulSoup(res.text, 'html.parser')

        # 記事本文を挿入
        article_div = soup.select_one('div#article.article')
        article['article'] = article_div.text

        # 記者名を探す
        writer_name = None
        for line in article_div.text.split('\n'):
            if line.startswith('기고자'):
                writer_name = line
                break

        article['writer'] = writer_name

        # Extract date in yyyy.mm.dd format
        date_text = soup.select_one('p#date_text')
        date_pattern = r'\d{4}\.\d{2}\.\d{2}'
        match = re.search(date_pattern, date_text.text)
        if match:
            extracted_date = match.group()
        else:
            extracted_date = None

        article['date'] = extracted_date

    with open(os.path.join('data', folder_name, 'articles.json'), 'w') as f:
        json.dump(articles, f, indent=4, ensure_ascii=False)
