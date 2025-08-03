# LemonSqueezy Product Configuration Guide

## Important Note About Credits/Compute Units

**LemonSqueezy doesn't manage your "credits" or "compute units" directly.** LemonSqueezy only handles the subscription billing. The credit/compute unit allocation is managed by your Selextract application backend when it processes subscription webhooks.

## Exact LemonSqueezy Product Settings

Create these 3 products in your LemonSqueezy dashboard with **ONLY** the billing information:

### Product 1: Selextract Starter Plan
```
Product Name: Selextract Starter Plan
Product Type: Subscription  
Billing Cycle: Monthly
Price: $19.00 USD
Description: Perfect for individuals and small teams getting started with web scraping automation.
```

### Product 2: Selextract Professional Plan  
```
Product Name: Selextract Professional Plan
Product Type: Subscription
Billing Cycle: Monthly  
Price: $49.00 USD
Description: Ideal for growing businesses with higher scraping demands.
```

### Product 3: Selextract Enterprise Plan
```
Product Name: Selextract Enterprise Plan
Product Type: Subscription
Billing Cycle: Monthly
Price: $99.00 USD  
Description: For large-scale operations requiring maximum capacity and performance.
```

## How Credit Allocation Works

The credit/compute unit allocation happens **automatically** in your Selextract backend:

| Plan | Monthly Price | Compute Units | Max Concurrent Tasks |
|------|---------------|---------------|---------------------|
| **Starter** | $19.00 | 1,000 units | 3 tasks |
| **Professional** | $49.00 | 5,000 units | 10 tasks |  
| **Enterprise** | $99.00 | 25,000 units | 50 tasks |

### Backend Credit Management Process

1. **User subscribes** → LemonSqueezy sends webhook to your app
2. **Webhook processed** → [`api/webhooks.py`](../api/webhooks.py) creates/updates user subscription
3. **Credits allocated** → [`api/models.py`](../api/models.py) automatically assigns compute units based on plan
4. **Usage tracking** → [`api/compute_units.py`](../api/compute_units.py) tracks consumption

## What NOT to Configure in LemonSqueezy

❌ **Don't try to configure:**
- Credit limits
- Usage quotas  
- Compute unit allocations
- Task concurrency limits
- Usage tracking

✅ **Only configure:**
- Product name
- Subscription type
- Monthly billing cycle
- Price in USD
- Basic description

## After Creating Products

Once you create the 3 products, you'll get **Variant IDs** from LemonSqueezy that look like:
- `variant_123456` (for Starter)
- `variant_789012` (for Professional)  
- `variant_345678` (for Enterprise)

These Variant IDs are what we need to complete the integration.