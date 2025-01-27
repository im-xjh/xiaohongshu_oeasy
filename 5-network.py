# -*- coding: utf-8 -*-

import json
import networkx as nx
import pandas as pd
from tqdm import tqdm

# ========== 文件路径部分：请根据需要修改 ==========
# 已经包含分词结果的 JSONL 文件（text_processed）
data_file = 'preprocessed_data.jsonl'
# 输出的节点表、边表
nodes_csv = 'network_nodes.csv'
edges_csv = 'network_edges.csv'

def read_jsonl(file_path):
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            item = json.loads(line)
            data.append(item)
    return data

def build_co_occurrence_network(words_list, window_size=2):
    """
    共现网络构建：
    以 window_size 窗口遍历 words_list（已经split好的分词列表），
    并在图中为每两个词添加边。
    """
    G = nx.Graph()
    length = len(words_list)
    for i in range(length - window_size + 1):
        for j in range(i+1, i+window_size):
            if j < length:
                w1, w2 = words_list[i], words_list[j]
                if G.has_edge(w1, w2):
                    G[w1][w2]['weight'] += 1
                else:
                    G.add_edge(w1, w2, weight=1)
    return G

def process_data(data):
    """
    合并所有文本的共现网络。
    """
    G_global = nx.Graph()
    for entry in tqdm(data, desc="处理数据", unit="条"):
        text_processed = entry.get('text_processed', '')
        if text_processed:
            words = text_processed.split()
            G_local = build_co_occurrence_network(words, window_size=2)
            G_global = nx.compose(G_global, G_local)
    return G_global

def generate_tables(G):
    """
    生成节点表和边表。
    """
    nodes = pd.DataFrame(list(G.nodes), columns=['Id'])
    nodes['Label'] = nodes['Id']  # 节点标签

    edges_data = []
    for source, target, attrs in G.edges(data=True):
        weight = attrs.get('weight', 1)
        edges_data.append([source, target, weight])
    edges = pd.DataFrame(edges_data, columns=['Source', 'Target', 'Weight'])

    return nodes, edges

def main():
    # 1. 读取数据
    data = read_jsonl(data_file)
    
    # 2. 构建全局共现网络
    G = process_data(data)
    
    # 3. 生成节点表、边表并保存
    nodes, edges = generate_tables(G)
    nodes.to_csv(nodes_csv, index=False, encoding='utf-8')
    edges.to_csv(edges_csv, index=False, encoding='utf-8')

    print(f"节点表格已保存至 {nodes_csv}，边表格已保存至 {edges_csv}。可在 Gephi 中导入。")

if __name__ == '__main__':
    main()