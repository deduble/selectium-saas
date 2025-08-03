#!/usr/bin/env python3
"""
Test script to validate billing endpoints functionality.
Tests all critical billing endpoints to ensure they return proper data.
"""
import sys
import os
import json
import asyncio
from typing import Dict, Any, List

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import the FastAPI app and dependencies
from main import app
from database import get_db, Base
from models import User, SubscriptionPlan, UserSubscription

# Create test database engine
TEST_DATABASE_URL = "sqlite:///./test_billing.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Override the dependency
app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(app)

def setup_test_database():
    """Set up test database with required data"""
    print("Setting up test database...")
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    db = TestingSessionLocal()
    
    try:
        # Check if plans already exist
        existing_plans = db.query(SubscriptionPlan).count()
        if existing_plans > 0:
            print(f"Found {existing_plans} existing plans, skipping creation")
            return
        
        # Create subscription plans
        plans = [
            SubscriptionPlan(
                id="free",
                name="Free",
                price_cents=0,
                monthly_compute_units=100,
                max_concurrent_tasks=1,
                is_active=True,
                lemon_squeezy_variant_id=None
            ),
            SubscriptionPlan(
                id="starter",
                name="Starter",
                price_cents=1900,
                monthly_compute_units=1000,
                max_concurrent_tasks=3,
                is_active=True,
                lemon_squeezy_variant_id="variant_id_starter"
            ),
            SubscriptionPlan(
                id="professional",
                name="Professional",
                price_cents=4900,
                monthly_compute_units=5000,
                max_concurrent_tasks=10,
                is_active=True,
                lemon_squeezy_variant_id="variant_id_professional"
            ),
            SubscriptionPlan(
                id="enterprise",
                name="Enterprise",
                price_cents=9900,
                monthly_compute_units=25000,
                max_concurrent_tasks=50,
                is_active=True,
                lemon_squeezy_variant_id="variant_id_enterprise"
            )
        ]
        
        for plan in plans:
            db.add(plan)
        
        db.commit()
        print(f"Created {len(plans)} subscription plans")
        
    except Exception as e:
        print(f"Error setting up database: {e}")
        db.rollback()
    finally:
        db.close()

