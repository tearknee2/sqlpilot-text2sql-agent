"""让 `python -m sqlpilot.eval` 可用（doc §4.7）。"""
import sys

from sqlpilot.eval.runner import main

sys.exit(main())