#!/usr/bin/env python3
"""
Alex Voice — Conversation Server (port 3001)
============================================
Thin wrapper that runs server.py in conversation mode.

Instead of duplicating server.py (~500 lines), this wrapper:
1. Sets environment variables for conversation mode + port 3001
2. Imports and runs server.main()

This gives us an independent process with a dedicated conversation prompt,
without duplicating any code.
"""

import os, sys

# Configurar modo conversación + puerto 3001
os.environ["CONV_MODE"] = "conversation"
os.environ["PLAN_B_PORT"] = "3001"

# Pasar argumentos a server.py
sys.argv = [sys.argv[0], "--mode", "conversation", "--port", "3001"]

# Importar y ejecutar server.py
import server

if __name__ == "__main__":
    server.main()
