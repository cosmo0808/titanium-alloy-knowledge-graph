# run_knowledge_storage.py - 知识存储系统集成脚本
import sys
import json
from pathlib import Path
from datetime import datetime
import logging
import networkx as nx
sys.stdout.reconfigure(encoding='utf-8')



# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """运行知识存储系统演示"""
    print("=" * 60)
    print("钛合金知识图谱存储系统演示")
    print("=" * 60)
    
    try:
        from script.knowledge_storage_system import MultimodalKnowledgeGraph
        
        # 1. 初始化系统
        print("1. 初始化多模态知识图谱系统...")
        storage_dir = PROJECT_ROOT / "data" / "graph_storage"
        kg_system = MultimodalKnowledgeGraph(storage_dir)
        
        # 2. 导入现有知识图谱
        print("2. 导入现有知识图谱...")
        kg_files = list((PROJECT_ROOT / "data" / "processed").glob("*hg*.json"))
        
        if kg_files:
            kg_file = kg_files[0]
            print(f"   导入文件: {kg_file}")
            kg_system.import_from_json(kg_file)
        else:
            print("   未找到知识图谱文件，创建示例数据...")
            # 创建示例数据
            kg_system.graph_db.add_node("Ti-6Al-4V", "alloy", {"description": "常用钛合金"})
            kg_system.graph_db.add_node("Ti", "element", {"atomic_number": 22})
            kg_system.graph_db.add_node("Al", "element", {"atomic_number": 13})
            kg_system.graph_db.add_node("V", "element", {"atomic_number": 23})
            kg_system.graph_db.add_node("强度", "property", {"unit": "MPa"})
            kg_system.graph_db.add_node("航空航天", "application", {"industry": "aerospace"})
            
            # 添加关系
            kg_system.graph_db.add_edge("Ti-6Al-4V", "Ti", "contains", weight=0.9)
            kg_system.graph_db.add_edge("Ti-6Al-4V", "Al", "contains", weight=0.06)
            kg_system.graph_db.add_edge("Ti-6Al-4V", "V", "contains", weight=0.04)
            kg_system.graph_db.add_edge("Ti-6Al-4V", "强度", "has_property")
            kg_system.graph_db.add_edge("Ti-6Al-4V", "航空航天", "used_in")
        
        # 3. 质量评估
        print("3. 执行质量评估...")
        quality_metrics = kg_system.quality_evaluator.evaluate_graph_quality(kg_system.graph_db)
        quality_report = kg_system.quality_evaluator.generate_quality_report()
        
        print("   质量评估结果:")
        for metric, score in quality_metrics.items():
            print(f"     {metric}: {score:.3f}")
        
        # 4. 图数据库查询演示
        print("4. 图数据库查询演示...")
        
        # 获取所有节点
        nodes = list(kg_system.graph_db.graph.nodes())
        print(f"   图中包含 {len(nodes)} 个节点")
        
        if len(nodes) >= 2:
            # 最短路径查询
            source, target = nodes[0], nodes[1]
            path = kg_system.graph_db.shortest_path(source, target)
            print(f"   {source} 到 {target} 的最短路径: {' -> '.join(path) if path else '无路径'}")
            
            # 邻居查询
            neighbors = kg_system.graph_db.get_neighbors(nodes[0])
            print(f"   {nodes[0]} 的邻居节点: {neighbors}")
        
        # 5. 语义搜索演示
        print("5. 语义搜索演示...")
        search_queries = ["钛合金", "强度", "航空"]
        
        for query in search_queries:
            results = kg_system.semantic_search(query, top_k=3)
            print(f"   搜索 '{query}' 的结果:")
            for result in results:
                print(f"     - {result['node_id']} (相关性: {result['relevance_score']:.2f})")
        
        # 6. 图查询演示
        print("6. 图查询演示...")
        if nodes:
            graph_query_result = kg_system.graph_query(nodes[0], max_hops=2)
            print(f"   从 {nodes[0]} 开始的2跳查询:")
            print(f"     找到 {graph_query_result['node_count']} 个节点, {graph_query_result['edge_count']} 条边")
        
        # 7. 多模态上下文添加
        print("7. 添加多模态上下文...")
        if nodes:
            # 为第一个节点添加文本上下文
            kg_system.add_multimodal_context(
                nodes[0], 
                'text_chunks', 
                {
                    'content': f'{nodes[0]}是一种重要的材料',
                    'source': 'example_document.pdf',
                    'page': 1
                }
            )
            
            # 添加表格上下文
            kg_system.add_multimodal_context(
                nodes[0],
                'table_data',
                {
                    'table_type': 'properties',
                    'data': {'strength': '900 MPa', 'density': '4.43 g/cm³'},
                    'source': 'material_database'
                }
            )
            
            print(f"   为 {nodes[0]} 添加了多模态上下文")
        
        # 8. 图谱优化
        print("8. 执行图谱优化...")
        optimization_result = kg_system.optimize_graph()
        print("   优化完成")
        
        # 9. 导出RAG格式
        print("9. 导出RAG格式数据...")
        rag_data = kg_system.export_to_rag_format()
        
        # 保存RAG格式数据
        rag_file = storage_dir / "rag_formatted_data.json"
        with open(rag_file, 'w', encoding='utf-8') as f:
            json.dump(rag_data, f, indent=2, ensure_ascii=False)
        
        print(f"   导出完成: {len(rag_data['entities'])} 个实体, {len(rag_data['relations'])} 个关系")
        print(f"   RAG数据已保存: {rag_file}")
        
        # 10. 保存系统状态
        print("10. 保存系统状态...")
        kg_system.save_system_state()
        
        # 11. 生成报告
        print("11. 生成系统报告...")
        generate_system_report(kg_system, storage_dir, quality_metrics)
        
        print("\n" + "=" * 60)
        print("知识存储系统演示完成!")
        print("=" * 60)
        print("主要输出文件:")
        print(f"  - 图数据库: {kg_system.graph_db.db_path}")
        print(f"  - RAG格式数据: {rag_file}")
        print(f"  - 系统状态: {storage_dir / 'system_state.pkl'}")
        print(f"  - 系统报告: {storage_dir / 'system_report.json'}")
        
        return True
        
    except Exception as e:
        logger.error(f"知识存储系统运行失败: {e}")
        return False


