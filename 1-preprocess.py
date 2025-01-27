import json
import re
from datetime import datetime, timedelta

CHINA_REGIONS = [
    "北京", "天津", "上海", "重庆", "河北", "山西", "辽宁", "吉林", "黑龙江", "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南", "湖北", "湖南", "广东", "海南", "四川", "贵州", "云南", "陕西", "甘肃", "青海", "台湾", "内蒙古", "广西", "西藏", "宁夏", "新疆"
]

def read_jsonl(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return [json.loads(line) for line in file]

def extract_id(note_url):
    match = re.search(r'/search_result/(\w+)', note_url)
    return match.group(1) if match else None

def process_numbers(value):
    if value in ["点赞", "收藏", "评论"]:
        return 0
    if "万" in value:
        return int(float(value.replace("万", "")) * 10000)
    return int(value)

def process_time(time_str):
    time_str = re.sub(r"^编辑于 ", "", time_str)
    today = datetime.strptime("01-26", "%m-%d")
    if match := re.match(r"今天 \d{2}:\d{2}", time_str):
        return "01-26", time_str.split()[-1]
    if match := re.match(r"昨天 \d{2}:\d{2}", time_str):
        return "01-25", time_str.split()[-1]
    if match := re.match(r"(\d+) 天前", time_str):
        days_ago = int(match.group(1))
        date_str = (today - timedelta(days=days_ago)).strftime("%m-%d")
        return date_str, time_str.split()[-1]
    if match := re.match(r"(\d{2}-\d{2}) (.+)", time_str):
        return match.groups()
    return time_str, ""

def process_data(records):
    unique_records = {}
    for record in records:
        record_id = extract_id(record["note_url"])
        if not record_id:
            continue
        record["id"] = record_id
        record["likes"] = process_numbers(record["likes"])
        record["favorites"] = process_numbers(record["favorites"])
        record["comments"] = process_numbers(record["comments"])
        record["time"], record["ip"] = process_time(record["time"])
        if record["ip"] in CHINA_REGIONS:
            continue
        unique_records[record_id] = record
    return list(unique_records.values())

def restructure_data(records):
    keys_order = [
        "id", "user_nickname", "title", "text", "tags", "likes", "favorites", "comments", "time", "ip", "note_url", "images", "user_home", "avatar_image"
    ]
    for record in records:
        record.pop("keyword", None)
    return [{key: record[key] for key in keys_order} for record in records]

def write_jsonl(file_path, records):
    with open(file_path, 'w', encoding='utf-8') as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + '\n')

file_path = '小红书/processed_notes.jsonl'
processed_records = process_data(read_jsonl(file_path))
restructured_records = restructure_data(processed_records)
output_file_path = '/Users/jhx/Documents/Code/processed_notes_data1.jsonl'
write_jsonl(output_file_path, restructured_records)

print("数据处理完成，输出文件为:", output_file_path)