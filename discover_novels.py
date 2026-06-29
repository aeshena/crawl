import os
import requests
from bs4 import BeautifulSoup
import re
from sync_novels import slugify, get_blacklisted_slugs, TARGET_FILE
import random
import time
from playwright.sync_api import sync_playwright

def discover_from_novelbin(limit=100):
    """Scrape novels from multiple lists and genres on NovelBin with pagination"""
    core_sources = [
        "https://novelbin.com/sort/top-view-novel",
        "https://novelbin.com/sort/hot-novel",
        "https://novelbin.com/sort/latest-novel"
    ]

    # Base genre URLs - we will append ?page=X for deeper discovery
    genre_bases = [
        "https://novelbin.com/genre/action", "https://novelbin.com/genre/adult", 
        "https://novelbin.com/genre/adventure", "https://novelbin.com/genre/anime-&-comics",
        "https://novelbin.com/genre/comedy", "https://novelbin.com/genre/drama",
        "https://novelbin.com/genre/eastern", "https://novelbin.com/genre/ecchi",
        "https://novelbin.com/genre/fan-fiction", "https://novelbin.com/genre/fantasy",
        "https://novelbin.com/genre/game", "https://novelbin.com/genre/gender-bender",
        "https://novelbin.com/genre/harem", "https://novelbin.com/genre/historical",
        "https://novelbin.com/genre/horror", "https://novelbin.com/genre/isekai",
        "https://novelbin.com/genre/josei", "https://novelbin.com/genre/lgbt+",
        "https://novelbin.com/genre/litrpg", "https://novelbin.com/genre/magic",
        "https://novelbin.com/genre/magical-realism", "https://novelbin.com/genre/martial-arts",
        "https://novelbin.com/genre/mature", "https://novelbin.com/genre/mecha",
        "https://novelbin.com/genre/military", "https://novelbin.com/genre/modern-life",
        "https://novelbin.com/genre/mystery", "https://novelbin.com/genre/other",
        "https://novelbin.com/genre/psychological", "https://novelbin.com/genre/reincarnation",
        "https://novelbin.com/genre/romance", "https://novelbin.com/genre/school-life",
        "https://novelbin.com/genre/sci-fi", "https://novelbin.com/genre/seinen",
        "https://novelbin.com/genre/shoujo", "https://novelbin.com/genre/shoujo-ai",
        "https://novelbin.com/genre/shounen", "https://novelbin.com/genre/shounen-ai",
        "https://novelbin.com/genre/slice-of-life", "https://novelbin.com/genre/smut",
        "https://novelbin.com/genre/sports", "https://novelbin.com/genre/supernatural",
        "https://novelbin.com/genre/system", "https://novelbin.com/genre/thriller",
        "https://novelbin.com/genre/tragedy", "https://novelbin.com/genre/urban",
        "https://novelbin.com/genre/video-games", "https://novelbin.com/genre/war",
        "https://novelbin.com/genre/wuxia", "https://novelbin.com/genre/xianxia",
        "https://novelbin.com/genre/xuanhuan", "https://novelbin.com/genre/yaoi",
        "https://novelbin.com/genre/yuri"
    ]

    random.shuffle(genre_bases)

    # Prepare sources list (core lists first, then randomized genres with pages)
    sources = []
    for base in core_sources:
        for page in range(1, 4): # Check first 3 pages of core lists
            sources.append(f"{base}?page={page}")

    for base in genre_bases:
        for page in range(1, 3): # Check first 2 pages of each genre
            sources.append(f"{base}?page={page}")

    # Expanded User-Agents to rotate
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
    ]

    blacklist = get_blacklisted_slugs()
    new_targets = []
    seen_urls = set()

    # Use a session to maintain cookies (more human-like)
    session = requests.Session()

    for url in sources:
        if len(new_targets) >= limit:
            break

        time.sleep(random.uniform(1.0, 3.0)) # Polite delay

        print(f"[*] Fetching novels from: {url}")
        try:
            headers = {
                "User-Agent": random.choice(user_agents),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://novelbin.com/",
                "Connection": "keep-alive",
                "DNT": "1",
                "Upgrade-Insecure-Requests": "1"
            }
            response = session.get(url, headers=headers, timeout=20)

            if response.status_code != 200:
                print(f"[-] Failed to fetch {url}. Status: {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', href=re.compile(r'/b/[^/]+$'))
            random.shuffle(links)

            for a in links:
                href = a.get('href')
                if not href: continue
                if href.startswith('/'): href = f"https://novelbin.com{href}"
                if href in seen_urls: continue

                match = re.search(r'/b/([^/]+)$', href)
                if not match: continue

                slug = slugify(match.group(1))
                if slug in blacklist: continue

                title = a.get('title') or a.text.strip()
                if not title: continue

                print(f"[found] New Novel: {title}")
                new_targets.append(href)
                seen_urls.add(href)

                if len(new_targets) >= limit:
                    return new_targets
        except Exception as e:
            print(f"[!] Error fetching {url}: {e}")

    return new_targets

def discover_from_empirenovel(limit=50):
    """Scrape novels from empirenovel.com using Playwright to bypass Cloudflare"""
    sources = [
        "https://empirenovel.com/novel-list",
        "https://empirenovel.com/novel-list?page=2",
        "https://empirenovel.com/novel-list?page=3"
    ]
    
    blacklist = get_blacklisted_slugs()
    new_targets = []
    seen_urls = set()

    from playwright_stealth import Stealth
    try:
        with sync_playwright() as p:
            # Use a realistic browser config but non-headless to pass Cloudflare manually if needed
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 720}
            )
            page = context.new_page()
            Stealth().apply_stealth_sync(page)

            for url in sources:
                if len(new_targets) >= limit:
                    break

                print(f"[*] Fetching novels from: {url} (Playwright)")
                
                try:
                    print("[!] Please check the browser window and solve the Cloudflare CAPTCHA if prompted. Waiting up to 60 seconds...")
                    # Wait for Cloudflare challenge to pass
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    
                    # Sometimes CF takes a few seconds to verify
                    # We can wait for a specific selector or just sleep
                    # Let's wait for any 'a' tag that looks like a novel link
                    try:
                        page.wait_for_selector('a[href*="/novel/"]', timeout=60000)
                    except Exception:
                        print("[-] Timeout waiting for novel links. Cloudflare might still be blocking or no novels found.")
                        time.sleep(2)
                        
                    # Now extract links
                    # In playwright we can evaluate JS to get links
                    links = page.evaluate('''() => {
                        return Array.from(document.querySelectorAll('a'))
                            .map(a => ({href: a.href, title: a.title || a.innerText}))
                            .filter(a => a.href.includes('/novel/'));
                    }''')
                    
                    random.shuffle(links)
                    
                    for link in links:
                        href = link['href']
                        if not href: continue
                        if href.startswith('/'): href = f"https://empirenovel.com{href}"
                        if href in seen_urls: continue

                        match = re.search(r'/novel/([^/]+)', href)
                        if not match: continue

                        slug = slugify(match.group(1))
                        if slug in blacklist: continue

                        title = link['title'].strip()
                        if not title: continue
                        
                        # Cleanup title from newlines or excess spaces
                        title = re.sub(r'\\s+', ' ', title)

                        print(f"[found] New Novel (EmpireNovel): {title}")
                        new_targets.append(href)
                        seen_urls.add(href)

                        if len(new_targets) >= limit:
                            break
                            
                except Exception as e:
                    print(f"[!] Error fetching {url}: {e}")
                    
            browser.close()
    except Exception as e:
        print(f"[!] Playwright error: {e}")
        print("[!] Ensure you have run: playwright install chromium")
        
    return new_targets

