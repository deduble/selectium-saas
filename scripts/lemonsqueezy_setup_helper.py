#!/usr/bin/env python3
"""
LemonSqueezy Setup Helper Script
Tests API connection and helps set up products/variants for Selextract billing.
"""

import os
import sys
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.dev')

def get_api_headers():
    """Get LemonSqueezy API headers"""
    api_key = os.getenv('LEMON_SQUEEZY_API_KEY')
    if not api_key:
        print("❌ Error: LEMON_SQUEEZY_API_KEY not found in environment")
        return None
    
    return {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json"
    }

def test_api_connection():
    """Test basic API connection"""
    print("🔍 Testing LemonSqueezy API connection...")
    
    headers = get_api_headers()
    if not headers:
        return False
    
    try:
        response = requests.get("https://api.lemonsqueezy.com/v1/users/me", headers=headers, timeout=10)
        
        if response.status_code == 200:
            user_data = response.json()
            user_name = user_data.get('data', {}).get('attributes', {}).get('name', 'Unknown')
            print(f"✅ API connection successful! Authenticated as: {user_name}")
            return True
        else:
            print(f"❌ API connection failed: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ API connection error: {str(e)}")
        return False

def list_stores():
    """List available stores"""
    print("\n🏪 Listing stores...")
    
    headers = get_api_headers()
    if not headers:
        return []
    
    try:
        response = requests.get("https://api.lemonsqueezy.com/v1/stores", headers=headers, timeout=10)
        
        if response.status_code == 200:
            stores_data = response.json()
            stores = stores_data.get('data', [])
            
            print(f"Found {len(stores)} store(s):")
            for store in stores:
                store_id = store['id']
                store_name = store['attributes']['name']
                store_url = store['attributes']['url']
                print(f"  📦 Store ID: {store_id} - Name: {store_name} - URL: {store_url}")
            
            return stores
        else:
            print(f"❌ Failed to list stores: {response.status_code} - {response.text}")
            return []
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error listing stores: {str(e)}")
        return []

def list_products(store_id):
    """List products for a specific store"""
    print(f"\n📦 Listing products for store {store_id}...")
    
    headers = get_api_headers()
    if not headers:
        return []
    
    try:
        url = f"https://api.lemonsqueezy.com/v1/products?filter[store_id]={store_id}"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            products_data = response.json()
            products = products_data.get('data', [])
            
            print(f"Found {len(products)} product(s):")
            for product in products:
                product_id = product['id']
                product_name = product['attributes']['name']
                product_status = product['attributes']['status']
                print(f"  🏷️  Product ID: {product_id} - Name: {product_name} - Status: {product_status}")
            
            return products
        else:
            print(f"❌ Failed to list products: {response.status_code} - {response.text}")
            return []
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error listing products: {str(e)}")
        return []

def list_variants(store_id):
    """List all variants for a specific store"""
    print(f"\n🎯 Listing variants for store {store_id}...")
    
    headers = get_api_headers()
    if not headers:
        return []
    
    try:
        url = f"https://api.lemonsqueezy.com/v1/variants?filter[store_id]={store_id}"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            variants_data = response.json()
            variants = variants_data.get('data', [])
            
            print(f"Found {len(variants)} variant(s):")
            for variant in variants:
                variant_id = variant['id']
                variant_name = variant['attributes']['name']
                variant_price = variant['attributes']['price']
                variant_status = variant['attributes']['status']
                print(f"  🏷️  Variant ID: {variant_id} - Name: {variant_name} - Price: ${variant_price/100:.2f} - Status: {variant_status}")
            
            return variants
        else:
            print(f"❌ Failed to list variants: {response.status_code} - {response.text}")
            return []
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error listing variants: {str(e)}")
        return []

