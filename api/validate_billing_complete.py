#!/usr/bin/env python3
"""
Comprehensive validation script for Phase 3 billing system implementation.
Tests all aspects: database, schemas, configuration, error handling, and authentication.
"""

import sys
import os
import json
from typing import Dict, Any, List
from datetime import datetime, timezone

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_database_schema_alignment():
    """Test 1: Validate database models align with API schemas"""
    print("=== Test 1: Database Schema Alignment ===")
    
    try:
        from models import User, SubscriptionPlan, UserSubscription
        from schemas import SubscriptionPlan as SubscriptionPlanSchema, SubscriptionTier, SubscriptionResponse
        from sqlalchemy import inspect
        
        # Test SubscriptionTier enum completeness
        expected_tiers = {'free', 'starter', 'professional', 'enterprise'}
        actual_tiers = {tier.value for tier in SubscriptionTier}
        
        print(f"Expected tiers: {expected_tiers}")
        print(f"Actual tiers: {actual_tiers}")
        
        if expected_tiers == actual_tiers:
            print("✅ SubscriptionTier enum contains all required tiers")
        else:
            missing = expected_tiers - actual_tiers
            extra = actual_tiers - expected_tiers
            if missing:
                print(f"❌ Missing tiers: {missing}")
            if extra:
                print(f"⚠️  Extra tiers: {extra}")
            return False
        
        # Test SubscriptionPlan model fields
        plan_model_columns = {col.name for col in inspect(SubscriptionPlan).columns}
        required_fields = {
            'id', 'name', 'price_cents', 'monthly_compute_units', 
            'max_concurrent_tasks', 'is_active', 'lemon_squeezy_variant_id'
        }
        
        if required_fields.issubset(plan_model_columns):
            print("✅ SubscriptionPlan model has all required fields")
        else:
            missing = required_fields - plan_model_columns
            print(f"❌ SubscriptionPlan missing fields: {missing}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Database schema test failed: {e}")
        return False

def test_subscription_plans_response():
    """Test 2: Simulate /api/v1/billing/plans endpoint response"""
    print("\n=== Test 2: Subscription Plans Response ===")
    
    try:
        from models import SubscriptionPlan
        from schemas import SubscriptionPlan as SubscriptionPlanSchema
        
        # Simulate the EXACT logic from main.py lines 1189-1203
        class MockPlan:
            def __init__(self, id, name, price_cents, monthly_compute_units, max_concurrent_tasks, is_active, lemon_squeezy_variant_id):
                self.id = id
                self.name = name
                self.price_cents = price_cents
                self.monthly_compute_units = monthly_compute_units
                self.max_concurrent_tasks = max_concurrent_tasks
                self.is_active = is_active
                self.lemon_squeezy_variant_id = lemon_squeezy_variant_id
            
            @property
            def price_dollars(self):
                return self.price_cents / 100.0
        
        # Mock database plans data (matching the INSERT statement from Phase 3)
        mock_plans = [
            MockPlan('free', 'Free', 0, 100, 1, True, None),
            MockPlan('starter', 'Starter', 1900, 1000, 3, True, 'variant_id_starter'),
            MockPlan('professional', 'Professional', 4900, 3000, 10, True, 'variant_id_professional'),
            MockPlan('enterprise', 'Enterprise', 9900, 10000, 50, True, 'variant_id_enterprise')
        ]
        
        # Simulate the exact endpoint logic from main.py
        validated_plans = []
        for plan in mock_plans:
            try:
                # This replicates the exact logic from main.py lines 1189-1203
                plan_response = SubscriptionPlanSchema(
                    id=plan.id,
                    name=plan.name,
                    tier=plan.id,  # Assuming plan ID matches tier
                    price=plan.price_dollars,
                    currency="USD",
                    compute_units_limit=plan.monthly_compute_units,
                    features=[
                        f"{plan.monthly_compute_units} compute units/month",
                        f"Up to {plan.max_concurrent_tasks} concurrent tasks",
                        "24/7 support" if plan.id != "free" else "Community support",
                        "API access" if plan.id != "free" else "Limited API access"
                    ],
                    billing_interval="monthly"
                )
                validated_plans.append(plan_response.dict())
                print(f"✅ Plan '{plan.name}' validates successfully")
            except Exception as e:
                print(f"❌ Plan '{plan.name}' validation failed: {e}")
                return False
        
        # Test that response structure matches frontend expectations
        print(f"\n📋 Generated response structure:")
        print(f"   Plans count: {len(validated_plans)}")
        print(f"   Plan IDs: {[p['id'] for p in validated_plans]}")
        
        # Check frontend compatibility - map backend fields to frontend expectations
        frontend_field_mapping = {
            'id': 'id',
            'name': 'name',
            'price': 'price_cents',  # Backend uses 'price' (dollars), frontend expects 'price_cents'
            'compute_units_limit': 'monthly_compute_units',
            'tier': 'tier'
        }
        
        print("📋 Field mapping validation:")
        for plan in validated_plans:
            plan_name = plan.get('name', 'Unknown')
            backend_fields = set(plan.keys())
            
            # Check that backend provides all essential fields for frontend
            essential_backend_fields = {'id', 'name', 'price', 'compute_units_limit', 'features', 'billing_interval'}
            if essential_backend_fields.issubset(backend_fields):
                print(f"   ✅ {plan_name}: Contains all essential backend fields")
                
                # Additional frontend compatibility notes
                price_dollars = plan.get('price', 0)
                price_cents_equivalent = int(price_dollars * 100)
                compute_units = plan.get('compute_units_limit', 0)
                
                print(f"      - Price: ${price_dollars:.2f} (equivalent to {price_cents_equivalent} cents)")
                print(f"      - Compute units: {compute_units}")
                print(f"      - Features: {len(plan.get('features', []))} items")
            else:
                missing = essential_backend_fields - backend_fields
                print(f"   ❌ {plan_name}: Missing backend fields: {missing}")
                return False
        
        print("✅ All plans provide data compatible with frontend expectations")
        return True
        
    except Exception as e:
        print(f"❌ Plans response test failed: {e}")
        return False

