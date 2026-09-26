#!/usr/bin/env python3
"""
Lightweight Keep-Alive Pinger for Modal AI Endpoints.
Sends periodic GET requests to /health on Modal containers to keep them warm
for hackathon evaluation without running heavy ASR model inference or exhausting quota.
"""
import time
import urllib.request
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("KeepAlivePinger")

ENDPOINTS = [
    ("Bengali XLS-R", "https://ybtheflash--bengali-asr-asr-web.modal.run/health"),
    ("Regional Whisper", "https://ybtheflash--whisper-bengali-whisperasr-web.modal.run/health")
]

PING_INTERVAL_SECONDS = 20 * 60  # Ping every 20 minutes

def ping_endpoint(name: str, url: str):
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "B2S-KeepAlive/1.0"})
        with urllib.request.urlopen(req, timeout=25.0) as resp:
            elapsed = time.time() - t0
            logger.info(f"[{name}] AWAKE (HTTP {resp.status}) - Latency: {elapsed:.2f}s")
            return True
    except Exception as e:
        elapsed = time.time() - t0
        logger.warning(f"[{name}] Waking up or unreachable ({e}) - Elapsed: {elapsed:.2f}s")
        return False

def main():
    logger.info("Starting B2S Modal Keep-Alive Pinger...")
    logger.info(f"Target Endpoints: {[name for name, _ in ENDPOINTS]}")
    logger.info(f"Interval: {PING_INTERVAL_SECONDS // 60} minutes")
    logger.info("Safety: Calls GET /health only (Zero GPU inference quota consumed).")

    while True:
        logger.info(f"--- Running health ping at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
        for name, url in ENDPOINTS:
            ping_endpoint(name, url)

        logger.info(f"Sleeping for {PING_INTERVAL_SECONDS // 60} minutes...")
        time.sleep(PING_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