def create_subscription_products(store_id):
    """Create the three subscription products needed for Selextract"""
    print(f"\n🛠️  Creating subscription products for store {store_id}...")
    
    headers = get_api_headers()
    if not headers:
        return []
    
    products_to_create = [
        {
            "name": "Selextract Starter Plan",
            "description": "Perfect for small projects and individual developers",
            "price": 1900,  # $19.00 in cents
            "billing_cycle": "month"
        },
        {
            "name": "Selextract Professional Plan", 
            "description": "Ideal for growing businesses and teams",
            "price": 4900,  # $49.00 in cents
            "billing_cycle": "month"
        },
        {
            "name": "Selextract Enterprise Plan",
            "description": "For large-scale operations and enterprise needs", 
            "price": 9900,  # $99.00 in cents
            "billing_cycle": "month"
        }
    ]
    
    created_variants = []
    
    for product_info in products_to_create:
        print(f"Creating product: {product_info['name']}...")
        
        # Create product
        product_data = {
            "data": {
                "type": "products",
                "attributes": {
                    "name": product_info["name"],
                    "description": product_info["description"],
                    "status": "published"
                },
                "relationships": {
                    "store": {
                        "data": {
                            "type": "stores",
                            "id": str(store_id)
                        }
                    }
                }
            }
        }
        
        try:
            response = requests.post("https://api.lemonsqueezy.com/v1/products", 
                                   headers=headers, json=product_data, timeout=10)
            
            if response.status_code == 201:
                product = response.json()['data']
                product_id = product['id']
                print(f"  ✅ Created product: {product_id}")
                
                # Create variant for the product
                variant_data = {
                    "data": {
                        "type": "variants",
                        "attributes": {
                            "name": product_info["name"],
                            "price": product_info["price"],
                            "is_subscription": True,
                            "interval": product_info["billing_cycle"],
                            "interval_count": 1,
                            "status": "published"
                        },
                        "relationships": {
                            "product": {
                                "data": {
                                    "type": "products",
                                    "id": str(product_id)
                                }
                            }
                        }
                    }
                }
                
                variant_response = requests.post("https://api.lemonsqueezy.com/v1/variants",
                                               headers=headers, json=variant_data, timeout=10)
                
                if variant_response.status_code == 201:
                    variant = variant_response.json()['data']
                    variant_id = variant['id']
                    print(f"  ✅ Created variant: {variant_id}")
                    created_variants.append({
                        'plan': product_info['name'].lower().split()[1],  # starter, professional, enterprise
                        'variant_id': variant_id
                    })
                else:
                    print(f"  ❌ Failed to create variant: {variant_response.status_code} - {variant_response.text}")
            else:
                print(f"  ❌ Failed to create product: {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Error creating product: {str(e)}")
    
    return created_variants

def generate_env_variables(variants):
    """Generate environment variable lines for the variants"""
    if not variants:
        print("\n⚠️  No variants to generate environment variables for.")
        return
    
    print("\n📝 Generated environment variables for .env.dev:")
    print("=" * 60)
    
    for variant_info in variants:
        plan_name = variant_info['plan'].upper()
        variant_id = variant_info['variant_id']
        print(f"LEMON_SQUEEZY_{plan_name}_VARIANT_ID={variant_id}")
    
    print("=" * 60)
    print("Copy these lines and add them to your .env.dev file!")

def main():
    """Main function to set up LemonSqueezy integration"""
    print("🍋 LemonSqueezy Setup Helper for Selextract")
    print("=" * 50)
    
    # Test API connection
    if not test_api_connection():
        print("\n❌ Cannot proceed without valid API connection.")
        sys.exit(1)
    
    # List stores
    stores = list_stores()
    if not stores:
        print("\n❌ No stores found. Please create a store in your LemonSqueezy dashboard first.")
        sys.exit(1)
    
    # Use the configured store ID
    configured_store_id = os.getenv('LEMON_SQUEEZY_STORE_ID')
    if not configured_store_id:
        print("\n❌ LEMON_SQUEEZY_STORE_ID not found in environment.")
        sys.exit(1)
    
    print(f"\n🎯 Using configured store ID: {configured_store_id}")
    
    # List existing products and variants
    existing_products = list_products(configured_store_id)
    existing_variants = list_variants(configured_store_id)
    
    if len(existing_variants) >= 3:
        print(f"\n✅ Found {len(existing_variants)} existing variants. You can use these:")
        print("Copy the variant IDs you want to use for starter/professional/enterprise plans")
        print("and add them to your .env.dev file manually.")
    else:
        print(f"\n⚠️  Only found {len(existing_variants)} variants. You need 3 for starter/professional/enterprise plans.")
        
        choice = input("\nWould you like to create the missing subscription products? (y/n): ").lower().strip()
        
        if choice == 'y':
            created_variants = create_subscription_products(configured_store_id)
            generate_env_variables(created_variants)
        else:
            print("\n💡 To manually create products:")
            print("1. Go to your LemonSqueezy dashboard")
            print("2. Navigate to Products section")
            print("3. Create 3 subscription products for starter/professional/enterprise plans")
            print("4. Note down the variant IDs and add them to .env.dev")

if __name__ == "__main__":
    main()