# export_to_neo4j.py - 将钛合金知识图谱导入Neo4j
"""
将处理好的钛合金知识图谱数据导入Neo4j图数据库
支持节点、关系、属性和向量索引的完整导入
"""

import json
import os
import pandas as pd
import numpy as np
from pathlib import Path
from neo4j import GraphDatabase
from typing import Dict, List, Any, Optional
import logging
import sys

# 确保UTF-8编码
sys.stdout.reconfigure(encoding='utf-8')

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Neo4jExporter:
    """Neo4j数据导出器"""
    
    def __init__(self, uri: str = None, username: str = None, password: str = None):
        """初始化Neo4j连接（凭据优先取环境变量 NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD）"""
        self.driver = GraphDatabase.driver(
            uri or os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(username or os.getenv("NEO4J_USER", "neo4j"),
                  password or os.getenv("NEO4J_PASSWORD"))
        )
        self.data_dir = Path(__file__).resolve().parent.parent / "data" / "processed"
        
    def close(self):
        """关闭数据库连接"""
        self.driver.close()
    
    def clear_database(self):
        """清空数据库（可选）"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            logger.info("数据库已清空")
    
    def create_constraints_and_indexes(self):
        """创建约束和索引"""
        with self.driver.session() as session:
            # 创建唯一性约束
            constraints = [
                "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
                "CREATE CONSTRAINT alloy_name IF NOT EXISTS FOR (a:Alloy) REQUIRE a.name IS UNIQUE", 
                "CREATE CONSTRAINT element_symbol IF NOT EXISTS FOR (el:Element) REQUIRE el.symbol IS UNIQUE",
                "CREATE CONSTRAINT property_name IF NOT EXISTS FOR (p:Property) REQUIRE p.name IS UNIQUE"
            ]
            
            for constraint in constraints:
                try:
                    session.run(constraint)
                    logger.info(f"约束创建成功: {constraint.split('(')[1].split(')')[0]}")
                except Exception as e:
                    logger.warning(f"约束创建失败或已存在: {e}")
            
            # 创建性能索引
            indexes = [
                "CREATE INDEX entity_type_idx IF NOT EXISTS FOR (e:Entity) ON (e.type)",
                "CREATE INDEX alloy_composition_idx IF NOT EXISTS FOR (a:Alloy) ON (a.composition)",
                "CREATE INDEX property_value_idx IF NOT EXISTS FOR (p:Property) ON (p.value)"
            ]
            
            for index in indexes:
                try:
                    session.run(index)
                    logger.info(f"索引创建成功")
                except Exception as e:
                    logger.warning(f"索引创建失败或已存在: {e}")
    
    def load_knowledge_graph_data(self) -> Dict[str, Any]:
        """加载知识图谱数据"""
        kg_files = list(self.data_dir.glob("*hg*.json"))
        
        if not kg_files:
            logger.error("未找到知识图谱文件")
            return {"nodes": {}, "edges": []}
        
        # 合并所有知识图谱文件
        combined_kg = {"nodes": {}, "edges": []}
        
        for kg_file in kg_files:
            logger.info(f"加载知识图谱文件: {kg_file}")
            with open(kg_file, 'r', encoding='utf-8') as f:
                kg_data = json.load(f)
            
            # 合并节点
            combined_kg["nodes"].update(kg_data.get("nodes", {}))
            
            # 合并边（去重）
            existing_edges = set(tuple(edge[:2]) for edge in combined_kg["edges"])
            for edge in kg_data.get("edges", []):
                if len(edge) >= 2:
                    edge_key = tuple(edge[:2])
                    if edge_key not in existing_edges:
                        combined_kg["edges"].append(edge)
                        existing_edges.add(edge_key)
        
        logger.info(f"合并后的知识图谱: {len(combined_kg['nodes'])} 个节点, {len(combined_kg['edges'])} 条边")
        return combined_kg
    
    def load_embeddings_data(self) -> Optional[pd.DataFrame]:
        """加载向量嵌入数据"""
        embedding_files = list(self.data_dir.glob("*embeddings*.csv"))
        
        if not embedding_files:
            logger.warning("未找到向量嵌入文件")
            return None
        
        embedding_file = embedding_files[0]
        logger.info(f"加载向量嵌入文件: {embedding_file}")
        
        try:
            embeddings_df = pd.read_csv(embedding_file, index_col=0)
            logger.info(f"向量嵌入数据: {len(embeddings_df)} 个实体, {embeddings_df.shape[1]} 维")
            return embeddings_df
        except Exception as e:
            logger.error(f"向量嵌入加载失败: {e}")
            return None
    
    def load_predicted_links(self) -> Optional[pd.DataFrame]:
        """加载预测链接数据"""
        prediction_files = list(self.data_dir.glob("predicted_links*.csv"))
        
        if not prediction_files:
            logger.warning("未找到预测链接文件")
            return None
        
        prediction_file = prediction_files[0]
        logger.info(f"加载预测链接文件: {prediction_file}")
        
        try:
            predictions_df = pd.read_csv(prediction_file)
            logger.info(f"预测链接数据: {len(predictions_df)} 条预测")
            return predictions_df
        except Exception as e:
            logger.error(f"预测链接加载失败: {e}")
            return None
    
    def import_nodes(self, kg_data: Dict[str, Any], embeddings_df: Optional[pd.DataFrame] = None):
        """导入节点到Neo4j"""
        logger.info("开始导入节点...")
        
        with self.driver.session() as session:
            for node_id, node_data in kg_data["nodes"].items():
                node_type = node_data.get("type", "Entity")
                
                # 准备节点属性
                properties = {
                    "id": node_id,
                    "name": node_id,
                    "type": node_type,
                    "source": node_data.get("source", "unknown")
                }
                
                # 添加其他属性
                for key, value in node_data.items():
                    if key not in ["type", "source"] and value is not None:
                        if isinstance(value, (str, int, float, bool)):
                            properties[key] = value
                        elif isinstance(value, list):
                            properties[key] = json.dumps(value, ensure_ascii=False)
                
                # 添加向量嵌入
                if embeddings_df is not None and node_id in embeddings_df.index:
                    embedding_vector = embeddings_df.loc[node_id].values.tolist()
                    properties["embedding"] = embedding_vector
                    properties["embedding_dim"] = len(embedding_vector)
                
                # 根据类型确定标签
                labels = ["Entity"]
                if node_type == "element":
                    labels.append("Element")
                    properties["symbol"] = node_id
                elif node_type == "alloy":
                    labels.append("Alloy")
                elif node_type == "property":
                    labels.append("Property")
                elif node_type == "material":
                    labels.append("Material")
                
                # 创建节点的Cypher查询
                labels_str = ":".join(labels)
                
                # 构建属性字符串
                props_list = []
                for key, value in properties.items():
                    if isinstance(value, str):
                        props_list.append(f"{key}: '{value.replace(chr(39), chr(39)+chr(39))}'")
                    elif isinstance(value, list):
                        # 对于向量嵌入，使用特殊处理
                        if key == "embedding":
                            props_list.append(f"{key}: {value}")
                        else:
                            props_list.append(f"{key}: '{json.dumps(value, ensure_ascii=False)}'")
                    else:
                        props_list.append(f"{key}: {value}")
                
                props_str = "{" + ", ".join(props_list) + "}"
                
                query = f"""
                MERGE (n:{labels_str} {{id: $node_id}})
                SET n += $properties
                """
                
                try:
                    session.run(query, node_id=node_id, properties=properties)
                except Exception as e:
                    logger.error(f"节点创建失败 {node_id}: {e}")
        
        logger.info(f"节点导入完成: {len(kg_data['nodes'])} 个节点")
    
    def import_relationships(self, kg_data: Dict[str, Any]):
        """导入关系到Neo4j"""
        logger.info("开始导入关系...")
        
        with self.driver.session() as session:
            for edge in kg_data["edges"]:
                if len(edge) < 2:
                    continue
                
                source_id = edge[0]
                target_id = edge[1]
                rel_type = edge[2] if len(edge) > 2 else "RELATED_TO"
                
                # 关系属性
                rel_properties = {}
                if len(edge) > 3:
                    rel_properties = edge[3] if isinstance(edge[3], dict) else {}
                
                # 标准化关系类型
                rel_type = rel_type.upper().replace(" ", "_").replace("-", "_")
                
                query = f"""
                MATCH (a:Entity {{id: $source_id}})
                MATCH (b:Entity {{id: $target_id}})
                MERGE (a)-[r:{rel_type}]->(b)
                SET r += $properties
                """
                
                try:
                    session.run(query, 
                               source_id=source_id, 
                               target_id=target_id,
                               properties=rel_properties)
                except Exception as e:
                    logger.error(f"关系创建失败 {source_id} -> {target_id}: {e}")
        
        logger.info(f"关系导入完成: {len(kg_data['edges'])} 条关系")
    
    def import_predicted_links(self, predictions_df: Optional[pd.DataFrame]):
        """导入预测链接"""
        if predictions_df is None:
            return
        
        logger.info("开始导入预测链接...")
        
        with self.driver.session() as session:
            for _, row in predictions_df.iterrows():
                source_id = row.get("source", row.get("entity1", ""))
                target_id = row.get("target", row.get("entity2", ""))
                score = row.get("score", row.get("confidence", 0.5))
                
                if source_id and target_id:
                    query = """
                    MATCH (a:Entity {id: $source_id})
                    MATCH (b:Entity {id: $target_id})
                    MERGE (a)-[r:PREDICTED_LINK]->(b)
                    SET r.score = $score, r.type = 'predicted'
                    """
                    
                    try:
                        session.run(query, 
                                   source_id=source_id,
                                   target_id=target_id, 
                                   score=float(score))
                    except Exception as e:
                        logger.error(f"预测链接创建失败 {source_id} -> {target_id}: {e}")
        
        logger.info(f"预测链接导入完成: {len(predictions_df)} 条预测")
    
    def create_vector_index(self):
        """创建向量相似性索引"""
        with self.driver.session() as session:
            try:
                # 创建向量索引（Neo4j 5.0+）
                query = """
                CREATE VECTOR INDEX entity_embeddings IF NOT EXISTS
                FOR (e:Entity) ON (e.embedding)
                OPTIONS {indexConfig: {
                    `vector.dimensions`: 128,
                    `vector.similarity_function`: 'cosine'
                }}
                """
                session.run(query)
                logger.info("向量索引创建成功")
            except Exception as e:
                logger.warning(f"向量索引创建失败（可能需要Neo4j 5.0+）: {e}")
    
    def export_to_neo4j(self, clear_existing: bool = False):
        """完整的Neo4j导出流程"""
        logger.info("开始导出到Neo4j...")
        
        try:
            # 可选：清空现有数据
            if clear_existing:
                self.clear_database()
            
            # 创建约束和索引
            self.create_constraints_and_indexes()
            
            # 加载数据
            kg_data = self.load_knowledge_graph_data()
            embeddings_df = self.load_embeddings_data()
            predictions_df = self.load_predicted_links()
            
            # 导入节点
            self.import_nodes(kg_data, embeddings_df)
            
            # 导入关系
            self.import_relationships(kg_data)
            
            # 导入预测链接
            self.import_predicted_links(predictions_df)
            
            # 创建向量索引
            self.create_vector_index()
            
            logger.info("Neo4j导出完成！")
            
            # 显示统计信息
            self.show_statistics()
            
        except Exception as e:
            logger.error(f"Neo4j导出失败: {e}")
            raise
    
    def show_statistics(self):
        """显示导入统计"""
        with self.driver.session() as session:
            # 节点统计
            node_result = session.run("MATCH (n) RETURN labels(n) as labels, count(n) as count")
            logger.info("节点统计:")
            for record in node_result:
                labels = record["labels"]
                count = record["count"]
                logger.info(f"  {'/'.join(labels)}: {count}")
            
            # 关系统计
            rel_result = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(r) as count")
            logger.info("关系统计:")
            for record in rel_result:
                rel_type = record["type"]
                count = record["count"]
                logger.info(f"  {rel_type}: {count}")


def create_neo4j_query_examples():
    """创建Neo4j查询示例"""
    examples = """
