import os
import json
import requests

# Connecting directly to the internal data center feed where the codes are stored
URL = "https://kingshot.net"
HISTORY_FILE = "codes_history.txt"

def fetch_active_codes():
    print("Connecting directly to Kingshot data feed...")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }
        response = requests.get(URL, headers=headers, timeout=12)
        
        valid_codes = []
        if response.status_code == 200:
            data = response.json()
            items = data.get("codes", data.get("active", data)) if isinstance(data, dict) else data
            
            if isinstance(items, list):
                for item in items:
                    code_text = ""
                    if isinstance(item, dict):
                        code_text = item.get("code", item.get("value", item.get("name", "")))
                        status = item.get("status", "active").lower()
                        if status != "active":
                            continue
                    else:
                        code_text = str(item)
                        
                    cleaned = code_text.strip()
                    if cleaned and len(cleaned) <= 20:  # Expanded character limit length for longer store codes
                        valid_codes.append(cleaned)
                        
                if valid_codes:
                    print(f"API Extraction successful! Found: {valid_codes}")
                    return valid_codes

        # DYNAMIC BACKUP: Scrapes the text of the webpage directly if the custom API block resets
        print("API structured extraction empty. Scraping direct text strings...")
        html_response = requests.get("https://kingshot.net/gift-codes", headers=headers, timeout=12)
        import re
        # Pulls any alphanumeric word between 6 and 20 characters that looks like a store promo code
        found_words = re.findall(r'\b(OFFICIALSTORE\d+|KINGSHOT\d+|VIP\d+|[A-Z0-9]{6,20})\b', html_response.text, re.IGNORECASE)
        for word in found_words:
            cleaned_word = word.strip()
            if cleaned_word.upper() not in ["ACTIVE", "EXPIRED", "VERSION", "TOTAL"]:
                if cleaned_word not in valid_codes:
                    valid_codes.append(cleaned_word)
                    
        return valid_codes
        
    except Exception as e:
        print(f"Direct feed access tracking failed: {e}")
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
        print("Error: DISCORD_WEBHOOK_URL is missing.")
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
        print("No active codes found.")
        return

    history = load_history()
    new_discoveries = [code for code in active_codes if code not in history]

    if new_discoveries:
        print(f"Posting newly discovered items: {new_discoveries}")
        for code in new_discoveries:
            send_to_discord(code)
            history.append(code)
        save_history(history)
        print("Discord update sequence completed successfully.")
    else:
        print("All codes discovered are already logged inside historical tracking memory.")

if __name__ == "__main__":
    main()
