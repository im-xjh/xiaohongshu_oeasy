import os
import pandas as pd
import re
import json
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
from gensim.models.coherencemodel import CoherenceModel
from gensim.corpora.dictionary import Dictionary
import numpy as np
import matplotlib.pyplot as plt
import pyLDAvis
from tqdm import tqdm
from matplotlib import font_manager

# 设置文件路径
preprocessed_file = ''  # 预处理后的数据文件路径

def main():
    # 1. 读取预处理后的数据
    data = []
    with open(preprocessed_file, 'r', encoding='utf-8') as f:
        for line in f:
            item = json.loads(line)
            text = item.get('text', '')
            text_processed = item.get('text_processed', '')
            if text_processed:
                data.append({'text': text, 'text_processed': text_processed})
    data = pd.DataFrame(data)

    print("预处理后的数据加载完成。")

    # 2. 特征提取
    n_features = 1000  # 提取 1000 个特征词语
    tf_vectorizer = CountVectorizer(strip_accents='unicode',
                                    max_features=n_features,
                                    max_df=0.5,
                                    min_df=10)
    tf = tf_vectorizer.fit_transform(data['text_processed'])
    print("特征提取完成。")

    # 3. 准备文本数据和词典
    texts = data['text_processed'].apply(lambda x: x.split()).tolist()
    dictionary = Dictionary(texts)

    # 4. 自定义主题数量范围
    min_topics = 4  # 最小主题数
    max_topics = 12  # 最大主题数
    topic_range = range(min_topics, max_topics + 1)

    # 5. 准备存储困惑度和一致性数据
    plexs = []
    coherences = []

    # 6. 设置中文字体
    font_path = ''  # 指定的中文字体路径
    font_prop = font_manager.FontProperties(fname=font_path)
    plt.rcParams['font.family'] = font_prop.get_name()
    plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

    # 7. 计算困惑度和一致性，并生成 LDA 模型
    print("开始计算困惑度和一致性，并生成 LDA 模型...")
    for n_topics in tqdm(topic_range):
        lda = LatentDirichletAllocation(n_components=n_topics, max_iter=50,
                                        learning_method='batch',
                                        learning_offset=50, random_state=0)
        lda.fit(tf)
        perplexity = lda.perplexity(tf)
        plexs.append(perplexity)

        # 获取主题词
        tf_feature_names = tf_vectorizer.get_feature_names_out()
        n_top_words = 20
        topics = []
        for topic_idx, topic in enumerate(lda.components_):
            topic_words = [tf_feature_names[i] for i in topic.argsort()[:-n_top_words -1:-1]]
            topics.append(topic_words)

        # 计算一致性
        cm = CoherenceModel(topics=topics, texts=texts, dictionary=dictionary, coherence='c_v', processes=1)
        coherence = cm.get_coherence()
        coherences.append(coherence)

        # 显示进度信息
        print(f"主题数：{n_topics}, 困惑度：{perplexity:.4f}, 一致性：{coherence:.4f}")


        # 8. 保存每个主题数量对应的 LDA 可视化文件
        print(f"正在生成主题数为 {n_topics} 的可视化文件...")
        doc_topic_distr = lda.transform(tf)
        doc_lengths = np.array(tf.sum(axis=1)).flatten()
        term_frequency = np.array(tf.sum(axis=0)).flatten()
        vocab = tf_vectorizer.get_feature_names_out()
        topic_term_dists = lda.components_ / lda.components_.sum(axis=1)[:, np.newaxis]
        doc_topic_dists = doc_topic_distr

        vis_data = pyLDAvis.prepare(topic_term_dists, doc_topic_dists, doc_lengths, vocab, term_frequency)
        vis_file = f'lda_visualization_{n_topics}.html'
        pyLDAvis.save_html(vis_data, vis_file)
        print(f"主题数为 {n_topics} 的可视化结果已保存为 '{vis_file}' 文件。")

        # 9. 如果需要，保存每个主题数量对应的结果文件
        # 如果生成速度快，可以取消以下注释，保存每个主题数量对应的结果文件
        
        print(f"正在保存主题数为 {n_topics} 的结果文件...")
        # 添加主题分布到 DataFrame
        for i in range(n_topics):
            data[f'topic{i+1}'] = doc_topic_distr[:, i]

        # 获取每篇文档的主要主题
        data['max_topic'] = doc_topic_distr.argmax(axis=1) + 1

        # 保存结果到 jsonl 文件
        result_file = f'data_with_topics_{n_topics}.jsonl'
        with open(result_file, 'w', encoding='utf-8') as f_out:
            for index, row in data.iterrows():
                record = {
                    'text': row['text'],
                    'text_processed': row['text_processed'],
                    'max_topic': int(row['max_topic']),
                    'topic_distribution': {f'topic{i+1}': float(row[f'topic{i+1}']) for i in range(n_topics)}
                }
                f_out.write(json.dumps(record, ensure_ascii=False) + '\n')
        print(f"主题数为 {n_topics} 的结果已保存为 '{result_file}' 文件。")
        

        # 10. 保存主题词到 CSV 文件
        topics_df = pd.DataFrame()
        for idx, topic_words in enumerate(topics):
            topics_df[f'topic{idx+1}_word'] = topic_words

        topics_file = f'lda_topics_{n_topics}.csv'
        topics_df.to_csv(topics_file, index=False, encoding='utf-8-sig')
        print(f"主题数为 {n_topics} 的主题词已保存为 '{topics_file}' 文件。")

    print("所有主题数量的模型训练和结果保存已完成。")

    # 11. 绘制困惑度和一致性曲线
    x = list(topic_range)

    plt.figure(figsize=(12, 5))

    plt.subplot(1, 2, 1)
    plt.plot(x, plexs, marker='o')
    plt.xlabel('主题数', fontproperties=font_prop)
    plt.ylabel('困惑度', fontproperties=font_prop)
    plt.title('困惑度随主题数的变化', fontproperties=font_prop)

    plt.subplot(1, 2, 2)
    plt.plot(x, coherences, marker='o', color='red')
    plt.xlabel('主题数', fontproperties=font_prop)
    plt.ylabel('一致性', fontproperties=font_prop)
    plt.title('一致性随主题数的变化', fontproperties=font_prop)

    plt.tight_layout()
    plt.savefig('perplexity_coherence.png', dpi=300)
    plt.show()
    print("困惑度和一致性曲线已保存为 'perplexity_coherence.png'。")

if __name__ == '__main__':
    main()