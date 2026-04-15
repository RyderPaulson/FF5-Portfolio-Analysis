#!/usr/bin/env python3
"""Connect your brokerage account via SnapTrade.

Usage:
    python scripts/connect_brokerage.py

Reads SNAPTRADE_CLIENT_ID, SNAPTRADE_CONSUMER_KEY, SNAPTRADE_USER_ID,
and SNAPTRADE_USER_SECRET from .env. Opens the SnapTrade connection
portal so you can link Chase (or any other supported broker).
"""

import os
import sys
import time
import webbrowser
from pathlib import Path

# Load .env from project root
env_path = Path(__file__).resolve().parent.parent / ".env"
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

from snaptrade_client import SnapTrade

client_id = os.environ.get("SNAPTRADE_CLIENT_ID", "")
consumer_key = os.environ.get("SNAPTRADE_CONSUMER_KEY", "")
user_id = os.environ.get("SNAPTRADE_USER_ID", "")
user_secret = os.environ.get("SNAPTRADE_USER_SECRET", "")

if not all([client_id, consumer_key, user_id, user_secret]):
    print("ERROR: Missing environment variables. Ensure these are set in .env:")
    print("  SNAPTRADE_CLIENT_ID")
    print("  SNAPTRADE_CONSUMER_KEY")
    print("  SNAPTRADE_USER_ID")
    print("  SNAPTRADE_USER_SECRET")
    sys.exit(1)

snaptrade = SnapTrade(consumer_key=consumer_key, client_id=client_id)

# Step 0: Verify credentials, re-register if secret is invalid
print("Verifying credentials...")
try:
    snaptrade.account_information.list_user_accounts(
        query_params={"userId": user_id, "userSecret": user_secret}
    )
    print("Credentials valid.")
except Exception as e:
    if "1083" in str(e) or "Invalid userID" in str(e):
        print(f"User secret is invalid. Cleaning up and re-registering '{user_id}'...")

        # Delete all existing users under this API key
        try:
            users_resp = snaptrade.authentication.list_snap_trade_users()
            for uid in (users_resp.body or []):
                print(f"  Deleting stale user: {uid}")
                snaptrade.authentication.delete_snap_trade_user(query_params={"userId": uid})
        except Exception:
            pass

        time.sleep(2)  # Give SnapTrade backend time to propagate the delete

        # Re-register
        try:
            register_response = snaptrade.authentication.register_snap_trade_user(
                body={"userId": user_id}
            )
            new_secret = register_response.body["userSecret"]
            user_secret = new_secret

            # Update .env automatically
            env_lines = env_path.read_text().splitlines()
            with open(env_path, "w") as f:
                for line in env_lines:
                    if line.strip().startswith("SNAPTRADE_USER_SECRET="):
                        f.write(f"SNAPTRADE_USER_SECRET={new_secret}\n")
                    else:
                        f.write(line + "\n")

            print(f"Re-registered! New user secret saved to .env.")
        except Exception as reg_err:
            print(f"ERROR: Could not re-register: {reg_err}")
            sys.exit(1)
    else:
        print(f"ERROR: {e}")
        sys.exit(1)

# Step 1: Check existing accounts
print("\nChecking for existing brokerage connections...")
try:
    accounts = snaptrade.account_information.list_user_accounts(
        query_params={"userId": user_id, "userSecret": user_secret}
    )
    if accounts.body:
        print(f"Already connected! Found {len(accounts.body)} account(s):")
        for acct in accounts.body:
            name = acct.get("name", acct.get("number", "Unknown"))
            inst = acct.get("institution_name", acct.get("brokerage", {}).get("name", "Unknown"))
            print(f"  - {name} ({inst})")
        print("\nTo add another connection, press Enter. To exit, press Ctrl+C.")
        input()
except Exception as e:
    print(f"Could not check accounts: {e}")

# Step 2: Generate connection portal link
print("Generating connection portal link...")
try:
    resp = snaptrade.authentication.login_snap_trade_user(
        query_params={"userId": user_id, "userSecret": user_secret}
    )
    url = resp.body.get("redirectURI") or resp.body.get("loginRedirectURI", "")

    if not url:
        print("ERROR: No redirect URL returned. Response:")
        print(resp.body)
        sys.exit(1)

    print(f"\nConnection portal URL:\n{url}\n")
    print("Opening in your browser...")
    webbrowser.open(url)
    print("\nAfter connecting your broker in the browser, run this script again")
    print("to verify the connection, or click 'Load from Brokerage' in the app.")

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