# Neo4j Cypher查询示例

## 1. 查找所有钛合金
MATCH (a:Alloy) 
WHERE a.name CONTAINS 'Ti'
RETURN a.name, a.composition, a.properties

## 2. 查找Ti-6Al-4V的相关元素
MATCH (alloy:Alloy {name: 'Ti-6Al-4V'})-[:CONTAINS]->(element:Element)
RETURN alloy.name, element.symbol, element.content

## 3. 查找具有特定性能的合金
MATCH (a:Alloy)-[:HAS_PROPERTY]->(p:Property)
WHERE p.name CONTAINS '强度' AND p.value > 900
RETURN a.name, p.name, p.value

## 4. 向量相似性搜索（需要Neo4j 5.0+）
MATCH (target:Entity {name: 'Ti-6Al-4V'})
CALL db.index.vector.queryNodes('entity_embeddings', 5, target.embedding)
YIELD node, score
RETURN node.name, score

## 5. 查找预测的新关系
MATCH (a:Entity)-[r:PREDICTED_LINK]->(b:Entity)
WHERE r.score > 0.8
RETURN a.name, b.name, r.score
ORDER BY r.score DESC

## 6. 路径查询：从元素到性能的路径
MATCH path = (e:Element)-[*1..3]-(p:Property)
WHERE e.symbol = 'Ti'
RETURN path LIMIT 10

