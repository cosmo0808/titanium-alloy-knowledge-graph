# script/advanced_graph_mining.py - 高级图挖掘与知识发现系统
import json
import pandas as pd
import numpy as np
import networkx as nx
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
import logging
from collections import defaultdict, Counter
from sklearn.manifold import TSNE
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TitaniumGraphMiner:
    """钛合金知识图谱挖掘与分析系统"""
    
    def __init__(self, processed_dir: Path):
        self.processed_dir = Path(processed_dir)
        
        # 加载知识图谱
        self.knowledge_graph = self.load_knowledge_graph()
        self.graph = self.build_networkx_graph()
        self.hypergraph = self.load_hypergraph()
        
        # 加载嵌入向量
        self.embeddings = self.load_embeddings()
        
        # 挖掘结果存储
        self.mining_results = {
            'link_predictions': [],
            'causal_paths': [],
            'knowledge_discoveries': [],
            'entity_clusters': [],
            'anomaly_detections': []
        }
        
        logger.info("图挖掘系统初始化完成")
    
    def load_knowledge_graph(self) -> Dict[str, Any]:
        """加载知识图谱"""
        kg_files = list(self.processed_dir.glob("*hg*.json"))
        if not kg_files:
            logger.warning("未找到知识图谱文件")
            return {'nodes': {}, 'edges': []}
        
        with open(kg_files[0], 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def build_networkx_graph(self) -> nx.Graph:
        """构建NetworkX图"""
        G = nx.Graph()
        
        # 添加节点
        for node, data in self.knowledge_graph.get('nodes', {}).items():
            G.add_node(node, **data)
        
        # 添加边
        for edge in self.knowledge_graph.get('edges', []):
            if len(edge) >= 3:
                head, relation, tail = edge[0], edge[1], edge[2]
                G.add_edge(head, tail, relation=relation, weight=1.0)
        
        return G
    
    def load_hypergraph(self) -> Dict[str, Any]:
        """加载超图"""
        # 构建简化超图
        hypergraph = {'hyperedges': [], 'node_hyperedge_map': defaultdict(list)}
        
        # 基于实体类型构建超边
        type_groups = defaultdict(list)
        for node, data in self.knowledge_graph.get('nodes', {}).items():
            node_type = data.get('type', 'unknown')
            type_groups[node_type].append(node)
        
        hyperedge_id = 0
        for node_type, node_list in type_groups.items():
            if len(node_list) > 2:  # 超边至少包含3个节点
                hyperedge = {
                    'id': hyperedge_id,
                    'nodes': node_list,
                    'type': node_type,
                    'weight': 1.0
                }
                hypergraph['hyperedges'].append(hyperedge)
                
                for node in node_list:
                    hypergraph['node_hyperedge_map'][node].append(hyperedge_id)
                
                hyperedge_id += 1
        
        return hypergraph
    
    def load_embeddings(self) -> Optional[pd.DataFrame]:
        """加载实体嵌入"""
        embedding_files = list(self.processed_dir.glob("*embeddings*.csv"))
        if not embedding_files:
            logger.warning("未找到嵌入文件")
            return None
        
        try:
            return pd.read_csv(embedding_files[0], index_col=0)
        except Exception as e:
            logger.error(f"嵌入加载失败: {e}")
            return None
    
    def run_comprehensive_mining(self) -> Dict[str, Any]:
        """运行综合挖掘分析"""
        logger.info("开始综合图挖掘...")
        
        # 1. 链路预测
        logger.info("执行链路预测...")
        link_predictions = self.predict_missing_links()
        self.mining_results['link_predictions'] = link_predictions
        
        # 2. 因果路径发现
        logger.info("发现因果路径...")
        causal_paths = self.discover_causal_paths()
        self.mining_results['causal_paths'] = causal_paths
        
        # 3. 知识新发现
        logger.info("挖掘新知识...")
        knowledge_discoveries = self.discover_new_knowledge()
        self.mining_results['knowledge_discoveries'] = knowledge_discoveries
        
        # 4. 实体聚类分析
        logger.info("执行实体聚类...")
        entity_clusters = self.cluster_entities()
        self.mining_results['entity_clusters'] = entity_clusters
        
        # 5. 异常检测
        logger.info("执行异常检测...")
        anomalies = self.detect_anomalies()
        self.mining_results['anomaly_detections'] = anomalies
        
        # 6. 超图推理
        logger.info("执行超图推理...")
        hypergraph_inferences = self.hypergraph_reasoning()
        self.mining_results['hypergraph_inferences'] = hypergraph_inferences
        
        # 保存结果
        self.save_mining_results()
        
        return self.mining_results
    
    def predict_missing_links(self, top_k: int = 50) -> List[Dict[str, Any]]:
        """链路预测 - 预测可能缺失的关系"""
        predictions = []
        
        if self.embeddings is None:
            logger.warning("无法进行链路预测：缺少嵌入向量")
            return predictions
        
        # 基于嵌入相似度的链路预测
        entities = list(self.embeddings.index)
        embeddings_matrix = self.embeddings.values
        
        # 计算所有实体对的相似度
        similarity_matrix = cosine_similarity(embeddings_matrix)
        
        # 获取现有边
        existing_edges = set()
        for edge in self.knowledge_graph.get('edges', []):
            if len(edge) >= 3:
                existing_edges.add((edge[0], edge[2]))
                existing_edges.add((edge[2], edge[0]))  # 无向图
        
        # 预测新链接
        for i, entity1 in enumerate(entities):
            for j, entity2 in enumerate(entities):
                if i >= j:  # 避免重复
                    continue
                
                # 跳过已存在的边
                if (entity1, entity2) in existing_edges:
                    continue
                
                similarity = similarity_matrix[i][j]
                
                # 只考虑高相似度的实体对
                if similarity > 0.7:
                    # 预测关系类型
                    predicted_relation = self.predict_relation_type(entity1, entity2)
                    
                    predictions.append({
                        'head': entity1,
                        'tail': entity2,
                        'predicted_relation': predicted_relation,
                        'confidence': float(similarity),
                        'method': 'embedding_similarity'
                    })
        
        # 基于图结构的链路预测
        structural_predictions = self.structural_link_prediction()
        predictions.extend(structural_predictions)
        
        # 按置信度排序
        predictions.sort(key=lambda x: x['confidence'], reverse=True)
        
        return predictions[:top_k]
    
    def predict_relation_type(self, entity1: str, entity2: str) -> str:
        """预测实体间的关系类型"""
        # 获取实体类型
        type1 = self.knowledge_graph['nodes'].get(entity1, {}).get('type', 'unknown')
        type2 = self.knowledge_graph['nodes'].get(entity2, {}).get('type', 'unknown')
        
        # 基于类型的关系预测规则
        type_relation_map = {
            ('alloy', 'element'): 'contains',
            ('element', 'alloy'): 'contained_in',
            ('alloy', 'property'): 'has_property',
            ('property', 'alloy'): 'property_of',
            ('alloy', 'application'): 'used_in',
            ('application', 'alloy'): 'uses',
            ('alloy', 'process'): 'processed_by',
            ('process', 'alloy'): 'processes',
            ('element', 'property'): 'affects',
            ('property', 'element'): 'affected_by'
        }
        
        return type_relation_map.get((type1, type2), 'related_to')
    
    def structural_link_prediction(self) -> List[Dict[str, Any]]:
        """基于图结构的链路预测"""
        predictions = []
        
        # 使用Adamic-Adar指标
        aa_predictions = nx.adamic_adar_index(self.graph)
        
        for u, v, score in aa_predictions:
            if score > 0.1:  # 阈值过滤
                predicted_relation = self.predict_relation_type(u, v)
                predictions.append({
                    'head': u,
                    'tail': v,
                    'predicted_relation': predicted_relation,
                    'confidence': float(score),
                    'method': 'adamic_adar'
                })
        
        return predictions
    
    def discover_causal_paths(self, max_length: int = 4) -> List[Dict[str, Any]]:
        """发现因果路径"""
        causal_paths = []
        
        # 定义因果关系类型
        causal_relations = ['causes', 'improves', 'enhances', 'affects', 'influences']
        
        # 查找潜在的起点和终点实体
        start_entities = []
        end_entities = []
        
        for node, data in self.knowledge_graph.get('nodes', {}).items():
            node_type = data.get('type', 'unknown')
            if node_type in ['process', 'element']:
                start_entities.append(node)
            elif node_type in ['property', 'application']:
                end_entities.append(node)
        
        # 搜索因果路径
        for start in start_entities[:10]:  # 限制搜索范围
            for end in end_entities[:10]:
                try:
                    # 查找最短路径
                    if nx.has_path(self.graph, start, end):
                        paths = list(nx.all_simple_paths(self.graph, start, end, cutoff=max_length))
                        
                        for path in paths[:3]:  # 每对实体最多3条路径
                            # 验证路径中的因果关系
                            path_relations = []
                            is_causal = True
                            
                            for i in range(len(path) - 1):
                                edge_data = self.graph.get_edge_data(path[i], path[i+1])
                                relation = edge_data.get('relation', 'unknown') if edge_data else 'unknown'
                                path_relations.append(relation)
                                
                                # 检查是否包含因果关系
                                if relation not in causal_relations and relation != 'related_to':
                                    is_causal = False
                            
                            if is_causal and len(path) > 2:
                                causal_paths.append({
                                    'start_entity': start,
                                    'end_entity': end,
                                    'path': path,
                                    'relations': path_relations,
                                    'length': len(path),
                                    'confidence': 1.0 / len(path),  # 路径越短置信度越高
                                    'causal_type': self.classify_causal_type(start, end)
                                })
                
                except nx.NetworkXNoPath:
                    continue
        
        # 按置信度排序
        causal_paths.sort(key=lambda x: x['confidence'], reverse=True)
        
        return causal_paths[:20]  # 返回前20条路径
    
    def classify_causal_type(self, start: str, end: str) -> str:
        """分类因果关系类型"""
        start_type = self.knowledge_graph['nodes'].get(start, {}).get('type', 'unknown')
        end_type = self.knowledge_graph['nodes'].get(end, {}).get('type', 'unknown')
        
        if start_type == 'element' and end_type == 'property':
            return 'composition_property'
        elif start_type == 'process' and end_type == 'property':
            return 'process_property'
        elif start_type == 'process' and end_type == 'application':
            return 'process_application'
        else:
            return 'general_causal'
    
    def discover_new_knowledge(self) -> List[Dict[str, Any]]:
        """知识新发现"""
        discoveries = []
        
        # 1. 基于PageRank的重要节点发现
        pagerank_discoveries = self.pagerank_based_discovery()
        discoveries.extend(pagerank_discoveries)
        
        # 2. 基于社区检测的知识发现
        community_discoveries = self.community_based_discovery()
        discoveries.extend(community_discoveries)
        
        # 3. 基于异常模式的发现
        pattern_discoveries = self.pattern_based_discovery()
        discoveries.extend(pattern_discoveries)
        
        return discoveries
    
    def pagerank_based_discovery(self) -> List[Dict[str, Any]]:
        """基于PageRank的知识发现"""
        discoveries = []
        
        # 计算PageRank
        pagerank_scores = nx.pagerank(self.graph)
        
        # 按类型分组分析
        type_scores = defaultdict(list)
        for node, score in pagerank_scores.items():
            node_type = self.knowledge_graph['nodes'].get(node, {}).get('type', 'unknown')
            type_scores[node_type].append((node, score))
        
        # 发现每个类型中的重要节点
        for node_type, scores in type_scores.items():
            scores.sort(key=lambda x: x[1], reverse=True)
            
            # 前3个最重要的节点
            for i, (node, score) in enumerate(scores[:3]):
                if score > 0.01:  # 阈值过滤
                    discoveries.append({
                        'type': 'important_entity',
                        'entity': node,
                        'entity_type': node_type,
                        'importance_score': score,
                        'rank_in_type': i + 1,
                        'description': f'{node}在{node_type}类别中具有重要地位',
                        'potential_application': self.suggest_application(node, node_type)
                    })
        
        return discoveries
    
    def suggest_application(self, entity: str, entity_type: str) -> str:
        """建议潜在应用"""
        suggestions = {
            'element': f'可考虑{entity}元素在新合金设计中的应用',
            'alloy': f'{entity}合金可能适用于特定工业场景',
            'process': f'{entity}工艺可能对材料性能有重要影响',
            'property': f'{entity}性能可作为材料优化的关键指标'
        }
        
        return suggestions.get(entity_type, f'{entity}值得进一步研究')
    
    def community_based_discovery(self) -> List[Dict[str, Any]]:
        """基于社区检测的知识发现"""
        discoveries = []
        
        # 使用Louvain算法进行社区检测
        try:
            communities = nx.community.louvain_communities(self.graph, seed=42)
            
            for i, community in enumerate(communities):
                if len(community) >= 3:  # 只考虑较大的社区
                    # 分析社区组成
                    community_types = defaultdict(int)
                    for node in community:
                        node_type = self.knowledge_graph['nodes'].get(node, {}).get('type', 'unknown')
                        community_types[node_type] += 1
                    
                    # 发现有趣的社区模式
                    dominant_type = max(community_types, key=community_types.get)
                    
                    if len(community_types) > 2:  # 多样性社区
                        discoveries.append({
                            'type': 'knowledge_cluster',
                            'community_id': i,
                            'entities': list(community),
                            'size': len(community),
                            'composition': dict(community_types),
                            'dominant_type': dominant_type,
                            'description': f'发现包含{len(community)}个实体的知识簇',
                            'insight': self.analyze_community_insight(community, community_types)
                        })
        
        except Exception as e:
            logger.warning(f"社区检测失败: {e}")
        
        return discoveries
    
    def analyze_community_insight(self, community: Set[str], types: Dict[str, int]) -> str:
        """分析社区洞察"""
        insights = []
        
        # 分析类型组合
        if 'alloy' in types and 'element' in types and 'property' in types:
            insights.append("发现了合金-元素-性能的关联模式")
        
        if 'process' in types and 'property' in types:
            insights.append("发现了工艺-性能的关联模式")
        
        if len(types) >= 4:
            insights.append("发现了跨领域的复杂关联模式")
        
        return "; ".join(insights) if insights else "需要进一步分析的知识簇"
    
    def pattern_based_discovery(self) -> List[Dict[str, Any]]:
        """基于模式的知识发现"""
        discoveries = []
        
        # 1. 发现高频模式
        relation_patterns = Counter()
        for edge in self.knowledge_graph.get('edges', []):
            if len(edge) >= 3:
                head_type = self.knowledge_graph['nodes'].get(edge[0], {}).get('type', 'unknown')
                tail_type = self.knowledge_graph['nodes'].get(edge[2], {}).get('type', 'unknown')
                pattern = (head_type, edge[1], tail_type)
                relation_patterns[pattern] += 1
        
        # 发现最常见的模式
        for pattern, count in relation_patterns.most_common(5):
            if count >= 3:  # 至少出现3次
                discoveries.append({
                    'type': 'frequent_pattern',
                    'pattern': pattern,
                    'frequency': count,
                    'description': f'发现频繁模式: {pattern[0]} -[{pattern[1]}]-> {pattern[2]}',
                    'significance': 'high' if count >= 10 else 'medium'
                })
        
        # 2. 发现罕见但重要的模式
        rare_patterns = [p for p, c in relation_patterns.items() if c == 1]
        for pattern in rare_patterns[:5]:
            discoveries.append({
                'type': 'rare_pattern',
                'pattern': pattern,
                'frequency': 1,
                'description': f'发现罕见模式: {pattern[0]} -[{pattern[1]}]-> {pattern[2]}',
                'significance': 'unique'
            })
        
        return discoveries
    
    def cluster_entities(self, n_clusters: int = 5) -> List[Dict[str, Any]]:
        """实体聚类分析"""
        clusters = []
        
        if self.embeddings is None:
            return clusters
        
        try:
            # K-means聚类
            embeddings_matrix = self.embeddings.values
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            cluster_labels = kmeans.fit_predict(embeddings_matrix)
            
            # 分析每个簇
            for cluster_id in range(n_clusters):
                cluster_indices = np.where(cluster_labels == cluster_id)[0]
                cluster_entities = [self.embeddings.index[i] for i in cluster_indices]
                
                if len(cluster_entities) >= 2:
                    # 分析簇的组成
                    cluster_types = defaultdict(int)
                    for entity in cluster_entities:
                        entity_type = self.knowledge_graph['nodes'].get(entity, {}).get('type', 'unknown')
                        cluster_types[entity_type] += 1
                    
                    # 计算簇内相似度
                    cluster_embeddings = embeddings_matrix[cluster_indices]
                    similarity_matrix = cosine_similarity(cluster_embeddings)
                    avg_similarity = np.mean(similarity_matrix[np.triu_indices_from(similarity_matrix, k=1)])
                    
                    clusters.append({
                        'cluster_id': cluster_id,
                        'entities': cluster_entities,
                        'size': len(cluster_entities),
                        'composition': dict(cluster_types),
                        'avg_similarity': float(avg_similarity),
                        'centroid': kmeans.cluster_centers_[cluster_id].tolist(),
                        'dominant_type': max(cluster_types, key=cluster_types.get) if cluster_types else 'unknown'
                    })
        
        except Exception as e:
            logger.error(f"聚类分析失败: {e}")
        
        return clusters
    
    def detect_anomalies(self) -> List[Dict[str, Any]]:
        """异常检测"""
        anomalies = []
        
        # 1. 度分布异常
        degrees = dict(self.graph.degree())
        degree_values = list(degrees.values())
        mean_degree = np.mean(degree_values)
        std_degree = np.std(degree_values)
        
        for node, degree in degrees.items():
            if degree > mean_degree + 2 * std_degree:  # 度异常高
                anomalies.append({
                    'type': 'high_degree_anomaly',
                    'entity': node,
                    'degree': degree,
                    'mean_degree': mean_degree,
                    'description': f'{node}的连接度异常高',
                    'severity': 'high' if degree > mean_degree + 3 * std_degree else 'medium'
                })
        
        # 2. 孤立节点检测
        isolated_nodes = list(nx.isolates(self.graph))
        for node in isolated_nodes:
            anomalies.append({
                'type': 'isolated_node',
                'entity': node,
                'description': f'{node}是孤立节点，没有任何连接',
                'severity': 'medium'
            })
        
        # 3. 桥边检测
        bridges = list(nx.bridges(self.graph))
        for bridge in bridges:
            anomalies.append({
                'type': 'bridge_edge',
                'entities': bridge,
                'description': f'{bridge[0]}和{bridge[1]}之间的边是桥边',
                'severity': 'low'
            })
        
        return anomalies
    
    def hypergraph_reasoning(self) -> List[Dict[str, Any]]:
        """超图推理"""
        inferences = []
        
        # 超边补全推理
        for hyperedge in self.hypergraph['hyperedges']:
            nodes = hyperedge['nodes']
            hyperedge_type = hyperedge['type']
            
            if len(nodes) >= 3:
                # 尝试发现可能缺失的节点
                candidates = self.find_hyperedge_candidates(nodes, hyperedge_type)
                
                for candidate in candidates:
                    if candidate not in nodes:
                        inferences.append({
                            'type': 'hyperedge_completion',
                            'hyperedge_id': hyperedge['id'],
                            'existing_nodes': nodes,
                            'candidate_node': candidate,
                            'confidence': candidate['score'],
                            'description': f'推理{candidate["entity"]}可能属于超边{hyperedge["id"]}'
                        })
        
        return inferences
    
    def find_hyperedge_candidates(self, existing_nodes: List[str], hyperedge_type: str) -> List[Dict[str, Any]]:
        """查找超边候选节点"""
        candidates = []
        
        # 查找同类型的其他节点
        for node, data in self.knowledge_graph.get('nodes', {}).items():
            if node in existing_nodes:
                continue
            
            if data.get('type') == hyperedge_type:
                # 计算与现有节点的相似度
                similarity_scores = []
                
                if self.embeddings is not None and node in self.embeddings.index:
                    node_embedding = self.embeddings.loc[node].values
                    
                    for existing_node in existing_nodes:
                        if existing_node in self.embeddings.index:
                            existing_embedding = self.embeddings.loc[existing_node].values
                            similarity = cosine_similarity([node_embedding], [existing_embedding])[0][0]
                            similarity_scores.append(similarity)
                
                if similarity_scores:
                    avg_similarity = np.mean(similarity_scores)
                    if avg_similarity > 0.6:  # 相似度阈值
                        candidates.append({
                            'entity': node,
                            'score': avg_similarity,
                            'type': hyperedge_type
                        })
        
        # 按分数排序
        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates[:5]
    
    def save_mining_results(self):
        """保存挖掘结果"""
        # 保存详细结果
        output_file = self.processed_dir / "graph_mining_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.mining_results, f, indent=2, ensure_ascii=False, default=str)
        
        # 保存链路预测结果（OpenKE格式）
        self.save_link_predictions_openke_format()
        
        logger.info(f"挖掘结果已保存: {output_file}")
    
    def save_link_predictions_openke_format(self):
        """保存链路预测结果为OpenKE格式"""
        if not self.mining_results['link_predictions']:
            return
        
        predictions_df = pd.DataFrame([
            {
                'head': pred['head'],
                'relation': pred['predicted_relation'],
                'tail': pred['tail'],
                'confidence': pred['confidence']
            }
            for pred in self.mining_results['link_predictions']
        ])
        
        output_file = self.processed_dir / "predicted_links.csv"
        predictions_df.to_csv(output_file, index=False, encoding='utf-8')
        
        logger.info(f"链路预测结果已保存: {output_file}")
    
    def generate_mining_report(self) -> str:
        """生成挖掘报告"""
        report_parts = ["# 钛合金知识图谱挖掘报告\n"]
        
        # 链路预测报告
        link_count = len(self.mining_results.get('link_predictions', []))
        report_parts.append(f"## 链路预测\n- 预测了 {link_count} 个潜在关系\n")
        
        if link_count > 0:
            high_conf_links = [p for p in self.mining_results['link_predictions'] if p['confidence'] > 0.8]
            report_parts.append(f"- 其中 {len(high_conf_links)} 个高置信度预测\n")
        
        # 因果路径报告
        path_count = len(self.mining_results.get('causal_paths', []))
        report_parts.append(f"## 因果路径发现\n- 发现了 {path_count} 条因果路径\n")
        
        # 知识发现报告
        discovery_count = len(self.mining_results.get('knowledge_discoveries', []))
        report_parts.append(f"## 知识新发现\n- 发现了 {discovery_count} 个新的知识模式\n")
        
        # 聚类分析报告
        cluster_count = len(self.mining_results.get('entity_clusters', []))
        report_parts.append(f"## 实体聚类\n- 识别了 {cluster_count} 个实体簇\n")
        
        # 异常检测报告
        anomaly_count = len(self.mining_results.get('anomaly_detections', []))
        report_parts.append(f"## 异常检测\n- 检测到 {anomaly_count} 个异常模式\n")
        
        return "".join(report_parts)


# 挖掘评估器
class MiningEvaluator:
    """图挖掘结果评估器"""
    
    def __init__(self, miner: TitaniumGraphMiner):
        self.miner = miner
    
    def evaluate_link_predictions(self, test_edges: List[Tuple[str, str, str]] = None) -> Dict[str, float]:
        """评估链路预测质量"""
        metrics = {
            'precision_at_k': 0.0,
            'recall_at_k': 0.0,
            'mrr': 0.0,
            'hits_at_10': 0.0
        }
        
        predictions = self.miner.mining_results.get('link_predictions', [])
        
        if not predictions or not test_edges:
            return metrics
        
        # 转换预测结果为集合
        predicted_edges = set()
        for pred in predictions[:10]:  # top-10
            predicted_edges.add((pred['head'], pred['tail']))
        
        # 转换测试边为集合
        test_edge_set = set()
        for edge in test_edges:
            test_edge_set.add((edge[0], edge[2]))
        
        # 计算指标
        if predicted_edges:
            correct_predictions = predicted_edges & test_edge_set
            metrics['precision_at_k'] = len(correct_predictions) / len(predicted_edges)
            metrics['hits_at_10'] = 1.0 if correct_predictions else 0.0
        
        if test_edge_set:
            metrics['recall_at_k'] = len(correct_predictions) / len(test_edge_set)
        
        return metrics
    
    def evaluate_causal_paths(self) -> Dict[str, float]:
        """评估因果路径质量"""
        paths = self.miner.mining_results.get('causal_paths', [])
        
        if not paths:
            return {'path_count': 0, 'avg_confidence': 0.0, 'avg_length': 0.0}
        
        confidences = [p['confidence'] for p in paths]
        lengths = [p['length'] for p in paths]
        
        return {
            'path_count': len(paths),
            'avg_confidence': np.mean(confidences),
            'avg_length': np.mean(lengths),
            'unique_start_entities': len(set(p['start_entity'] for p in paths)),
            'unique_end_entities': len(set(p['end_entity'] for p in paths))
        }


# 使用示例
if __name__ == "__main__":
    from pathlib import Path
    
    # 初始化图挖掘系统
    processed_dir = Path(__file__).resolve().parent.parent / "data" / "processed"
    miner = TitaniumGraphMiner(processed_dir)
    
    # 运行综合挖掘
    results = miner.run_comprehensive_mining()
    
    # 生成报告
    report = miner.generate_mining_report()
    print(report)
    
    # 评估结果
    evaluator = MiningEvaluator(miner)
    
    link_eval = evaluator.evaluate_link_predictions()
    path_eval = evaluator.evaluate_causal_paths()
    
    print(f"\n评估结果:")
    print(f"链路预测: {link_eval}")
    print(f"因果路径: {path_eval}")
    
    print(f"\n挖掘统计:")
    print(f"- 链路预测: {len(results['link_predictions'])} 个")
    print(f"- 因果路径: {len(results['causal_paths'])} 条")
    print(f"- 知识发现: {len(results['knowledge_discoveries'])} 个")
    print(f"- 实体簇: {len(results['entity_clusters'])} 个")
    print(f"- 异常检测: {len(results['anomaly_detections'])} 个")