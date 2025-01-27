import os
import json

# 读取和下载图片的库
import requests

# 定义文件路径
jsonl_file_path = "preprocessed_data.jsonl"
save_directory = "xiaohongshu_oeasy/downloaded_images"

# 确保保存目录存在
if not os.path.exists(save_directory):
    os.makedirs(save_directory)

# 读取 JSONL 文件并解析
def download_images_from_jsonl(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            try:
                # 解析 JSON 行
                note = json.loads(line.strip())
                images = note.get("images", [])
                
                for index, image_url in enumerate(images):
                    try:
                        # 获取图片内容
                        response = requests.get(image_url, stream=True)
                        if response.status_code == 200:
                            # 构造文件名，使用笔记标题+序号
                            title_safe = note.get("title", "untitled").replace(" ", "_").replace("/", "_")
                            file_name = f"{title_safe}_{index + 1}.webp"
                            file_path = os.path.join(save_directory, file_name)
                            
                            # 保存图片到本地
                            with open(file_path, 'wb') as img_file:
                                for chunk in response.iter_content(1024):
                                    img_file.write(chunk)
                            
                            print(f"图片已下载: {file_path}")
                        else:
                            print(f"无法下载图片: {image_url}，状态码: {response.status_code}")
                    except Exception as e:
                        print(f"下载图片失败: {image_url}，错误: {e}")
            except json.JSONDecodeError as e:
                print(f"JSON解析错误: {e}")

# 执行下载任务
download_images_from_jsonl(jsonl_file_path)

print("所有图片下载完成！")