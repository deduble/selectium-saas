#!/usr/bin/env python3
"""
Schema Validation Script for Billing System
Validates that backend response schemas match frontend TypeScript interfaces.
"""
import sys
import json
from typing import Dict, Any, List

def validate_subscription_plan_schema(plan: Dict[str, Any]) -> List[str]:
    """
    Validate subscription plan matches frontend SubscriptionPlan interface.
    
    Expected frontend interface:
    interface SubscriptionPlan {
      id: string;
      name: string;
      tier: string;
      price: number;
      currency: string;
      compute_units_limit: number;
      features: string[];
      billing_interval: string;
      popular?: boolean;
    }
    """
    errors = []
    
    # Required fields
    required_fields = [
        "id", "name", "tier", "price", "currency", 
        "compute_units_limit", "features", "billing_interval"
    ]
    
    for field in required_fields:
        if field not in plan:
            errors.append(f"Missing required field: {field}")
    
    # Type validation
    if "id" in plan and not isinstance(plan["id"], str):
        errors.append("Field 'id' should be string")
    
    if "name" in plan and not isinstance(plan["name"], str):
        errors.append("Field 'name' should be string")
    
    if "tier" in plan and not isinstance(plan["tier"], str):
        errors.append("Field 'tier' should be string")
    
    if "price" in plan and not isinstance(plan["price"], (int, float)):
        errors.append("Field 'price' should be number")
    
    if "currency" in plan and not isinstance(plan["currency"], str):
        errors.append("Field 'currency' should be string")
    
    if "compute_units_limit" in plan and not isinstance(plan["compute_units_limit"], int):
        errors.append("Field 'compute_units_limit' should be integer")
    
    if "features" in plan and not isinstance(plan["features"], list):
        errors.append("Field 'features' should be array")
    
    if "billing_interval" in plan and not isinstance(plan["billing_interval"], str):
        errors.append("Field 'billing_interval' should be string")
    
    # Optional fields
    if "popular" in plan and not isinstance(plan["popular"], bool):
        errors.append("Field 'popular' should be boolean")
    
    return errors

def validate_invoice_schema(invoice: Dict[str, Any]) -> List[str]:
    """
    Validate invoice matches frontend Invoice interface.
    
    Expected frontend interface:
    interface Invoice {
      id: string;
      amount: number;
      currency: string;
      status: string;
      created_at: string;
      receipt_url?: string;
      invoice_url?: string;
    }
    """
    errors = []
    
    # Required fields
    required_fields = ["id", "amount", "currency", "status", "created_at"]
    
    for field in required_fields:
        if field not in invoice:
            errors.append(f"Missing required field: {field}")
    
    # Type validation
    if "id" in invoice and not isinstance(invoice["id"], str):
        errors.append("Field 'id' should be string")
    
    if "amount" in invoice and not isinstance(invoice["amount"], (int, float)):
        errors.append("Field 'amount' should be number")
    
    if "currency" in invoice and not isinstance(invoice["currency"], str):
        errors.append("Field 'currency' should be string")
    
    if "status" in invoice and not isinstance(invoice["status"], str):
        errors.append("Field 'status' should be string")
    
    if "created_at" in invoice and not isinstance(invoice["created_at"], str):
        errors.append("Field 'created_at' should be string")
    
    # Optional fields
    if "receipt_url" in invoice and invoice["receipt_url"] is not None and not isinstance(invoice["receipt_url"], str):
        errors.append("Field 'receipt_url' should be string or null")
    
    if "invoice_url" in invoice and invoice["invoice_url"] is not None and not isinstance(invoice["invoice_url"], str):
        errors.append("Field 'invoice_url' should be string or null")
    
    return errors

