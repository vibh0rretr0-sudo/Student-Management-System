"""List every /api route registered on the app (dev utility)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app

app = create_app()
skip = {"HEAD", "OPTIONS"}
rules = []
for rule in app.url_map.iter_rules():
    if not rule.rule.startswith("/api"):
        continue
    methods = ",".join(sorted(rule.methods - skip))
    rules.append((rule.rule, methods))
for path, methods in sorted(rules):
    print(methods.ljust(6), path)
print("---TOTAL---", len(rules))
