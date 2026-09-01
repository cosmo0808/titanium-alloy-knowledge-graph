# config/paths.py - 项目路径配置
import sys
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 数据目录（全部基于项目根，避免机器特定绝对路径）
DATA_DIR = PROJECT_ROOT / "data"
PDF_DIRECTORY = DATA_DIR / "sample"            # 样例 PDF / 演示数据目录
SAMPLE_DATA_DIR = DATA_DIR / "sample"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
OPENKE_BENCHMARK_DIR = PROJECT_ROOT / "data" / "openke_benchmark"
RESULTS_DIR = PROJECT_ROOT / "results"
DOCS_DIR = PROJECT_ROOT / "docs"
DATABASE_PATH = PROCESSED_DATA_DIR / "materials.db"

# OpenKE 路径配置（可选：本地克隆 OpenKE 仓库位置）
OPENKE_ROOT = DATA_DIR / "OpenKE"
OPENKE_BENCHMARKS = OPENKE_BENCHMARK_DIR
OPENKE_EXAMPLES = OPENKE_ROOT / "examples"
OPENKE_MODULE = OPENKE_ROOT / "openke"

# 处理参数
MAX_PDFS = 100
DB_LIMIT = 1000

# 确保输出目录存在
for _dir in (PROCESSED_DATA_DIR, RESULTS_DIR, OPENKE_BENCHMARK_DIR):
    _dir.mkdir(parents=True, exist_ok=True)


def setup_openke_path():
    """将 OpenKE 源码路径加入 sys.path（若已克隆到 data/OpenKE）"""
    openke_paths = [str(OPENKE_ROOT), str(OPENKE_MODULE), str(OPENKE_EXAMPLES)]
    for path in openke_paths:
        if path not in sys.path:
            sys.path.append(path)
    return openke_paths


def validate_data_paths():
    """验证数据路径"""
    return {
        'pdf_directory': PDF_DIRECTORY.exists(),
        'database_file': DATABASE_PATH.exists(),
        'openke_installed': OPENKE_ROOT.exists(),
        'pdf_count': len(list(PDF_DIRECTORY.glob("**/*.pdf"))) if PDF_DIRECTORY.exists() else 0
    }
