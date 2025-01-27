import csv
import os
import random
import time
import json
import re

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from urllib.parse import quote

# ========== 全局配置部分 ==========

chrome_driver_path = ""  
user_data_dir = ""      
max_notes = 500  # 每个关键词最多抓取的笔记数

# 实时输出的 JSONL 文件：保存笔记链接 & 详细内容
jsonl_output_file = "notes.jsonl"
# CSV 输出目录
output_dir = 'csv'
os.makedirs(output_dir, exist_ok=True)

# 需要搜索的关键词列表
keywords = ["tiktokrefugee"]  # 可添加更多关键词

print("启动中，请等待...")

# ======== 启动浏览器 ========
service = Service(chrome_driver_path)
options = Options()
options.add_argument("--remote-debugging-port=9222")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument(f"--user-data-dir={user_data_dir}")
options.add_argument("--disable-blink-features=AutomationControlled")  # 绕过反爬机制

driver = webdriver.Chrome(service=service, options=options)
print("启动完成，请手动登录小红书...")

# 打开小红书主页，用户手动登录
driver.get("https://www.xiaohongshu.com")
input("请在打开的浏览器窗口中手动完成登录，登录完成后按回车键继续...")

driver.refresh()
print("已成功完成登录，开始爬取数据...\n")

# ========== 工具函数部分 ==========

def scroll_and_get_links(driver, max_count=1000):
    """
    滚动页面并动态获取笔记链接信息，直到获取到 max_count 条或无法继续加载更多。
    """
    links = []
    last_height = 0

    while len(links) < max_count:
        soup = BeautifulSoup(driver.page_source, "html.parser")
        a_tags = soup.find_all('a', class_='cover')

        for a in a_tags:
            href = a.get('href', '')
            if href and ("/explore/" in href or "/search_result/" in href):
                full_url = f"https://www.xiaohongshu.com{href}"
                if full_url not in links:
                    links.append(full_url)
                    if len(links) >= max_count:
                        break

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2 + random.uniform(1, 2))

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            # 页面高度不变，说明到底或无法再加载更多
            break
        last_height = new_height

    return links

def safe_find_element(driver, by, selector):
    """安全查找单个元素，若找不到则返回 None。"""
    try:
        return driver.find_element(by, selector)
    except:
        return None

def safe_find_elements(driver, by, selector):
    """安全查找多个元素，若找不到则返回空列表。"""
    try:
        return driver.find_elements(by, selector)
    except:
        return []

def extract_video_poster_url(style_str):
    """
    从 xg-poster 的 style 属性中解析出背景图片 URL。
    形如 background-image: url("http://xxx.jpg");
    用正则匹配双引号内的地址。
    """
    pattern = r'url$begin:math:text$"(.*?)"$end:math:text$'
    match = re.search(pattern, style_str)
    if match:
        return match.group(1)
    return None