def test_backend_schema_generation():
    """Test that backend can generate schemas matching frontend expectations"""
    print("🧪 Testing Backend Schema Generation")
    print("="*60)
    
    # Import backend schemas
    try:
        sys.path.insert(0, '.')
        from schemas import SubscriptionPlan as SubscriptionPlanSchema
        from models import SubscriptionPlan
        print("✅ Successfully imported backend schemas")
    except Exception as e:
        print(f"❌ Failed to import backend schemas: {e}")
        return False
    
    # Test subscription plan schema generation
    print("\n📋 Testing SubscriptionPlan Schema Generation")
    
    # Create a mock plan object
    mock_plan = SubscriptionPlan(
        id="professional",
        name="Professional",
        price_cents=4900,
        monthly_compute_units=5000,
        max_concurrent_tasks=10,
        is_active=True,
        lemon_squeezy_variant_id="variant_123"
    )
    
    # Generate schema as would be done in the endpoint
    try:
        generated_plan = SubscriptionPlanSchema(
            id=mock_plan.id,
            name=mock_plan.name,
            tier=mock_plan.id,  # tier matches ID
            price=mock_plan.price_dollars,
            currency="USD",
            compute_units_limit=mock_plan.monthly_compute_units,
            features=[
                f"{mock_plan.monthly_compute_units} compute units/month",
                f"Up to {mock_plan.max_concurrent_tasks} concurrent tasks",
                "24/7 support",
                "API access"
            ],
            billing_interval="monthly"
        )
        
        # Convert to dict for validation
        plan_dict = generated_plan.dict()
        print(f"Generated plan schema: {json.dumps(plan_dict, indent=2)}")
        
        # Validate against frontend interface
        errors = validate_subscription_plan_schema(plan_dict)
        if errors:
            print(f"❌ Schema validation errors: {errors}")
            return False
        else:
            print("✅ Generated schema matches frontend interface")
            
    except Exception as e:
        print(f"❌ Failed to generate schema: {e}")
        return False
    
    return True

def validate_subscription_plan_endpoint_logic():
    """Validate the logic used in the /api/v1/billing/plans endpoint"""
    print("\n📋 Testing Billing Plans Endpoint Logic")
    
    try:
        # Import required modules
        from models import SubscriptionPlan
        from schemas import SubscriptionPlan as SubscriptionPlanSchema
        
        # Mock plans as would exist in database
        mock_plans = [
            SubscriptionPlan(
                id="free",
                name="Free",
                price_cents=0,
                monthly_compute_units=100,
                max_concurrent_tasks=1,
                is_active=True
            ),
            SubscriptionPlan(
                id="starter",
                name="Starter", 
                price_cents=1900,
                monthly_compute_units=1000,
                max_concurrent_tasks=3,
                is_active=True
            ),
            SubscriptionPlan(
                id="professional",
                name="Professional",
                price_cents=4900,
                monthly_compute_units=5000,
                max_concurrent_tasks=10,
                is_active=True
            ),
            SubscriptionPlan(
                id="enterprise",
                name="Enterprise",
                price_cents=9900,
                monthly_compute_units=25000,
                max_concurrent_tasks=50,
                is_active=True
            )
        ]
        
        # Test the endpoint logic (from main.py lines 1189-1203)
        generated_schemas = []
        for plan in mock_plans:
            schema = SubscriptionPlanSchema(
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
            generated_schemas.append(schema.dict())
        
        print(f"Generated {len(generated_schemas)} plan schemas")
        
        # Validate each generated schema
        all_valid = True
        for i, plan_dict in enumerate(generated_schemas):
            print(f"\nValidating plan {i+1}: {plan_dict['name']}")
            errors = validate_subscription_plan_schema(plan_dict)
            if errors:
                print(f"❌ Validation errors: {errors}")
                all_valid = False
            else:
                print("✅ Schema valid")
        
        if all_valid:
            print(f"\n✅ All {len(generated_schemas)} plans generate valid schemas")
            return True
        else:
            print(f"\n❌ Some plans have invalid schemas")
            return False
            
    except Exception as e:
        print(f"❌ Failed to test endpoint logic: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all schema validation tests"""
    print("🔍 Billing System Schema Validation")
    print("="*80)
    
    results = []
    
    # Test 1: Backend schema generation
    result1 = test_backend_schema_generation()
    results.append(("Backend Schema Generation", result1))
    
    # Test 2: Endpoint logic validation  
    result2 = validate_subscription_plan_endpoint_logic()
    results.append(("Endpoint Logic Validation", result2))
    
    # Summary
    print("\n" + "="*80)
    print("📊 VALIDATION SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ All schema validations passed!")
        print("✅ Backend endpoints should return data compatible with frontend")
        return True
    else:
        print(f"\n❌ {total - passed} schema validations failed")
        print("❌ Frontend may encounter compatibility issues")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Validation script failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)