def test_endpoint(method: str, url: str, expected_status: int = 200, headers: Dict[str, str] = None) -> Dict[str, Any]:
    """Test an endpoint and return the result"""
    print(f"\n{'='*60}")
    print(f"Testing {method} {url}")
    print(f"{'='*60}")
    
    try:
        if method == "GET":
            response = client.get(url, headers=headers)
        elif method == "POST":
            response = client.post(url, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        print(f"Status Code: {response.status_code} (expected: {expected_status})")
        
        if response.status_code == expected_status:
            print("✅ Status code matches expected")
        else:
            print("❌ Status code does not match expected")
        
        # Try to parse JSON response
        try:
            json_data = response.json()
            print(f"Response Type: {type(json_data)}")
            
            if isinstance(json_data, list):
                print(f"Response Length: {len(json_data)} items")
                if len(json_data) > 0:
                    print("First item structure:")
                    print(json.dumps(json_data[0], indent=2, default=str))
            elif isinstance(json_data, dict):
                print("Response structure:")
                print(json.dumps(json_data, indent=2, default=str))
            
            return {
                "success": response.status_code == expected_status,
                "status_code": response.status_code,
                "data": json_data,
                "content_type": response.headers.get("content-type"),
                "error": None
            }
            
        except Exception as e:
            print(f"Could not parse JSON: {e}")
            print(f"Raw response: {response.text}")
            return {
                "success": False,
                "status_code": response.status_code,
                "data": None,
                "content_type": response.headers.get("content-type"),
                "error": f"JSON parse error: {e}",
                "raw_text": response.text
            }
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return {
            "success": False,
            "status_code": None,
            "data": None,
            "content_type": None,
            "error": str(e)
        }

def validate_subscription_plan_schema(plan: Dict[str, Any]) -> List[str]:
    """Validate subscription plan matches expected schema"""
    errors = []
    
    required_fields = ["id", "name", "tier", "price", "currency", "compute_units_limit", "features", "billing_interval"]
    
    for field in required_fields:
        if field not in plan:
            errors.append(f"Missing required field: {field}")
    
    # Validate types
    if "price" in plan and not isinstance(plan["price"], (int, float)):
        errors.append("Price should be a number")
    
    if "features" in plan and not isinstance(plan["features"], list):
        errors.append("Features should be a list")
    
    if "compute_units_limit" in plan and not isinstance(plan["compute_units_limit"], int):
        errors.append("Compute units limit should be an integer")
    
    return errors

def run_comprehensive_tests():
    """Run comprehensive endpoint tests"""
    print("🧪 Starting Comprehensive Billing Endpoint Tests")
    print("="*80)
    
    setup_test_database()
    
    # Test results storage
    results = []
    
    # Test 1: Health check (baseline)
    print("\n📋 TEST 1: Health Check (Baseline)")
    result = test_endpoint("GET", "/health")
    results.append(("Health Check", result))
    
    # Test 2: Get subscription plans (CRITICAL)
    print("\n📋 TEST 2: Get Subscription Plans (CRITICAL)")
    result = test_endpoint("GET", "/api/v1/billing/plans")
    results.append(("Billing Plans", result))
    
    # Validate plan schema if successful
    if result["success"] and result["data"]:
        print("\n🔍 Validating plan schema...")
        plans = result["data"]
        if isinstance(plans, list) and len(plans) > 0:
            for i, plan in enumerate(plans):
                errors = validate_subscription_plan_schema(plan)
                if errors:
                    print(f"❌ Plan {i+1} schema errors: {errors}")
                else:
                    print(f"✅ Plan {i+1} schema is valid")
        else:
            print("❌ Expected non-empty list of plans")
    
    # Test 3: Get subscription details (requires auth - expect 401)
    print("\n📋 TEST 3: Get Subscription Details (Auth Required)")
    result = test_endpoint("GET", "/api/v1/billing/subscription", expected_status=401)
    results.append(("Billing Subscription", result))
    
    # Test 4: Get invoices (requires auth - expect 401)
    print("\n📋 TEST 4: Get Invoices (Auth Required)")
    result = test_endpoint("GET", "/api/v1/billing/invoices", expected_status=401)
    results.append(("Billing Invoices", result))
    
    # Test 5: Resume subscription (requires auth - expect 401)
    print("\n📋 TEST 5: Resume Subscription (Auth Required)")
    result = test_endpoint("POST", "/api/v1/billing/subscription/resume", expected_status=401)
    results.append(("Resume Subscription", result))
    
    # Print summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    
    total_tests = len(results)
    passed_tests = sum(1 for _, result in results if result["success"])
    
    for test_name, result in results:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"{status} {test_name} - Status: {result['status_code']}")
        if not result["success"] and result["error"]:
            print(f"    Error: {result['error']}")
    
    print(f"\nResults: {passed_tests}/{total_tests} tests passed")
    
    # Critical validation for billing plans
    billing_plans_result = next((result for name, result in results if name == "Billing Plans"), None)
    if billing_plans_result and billing_plans_result["success"]:
        plans = billing_plans_result["data"]
        if isinstance(plans, list) and len(plans) >= 4:
            print("✅ CRITICAL: Billing plans endpoint returns expected data")
            print(f"   Found {len(plans)} plans with proper schema")
        else:
            print("❌ CRITICAL: Billing plans endpoint does not return enough plans")
    else:
        print("❌ CRITICAL: Billing plans endpoint failed")
    
    return results

if __name__ == "__main__":
    try:
        results = run_comprehensive_tests()
        
        # Exit with proper code
        failed_tests = [result for _, result in results if not result["success"]]
        if failed_tests:
            print(f"\n❌ {len(failed_tests)} tests failed")
            sys.exit(1)
        else:
            print("\n✅ All tests passed!")
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Cleanup test database
        try:
            os.remove("test_billing.db")
            print("🧹 Cleaned up test database")
        except:
            pass