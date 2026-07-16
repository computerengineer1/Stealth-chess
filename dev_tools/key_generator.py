import secrets
import datetime

def generate_subscription_key(tier="MONTHLY"):
    """
    Generates a unique, secure license key.
    Format: tier_prefix - random_hex
    Example: MON-8F2E-9D2A-4C12-3B8E
    """
    prefix = "MON" # Monthly
    if tier == "3MONTHS":
        prefix = "TRM" # Tri-Month
    elif tier == "LIFETIME":
        prefix = "LFT" # Lifetime
    elif tier == "TRIAL":
        prefix = "TRL" # 1-Day Trial
        
    # Generate random unique token
    random_part = "-".join([secrets.token_hex(2) for _ in range(4)])
    key = f"{prefix}-{random_part}".upper()
    return key

if __name__ == "__main__":
    print("="*60)
    print("        Subscription & Trial Key Generator Tool")
    print("="*60)
    
    # Generate standard keys
    monthly_key = generate_subscription_key('MONTHLY')
    threemonth_key = generate_subscription_key('3MONTHS')
    lifetime_key = generate_subscription_key('LIFETIME')
    trial_key = generate_subscription_key('TRIAL')
    
    print(f"Generated Monthly Key (30 Days):   {monthly_key}")
    print(f"Generated 3-Month Key (90 Days):   {threemonth_key}")
    print(f"Generated Lifetime Key (Never):    {lifetime_key}")
    print(f"Generated 1-Day Trial Key:         {trial_key}")
    print("-"*60)
    
    # Calculate dates for copying
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    next_month = today + datetime.timedelta(days=30)
    next_three_months = today + datetime.timedelta(days=90)
    lifetime_date = datetime.date(2099, 12, 31)
    
    print("[+] Ready-to-copy entries for encrypt_licenses.py:\n")
    print(f'            "{trial_key}" : {{')
    print(f'                "tier": "Trial",')
    print(f'                "expiry": "{tomorrow.strftime("%Y-%m-%d")}"')
    print(f'            }},')
    print(f'            "{monthly_key}" : {{')
    print(f'                "tier": "Monthly",')
    print(f'                "expiry": "{next_month.strftime("%Y-%m-%d")}"')
    print(f'            }},')
    print("="*60)

