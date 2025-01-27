import os
import random
from PIL import Image

# 设置路径
image_folder = "xiaohongshu_oeasy/downloaded_images"
output_image_path = "final_collage.jpg"

# 拼接参数
grid_rows = 20  # 行数
grid_cols = 50  # 列数
max_width = 5000  # 横向最大像素

# 获取所有图片并打乱顺序
image_files = [f for f in os.listdir(image_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
random.shuffle(image_files)

# 确保有足够的图片
if len(image_files) < grid_rows * grid_cols:
    raise ValueError(f"图片数量不足，共有 {len(image_files)} 张，至少需要 {grid_rows * grid_cols} 张图片")

# 读取第一张图片，计算缩放比例
with Image.open(os.path.join(image_folder, image_files[0])) as img:
    img_width, img_height = img.size

# 计算每张图片的新宽度，确保横向最大像素不超过 5000
target_width = max_width // grid_cols
target_height = int((target_width / img_width) * img_height)

# 创建最终大画布
final_width = target_width * grid_cols
final_height = target_height * grid_rows
collage_image = Image.new("RGB", (final_width, final_height))

# 逐行拼接，减少内存占用
for row in range(grid_rows):
    row_images = []
    for col in range(grid_cols):
        idx = row * grid_cols + col
        img_path = os.path.join(image_folder, image_files[idx])
        with Image.open(img_path) as img:
            img_resized = img.resize((target_width, target_height))
            row_images.append(img_resized)

    # 拼接整行
    row_image = Image.new("RGB", (final_width, target_height))
    x_offset = 0
    for img in row_images:
        row_image.paste(img, (x_offset, 0))
        x_offset += target_width
    
    # 粘贴整行到最终图像
    collage_image.paste(row_image, (0, row * target_height))
    print(f"拼接第 {row + 1}/{grid_rows} 行完成")

# 保存最终拼接的图像
collage_image.save(output_image_path, quality=95)
print(f"拼接完成，已保存至 {output_image_path}")