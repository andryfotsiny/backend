import socket
import subprocess
import sys
from dotenv import load_dotenv
import os

load_dotenv()

PORT = int(os.getenv("PORT", 8000))

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()

if __name__ == "__main__":
    ip = get_local_ip()
    print(f"IP : {ip}")
    print(f"URL : http://{ip}:{PORT}/api/v1")
    print(f"Docs : http://{ip}:{PORT}/docs")
    subprocess.run([sys.executable, "-m", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", str(PORT)])