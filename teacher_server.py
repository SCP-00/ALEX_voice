#!/usr/bin/env python3
"""
Alex Voice — Teacher Server (port 3000)
========================================
Dedicated server for Teacher mode.
LLM conversation + multi-output parsing (TEXT/PRONUNCIATION/TRANSLATION/EXPLANATION/EXERCISE).
Shares llama-server (port 8081) with Conversation mode but runs as separate process.

Usage:
    python teacher_server.py                # → http://localhost:3000
    python teacher_server.py --port 3000    # Custom port
"""

import os
import sys
import time
from pathlib import Path

# ── Structured logging ──
def log_info(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [Teacher] [INFO] {msg}")

# Set environment variables for server.py to pick up
os.environ["TEACHER_MODE"] = "teacher"
os.environ["PLAN_B_PORT"] = os.environ.get("PLAN_B_PORT", "3000")

# Parse --port argument
for i, arg in enumerate(sys.argv):
    if arg == "--port" and i + 1 < len(sys.argv):
        os.environ["PLAN_B_PORT"] = sys.argv[i + 1]

# Import and run server.py main()
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

port = int(os.environ["PLAN_B_PORT"])

from server import main as server_main

if __name__ == "__main__":
    log_info(f"{'='*50}")
    log_info(f"  Alex Voice — Teacher Mode (port {port})")
    log_info(f"  http://localhost:{port}")
    log_info(f"{'='*50}")
    server_main()
