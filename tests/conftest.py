import sys
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("API_KEYS", "demo-key:tenant-demo,other-key:tenant-other")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "1000")
