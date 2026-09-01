# script/knowledge_storage_system.py - 知识存储和图数据库集成系统
import json
import sqlite3
import pandas as pd
import numpy as np
import networkx as nx
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime
import pickle
from collections import defaultdict
import sys
sys.stdout.reconfigure(encoding='utf-8')


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GraphDatabaseInterface:
    """图数据库接口 - 轻量级实现"""
    
    def __init__(self, storage_dir: Path):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 使用SQLite作为后端存储，NetworkX作为图操作引擎
        self.db_path = self.storage_dir / "graph_database.db"
        self.graph = nx.MultiDiGraph()  # 支持多重有向图
        
        # 初始化数据库
        self._init_database()
        
        # 加载现有图数据
        self._load_graph_from_db()
        
        logger.info(f"图数据库初始化完成: {self.db_path}")
    
    def _init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 节点表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                type TEXT,
                properties TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 边表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                target TEXT,
                relation TEXT,
                properties TEXT,
                weight REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source) REFERENCES nodes (id),
                FOREIGN KEY (target) REFERENCES nodes (id)
            )
        ''')
        
        # 索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_edges_relation ON edges(relation)')
        
        conn.commit()
        conn.close()
    
    def _load_graph_from_db(self):
        """从数据库加载图到内存"""
        conn = sqlite3.connect(self.db_path)
        
        # 加载节点
        nodes_df = pd.read_sql_query("SELECT * FROM nodes", conn)
        for _, row in nodes_df.iterrows():
            properties = json.loads(row['properties']) if row['properties'] else {}
            properties.update({
                'type': row['type'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            })
            self.graph.add_node(row['id'], **properties)
        
        # 加载边
        edges_df = pd.read_sql_query("SELECT * FROM edges", conn)
        for _, row in edges_df.iterrows():
            properties = json.loads(row['properties']) if row['properties'] else {}
            properties.update({
                'relation': row['relation'],
                'weight': row['weight'],
                'edge_id': row['id'],
                'created_at': row['created_at']
            })
            self.graph.add_edge(row['source'], row['target'], **properties)
        
        conn.close()
        logger.info(f"从数据库加载: {len(self.graph.nodes)} 个节点, {len(self.graph.edges)} 条边")
    
    def add_node(self, node_id: str, node_type: str, properties: Dict[str, Any] = None):
        """添加节点"""
        properties = properties or {}
        
        # 添加到内存图
        self.graph.add_node(node_id, type=node_type, **properties)
        
        # 保存到数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO nodes (id, type, properties, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (node_id, node_type, json.dumps(properties, ensure_ascii=False)))
        
        conn.commit()
        conn.close()
    
    def add_edge(self, source: str, target: str, relation: str, 
                 properties: Dict[str, Any] = None, weight: float = 1.0):
        """添加边"""
        properties = properties or {}
        
        # 确保节点存在
        if source not in self.graph.nodes:
            self.add_node(source, 'unknown')
        if target not in self.graph.nodes:
            self.add_node(target, 'unknown')
        
        # 添加到内存图
        self.graph.add_edge(source, target, relation=relation, weight=weight, **properties)
        
        # 保存到数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO edges (source, target, relation, properties, weight)
            VALUES (?, ?, ?, ?, ?)
        ''', (source, target, relation, json.dumps(properties, ensure_ascii=False), weight))
        
        conn.commit()
        conn.close()
    
    def shortest_path(self, source: str, target: str) -> List[str]:
        """最短路径查询"""
        try:
            return nx.shortest_path(self.graph, source, target)
        except nx.NetworkXNoPath:
            return []
    
    def subgraph_match(self, node_types: List[str], max_nodes: int = 50) -> nx.Graph:
        """子图匹配"""
        matching_nodes = []
        for node, data in self.graph.nodes(data=True):
            if data.get('type') in node_types and len(matching_nodes) < max_nodes:
                matching_nodes.append(node)
        
        return self.graph.subgraph(matching_nodes)
    
    def get_neighbors(self, node: str, relation_type: str = None) -> List[str]:
        """获取邻居节点"""
        neighbors = []
        for neighbor in self.graph.neighbors(node):
            edge_data = self.graph.get_edge_data(node, neighbor)
            if relation_type is None or any(d.get('relation') == relation_type for d in edge_data.values()):
                neighbors.append(neighbor)
        return neighbors
    
    def export_to_standard_format(self) -> Dict[str, Any]:
        """导出为标准格式"""
        return {
            'nodes': dict(self.graph.nodes(data=True)),
            'edges': [
                {
                    'source': u,
                    'target': v,
                    'relation': d.get('relation', 'unknown'),
                    'weight': d.get('weight', 1.0),
                    'properties': {k: v for k, v in d.items() if k not in ['relation', 'weight']}
                }
                for u, v, d in self.graph.edges(data=True)
            ]
        }


