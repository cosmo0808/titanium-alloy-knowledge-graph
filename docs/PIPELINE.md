---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 0c9efe16b40bce9f69d16a27d80c8dc9_7ae12843a5ff11f1891f525400f8a581
    ReservedCode1: Fg00+BM1zLdQXnPH6SuogotwYbtCQQ5R6bufRKjaOYbAqKrIpJ/oaixMtZ06aMdewCrZU77+7OXpguHZ0kCoYJ4QKfHqdfs7EDRfgOHwAM4XRA2tr79K53nmQc4o0f5VbDKO3D7KhnoWDWTtwENAYXCZGKxdeh06Zp5Vf+kiy3q/IiMXcQJY+HeLxrE=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 0c9efe16b40bce9f69d16a27d80c8dc9_7ae12843a5ff11f1891f525400f8a581
    ReservedCode2: Fg00+BM1zLdQXnPH6SuogotwYbtCQQ5R6bufRKjaOYbAqKrIpJ/oaixMtZ06aMdewCrZU77+7OXpguHZ0kCoYJ4QKfHqdfs7EDRfgOHwAM4XRA2tr79K53nmQc4o0f5VbDKO3D7KhnoWDWTtwENAYXCZGKxdeh06Zp5Vf+kiy3q/IiMXcQJY+HeLxrE=
---

# 数据流与目录约定

## 数据流总览

```
data/sample/*.pdf
      │  script/data_loader.py（PDF 解析）
      ▼
data/processed/materials.db  （SQLite 抽取，script/entity_relation_extractor_db.py）
      │  main.py / script/entity_relation_extractor.py（实体关系抽取）
      ▼
data/processed/*.json        （知识图谱 / 超图 / 问答 / 挖掘报告）
      │  script/generate_graphml.py / db_to_graphml_generator.py
      ▼
data/processed/*.graphml     （GraphML 图谱）
      │  script/openke_integration.py（TransE 嵌入）
      ▼
data/processed/*_embeddings.csv  +  data/openke_benchmark/*（OpenKE 基准格式）
      │  script/advanced_graph_mining.py / script/dynamic_qa_generator.py
      ▼
results/*_report.json        （报告类产出）
```

## 目录约定（重要）

| 目录 | 内容 | 是否入库 |
| --- | --- | --- |
| `data/sample/` | 小型公开演示数据（JSON / GraphML / 精简 embedding CSV / HTML） | 入库 |
| `data/processed/` | 运行生成的大规模 embedding CSV、报告 JSON、materials.db | 不入库（.gitignore） |
| `data/openke_benchmark/` | OpenKE 基准格式小文件（entity2id / relation2id / train2id / test2id / valid2id） | 入库 |
| `data/graph_storage/` | 本地图数据库（graph_database.db）、system_state.pkl 等 | 不入库 |
| `results/` | 报告类最终产出 | 不入库 |
| `docs/` | 本文档等说明 | 入库 |

所有 Python 脚本的路径均基于 `config/paths.py` 中 `PROJECT_ROOT` 计算，不再依赖机器特定绝对路径。新增目录时请先在 `config/paths.py` 注册常量，再在脚本中引用。
*（内容由AI生成，仅供参考）*
