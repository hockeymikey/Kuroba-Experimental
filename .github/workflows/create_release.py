import os
import requests
import json
import re
import subprocess
import sys

# --- CONFIGURATION ---
# This pulls your repo name (e.g. "YourName/YourRepo") automatically from the Action
REPO_NAME = os.getenv('GITHUB_REPOSITORY') 
# Path to your APK. Check if this matches your actual build output!
ASSET_PATH = 'app/build/outputs/apk/beta/release/KurobaEx-beta.apk'
# ---------------------

def create_github_release(token, repo, tag_name, release_name, body, asset_path):
    url = f"https://api.github.com/repos/{repo}/releases"
    headers = { "Authorization": f"token {token}", "Content-Type": "application/json" }
    
    payload = {
        "tag_name": tag_name,
        "name": release_name,
        "body": body,
        "draft": False,
        "prerelease": True # Set to True since this is a beta build
    }

    print(f"Creating release {tag_name}...")
    response = requests.post(url, headers=headers, data=json.dumps(payload))

    if response.status_code != 201:
        print(f"Failed to create release. Status: {response.status_code}")
        print(response.content)
        sys.exit(1)

    print("Release created successfully.")
    upload_url = response.json()["upload_url"].split("{")[0]
    upload_asset(upload_url, asset_path, headers)

def upload_asset(upload_url, asset_path, headers):
    if not os.path.exists(asset_path):
        print(f"Error: Asset file not found at {asset_path}")
        sys.exit(1)

    headers["Content-Type"] = "application/vnd.android.package-archive"
    file_name = os.path.basename(asset_path)
    asset_url = f"{upload_url}?name={file_name}"

    print(f"Uploading {file_name}...")
    with open(asset_path, "rb") as file:
        file_data = file.read()

    response = requests.post(asset_url, headers=headers, data=file_data)
    if response.status_code != 201:
        print(f"Failed to upload asset. Status: {response.status_code}")
        sys.exit(1)
    
    print("Asset uploaded successfully.")

def get_latest_release_tag(owner_repo, token):
    url = f"https://api.github.com/repos/{owner_repo}/releases/latest"
    headers = { "Authorization": f"token {token}" }
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()['tag_name']
    else:
        return None # No releases found

def generate_next_tag(repo, token):
    current_tag = get_latest_release_tag(repo, token)
    
    # FALLBACK: If no tags exist yet, start with this one
    if not current_tag:
        print("No previous tags found. Starting v1.0.0.0-beta")
        return "v1.0.0.0-beta"

    print(f"Found previous tag: {current_tag}")
    
    # Regex to parse vX.Y.Z.N-beta
    pattern = r'v(\d+)\.(\d+)\.(\d+)\.(\d+)-beta'
    match = re.search(pattern, current_tag)
    
    if match:
        groups = list(match.groups())
        # Increment the last number
        groups[3] = str(int(groups[3]) + 1)
        new_tag = f"v{groups[0]}.{groups[1]}.{groups[2]}.{groups[3]}-beta"
        return new_tag
    else:
        # If tag format changed, just append a timestamp or fail safely
        print("Error: Previous tag format does not match vX.X.X.X-beta")
        return f"{current_tag}-next"

def get_commit_logs():
    # Gets the last 10 commits for the changelog
    cmd = ["git", "log", "-n", "10", "--pretty=format:- %s"]
    try:
        output = subprocess.check_output(cmd, text=True)
        return output
    except Exception as e:
        print(f"Error getting git logs: {e}")
        return "No changelog available."

if __name__ == "__main__":
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        print("Error: GITHUB_TOKEN is missing.")
        sys.exit(1)

    if not REPO_NAME:
        print("Error: GITHUB_REPOSITORY env var is missing.")
        sys.exit(1)

    new_tag = generate_next_tag(REPO_NAME, token)
    print(f"Calculated new tag: {new_tag}")

    commits = get_commit_logs()
    
    release_title = f"KurobaEx-beta {new_tag}"
    body = f"Automated Beta Release.\n\nChanges:\n{commits}"
    
    create_github_release(token, REPO_NAME, new_tag, release_title, body, ASSET_PATH)