class KnowledgeQualityEvaluator:
    """知识图谱质量评估器 - 基于规则和统计的方法"""
    
    def __init__(self):
        self.evaluation_metrics = {}
    
    def evaluate_graph_quality(self, graph_db: GraphDatabaseInterface) -> Dict[str, float]:
        """评估图谱质量"""
        graph = graph_db.graph
        
        metrics = {
            'completeness': self._evaluate_completeness(graph),
            'consistency': self._evaluate_consistency(graph),
            'connectivity': self._evaluate_connectivity(graph),
            'informativeness': self._evaluate_informativeness(graph),
            'coverage': self._evaluate_domain_coverage(graph)
        }
        
        # 计算综合评分
        weights = {
            'completeness': 0.25,
            'consistency': 0.20,
            'connectivity': 0.20,
            'informativeness': 0.20,
            'coverage': 0.15
        }
        
        overall_score = sum(metrics[k] * weights[k] for k in weights)
        metrics['overall_score'] = overall_score
        
        self.evaluation_metrics = metrics
        return metrics
    
    def _evaluate_completeness(self, graph: nx.Graph) -> float:
        """评估完整性"""
        # 检查节点和边的数量
        node_count = len(graph.nodes)
        edge_count = len(graph.edges)
        
        # 基于预期的规模评分
        expected_nodes = 200
        expected_edges = 500
        
        node_score = min(node_count / expected_nodes, 1.0)
        edge_score = min(edge_count / expected_edges, 1.0)
        
        return (node_score + edge_score) / 2
    
    def _evaluate_consistency(self, graph: nx.Graph) -> float:
        """评估一致性"""
        consistency_score = 1.0
        
        # 检查节点类型一致性
        type_counts = defaultdict(int)
        for node, data in graph.nodes(data=True):
            node_type = data.get('type', 'unknown')
            type_counts[node_type] += 1
        
        # 减少未知类型的比例
        unknown_ratio = type_counts.get('unknown', 0) / len(graph.nodes)
        consistency_score -= unknown_ratio * 0.3
        
        # 检查关系一致性
        relation_counts = defaultdict(int)
        for u, v, data in graph.edges(data=True):
            relation = data.get('relation', 'unknown')
            relation_counts[relation] += 1
        
        unknown_rel_ratio = relation_counts.get('unknown', 0) / len(graph.edges)
        consistency_score -= unknown_rel_ratio * 0.3
        
        return max(consistency_score, 0.0)
    
    def _evaluate_connectivity(self, graph: nx.Graph) -> float:
        """评估连通性"""
        if len(graph.nodes) == 0:
            return 0.0
        
        # 计算连通组件
        if graph.is_directed():
            components = list(nx.weakly_connected_components(graph))
        else:
            components = list(nx.connected_components(graph))
        
        # 最大连通组件的比例
        largest_component_size = max(len(comp) for comp in components) if components else 0
        connectivity_ratio = largest_component_size / len(graph.nodes)
        
        # 平均度
        degrees = [d for n, d in graph.degree()]
        avg_degree = np.mean(degrees) if degrees else 0
        degree_score = min(avg_degree / 4, 1.0)  # 期望平均度为4
        
        return (connectivity_ratio + degree_score) / 2
    
    def _evaluate_informativeness(self, graph: nx.Graph) -> float:
        """评估信息丰富度"""
        # 检查节点属性丰富度
        attribute_scores = []
        for node, data in graph.nodes(data=True):
            attr_count = len([k for k in data.keys() if k not in ['type']])
            attribute_scores.append(min(attr_count / 3, 1.0))  # 期望每个节点有3个属性
        
        avg_attr_score = np.mean(attribute_scores) if attribute_scores else 0
        
        # 检查关系类型多样性
        relation_types = set()
        for u, v, data in graph.edges(data=True):
            relation_types.add(data.get('relation', 'unknown'))
        
        relation_diversity = min(len(relation_types) / 10, 1.0)  # 期望10种关系类型
        
        return (avg_attr_score + relation_diversity) / 2
    
    def _evaluate_domain_coverage(self, graph: nx.Graph) -> float:
        """评估领域覆盖度"""
        # 钛合金领域的关键概念
        key_concepts = {
            'elements': ['Ti', 'Al', 'V', 'Mo', 'Nb', 'Zr'],
            'alloys': ['Ti-6Al-4V', 'Ti-3Al-2.5V', 'TC4'],
            'properties': ['强度', '硬度', '密度', '耐腐蚀性'],
            'applications': ['航空航天', '医疗', '汽车']
        }
        
        coverage_scores = []
        for category, concepts in key_concepts.items():
            found_concepts = 0
            for concept in concepts:
                if concept in graph.nodes:
                    found_concepts += 1
            
            coverage = found_concepts / len(concepts)
            coverage_scores.append(coverage)
        
        return np.mean(coverage_scores)
    
    def generate_quality_report(self) -> str:
        """生成质量评估报告"""
        if not self.evaluation_metrics:
            return "尚未进行质量评估"
        
        report = "知识图谱质量评估报告\n"
        report += "=" * 40 + "\n"
        
        for metric, score in self.evaluation_metrics.items():
            if metric != 'overall_score':
                report += f"{metric}: {score:.2f}\n"
        
        report += f"\n综合评分: {self.evaluation_metrics['overall_score']:.2f}\n"
        
        # 评级
        overall = self.evaluation_metrics['overall_score']
        if overall >= 0.8:
            grade = "优秀"
        elif overall >= 0.6:
            grade = "良好"
        elif overall >= 0.4:
            grade = "一般"
        else:
            grade = "需要改进"
        
        report += f"质量等级: {grade}\n"
        
        return report


