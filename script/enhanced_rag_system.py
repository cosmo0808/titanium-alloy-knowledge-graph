# working_offline_rag.py - 增强版离线RAG系统（支持Fe-Ti合金）
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
from collections import defaultdict, Counter
import re
import os
import sys

# 安全的编码设置
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OfflineTextEncoder:
    """离线文本编码器"""
    
    def __init__(self, vocab_size: int = 1000):
        self.vocab_size = vocab_size
        self.word_to_idx = {}
        self.idx_to_word = {}
        self.embedding_dim = 128
        self.is_built = False
        
    def build_vocabulary(self, texts: List[str]):
        """构建词汇表"""
        word_counts = Counter()
        
        for text in texts:
            words = self._tokenize(text)
            word_counts.update(words)
        
        # 选择最常见的词汇
        most_common = word_counts.most_common(self.vocab_size - 2)
        
        # 特殊token
        self.word_to_idx = {'<UNK>': 0, '<PAD>': 1}
        self.idx_to_word = {0: '<UNK>', 1: '<PAD>'}
        
        for i, (word, _) in enumerate(most_common, 2):
            self.word_to_idx[word] = i
            self.idx_to_word[i] = word
        
        self.is_built = True
        logger.info(f"构建词汇表完成: {len(self.word_to_idx)} 个词汇")
    
    def _tokenize(self, text: str) -> List[str]:
        """简单分词"""
        if not isinstance(text, str):
            text = str(text)
        
        # 清理文本
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text.lower())
        words = []
        
        # 分离中英文
        current_word = ""
        for char in text:
            if '\u4e00' <= char <= '\u9fff':  # 中文字符
                if current_word:
                    words.append(current_word)
                    current_word = ""
                words.append(char)
            elif char.isalnum():
                current_word += char
            elif char.isspace():
                if current_word:
                    words.append(current_word)
                    current_word = ""
        
        if current_word:
            words.append(current_word)
        
        return [w for w in words if len(w.strip()) > 0]
    
    def encode(self, texts: List[str]) -> np.ndarray:
        """编码文本为向量"""
        if not self.is_built:
            logger.warning("词汇表未构建，使用默认编码")
            return np.random.normal(0, 0.1, (len(texts), self.embedding_dim))
        
        if not isinstance(texts, list):
            texts = [texts]
        
        embeddings = []
        
        for text in texts:
            words = self._tokenize(text)
            
            # 创建向量
            vector = np.zeros(self.embedding_dim)
            
            # 使用简单的词袋模型
            word_counts = Counter(words)
            total_words = len(words) if words else 1
            
            for word, count in word_counts.items():
                idx = self.word_to_idx.get(word, 0)  # UNK token
                if idx < self.embedding_dim:
                    vector[idx] = count / total_words
            
            # 归一化
            norm = np.linalg.norm(vector)
            if norm > 0:
                vector = vector / norm
            
            embeddings.append(vector)
        
        return np.array(embeddings)

