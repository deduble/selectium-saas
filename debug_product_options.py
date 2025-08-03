#!/usr/bin/env python3
"""
Test if product_options is causing the checkout failure
"""
import os
import sys
import json
import requests

sys.path.append('api')

def test_with_and_without_product_options():
    """Test checkout creation with and without product_options"""
    
    # Load environment variables from .env.dev
    with open('.env.dev', 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value
    
    api_key = os.environ.get("LEMON_SQUEEZY_API_KEY")
    store_id = os.environ.get("LEMON_SQUEEZY_STORE_ID")
    starter_variant = os.environ.get("LEMON_SQUEEZY_STARTER_VARIANT_ID")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json"
    }
    
    # Base checkout data (like debug script - working)
    base_checkout_data = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "checkout_data": {
                    "email": "yunusemremre@gmail.com",
                    "name": "Yunus Emre",
                    "custom": {
                        "user_id": "a5d154eb-de07-499e-baa1-2c61ef7cf198",
                        "plan_id": "starter"
                    }
                },
                "checkout_options": {
                    "embed": False,
                    "media": True,
                    "logo": True,
                    "desc": True,
                    "discount": True,
                    "dark": False,
                    "subscription_preview": True,
                    "button_color": "#2563eb"
                },
                "expires_at": "2025-08-03T23:33:00.000Z",
                "preview": False,
                "test_mode": True
            },
            "relationships": {
                "store": {
                    "data": {
                        "type": "stores",
                        "id": str(store_id)
                    }
                },
                "variant": {
                    "data": {
                        "type": "variants",
                        "id": str(starter_variant)
                    }
                }
            }
        }
    }
    
    print("🧪 Test 1: WITHOUT product_options (like our working debug script)")
    try:
        response1 = requests.post(
            "https://api.lemonsqueezy.com/v1/checkouts",
            headers=headers,
            json=base_checkout_data
        )
        print(f"Response: {response1.status_code}")
        if response1.status_code != 201:
            print(f"Error: {response1.text}")
        else:
            print("✅ SUCCESS without product_options")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n🧪 Test 2: WITH product_options (like the application)")
    # Add product_options like the application does
    checkout_with_options = base_checkout_data.copy()
    checkout_with_options["data"]["attributes"]["product_options"] = {
        "redirect_url": "http://localhost:3000/billing/success"
    }
    
    print("Checkout data with product_options:")
    print(json.dumps(checkout_with_options, indent=2))
    
    try:
        response2 = requests.post(
            "https://api.lemonsqueezy.com/v1/checkouts",
            headers=headers,
            json=checkout_with_options
        )
        print(f"Response: {response2.status_code}")
        if response2.status_code != 201:
            print(f"Error: {response2.text}")
        else:
            print("✅ SUCCESS with product_options")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_with_and_without_product_options()