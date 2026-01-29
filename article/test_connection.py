import urllib.request
import json
import socket

# Configuration
REMOTE_IP = "100.103.97.106"
REMOTE_PORT = 9222
TIMEOUT = 5  # seconds

def test_connection():
    base_url = f"http://{REMOTE_IP}:{REMOTE_PORT}"
    endpoint = f"{base_url}/json/version"
    
    print(f"🔄 Testing connection to Remote Chrome at {base_url}...")
    print(f"   (Make sure your local Chrome is started with --remote-debugging-port={REMOTE_PORT})")
    print("-" * 50)
    
    # 1. TCP Socket Test
    try:
        print(f"1. TCP Ping to {REMOTE_IP}:{REMOTE_PORT}...", end=" ", flush=True)
        sock = socket.create_connection((REMOTE_IP, REMOTE_PORT), timeout=TIMEOUT)
        sock.close()
        print("✅ Success!")
    except Exception as e:
        print(f"❌ Failed: {e}")
        print("   -> Check if Tailscale is connected on both sides.")
        print("   -> Check if Chrome is running with correct flag.")
        print("   -> Check if Windows Firewall is allowing port 9222.")
        return

    # 2. HTTP CDP Test
    try:
        print(f"2. Fetching CDP Info from {endpoint}...", end=" ", flush=True)
        with urllib.request.urlopen(endpoint, timeout=TIMEOUT) as response:
            data = json.loads(response.read().decode())
            print("✅ Success!")
            print("-" * 50)
            print("Browser Info Received:")
            print(json.dumps(data, indent=2))
            
            ws_url = data.get('webSocketDebuggerUrl')
            if ws_url:
                print(f"\n🎯 WebSocket URL found: {ws_url}")
                print("   Connection is READY for automation.")
            else:
                print("\n⚠️ No WebSocket URL found in response.")
                
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    test_connection()
