#!/usr/bin/env python3
"""
Debug checkout creation with LemonSqueezy API
"""
import os
import sys
import json
import requests

sys.path.append('api')

def test_checkout_creation():
    """Debug the exact checkout request being sent"""
    
    # Environment variables
    api_key = os.environ.get("LEMON_SQUEEZY_API_KEY", "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI5NGQ1OWNlZi1kYmI4LTRlYTUtYjE3OC1kMjU0MGZjZDY5MTkiLCJqdGkiOiJkMGNmMWVkMWM0MTExMTViNjQ4N2U3MWJhZDJmMWE4NmE1YzlhOTIxMzdmNzVmOTlmMmU0ODdjMWUxYTlhOTlhY2RhYmNmMTY1OTQ3YmMzYiIsImlhdCI6MTc1NDEzNzA3MS41MDYxMzQsIm5iZiI6MTc1NDEzNzA3MS41MDYxMzcsImV4cCI6MjA2OTY2OTg3MS40NjM5MSwic3ViIjoiNTI5MjQzOSIsInNjb3BlcyI6W119.EtG_8ypngz51Tp_Mx6xUf83tIWtjZia3eNO8AFGE_3jDB-irBHI6mLDljPySm7IMR7oDH01yY4fF3AGsLtR6kpDI1vmm40JNwk5I1q2stNai2mEalo3WbxfvGWVbMi_eHqgydABAWkuYIpUzUKGVMoZ9d8LVrzCvSAKJLd4vCxxMGBqycqKI6geoFqHmGxjoPeM8Vk5XlzuDkAslr7J3KhycJljb0mfl7O4qC-Auw4qRvAgkdvm481iyV1sFaeNnpNw082zlypE6nmeXmv2GPkkuauGYfXjDByr1Ed_EjHc4-r8HsJaP2N2ohZvpg5g1uc5Jd4q06ccYBo53NqkhGeJDASvyRS1mIlC09iumhh6eYHbjMXl48OitAufpA14XhQ5eAKFfkUEwhcNwTVcSauBKSC86OICpU5Y7bGbSpsdAIiaCvmMGyyAlxvaAEOzU8iggs8tsVRC9BmwVDs_2ZAwKwu8Bk0TuhaqUHmI-QSL0zIrn0DinxFyRb8PIquIZ")
    store_id = os.environ.get("LEMON_SQUEEZY_STORE_ID", "208607")
    starter_variant = os.environ.get("LEMON_SQUEEZY_STARTER_VARIANT_ID", "930404")
    
    print(f"🔍 DEBUG CHECKOUT CREATION")
    print(f"API Key: {api_key[:50]}...")
    print(f"Store ID: {store_id}")
    print(f"Testing with Starter Variant ID: {starter_variant}")
    
    # Test 1: Get variant directly to see if it exists
    print(f"\n1️⃣ Testing if variant {starter_variant} exists...")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json"
    }
    
    try:
        variant_response = requests.get(
            f"https://api.lemonsqueezy.com/v1/variants/{starter_variant}",
            headers=headers
        )
        print(f"Variant check: {variant_response.status_code}")
        if variant_response.status_code == 200:
            variant_data = variant_response.json()
            print(f"✅ Variant exists: {variant_data.get('data', {}).get('attributes', {}).get('name', 'Unknown')}")
            product_id = variant_data.get('data', {}).get('relationships', {}).get('product', {}).get('data', {}).get('id', 'Unknown')
            print(f"   Product ID: {product_id}")
            print(f"   Full response: {variant_response.text}")
        else:
            print(f"❌ Variant not found: {variant_response.text}")
            return False
    except Exception as e:
        print(f"❌ Error checking variant: {e}")
        return False
    
    # Test 2: Create checkout with exact same format as billing.py
    print(f"\n2️⃣ Testing checkout creation...")
    
    checkout_data = {
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
    
    print(f"Checkout payload:")
    print(json.dumps(checkout_data, indent=2))
    
    try:
        checkout_response = requests.post(
            "https://api.lemonsqueezy.com/v1/checkouts",
            headers=headers,
            json=checkout_data
        )
        
        print(f"Checkout response: {checkout_response.status_code}")
        print(f"Response: {checkout_response.text}")
        
        if checkout_response.status_code == 201:
            print("✅ Checkout created successfully!")
            return True
        else:
            print("❌ Checkout creation failed")
            return False
            
    except Exception as e:
        print(f"❌ Error creating checkout: {e}")
        return False

if __name__ == "__main__":
    # Load environment variables from .env.dev
    with open('.env.dev', 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value
    
    test_checkout_creation()