#!/usr/bin/env python3
"""
Debug webhook signature verification
"""
import json
import hmac
import hashlib
import requests

def test_signature_generation():
    """Test our signature generation against the API server expectations"""
    
    # Use the same secret as in .env.dev
    webhook_secret = "dev-webhook-secret-selextract-2025"
    
    # Simple test payload
    test_payload = {
        "meta": {
            "event_name": "subscription_created",
            "custom_data": {
                "user_id": "a5d154eb-de07-499e-baa1-2c61ef7cf198",
                "plan_id": "starter"
            },
            "test_mode": True
        },
        "data": {
            "id": "12345",
            "type": "subscriptions",
            "attributes": {
                "status": "active",
                "created_at": "2023-01-01T00:00:00Z",
                "renews_at": "2023-02-01T00:00:00Z",
                "variant_id": "930404"
            }
        }
    }
    
    # Convert to JSON string exactly as we send it
    payload_str = json.dumps(test_payload, separators=(',', ':'))
    print(f"Payload string: {payload_str}")
    
    # Generate signature
    signature = hmac.new(
        webhook_secret.encode('utf-8'),
        payload_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    full_signature = f"sha256={signature}"
    print(f"Generated signature: {full_signature}")
    
    # Test with API
    headers = {
        "Content-Type": "application/json",
        "X-Signature": full_signature
    }
    
    response = requests.post(
        "http://localhost:8000/api/v1/billing/webhooks/lemon-squeezy",
        data=payload_str,
        headers=headers
    )
    
    print(f"API Response: {response.status_code}")
    print(f"Response body: {response.text}")
    
    return response.status_code == 200

if __name__ == "__main__":
    print("🔍 WEBHOOK SIGNATURE DEBUG TEST")
    print("=" * 50)
    success = test_signature_generation()
    print(f"Test {'PASSED' if success else 'FAILED'}")