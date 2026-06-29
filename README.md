# Novel Sync

Automated tool to download light novels and sync them to Google Drive.

## Features
- Downloads novels from various sources using `lightnovel-crawler`.
- Filters out already owned or previously downloaded novels.
- Batch processing (default 5 novels per run).
- GitHub Actions integration for automated daily sync.
- Rclone integration for Google Drive upload.

## Setup
1. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies: `pip install -r requirements.txt`
3. Add novel URLs to `target_list.txt`.
4. List your existing completed novels in `completed.txt` (one per line).
5. Run the script: `python sync_novels.py`

## Configuration
- `BATCH_SIZE`: Number of novels to process per run (in `sync_novels.py`).
- `RCLONE_CONFIG_DATA`: GitHub Secret containing your rclone config.
