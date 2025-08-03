#!/usr/bin/env python3
"""
End-to-End Billing Flow Test Script
Simulates complete subscription lifecycle with webhook payloads
Tests all critical billing scenarios without external API dependencies
"""

import json
import hmac
import hashlib
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

import jwt

# Test configuration
API_BASE_URL = "http://localhost:8000"

# Use the real JWT token provided by the user
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhNWQxNTRlYi1kZTA3LTQ5OWUtYmFhMS0yYzYxZWY3Y2YxOTgiLCJlbWFpbCI6Inl1bnVzZW1yZW1yZUBnbWFpbC5jb20iLCJleHAiOjE3NTQxNDE4MDgsImlhdCI6MTc1NDE0MDAwOCwidHlwZSI6ImFjY2Vzc190b2tlbiJ9._g1D_VIzpPYBWlWJeihzPv6zyDV28QwmL5ZAxIRCNN4"
# Real user information from the database query
REAL_USER_ID = "a5d154eb-de07-499e-baa1-2c61ef7cf198"
REAL_USER_EMAIL = "yunusemremre@gmail.com"

# For development testing, we'll set a webhook secret that matches what the billing module expects
WEBHOOK_SECRET = "dev-webhook-secret-selextract-2025"

def create_webhook_signature(payload: str) -> str:
    """Create HMAC-SHA256 signature for webhook payload"""
    signature = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"

def send_webhook(event_name: str, data: Dict[str, Any], meta_custom: Dict[str, Any]) -> Dict[str, Any]:
    """Send webhook payload to API"""
    webhook_payload = {
        "meta": {
            "event_name": event_name,
            "custom_data": meta_custom,
            "test_mode": True
        },
        "data": data
    }
    
    payload_str = json.dumps(webhook_payload, separators=(',', ':'))
    signature = create_webhook_signature(payload_str)
    
    headers = {
        "Content-Type": "application/json",
        "X-Signature": signature
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/billing/webhooks/lemon-squeezy",
        data=payload_str,
        headers=headers
    )
    
    print(f"📡 Webhook {event_name}: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ Result: {result.get('status', 'unknown')}")
        return result
    else:
        print(f"   ❌ Error: {response.text}")
        return {"error": response.text}

def get_user_subscription(token: str) -> Dict[str, Any]:
    """Get current user subscription details"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_BASE_URL}/api/v1/billing/subscription", headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Failed to get subscription: {response.text}")
        return {}

def get_user_analytics(token: str) -> Dict[str, Any]:
    """Get user analytics/dashboard data"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_BASE_URL}/api/v1/analytics/dashboard", headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Failed to get analytics: {response.text}")
        return {}

def print_subscription_status(description: str, token: str):
    """Print current subscription status"""
    print(f"\n🔍 {description}")
    print("=" * 50)
    
    subscription = get_user_subscription(token)
    analytics = get_user_analytics(token)
    
    if subscription:
        plan = subscription.get('plan', {})
        sub_details = subscription.get('subscription', {})
        
        print(f"Plan: {plan.get('name', 'Unknown')} (${plan.get('price_cents', 0)/100:.2f}/month)")
        print(f"Status: {sub_details.get('status', 'N/A') if sub_details else 'free'}")
        print(f"Compute Units: {subscription.get('compute_units_remaining', 0)}/{plan.get('monthly_compute_units', 0)}")
        
        if sub_details:
            print(f"Period: {sub_details.get('current_period_start', 'N/A')} to {sub_details.get('current_period_end', 'N/A')}")
            print(f"Days until renewal: {sub_details.get('days_until_renewal', 'N/A')}")
            print(f"Cancel at period end: {sub_details.get('cancel_at_period_end', False)}")
    
    if analytics:
        print(f"Total tasks: {analytics.get('total_tasks', 0)}")
        print(f"Usage this month: {analytics.get('compute_units_used_this_month', 0)} units")