class MultimodalKnowledgeGraph:
    """多模态知识图谱系统"""
    
    def __init__(self, storage_dir: Path):
        self.storage_dir = Path(storage_dir)
        self.graph_db = GraphDatabaseInterface(storage_dir)
        self.quality_evaluator = KnowledgeQualityEvaluator()
        
        # 多模态数据存储
        self.multimodal_data = {
            'text_chunks': {},      # 文本片段
            'table_data': {},       # 表格数据
            'image_metadata': {},   # 图像元数据
            'formula_data': {}      # 公式数据
        }
        
        logger.info("多模态知识图谱系统初始化完成")
    
    def import_from_json(self, kg_file: Path):
        """从JSON文件导入知识图谱"""
        with open(kg_file, 'r', encoding='utf-8') as f:
            kg_data = json.load(f)
        
        # 导入节点
        nodes = kg_data.get('nodes', {})
        for node_id, node_data in nodes.items():
            node_type = node_data.get('type', 'unknown')
            properties = {k: v for k, v in node_data.items() if k != 'type'}
            self.graph_db.add_node(node_id, node_type, properties)
        
        # 导入边
        edges = kg_data.get('edges', [])
        for edge in edges:
            if len(edge) >= 3:
                source, relation, target = edge[0], edge[1], edge[2]
                weight = edge[3] if len(edge) > 3 else 1.0
                self.graph_db.add_edge(source, target, relation, weight=weight)
        
        logger.info(f"从{kg_file}导入: {len(nodes)}个节点, {len(edges)}条边")
    
    def add_multimodal_context(self, entity_id: str, modality: str, data: Dict[str, Any]):
        """为实体添加多模态上下文"""
        if modality not in self.multimodal_data:
            self.multimodal_data[modality] = {}
        
        if entity_id not in self.multimodal_data[modality]:
            self.multimodal_data[modality][entity_id] = []
        
        self.multimodal_data[modality][entity_id].append(data)
    
    def semantic_search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """语义搜索"""
        # 简化的语义搜索实现
        results = []
        query_lower = query.lower()
        
        for node_id, node_data in self.graph_db.graph.nodes(data=True):
            relevance_score = 0
            
            # 节点名称匹配
            if query_lower in node_id.lower():
                relevance_score += 0.8
            
            # 节点类型匹配
            node_type = node_data.get('type', '')
            if any(word in node_type.lower() for word in query_lower.split()):
                relevance_score += 0.3
            
            # 属性匹配
            for key, value in node_data.items():
                if isinstance(value, str) and query_lower in value.lower():
                    relevance_score += 0.2
            
            if relevance_score > 0:
                results.append({
                    'node_id': node_id,
                    'relevance_score': relevance_score,
                    'node_data': node_data
                })
        
        # 按相关性排序
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        return results[:top_k]
    
    def graph_query(self, start_node: str, relation_type: str = None, max_hops: int = 2) -> Dict[str, Any]:
        """图查询"""
        subgraph_nodes = {start_node}
        current_nodes = {start_node}
        
        for hop in range(max_hops):
            next_nodes = set()
            for node in current_nodes:
                neighbors = self.graph_db.get_neighbors(node, relation_type)
                next_nodes.update(neighbors)
            
            subgraph_nodes.update(next_nodes)
            current_nodes = next_nodes
        
        # 提取子图
        subgraph = self.graph_db.graph.subgraph(subgraph_nodes)
        
        return {
            'nodes': list(subgraph.nodes()),
            'edges': list(subgraph.edges()),
            'node_count': len(subgraph.nodes()),
            'edge_count': len(subgraph.edges())
        }
    
    def optimize_graph(self):
        """图谱优化"""
        logger.info("开始图谱优化...")
        
        # 1. 质量评估
        quality_metrics = self.quality_evaluator.evaluate_graph_quality(self.graph_db)
        
        # 2. 基于质量评估的优化
        optimizations = []
        
        if quality_metrics['completeness'] < 0.7:
            optimizations.append("建议增加更多实体和关系")
        
        if quality_metrics['consistency'] < 0.7:
            optimizations.append("建议清理未知类型的节点和关系")
        
        if quality_metrics['connectivity'] < 0.7:
            optimizations.append("建议增加实体间的连接")
        
        # 3. 执行自动优化
        self._auto_optimize()
        
        logger.info("图谱优化完成")
        return {
            'quality_before': quality_metrics,
            'optimizations_applied': optimizations
        }
    
    def _auto_optimize(self):
        """自动优化"""
        # 1. 移除孤立节点
        isolated_nodes = list(nx.isolates(self.graph_db.graph))
        for node in isolated_nodes[:10]:  # 限制数量
            self.graph_db.graph.remove_node(node)
        
        # 2. 合并相似节点（简化版）
        # 这里可以添加更复杂的实体消歧逻辑
        
        logger.info(f"移除了 {len(isolated_nodes)} 个孤立节点")
    
    def export_to_rag_format(self) -> Dict[str, Any]:
        """导出为RAG系统格式"""
        # 为RAG系统准备的格式
        rag_data = {
            'entities': [],
            'relations': [],
            'contexts': {}
        }
        
        # 导出实体
        for node_id, node_data in self.graph_db.graph.nodes(data=True):
            entity = {
                'id': node_id,
                'type': node_data.get('type', 'unknown'),
                'properties': node_data,
                'description': self._generate_entity_description(node_id, node_data)
            }
            rag_data['entities'].append(entity)
        
        # 导出关系
        for source, target, edge_data in self.graph_db.graph.edges(data=True):
            relation = {
                'source': source,
                'target': target,
                'relation': edge_data.get('relation', 'unknown'),
                'weight': edge_data.get('weight', 1.0),
                'description': f"{source} {edge_data.get('relation', 'relates to')} {target}"
            }
            rag_data['relations'].append(relation)
        
        # 添加多模态上下文
        rag_data['contexts'] = self.multimodal_data
        
        return rag_data
    
    def _generate_entity_description(self, entity_id: str, entity_data: Dict[str, Any]) -> str:
        """生成实体描述"""
        entity_type = entity_data.get('type', 'entity')
        
        if entity_type == 'alloy':
            return f"{entity_id}是一种钛合金材料"
        elif entity_type == 'element':
            return f"{entity_id}是一种化学元素"
        elif entity_type == 'property':
            return f"{entity_id}是材料的一种性能指标"
        elif entity_type == 'application':
            return f"{entity_id}是钛合金的一个应用领域"
        else:
            return f"{entity_id}是{entity_type}类型的实体"
    
    def save_system_state(self):
        """保存系统状态"""
        state_file = self.storage_dir / "system_state.pkl"
        
        state = {
            'multimodal_data': self.multimodal_data,
            'quality_metrics': self.quality_evaluator.evaluation_metrics,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(state_file, 'wb') as f:
            pickle.dump(state, f)
        
        logger.info(f"系统状态已保存: {state_file}")

        # 在 knowledge_storage_system.py 中添加GraphML导出
    def export_to_graphml(self, output_path: Path):
        import networkx as nx
        nx.write_graphml(self.graph_db.graph, output_path)

# 使用示例
if __name__ == "__main__":
    from pathlib import Path
    
    # 初始化系统
    project_root = Path(__file__).resolve().parent.parent
    storage_dir = project_root / "data" / "graph_storage"
    kg_system = MultimodalKnowledgeGraph(storage_dir)
    
    # 导入现有知识图谱
    kg_file = project_root / "data" / "processed" / "entities_relations_hg.json"
    if kg_file.exists():
        kg_system.import_from_json(kg_file)
    
    # 评估质量
    quality_report = kg_system.quality_evaluator.generate_quality_report()
    print("质量评估报告:")
    print(quality_report)
    
    # 优化图谱
    optimization_result = kg_system.optimize_graph()
    print(f"\n优化结果: {optimization_result}")
    
    # 导出RAG格式
    rag_data = kg_system.export_to_rag_format()
    print(f"\nRAG格式数据: {len(rag_data['entities'])} 个实体, {len(rag_data['relations'])} 个关系")
    
    # 保存系统状态
    kg_system.save_system_state()