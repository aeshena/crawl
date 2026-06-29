#!/bin/bash
if [ ! -d "venv" ]; then
    echo "[*] Creating virtual environment..."
    python3 -m venv venv
fi

echo "[*] Activating virtual environment..."
source venv/bin/activate

echo "[*] Installing/Updating dependencies..."
pip install -r requirements.txt --quiet

echo "[*] Discovering new novels..."
python3 discover_novels.py

echo "[*] Checking for new chapters..."
python3 check_updates.py

echo "[*] Running Novel Sync..."
python sync_novels.py

echo "[*] Done."
read -p "Press enter to exit..."
