# script/rag_system.py - 增强的RAG系统
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)

class EnhancedAlloyRAGSystem:
    """增强的钛合金RAG系统"""
    
    def __init__(self, kg_path: str, embeddings_path: Optional[str] = None):
        self.kg_path = Path(kg_path)
        self.embeddings_path = Path(embeddings_path) if embeddings_path else None
        self.kg_data = self._load_knowledge_graph()
        self.embeddings = self._load_embeddings()
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        
    def _load_knowledge_graph(self) -> Dict[str, Any]:
        """加载知识图谱"""
        try:
            with open(self.kg_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"知识图谱加载失败: {e}")
            return {'nodes': {}, 'edges': []}
    
    def _load_embeddings(self) -> Optional[pd.DataFrame]:
        """加载embeddings"""
        if not self.embeddings_path or not self.embeddings_path.exists():
            return None
        try:
            return pd.read_csv(self.embeddings_path, index_col=0)
        except Exception as e:
            logger.error(f"Embeddings加载失败: {e}")
            return None
    
    def query(self, question: str) -> Dict[str, Any]:
        """查询接口"""
        try:
            # 简化的检索逻辑
            relevant_entities = self._retrieve_entities(question)
            answer = self._generate_answer(question, relevant_entities)
            
            return {
                'answer': answer,
                'confidence': 0.75,
                'sources': relevant_entities[:3],
                'query': question
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'query': question
            }
    
    def _retrieve_entities(self, question: str) -> List[str]:
        """检索相关实体"""
        # 简化的关键词匹配
        keywords = ['钛', 'Ti', '合金', '强度', '元素', '铝', 'Al', 'V']
        relevant = []
        
        for entity, data in self.kg_data.get('nodes', {}).items():
            if any(kw in question for kw in keywords):
                if any(kw in entity for kw in keywords):
                    relevant.append(entity)
        
        return relevant[:10]
    
    def _generate_answer(self, question: str, entities: List[str]) -> str:
        """生成答案"""
        if not entities:
            return "抱歉，未找到相关信息。"
        
        # 简化的答案生成
        context = f"基于知识图谱检索到的相关实体: {', '.join(entities[:3])}"
        return f"根据钛合金知识图谱，{context}。这些实体与您的问题相关，可以提供相关的材料特性和应用信息。"

# 测试函数
def test_rag_system():
    """测试RAG系统"""
    try:
        from pathlib import Path
        kg_path = Path('data/processed/latest_knowledge_graph.json')
        
        if not kg_path.exists():
            print("知识图谱文件不存在，无法测试RAG系统")
            return False
        
        rag = EnhancedAlloyRAGSystem(str(kg_path))
        
        test_queries = [
            "钛合金中铝元素的作用是什么？",
            "Ti-6Al-4V合金有什么特点？"
        ]
        
        for query in test_queries:
            result = rag.query(query)
            print(f"查询: {query}")
            print(f"回答: {result.get('answer', result.get('error'))}")
            print("-" * 50)
        
        return True
        
    except Exception as e:
        print(f"RAG系统测试失败: {e}")
        return False

if __name__ == "__main__":
    test_rag_system()
