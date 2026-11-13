import os
import re
import requests
from bs4 import BeautifulSoup

URL = "https://kingshot.net/gift-codes"
HISTORY_FILE = "codes_history.txt"
CODE_PATTERN = re.compile(r"^[A-Za-z0-9]{4,40}$")
# Only inspect code-styled elements within the active section.
def _extract_codes_from_active_section(soup):
    heading = soup.find(
        lambda tag: tag.name in ("h2", "h3")
        and "active gift codes" in tag.get_text(" ", strip=True).lower()
    )
    if heading is None:
        raise ValueError("Active Gift Codes heading missing; layout may have changed")

    codes = []
    # Work only between the active heading and the start of expired/redeem help.
    for element in heading.next_elements:
        if getattr(element, "name", None) in ("h2", "h3"):
            label = element.get_text(" ", strip=True).lower()
            if "expired" in label or "how to redeem" in label:
                break
        if getattr(element, "name", None) not in ("code", "p"):
            continue
        classes = element.get("class", [])
        if element.name == "p" and not any("font-mono" in cls for cls in classes):
            continue
        # New layout can put several codes in one monospace paragraph.
        # Split on whitespace instead of announcing the entire paragraph.
        for value in element.get_text(" ", strip=True).split():
            if CODE_PATTERN.fullmatch(value) and value not in codes:
                codes.append(value)
    return codes


def fetch_active_codes():
    print(f"Checking active gift codes at {URL}")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; OTW-Kingshot-Code-Watcher/1.0)"
        }
        response = requests.get(URL, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        codes = _extract_codes_from_active_section(soup)
        if not codes:
            print("No individual code-styled elements found; skipping to avoid false alerts")
        else:
            print(f"Individual active gift codes found: {codes}")
        return codes
    except (requests.RequestException, ValueError) as error:
        print(f"Could not safely read gift codes: {error}")
        return []


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as file:
        return [line.strip() for line in file if line.strip()]


def save_history(all_codes):
    with open(HISTORY_FILE, "w", encoding="utf-8") as file:
        for code in all_codes:
            file.write(f"{code}\n")


def send_to_discord(new_code):
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("DISCORD_WEBHOOK_URL missing; not posting")
        return False

    payload = {
        "username": "Kingshot Code Watcher",
        "content": (
            f"🚨 **New Kingshot Gift Code Spotted!** 🚨\n\n"
            f"Grab it quickly: `{new_code}`\n\n"
            f"🔗 Redeem it here: [Kingshot Gift Code Center]({URL})."
        ),
    }
    try:
        response = requests.post(webhook_url, json=payload, timeout=15)
        response.raise_for_status()
        return True
    except requests.RequestException as error:
        print(f"Discord webhook failed for {new_code}: {error}")
        return False


def main():
    active_codes = fetch_active_codes()
    if not active_codes:
        print("No safe codes retrieved; leaving history unchanged")
        return

    history = load_history()
    known = set(history)
    new_codes = [code for code in active_codes if code not in known]

    if not new_codes:
        print("No new active codes")
        return

    for code in new_codes:
        if send_to_discord(code):
            history.append(code)
            known.add(code)
            # Persist only successful notifications.
            save_history(history)


if __name__ == "__main__":
    main()
