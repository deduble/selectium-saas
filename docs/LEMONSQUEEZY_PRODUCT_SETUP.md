# LemonSqueezy Product Setup Instructions

## Overview
You need to create 3 subscription products in your LemonSqueezy dashboard to complete the billing system integration. These products must match the pricing and specifications defined in your database schema.

## Step-by-Step Setup Instructions

### 1. Access Your LemonSqueezy Dashboard
- Navigate to: https://app.lemonsqueezy.com/stores/208607/products
- You should see "Do not create store" (Store ID: 208607)

### 2. Create Product 1: Selextract Starter Plan
**Click "Create Product" and configure:**
- **Product Name**: `Selextract Starter Plan`
- **Product Type**: `Subscription`
- **Billing Cycle**: `Monthly`
- **Price**: `$19.00` (USD)
- **Description**: `Perfect for individuals and small teams getting started with web scraping automation. Includes 1,000 monthly compute units and up to 3 concurrent tasks.`
- **Features** (optional):
  - 1,000 monthly compute units
  - Up to 3 concurrent tasks
  - Email support
  - Basic analytics

### 3. Create Product 2: Selextract Professional Plan
**Click "Create Product" and configure:**
- **Product Name**: `Selextract Professional Plan`
- **Product Type**: `Subscription`
- **Billing Cycle**: `Monthly`
- **Price**: `$49.00` (USD)
- **Description**: `Ideal for growing businesses with higher scraping demands. Includes 5,000 monthly compute units and up to 10 concurrent tasks.`
- **Features** (optional):
  - 5,000 monthly compute units
  - Up to 10 concurrent tasks
  - Priority email support
  - Advanced analytics
  - API access

### 4. Create Product 3: Selextract Enterprise Plan
**Click "Create Product" and configure:**
- **Product Name**: `Selextract Enterprise Plan`
- **Product Type**: `Subscription`
- **Billing Cycle**: `Monthly`
- **Price**: `$99.00` (USD)
- **Description**: `For large-scale operations requiring maximum capacity and performance. Includes 25,000 monthly compute units and up to 50 concurrent tasks.`
- **Features** (optional):
  - 25,000 monthly compute units
  - Up to 50 concurrent tasks
  - Phone + email support
  - Custom integrations
  - Dedicated account manager

## After Creating Products

### 5. Collect Variant IDs
After creating each product, LemonSqueezy will assign a unique **Variant ID** to each. You need to:

1. **Click into each product** you just created
2. **Look for the Variant ID** (usually displayed in the product details or variants section)
3. **Copy the Variant ID** for each product

The Variant IDs will look something like: `variant_123456` or similar format.

### 6. Update Environment Configuration
Once you have all 3 Variant IDs, update your `.env.dev` file:

```bash
# Replace these placeholder values with the actual Variant IDs from LemonSqueezy
LEMON_SQUEEZY_STARTER_VARIANT_ID=your_actual_starter_variant_id
LEMON_SQUEEZY_PROFESSIONAL_VARIANT_ID=your_actual_professional_variant_id
LEMON_SQUEEZY_ENTERPRISE_VARIANT_ID=your_actual_enterprise_variant_id
```

### 7. Verification
After updating the environment variables, we'll run the setup helper again to verify the products are correctly configured:

```bash
python scripts/lemonsqueezy_setup_helper.py
```

## Important Notes

- **Currency**: All prices should be in USD to match the database schema
- **Billing**: Must be set to "Monthly" recurring subscriptions
- **Naming**: Product names should match exactly as shown above for consistency
- **Variant IDs**: These are critical for the billing integration - without them, checkout flows will fail

## Troubleshooting

**If you can't find Variant IDs:**
- Look in the "Variants" section of each product
- Check the product's "Settings" or "Details" page
- The ID might be shown in the URL when viewing the product

**If products don't appear in our helper script:**
- Wait a few minutes for LemonSqueezy to sync
- Ensure products are published/active
- Verify the Store ID (208607) is correct

## Next Steps

Once you have the Variant IDs and update the `.env.dev` file, we'll:
1. Re-run the setup helper to verify configuration
2. Execute the end-to-end billing test with real LemonSqueezy integration
3. Validate the complete subscription lifecycle