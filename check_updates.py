import os
import subprocess
import sys
import re
from sync_novels import LIBRARY_FILE, TARGET_FILE

def get_remote_chapter_count(url):
    """Use lncrawl to quickly get the latest chapter count"""
    print(f"[*] Checking for updates: {url}")
    try:
        cmd = [
            sys.executable, "-m", "lncrawl", "crawl", url,
            "--noin",
            "--last", "1" # Just get the metadata and the last chapter
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        
        # Look for "X volumes, Y chapters"
        match = re.search(r'(\d+) chapters', result.stdout)
        if match:
            return int(match.group(1))
    except Exception as e:
        print(f"[-] Error checking {url}: {e}")
    return 0

def main():
    if not os.path.exists(LIBRARY_FILE):
        print(f"[*] No {LIBRARY_FILE} found. Nothing to check.")
        return

    library_data = []
    with open(LIBRARY_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if "|" in line:
                url, count = line.strip().split("|")
                library_data.append({"url": url.strip(), "count": int(count.strip())})
            else:
                # Legacy format support
                url = line.strip()
                if url:
                    library_data.append({"url": url, "count": 0})

    if not library_data:
        print("[*] Library is empty.")
        return

    print(f"[*] Scanning library for updates (limit: 5)...")
    
    updates_found = []
    
    # Randomize check order so we don't always check the same ones first
    import random
    random.shuffle(library_data)

    for item in library_data:
        if len(updates_found) >= 5:
            break
            
        url = item["url"]
        local_count = item["count"]
        
        remote_count = get_remote_chapter_count(url)
        
        if remote_count > local_count:
            print(f"[update] {url}: {local_count} -> {remote_count} chapters!")
            updates_found.append(url)
        else:
            print(f"[ok] {url}: Up to date.")

    if updates_found:
        # 1. Add to target_list.txt
        existing_targets = []
        if os.path.exists(TARGET_FILE):
            with open(TARGET_FILE, "r", encoding="utf-8") as f:
                existing_targets = [l.strip() for l in f]
        
        with open(TARGET_FILE, "a", encoding="utf-8") as f:
            for url in updates_found:
                if url not in existing_targets:
                    f.write(url + "\n")
        
        # NOTE: We DO NOT update library.txt here. 
        # sync_novels.py will update it after successful download.
            
        print(f"\n[*] Finished. Found {len(updates_found)} updates. Added to {TARGET_FILE}.")
    else:
        print("\n[*] No new chapters found.")

if __name__ == "__main__":
    main()
