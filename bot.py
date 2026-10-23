import os
import json
import requests
from bs4 import BeautifulSoup

# FIXED: Hardcoded precisely to the gift codes layout page
URL = "https://kingshot.net/gift-codes"
HISTORY_FILE = "codes_history.txt"

def fetch_active_codes():
    print(f"Connecting directly to target page: {URL}")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(URL, headers=headers, timeout=12)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        valid_codes = []
        
        # 1. Locate the precise "Active Gift Codes" section header
        active_heading = soup.find(lambda tag: tag.name in ['h2', 'h3'] and "Active Gift Codes" in tag.text)
        
        if active_heading:
            print("Found Active section header. Scanning items inside block...")
            # 2. Sweep downwards through elements until reaching the Expired codes heading block
            current_element = active_heading.find_next()
            while current_element:
                # Instantly break the scan loop if we step past into the expired container
                if current_element.name in ['h2', 'h3'] and "Expired" in current_element.text:
                    break
                
                # Filter strictly for paragraph elements holding your font-mono text layout
                if current_element.name == "p" and "font-mono" in "".join(current_element.get("class", [])):
                    code_text = current_element.get_text().strip()
                    if code_text and code_text not in valid_codes:
                        valid_codes.append(code_text)
                
                current_element = current_element.find_next()
                
        # 3. Text Sentence Extraction Backup if visual container blocks are delayed during loading
        if not valid_codes:
            print("Layout elements empty, parsing direct text summary sentence instead...")
            page_text = soup.get_text()
            import re
            match = re.search(r'active gift codes:\s*([A-Za-z0-9,\s]+)\.', page_text, re.IGNORECASE)
            if match:
                raw_list = match.group(1).split(',')
                for item in raw_list:
                    cleaned = item.replace("and", "").strip()
                    if cleaned and cleaned.upper() not in ["ACTIVE", "EXPIRED"]:
                        valid_codes.append(cleaned)

        print(f"Verified Active Gift Codes: {valid_codes}")
        return valid_codes
        
    except Exception as e:
        print(f"Webpage connection parsing error: {e}")
        return []

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return [line.strip() for line in f.readlines()]
    return []

def save_history(all_codes):
    with open(HISTORY_FILE, "w") as f:
        for code in all_codes:
            f.write(f"{code}\n")

def send_to_discord(new_code):
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return

    payload = {
        "username": "Kingshot Code Watcher",
        "avatar_url": "https://kingshot.net",
        "content": f"🚨 **New Kingshot Gift Code Spotted!** 🚨\n\nGrab it quickly: `{new_code}`\n\n🔗 Redeem it here: [Kingshot Gift Code Center](https://kingshot.net/gift-codes)."
    }
    requests.post(webhook_url, json=payload)

def main():
    active_codes = fetch_active_codes()
    if not active_codes:
        print("No codes retrieved during this check run.")
        return

    history = load_history()
    new_discoveries = [code for code in active_codes if code not in history]

    if new_discoveries:
        print(f"Posting new findings: {new_discoveries}")
        for code in new_discoveries:
            send_to_discord(code)
            history.append(code)
        save_history(history)
        print("Discord update sequence completed.")
    else:
        print("No new active items found since previous execution loop check.")

if __name__ == "__main__":
    main()