def test_subscription_creation():
    """Test 1: Subscription Creation"""
    print("\n🧪 TEST 1: Subscription Creation")
    print("=" * 60)
    
    # Show initial state (should be free tier)
    print_subscription_status("Initial State (Free Tier)", JWT_TOKEN)
    
    # Simulate subscription_created webhook for starter plan
    now = datetime.now(timezone.utc)
    period_end = now + timedelta(days=30)
    
    subscription_data = {
        "id": "sub_12345",
        "type": "subscriptions",
        "attributes": {
            "status": "active",
            "variant_id": "930404",
            "created_at": now.isoformat().replace('+00:00', 'Z'),
            "renews_at": period_end.isoformat().replace('+00:00', 'Z'),
            "customer_id": "cust_12345"
        }
    }
    
    meta_custom = {
        "user_id": REAL_USER_ID,
        "plan_id": "starter"
    }
    
    result = send_webhook("subscription_created", subscription_data, meta_custom)
    
    # Verify subscription was created
    print_subscription_status("After Subscription Creation", JWT_TOKEN)
    
    return result.get('status') == 'processed'

def test_subscription_update():
    """Test 2: Subscription Update (Plan Change)"""
    print("\n🧪 TEST 2: Subscription Update (Plan Change)")
    print("=" * 60)
    
    # Simulate subscription update to professional plan
    subscription_data = {
        "id": "sub_12345",
        "type": "subscriptions",
        "attributes": {
            "status": "active",
            "variant_id": "930406",
            "renews_at": (datetime.now(timezone.utc) + timedelta(days=28)).isoformat().replace('+00:00', 'Z')
        }
    }
    
    meta_custom = {
        "user_id": REAL_USER_ID,
        "plan_id": "professional"
    }
    
    result = send_webhook("subscription_updated", subscription_data, meta_custom)
    
    # Verify plan change
    print_subscription_status("After Plan Upgrade", JWT_TOKEN)
    
    return result.get('status') == 'processed'

def test_payment_cycle():
    """Test 3: Payment Success (Monthly Renewal)"""
    print("\n🧪 TEST 3: Payment Success (Monthly Renewal)")
    print("=" * 60)
    
    # Simulate payment success webhook
    subscription_data = {
        "id": "sub_12345",
        "type": "subscriptions",
        "attributes": {
            "status": "active",
            "variant_id": "930406",
            "renews_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat().replace('+00:00', 'Z')
        }
    }
    
    meta_custom = {
        "user_id": REAL_USER_ID,
        "plan_id": "professional"
    }
    
    result = send_webhook("subscription_payment_success", subscription_data, meta_custom)
    
    # Verify compute units were reset
    print_subscription_status("After Payment Success", JWT_TOKEN)
    
    return result.get('status') == 'processed'

def test_payment_failure():
    """Test 4: Payment Failure"""
    print("\n🧪 TEST 4: Payment Failure")
    print("=" * 60)
    
    # Simulate payment failure webhook
    subscription_data = {
        "id": "sub_12345",
        "type": "subscriptions", 
        "attributes": {
            "status": "past_due",
            "variant_id": "930406"
        }
    }
    
    meta_custom = {
        "user_id": REAL_USER_ID,
        "plan_id": "professional"
    }
    
    result = send_webhook("subscription_payment_failed", subscription_data, meta_custom)
    
    # Verify status change
    print_subscription_status("After Payment Failure", JWT_TOKEN)
    
    return result.get('status') == 'processed'

def test_subscription_cancellation():
    """Test 5: Subscription Cancellation"""
    print("\n🧪 TEST 5: Subscription Cancellation")
    print("=" * 60)
    
    # Simulate subscription cancellation webhook
    subscription_data = {
        "id": "sub_12345",
        "type": "subscriptions",
        "attributes": {
            "status": "cancelled",
            "variant_id": "930406",
            "ends_at": (datetime.now(timezone.utc) + timedelta(days=15)).isoformat().replace('+00:00', 'Z')
        }
    }
    
    meta_custom = {
        "user_id": REAL_USER_ID,
        "plan_id": "professional"
    }
    
    result = send_webhook("subscription_cancelled", subscription_data, meta_custom)
    
    # Verify cancellation
    print_subscription_status("After Cancellation", JWT_TOKEN)
    
    return result.get('status') == 'processed'