def generate_system_report(kg_system, storage_dir: Path, quality_metrics: dict):
    """生成系统报告"""
    
    # 收集系统统计信息
    graph = kg_system.graph_db.graph
    
    # 节点类型分布
    node_types = {}
    for node, data in graph.nodes(data=True):
        node_type = data.get('type', 'unknown')
        node_types[node_type] = node_types.get(node_type, 0) + 1
    
    # 关系类型分布
    relation_types = {}
    for u, v, data in graph.edges(data=True):
        relation = data.get('relation', 'unknown')
        relation_types[relation] = relation_types.get(relation, 0) + 1
    
    # 连通性分析
    connected_components = list(nx.weakly_connected_components(graph)) if graph.is_directed() else list(nx.connected_components(graph))
    largest_component_size = max(len(comp) for comp in connected_components) if connected_components else 0
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'system_info': {
            'total_nodes': len(graph.nodes),
            'total_edges': len(graph.edges),
            'node_types': node_types,
            'relation_types': relation_types,
            'connected_components': len(connected_components),
            'largest_component_size': largest_component_size
        },
        'quality_metrics': quality_metrics,
        'multimodal_data': {
            'text_chunks': len(kg_system.multimodal_data.get('text_chunks', {})),
            'table_data': len(kg_system.multimodal_data.get('table_data', {})),
            'image_metadata': len(kg_system.multimodal_data.get('image_metadata', {})),
            'formula_data': len(kg_system.multimodal_data.get('formula_data', {}))
        },
        'storage_info': {
            'graph_database_path': str(kg_system.graph_db.db_path),
            'storage_directory': str(storage_dir)
        }
    }
    
    # 保存报告
    report_file = storage_dir / "system_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    logger.info(f"系统报告已保存: {report_file}")


if __name__ == "__main__":
    success = main()
    if success:
        print("\n知识存储系统运行成功")
    else:
        print("\n知识存储系统运行失败")
        sys.exit(1)