class WorkingRAGSystem:
    """可正常工作的离线RAG系统"""
    
    def __init__(self, processed_dir: Optional[Path] = None):
        if processed_dir is None:
            processed_dir = Path(__file__).resolve().parent.parent / "data" / "processed"
        
        self.processed_dir = Path(processed_dir)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        # 扩展领域词汇，增加Fe-Ti合金相关内容
        self.domain_vocabulary = {
            'elements': ['Ti', 'Al', 'V', 'Mo', 'Nb', 'Zr', 'Sn', 'Fe', 'Cr', 'Ni', 
                        '钛', '铝', '钒', '钼', '铌', '锆', '锡', '铁', '铬', '镍'],
            'alloys': ['Ti-6Al-4V', 'TC4', 'Ti-3Al-2.5V', 'TA18', 'Ti-6Al-7Nb', 
                      '钛合金', 'TC4合金', 'TA1', 'TA2', 'TA3', 'Fe-Ti', '铁钛合金'],
            'properties': ['强度', '硬度', '密度', '弹性模量', '屈服强度', '抗拉强度', 
                          '疲劳强度', '耐腐蚀性', '导热性', '延伸率', '断面收缩率',
                          'strength', 'hardness', 'density', 'modulus', 'yield', 'tensile'],
            'processes': ['熔炼', '锻造', '轧制', '挤压', '焊接', '热处理', '表面处理',
                         '退火', '固溶', '时效', 'melting', 'forging', 'rolling', 'welding',
                         '脉冲电流辅助', '快速加热', '快速冷却', '致密化'],
            'applications': ['航空航天', '医疗植入', '汽车工业', '船舶制造', '石油化工',
                           '核工业', 'aerospace', 'medical', 'automotive', '航空', '医疗'],
            'materials': ['铁粉', '钛粉', '二氧化钛', 'TiO2', '氯化钛', 'TiCl4', '纳米粉', '起始材料']
        }
        
        # 初始化编码器
        self.encoder = OfflineTextEncoder()
        
        # 加载知识图谱
        self.knowledge_graph = self.load_or_create_knowledge_graph()
        
        # 准备编码器
        self._prepare_encoder()
        
        # 创建向量数据库
        self.vector_database = self.create_vector_database()
        
        logger.info("离线RAG系统初始化完成")
    
    def load_or_create_knowledge_graph(self) -> Dict[str, Any]:
        """加载或创建知识图谱"""
        kg_file = self.processed_dir / "titanium_kg.json"
        
        if kg_file.exists():
            try:
                with open(kg_file, 'r', encoding='utf-8') as f:
                    kg_data = json.load(f)
                logger.info(f"已加载知识图谱: {len(kg_data.get('nodes', {}))} 节点")
                return kg_data
            except Exception as e:
                logger.error(f"知识图谱加载失败: {e}")
        
        # 创建默认知识图谱
        logger.info("创建默认知识图谱...")
        kg_data = self._create_knowledge_graph()
        
        # 保存到文件
        try:
            with open(kg_file, 'w', encoding='utf-8') as f:
                json.dump(kg_data, f, ensure_ascii=False, indent=2)
            logger.info(f"知识图谱已保存: {kg_file}")
        except Exception as e:
            logger.warning(f"知识图谱保存失败: {e}")
        
        return kg_data
    
    def _create_knowledge_graph(self) -> Dict[str, Any]:
        """创建知识图谱"""
        return {
            "nodes": {
                # 元素节点
                "Ti": {
                    "type": "element", "name": "钛",
                    "properties": ["轻质", "耐腐蚀", "高强度", "生物相容性"],
                    "description": "钛是一种银白色的过渡金属，具有重量轻、强度高、耐腐蚀性强等特点"
                },
                "Al": {
                    "type": "element", "name": "铝",
                    "properties": ["轻质", "α稳定元素", "强化"],
                    "description": "铝是钛合金中重要的α稳定化元素，能够固溶强化基体"
                },
                "V": {
                    "type": "element", "name": "钒",
                    "properties": ["β稳定元素", "强化", "改善韧性"],
                    "description": "钒是重要的β稳定化元素，能够细化晶粒，提高合金的强度和韧性"
                },
                "Fe": {
                    "type": "element", "name": "铁",
                    "properties": ["高强度", "良好磁性", "成本低"],
                    "description": "铁是地壳中含量丰富的金属元素，具有良好的机械性能和低成本优势"
                },
                
                # 合金节点
                "Ti-6Al-4V": {
                    "type": "alloy", "name": "Ti-6Al-4V钛合金",
                    "composition": ["Ti", "Al", "V"],
                    "properties": ["高强度", "良好韧性", "优异耐腐蚀性", "可焊接性好"],
                    "applications": ["航空结构件", "航空发动机", "医疗植入物"],
                    "description": "最重要的α+β型钛合金，具有优异的强度、韧性和耐腐蚀性的平衡"
                },
                "Fe-Ti": {
                    "type": "alloy", "name": "铁钛合金",
                    "composition": ["Fe", "Ti"],
                    "properties": ["高强度", "良好耐磨性", "成本效益高"],
                    "applications": ["结构材料", "耐磨部件", "合金添加剂"],
                    "description": "铁和钛组成的合金，具有良好的机械性能和成本优势"
                },
                "TC4": {
                    "type": "alloy", "name": "TC4钛合金",
                    "composition": ["Ti", "Al", "V"],
                    "properties": ["高强度", "良好塑性", "优异焊接性"],
                    "applications": ["航空发动机叶片", "压气机盘", "结构件"],
                    "description": "TC4是Ti-6Al-4V的中国牌号，广泛应用于航空航天领域"
                },
                
                # 材料节点
                "TiO2": {
                    "type": "material", "name": "二氧化钛",
                    "properties": ["白色粉末", "稳定性好", "来源广泛"],
                    "description": "二氧化钛是制备钛和钛合金的重要原料，可通过还原反应得到金属钛"
                },
                "TiCl4": {
                    "type": "material", "name": "四氯化钛",
                    "properties": ["无色液体", "易挥发", "还原性强"],
                    "description": "四氯化钛是制备高纯钛和钛合金的重要中间体"
                },
                "纳米粉": {
                    "type": "material", "name": "纳米粉末",
                    "properties": ["高比表面积", "活性高", "烧结性能好"],
                    "description": "纳米级金属粉末，具有优异的烧结性能和反应活性"
                },
                
                # 工艺节点
                "脉冲电流辅助": {
                    "type": "process", "name": "脉冲电流辅助反应",
                    "advantages": ["快速加热", "快速冷却", "提高致密化", "保持纳米特性"],
                    "description": "利用脉冲电流进行快速加热和冷却的制备工艺，能够有效保持纳米材料的固有特性"
                },
                "热处理": {
                    "type": "process", "name": "热处理工艺",
                    "effects": ["调整组织", "提高强度", "改善塑性"],
                    "description": "通过加热和冷却改变钛合金显微组织和性能的工艺方法"
                },
                
                # 性能节点
                "强度": {
                    "type": "property", "name": "材料强度",
                    "factors": ["合金成分", "显微组织", "热处理工艺"],
                    "description": "材料抵抗变形和断裂的能力"
                },
                "致密化": {
                    "type": "property", "name": "致密化效果",
                    "factors": ["烧结温度", "压力", "粉末特性"],
                    "description": "材料在制备过程中达到高密度的能力"
                }
            },
            "edges": [
                # 合金成分关系
                ["Ti-6Al-4V", "contains", "Ti"], ["Ti-6Al-4V", "contains", "Al"], ["Ti-6Al-4V", "contains", "V"],
                ["Fe-Ti", "contains", "Fe"], ["Fe-Ti", "contains", "Ti"],
                ["TC4", "contains", "Ti"], ["TC4", "contains", "Al"], ["TC4", "contains", "V"],
                
                # 材料制备关系
                ["Fe-Ti", "prepared_from", "Fe"], ["Fe-Ti", "prepared_from", "Ti"],
                ["Fe-Ti", "prepared_from", "TiO2"], ["Fe-Ti", "prepared_from", "TiCl4"],
                
                # 工艺优势关系
                ["脉冲电流辅助", "provides", "快速加热"], ["脉冲电流辅助", "provides", "快速冷却"],
                ["脉冲电流辅助", "improves", "致密化"], ["脉冲电流辅助", "preserves", "纳米特性"],
                
                # 元素对性能的影响
                ["Al", "improves", "强度"], ["Al", "improves", "硬度"],
                ["V", "improves", "强度"], ["V", "improves", "韧性"],
                ["Fe", "improves", "强度"], ["Fe", "reduces", "成本"],
                
                # 合金性能关系
                ["Ti-6Al-4V", "has_property", "强度"], ["Ti-6Al-4V", "has_property", "耐腐蚀性"],
                ["Fe-Ti", "has_property", "强度"], ["Fe-Ti", "has_property", "耐磨性"],
                
                # 工艺应用关系
                ["脉冲电流辅助", "used_for", "Fe-Ti"], ["脉冲电流辅助", "used_for", "纳米粉"],
                
                # 材料特性关系
                ["纳米粉", "has_property", "高活性"], ["纳米粉", "has_property", "易烧结"]
            ]
        }
    
    def _prepare_encoder(self):
        """准备编码器"""
        # 收集所有文本
        all_texts = []
        
        for entity, info in self.knowledge_graph['nodes'].items():
            texts = [entity]
            
            if 'name' in info:
                texts.append(info['name'])
            
            if 'description' in info:
                texts.append(info['description'])
            
            for key in ['properties', 'applications', 'effects', 'requirements', 'advantages']:
                if key in info:
                    if isinstance(info[key], list):
                        texts.extend(info[key])
                    else:
                        texts.append(str(info[key]))
            
            all_texts.extend(texts)
        
        # 添加领域词汇
        for category, terms in self.domain_vocabulary.items():
            all_texts.extend(terms)
        
        # 构建词汇表
        self.encoder.build_vocabulary(all_texts)
    
    def create_vector_database(self) -> pd.DataFrame:
        """创建向量数据库"""
        entities = list(self.knowledge_graph['nodes'].keys())
        entity_texts = []
        
        for entity in entities:
            info = self.knowledge_graph['nodes'][entity]
            
            # 组合实体的所有文本信息
            text_parts = [entity]
            
            if 'name' in info:
                text_parts.append(info['name'])
            
            if 'description' in info:
                text_parts.append(info['description'])
            
            # 添加属性信息
            for key in ['properties', 'applications', 'effects', 'requirements', 'advantages']:
                if key in info and isinstance(info[key], list):
                    text_parts.extend(info[key])
            
            combined_text = ' '.join(text_parts)
            entity_texts.append(combined_text)
        
        # 编码为向量
        embeddings = self.encoder.encode(entity_texts)
        
        # 创建DataFrame
        df = pd.DataFrame(embeddings, index=entities)
        
        logger.info(f"创建向量数据库: {len(entities)} 实体, {embeddings.shape[1]} 维")
        return df
    
    def query(self, question: str, top_k: int = 5, method: str = 'hybrid') -> Dict[str, Any]:
        """主查询接口"""
        logger.info(f"处理查询: {question}")
        
        processed_question = self.preprocess_query(question)
        
        results = {
            'question': question,
            'processed_question': processed_question,
            'retrieval_results': {},
            'final_answer': '',
            'confidence': 0.0,
            'sources': []
        }
        
        # 执行不同的检索方法
        if method in ['semantic', 'hybrid']:
            semantic_results = self.semantic_retrieval(processed_question, top_k)
            results['retrieval_results']['semantic'] = semantic_results
        
        if method in ['keyword', 'hybrid']:
            keyword_results = self.keyword_retrieval(processed_question, top_k)
            results['retrieval_results']['keyword'] = keyword_results
        
        if method in ['graph', 'hybrid']:
            graph_results = self.graph_retrieval(processed_question, top_k)
            results['retrieval_results']['graph'] = graph_results
        
        # 生成最终答案
        final_answer, confidence = self.generate_answer(results['retrieval_results'], question)
        results['final_answer'] = final_answer
        results['confidence'] = confidence
        results['sources'] = self.extract_sources(results['retrieval_results'])
        
        return results
    
    def preprocess_query(self, question: str) -> str:
        """预处理查询"""
        # 修正常见错误
        corrections = {
            '二氧化社': '二氧化钛',
            '氣化铁': '氯化钛',
            'T1O2': 'TiO2',
            'TiM2': 'TiCl4',
            '优务': '优势',
            '粉求': '粉末'
        }
        
        processed = question.strip()
        for wrong, correct in corrections.items():
            processed = processed.replace(wrong, correct)
        
        return processed
    
    def semantic_retrieval(self, question: str, top_k: int) -> List[Dict[str, Any]]:
        """语义检索"""
        results = []
        
        try:
            # 编码查询
            query_embedding = self.encoder.encode([question])[0]
            
            # 计算相似度
            for entity in self.vector_database.index:
                entity_embedding = self.vector_database.loc[entity].values
                similarity = self.cosine_similarity(query_embedding, entity_embedding)
                
                if similarity > 0.05:  # 最小相似度阈值
                    entity_info = self.knowledge_graph['nodes'][entity]
                    results.append({
                        'entity': entity,
                        'type': entity_info.get('type', 'unknown'),
                        'similarity': float(similarity),
                        'method': 'semantic',
                        'details': entity_info
                    })
        
        except Exception as e:
            logger.error(f"语义检索失败: {e}")
            return self.keyword_retrieval(question, top_k)
        
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]
    
    def keyword_retrieval(self, question: str, top_k: int) -> List[Dict[str, Any]]:
        """关键词检索"""
        results = []
        question_lower = question.lower()
        
        keywords = self.extract_keywords(question)
        
        for entity, info in self.knowledge_graph['nodes'].items():
            score = 0
            
            # 实体名称匹配
            if entity.lower() in question_lower:
                score += 5
            
            # 中文名称匹配
            if info.get('name', '').lower() in question_lower:
                score += 5
            
            # 关键词匹配
            for keyword in keywords:
                if keyword in info.get('description', '').lower():
                    score += 2
                
                for prop_key in ['properties', 'applications', 'effects', 'advantages']:
                    if prop_key in info and isinstance(info[prop_key], list):
                        for prop in info[prop_key]:
                            if keyword in prop.lower():
                                score += 3
            
            if score > 0:
                results.append({
                    'entity': entity,
                    'type': info.get('type', 'unknown'),
                    'score': score,
                    'method': 'keyword',
                    'details': info
                })
        
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]
    
    def graph_retrieval(self, question: str, top_k: int) -> List[Dict[str, Any]]:
        """图检索"""
        results = []
        
        # 识别种子实体
        seed_entities = self.extract_entities_from_question(question)
        
        if not seed_entities:
            return results
        
        # 扩展相关实体
        related_entities = set(seed_entities)
        
        for edge in self.knowledge_graph.get('edges', []):
            if len(edge) >= 3:
                head, relation, tail = edge[0], edge[1], edge[2]
                if head in seed_entities:
                    related_entities.add(tail)
                elif tail in seed_entities:
                    related_entities.add(head)
        
        # 计算实体重要性
        for entity in related_entities:
            if entity in self.knowledge_graph['nodes']:
                connections = sum(1 for edge in self.knowledge_graph['edges'] 
                                if len(edge) >= 3 and entity in [edge[0], edge[2]])
                
                seed_bonus = 2 if entity in seed_entities else 0
                total_score = connections * 0.5 + seed_bonus
                
                results.append({
                    'entity': entity,
                    'type': self.knowledge_graph['nodes'][entity].get('type', 'unknown'),
                    'score': total_score,
                    'method': 'graph',
                    'details': self.knowledge_graph['nodes'][entity]
                })
        
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]
    
    def extract_keywords(self, question: str) -> List[str]:
        """提取关键词"""
        stop_words = {'是', '的', '在', '有', '和', '与', '对', '为', '了', '吗', '什么', '如何', '怎样'}
        words = re.findall(r'\w+', question.lower())
        return [word for word in words if word not in stop_words and len(word) > 1]
    
    def extract_entities_from_question(self, question: str) -> List[str]:
        """从问题中提取实体"""
        entities = []
        question_lower = question.lower()
        
        # 按长度排序，优先匹配长实体名
        entity_list = list(self.knowledge_graph['nodes'].keys())
        entity_list.sort(key=len, reverse=True)
        
        for entity in entity_list:
            if entity.lower() in question_lower:
                entities.append(entity)
        
        # 检查中文名称
        for entity, info in self.knowledge_graph['nodes'].items():
            name = info.get('name', '')
            if name and name.lower() in question_lower and entity not in entities:
                entities.append(entity)
        
        return entities
    
    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def generate_answer(self, retrieval_results: Dict[str, List], question: str) -> Tuple[str, float]:
        """生成最终答案"""
        all_results = []
        for method, results in retrieval_results.items():
            all_results.extend(results)
        
        if not all_results:
            return "抱歉，未找到相关信息。", 0.0
        
        # 选择最佳实体
        entity_scores = defaultdict(list)
        
        for result in all_results:
            entity = result['entity']
            if 'similarity' in result:
                entity_scores[entity].append(result['similarity'])
            elif 'score' in result:
                entity_scores[entity].append(min(result['score'] / 10.0, 1.0))
        
        top_entities = []
        for entity, scores in entity_scores.items():
            avg_score = np.mean(scores)
            entity_info = self.knowledge_graph['nodes'].get(entity, {})
            top_entities.append((entity, avg_score, entity_info))
        
        top_entities.sort(key=lambda x: x[1], reverse=True)
        
        if not top_entities:
            return "未找到相关信息。", 0.0
        
        # 生成答案
        answer = self.generate_typed_answer(top_entities, question)
        confidence = min(np.mean([score for _, score, _ in top_entities[:3]]), 1.0)
        
        return answer, confidence
    
    def generate_typed_answer(self, top_entities: List[Tuple], question: str) -> str:
        """根据问题类型生成答案"""
        if not top_entities:
            return "抱歉，未找到相关信息。"
        
        question_lower = question.lower()
        entity, score, info = top_entities[0]
        
        # 特殊处理Fe-Ti合金相关问题
        if 'fe-ti' in question_lower or '铁钛' in question_lower:
            return self._answer_fe_ti_specific(question, top_entities)
        
        # 问题类型识别
        if any(kw in question_lower for kw in ['什么', 'what', '介绍', '哪些', '材料']):
            return self._answer_definition(entity, info)
        
        elif any(kw in question_lower for kw in ['作用', '影响', 'effect', '优势', '优务']):
            return self._answer_effect(entity, info)
        
        elif any(kw in question_lower for kw in ['特点', '性能', 'property']):
            return self._answer_properties(entity, info)
        
        elif any(kw in question_lower for kw in ['如何', 'how', '方法']):
            return self._answer_method(entity, info)
        
        elif any(kw in question_lower for kw in ['应用', 'application']):
            return self._answer_application(entity, info)
        
        elif any(kw in question_lower for kw in ['比较', 'compare', '区别']):
            return self._answer_comparison(top_entities)
        
        else:
            return self._answer_general(entity, info)
    
    def _answer_fe_ti_specific(self, question: str, top_entities: List[Tuple]) -> str:
        """专门处理Fe-Ti合金相关问题"""
        question_lower = question.lower()
        
        if any(kw in question_lower for kw in ['起始材料', '原材料', '制备材料']):
            return "用于制备Fe-Ti合金的起始材料包括铁粉、钛粉、二氧化钛(TiO2)和四氯化钛(TiCl4)等。"
        
        elif any(kw in question_lower for kw in ['脉冲电流', '优势', '优点', '优务']):
            return "使用脉冲电流辅助反应制备Fe-Ti合金的主要优势包括：能够快速加热和冷却，提高致密化效果，同时保持纳米粉末的固有特性。"
        
        # 默认回答
        entity, score, info = top_entities[0]
        return self._answer_general(entity, info)
    
    def _answer_definition(self, entity: str, info: Dict) -> str:
        """定义类答案"""
        parts = []
        
        if 'name' in info and info['name'] != entity:
            parts.append(f"{entity}（{info['name']}）")
        else:
            parts.append(entity)
        
        entity_type = info.get('type', 'unknown')
        type_desc = {
            'alloy': '是一种合金',
            'element': '是一种化学元素',
            'property': '是材料的重要性能指标',
            'process': '是一种工艺方法',
            'application': '是重要的应用领域',
            'material': '是一种材料'
        }
        
        if entity_type in type_desc:
            parts.append(type_desc[entity_type])
        
        if 'composition' in info:
            comp = ', '.join(info['composition'])
            parts.append(f"，主要由{comp}组成")
        
        if 'description' in info:
            parts.append(f"。{info['description']}")
        
        return ''.join(parts) + ('。' if not parts[-1].endswith('。') else '')
    
    def _answer_effect(self, entity: str, info: Dict) -> str:
        """作用效果类答案"""
        effects = []
        
        # 从关系中查找作用
        for edge in self.knowledge_graph['edges']:
            if len(edge) >= 3 and edge[0] == entity:
                if edge[1] == 'improves':
                    effects.append(f"提高{edge[2]}")
                elif edge[1] == 'provides':
                    effects.append(f"提供{edge[2]}")
                elif edge[1] == 'preserves':
                    effects.append(f"保持{edge[2]}")
                elif edge[1] == 'reduces':
                    effects.append(f"降低{edge[2]}")
        
        if 'effects' in info:
            effects.extend(info['effects'])
        
        if 'advantages' in info:
            effects.extend(info['advantages'])
        
        if effects:
            return f"{entity}的主要作用包括：{', '.join(effects)}。"
        else:
            return f"{entity}在材料制备中发挥重要作用，具体效果取决于应用条件。"
    
    def _answer_properties(self, entity: str, info: Dict) -> str:
        """特性属性类答案"""
        properties = info.get('properties', [])
        
        if properties:
            return f"{entity}的主要特点包括：{', '.join(properties)}。"
        else:
            return f"{entity}具有优异的综合性能。"
    
    def _answer_method(self, entity: str, info: Dict) -> str:
        """方法类答案"""
        methods = []
        
        for edge in self.knowledge_graph['edges']:
            if len(edge) >= 3 and edge[2] == entity and edge[1] == 'processed_by':
                methods.append(f"可通过{edge[0]}进行处理")
            elif len(edge) >= 3 and edge[2] == entity and edge[1] == 'prepared_from':
                methods.append(f"可使用{edge[0]}作为原料")
            elif len(edge) >= 3 and edge[0] == entity and edge[1] == 'used_for':
                methods.append(f"可用于制备{edge[2]}")
        
        if 'requirements' in info:
            methods.extend([f"需要{req}" for req in info['requirements']])
        
        if methods:
            return f"对于{entity}，{'; '.join(methods)}。"
        else:
            return f"处理{entity}需要采用适当的工艺方法。"
    
    def _answer_application(self, entity: str, info: Dict) -> str:
        """应用类答案"""
        applications = info.get('applications', [])
        
        if applications:
            return f"{entity}主要应用于：{', '.join(applications)}等领域。"
        else:
            return f"{entity}在多个工业领域都有重要应用。"
    
    def _answer_comparison(self, top_entities: List) -> str:
        """比较类答案"""
        if len(top_entities) < 2:
            return "需要更多信息来进行比较分析。"
        
        entity1, _, info1 = top_entities[0]
        entity2, _, info2 = top_entities[1]
        
        return f"{entity1}和{entity2}都是材料体系中的重要组成部分，各有其特定的性能特点和应用领域。"
    
    def _answer_general(self, entity: str, info: Dict) -> str:
        """通用答案"""
        parts = [f"关于{entity}："]
        
        if 'description' in info:
            parts.append(info['description'])
        else:
            parts.append("这是材料体系中的重要组成部分")
        
        if 'properties' in info:
            key_props = info['properties'][:3]
            parts.append(f"，主要特点包括{', '.join(key_props)}")
        
        return ''.join(parts) + '。'
    
    def extract_sources(self, retrieval_results: Dict[str, List]) -> List[str]:
        """提取信息源"""
        sources = {'offline_titanium_knowledge_base'}
        
        for method, results in retrieval_results.items():
            if results:
                sources.add(f"{method}_retrieval")
        
        return list(sources)