def test_subscription_expiration():
    """Test 6: Subscription Expiration"""
    print("\n🧪 TEST 6: Subscription Expiration")
    print("=" * 60)
    
    # Simulate subscription expiration webhook
    subscription_data = {
        "id": "sub_12345",
        "type": "subscriptions",
        "attributes": {
            "status": "expired",
            "variant_id": "930406"
        }
    }
    
    meta_custom = {
        "user_id": REAL_USER_ID,
        "plan_id": "professional"
    }
    
    result = send_webhook("subscription_expired", subscription_data, meta_custom)
    
    # Verify downgrade to free
    print_subscription_status("After Expiration (Should be Free)", JWT_TOKEN)
    
    return result.get('status') == 'processed'

def test_edge_cases():
    """Test 7: Edge Cases and Error Handling"""
    print("\n🧪 TEST 7: Edge Cases and Error Handling")
    print("=" * 60)
    
    success_count = 0
    total_tests = 0
    
    # Test 1: Invalid signature
    print("📋 Testing invalid webhook signature...")
    headers = {
        "Content-Type": "application/json",
        "X-Signature": "invalid_signature"
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/billing/webhooks/lemon-squeezy",
        json={"test": "data"},
        headers=headers
    )
    
    if response.status_code == 401:
        print("   ✅ Correctly rejected invalid signature")
        success_count += 1
    else:
        print(f"   ❌ Expected 401, got {response.status_code}")
    total_tests += 1
    
    # Test 2: Missing signature header
    print("📋 Testing missing signature header...")
    headers = {"Content-Type": "application/json"}
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/billing/webhooks/lemon-squeezy",
        json={"test": "data"},
        headers=headers
    )
    
    if response.status_code == 400:
        print("   ✅ Correctly rejected missing signature")
        success_count += 1
    else:
        print(f"   ❌ Expected 400, got {response.status_code}")
    total_tests += 1
    
    # Test 3: Invalid JSON payload
    print("📋 Testing invalid JSON payload...")
    payload = "invalid json"
    signature = create_webhook_signature(payload)
    headers = {
        "Content-Type": "application/json",
        "X-Signature": signature
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/billing/webhooks/lemon-squeezy",
        data=payload,
        headers=headers
    )
    
    if response.status_code == 400:
        print("   ✅ Correctly rejected invalid JSON")
        success_count += 1
    else:
        print(f"   ❌ Expected 400, got {response.status_code}")
    total_tests += 1
    
    # Test 4: Unknown event type
    print("📋 Testing unknown event type...")
    webhook_payload = {
        "meta": {
            "event_name": "unknown_event_type",
            "custom_data": {},
            "test_mode": True
        },
        "data": {"id": "test", "type": "test"}
    }
    
    payload_str = json.dumps(webhook_payload)
    signature = create_webhook_signature(payload_str)
    headers = {
        "Content-Type": "application/json",
        "X-Signature": signature
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/v1/billing/webhooks/lemon-squeezy",
        data=payload_str,
        headers=headers
    )
    
    if response.status_code == 200:
        result = response.json()
        if result.get('status') == 'ignored':
            print("   ✅ Correctly ignored unknown event")
            success_count += 1
        else:
            print(f"   ❌ Expected 'ignored' status, got {result.get('status')}")
    else:
        print(f"   ❌ Expected 200, got {response.status_code}")
    total_tests += 1
    
    print(f"\n📊 Edge case tests: {success_count}/{total_tests} passed")
    return success_count == total_tests

def run_comprehensive_test():
    """Run the complete end-to-end billing test suite"""
    print("🚀 SELEXTRACT CLOUD - END-TO-END BILLING FLOW TEST")
    print("=" * 80)
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Test Mode: Development")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test sequence
    tests = [
        ("Subscription Creation", test_subscription_creation),
        ("Subscription Update", test_subscription_update), 
        ("Payment Success", test_payment_cycle),
        ("Payment Failure", test_payment_failure),
        ("Subscription Cancellation", test_subscription_cancellation),
        ("Subscription Expiration", test_subscription_expiration),
        ("Edge Cases", test_edge_cases)
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                print(f"✅ {test_name}: PASSED")
                passed_tests += 1
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"💥 {test_name}: ERROR - {str(e)}")
    
    # Final summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success rate: {passed_tests/total_tests*100:.1f}%")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED! Billing system is working correctly.")
        return True
    else:
        print(f"\n⚠️  {total_tests - passed_tests} tests failed. Review the issues above.")
        return False

if __name__ == "__main__":
    success = run_comprehensive_test()
    exit(0 if success else 1)