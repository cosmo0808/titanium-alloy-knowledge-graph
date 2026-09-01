import json
from pathlib import Path
import networkx as nx
import plotly.graph_objects as go

# ====== 配置 ======
# 默认读取项目 data/sample 下的演示知识图谱，可自行替换为其他 JSON
PROJECT_ROOT = Path(__file__).resolve().parent
JSON_PATH = PROJECT_ROOT / "data" / "sample" / "knowledge_graph_simplified.json"
# ====== 读取 JSON ======
with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

nodes_data = data["nodes"]
edges_data = data["edges"]

# ====== 构建 NetworkX 图 ======
G = nx.Graph()

# 添加节点
for node, info in nodes_data.items():
    node_type = info.get("type", "alloy")
    G.add_node(node, type=node_type)

# 添加边
for source, target in edges_data:
    if source in G.nodes and target in G.nodes:
        G.add_edge(source, target)

# ====== 节点布局 ======
pos = nx.spring_layout(G, seed=42, k=0.5)

# ====== 节点颜色 ======
color_map = {"alloy": "skyblue", "element": "orange", "property": "lightgreen"}

# ====== 创建 Plotly 节点散点 ======
node_x, node_y = [], []
node_color, node_text = [], []

for n, attr in G.nodes(data=True):
    x, y = pos[n]
    node_x.append(x)
    node_y.append(y)
    node_color.append(color_map.get(attr["type"], "grey"))
    node_text.append(f"{n} ({attr['type']})")  # hover 显示完整名称和类型

node_trace = go.Scatter(
    x=node_x, y=node_y,
    mode='markers+text',
    textposition='top center',
    marker=dict(size=15, color=node_color),
    text=[n if len(n)<=20 else n[:17]+"..." for n in nodes_data.keys()],
    hovertext=node_text,
    hoverinfo='text'
)

# ====== 创建 Plotly 边 ======
edge_x, edge_y = [], []
for edge in G.edges():
    x0, y0 = pos[edge[0]]
    x1, y1 = pos[edge[1]]
    edge_x.extend([x0, x1, None])
    edge_y.extend([y0, y1, None])

edge_trace = go.Scatter(
    x=edge_x, y=edge_y,
    line=dict(width=1, color='#888'),
    hoverinfo='none',
    mode='lines'
)

# ====== 创建图表 ======
fig = go.Figure(data=[edge_trace, node_trace],
                layout=go.Layout(
                    title='Materials Hypergraph',
                    title_x=0.5,
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=20,l=5,r=5,t=40),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
                ))

fig.show()