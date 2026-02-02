from pyngrok import ngrok
import time
import sys

# Ensure ngrok installed
# Open a HTTP tunnel on port 8501
try:
    # Need to specify protocol='http' or port=8501
    # .connect returns a NgrokTunnel object
    # If users haven't authenticated, they might get a warning or limited time, but it works for dev.
    tunnel = ngrok.connect(8501)
    print(f"PUBLIC_URL: {tunnel.public_url}")
    sys.stdout.flush()
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

# Keep alive
while True:
    time.sleep(10)
