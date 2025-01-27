# -*- coding: utf-8 -*-

import json
import jieba
from sklearn.feature_extraction.text import TfidfVectorizer
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from matplotlib.font_manager import FontProperties
import os

# ========== 文件路径部分：请根据需要修改 ==========
# 输入文件：应是分词后含 'text_processed' 字段的 JSONL 文件
data_file = 'preprocessed_data.jsonl'
# 停用词表（可选），若无需则留空
stopword_path = ''
# 字体文件路径（用于绘制中文词云）
font_path = ''
# 输出结果文件
output_tfidf_json = 'tfidf_result.json'
output_wordcloud_img = 'wordcloud.png'

def main():
    # 1. 读取 JSONL 文件
    data = []
    with open(data_file, 'r', encoding='utf-8') as f:
        for line in f:
            data.append(json.loads(line))

    # 提取已分好词的字段（text_processed）
    texts_processed = [item['text_processed'] for item in data if 'text_processed' in item]

    # 2. 加载停用词（可选）
    stopwords = []
    if stopword_path:
        try:
            with open(stopword_path, 'r', encoding='utf-8') as f:
                stopwords = f.read().splitlines()
        except:
            print("停用词文件读取失败。")

    # 3. TF-IDF 词频统计
    # 调整 max_features 以控制选取多少高频词
    max_features = 100
    vectorizer = TfidfVectorizer(
        stop_words=stopwords,
        max_features=max_features,
        token_pattern=r"(?u)\b\w+\b",
        analyzer='word'
    )
    tfidf_matrix = vectorizer.fit_transform(texts_processed)

    feature_names = vectorizer.get_feature_names_out()
    tfidf_scores = tfidf_matrix.toarray().sum(axis=0)

    # 生成词频统计结果
    tfidf_dict = dict(zip(feature_names, tfidf_scores))
    sorted_tfidf = sorted(tfidf_dict.items(), key=lambda x: x[1], reverse=True)
    result_list = [{"word": w, "score": s} for w, s in sorted_tfidf]

    # 4. 保存 TF-IDF 结果为 JSON
    with open(output_tfidf_json, 'w', encoding='utf-8') as f:
        json.dump(result_list, f, ensure_ascii=False, indent=4)
    print(f"TF-IDF 结果已保存至 '{output_tfidf_json}'。")

    # 5. 读取保存的 JSON 生成词云
    word_freq = {item['word']: item['score'] for item in result_list}

    wordcloud = WordCloud(
        font_path=font_path,
        width=800,
        height=400,
        background_color='white'
    )

    try:
        wordcloud.generate_from_frequencies(word_freq)
    except AttributeError as e:
        print("生成词云出错，可能与 Pillow 或 wordcloud 库版本相关。请检查并尝试升级/降级相应库。")
        raise e

    # 显示并保存词云图
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.title("词云图", fontproperties=FontProperties(fname=font_path))

    plt.savefig(output_wordcloud_img)
    plt.show()

    print(f"词云图已保存至 '{output_wordcloud_img}'。")

if __name__ == '__main__':
    main()