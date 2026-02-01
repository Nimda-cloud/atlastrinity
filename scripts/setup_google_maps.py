#!/usr/bin/env python3
import json
import os
import random
import re
import shutil
import string
import subprocess
import sys
import time
from pathlib import Path

# --- Constants ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
REQUIRED_SERVICES = [
    "maps-backend.googleapis.com",
    "static-maps-backend.googleapis.com",
    "street-view-image-backend.googleapis.com",
    "directions-backend.googleapis.com",
    "places-backend.googleapis.com",
    "geocoding-backend.googleapis.com",
    "addressvalidation.googleapis.com" # Added for additional verification/autocomplete
]

class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"

def print_step(msg):
    print(f"{Colors.BOLD}{Colors.OKBLUE}[GCP]{Colors.ENDC} {msg}")

def print_success(msg):
    print(f"{Colors.OKGREEN}✓{Colors.ENDC} {msg}")

def print_warning(msg):
    print(f"{Colors.WARNING}⚠{Colors.ENDC} {msg}")

def print_error(msg):
    print(f"{Colors.FAIL}✗{Colors.ENDC} {msg}")

def run_command(cmd, capture_output=True, check=True):
    try:
        result = subprocess.run(cmd, capture_output=capture_output, text=True, check=check, shell=isinstance(cmd, str))
        return result
    except subprocess.CalledProcessError as e:
        if check:
            raise e
        return e

def check_gcloud():
    print_step("Checking gcloud installation...")
    if not subprocess.run(["which", "gcloud"], capture_output=True).returncode == 0:
        print_error("gcloud CLI not found. Please install Google Cloud SDK first.")
        print("Install link: https://cloud.google.com/sdk/docs/install")
        sys.exit(1)
    print_success("gcloud found")

def check_auth():
    print_step("Checking Google Cloud authentication...")
    result = run_command(["gcloud", "auth", "list", "--format=json"], check=False)
    if result.returncode != 0:
        print_info("Not authenticated. Launching browser login...")
        run_command(["gcloud", "auth", "login"], capture_output=False)
    else:
        try:
            auths = json.loads(result.stdout)
            active_auth = next((a for a in auths if a.get('active', False)), None)
            if active_auth:
                print_success(f"Authenticated as: {active_auth['account']}")
            else:
                print_info("No active account found. Launching login...")
                run_command(["gcloud", "auth", "login"], capture_output=False)
        except Exception:
            run_command(["gcloud", "auth", "login"], capture_output=False)

def get_or_create_project():
    print_step("Managing GCP Project...")
    
    # Check current project
    result = run_command(["gcloud", "config", "get-value", "project"], check=False)
    current_project = result.stdout.strip()
    
    if current_project and "(unset)" not in current_project:
        print_info(f"Current project: {Colors.BOLD}{current_project}{Colors.ENDC}")
        choice = input("Use this project? (y/n/create): ").lower()
        if choice == 'y':
            return current_project
        elif choice == 'create':
            return create_project()
    
    # List projects
    print_info("Fetching projects...")
    result = run_command(["gcloud", "projects", "list", "--format=json"])
    projects = json.loads(result.stdout)
    
    if not projects:
        print_warning("No projects found.")
        return create_project()
        
    print("\nAvailable projects:")
    for i, p in enumerate(projects):
        print(f"{i+1}) {p['projectId']} ({p['name']})")
    print(f"{len(projects)+1}) [Create New Project]")
    
    try:
        idx = int(input(f"\nSelect project (1-{len(projects)+1}): ")) - 1
        if idx == len(projects):
            return create_project()
        project_id = projects[idx]['projectId']
        run_command(["gcloud", "config", "set", "project", project_id])
        return project_id
    except (ValueError, IndexError):
        print_error("Invalid selection")
        sys.exit(1)

def create_project():
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    project_id = f"atlastrinity-maps-{suffix}"
    print_step(f"Creating new project: {project_id}...")
    run_command(["gcloud", "projects", "create", project_id, "--name=AtlasTrinity Maps"])
    run_command(["gcloud", "config", "set", "project", project_id])
    print_success(f"Project {project_id} created and set as active")
    
    print_warning("IMPORTANT: You must enable Billing for this project in the Google Cloud Console.")
    print_warning("Without billing, maps will show 'for development purposes only' watermark and be darkened.")
    print(f"URL: https://console.cloud.google.com/billing/linkedaccount?project={project_id}")
    input("\nPress Enter after you have linked a billing account to continue setup...")
    
    return project_id

def check_billing(project_id):
    """Перевірка прив'язки Білінгу до проекту"""
    print_step("Checking Billing status...")
    try:
        result = run_command(["gcloud", "billing", "projects", "describe", project_id, "--format=json"], check=False)
        if result.returncode == 0:
            billing_info = json.loads(result.stdout)
            if billing_info.get("billingEnabled"):
                print_success(f"Billing is ENABLED for project {project_id}")
                return True
        
        print_warning(f"Billing is NOT enabled for project {project_id}")
        print_info("Without billing, maps will show 'for development purposes only' watermark.")
        print(f"URL: https://console.cloud.google.com/billing/linkedaccount?project={project_id}")
        choice = input("\nDo you want to continue without billing? (y/n): ").lower()
        return choice == 'y'
    except Exception as e:
        print_warning(f"Could not verify billing status: {e}")
        return True # Continue anyway

