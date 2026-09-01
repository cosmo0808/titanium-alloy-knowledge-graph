---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 0c9efe16b40bce9f69d16a27d80c8dc9_95d007e0a60b11f199d2525400287e28
    ReservedCode1: szFQT8uFyr27ASBzPYyOXpx2I6ZVubz8Ynba2kN4x86UVun8HUgUYkRncmOSDSz+Bi9wrQukf+oXYLm4nHY5967da+g0CIP6gF2yat64sb1MdSIxFaJyoKSxn0NH9kC9W1TV1SM6gfg6vkUtoLEcsZvajGryOuJpqraCzYlKUjRnLFTI1ts/wxmTgQI=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 0c9efe16b40bce9f69d16a27d80c8dc9_95d007e0a60b11f199d2525400287e28
    ReservedCode2: szFQT8uFyr27ASBzPYyOXpx2I6ZVubz8Ynba2kN4x86UVun8HUgUYkRncmOSDSz+Bi9wrQukf+oXYLm4nHY5967da+g0CIP6gF2yat64sb1MdSIxFaJyoKSxn0NH9kC9W1TV1SM6gfg6vkUtoLEcsZvajGryOuJpqraCzYlKUjRnLFTI1ts/wxmTgQI=
---

# data/ 数据目录说明

本项目的数据输入、运行产物与演示数据统一放置在本目录，所有路径由
`config/paths.py` 基于项目根目录动态解析，不依赖机器特定绝对路径。

## 目录结构

| 目录 | 用途 | Git 跟踪 |
|------|------|----------|
| `sample/` | 演示数据（processed JSON、图谱 JSON、CSV、GraphML、HTML 可视化产物等） | 保留 |
| `processed/` | 数据预处理运行产物（PDF 解析结果 JSON、materials.db、超图 JSON 等） | 忽略 |
| `openke_benchmark/` | OpenKE 基准格式文件（entity2id/relation2id/train2id/test2id/valid2id） | 保留 |
| `OpenKE/` | 可选：本地克隆的 OpenKE 源码目录 | 忽略 |
| `graph_storage/`、`embeddings/` | 可选存储/嵌入运行产物 | 忽略 |

## 输入数据格式规范

### 1. PDF 文档（私有数据接入）

- 放置位置：`data/sample/*.pdf`（`config/paths.py` 中 `PDF_DIRECTORY = DATA_DIR / "sample"`）
- 解析流程（`script/data_loader.py` 的 `PDFProcessor`）：使用 PyMuPDF 逐页提取
  - `text`：每页文本（截断至 2000 字符）
  - `tables`：表格元数据字典
  - `images`：图像元数据（文件前缀 + 页码 + 序号）
  - `formulas`：公式占位（当前为空列表）
- 解析结果以 `{pdf_stem}_processed.json` 写入 `data/processed/`

**表格字典格式**（当前实现的两种形态）：

```json
{
  "page": 1,
  "table_num": 1,
  "rows": 5,
  "columns": 3
}
```

- 内联元数据形态：仅含 `page / table_num / rows / columns`，表示"检测到表格但无单元格内容"
- 可选扩展形态：额外携带 `csv_file` 字段，指向 `data/processed/` 下真实导出的 CSV 表，
  此时抽取器会读取 CSV 并按元素-含量列提取实体关系

> 兼容性说明：抽取器（`script/entity_relation_extractor.py`）对两种形态均安全——
> 无 `csv_file` 的内联表格会被跳过而不中断流程（日志记录 debug 信息）。

### 2. SQLite 数据库（私有数据接入）

- 放置位置：`data/processed/materials.db`（`config/paths.py` 中 `DATABASE_PATH`）
- 解析流程（`script/data_loader.py` 的 `DatabaseParser`）：读取数据库表作为补充数据源，
  单库最多读取 1000 张表（`DB_LIMIT`）

## Mock 降级机制

当输入数据缺失时，系统自动降级为内置模拟数据，保证全流程可复现：

| 缺失输入 | 降级行为 |
|----------|----------|
| `data/sample/` 下无 PDF | 日志提示「未找到PDF文件，创建模拟数据」，生成 5 个 mock `*_processed.json`（含文本与表格元数据） |
| `data/processed/materials.db` 不存在 | 日志提示「数据库不存在，创建模拟数据」，生成 mock 表数据 |

该机制是 `python main.py` 开箱即跑的基础；mock 数据的实体稀疏性说明见顶层 README
「Realistic Benchmarks & Limitations」。

## 如何接入私有数据

1. 将论文/报告的 PDF 放入 `data/sample/`（可多文件，`MAX_PDFS = 100`）
2. （可选）将结构化材料数据库复制为 `data/processed/materials.db`
3. 运行 `python main.py`，系统自动完成解析、抽取、图谱构建、RAG、挖掘与验收全流程
4. 用 `python visualize_hypergraph_plotly.py` 可视化 `data/sample/knowledge_graph_simplified.json`

## 演示数据速览（data/sample/）

- `*_processed.json`：PDF 预处理输出样例
- `entities_relations_hg.json` / `sample_alloy_hg.json`：超图 JSON（nodes + edges）
- `knowledge_graph_simplified.json`：可视化用简化图谱
- `*.csv`：实体/关系嵌入与链接预测结果
- `*.graphml`：GraphML 导出（可导入 Gephi 等工具）
- `graph_viewer.html`：Plotly 交互可视化导出
- `final_acceptance_report.json`：验收报告样例
*（内容由AI生成，仅供参考）*
