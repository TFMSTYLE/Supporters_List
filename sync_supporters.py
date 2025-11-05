import json
import requests
import os
from github import Github

# --- CONFIGURATION ---
PATREON_TOKEN = os.getenv("PATREON_TOKEN")
CAMPAIGN_ID = os.getenv("PATREON_CAMPAIGN_ID")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

REPO_NAME = "TFMSTYLE/Supporters_List"
FILE_PATH = "supporters.json"

# Map Patreon tiers to icons
ICON_MAP = {
    "Everydays Project Supporter": "USER",
    "Everydays Project Supporter Plus+": "MOD_VERTEX_WEIGHT",
    "Everydays Project Supporter Plus++": "MONKEY",
    "Supporter": "BRUSH_DATA",
}

def fetch_patrons():
    """Fetch all active patrons and their tiers from Patreon API"""
    url = f"https://www.patreon.com/api/oauth2/v2/campaigns/{CAMPAIGN_ID}/members"
    params = {
        "include": "currently_entitled_tiers",
        "fields[member]": "full_name,patron_status",
        "fields[tier]": "title",
        "page[count]": 100
    }
    headers = {"Authorization": f"Bearer {PATREON_TOKEN}"}
    patrons = []

    while url:
        r = requests.get(url, headers=headers, params=params)
        r.raise_for_status()
        data = r.json()

        # Build a map of tier id → tier title
        tier_titles = {}
        for item in data.get("included", []):
            if item["type"] == "tier":
                tier_titles[item["id"]] = item["attributes"]["title"]

        for member in data["data"]:
            attrs = member["attributes"]
            if attrs["patron_status"] == "active_patron":
                tier_id = None
                if member["relationships"].get("currently_entitled_tiers", {}).get("data"):
                    tier_id = member["relationships"]["currently_entitled_tiers"]["data"][0]["id"]
                tier_name = tier_titles.get(tier_id, "Supporter")
                patrons.append({
                    "name": attrs["full_name"],
                    "tier": tier_name
                })

        url = data.get("links", {}).get("next")

    return patrons


def fetch_github_file():
    """Get the current supporters.json file from GitHub"""
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    file = repo.get_contents(FILE_PATH)
    current = json.loads(file.decoded_content.decode())
    return repo, file, current


def update_supporters(patrons):
    """Build supporters list compatible with supporters.json format"""
    supporters = []
    for p in patrons:
        icon = ICON_MAP.get(p["tier"], "BRUSH_DATA")
        supporters.append({
            "name": p["name"],
            "url": "",
            "icon": icon
        })
    return supporters


def commit_to_github(repo, file, new_data):
    """Commit updated JSON back to GitHub"""
    repo.update_file(
        file.path,
        "Auto-update supporters.json from Patreon",
        json.dumps(new_data, indent=4),
        file.sha
    )


if __name__ == "__main__":
    print("🔄 Fetching patrons from Patreon...")
    patrons = fetch_patrons()
    print(f"✅ Found {len(patrons)} active patrons")

    print("📂 Fetching current supporters.json from GitHub...")
    repo, file, current = fetch_github_file()

    print("🧩 Updating list...")
    updated = update_supporters(patrons)

    if updated != current:
        print("💾 Changes detected — committing update...")
        commit_to_github(repo, file, updated)
        print("✅ Supporters list updated and committed to GitHub.")
    else:
        print("✅ No changes — supporters.json is already up-to-date.")
