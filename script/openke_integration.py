# enhanced_kg_embedding.py - 增强版知识图嵌入集成脚本
import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path
import logging
from typing import Dict, List, Tuple, Optional, Union
import random
from tqdm import tqdm
import time
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

class EnhancedTransE:
    """增强版TransE模型，支持不同数据源"""
    
    def __init__(self, entity_count: int, relation_count: int, 
                 embedding_dim: int = 64, margin: float = 1.0,
                 data_source: str = "general"):
        self.entity_count = entity_count
        self.relation_count = relation_count
        self.embedding_dim = embedding_dim
        self.margin = margin
        self.data_source = data_source
        
        # 初始化嵌入矩阵
        self.entity_embeddings = np.random.uniform(
            -6/np.sqrt(embedding_dim), 6/np.sqrt(embedding_dim),
            (entity_count, embedding_dim)
        )
        self.relation_embeddings = np.random.uniform(
            -6/np.sqrt(embedding_dim), 6/np.sqrt(embedding_dim),
            (relation_count, embedding_dim)
        )
        
        # 归一化实体嵌入
        self._normalize_entity_embeddings()
        
        # 训练统计
        self.training_stats = {
            'epochs_completed': 0,
            'best_loss': float('inf'),
            'training_time': 0,
            'final_loss': 0
        }
        
        logger.info(f"TransE模型初始化 [{data_source}]: 实体={entity_count}, 关系={relation_count}, 维度={embedding_dim}")
    
    def _normalize_entity_embeddings(self):
        """归一化实体嵌入向量"""
        norms = np.linalg.norm(self.entity_embeddings, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-8)
        self.entity_embeddings = self.entity_embeddings / norms
    
    def _score_triplet(self, head: int, relation: int, tail: int) -> float:
        """计算三元组得分"""
        h = self.entity_embeddings[head]
        r = self.relation_embeddings[relation]
        t = self.entity_embeddings[tail]
        return np.linalg.norm(h + r - t)
    
    def _generate_negative_sample(self, head: int, relation: int, tail: int, 
                                 valid_entities: Optional[set] = None) -> Tuple[int, int, int]:
        """生成负样本，可以指定有效实体集合"""
        if valid_entities is None:
            valid_entities = set(range(self.entity_count))
        
        if random.random() < 0.5:
            # 替换头实体
            candidates = list(valid_entities - {head})
            if candidates:
                neg_head = random.choice(candidates)
                return neg_head, relation, tail
        
        # 替换尾实体
        candidates = list(valid_entities - {tail})
        if candidates:
            neg_tail = random.choice(candidates)
            return head, relation, neg_tail
        
        # 如果没有有效候选，使用原始方法
        if random.random() < 0.5:
            neg_head = random.randint(0, self.entity_count - 1)
            return neg_head, relation, tail
        else:
            neg_tail = random.randint(0, self.entity_count - 1)
            return head, relation, neg_tail
    
    def train_step(self, positive_triplets: List[Tuple[int, int, int]], 
                   learning_rate: float = 0.01, neg_samples_per_pos: int = 1):
        """执行一步训练"""
        total_loss = 0.0
        
        for pos_triplet in positive_triplets:
            head, relation, tail = pos_triplet
            
            # 计算正样本得分
            pos_score = self._score_triplet(head, relation, tail)
            
            # 生成负样本并计算得分
            for _ in range(neg_samples_per_pos):
                neg_triplet = self._generate_negative_sample(head, relation, tail)
                neg_score = self._score_triplet(*neg_triplet)
                
                # 计算margin loss
                loss = max(0, self.margin + pos_score - neg_score)
                total_loss += loss
                
                if loss > 0:
                    self._update_embeddings(pos_triplet, neg_triplet, learning_rate)
        
        # 重新归一化实体嵌入
        self._normalize_entity_embeddings()
        
        return total_loss / len(positive_triplets)
    
    def _update_embeddings(self, pos_triplet: Tuple[int, int, int], 
                          neg_triplet: Tuple[int, int, int], lr: float):
        """更新嵌入参数"""
        pos_h, pos_r, pos_t = pos_triplet
        neg_h, neg_r, neg_t = neg_triplet
        
        # 计算梯度
        pos_h_emb = self.entity_embeddings[pos_h]
        pos_r_emb = self.relation_embeddings[pos_r]
        pos_t_emb = self.entity_embeddings[pos_t]
        
        neg_h_emb = self.entity_embeddings[neg_h]
        neg_r_emb = self.relation_embeddings[neg_r]
        neg_t_emb = self.entity_embeddings[neg_t]
        
        # 正样本梯度
        pos_diff = pos_h_emb + pos_r_emb - pos_t_emb
        pos_norm = np.linalg.norm(pos_diff)
        if pos_norm > 1e-8:
            pos_grad = pos_diff / pos_norm
        else:
            pos_grad = np.zeros_like(pos_diff)
        
        # 负样本梯度
        neg_diff = neg_h_emb + neg_r_emb - neg_t_emb
        neg_norm = np.linalg.norm(neg_diff)
        if neg_norm > 1e-8:
            neg_grad = neg_diff / neg_norm
        else:
            neg_grad = np.zeros_like(neg_diff)
        
        # 更新参数
        self.entity_embeddings[pos_h] -= lr * pos_grad
        self.relation_embeddings[pos_r] -= lr * pos_grad
        self.entity_embeddings[pos_t] += lr * pos_grad
        
        self.entity_embeddings[neg_h] += lr * neg_grad
        self.relation_embeddings[neg_r] += lr * neg_grad
        self.entity_embeddings[neg_t] -= lr * neg_grad
    
    def train(self, triplets: List[Tuple[int, int, int]], 
              epochs: int = 100, learning_rate: float = 0.01, 
              batch_size: int = 100, early_stopping: bool = True,
              patience: int = 10):
        """训练模型"""
        logger.info(f"开始训练 [{self.data_source}]，轮数: {epochs}, 学习率: {learning_rate}")
        
        start_time = time.time()
        best_loss = float('inf')
        patience_counter = 0
        
        for epoch in tqdm(range(epochs), desc=f"Training {self.data_source}"):
            random.shuffle(triplets)
            
            total_loss = 0.0
            batch_count = 0
            
            for i in range(0, len(triplets), batch_size):
                batch = triplets[i:i + batch_size]
                loss = self.train_step(batch, learning_rate)
                total_loss += loss
                batch_count += 1
            
            avg_loss = total_loss / batch_count
            
            # 早停检查
            if avg_loss < best_loss:
                best_loss = avg_loss
                patience_counter = 0
            else:
                patience_counter += 1
            
            if (epoch + 1) % 10 == 0:
                logger.info(f"Epoch {epoch + 1}/{epochs}, Loss: {avg_loss:.4f}, Best: {best_loss:.4f}")
            
            # 早停
            if early_stopping and patience_counter >= patience:
                logger.info(f"早停触发，在第 {epoch + 1} 轮停止训练")
                break
        
        training_time = time.time() - start_time
        
        # 更新训练统计
        self.training_stats = {
            'epochs_completed': epoch + 1,
            'best_loss': best_loss,
            'training_time': training_time,
            'final_loss': avg_loss
        }
        
        logger.info(f"训练完成 [{self.data_source}]: {training_time:.2f}秒, 最佳损失: {best_loss:.4f}")
    
    def predict_links(self, test_triplets: List[Tuple[int, int, int]], 
                     k: int = 10) -> Dict[str, float]:
        """链接预测评估"""
        hits_at_k = 0
        total_triplets = len(test_triplets)
        
        for head, relation, tail in test_triplets:
            # 为这个三元组生成候选
            candidates = []
            true_score = self._score_triplet(head, relation, tail)
            
            # 生成所有可能的尾实体候选
            for candidate_tail in range(self.entity_count):
                score = self._score_triplet(head, relation, candidate_tail)
                candidates.append((score, candidate_tail))
            
            # 按得分排序（得分越低越好）
            candidates.sort(key=lambda x: x[0])
            
            # 检查真实尾实体是否在前k个候选中
            top_k_entities = [cand[1] for cand in candidates[:k]]
            if tail in top_k_entities:
                hits_at_k += 1
        
        hits_at_k_score = hits_at_k / total_triplets
        return {
            f'hits@{k}': hits_at_k_score,
            'total_tested': total_triplets
        }
    
    def save_embeddings(self, entity_names: List[str], relation_names: List[str], 
                       output_dir: Path, prefix: str = ""):
        """保存嵌入向量"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        entity_filename = f"{prefix}entity_embeddings_{self.data_source}_{timestamp}.csv"
        relation_filename = f"{prefix}relation_embeddings_{self.data_source}_{timestamp}.csv"
        
        # 保存实体嵌入
        entity_df = pd.DataFrame(
            self.entity_embeddings,
            index=entity_names,
            columns=[f"dim_{i}" for i in range(self.embedding_dim)]
        )
        entity_file = output_dir / entity_filename
        entity_df.to_csv(entity_file, encoding='utf-8')
        
        # 保存关系嵌入
        relation_df = pd.DataFrame(
            self.relation_embeddings,
            index=relation_names,
            columns=[f"dim_{i}" for i in range(self.embedding_dim)]
        )
        relation_file = output_dir / relation_filename
        relation_df.to_csv(relation_file, encoding='utf-8')
        
        # 保存模型元数据
        metadata = {
            'data_source': self.data_source,
            'entity_count': self.entity_count,
            'relation_count': self.relation_count,
            'embedding_dim': self.embedding_dim,
            'margin': self.margin,
            'training_stats': self.training_stats,
            'created_at': timestamp
        }
        
        metadata_file = output_dir / f"{prefix}model_metadata_{self.data_source}_{timestamp}.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logger.info(f"嵌入已保存 [{self.data_source}]: {entity_file}, {relation_file}")
        return entity_file, relation_file, metadata_file


class MultiSourceKGEmbedding:
    """多数据源知识图嵌入系统"""
    
    def __init__(self):
        self.processed_dir = PROCESSED_DIR
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.models = {}
        self.results = {}
    
    def detect_knowledge_graphs(self) -> Dict[str, Path]:
        """检测可用的知识图谱文件"""
        kg_files = {}
        
        # 查找PDF相关知识图谱
        pdf_kg_files = list(self.processed_dir.glob("*pdf*hg*.json")) + \
                       list(self.processed_dir.glob("entities_relations_hg.json"))
        
        if pdf_kg_files:
            kg_files['pdf'] = pdf_kg_files[0]
        
        # 查找数据库相关知识图谱
        db_kg_files = list(self.processed_dir.glob("*hg_db*.json")) + \
                      list(self.processed_dir.glob("*db_hg*.json"))
        
        if db_kg_files:
            kg_files['database'] = db_kg_files[0]
        
        # 查找通用知识图谱
        general_kg_files = list(self.processed_dir.glob("*hg*.json"))
        for f in general_kg_files:
            if 'db' not in f.name.lower() and 'pdf' not in f.name.lower():
                kg_files['general'] = f
                break
        
        logger.info(f"检测到知识图谱文件: {list(kg_files.keys())}")
        return kg_files
    
    def load_knowledge_graph(self, kg_file: Path) -> Dict:
        """加载知识图谱"""
        with open(kg_file, 'r', encoding='utf-8') as f:
            kg_data = json.load(f)
        
        logger.info(f"知识图谱已加载: {kg_file}")
        return kg_data
    
    def prepare_training_data(self, kg_data: Dict, data_source: str) -> Tuple[List[Tuple[int, int, int]], 
                                                                            List[str], List[str]]:
        """准备训练数据"""
        nodes = kg_data.get("nodes", {})
        edges = kg_data.get("edges", [])
        
        # 创建实体和关系映射
        entities = list(nodes.keys())
        relations = []
        
        # 提取关系
        for edge in edges:
            if isinstance(edge, list) and len(edge) >= 3:
                relation = edge[1]
                if relation not in relations:
                    relations.append(relation)
            elif isinstance(edge, dict):
                relation = edge.get('relation', edge.get('type', 'unknown'))
                if relation not in relations:
                    relations.append(relation)
        
        entity2id = {entity: i for i, entity in enumerate(entities)}
        relation2id = {relation: i for i, relation in enumerate(relations)}
        
        # 创建三元组
        triplets = []
        for edge in edges:
            try:
                if isinstance(edge, list) and len(edge) >= 3:
                    head, relation, tail = edge[0], edge[1], edge[2]
                elif isinstance(edge, dict):
                    head = edge.get('source', edge.get('head'))
                    tail = edge.get('target', edge.get('tail'))
                    relation = edge.get('relation', edge.get('type', 'unknown'))
                else:
                    continue
                
                if head in entity2id and tail in entity2id and relation in relation2id:
                    triplets.append((
                        entity2id[head],
                        relation2id[relation],
                        entity2id[tail]
                    ))
            except Exception as e:
                logger.warning(f"跳过无效边: {edge}, 错误: {e}")
                continue
        
        logger.info(f"训练数据准备完成 [{data_source}]:")
        logger.info(f"  实体数: {len(entities)}")
        logger.info(f"  关系数: {len(relations)}")
        logger.info(f"  三元组数: {len(triplets)}")
        
        return triplets, entities, relations
    
    def train_source_embedding(self, data_source: str, kg_file: Path,
                              embedding_dim: int = 64, epochs: int = 100) -> Dict:
        """为特定数据源训练嵌入"""
        logger.info(f"开始为 {data_source} 训练嵌入...")
        
        try:
            # 加载数据
            kg_data = self.load_knowledge_graph(kg_file)
            triplets, entities, relations = self.prepare_training_data(kg_data, data_source)
            
            if not triplets:
                logger.warning(f"数据源 {data_source} 没有有效的三元组")
                return {'success': False, 'error': 'No valid triplets'}
            
            # 创建并训练模型
            model = EnhancedTransE(
                entity_count=len(entities),
                relation_count=len(relations),
                embedding_dim=embedding_dim,
                data_source=data_source
            )
            
            # 分割训练和测试数据
            random.shuffle(triplets)
            split_idx = int(0.8 * len(triplets))
            train_triplets = triplets[:split_idx]
            test_triplets = triplets[split_idx:]
            
            # 训练模型
            model.train(train_triplets, epochs=epochs)
            
            # 评估模型
            evaluation = {}
            if test_triplets:
                evaluation = model.predict_links(test_triplets, k=10)
            
            # 保存嵌入
            entity_file, relation_file, metadata_file = model.save_embeddings(
                entities, relations, self.processed_dir
            )
            
            # 存储结果
            result = {
                'success': True,
                'data_source': data_source,
                'entity_file': str(entity_file),
                'relation_file': str(relation_file),
                'metadata_file': str(metadata_file),
                'entity_count': len(entities),
                'relation_count': len(relations),
                'triplet_count': len(triplets),
                'training_stats': model.training_stats,
                'evaluation': evaluation
            }
            
            self.models[data_source] = model
            self.results[data_source] = result
            
            logger.info(f"✅ {data_source} 嵌入训练完成")
            return result
            
        except Exception as e:
            logger.error(f"❌ {data_source} 嵌入训练失败: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                'success': False,
                'data_source': data_source,
                'error': str(e)
            }
    
    def run_multi_source_training(self, embedding_dim: int = 64, epochs: int = 50):
        """运行多数据源嵌入训练"""
        logger.info("开始多数据源知识图嵌入训练")
        
        # 检测知识图谱文件
        kg_files = self.detect_knowledge_graphs()
        
        if not kg_files:
            logger.warning("未找到知识图谱文件")
            return {'success': False, 'error': 'No knowledge graph files found'}
        
        results = {}
        
        # 为每个数据源训练嵌入
        for data_source, kg_file in kg_files.items():
            logger.info(f"\n{'='*60}")
            logger.info(f"处理数据源: {data_source}")
            logger.info(f"{'='*60}")
            
            result = self.train_source_embedding(
                data_source, kg_file, embedding_dim, epochs
            )
            results[data_source] = result
        
        # 生成总结报告
        self.generate_summary_report(results)
        
        return {
            'success': True,
            'results': results,
            'total_sources': len(results)
        }
    
    def generate_summary_report(self, results: Dict):
        """生成总结报告"""
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'total_sources': len(results),
            'results': results,
            'summary': {
                'successful': sum(1 for r in results.values() if r.get('success', False)),
                'failed': sum(1 for r in results.values() if not r.get('success', False)),
                'total_entities': sum(r.get('entity_count', 0) for r in results.values() if r.get('success', False)),
                'total_relations': sum(r.get('relation_count', 0) for r in results.values() if r.get('success', False)),
                'total_triplets': sum(r.get('triplet_count', 0) for r in results.values() if r.get('success', False))
            }
        }
        
        # 保存报告
        report_file = self.processed_dir / f"kg_embedding_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        # 打印总结
        print("\n" + "="*80)
        print(" 多数据源知识图嵌入训练完成")
        print("="*80)
        
        for data_source, result in results.items():
            status = "✅ 成功" if result.get('success', False) else "❌ 失败"
            print(f"{data_source:15s}: {status}")
            
            if result.get('success', False):
                print(f"  - 实体数量: {result.get('entity_count', 0)}")
                print(f"  - 关系数量: {result.get('relation_count', 0)}")
                print(f"  - 三元组数量: {result.get('triplet_count', 0)}")
                
                training_stats = result.get('training_stats', {})
                if training_stats:
                    print(f"  - 训练轮数: {training_stats.get('epochs_completed', 0)}")
                    print(f"  - 最终损失: {training_stats.get('final_loss', 0):.4f}")
                    print(f"  - 训练时间: {training_stats.get('training_time', 0):.2f}秒")
                
                evaluation = result.get('evaluation', {})
                if evaluation:
                    print(f"  - Hits@10: {evaluation.get('hits@10', 0):.4f}")
            else:
                print(f"  - 错误: {result.get('error', 'Unknown error')}")
        
        print(f"\n总计:")
        print(f"  - 处理数据源: {report_data['total_sources']}")
        print(f"  - 成功: {report_data['summary']['successful']}")
        print(f"  - 失败: {report_data['summary']['failed']}")
        print(f"  - 总实体数: {report_data['summary']['total_entities']}")
        print(f"  - 总关系数: {report_data['summary']['total_relations']}")
        print(f"  - 总三元组数: {report_data['summary']['total_triplets']}")
        
        print(f"\n📊 详细报告已保存: {report_file}")
        print("="*80)
        
        logger.info(f"总结报告已保存: {report_file}")


def main():
    """主函数"""
    print("增强版多数据源知识图嵌入系统")
    print("="*80)
    print("支持PDF和数据库数据源的独立嵌入训练")
    print("="*80)
    
    # 创建多数据源嵌入系统
    multi_kg_embedding = MultiSourceKGEmbedding()
    
    # 运行多数据源训练
    result = multi_kg_embedding.run_multi_source_training(
        embedding_dim=64,  # 可以调整嵌入维度
        epochs=50          # 可以调整训练轮数
    )
    
    if result['success']:
        print(f"\n🎉 多数据源嵌入训练成功完成!")
        print(f"📊 处理了 {result['total_sources']} 个数据源")
    else:
        print(f"\n❌ 训练失败: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()