def discover_from_readnovelfull(limit=100):
    """Scrape novels from readnovelfull.com (fast, no Cloudflare)"""
    sources = [
        f"https://readnovelfull.com/novel-list/completed-novel?page={i}" for i in range(1, 20)
    ]
    
    import libsql_client
    url_db = os.environ.get('TURSO_DB_URL')
    token = os.environ.get('TURSO_AUTH_TOKEN')
    
    blacklist = set()
    if token:
        try:
            client = libsql_client.create_client_sync(url_db, auth_token=token)
            rs = client.execute("SELECT title FROM books;")
            for row in rs.rows:
                blacklist.add(slugify(str(row[0]).strip()))
        except Exception as e:
            print("DB error, falling back to local blacklist:", e)
            blacklist = get_blacklisted_slugs()
    else:
        print("Warning: TURSO_AUTH_TOKEN not set, using local completed.txt for blacklist.")
        blacklist = get_blacklisted_slugs()
    new_targets = []
    seen_urls = set()
    
    session = requests.Session()
    
    for url in sources:
        if len(new_targets) >= limit:
            break
            
        print(f"[*] Fetching novels from: {url}")
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = session.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                print(f"[-] Failed to fetch {url}. Status: {response.status_code}")
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            # Extract all links that look like a novel URL (start with /, end with .html, no 'chapter')
            links = soup.find_all('a')
            random.shuffle(links)
            
            for a in links:
                href = a.get('href')
                if not href: continue
                if not href.startswith('/'): continue
                if 'chapter' in href.lower(): continue
                if not href.endswith('.html'): continue
                
                href = f"https://readnovelfull.com{href}"
                if href in seen_urls: continue
                
                # regex to extract slug from /novel.html
                match = re.search(r'/([^/.]+)\.html$', href)
                if not match: continue
                
                slug = slugify(match.group(1))
                if slug in blacklist: continue
                
                title = a.text.strip()
                if not title: continue
                if title == 'Read now' or title == 'Read More': continue
                
                print(f"[found] New Novel (ReadNovelFull): {title}")
                new_targets.append(href)
                seen_urls.add(href)
                
                if len(new_targets) >= limit:
                    break
        except Exception as e:
            print(f"[!] Error fetching {url}: {e}")
            
    return new_targets

def main():
    existing_targets = []
    if os.path.exists(TARGET_FILE):
        with open(TARGET_FILE, "r", encoding="utf-8") as f:
            existing_targets = [line.strip() for line in f if line.strip()]

    new_novels = []

    # ReadNovelFull (Fast, reliable, works with lncrawl)
    rnf_novels = discover_from_readnovelfull(limit=100)
    new_novels.extend(rnf_novels)

    added_count = 0
    if new_novels:
        with open(TARGET_FILE, "a", encoding="utf-8") as f:
            for url in new_novels:
                if url not in existing_targets:
                    f.write(url + "\n")
                    added_count += 1
    
    print(f"\n[*] Discovery finished. Added {added_count} new novels to {TARGET_FILE}.")

if __name__ == "__main__":
    main()
