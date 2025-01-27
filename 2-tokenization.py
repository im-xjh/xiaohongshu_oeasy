import os
import re
import json
import jieba
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import pandas as pd
from tqdm import tqdm

# 文件路径配置
data_file = 'processed_notes.jsonl'  
output_file = 'preprocessed_data.jsonl'
cn_stop_file = 'stopword_cn.txt'  # 中文停用词文件
en_stop_file = 'stopwords_en.txt'  # 英文自定义停用词文件
custom_dict_file = ''  # 自定义中文词典文件

# 下载 NLTK 停用词表（若未下载过）
nltk.download('stopwords')

def load_stopwords(cn_stop_file_path, en_stop_file_path):
    """
    读取中文和英文停用词，返回停用词集合。
    - 中文停用词从 cn_stop_file_path 读取；
    - 英文停用词从 en_stop_file_path 和 nltk 自带停用词合并。
    """
    stopwords_set = set()

    # 加载本地中文停用词
    if cn_stop_file_path and os.path.exists(cn_stop_file_path):
        with open(cn_stop_file_path, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
            stopwords_set.update([w.strip() for w in lines if w.strip()])
        print("中文停用词已加载。")
    else:
        print("未找到中文停用词文件，将不使用本地中文停用词。")

    # 加载本地英文停用词
    if en_stop_file_path and os.path.exists(en_stop_file_path):
        with open(en_stop_file_path, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
            stopwords_set.update([w.strip().lower() for w in lines if w.strip()])
        print("自定义英文停用词已加载。")
    else:
        print("未找到自定义英文停用词文件，将仅使用NLTK默认停用词。")

    # 加载 NLTK 自带的英文停用词
    nltk_stopwords = set(stopwords.words('english'))
    stopwords_set.update(nltk_stopwords)
    print("NLTK 英文停用词已加载。")

    return stopwords_set


def split_text_to_cn_en(text):
    """
    使用正则表达式，将文本分割成中英文片段的列表。
    """
    pattern = r'([\u4e00-\u9fa5]+)'
    parts = re.split(pattern, text)
    parts = [p.strip() for p in parts if p.strip()]
    return parts


def tokenize_mixed_text(text, stopwords=None):
    """
    对混合文本进行中英分割，再对中文部分用 jieba 分词，
    对英文部分用 nltk.word_tokenize 分词，最后合并结果并去除停用词。
    """
    if stopwords is None:
        stopwords = set()

    segments = split_text_to_cn_en(text)
    tokens = []

    for seg in segments:
        if re.match(r'^[\u4e00-\u9fa5]+$', seg):
            # 中文分词
            seg_cut = list(jieba.cut(seg))
            tokens.extend(seg_cut)
        else:
            # 英文分词，统一小写
            eng_tokens = word_tokenize(seg.lower())
            tokens.extend(eng_tokens)

    # 去停用词、去除无效字符
    cleaned_tokens = []
    for w in tokens:
        w_stripped = w.strip()
        if not w_stripped:
            continue
        if w_stripped in stopwords:
            continue
        cleaned_tokens.append(w_stripped)

    return cleaned_tokens


def main():
    # ========== 加载停用词 ==========
    stopwords = load_stopwords(cn_stop_file, en_stop_file)

    # ========== 加载自定义中文词典（若需要） ==========
    if custom_dict_file and os.path.exists(custom_dict_file):
        try:
            jieba.load_userdict(custom_dict_file)
            print(f"自定义词典加载成功：{custom_dict_file}")
        except Exception as e:
            print(f"加载自定义词典时出现错误: {e}")
    jieba.initialize()

    # ========== 读取原始 JSONL 数据 ==========
    data_records = []
    with open(data_file, 'r', encoding='utf-8') as f:
        for line in f:
            item = json.loads(line)
            text = item.get('text', '')
            if text:
                data_records.append(item)
    df = pd.DataFrame(data_records)

    # ========== 对 text 字段进行中英混合分词 ==========
    tqdm.pandas()
    print("开始对文本进行中英文分词处理...")
    df['text_processed'] = df['text'].progress_apply(
        lambda x: ' '.join(tokenize_mixed_text(x, stopwords=stopwords))
    )
    print("分词处理完成。")

    # ========== 保存处理结果 ==========
    df.to_json(output_file, orient='records', lines=True, force_ascii=False)
    print(f"处理后的数据已保存到: {output_file}")


if __name__ == '__main__':
    main()