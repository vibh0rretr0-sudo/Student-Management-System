"""Compile the C++ engine (sms_engine) with warnings enabled (Rules.md §3).

Run:  python scripts/build_cpp.py

The flags tell the whole story: -Wall -Wextra surface sloppy code, -O2
because the engine does arithmetic in loops, -std=c++14 for the modern
basics without bleeding-edge requirements. Warnings are printed and the
build is expected to stay warning-free (the project rule is 'enable and
fix', not '-Werror' — a deliberate choice so a future portability
warning can't hard-block a demo rebuild).
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "cpp_module" / "src" / "sms_engine.cpp"
BUILD_DIR = ROOT / "cpp_module" / "build"
# The .exe suffix is the only Windows/Mac difference — config.py points
# at the same relative path on every OS.
OUT_NAME = "sms_engine.exe" if sys.platform == "win32" else "sms_engine"
OUT = BUILD_DIR / OUT_NAME


def main():
    """Locate g++, compile with warnings enabled, report; exits non-zero on failure."""
    compiler = shutil.which("g++")
    if compiler is None:
        sys.exit("g++ not found on PATH. Install MinGW-w64 or TDM-GCC, then re-run.")

    if not SRC.exists():
        sys.exit(f"Source file not found: {SRC}")

    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        compiler,
        "-std=c++14",
        "-Wall",
        "-Wextra",
        "-O2",
        str(SRC),
        "-o",
        str(OUT),
    ]
    print("Compiling:", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        # gcc writes WARNINGS here (not stdout) — visible but non-fatal.
        print(result.stderr.strip())

    if result.returncode != 0:
        sys.exit(f"Compilation failed (exit code {result.returncode}).")

    print(f"Built {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
