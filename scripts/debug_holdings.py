#!/usr/bin/env python3
"""Debug SnapTrade holdings response."""

import json
import os
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / ".env"
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

from snaptrade_client import SnapTrade

client_id = os.environ["SNAPTRADE_CLIENT_ID"]
consumer_key = os.environ["SNAPTRADE_CONSUMER_KEY"]
user_id = os.environ["SNAPTRADE_USER_ID"]
user_secret = os.environ["SNAPTRADE_USER_SECRET"]

snaptrade = SnapTrade(consumer_key=consumer_key, client_id=client_id)
ukw = {"user_id": user_id, "user_secret": user_secret}

# List accounts
print("=== ACCOUNTS ===")
accounts = snaptrade.account_information.list_user_accounts(**ukw)
print(json.dumps(accounts.body, indent=2, default=str))

# Get positions for each account
for acct in accounts.body:
    acct_id = acct.get("id") or acct.get("accountId")
    print(f"\n=== POSITIONS for account {acct_id} ===")
    try:
        pos = snaptrade.account_information.get_user_account_positions(
            account_id=acct_id, **ukw
        )
        print(json.dumps(pos.body, indent=2, default=str))
    except Exception as e:
        print(f"Error: {e}")
