#!/usr/bin/env python3
"""
Alex Voice — Conversation Server (port 3001)
============================================
Thin wrapper that runs server.py in conversation mode.
Conversation mode = LLM conversation + AEC (mute-while-speaking).
Shares llama-server (port 8081) with Teacher mode.

Usage:
    python conv_server.py                # → http://localhost:3001
    python conv_server.py --port 3001    # Custom port
"""

import os
import sys
import time
from pathlib import Path

# ── Structured logging ──
def log_info(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [Conversation] [INFO] {msg}")

# Set environment variables for server.py to pick up
os.environ["CONV_MODE"] = "conversation"
os.environ["PLAN_B_PORT"] = os.environ.get("PLAN_B_PORT", "3001")

# Parse --port argument
for i, arg in enumerate(sys.argv):
    if arg == "--port" and i + 1 < len(sys.argv):
        os.environ["PLAN_B_PORT"] = sys.argv[i + 1]

# Import and run server.py main()
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# Override PORT before server imports it
port = int(os.environ["PLAN_B_PORT"])

from server import main as server_main

if __name__ == "__main__":
    log_info(f"{'='*50}")
    log_info(f"  Alex Voice — Conversation Mode (port {port})")
    log_info(f"  AEC: mute-while-speaking enabled")
    log_info(f"  http://localhost:{port}")
    log_info(f"{'='*50}")
    server_main()
