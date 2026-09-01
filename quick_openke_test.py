# quick_openke_test.py - 快速测试OpenKE导入
import os
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')


# 添加OpenKE路径（项目根下 data/OpenKE，可用环境变量 OPENKE_ROOT 覆盖）
PROJECT_ROOT = Path(__file__).resolve().parent
openke_root = Path(os.getenv("OPENKE_ROOT", str(PROJECT_ROOT / "data" / "OpenKE")))
sys.path.insert(0, str(openke_root))
sys.path.insert(0, str(openke_root / "openke"))

print("OpenKE导入测试")
print("=" * 40)

# 测试1: 基础导入
print("1. 测试基础导入...")
try:
    import openke
    print("✅ import openke - 成功")
except ImportError as e:
    print(f"❌ import openke - 失败: {e}")

# 测试2: 配置导入
print("\n2. 测试配置导入...")
try:
    from openke.config import Trainer, Tester
    print("✅ from openke.config import Trainer, Tester - 成功")
except ImportError as e:
    print(f"❌ from openke.config import Trainer, Tester - 失败: {e}")

# 测试3: 数据导入
print("\n3. 测试数据导入...")
try:
    from openke.data import TrainDataLoader, TestDataLoader
    print("✅ from openke.data import TrainDataLoader, TestDataLoader - 成功")
except ImportError as e:
    print(f"❌ from openke.data import TrainDataLoader, TestDataLoader - 失败: {e}")

# 测试4: 现代模型导入
print("\n4. 测试现代模型导入...")
try:
    from openke.module.model import TransE
    print("✅ from openke.module.model import TransE - 成功")
except ImportError as e:
    print(f"❌ from openke.module.model import TransE - 失败: {e}")

# 测试5: 现代损失函数导入
print("\n5. 测试现代损失函数导入...")
try:
    from openke.module.loss import MarginLoss
    print("✅ from openke.module.loss import MarginLoss - 成功")
except ImportError as e:
    print(f"❌ from openke.module.loss import MarginLoss - 失败: {e}")

# 测试6: 现代策略导入
print("\n6. 测试现代策略导入...")
try:
    from openke.module.strategy import NegativeSampling
    print("✅ from openke.module.strategy import NegativeSampling - 成功")
except ImportError as e:
    print(f"❌ from openke.module.strategy import NegativeSampling - 失败: {e}")

# 测试7: 旧式模型导入
print("\n7. 测试旧式模型导入...")
try:
    from openke.models import TransE as OldTransE
    print("✅ from openke.models import TransE - 成功")
except ImportError as e:
    print(f"❌ from openke.models import TransE - 失败: {e}")

print("\n" + "=" * 40)
print("测试完成!")