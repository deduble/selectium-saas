#!/usr/bin/env python3
"""
Verification script for the automatic development login feature.
Tests the /api/v1/auth/dev/login endpoint under different environment scenarios.
"""

import os
import sys
import requests
import json
from datetime import datetime, timezone
from jose import jwt, JWTError

# Test configuration
API_BASE_URL = "http://localhost:8000"
DEV_LOGIN_ENDPOINT = f"{API_BASE_URL}/api/v1/auth/dev/login"
DEV_USER_EMAIL = "yunusemremre@gmail.com"

# JWT configuration (matching api/auth.py)
JWT_SECRET_KEY = os.getenv("SELEXTRACT_JWT_SECRET_KEY", os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production"))
JWT_ALGORITHM = "HS256"

def print_header(title):
    """Print a formatted test section header."""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}")

def print_result(test_name, success, message=""):
    """Print test result with formatting."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {test_name}")
    if message:
        print(f"    {message}")

def verify_jwt_token(token, expected_email):
    """Verify JWT token structure and content."""
    try:
        # Decode the token
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        # Check required fields
        required_fields = ['sub', 'email', 'exp', 'iat', 'type']
        for field in required_fields:
            if field not in payload:
                return False, f"Missing required field: {field}"
        
        # Verify token type
        if payload.get('type') != 'access_token':
            return False, f"Invalid token type: {payload.get('type')}"
        
        # Verify email matches expected
        if payload.get('email') != expected_email:
            return False, f"Email mismatch. Expected: {expected_email}, Got: {payload.get('email')}"
        
        # Check expiration
        exp_timestamp = payload.get('exp')
        current_timestamp = datetime.now(timezone.utc).timestamp()
        if exp_timestamp <= current_timestamp:
            return False, "Token is expired"
        
        return True, f"Valid token for user {payload.get('email')} (ID: {payload.get('sub')})"
        
    except JWTError as e:
        return False, f"JWT decode error: {str(e)}"
    except Exception as e:
        return False, f"Token verification error: {str(e)}"

def test_development_environment():
    """Test the endpoint when SELEXTRACT_ENVIRONMENT is set to 'development'."""
    print_header("TEST 1: Development Environment")
    
    try:
        # Set environment variable for this test
        original_env = os.environ.get('SELEXTRACT_ENVIRONMENT')
        os.environ['SELEXTRACT_ENVIRONMENT'] = 'development'
        
        print(f"Making POST request to: {DEV_LOGIN_ENDPOINT}")
        print(f"Environment set to: {os.environ.get('SELEXTRACT_ENVIRONMENT')}")
        
        # Make the request
        response = requests.post(DEV_LOGIN_ENDPOINT, timeout=10)
        
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Response Data: {json.dumps(data, indent=2)}")
                
                # Verify response structure
                required_fields = ['access_token', 'token_type', 'expires_in', 'user']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    print_result("Response Structure", False, f"Missing fields: {missing_fields}")
                    return False
                
                print_result("Response Structure", True, "All required fields present")
                
                # Verify token type
                if data.get('token_type') != 'bearer':
                    print_result("Token Type", False, f"Expected 'bearer', got '{data.get('token_type')}'")
                    return False
                
                print_result("Token Type", True, "Correct token type 'bearer'")
                
                # Verify expires_in
                expires_in = data.get('expires_in')
                if not isinstance(expires_in, int) or expires_in <= 0:
                    print_result("Token Expiration", False, f"Invalid expires_in: {expires_in}")
                    return False
                
                print_result("Token Expiration", True, f"Valid expiration: {expires_in} seconds")
                
                # Verify user object
                user = data.get('user')
                if not isinstance(user, dict):
                    print_result("User Object", False, "User is not a valid object")
                    return False
                
                if user.get('email') != DEV_USER_EMAIL:
                    print_result("User Email", False, f"Expected {DEV_USER_EMAIL}, got {user.get('email')}")
                    return False
                
                print_result("User Email", True, f"Correct user email: {user.get('email')}")
                
                # Verify user subscription tier
                if user.get('subscription_tier') != 'enterprise':
                    print_result("User Subscription", False, f"Expected 'enterprise', got {user.get('subscription_tier')}")
                    return False
                
                print_result("User Subscription", True, f"Correct subscription tier: {user.get('subscription_tier')}")
                
                # Verify JWT token
                access_token = data.get('access_token')
                token_valid, token_message = verify_jwt_token(access_token, DEV_USER_EMAIL)
                print_result("JWT Token Validation", token_valid, token_message)
                
                if token_valid:
                    print_result("Development Environment Test", True, "All checks passed")
                    return True
                else:
                    return False
                
            except json.JSONDecodeError as e:
                print_result("JSON Response", False, f"Invalid JSON: {str(e)}")
                print(f"Raw Response: {response.text}")
                return False
                
        else:
            print_result("HTTP Status", False, f"Expected 200, got {response.status_code}")
            print(f"Response Text: {response.text}")
            return False
            
    except requests.RequestException as e:
        print_result("Request", False, f"Request failed: {str(e)}")
        return False
    except Exception as e:
        print_result("Test Execution", False, f"Unexpected error: {str(e)}")
        return False
    finally:
        # Restore original environment
        if original_env is not None:
            os.environ['SELEXTRACT_ENVIRONMENT'] = original_env
        elif 'SELEXTRACT_ENVIRONMENT' in os.environ:
            del os.environ['SELEXTRACT_ENVIRONMENT']

def test_production_environment():
    """Test the endpoint when SELEXTRACT_ENVIRONMENT is set to 'production'."""
    print_header("TEST 2: Production Environment Security")
    
    try:
        # Set environment variable for this test
        original_env = os.environ.get('SELEXTRACT_ENVIRONMENT')
        os.environ['SELEXTRACT_ENVIRONMENT'] = 'production'
        
        print(f"Making POST request to: {DEV_LOGIN_ENDPOINT}")
        print(f"Environment set to: {os.environ.get('SELEXTRACT_ENVIRONMENT')}")
        
        # Make the request
        response = requests.post(DEV_LOGIN_ENDPOINT, timeout=10)
        
        print(f"Response Status Code: {response.status_code}")
        
        # In production, the endpoint should not exist (404) or be forbidden (403)
        if response.status_code in [404, 405]:  # 405 = Method Not Allowed (endpoint doesn't exist)
            print_result("Security Check", True, f"Endpoint correctly unavailable in production (HTTP {response.status_code})")
            return True
        elif response.status_code == 403:
            print_result("Security Check", True, f"Endpoint correctly forbidden in production (HTTP {response.status_code})")
            return True
        else:
            print_result("Security Check", False, f"Endpoint should not be available in production, but got HTTP {response.status_code}")
            print(f"Response Text: {response.text}")
            return False
            
    except requests.RequestException as e:
        print_result("Request", False, f"Request failed: {str(e)}")
        return False
    except Exception as e:
        print_result("Test Execution", False, f"Unexpected error: {str(e)}")
        return False
    finally:
        # Restore original environment
        if original_env is not None:
            os.environ['SELEXTRACT_ENVIRONMENT'] = original_env
        elif 'SELEXTRACT_ENVIRONMENT' in os.environ:
            del os.environ['SELEXTRACT_ENVIRONMENT']

def test_health_check():
    """Test that the API is running and accessible."""
    print_header("TEST 0: API Health Check")
    
    try:
        health_url = f"{API_BASE_URL}/health"
        print(f"Checking API health at: {health_url}")
        
        response = requests.get(health_url, timeout=5)
        
        if response.status_code == 200:
            try:
                data = response.json()
                status = data.get('status', 'unknown')
                print_result("API Health", True, f"API is {status}")
                return True
            except json.JSONDecodeError:
                print_result("API Health", True, "API responded but with non-JSON content")
                return True
        else:
            print_result("API Health", False, f"Health check failed with status {response.status_code}")
            return False
            
    except requests.RequestException as e:
        print_result("API Health", False, f"Cannot connect to API: {str(e)}")
        return False

def main():
    """Run all verification tests."""
    print("🚀 Starting Development Auto-Login Verification")
    print(f"Testing against API at: {API_BASE_URL}")
    print(f"Target endpoint: {DEV_LOGIN_ENDPOINT}")
    print(f"Expected dev user: {DEV_USER_EMAIL}")
    
    # Track test results
    tests_passed = 0
    total_tests = 3
    
    # Test 0: Health check
    if test_health_check():
        tests_passed += 1
    else:
        print("\n❌ API is not accessible. Please ensure the backend is running.")
        print("   Run: ./dev/start-api.sh")
        sys.exit(1)
    
    # Test 1: Development environment
    if test_development_environment():
        tests_passed += 1
    
    # Test 2: Production environment security
    if test_production_environment():
        tests_passed += 1
    
    # Summary
    print_header("VERIFICATION SUMMARY")
    print(f"Tests Passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Development auto-login backend is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the results above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())