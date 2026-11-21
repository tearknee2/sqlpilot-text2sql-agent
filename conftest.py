# conftest.py（项目根目录，内容可以为空，或：
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))