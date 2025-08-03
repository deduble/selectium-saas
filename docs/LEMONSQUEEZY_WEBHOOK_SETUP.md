# LemonSqueezy Webhook Setup Guide

## Critical Missing Step: Webhook Configuration

You're absolutely right! The test is failing because we haven't set up the webhook in LemonSqueezy yet. This is a crucial step for the billing system to work.

## Webhook Setup Instructions

### 1. Access LemonSqueezy Webhook Settings
- Go to: https://app.lemonsqueezy.com/settings/webhooks
- Click "Create webhook"

### 2. Configure Webhook Details

**Webhook URL:**
```
http://localhost:8000/api/v1/billing/webhooks/lemon-squeezy
```

**Webhook Secret:**
```
dev-webhook-secret-selextract-2025
```
(This matches your `.env.dev` file)

**Events to Subscribe To:**
Enable these events (check all that apply):
- ✅ `subscription_created`
- ✅ `subscription_updated` 
- ✅ `subscription_cancelled`
- ✅ `subscription_resumed`
- ✅ `subscription_expired`
- ✅ `subscription_paused`
- ✅ `subscription_unpaused`
- ✅ `subscription_payment_failed`
- ✅ `subscription_payment_success`
- ✅ `subscription_payment_recovered`
- ✅ `order_created`
- ✅ `order_refunded`

### 3. Webhook URL Notes

**For Development:**
- URL: `http://localhost:8000/api/v1/billing/webhooks/lemon-squeezy`
- This only works when your API is running locally

**For Production:**
- URL: `https://yourdomain.com/api/v1/billing/webhooks/lemon-squeezy`
- Replace `yourdomain.com` with your actual domain

### 4. Test the Webhook

After setting up the webhook:

1. **Start your API** (make sure it's running on port 8000)
2. **Run the test script:**
   ```bash
   python test_end_to_end_billing.py
   ```
3. **Check LemonSqueezy webhook logs** in the dashboard to see if events are being sent

### 5. Troubleshooting

**Common Issues:**

1. **Webhook URL not reachable:**
   - Make sure your API is running on `http://localhost:8000`
   - Check firewall settings

2. **Invalid signature errors:**
   - Verify the webhook secret matches exactly: `dev-webhook-secret-selextract-2025`

3. **No events received:**
   - Check webhook is enabled in LemonSqueezy
   - Verify all subscription events are selected

### 6. Production Webhook Setup

When deploying to production:

1. **Update webhook URL** to your production domain
2. **Change webhook secret** to a secure random string
3. **Update `.env.prod`** with the new secret:
   ```
   LEMON_SQUEEZY_WEBHOOK_SECRET=your-secure-production-secret
   ```

## What This Enables

Once the webhook is configured, LemonSqueezy will automatically:
- ✅ Notify your app when subscriptions are created
- ✅ Update subscription status changes  
- ✅ Handle payment successes/failures
- ✅ Process cancellations and renewals
- ✅ Manage plan upgrades/downgrades

This is the missing piece that makes the billing system fully automated!