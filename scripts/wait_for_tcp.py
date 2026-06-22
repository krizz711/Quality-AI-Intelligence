#!/usr/bin/env python3
import os
import socket
import time
import sys

host = os.environ.get('DB_HOST', 'timescaledb')
port = int(os.environ.get('DB_PORT', '5432'))
timeout = int(os.environ.get('DB_WAIT_TIMEOUT', '60'))

deadline = time.time() + timeout
print(f"Waiting for TCP {host}:{port} (timeout={timeout}s)")
while time.time() < deadline:
    try:
        s = socket.create_connection((host, port), timeout=1)
        s.close()
        print('TCP connection succeeded')
        sys.exit(0)
    except Exception as e:
        print('TCP connect failed, retrying...', e)
        time.sleep(2)

print('Timed out waiting for TCP connection')
sys.exit(2)
