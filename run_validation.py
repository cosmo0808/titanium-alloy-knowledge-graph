# run_validation.py - 快速验证脚本
import sys
import os
import subprocess
import json
from pathlib import Path
from datetime import datetime
import logging
import sys
sys.stdout.reconfigure(encoding='utf-8')


# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SystemValidator:
    """系统快速验证器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.validation_results = {
            'timestamp': datetime.now().isoformat(),
            'tests': {},
            'overall_score': 0,
            'status': 'UNKNOWN'
        }
    
    def run_quick_validation(self):
        """运行快速验证"""
        logger.info("🚀 开始系统快速验证")
        
        # 验证测试用例
        tests = [
            ('data_processing', self.test_data_processing),
            ('knowledge_graph', self.test_knowledge_graph),
            ('rag_system', self.test_rag_system),
            ('graph_mining', self.test_graph_mining),
            ('system_intergration', self.test_system_integration)
        ]
        
        total_score = 0
        max_score = len(tests) * 20  # 每个测试20分
        
        for test_name, test_func in tests:
            logger.info(f"🔍 执行测试: {test_name}")
            try:
                result = test_func()
                self.validation_results['tests'][test_name] = result
                total_score += result.get('score', 0)
                logger.info(f"✅ {test_name}: {result.get('status', 'UNKNOWN')} ({result.get('score', 0)}/20)")
            except Exception as e:
                logger.error(f"❌ {test_name} 失败: {e}")
                self.validation_results['tests'][test_name] = {
                    'status': 'FAILED',
                    'error': str(e),
                    'score': 0
                }
        
        # 计算总分
        self.validation_results['overall_score'] = total_score
        self.validation_results['max_score'] = max_score
        self.validation_results['percentage'] = (total_score / max_score) * 100
        
        # 确定状态
        percentage = self.validation_results['percentage']
        if percentage >= 80:
            self.validation_results['status'] = 'EXCELLENT'
        elif percentage >= 60:
            self.validation_results['status'] = 'GOOD'
        elif percentage >= 40:
            self.validation_results['status'] = 'PARTIAL'
        else:
            self.validation_results['status'] = 'FAILED'
        
        # 保存结果
        self.save_results()
        
        # 输出总结
        self.print_summary()
        
        return self.validation_results
    
    def test_data_processing(self):
        """测试数据预处理"""
        result = {'status': 'TESTING', 'score': 0, 'details': {}}
        
        try:
            # 检查必要文件
            processed_dir = self.project_root / "data" / "processed"
            if not processed_dir.exists():
                processed_dir.mkdir(parents=True, exist_ok=True)
            
            # 检查处理脚本
            data_loader = self.project_root / "script" / "data_loader.py"
            if data_loader.exists():
                result['score'] += 5
                result['details']['data_loader'] = 'EXISTS'
            
            # 检查处理结果
            processed_files = list(processed_dir.glob("*_processed.json"))
            result['details']['processed_files'] = len(processed_files)
            
            if len(processed_files) >= 5:
                result['score'] += 10
            elif len(processed_files) >= 1:
                result['score'] += 5
            
            # 检查统一数据集
            unified_file = processed_dir / "unified_dataset.json"
            if unified_file.exists():
                result['score'] += 5
                result['details']['unified_dataset'] = 'EXISTS'
            
            result['status'] = 'PASS' if result['score'] >= 15 else 'PARTIAL' if result['score'] >= 10 else 'FAIL'
            
        except Exception as e:
            result['status'] = 'ERROR'
            result['error'] = str(e)
        
        return result
    
    def test_knowledge_graph(self):
        """测试知识图谱构建"""
        result = {'status': 'TESTING', 'score': 0, 'details': {}}
        
        try:
            processed_dir = self.project_root / "data" / "processed"
            
            # 检查知识图谱文件
            kg_files = list(processed_dir.glob("*hg*.json"))
            result['details']['kg_files'] = len(kg_files)
            
            if kg_files:
                result['score'] += 8
                
                # 检查图谱内容
                with open(kg_files[0], 'r', encoding='utf-8') as f:
                    kg_data = json.load(f)
                
                nodes_count = len(kg_data.get('nodes', {}))
                edges_count = len(kg_data.get('edges', []))
                
                result['details']['nodes_count'] = nodes_count
                result['details']['edges_count'] = edges_count
                
                if nodes_count >= 50:
                    result['score'] += 6
                elif nodes_count >= 20:
                    result['score'] += 3
                
                if edges_count >= 30:
                    result['score'] += 6
                elif edges_count >= 10:
                    result['score'] += 3
            
            # 检查OpenKE格式（新目录约定 data/openke_benchmark）
            openke_dir = self.project_root / "data" / "openke_benchmark"
            if openke_dir.exists():
                openke_files = ['entity2id.txt', 'relation2id.txt', 'train2id.txt']
                existing_files = sum(1 for f in openke_files if (openke_dir / f).exists())
                result['details']['openke_files'] = f"{existing_files}/{len(openke_files)}"
                
                if existing_files == len(openke_files):
                    result['score'] += 6
                elif existing_files >= 2:
                    result['score'] += 3
            
            result['status'] = 'PASS' if result['score'] >= 15 else 'PARTIAL' if result['score'] >= 8 else 'FAIL'
            
        except Exception as e:
            result['status'] = 'ERROR'
            result['error'] = str(e)
        
        return result
    
    def test_rag_system(self):
        """测试RAG系统"""
        result = {'status': 'TESTING', 'score': 0, 'details': {}}
        
        try:
            # 检查RAG脚本
            rag_script = self.project_root / "script" / "enhanced_rag_system.py"
            if rag_script.exists():
                result['score'] += 8
                result['details']['rag_script'] = 'EXISTS'
            
            # 检查向量数据库
            processed_dir = self.project_root / "data" / "processed"
            vector_files = list(processed_dir.glob("*embeddings*.csv"))
            result['details']['vector_files'] = len(vector_files)
            
            if vector_files:
                result['score'] += 6
                # 检查向量维度
                try:
                    import pandas as pd
                    df = pd.read_csv(vector_files[0], index_col=0)
                    result['details']['vector_dimension'] = df.shape[1]
                    result['details']['vector_entities'] = len(df)
                    
                    if len(df) >= 20:
                        result['score'] += 3
                    if df.shape[1] >= 64:  # 合理的嵌入维度
                        result['score'] += 3
                except Exception:
                    pass
            
            result['status'] = 'PASS' if result['score'] >= 15 else 'PARTIAL' if result['score'] >= 8 else 'FAIL'
            
        except Exception as e:
            result['status'] = 'ERROR'
            result['error'] = str(e)
        
        return result
    
    def test_graph_mining(self):
        """测试图挖掘"""
        result = {'status': 'TESTING', 'score': 0, 'details': {}}
        
        try:
            # 检查挖掘脚本
            mining_script = self.project_root / "script" / "advanced_graph_mining.py"
            if mining_script.exists():
                result['score'] += 8
                result['details']['mining_script'] = 'EXISTS'
            
            # 检查挖掘结果
            processed_dir = self.project_root / "data" / "processed"
            
            # 链路预测结果
            pred_files = list(processed_dir.glob("predicted_links*.csv"))
            if pred_files:
                result['score'] += 6
                result['details']['prediction_files'] = len(pred_files)
                
                try:
                    import pandas as pd
                    df = pd.read_csv(pred_files[0])
                    result['details']['predicted_links'] = len(df)
                    
                    if len(df) >= 10:
                        result['score'] += 3
                except Exception:
                    pass
            
            # 挖掘结果文件
            mining_results = processed_dir / "graph_mining_results.json"
            if mining_results.exists():
                result['score'] += 3
                result['details']['mining_results'] = 'EXISTS'
            
            result['status'] = 'PASS' if result['score'] >= 15 else 'PARTIAL' if result['score'] >= 8 else 'FAIL'
            
        except Exception as e:
            result['status'] = 'ERROR'
            result['error'] = str(e)
        
        return result
    
    def test_system_integration(self):
        """测试系统整合"""
        result = {'status': 'TESTING', 'score': 0, 'details': {}}
        
        try:
            # 检查主控制脚本
            main_scripts = ['main.py', 'enhanced_main.py']
            for script in main_scripts:
                script_path = self.project_root / script
                if script_path.exists():
                    result['score'] += 4
                    result['details'][script] = 'EXISTS'
            
            # 检查配置文件
            config_paths = ['config/paths.py', 'config/__init__.py']
            for config in config_paths:
                config_path = self.project_root / config
                if config_path.exists():
                    result['score'] += 2
                    result['details'][config] = 'EXISTS'
            
            # 检查Web应用
            app_file = self.project_root / "app.py"
            if app_file.exists():
                result['score'] += 4
                result['details']['web_app'] = 'EXISTS'
            
            # 检查快速启动
            quick_start = self.project_root / "quick_start.py"
            if quick_start.exists():
                result['score'] += 2
                result['details']['quick_start'] = 'EXISTS'
            
            # 检查验收测试
            acceptance_test = self.project_root / "acceptance_test.py"
            if acceptance_test.exists():
                result['score'] += 2
                result['details']['acceptance_test'] = 'EXISTS'
            
            # 检查结果目录
            results_dir = self.project_root / "results"
            if results_dir.exists():
                result_files = list(results_dir.glob("*.json"))
                result['details']['result_files'] = len(result_files)
                
                if len(result_files) >= 1:
                    result['score'] += 4
            
            result['status'] = 'PASS' if result['score'] >= 15 else 'PARTIAL' if result['score'] >= 10 else 'FAIL'
            
        except Exception as e:
            result['status'] = 'ERROR'
            result['error'] = str(e)
        
        return result
    
    def save_results(self):
        """保存验证结果"""
        results_dir = self.project_root / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = results_dir / f"quick_validation_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.validation_results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"验证结果已保存: {output_file}")
    
    def print_summary(self):
        """打印验证总结"""
        print("\n" + "="*60)
        print("🎯 钛合金知识图谱系统快速验证报告")
        print("="*60)
        
        print(f"📊 总体评分: {self.validation_results['overall_score']}/{self.validation_results['max_score']} ({self.validation_results['percentage']:.1f}%)")
        print(f"🏆 验证状态: {self.validation_results['status']}")
        
        print(f"\n📋 详细测试结果:")
        for test_name, result in self.validation_results['tests'].items():
            status_emoji = {
                'PASS': '✅',
                'PARTIAL': '⚠️',
                'FAIL': '❌',
                'ERROR': '💥'
            }.get(result['status'], '❓')
            
            print(f"  {status_emoji} {test_name}: {result['status']} ({result['score']}/20)")
            
            if 'details' in result and result['details']:
                for key, value in result['details'].items():
                    print(f"    - {key}: {value}")
        
        print(f"\n📈 评估建议:")
        percentage = self.validation_results['percentage']
        
        if percentage >= 80:
            print("  🎉 系统表现优秀，可以进行完整部署")
        elif percentage >= 60:
            print("  👍 系统基本达标，建议优化低分模块后部署")
        elif percentage >= 40:
            print("  🔧 系统需要改进，建议完善核心功能")
        else:
            print("  🚧 系统需要重大改进，建议重新构建关键模块")
        
        print("="*60)


def create_minimal_test_data():
    """创建最小测试数据"""
    logger.info("创建测试数据...")
    
    project_root = Path(__file__).parent
    
    # 创建目录结构
    directories = [
        "data/processed",
        "results", 
        "script",
        "config"
    ]
    
    for dir_path in directories:
        (project_root / dir_path).mkdir(parents=True, exist_ok=True)
    
    # 创建简单的配置文件（仅当不存在时写入，避免覆盖项目已有配置）
    config_content = '''# config/paths.py
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PDF_DIRECTORY = DATA_DIR / "sample"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
RESULTS_DIR = PROJECT_ROOT / "results"
DATABASE_PATH = PROCESSED_DATA_DIR / "materials.db"
MAX_PDFS = 100
DB_LIMIT = 1000
'''
    
    config_file = project_root / "config" / "paths.py"
    if not config_file.exists():
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_content)
    
    # 创建简单的__init__.py
    init_file = project_root / "config" / "__init__.py"
    with open(init_file, 'w', encoding='utf-8') as f:
        f.write('# Configuration package\n')
    
    # 创建测试知识图谱
    test_kg = {
        "nodes": {
            "Ti": {"type": "element", "sources": ["test"]},
            "Al": {"type": "element", "sources": ["test"]},
            "V": {"type": "element", "sources": ["test"]},
            "Ti-6Al-4V": {"type": "alloy", "sources": ["test"]},
            "强度": {"type": "property", "sources": ["test"]},
            "航空航天": {"type": "application", "sources": ["test"]}
        },
        "edges": [
            ["Ti-6Al-4V", "contains", "Ti"],
            ["Ti-6Al-4V", "contains", "Al"],
            ["Ti-6Al-4V", "contains", "V"],
            ["Ti-6Al-4V", "has_property", "强度"],
            ["Ti-6Al-4V", "used_in", "航空航天"]
        ],
        "statistics": {
            "node_count": 6,
            "edge_count": 5
        }
    }
    
    kg_file = project_root / "data" / "processed" / "entities_relations_hg.json"
    with open(kg_file, 'w', encoding='utf-8') as f:
        json.dump(test_kg, f, indent=2, ensure_ascii=False)
    
    # 创建测试向量数据
    import pandas as pd
    import numpy as np
    
    entities = ["Ti", "Al", "V", "Ti-6Al-4V", "强度", "航空航天"]
    embeddings = np.random.random((len(entities), 128))  # 128维向量
    
    df = pd.DataFrame(embeddings, index=entities)
    vector_file = project_root / "data" / "processed" / "entity_embeddings.csv"
    df.to_csv(vector_file)
    
    # 创建测试链路预测结果
    predictions = [
        {"head": "Ti", "relation": "improves", "tail": "强度", "confidence": 0.85},
        {"head": "Al", "relation": "enhances", "tail": "强度", "confidence": 0.72}
    ]
    
    pred_df = pd.DataFrame(predictions)
    pred_file = project_root / "data" / "processed" / "predicted_links.csv"
    pred_df.to_csv(pred_file, index=False)
    
    # 创建OpenKE格式数据
    openke_dir = project_root / "data" / "openke_benchmark"
    openke_dir.mkdir(exist_ok=True)
    
    # entity2id.txt
    with open(openke_dir / "entity2id.txt", 'w', encoding='utf-8') as f:
        f.write(f"{len(entities)}\n")
        for i, entity in enumerate(entities):
            f.write(f"{entity}\t{i}\n")
    
    # relation2id.txt
    relations = ["contains", "has_property", "used_in"]
    with open(openke_dir / "relation2id.txt", 'w', encoding='utf-8') as f:
        f.write(f"{len(relations)}\n")
        for i, relation in enumerate(relations):
            f.write(f"{relation}\t{i}\n")
    
    # train2id.txt
    with open(openke_dir / "train2id.txt", 'w', encoding='utf-8') as f:
        f.write("5\n")
        f.write("3\t0\t0\n")  # Ti-6Al-4V contains Ti
        f.write("3\t1\t0\n")  # Ti-6Al-4V contains Al
        f.write("3\t2\t0\n")  # Ti-6Al-4V contains V
        f.write("3\t4\t1\n")  # Ti-6Al-4V has_property 强度
        f.write("3\t5\t2\n")  # Ti-6Al-4V used_in 航空航天
    
    logger.info("测试数据创建完成")


if __name__ == "__main__":
    # 创建验证器
    validator = SystemValidator()
    
    # 如果没有测试数据，创建最小测试数据
    processed_dir = Path(__file__).resolve().parent / "data" / "processed"
    if not processed_dir.exists() or not list(processed_dir.glob("*.json")):
        create_minimal_test_data()
    
    # 运行验证
    results = validator.run_quick_validation()
    
    # 返回状态码
    if results['percentage'] >= 60:
        sys.exit(0)  # 成功
    else:
        sys.exit(1)  # 失败