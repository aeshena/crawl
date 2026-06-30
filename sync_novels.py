import os
import subprocess
import sys
import re

# --- Configuration ---
TARGET_FILE = sys.argv[1] if len(sys.argv) > 1 else "target_list.txt"   # URLs you paste manually
COMPLETED_TITLES_FILE = "completed.txt" # Your completed names
LIBRARY_FILE = "library.txt"     # Successfully downloaded URLs
OUTPUT_DIR = "downloads"
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", 5)) # Number of novels to process per run
# ---------------------

def slugify(text):
    """Normalize names to match slugs aggressively"""
    text = text.lower()
    text = re.sub(r'\.epub$', '', text)
    # Remove common words that vary between sites (the, of, etc.)
    stop_words = ['the', 'of', 'a', 'an', 'and', 'in', 'on', 'at', 'to', 'for', 'with']
    for word in stop_words:
        text = re.sub(rf'\b{word}\b', '', text)
    
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'\s+', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    text = re.sub(r'-v\d+$', '', text)
    return text

def get_completed_slugs():
    slugs = set()
    if os.path.exists(COMPLETED_TITLES_FILE):
        with open(COMPLETED_TITLES_FILE, "r", encoding="utf-8") as f:
            for line in f:
                name = line.strip()
                if name: slugs.add(slugify(name))
    return slugs

