---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 0c9efe16b40bce9f69d16a27d80c8dc9_91486b2ba60b11f1891f525400f8a581
    ReservedCode1: HZQ5E5WGIA/zjs7QunAoz803YerpDeSpFcOVltVPThuBDghCVmqES8tkDofvnlWBuigSjqvaCX6LJ6275tx4cJZ4dzGdP/yyRWO9bB4kcaSa/ftOReSQzGG0kwDP4VB4RsgUuHaC8HCXwpJ0kbokYFijb79SgpzAcvNWh7KEA7Lg6qsxVZirfbPZKYg=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 0c9efe16b40bce9f69d16a27d80c8dc9_91486b2ba60b11f1891f525400f8a581
    ReservedCode2: HZQ5E5WGIA/zjs7QunAoz803YerpDeSpFcOVltVPThuBDghCVmqES8tkDofvnlWBuigSjqvaCX6LJ6275tx4cJZ4dzGdP/yyRWO9bB4kcaSa/ftOReSQzGG0kwDP4VB4RsgUuHaC8HCXwpJ0kbokYFijb79SgpzAcvNWh7KEA7Lg6qsxVZirfbPZKYg=
---

# Titanium Alloy Knowledge Graph

> 面向材料科学的多模态知识图谱构建管线：从 PDF / 数据库到超图建模、双层存储、
> 神经符号混合检索 RAG、图挖掘与自动化验收评估。

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.x-green?logo=neo4j&logoColor=white)](https://neo4j.com/)
[![NetworkX](https://img.shields.io/badge/NetworkX-3.x-orange?logo=networkx)](https://networkx.org/)
[![Plotly](https://img.shields.io/badge/Plotly-5.x-3D9970)](https://plotly.com/python/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Validation](https://img.shields.io/badge/Validation-Automated%20Pipeline-blue)](#validation-framework--evaluation-protocol)

---

## Table of Contents

- [Executive Summary](#executive-summary)
- [Motivation: 为什么材料知识需要超图](#motivation-为什么材料知识需要超图)
- [Core Architecture & Data Flow](#core-architecture--data-flow)
- [Key Technical Highlights](#key-technical-highlights)
  - [1. Hypergraph Modeling for Materials Science](#1-hypergraph-modeling-for-materials-science)
  - [2. Dual-Tier Storage Architecture](#2-dual-tier-storage-architecture)
  - [3. Neuro-Symbolic Hybrid RAG](#3-neuro-symbolic-hybrid-rag)
  - [4. Native TransE & OpenKE Compatibility](#4-native-transe--openke-compatibility)
  - [5. Automated 5-Stage Metric Scoring](#5-automated-5-stage-metric-scoring)
- [Repository Structure](#repository-structure)
- [Quickstart & Reproducibility](#quickstart--reproducibility)
- [Configuration](#configuration)
- [Validation Framework & Evaluation Protocol](#validation-framework--evaluation-protocol)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Executive Summary

钛合金（如 Ti-6Al-4V、TC4、TA15 等）是航空航天、生物医用与先进制造领域的核心结构
材料，其"成分 - 工艺 - 组织 - 性能"四要素之间存在强耦合、多组分、多相反应等复杂
关系。传统关系型表格与二元知识图谱难以无损表达这类 **N 元关系**。

本项目实现了一条完整的**材料超图知识图谱构建与关系分析管线**：

- 从 PDF 文献与 SQLite 数据库自动抽取材料实体（合金牌号、元素、力学性能）与关系；
- 以**超图关联图（Hypergraph Incidence Graph）**统一建模多组分/多相 N 元关系；
- 采用 **双层存储**（零依赖 SQLite / NetworkX 本地层 + 可选 Neo4j 企业层）；
- 提供 **神经符号混合检索 RAG**（语义向量 + 关键词 + 拓扑子图三路召回融合）；
- 内置纯 Python / NumPy 实现的 **TransE 知识表示学习**，兼容 OpenKE 基准格式；
- 提供 **5 阶段自动化验收** 与 **5 类快速验证** 双套评分体系，全部基于真实运行产物。

项目内置完整的自动化验证体系（详见
[Validation Framework & Evaluation Protocol](#validation-framework--evaluation-protocol)）：
`run_validation.py` 快速验收与 `main.py` 完整验收双入口，配合
`validation_system.py` 多维评分模型，覆盖数据预处理、知识图谱构建、RAG、
图挖掘与系统集成全链路；所有验证结果输出为 `results/` 下的 JSON 报告，
可复现、可门禁，用于 CI/CD 自动化校验与私有数据接入时的质量把控。

---

## Motivation: 为什么材料知识需要超图

### 二元图的表达瓶颈

知识图谱的经典表示是**有向三元组** `(head, relation, tail)`，例如：

```
(Ti-6Al-4V) --contains--> (Ti)
(Ti-6Al-4V) --contains--> (Al)
(Ti-6Al-4V) --contains--> (V)
```

这在语义上**丢失了关键信息**：

1. **配比丢失**：Ti-6Al-4V 含 90% Ti、6% Al、4% V，但三条 `contains` 边无法区分
   主元素与微量元素的权重差异；
2. **多组分协同**：某性能是"Ti-6Al-4V 在 950℃ 固溶 + 550℃ 时效"这一**组合条件**的
   结果，而非任意单一路径的结果；
3. **多相反应**：α+β 双相组织、晶界 α 相析出等涉及**多个参与实体同时出现**，
   三元组只能强行拆分为多对二，破坏整体语义。

### 超图（Hypergraph）如何解决

超图将二元图的边推广为**超边（hyperedge）**：一条超边可以连接任意数量的节点。
材料合成中的多组分/多相反应天然是 N 元关系：

```
超边: [Ti-6Al-4V, Ti(90%), Al(6%), V(4%), 950℃固溶, 550℃时效] --表示--> 双相组织+高强度
```

为便于计算与可视化，本项目采用**超图关联图（Incidence Graph / Bipartite Graph）**
表示：超边本身也建模为一种节点，超边节点与其成员节点之间用普通边相连。这样既保留
N 元关系语义，又可直接复用成熟的图算法（PageRank、Louvain 社区发现、链路预测等）。

### 材料领域的收益

- **查询完整性**：可回答"哪些合金在什么工艺下同时满足强度 > 900MPa 且延伸率 > 10%"；
- **知识发现**：通过社区检测发现未被文献明确书写的高相关合金族；
- **链接预测**：利用嵌入相似度预测缺失的合金-性能关联，为实验设计提供候选。

---

## Core Architecture & Data Flow

<div align="center">
  <img src="docs/images/architecture.png" alt="System Architecture" width="850px" />
  <p><em>Figure 1: Full-lifecycle pipeline from multimodal ingestion to OpenKE embedding and hybrid RAG.</em></p>
</div>

```
                          ┌─────────────────────────────────────────────────────┐
                          │                   输入层（config/paths.py）           │
                          │   data/sample/*.pdf      data/processed/materials.db │
                          └───────────────┬─────────────────────────────────────┘
                                          │
                          ┌───────────────▼─────────────────────────────────────┐
                          │  阶段 1：数据预处理（script/data_loader.py）          │
                          │  PDFProcessor：PyMuPDF 逐页提取文本/表格元数据/图像   │
                          │  DatabaseParser：读取 SQLite 表补充数据源             │
                          │  ⚠ 无 PDF/DB 时自动降级为内置 Mock 数据              │
                          └───────────────┬─────────────────────────────────────┘
                                          │ processed/*_processed.json
                          ┌───────────────▼─────────────────────────────────────┐
                          │  阶段 2：知识图谱构建（entity_relation_extractor.py） │
                          │  规则抽取：合金牌号/元素/力学性能正则模式             │
                          │  神经抽取（可选）：QwenParser 经 Ollama CLI 调用      │
                          │  表格抽取：csv_file 优先，内联元数据安全跳过          │
                          │  → 实体-关系列表 → 去重 → 超图构建 → 超图清洗          │
                          └───────────────┬─────────────────────────────────────┘
                                          │ entities_relations_hg.json / hypergraph
                          ┌───────────────▼─────────────────────────────────────┐
                          │  双层存储（Dual-Tier）                               │
                          │  本地层：SQLite / NetworkX / JSON（零依赖）           │
                          │  企业层（可选）：Neo4j Vector Index（需 .env 配置）   │
                          └───────────────┬─────────────────────────────────────┘
                                          │
                          ┌───────────────▼─────────────────────────────────────┐
                          │  阶段 3：RAG 系统（enhanced_rag_system.py）          │
                          │  OfflineTextEncoder 词频向量（无需 GPU）             │
                          │  query(top_k=5, method='hybrid')                     │
                          │  = 语义召回 + 关键词召回 + 图拓扑召回 三路融合        │
                          └───────────────┬─────────────────────────────────────┘
                                          │
                          ┌───────────────▼─────────────────────────────────────┐
                          │  阶段 4：图挖掘（advanced_graph_mining.py）           │
                          │  PageRank 重要节点 / Louvain 社区发现               │
                          │  余弦相似度(>0.7) 链接预测 / 因果路径 / 实体聚类      │
                          └───────────────┬─────────────────────────────────────┘
                                          │
                          ┌───────────────▼─────────────────────────────────────┐
                          │  阶段 5-6：验收测试 + 最终报告（main.py / validation_system.py）│
                          │  6 阶段总分 70（预处理10+图谱15+RAG15+挖掘15+用例15） │
                          │  results/final_acceptance_report_*.json              │
                          └─────────────────────────────────────────────────────┘
```

### 模块全景（22 个已编译验证的 .py）

| 层 | 模块 | 职责 |
|----|------|------|
| 入口 | `main.py` | 6 阶段端到端验收流程（`EnhancedAlloyKGSystem`） |
| 预处理 | `script/data_loader.py` | PDF / DB 解析与 Mock 降级 |
| 抽取 | `script/entity_relation_extractor.py` | 规则 + 可选 LLM 的实体关系抽取、超图构建 |
| 抽取 | `script/entity_relation_extractor_db.py` | 数据库源实体关系抽取 |
| 存储 | `script/knowledge_storage_system.py` | SQLite / NetworkX 双层存储接口、质量评估 |
| 存储 | `script/neo4j_knowledge_storage.py` | Neo4j 导出（可选，需环境变量） |
| 存储 | `neo4j_hypergraph_generator.py` | Neo4j 超图生成（可选） |
| 存储 | `db_to_graphml_generator.py` | 数据库 → GraphML 导出 |
| RAG | `script/enhanced_rag_system.py` | 混合检索 RAG（`WorkingRAGSystem`） |
| RAG | `script/rag_system.py` | RAG 模板（`EnhancedAlloyRAGSystem`） |
| 挖掘 | `script/advanced_graph_mining.py` | 图挖掘套件（`TitaniumGraphMiner`） |
| 挖掘 | `script/dynamic_qa_generator.py` | 动态 QA 生成 |
| 嵌入 | `script/openke_integration.py` | 原生 TransE（`EnhancedTransE`）+ OpenKE 兼容 |
| 嵌入 | `quick_openke_test.py` | OpenKE 可选探测（import 均在 try 内） |
| 验证 | `validation_system.py` | 5 类评分验证系统（`ValidationSystem`） |
| 验证 | `run_validation.py` | 快速验证入口（`SystemValidator`，100 分制） |
| 可视化 | `visualize_hypergraph_plotly.py` | Plotly 交互可视化（浏览器打开） |
| 配置 | `config/paths.py` | 全部路径基于项目根解析，无机器绝对路径 |

---

## Key Technical Highlights

### 1. Hypergraph Modeling for Materials Science

<div align="center">
  <img src="docs/images/hypergraph_network.png" alt="Materials Hypergraph Visualization" width="850px" />
  <p><em>Figure 2: Force-directed topological visualization of alloy-element incidence structures.</em></p>
</div>

**N 元超边关系建模**是区别于普通知识图谱项目的核心差异点。

- `RuleBasedExtractorHG`（`script/entity_relation_extractor.py`）将抽取结果组织为
  `{'nodes': {...}, 'edges': [...]}` 的超图 JSON；超边节点与其成员节点之间的关联
  构成**关联图（Incidence Graph）**，可直接导入 NetworkX 复用图算法；
- 领域正则模式覆盖常见材料表达：
  - 合金牌号：`Ti-6Al-4V`、`TC4`、`TA15`、`Grade 5`、`TNTZ` 等；
  - 元素含量：`Ti 90%`、`Al content of 6%`、`6wt V` 等；
  - 力学性能：`tensile strength`、`yield strength`、`hardness`、`modulus` 等；
- 实体归一化（`normalize_entity`）处理 OCR 常见混淆（`l/1`、`O/0`、`S/5`），
  并通过白名单映射统一异写；
- 超图清洗（hypergraph cleaning）在构建后执行，移除孤立节点与冗余边，
  保证下游图算法输入质量。

### 2. Dual-Tier Storage Architecture

<div align="center">
  <img src="docs/images/neo4j_graph.png" alt="Neo4j Schema and Graph View" width="850px" />
  <p><em>Figure 3: Neo4j schema definition, APOC graph batch import, and connected subgraph queries.</em></p>
</div>

面向"本地可复现"与"企业可扩展"两种使用场景，存储层分为两级：

| 层级 | 技术 | 特点 | 代码 |
|------|------|------|------|
| 本地层 | SQLite + NetworkX + JSON | 零外部服务依赖，clone 即跑；`GraphDatabaseInterface` 统一接口 | `script/knowledge_storage_system.py` |
| 企业层 | Neo4j（5.x，Vector Index） | 图遍历与向量检索扩展；凭据经环境变量注入，无硬编码 | `script/neo4j_knowledge_storage.py`、`neo4j_hypergraph_generator.py` |

- 安全实践：Neo4j 连接信息只从 `NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD` 环境变量
  读取，仓库无任何真实凭据残留，`.env.example` 提供模板；
- `KnowledgeQualityEvaluator` 对存储前后的知识质量（完整性/一致性）进行量化评估；
- GraphML 导出（`db_to_graphml_generator.py`）支持将图谱导入 Gephi 等外部工具。

### 3. Neuro-Symbolic Hybrid RAG

`WorkingRAGSystem.query(question, top_k=5, method='hybrid')` 实现三路召回融合：

```
                    ┌────────────────────────────────────────────┐
   question ──────► │ semantic_retrieval  词频向量余弦相似度       │
                    │ keyword_retrieval   关键词倒排匹配          │
                    │ graph_retrieval     图拓扑子图遍历          │
                    └────────────────────────────────────────────┘
                                   │ 融合（method='hybrid'）
                                   ▼
                          top-k 检索结果 + 来源
```

- **符号侧**：`graph_retrieval` 沿知识图谱拓扑遍历，保留可解释的路径证据；
- **神经侧**：`OfflineTextEncoder` 提供零依赖词频向量编码（vocab=1000，无需 GPU），
  可选安装 `sentence-transformers` 后升级为语义嵌入；
- 三路结果按 `top_k` 融合输出，兼顾语义相似与结构可达。

### 4. Native TransE & OpenKE Compatibility

<div align="center">
  <img src="docs/images/predicted_links_table.png" alt="Predicted Links Ranking" width="650px" />
  <p><em>Figure 4: Knowledge representation learning output and link prediction score ranking.</em></p>
</div>

`EnhancedTransE`（`script/openke_integration.py`）是**纯 Python / NumPy** 实现的
TransE 翻译距离模型，无需 PyTorch：

- 参数：`embedding_dim=64`、`margin=1.0`、`learning_rate=0.01`、负采样 1:1；
- 训练：margin-based ranking loss（`max(0, margin + pos_score - neg_score)`），
  逐三元组随机梯度更新实体/关系嵌入；
- 兼容性：`data/openke_benchmark/` 提供标准 OpenKE 基准格式
  （`entity2id.txt / relation2id.txt / train2id.txt / valid2id.txt / test2id.txt`）；
  `MultiSourceKGEmbedding` 支持多源知识图谱联合嵌入；
- `quick_openke_test.py` 探测外部 OpenKE 是否可用——所有 `openke.*` import 均在
  try/except 内，未安装时优雅降级，不影响主流程。

### 5. Automated 5-Stage Validation Architecture

项目内置**两套可复现的自动化验证体系**，全部基于真实运行产物，杜绝人工估分：

**A. 快速验证 `run_validation.py`（`SystemValidator`，5 类检查）**

| 测试类 | 考察内容 |
|--------|----------|
| `data_processing` | 数据加载器存在性、processed 文件数量 |
| `knowledge_graph` | 图谱文件、节点/边规模、OpenKE 基准文件 |
| `rag_system` | RAG 脚本、向量文件 |
| `graph_mining` | 挖掘脚本、结果产物 |
| `system_integration` | 主入口、配置、运行结果文件 |

**B. 完整验收 `main.py`（`EnhancedAlloyKGSystem`，6 阶段流水线）**

| 阶段 | 验证内容 |
|------|----------|
| 阶段 1 数据预处理 | 多模态解析与数据清洗产物 |
| 阶段 2 知识图谱构建 | 图谱文件、节点/边规模、向量嵌入 |
| 阶段 3 RAG 系统 | 检索实现与查询质量 |
| 阶段 4 图挖掘 | 挖掘实现、方法合理性、产物质量 |
| 阶段 5 验收测试用例 | 端到端断言 |
| 阶段 6 最终报告生成 | 汇总输出至 `results/` |

每阶段产出 JSON 报告至 `results/`，含分项结论与失败原因，可直接用于 CI 门禁。

---

## Repository Structure

```
titanium-alloy-knowledge-graph/
├── main.py                          # 6 阶段端到端验收入口
├── run_validation.py                # 快速验证入口（100 分制）
├── validation_system.py             # 5 类评分验证系统
├── visualize_hypergraph_plotly.py   # Plotly 交互可视化
├── db_to_graphml_generator.py       # DB → GraphML 导出
├── neo4j_hypergraph_generator.py    # Neo4j 超图生成（可选）
├── quick_openke_test.py             # OpenKE 可选探测
├── run_knowledge_storage.py         # 双层存储演示入口
├── config/
│   ├── paths.py                     # 全部路径（基于项目根）
│   └── __init__.py
├── script/
│   ├── data_loader.py               # PDF / DB 解析 + Mock 降级
│   ├── entity_relation_extractor.py # 规则 + 可选 LLM 抽取、超图构建
│   ├── entity_relation_extractor_db.py
│   ├── knowledge_storage_system.py  # SQLite / NetworkX 双层存储
│   ├── neo4j_knowledge_storage.py   # Neo4j 导出（可选）
│   ├── rag_system.py                # RAG 模板
│   ├── enhanced_rag_system.py       # 混合检索 RAG
│   ├── advanced_graph_mining.py     # 图挖掘套件
│   ├── dynamic_qa_generator.py      # 动态 QA 生成
│   └── openke_integration.py        # 原生 TransE + OpenKE 兼容
├── data/
│   ├── sample/                      # 演示数据（入库）
│   ├── openke_benchmark/            # OpenKE 基准格式（入库）
│   ├── processed/                   # 运行产物（gitignored）
│   └── README.md                    # 数据格式规范与接入说明
├── docs/
│   ├── PIPELINE.md
│   └── CHANGELOG.md
├── PROJECT_DOCUMENTATION.md         # 14 章自包含技术文档（21/21 源码覆盖）
├── results/                         # 运行报告 JSON（gitignored）
├── requirements.txt                 # 核心轻量依赖
├── requirements-optional.txt        # 可选重依赖
├── .env.example                     # 环境变量模板
└── LICENSE                          # MIT
```

---

## Quickstart & Reproducibility

### 环境要求

- Python 3.9+
- 核心依赖见 `requirements.txt`（7 个轻量包：pandas / numpy / networkx /
  scikit-learn / PyMuPDF / plotly / tqdm）
- 可选依赖见 `requirements-optional.txt`（Neo4j / sentence-transformers / torch /
  requests / OpenKE，按需安装）
- Windows / Linux / macOS 均可运行（路径由 `config/paths.py` 统一解析）

### 安装

```bash
git clone <your-repo-url>
cd titanium-alloy-knowledge-graph
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
# 可选：pip install -r requirements-optional.txt
```

### 两分钟跑通完整流程

项目内置 Mock 降级机制：无 PDF、无数据库时自动生成模拟数据，
**无需任何外部服务**即可端到端运行。

```bash
# 1. 完整验收（6 阶段：预处理 -> 图谱 -> RAG -> 挖掘 -> 用例 -> 报告）
python main.py

# 2. 快速验证（100 分制）
python run_validation.py

# 3. 可视化（读取 data/sample/knowledge_graph_simplified.json，浏览器打开）
python visualize_hypergraph_plotly.py

# 4. 快速验证脚本编译（可选）
python -m py_compile main.py run_validation.py validation_system.py script/*.py
```

### 可选扩展能力

```bash
# 双层存储演示（本地 SQLite / NetworkX，无外部服务）
python run_knowledge_storage.py

# 数据库 -> GraphML 导出
python db_to_graphml_generator.py

# OpenKE 可用性探测（未安装 OpenKE 时输出提示，不报错）
python quick_openke_test.py

# Neo4j 超图生成（需先配置 .env 的 NEO4J_* 并安装 neo4j 依赖）
python neo4j_hypergraph_generator.py
```

### 复现与审计

每次运行会在 `results/` 生成带时间戳的 JSON 报告
（如 `quick_validation_20260901_213659.json`、`final_acceptance_report_*.json`），
内含分项得分与详情字段，可用于版本间对比与 CI 审计。

---

## Configuration

### 路径配置（config/paths.py）

| 配置 | 默认值 | 说明 |
|------|--------|------|
| `PDF_DIRECTORY` | `data/sample` | 私有 PDF 放置目录 |
| `DATABASE_PATH` | `data/processed/materials.db` | 私有 SQLite 数据库路径 |
| `PROCESSED_DATA_DIR` | `data/processed` | 预处理输出 |
| `OPENKE_BENCHMARK_DIR` | `data/openke_benchmark` | OpenKE 基准格式 |
| `OPENKE_ROOT` | `data/OpenKE` | 可选外部 OpenKE 源码 |
| `MAX_PDFS` / `DB_LIMIT` | 100 / 1000 | 输入规模上限 |

### 环境变量（.env.example）

```bash
# Neo4j（可选）
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password

# OpenKE（可选）
# OPENKE_ROOT=/path/to/OpenKE
```

### 接入私有数据

1. 将文献 PDF 放入 `data/sample/`（详见 `data/README.md`）；
2. （可选）放置 SQLite 数据库为 `data/processed/materials.db`；
3. （可选）安装 Ollama 并拉取模型，启用 `QwenParser` 神经抽取；
4. 运行 `python main.py`。

---

## Validation Framework & Evaluation Protocol

> 验证体系面向 **CI/CD 自动化校验** 与 **私有数据接入时的质量把控** 设计：
> 所有检查均基于真实运行产物（`results/` 下的 JSON 报告），可复现、可门禁，
> 不依赖人工估分。报告文件示例见 `results/quick_validation_*.json` 与
> `results/final_acceptance_report_*.json`。

### 5-Stage Automated Verification Pipeline

验证体系由两条互补的自动化流水线构成，覆盖从数据接入到交付物的全链路：

| 入口 | 实现类 | 结构 | 覆盖范围 |
|------|--------|------|----------|
| `run_validation.py` | `SystemValidator` | 5 类检查 | 数据预处理、知识图谱、RAG、图挖掘、系统集成 |
| `main.py` | `EnhancedAlloyKGSystem` | 6 阶段流水线 | 数据预处理 → 图谱构建 → RAG → 图挖掘 → 验收用例 → 最终报告 |
| `validation_system.py` | `ValidationSystem` | 5 类评分模型 | 与 `main.py` 各阶段一一对应，输出分项结论 |

每个检查项输出明确结论（PASS / PARTIAL / FAIL）与失败原因，供 CI 门禁直接消费。

### Multi-dimensional Graph Quality Metrics

评分模型从多个维度评估图谱与检索质量，各维度均有对应源码检查点：

| 维度 | 考察内容 | 源码检查点 |
|------|----------|------------|
| **Completeness** | 节点规模、实体类型多样性、边规模、向量嵌入产物 | `ValidationSystem._test_kg_completeness` |
| **Consistency** | 数据清洗后的有效元素比例与孤立实体比例 | `ValidationSystem._evaluate_data_cleaning` |
| **Connectivity** | 孤立节点检测、桥边检测与超边补全推理 | `script/advanced_graph_mining.py` |
| **Informativeness** | RAG 查询质量、图挖掘产物质量 | `ValidationSystem._test_rag_quality` / `_test_mining_quality` |
| **Coverage** | 多类型问题覆盖、多模态渠道（文本/表格/图像）覆盖 | `dynamic_qa_generator.py` / 抽取管线 |

### Graceful Degradation & Unit Fallbacks

验证套件在无本地 LLM / GPU / 外部服务环境下仍可完整运行，通过逐级降级保证
**可测试性**：

| 能力 | 依赖 | 缺失时行为 |
|------|------|------------|
| PDF 解析 / 图谱构建 / 图挖掘 / 可视化 | 无外部服务 | 正常运行（Mock 降级） |
| 图像神经抽取 | Ollama CLI（可选） | 回退规则解析，日志告警 |
| Neo4j 企业存储 | Neo4j 5.x（可选） | 跳过企业层，仅本地层 |
| 语义嵌入升级 | sentence-transformers（可选） | 使用内置词频向量 |
| OpenKE 外部训练 | OpenKE 源码（可选） | 使用内置原生 TransE |

降级机制确保验证流水线可在 **零外部依赖** 的 CI 环境中稳定执行，同时在
接入真实数据与可选服务后自动获得更强的抽取与检索能力。

---

## Roadmap

- [ ] 接入真实 PDF 文献集，验证图谱规模与抽取精度；
- [ ] 修复 `run_validation.py` 对旧项目结构入口的检查假设（类 F 检查项）；
- [ ] 将 `csv_file` 内联表格的单元格内容解析纳入 Mock 数据，提升表格抽取覆盖率；
- [ ] 增加 `sentence-transformers` 语义检索的端到端示例与对比基准；
- [ ] 补充 Neo4j Vector Index 的 Docker Compose 一键启动；
- [ ] 固定 requirements 精确版本，提供 CI 流水线模板（GitHub Actions）；
- [ ] 增加多语言（中文/英文）抽取评测集与 F1 指标。

---

## Contributing

欢迎提交 Issue 与 Pull Request。参与前请阅读 `docs/PIPELINE.md` 了解管线约定。

开发约束（与项目基线保持一致）：

- **不重写既有算法**：图算法、RAG 方法论、TransE 实现保持现有架构；
- **不拆分文件**：模块边界已稳定，新增功能请放入对应 `script/` 模块；
- **不捏造验证结果**：所有结论必须来自真实运行产物；
- **路径安全**：新增代码不得引入机器特定绝对路径。

---

## License

本项目基于 [MIT License](LICENSE) 开源。版权所有 © 2026 Titanium Alloy Knowledge
Graph Project Contributors。第三方依赖（PyMuPDF、NetworkX、scikit-learn、Plotly、
Neo4j 等）遵循各自许可证。
*（内容由AI生成，仅供参考）*