## 7. 聚合分析：每种元素的平均含量
MATCH (e:Element)-[r:CONTENT_OF]->(a:Alloy)
RETURN e.symbol, avg(toFloat(r.percentage)) as avg_content
ORDER BY avg_content DESC
"""
    
    results_dir = Path(__file__).resolve().parent.parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    with open(results_dir / "neo4j_query_examples.cypher", "w", encoding="utf-8") as f:
        f.write(examples)
    
    logger.info("Neo4j查询示例已保存到 results/neo4j_query_examples.cypher")


def main():
    """主函数"""
    print("钛合金知识图谱 -> Neo4j 导出工具")
    print("=" * 50)
    
    # 配置Neo4j连接（从环境变量读取，见 .env.example）
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USERNAME = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

    if not NEO4J_PASSWORD:
        print("错误：未设置 NEO4J_PASSWORD 环境变量，请参考 .env.example 配置后重试")
        return
    
    try:
        # 创建导出器
        exporter = Neo4jExporter(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
        
        # 询问是否清空数据库
        clear_db = input("是否清空现有数据库? (y/N): ").lower().strip() == 'y'
        
        # 执行导出
        exporter.export_to_neo4j(clear_existing=clear_db)
        
        # 创建查询示例
        create_neo4j_query_examples()
        
        # 关闭连接
        exporter.close()
        
        print("\n导出完成！可以通过Neo4j Browser查看数据:")
        print(f"URL: http://localhost:7474")
        print("查询示例文件: results/neo4j_query_examples.cypher")
        
    except Exception as e:
        logger.error(f"导出失败: {e}")
        print("请检查Neo4j服务是否运行，以及连接配置是否正确")


if __name__ == "__main__":
    main()