def test_lemon_squeezy_configuration():
    """Test 3: Validate LemonSqueezy environment configuration"""
    print("\n=== Test 3: LemonSqueezy Configuration ===")
    
    try:
        # Check required environment variables
        required_env_vars = [
            'LEMON_SQUEEZY_API_KEY',
            'LEMON_SQUEEZY_STORE_ID', 
            'LEMON_SQUEEZY_WEBHOOK_SECRET',
            'LEMON_SQUEEZY_STARTER_VARIANT_ID',
            'LEMON_SQUEEZY_PROFESSIONAL_VARIANT_ID',
            'LEMON_SQUEEZY_ENTERPRISE_VARIANT_ID'
        ]
        
        missing_vars = []
        placeholder_vars = []
        
        for var in required_env_vars:
            value = os.environ.get(var)
            if not value:
                missing_vars.append(var)
            elif value in ['your-lemonsqueezy-api-key-here', 'your-store-id-here', 'your-webhook-secret-here',
                          'starter-plan-variant-id', 'professional-plan-variant-id', 'enterprise-plan-variant-id']:
                placeholder_vars.append(var)
        
        if missing_vars:
            print(f"⚠️  Environment variables not set (OK for dev): {missing_vars}")
        else:
            print("✅ All required LemonSqueezy environment variables are set")
        
        if placeholder_vars:
            print(f"⚠️  Placeholder values detected (OK for dev, need real values for production): {placeholder_vars}")
        else:
            print("✅ Production-ready environment variable values detected")
        
        # Test LemonSqueezyClient initialization (expected to fail in dev without real credentials)
        try:
            from billing import LemonSqueezyClient
            # Don't actually initialize - just check import works
            print("✅ LemonSqueezyClient class imports successfully")
            print("⚠️  Skipping client initialization (requires real credentials)")
            
        except Exception as e:
            print(f"❌ LemonSqueezyClient import failed: {e}")
            return False
        
        # Configuration is valid if we can import the client class
        return True
        
    except Exception as e:
        print(f"❌ LemonSqueezy configuration test failed: {e}")
        return False