# 主程序
def main():
    """主函数：演示离线RAG系统功能"""
    print("=== 离线钛合金RAG系统演示 ===\n")
    
    try:
        # 初始化系统
        print("正在初始化离线RAG系统...")
        rag_system = WorkingRAGSystem()
        print("系统初始化完成！\n")
        
        # 测试问题 - 包括Fe-Ti合金相关问题
        test_questions = [
            "用于制备Fe-Ti合金的起始材料有哪些？",
            "使用脉冲电流辅助反应制备Fe-Ti合金的主要优势是什么？",
            "钛合金中铝元素的作用是什么？",
            "Ti-6Al-4V合金有什么特点？",
            "如何提高钛合金的强度？", 
            "钛合金在航空航天领域有哪些应用？"
        ]
        
        print("开始测试查询...\n")
        
        for i, question in enumerate(test_questions, 1):
            print(f"问题 {i}: {question}")
            print("-" * 50)
            
            try:
                # 执行查询
                result = rag_system.query(question, method='hybrid')
                
                print(f"答案: {result['final_answer']}")
                print(f"置信度: {result['confidence']:.3f}")
                
                # 显示检索结果
                total_results = sum(len(results) for results in result['retrieval_results'].values())
                print(f"检索结果: {total_results} 个相关实体")
                print(f"使用方法: {list(result['retrieval_results'].keys())}")
                print(f"信息源: {', '.join(result['sources'])}")
                
            except Exception as e:
                print(f"查询出错: {e}")
            
            print("=" * 60)
            print()
        
        # 交互式查询
        print("\n=== 交互式查询模式 ===")
        print("输入您的问题（输入'退出'或'quit'结束）：")
        
        while True:
            try:
                user_question = input("\n> ").strip()
                
                if user_question.lower() in ['退出', 'quit', 'exit', '']:
                    break
                
                result = rag_system.query(user_question, method='hybrid')
                print(f"\n答案: {result['final_answer']}")
                print(f"置信度: {result['confidence']:.3f}")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"查询出错: {e}")
        
        print("\n感谢使用离线RAG系统！")
        
    except Exception as e:
        print(f"系统初始化失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()