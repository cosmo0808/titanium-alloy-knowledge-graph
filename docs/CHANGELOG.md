---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 0c9efe16b40bce9f69d16a27d80c8dc9_7d4212cea5ff11f1891f525400f8a581
    ReservedCode1: f9FVuFGdha4OTNgTNwtd6yUInrB08mL5ohiW8+ztnSOYUA3uIjEJKRV3Ug6sXfzqbSKFM/7+e2SVd1DQsfMVRAlmZX0c7W76MwFLb5OOAu5l7yE33o7r3wVJbmbireVjUB1e95RU7erkcZU4g2mzBqXJWPzxRYQmV+sttManL9/oRGG/PYnuPJjejnk=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 0c9efe16b40bce9f69d16a27d80c8dc9_7d4212cea5ff11f1891f525400f8a581
    ReservedCode2: f9FVuFGdha4OTNgTNwtd6yUInrB08mL5ohiW8+ztnSOYUA3uIjEJKRV3Ug6sXfzqbSKFM/7+e2SVd1DQsfMVRAlmZX0c7W76MwFLb5OOAu5l7yE33o7r3wVJbmbireVjUB1e95RU7erkcZU4g2mzBqXJWPzxRYQmV+sttManL9/oRGG/PYnuPJjejnk=
---

# 仓库清理说明

本文档记录针对公开 GitHub 作品集仓库的保守清理与组织动作，便于回溯。

## 清理动作

- 删除 `__pycache__/`、`*.pyc` 等 Python 缓存
- 删除 `script/data/graph_storage/graph_database.db`（本地 SQLite 图数据库）
- 删除 `system_state.pkl` 等序列化状态文件
- 删除 `script/data/processed/` 下大量带时间戳的 embedding CSV 与报告 JSON 等大规模运行产物
- 保留具有展示价值的小型演示文件（JSON / GraphML / 精简 embedding CSV / HTML），移至 `data/sample/`
- OpenKE 基准小文件（entity2id / relation2id / train2id / test2id / valid2id）保留至 `data/openke_benchmark/`

## 组织动作

- 目录重组为 `config/`、`script/`、`data/sample`、`data/processed`、`data/openke_benchmark`、`docs/`、`results/`
- `script/openke_intergration.py` → `script/openke_integration.py`（修正拼写），全仓库无其他引用旧名的位置
- 新增 `script/__init__.py`，保持 `from script.xxx import ...` 包内导入可用
- 新增 `.gitignore`、`requirements.txt`、`requirements-optional.txt`、`README.md`、`.env.example`

## 路径与凭据

- `config/paths.py` 全面改为基于 `PROJECT_ROOT` 的相对路径，覆盖 `data/sample`、`data/processed`、`data/openke_benchmark`、`results`、`docs`
- 移除 `D:\alloy_hypergraph_rag`、`C:\Users\...`、`/home/...` 等机器特定绝对路径
- `script/neo4j_knowledge_storage.py` 中硬编码的 Neo4j 密码替换为环境变量读取
  （`NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD`），未设置密码时拒绝运行
- 全仓库已确认无真实凭据残留

## 未改动的部分

- 所有算法逻辑、管线结构、模块划分保持不变，未引入新抽象
- 未拆分任何大文件
*（内容由AI生成，仅供参考）*