def enable_apis(project_id):
    print_step("Verifying & Enabling required Google Maps APIs...")
    
    # Get currently enabled services to avoid redundant calls
    enabled_result = run_command(["gcloud", "services", "list", "--enabled", "--project", project_id, "--format=json"])
    enabled_names = [s['config']['name'] for s in json.loads(enabled_result.stdout)]
    
    for service in REQUIRED_SERVICES:
        if service in enabled_names:
            print_success(f"Service {service} is already enabled")
        else:
            print(f"  Enabling {service}...")
            run_command(["gcloud", "services", "enable", service, "--project", project_id])
    print_success("All required APIs enabled")

def ensure_key_unrestricted(project_id, key_name):
    """Знімає обмеження з ключа для уникнення ApiTargetBlockedMapError"""
    print_step("Optimizing API Key restrictions...")
    try:
        # We use alpha services api-keys update --clear-restrictions
        print_info(f"Clearing restrictions for key: {key_name}")
        run_command(["gcloud", "alpha", "services", "api-keys", "update", key_name, "--clear-restrictions", "--project", project_id])
        print_success("API Key restrictions cleared (Full access enabled)")
    except Exception as e:
        print_warning(f"Could not clear restrictions automatically: {e}")

def get_or_create_api_key(project_id):
    print_step("Managing API Key...")
    
    # List existing keys (requires alpha or specifically targeted list)
    # Using 'gcloud alpha services api-keys' if available, otherwise just create new one
    print_info("Checking for existing API keys...")
    
    try:
        # Try to find a key named 'AtlasTrinity Key'
        result = run_command(["gcloud", "alpha", "services", "api-keys", "list", "--project", project_id, "--format=json"], check=False)
        if result.returncode == 0:
            keys = json.loads(result.stdout)
            trinity_key = next((k for k in keys if k.get('displayName') == "AtlasTrinity Key"), None)
            if trinity_key:
                # We need to get the key string. Keys list doesn't show the actual secret easily.
                # However, we can use the 'describe' command
                key_name = trinity_key['name'] # This is long format projects/.../keys/...
                print_info("Found existing AtlasTrinity Key, retrieving value...")
                desc = run_command(["gcloud", "alpha", "services", "api-keys", "get-key-string", key_name], check=False)
                if desc.returncode == 0:
                    api_key = desc.stdout.strip().split("keyString: ")[-1]
                    # Ensure it is unrestricted
                    ensure_key_unrestricted(project_id, key_name)
                    return api_key

        print_info("Creating new API key...")
        # Create a new key
        name_result = run_command(["gcloud", "alpha", "services", "api-keys", "create", 
                                   "--display-name=AtlasTrinity Key", "--project", project_id, "--format=json"])
        key_info = json.loads(name_result.stdout)
        # The creation response might not have the key string, we might need to describe it
        # Actually gcloud alpha ... create usually returns the resource info.
        # But 'get-key-string' is most reliable for the actual AIza... string
        key_res_name = key_info['name']
        print_info("Waiting for key to propagate...")
        time.sleep(5)
        desc = run_command(["gcloud", "alpha", "services", "api-keys", "get-key-string", key_res_name])
        # Output format is usually keyString: AIza...
        api_key = desc.stdout.strip().split("keyString: ")[-1].strip()
        # Ensure it is unrestricted
        ensure_key_unrestricted(project_id, key_res_name)
        return api_key

    except Exception as e:
        print_warning(f"Could not automate API Key creation via CLI: {e}")
        print_info("Please create an API key manually at: https://console.cloud.google.com/google/maps-apis/credentials")
        api_key = input("Enter your API Key: ").strip()
        return api_key

def update_env(api_key):
    print_step("Updating .env file...")
    if not ENV_FILE.exists():
        example = PROJECT_ROOT / ".env.example"
        if example.exists():
            shutil.copy2(example, ENV_FILE)
            print_info("Created .env from .env.example")
        else:
            ENV_FILE.touch()
    
    with open(ENV_FILE) as f:
        content = f.read()
    
    key_pattern = r'^GOOGLE_MAPS_API_KEY=.*$'
    vite_key_pattern = r'^VITE_GOOGLE_MAPS_API_KEY=.*$'
    
    new_line = f"GOOGLE_MAPS_API_KEY={api_key}"
    vite_new_line = f"VITE_GOOGLE_MAPS_API_KEY={api_key}"
    
    # Update or Add GOOGLE_MAPS_API_KEY
    if re.search(key_pattern, content, re.M):
        content = re.sub(key_pattern, new_line, content, flags=re.M)
    else:
        if content and not content.endswith('\n'):
            content += '\n'
        content += new_line + '\n'

    # Update or Add VITE_GOOGLE_MAPS_API_KEY
    if re.search(vite_key_pattern, content, re.M):
        content = re.sub(vite_key_pattern, vite_new_line, content, flags=re.M)
    else:
        if content and not content.endswith('\n'):
            content += '\n'
        content += vite_new_line + '\n'
        
    with open(ENV_FILE, 'w') as f:
        f.write(content)
    print_success(".env file updated with GOOGLE_MAPS_API_KEY")

def print_info(msg):
    print(f"{Colors.OKCYAN}ℹ{Colors.ENDC} {msg}")

def main():
    print(f"\n{Colors.BOLD}{Colors.HEADER}=== AtlasTrinity Google Maps Setup ==={Colors.ENDC}\n")
    
    check_gcloud()
    check_auth()
    
    project_id = get_or_create_project()
    check_billing(project_id)
    enable_apis(project_id)
    
    api_key = get_or_create_api_key(project_id)
    if api_key:
        update_env(api_key)
        print_success("Setup completed successfully!")
    else:
        print_error("Failed to retrieve API key.")

if __name__ == "__main__":
    main()
