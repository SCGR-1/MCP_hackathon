# test_client_fixed.py
import sys, json, subprocess, time

def start_server():
    return subprocess.Popen([sys.executable, "mcp_server.py"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, bufsize=1)

def send(proc, obj):
    proc.stdin.write(json.dumps(obj) + "\n")
    proc.stdin.flush()

def recv(proc):
    line = proc.stdout.readline()
    if not line:
        return None
    return json.loads(line)

if __name__ == "__main__":
    proc = start_server()
    time.sleep(1)

    # 1. initialize
    req = {
      "jsonrpc": "2.0",
      "id": 1,
      "method": "initialize",
      "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {
          "tools": {},
          "resources": {},
          "sampling": {},
          "roots": {"listChanged": True}
        },
        "clientInfo": {
          "name": "test-client",
          "version": "0.1",
          "title": "Test Client"
        }
      }
    }
    print("Initializing...")
    send(proc, req)
    print("Init response:", recv(proc))

    # 2. list tools
    req2 = {
      "jsonrpc": "2.0",
      "id": 2,
      "method": "tools/list",
      "params": {}
    }
    print("Listing tools...")
    send(proc, req2)
    print("List response:", recv(proc))

    # Then you can call tool if you like...
