# db_to_graphml_generator.py - 从materials.db生成GraphML文件
import sqlite3
import pandas as pd
import networkx as nx
import json
import sys
import re
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent if Path(__file__).parent.name == 'script' else Path(__file__).parent
sys.path.append(str(PROJECT_ROOT))

try:
    from config.paths import DATABASE_PATH, PROCESSED_DATA_DIR
except ImportError:
    # Fallback paths if config is not available
    DATABASE_PATH = PROJECT_ROOT / "materials.db"
    PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"

class DatabaseGraphMLGenerator:
    """从materials.db数据库生成GraphML文件的类"""
    
    def __init__(self):
        self.db_path = DATABASE_PATH
        self.output_dir = PROCESSED_DATA_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 有效化学元素
        self.valid_elements = {
            "H","He","Li","Be","B","C","N","O","F","Ne",
            "Na","Mg","Al","Si","P","S","Cl","Ar",
            "K","Ca","Sc","Ti","V","Cr","Mn","Fe","Co","Ni","Cu","Zn",
            "Ga","Ge","As","Se","Br","Kr",
            "Rb","Sr","Y","Zr","Nb","Mo","Tc","Ru","Rh","Pd","Ag","Cd",
            "In","Sn","Sb","Te","I","Xe",
            "Cs","Ba","La","Ce","Pr","Nd","Pm","Sm","Eu","Gd","Tb","Dy",
            "Ho","Er","Tm","Yb","Lu","Hf","Ta","W","Re","Os","Ir","Pt","Au","Hg",
            "Tl","Pb","Bi","Po","At","Rn"
        }
        
        # 节点颜色映射
        self.color_map = {
            'element': '#FF6B6B',       # 红色 - 元素
            'alloy': '#45B7D1',         # 蓝色 - 合金
            'property': '#FFEAA7',      # 黄色 - 性能
            'composition': '#96CEB4',   # 绿色 - 成分
            'application': '#DDA0DD',   # 紫色 - 应用
            'process': '#FFB347',       # 橙色 - 工艺
            'measurement': '#F0E68C'    # 卡其色 - 测量
        }
    
    def load_database_tables(self):
        """加载数据库表"""
        if not self.db_path.exists():
            print(f"数据库文件不存在: {self.db_path}")
            return {}
        
        tables = {}
        try:
            conn = sqlite3.connect(self.db_path)
            
            # 获取所有表名
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            table_names = [row[0] for row in cursor.fetchall()]
            
            print(f"发现数据库表: {table_names}")
            
            # 加载每个表
            for table_name in table_names:
                try:
                    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
                    tables[table_name] = df
                    print(f"加载表 {table_name}: {len(df)} 行, {len(df.columns)} 列")
                except Exception as e:
                    print(f"加载表 {table_name} 失败: {e}")
            
            conn.close()
            
        except Exception as e:
            print(f"连接数据库失败: {e}")
        
        return tables
    
    def clean_text(self, text):
        """清理文本"""
        if pd.isna(text) or not text:
            return ""
        
        text = str(text).replace("\n", " ").strip()
        text = re.sub(r"\(.*?\)", "", text)  # 移除括号内容
        text = re.sub(r"\s+", " ", text)     # 合并多个空格
        return text.strip()
    
    def extract_elements_from_alloy_name(self, alloy_name):
        """从合金名称中提取元素"""
        elements = []
        
        # 使用正则表达式匹配化学元素符号
        element_matches = re.findall(r"[A-Z][a-z]?", alloy_name)
        
        for element in element_matches:
            if element in self.valid_elements:
                elements.append(element)
        
        return elements
    
    def process_materials_table(self, df):
        """处理Materials表"""
        nodes = {}
        edges = []
        
        if df.empty:
            return nodes, edges
        
        # 查找名称列
        name_columns = ['name', 'material_name', 'alloy_name', 'title', 'material']
        name_col = None
        
        for col in name_columns:
            if col in df.columns:
                name_col = col
                break
        
        if name_col is None and len(df.columns) > 1:
            name_col = df.columns[1]  # 使用第二列作为后备
        
        if name_col is None:
            print("无法识别Materials表的名称列")
            return nodes, edges
        
        print(f"使用列 '{name_col}' 作为材料名称")
        
        for _, row in df.iterrows():
            try:
                material_name = self.clean_text(row[name_col])
                if not material_name:
                    continue
                
                # 添加合金节点
                if material_name not in nodes:
                    nodes[material_name] = {
                        "type": "alloy",
                        "label": material_name,
                        "source": "database",
                        "color": self.color_map['alloy']
                    }
                
                # 提取并添加元素节点
                elements = self.extract_elements_from_alloy_name(material_name)
                for element in elements:
                    if element not in nodes:
                        nodes[element] = {
                            "type": "element",
                            "label": element,
                            "source": "database",
                            "color": self.color_map['element']
                        }
                    
                    # 添加关系: 合金包含元素
                    edge = (material_name, element, "contains")
                    if edge not in edges:
                        edges.append(edge)
                
                # 处理其他列作为属性
                for col in df.columns:
                    if col != name_col and not pd.isna(row[col]):
                        value = self.clean_text(row[col])
                        if value and len(value) > 1:
                            attr_name = f"{col}: {value}"
                            
                            if attr_name not in nodes:
                                nodes[attr_name] = {
                                    "type": "property",
                                    "label": attr_name,
                                    "source": "database",
                                    "color": self.color_map['property']
                                }
                            
                            edge = (material_name, attr_name, "has_property")
                            if edge not in edges:
                                edges.append(edge)
            
            except Exception as e:
                print(f"处理材料行时出错: {e}")
                continue
        
        return nodes, edges
    
    def process_properties_table(self, df, existing_nodes):
        """处理Properties表"""
        nodes = {}
        edges = []
        
        if df.empty:
            return nodes, edges
        
        # 查找相关列
        material_columns = ['material', 'material_id', 'material_name', 'alloy', 'alloy_name']
        property_columns = ['property', 'property_name', 'property_type', 'name']
        value_columns = ['value', 'metric_value', 'english_value', 'measurement', 'val']
        
        material_col = None
        property_col = None
        value_col = None
        
        for col in material_columns:
            if col in df.columns:
                material_col = col
                break
        
        for col in property_columns:
            if col in df.columns:
                property_col = col
                break
        
        for col in value_columns:
            if col in df.columns:
                value_col = col
                break
        
        if not property_col:
            print("Properties表中未找到属性列")
            return nodes, edges
        
        print(f"Properties表列映射: material='{material_col}', property='{property_col}', value='{value_col}'")
        
        for _, row in df.iterrows():
            try:
                # 获取属性信息
                prop_name = self.clean_text(row[property_col])
                if not prop_name:
                    continue
                
                # 获取值
                value = ""
                if value_col and not pd.isna(row[value_col]):
                    value = self.clean_text(row[value_col])
                
                # 创建属性节点
                if value:
                    prop_node_name = f"{prop_name}: {value}"
                else:
                    prop_node_name = prop_name
                
                if prop_node_name not in nodes:
                    nodes[prop_node_name] = {
                        "type": "property",
                        "label": prop_node_name,
                        "source": "database",
                        "color": self.color_map['property']
                    }
                
                # 连接到材料
                if material_col:
                    material_ref = self.clean_text(row[material_col])
                    if material_ref:
                        # 查找匹配的材料节点
                        matching_material = None
                        for material_name in existing_nodes:
                            if existing_nodes[material_name]["type"] == "alloy":
                                if (material_ref in material_name or 
                                    material_name in material_ref or
                                    material_ref.lower() == material_name.lower()):
                                    matching_material = material_name
                                    break
                        
                        if matching_material:
                            edge = (matching_material, prop_node_name, "has_property")
                            if edge not in edges:
                                edges.append(edge)
            
            except Exception as e:
                print(f"处理属性行时出错: {e}")
                continue
        
        return nodes, edges
    
    def create_knowledge_graph(self, all_nodes, all_edges):
        """创建知识图谱"""
        G = nx.DiGraph()
        
        # 添加节点
        for node_id, node_data in all_nodes.items():
            G.add_node(node_id, **node_data)
        
        # 添加边
        for source, target, relation in all_edges:
            if source in G.nodes and target in G.nodes:
                G.add_edge(source, target, relation=relation, weight=1.0)
        
        return G
    
    def create_hypergraph(self, G):
        """创建超图"""
        H = G.copy()
        
        # 添加超边节点
        hyperedges = []
        
        # 1. 合金组成超边
        alloy_nodes = [n for n, d in G.nodes(data=True) if d.get('type') == 'alloy']
        if alloy_nodes:
            he_composition = "HE_alloy_composition"
            H.add_node(he_composition, 
                      type='hyperedge',
                      hyperedge_type='alloy_composition',
                      label='合金组成超边',
                      description='连接合金与其组成元素',
                      color='#FF69B4')
            
            # 连接合金和元素
            for alloy in alloy_nodes[:5]:  # 限制数量避免过于复杂
                H.add_edge(he_composition, alloy, relation='hyperedge_connects')
                
                # 找到该合金的元素
                for _, target, data in G.edges(alloy, data=True):
                    if (G.nodes[target].get('type') == 'element' and 
                        data.get('relation') == 'contains'):
                        H.add_edge(he_composition, target, relation='hyperedge_connects')
            
            hyperedges.append(he_composition)
        
        # 2. 性能特征超边
        property_nodes = [n for n, d in G.nodes(data=True) if d.get('type') == 'property']
        if property_nodes:
            he_properties = "HE_material_properties"
            H.add_node(he_properties,
                      type='hyperedge', 
                      hyperedge_type='material_properties',
                      label='材料性能超边',
                      description='连接材料与其性能特征',
                      color='#32CD32')
            
            # 连接材料和属性
            for prop in property_nodes[:10]:  # 限制数量
                H.add_edge(he_properties, prop, relation='hyperedge_connects')
                
                # 找到拥有该属性的材料
                for source, _, data in G.edges(data=True):
                    if data.get('relation') == 'has_property' and _ == prop:
                        H.add_edge(he_properties, source, relation='hyperedge_connects')
            
            hyperedges.append(he_properties)
        
        return H, hyperedges
    
    def save_graphml_files(self):
        """保存GraphML文件"""
        print("开始处理数据库...")
        
        # 加载数据库
        tables = self.load_database_tables()
        if not tables:
            print("没有可用的数据库表")
            return None, None
        
        # 处理所有表
        all_nodes = {}
        all_edges = []
        
        # 处理Materials表
        if 'Materials' in tables:
            mat_nodes, mat_edges = self.process_materials_table(tables['Materials'])
            all_nodes.update(mat_nodes)
            all_edges.extend(mat_edges)
            print(f"从Materials表提取: {len(mat_nodes)} 节点, {len(mat_edges)} 边")
        
        # 处理Properties表
        if 'Properties' in tables:
            prop_nodes, prop_edges = self.process_properties_table(tables['Properties'], all_nodes)
            all_nodes.update(prop_nodes)
            all_edges.extend(prop_edges)
            print(f"从Properties表提取: {len(prop_nodes)} 节点, {len(prop_edges)} 边")
        
        # 处理其他表
        for table_name, df in tables.items():
            if table_name not in ['Materials', 'Properties'] and not df.empty:
                # 简单处理其他表
                for col in df.columns:
                    unique_values = df[col].dropna().unique()
                    for value in unique_values[:20]:  # 限制数量
                        value_str = self.clean_text(value)
                        if value_str and len(value_str) > 1:
                            node_name = f"{table_name}_{col}: {value_str}"
                            if node_name not in all_nodes:
                                all_nodes[node_name] = {
                                    "type": "database_attribute",
                                    "label": node_name,
                                    "source": f"database_{table_name}",
                                    "color": self.color_map.get('measurement', '#CCCCCC')
                                }
        
        print(f"总计: {len(all_nodes)} 节点, {len(all_edges)} 边")
        
        if not all_nodes:
            print("没有提取到任何实体")
            return None, None
        
        # 创建知识图谱
        G = self.create_knowledge_graph(all_nodes, all_edges)
        
        # 创建超图
        H, hyperedges = self.create_hypergraph(G)
        
        # 保存GraphML文件
        kg_file = self.output_dir / "knowledge_graph.graphml"
        nx.write_graphml(G, kg_file, encoding='utf-8')
        
        hg_file = self.output_dir / "hypergraph.graphml"
        nx.write_graphml(H, hg_file, encoding='utf-8')
        
        # 保存超图文本描述
        hg_txt_file = self.output_dir / "hypergraph_structure.txt"
        with open(hg_txt_file, 'w', encoding='utf-8') as f:
            f.write("Materials Database Hypergraph Structure\n")
            f.write("=" * 50 + "\n\n")
            
            f.write("NODES:\n")
            node_types = {}
            for node, data in H.nodes(data=True):
                node_type = data.get('type', 'unknown')
                node_types[node_type] = node_types.get(node_type, 0) + 1
                f.write(f"- {node}: {node_type}\n")
            
            f.write(f"\nNODE TYPE STATISTICS:\n")
            for node_type, count in node_types.items():
                f.write(f"- {node_type}: {count}\n")
            
            f.write(f"\nHYPEREDGES:\n")
            for he in hyperedges:
                he_data = H.nodes[he]
                f.write(f"\n{he}:\n")
                f.write(f"  Type: {he_data.get('hyperedge_type', 'unknown')}\n")
                f.write(f"  Description: {he_data.get('description', 'N/A')}\n")
                
                connected = [n for n in H.neighbors(he) if H.nodes[n].get('type') != 'hyperedge']
                f.write(f"  Connected Nodes ({len(connected)}): {', '.join(connected[:10])}\n")
                if len(connected) > 10:
                    f.write(f"  ... and {len(connected) - 10} more\n")
        
        # 生成统计报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "database_file": str(self.db_path),
            "tables_processed": list(tables.keys()),
            "knowledge_graph": {
                "nodes": G.number_of_nodes(),
                "edges": G.number_of_edges(),
                "file": str(kg_file)
            },
            "hypergraph": {
                "nodes": H.number_of_nodes(),
                "edges": H.number_of_edges(),
                "hyperedges": len(hyperedges),
                "file": str(hg_file),
                "txt_file": str(hg_txt_file)
            },
            "node_type_distribution": node_types
        }
        
        report_file = self.output_dir / "database_graphml_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\nGraphML文件生成完成!")
        print(f"知识图谱: {kg_file}")
        print(f"超图: {hg_file}")
        print(f"超图文档: {hg_txt_file}")
        print(f"统计报告: {report_file}")
        
        return kg_file, hg_file

def main():
    """主函数"""
    generator = DatabaseGraphMLGenerator()
    kg_file, hg_file = generator.save_graphml_files()
    
    if kg_file and hg_file:
        print("\n验收文件已准备完成:")
        print(f"- knowledge_graph.graphml: 标准知识图谱")
        print(f"- hypergraph.graphml: 超图版本")
        print(f"- hypergraph_structure.txt: 超图文档")
    else:
        print("\n文件生成失败，请检查数据库连接")

if __name__ == "__main__":
    main()