def get_library_slugs():
    slugs = set()
    if os.path.exists(LIBRARY_FILE):
        with open(LIBRARY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if "|" in line:
                    url = line.split("|")[0].strip()
                else:
                    url = line.strip()
                
                match = re.search(r'/(?:b|novel|fiction)/([^/.]+)', url)
                if match:
                    slugs.add(slugify(match.group(1)))
                else:
                    match = re.search(r'/([^/.]+)\.html$', url)
                    if match:
                        slugs.add(slugify(match.group(1)))
    return slugs

def get_blacklisted_slugs():
    """Combined blacklist for discovery scripts"""
    return get_completed_slugs().union(get_library_slugs())

def get_targets():
    if not os.path.exists(TARGET_FILE):
        return []
    with open(TARGET_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def download_novel(url, chapter_offset=0, chapter_suffix=None):
    print(f"[*] Downloading: {url}")
    if chapter_offset > 0:
        print(f"[*] Incremental update: fetching last {chapter_offset} chapters.")
    
    try:
        # Correct command for lncrawl v4.6.0
        cmd = [
            sys.executable, "-m", "lncrawl", "crawl", url,
            "--noin",
            "--format", "epub"
        ]
        
        if chapter_offset > 0:
            cmd.extend(["--last", str(chapter_offset)])
        else:
            cmd.append("--all")
        
        # Set COLUMNS environment variable to prevent lncrawl from hard-wrapping the output paths
        env_vars = os.environ.copy()
        env_vars['COLUMNS'] = '500'

        # Use subprocess.Popen to stream output in real-time
        process = subprocess.Popen(
            cmd,
            env=env_vars,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, # Merge stderr into stdout
            text=True,
            encoding='utf-8',
            errors='ignore',
            bufsize=1 # Line buffered
        )

        full_output = []
        for line in iter(process.stdout.readline, ''):
            try:
                print(line, end='', flush=True)
            except UnicodeEncodeError:
                # Fallback for Windows console not supporting Unicode box characters
                print(line.encode('ascii', 'replace').decode('ascii'), end='', flush=True) # Print to terminal as it comes
            full_output.append(line)
        
        process.wait()
        
        # Get raw output to handle path reconstruction
        raw_output = "".join(full_output)
        # Also keep a cleaned version for metadata parsing
        output_str = raw_output.replace("\n", " ").replace("\r", " ")
        output_str = re.sub(r'\s+', ' ', output_str)
        
        if process.returncode == 0:
            # Parse output for chapter count: e.g. "3 volumes, 240 chapters"
            chapter_count = 0
            count_match = re.search(r'(\d+) chapters', output_str)
            if count_match:
                chapter_count = int(count_match.group(1))

            # Parse output for the epub path
            # Strategy: Find "epub (size):" or "epub:" and capture everything until ".epub"
            match = re.search(r'epub (?:\(.+?\))?:[\s]*(.*?\.epub)', raw_output, re.IGNORECASE | re.DOTALL)
            
            if match:
                # Reconstruct path: replace newlines with spaces and collapse spaces
                # This handles terminal wrapping correctly.
                epub_path_raw = match.group(1).strip().replace("\n", " ").replace("\r", " ")
                epub_path = re.sub(r'\s+', ' ', epub_path_raw)
                
                # Fallback: if path doesn't exist, try globbing in the artifacts folder
                if not os.path.exists(epub_path):
                    print(f"[*] Path not found: {epub_path}. Searching artifacts directory...")
                    # Try to find the novel ID/folder from the path
                    dir_match = re.search(r'(.*artifacts/)', epub_path)
                    if dir_match:
                        artifacts_dir = dir_match.group(1)
                        if os.path.exists(artifacts_dir):
                            import glob
                            epubs = glob.glob(os.path.join(artifacts_dir, "*.epub"))
                            if epubs:
                                epub_path = epubs[0]
                                print(f"[*] Found file via glob: {epub_path}")

                if os.path.exists(epub_path):
                    filename = os.path.basename(epub_path)
                    
                    if chapter_suffix:
                        name, ext = os.path.splitext(filename)
                        filename = f"{name}{chapter_suffix}{ext}"
                        
                    dest_path = os.path.join(OUTPUT_DIR, filename)
                    import shutil
                    # Ensure output dir exists
                    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
                    shutil.move(epub_path, dest_path)
                    print(f"\n[+] Success! Saved to {dest_path}")
                    return True, chapter_count
                else:
                    print(f"\n[!] Located EPUB path but file does not exist: {epub_path}")
            
            print(f"\n[?] Download reported success but couldn't locate EPUB file in output.")
            return False, 0
        else:
            print(f"\n[-] Failed: {url} (Exit Code: {process.returncode})")
            return False, 0
    except Exception as e:
        print(f"\n[!] Exception: {e}")
        return False, 0

def main():
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
    
    completed_slugs = get_completed_slugs()
    
    # Load library data for offset calculation
    library_data = {}
    if os.path.exists(LIBRARY_FILE):
        with open(LIBRARY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if "|" in line:
                    url, count = line.strip().split("|")
                    library_data[url.strip()] = int(count.strip())
    
    print(f"[*] Completed: {len(completed_slugs)}, Library: {len(library_data)} entries.")

    targets = get_targets()
    if not targets:
        print(f"[*] {TARGET_FILE} is empty. No novels to download.")
        return

    to_process = []
    downloaded_urls = []
    for url in targets:
        # Extract slug for checking
        match = re.search(r'/(?:b|novel|fiction)/([^/.]+)', url)
        slug = ""
        if match:
            slug = slugify(match.group(1))
        else:
            match = re.search(r'/([^/.]+)\.html$', url)
            if match:
                slug = slugify(match.group(1))
        
        if slug and slug in completed_slugs:
            print(f"[skip] Already completed (in completed.txt): {url}")
            downloaded_urls.append(url)
            continue
        
        to_process.append(url)

    if not to_process:
        print("[*] No valid targets to process.")
        # We might still have skipped items to remove from target_list
        pass 
    else:
        print(f"[*] Found {len(to_process)} novels in queue.")
    
    count = 0
    
    for url in to_process:
        if count >= BATCH_SIZE:
            print(f"[*] Reached BATCH_SIZE ({BATCH_SIZE}). Stopping.")
            break
            
        # Calculate offset if already in library
        chapter_offset = 0
        chapter_suffix = None
        if url in library_data:
            from check_updates import get_remote_chapter_count
            remote_count = get_remote_chapter_count(url)
            local_count = library_data[url]
            
            if remote_count > local_count:
                chapter_offset = remote_count - local_count
                chapter_suffix = f"_c{local_count+1}-{remote_count}"
                print(f"[*] Update found: {local_count} -> {remote_count} (+{chapter_offset} chapters)")
            else:
                print(f"[skip] {url} is already up to date ({local_count} chapters).")
                downloaded_urls.append(url) # Mark as done to remove from target
                continue # Move to next target without incrementing 'count'

        success, chapters = download_novel(url, chapter_offset, chapter_suffix=chapter_suffix)
        if success:
            # lncrawl always reports the total chapter count in the header, 
            # so we just use that directly.
            library_data[url] = chapters
            
            downloaded_urls.append(url)
            count += 1
            
            # Save library.txt after each success
            with open(LIBRARY_FILE, "w", encoding="utf-8") as f:
                for lib_url, lib_count in library_data.items():
                    f.write(f"{lib_url} | {lib_count}\n")
        else:
            # If download fails, we still count it as a "processed" attempt for this batch?
            # Usually better to try next one if one fails, but let's increment count 
            # to avoid infinite loops on broken URLs.
            count += 1
            downloaded_urls.append(url) 
    
    # Remove downloaded URLs from target_list.txt
    if downloaded_urls:
        remaining_targets = [t for t in targets if t not in downloaded_urls]
        with open(TARGET_FILE, "w", encoding="utf-8") as f:
            for t in remaining_targets:
                f.write(t + "\n")
        print(f"[*] Updated {TARGET_FILE} (removed {len(downloaded_urls)} items).")

    print(f"\n[*] Finished. Processed {count} novels.")

if __name__ == "__main__":
    main()
