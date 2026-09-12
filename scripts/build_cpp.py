"""Compile the C++ engine (sms_engine) with warnings enabled (Rules.md §3).

Run:  python scripts/build_cpp.py
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "cpp_module" / "src" / "sms_engine.cpp"
BUILD_DIR = ROOT / "cpp_module" / "build"
OUT_NAME = "sms_engine.exe" if sys.platform == "win32" else "sms_engine"
OUT = BUILD_DIR / OUT_NAME


def main():
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
        print(result.stderr.strip())  # compiler warnings appear here — fix them

    if result.returncode != 0:
        sys.exit(f"Compilation failed (exit code {result.returncode}).")

    print(f"Built {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
