#!/usr/bin/env python3
"""Clone a Thunderbird mail account to create multiple new accounts."""

import os
import re
import sys
import glob

# Auto-detect Thunderbird profile
profile_matches = glob.glob(os.path.expanduser("~/.thunderbird/*.default-release"))
if not profile_matches:
    print("✗ No Thunderbird profile found. Launch Thunderbird first!")
    sys.exit(1)
PROFILE_PATH = profile_matches[0]
PREFS_FILE = os.path.join(PROFILE_PATH, "prefs.js")

# Source account to clone from (add this manually first!)
SOURCE_EMAIL = "deniz@mail.local"

# New accounts to create (email, password, display_name)
NEW_ACCOUNTS = [
    ("company@mail.local", "company01", "Company"),  # Main account for redirection
    ("support@mail.local", "support01", "Support"),
    ("sales@mail.local", "sales01", "Sales"),
    ("vendors@mail.local", "vendors01", "Vendors"),
    ("hr@mail.local", "hr01", "HR"),
    ("it@mail.local", "it01", "IT"),
    ("legal@mail.local", "legal01", "Legal"),
    ("promotions@mail.local", "promotions01", "Promotions"),
]

def main():
    print("⚠️  Close Thunderbird before running this script!")
    print(f"Make sure '{SOURCE_EMAIL}' account exists in Thunderbird first.")
    input("Press Enter when ready...")
    
    # Read prefs
    with open(PREFS_FILE, "r") as f:
        content = f.read()
    
    # Find source account details
    server_match = re.search(rf'mail\.server\.(server\d+)\.userName.*{re.escape(SOURCE_EMAIL)}', content)
    if not server_match:
        print(f"✗ Could not find account for {SOURCE_EMAIL}")
        print("  Add it manually in Thunderbird first!")
        sys.exit(1)
    
    source_server = server_match.group(1)
    print(f"Found source: {source_server}")
    
    # Extract all source server settings
    server_prefs = {}
    for match in re.finditer(rf'user_pref\("mail\.server\.{source_server}\.(\w+)", ([^)]+)\);', content):
        key, value = match.groups()
        server_prefs[key] = value
    
    # Find source identity
    identity_match = re.search(rf'mail\.identity\.(id\d+)\.useremail.*{re.escape(SOURCE_EMAIL)}', content)
    if identity_match:
        source_identity = identity_match.group(1)
        identity_prefs = {}
        for match in re.finditer(rf'user_pref\("mail\.identity\.{source_identity}\.(\w+)", ([^)]+)\);', content):
            key, value = match.groups()
            identity_prefs[key] = value
    else:
        identity_prefs = {}
    
    # Find source SMTP
    smtp_match = re.search(rf'mail\.smtpserver\.(smtp\d+)\.username.*{re.escape(SOURCE_EMAIL)}', content)
    if smtp_match:
        source_smtp = smtp_match.group(1)
        smtp_prefs = {}
        for match in re.finditer(rf'user_pref\("mail\.smtpserver\.{source_smtp}\.(\w+)", ([^)]+)\);', content):
            key, value = match.groups()
            smtp_prefs[key] = value
    else:
        smtp_prefs = {}
    
    # Find highest existing numbers
    all_servers = [int(x) for x in re.findall(r'mail\.server\.server(\d+)', content)]
    all_identities = [int(x) for x in re.findall(r'mail\.identity\.id(\d+)', content)]
    all_accounts = [int(x) for x in re.findall(r'mail\.account\.account(\d+)', content)]
    all_smtps = [int(x) for x in re.findall(r'mail\.smtpserver\.smtp(\d+)', content)]
    
    next_server = max(all_servers, default=0) + 1
    next_identity = max(all_identities, default=0) + 1
    next_account = max(all_accounts, default=0) + 1
    next_smtp = max(all_smtps, default=0) + 1
    
    # Generate new accounts
    new_prefs = ["\n// === Cloned accounts ===\n"]
    new_account_keys = []
    new_smtp_keys = []
    added_count = 0
    skipped_count = 0
    
    for email, password, name in NEW_ACCOUNTS:
        # Skip if account already exists
        if re.search(rf'mail\.server\.server\d+\.userName.*{re.escape(email)}', content):
            print(f"⏭ Skipping {email} (already exists)")
            skipped_count += 1
            continue
        
        srv = f"server{next_server}"
        ident = f"id{next_identity}"
        acct = f"account{next_account}"
        smtp_key = f"smtp{next_smtp}"
        
        # Clone server prefs
        for key, value in server_prefs.items():
            if key == "userName":
                value = f'"{email}"'
            elif key == "name":
                value = f'"{email}"'
            elif "spamActionTargetAccount" in key:
                continue  # Skip spam settings
            new_prefs.append(f'user_pref("mail.server.{srv}.{key}", {value});')
        
        # Clone identity prefs
        for key, value in identity_prefs.items():
            if key == "useremail":
                value = f'"{email}"'
            elif key == "fullName":
                value = f'"{name}"'
            elif key == "smtpServer":
                value = f'"{smtp_key}"'
            new_prefs.append(f'user_pref("mail.identity.{ident}.{key}", {value});')
        
        # Clone SMTP prefs
        for key, value in smtp_prefs.items():
            if key == "username":
                value = f'"{email}"'
            new_prefs.append(f'user_pref("mail.smtpserver.{smtp_key}.{key}", {value});')
        
        # Account binding
        new_prefs.append(f'user_pref("mail.account.{acct}.identities", "{ident}");')
        new_prefs.append(f'user_pref("mail.account.{acct}.server", "{srv}");')
        
        new_account_keys.append(acct)
        new_smtp_keys.append(smtp_key)
        
        print(f"✓ Cloned {email}")
        added_count += 1
        
        next_server += 1
        next_identity += 1
        next_account += 1
        next_smtp += 1
    
    if not new_account_keys:
        print("\n✓ All accounts already exist, nothing to do!")
        return
    
    # Update account list
    accounts_match = re.search(r'user_pref\("mail\.accountmanager\.accounts", "([^"]*)"\);', content)
    if accounts_match:
        old_list = accounts_match.group(1)
        new_list = old_list + "," + ",".join(new_account_keys)
        content = re.sub(
            r'user_pref\("mail\.accountmanager\.accounts", "[^"]*"\);',
            f'user_pref("mail.accountmanager.accounts", "{new_list}");',
            content
        )
    
    # Update SMTP list
    smtp_match = re.search(r'user_pref\("mail\.smtpservers", "([^"]*)"\);', content)
    if smtp_match:
        old_list = smtp_match.group(1)
        new_list = old_list + "," + ",".join(new_smtp_keys)
        content = re.sub(
            r'user_pref\("mail\.smtpservers", "[^"]*"\);',
            f'user_pref("mail.smtpservers", "{new_list}");',
            content
        )
    
    # Write back
    with open(PREFS_FILE, "w") as f:
        f.write(content)
        f.write("\n".join(new_prefs))
    
    print(f"\n✓ Added {added_count} accounts, skipped {skipped_count} existing")
    print("  Start Thunderbird and enter passwords when prompted.")

if __name__ == "__main__":
    main()