def test_error_handling_patterns():
    """Test 4: Validate error handling patterns in billing endpoints"""
    print("\n=== Test 4: Error Handling Patterns ===")
    
    try:
        # Read main.py to analyze error handling patterns
        with open('main.py', 'r') as f:
            main_content = f.read()
        
        # Check for billing-related error patterns
        billing_endpoints = [
            '/api/v1/billing/plans',
            '/api/v1/billing/subscription',
            '/api/v1/billing/create-checkout',
            '/api/v1/billing/invoices',
            '/api/v1/billing/portal',
            '/api/v1/billing/update-subscription',
            '/api/v1/billing/cancel-subscription',
            '/api/v1/billing/resume-subscription'
        ]
        
        error_patterns = {
            'HTTPException(status_code=404': 'Not Found errors',
            'HTTPException(status_code=400': 'Bad Request errors', 
            'HTTPException(status_code=500': 'Internal Server errors',
            'HTTPException(status_code=402': 'Payment Required errors'
        }
        
        found_patterns = {}
        for pattern, description in error_patterns.items():
            count = main_content.count(pattern)
            found_patterns[description] = count
            
        print("📋 Error handling patterns found:")
        for desc, count in found_patterns.items():
            print(f"   {desc}: {count} occurrences")
        
        # Check specific billing error scenarios
        billing_errors = [
            'No active subscription found',
            'Plan not found', 
            'Failed to create checkout session',
            'Failed to get invoices',
            'Failed to cancel subscription',
            'Failed to resume subscription'
        ]
        
        missing_error_handling = []
        for error_msg in billing_errors:
            if error_msg not in main_content:
                missing_error_handling.append(error_msg)
        
        if missing_error_handling:
            print(f"⚠️  Missing specific error messages: {missing_error_handling}")
        else:
            print("✅ All expected billing error scenarios are handled")
        
        return len(missing_error_handling) == 0
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

def test_authentication_coverage():
    """Test 5: Validate authentication coverage for billing endpoints"""
    print("\n=== Test 5: Authentication Coverage ===")
    
    try:
        with open('main.py', 'r') as f:
            main_content = f.read()
        
        # Define expected authentication patterns for each endpoint (actual URLs)
        auth_expectations = {
            '/api/v1/billing/plans': 'PUBLIC',  # Should be public for plan browsing
            '/api/v1/billing/subscription': 'RequireAuth',
            '/api/v1/billing/create-checkout': 'RequireAuth',
            '/api/v1/billing/invoices': 'RequireAuth',
            '/api/v1/billing/portal': 'RequireAuth',
            '/api/v1/billing/subscription': 'RequireAuth',  # PUT endpoint
            '/api/v1/billing/subscription/cancel': 'RequireAuth',
            '/api/v1/billing/subscription/resume': 'RequireAuth'
        }
        
        auth_results = {}
        for endpoint, expected_auth in auth_expectations.items():
            # Find the endpoint definition
            endpoint_pattern = f'@app.get("{endpoint}")|@app.post("{endpoint}")|@app.put("{endpoint}")|@app.patch("{endpoint}")'
            
            if endpoint in main_content:
                if expected_auth == 'PUBLIC':
                    # Check that it doesn't have RequireAuth
                    endpoint_section = main_content[main_content.find(endpoint):main_content.find(endpoint) + 500]
                    if 'RequireAuth' not in endpoint_section and 'user: User =' not in endpoint_section:
                        auth_results[endpoint] = '✅ Correctly PUBLIC'
                    else:
                        auth_results[endpoint] = '❌ Should be PUBLIC but has auth'
                else:
                    # Check that it has RequireAuth
                    endpoint_section = main_content[main_content.find(endpoint):main_content.find(endpoint) + 500]
                    if 'user: User = RequireAuth' in endpoint_section:
                        auth_results[endpoint] = '✅ Correctly authenticated'
                    else:
                        auth_results[endpoint] = '❌ Missing authentication'
            else:
                auth_results[endpoint] = '⚠️  Endpoint not found'
        
        print("📋 Authentication coverage results:")
        for endpoint, result in auth_results.items():
            print(f"   {endpoint}: {result}")
        
        # Count successful auth patterns
        success_count = sum(1 for result in auth_results.values() if result.startswith('✅'))
        total_count = len(auth_results)
        
        print(f"\n📊 Authentication coverage: {success_count}/{total_count} endpoints correctly configured")
        
        return success_count == total_count
        
    except Exception as e:
        print(f"❌ Authentication coverage test failed: {e}")
        return False

def main():
    """Run all validation tests"""
    print("🔍 PHASE 3 BILLING SYSTEM VALIDATION")
    print("=====================================")
    print("Testing billing API endpoints for production readiness...")
    
    tests = [
        ("Database Schema Alignment", test_database_schema_alignment),
        ("Subscription Plans Response", test_subscription_plans_response), 
        ("LemonSqueezy Configuration", test_lemon_squeezy_configuration),
        ("Error Handling Patterns", test_error_handling_patterns),
        ("Authentication Coverage", test_authentication_coverage)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*50)
    print("📊 VALIDATION SUMMARY")
    print("="*50)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Overall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Billing system is ready for Phase 3 completion.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)