def extract_note_details(driver, url):
    """
    访问笔记详情页，抽取所需字段并返回字典形式的数据。
    包括笔记图片、视频封面(若有)、用户主页、头像、昵称、标题、标签、文本、时间、点赞、收藏、评论。
    """
    data = {
        "note_url": url,
        "images": [],
        "user_home": "",
        "avatar_image": "",
        "user_nickname": "",
        "title": "",
        "tags": [],
        "text": "",
        "time": "",   
        "likes": "0",
        "favorites": "0",
        "comments": "0"
    }

    driver.get(url)
    time.sleep(1 + random.uniform(0.5, 2))

    # ========== 图片处理 ========== 
    img_urls = set()
    # 1) 抓取所有图片
    imgs = safe_find_elements(
        driver,
        By.XPATH,
        '//*[@id="noteContainer"]/div[2]/div/div/div[2]/div/div[contains(@class,"")]//img'
    )
    for img_el in imgs:
        src = img_el.get_attribute("src")
        if src:
            img_urls.add(src)

    # 2) 不论是否有图片，都尝试抓取 xg-poster 里的封面图
    poster_el = safe_find_element(
        driver,
        By.XPATH,
        '//*[@id="noteContainer"]/div[2]/div/div/xg-poster'
    )
    if poster_el:
        style_str = poster_el.get_attribute("style")
        if style_str:
            poster_url = extract_video_poster_url(style_str)
            if poster_url:
                img_urls.add(poster_url)

    data["images"] = list(img_urls)

    # ========== 用户主页、头像、昵称 ==========
    user_home_el = safe_find_element(
        driver,
        By.XPATH,
        '//*[@id="noteContainer"]/div[4]/div[1]/div/div[1]/a[1]'
    )
    if user_home_el:
        home_href = user_home_el.get_attribute("href")
        if home_href:
            data["user_home"] = home_href

    avatar_img_el = safe_find_element(
        driver,
        By.XPATH,
        '//*[@id="noteContainer"]/div[4]/div[1]/div/div[1]/a[1]/img'
    )
    if avatar_img_el:
        avatar_src = avatar_img_el.get_attribute("src")
        if avatar_src:
            data["avatar_image"] = avatar_src

    nickname_el = safe_find_element(
        driver,
        By.XPATH,
        '//*[@id="noteContainer"]/div[4]/div[1]/div/div[1]/a[2]/span'
    )
    if nickname_el:
        data["user_nickname"] = nickname_el.text.strip()

    # ========== 标题 ==========
    title_el = safe_find_element(driver, By.XPATH, '//*[@id="detail-title"]')
    if title_el:
        data["title"] = title_el.text.strip()

    # ========== 标签 & 文本（描述） ==========
    desc_el = safe_find_element(driver, By.XPATH, '//*[@id="detail-desc"]/span')
    if desc_el:
        full_text = desc_el.text.strip()
        # 提取标签
        tag_elements = desc_el.find_elements(By.TAG_NAME, "a")
        tag_list = []
        for t in tag_elements:
            tag_txt = t.text.strip()
            if tag_txt.startswith("#"):
                tag_list.append(tag_txt)
        data["tags"] = tag_list
        data["text"] = full_text

    # ========== 时间 ==========
    soup = BeautifulSoup(driver.page_source, "html.parser")
    date_span = soup.find('span', class_="date")
    if date_span:
        data["time"] = date_span.get_text(strip=True)

    # ========== 点赞、收藏、评论 ==========
    likes_el = safe_find_element(
        driver,
        By.XPATH,
        '//*[@id="noteContainer"]/div[4]/div[3]/div/div/div[1]/div[2]/div/div[1]/span[1]/span[2]'
    )
    if likes_el:
        data["likes"] = likes_el.text.strip()

    fav_el = safe_find_element(
        driver,
        By.XPATH,
        '//*[@id="note-page-collect-board-guide"]/span'
    )
    if fav_el:
        data["favorites"] = fav_el.text.strip()

    comment_el = safe_find_element(
        driver,
        By.XPATH,
        '//*[@id="noteContainer"]/div[4]/div[3]/div/div/div[1]/div[2]/div/div[1]/span[3]/span'
    )
    if comment_el:
        data["comments"] = comment_el.text.strip()

    return data

# ========== 主流程 ==========

base_url = "https://www.xiaohongshu.com/search_result?keyword="
total_expected = len(keywords) * max_notes  # 预期总抓取量（链接数）
all_collected_links = 0
all_detail_count = 0

with open(jsonl_output_file, "a", encoding="utf-8") as jsonl_file:
    for keyword in keywords:
        # 第一个任务：滚动抓取笔记网址
        print(f"开始处理关键词：{keyword}")
        encoded_keyword = quote(keyword)
        search_url = f"{base_url}{encoded_keyword}"
        driver.get(search_url)
        time.sleep(3 + random.uniform(1, 3))

        note_links = scroll_and_get_links(driver, max_count=max_notes)
        found_count = len(note_links)
        all_collected_links += found_count

        # 第一个任务完成，汇报抓取结果
        print(f"第一个任务完成：关键词【{keyword}】，共抓取 {found_count} 条网址。")

        # 第二个任务：采集每个网址的笔记详情
        csv_filename = os.path.join(output_dir, f"{keyword}.csv")
        with open(csv_filename, "w", encoding='utf8', newline='') as fp:
            writer = csv.writer(fp)
            writer.writerow([
                '笔记链接', '标题', '喜欢数', '收藏数', '评论数',
                '时间', '笔记图片', '用户主页', '头像图片',
                '用户昵称', '标签', '文本'
            ])

            detail_count = 0
            for url in note_links:
                note_data = extract_note_details(driver, url)
                detail_count += 1
                all_detail_count += 1

                # 写入 CSV（可根据需要保留或去除）
                writer.writerow([
                    note_data["note_url"],
                    note_data["title"],
                    note_data["likes"],
                    note_data["favorites"],
                    note_data["comments"],
                    note_data["time"],
                    "|".join(note_data["images"]),
                    note_data["user_home"],
                    note_data["avatar_image"],
                    note_data["user_nickname"],
                    "|".join(note_data["tags"]),
                    note_data["text"]
                ])

                # 实时写入 JSONL
                record = {"keyword": keyword, **note_data}
                jsonl_file.write(json.dumps(record, ensure_ascii=False) + "\n")
                jsonl_file.flush()

                # 每 10 条进度提示
                if detail_count % 10 == 0:
                    print(f"关键词【{keyword}】已抓取笔记详情 {detail_count} 条...")

        print(f"关键词【{keyword}】详情采集完毕，共抓取 {detail_count} 条。\n")

# 全部关键词处理完毕，输出整体结果
print("所有关键词处理结束。")
print(f"预期抓取笔记链接总数：{total_expected}，实际获取笔记链接总数：{all_collected_links}")
print(f"共采集到笔记详情：{all_detail_count} 条。")
driver.quit()
print("程序运行结束。")