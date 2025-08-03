### Getting Started with Lemon Squeezy Documentation
Lemon Squeezy offers comprehensive documentation to help you integrate their billing system into your application. Below, you'll find a breakdown of how to implement checkout sessions, handle webhooks, manage subscriptions, and integrate the customer portal, ensuring your billing integration aligns with their latest API specifications.

#### Checkout Sessions
To create checkout sessions, use the `POST /v1/checkouts` endpoint. This allows you to generate a URL for customers to purchase products or subscriptions. You can pre-fill customer information, set custom pricing, and customize product details. For example, include the store and variant IDs, and optionally add customer email and name in the `checkout_data` field.

- **Example URL**: [Lemon Squeezy Taking Payments Guide](https://docs.lemonsqueezy.com/guides/developer-guide/taking-payments)

#### Webhook Handling
Webhooks keep your application updated with store events like order creation or subscription renewals. Set up an endpoint to receive POST requests, configure it via the dashboard at [Settings » Webhooks](https://app.lemonsqueezy.com/settings/webhooks) or the `POST /v1/webhooks` API, and verify requests using the `X-Signature` header to ensure security.

- **Example URL**: [Webhooks Guide](https://docs.lemonsqueezy.com/guides/developer-guide/webhooks)

#### Subscription Management
Manage subscriptions using endpoints like `PATCH /v1/subscriptions/{id}` for updates (e.g., changing plans), `DELETE /v1/subscriptions/{id}` for cancellations, and options for pausing or resuming. Handle proration by setting `"invoice_immediately": true` or disabling it with `"disable_prorations": true`.

- **Example URL**: [Subscription Management Guide](https://docs.lemonsqueezy.com/guides/developer-guide/managing-subscriptions)

#### Customer Portal Integration
The customer portal lets customers manage subscriptions and billing. Provide a signed URL (valid for 24 hours) via `GET /v1/subscriptions/{id}` or use an unsigned URL like `[invalid url, do not cite]`. Customize the portal through the dashboard at [Design » Customer Portal](https://app.lemonsqueezy.com/design/customer-portal).

- **Example URL**: [Customer Portal Guide](https://docs.lemonsqueezy.com/guides/developer-guide/customer-portal)

---

---

### Detailed Survey Note on Lemon Squeezy Billing Integration

This survey note provides an in-depth exploration of implementing Lemon Squeezy's billing integration, focusing on checkout sessions, webhook handling, subscription management, and customer portal integration, based on the latest API specifications as of July 30, 2025. The information is derived from official documentation and guides, ensuring accuracy and relevance for developers seeking to integrate these features.

#### Introduction to Lemon Squeezy API
Lemon Squeezy's API is a RESTful service adhering to JSON:API specifications, accessible at `https://api.lemonsqueezy.com/v1/`. All requests require HTTPS and authentication via a Bearer token, created in the dashboard at [Settings » API](https://app.lemonsqueezy.com/settings/api). Headers must include `Accept: application/vnd.api+json`, `Content-Type: application/vnd.api+json`, and `Authorization: Bearer {api_key}`. The API supports test mode for development, ensuring no impact on live data until you're ready to go live.

The API covers store management, including products, customers, discounts, and files, with capabilities like creating checkout links, managing subscriptions, and handling license keys. Responses follow JSON:API standards, including object data and relationships, as seen in example order objects.

#### Checkout Sessions: Detailed Implementation
Checkout sessions are crucial for initiating purchases, and Lemon Squeezy provides a robust API for this purpose. The primary endpoint is `POST /v1/checkouts`, requiring relationships to a store and variant. For instance, to create a basic checkout:

- **Required Fields**: `store` (e.g., ID "2") and `variant` (e.g., ID "2").
- **Optional Customizations**:
  - Pre-fill customer info via `checkout_data`, e.g., `{"email": "[email protected]", "name": "John Doe"}`.
  - Pass custom data for webhooks in `checkout_data.custom`, e.g., `{"custom": {"user_id": 123}}`.
  - Set custom pricing with `custom_price`, e.g., `{"custom_price": 599}` (excluding tax).
  - Override product details with `product_options`, e.g., `{"name": "Unique subscription for Dave", "redirect_url": "https://myapp.com/welcome/?user=dave123"}`.
  - Set expiration with `expires_at`, e.g., `{"expires_at": "2023-04-30T23:59:59.000000Z"}`.

Checkout URLs follow the structure `https://[STORE].lemonsqueezy.com/checkout/buy/[VARIANT_ID]`, and cart URLs (single-use, non-shareable) use `/checkout/?cart=`. Pre-fill fields can also be passed via URL parameters like `checkout[email]` for email or `checkout[discount_code]` for discounts. Customization options include query params like `embed=1` for embedded checkouts or `button_color=%23111111` for styling.

For a seamless experience, use Lemon.js (2.3kB library) by including the script from `/help/lemonjs` and using `LemonSqueezy.Url.Open(checkoutUrl)` for overlays. Documentation emphasizes not self-hosting Lemon.js to ensure security updates.

**Table: Checkout Session Customization Options**

| **Option**               | **Description**                                      | **Example**                                                                 |
|--------------------------|------------------------------------------------------|-----------------------------------------------------------------------------|
| Pre-fill Customer Info   | Pass email, name, etc., in `checkout_data`           | `{"email": "[email protected]", "name": "John Doe"}`                     |
| Custom Data for Webhooks | Add custom data in `checkout_data.custom`            | `{"custom": {"user_id": 123}}`                                              |
| Custom Pricing           | Override price with `custom_price`                   | `{"custom_price": 599}`                                                     |
| Product Details Override | Customize name, redirect URL via `product_options`   | `{"name": "Unique subscription", "redirect_url": "https://myapp.com/welcome"}` |
| Expiration               | Set checkout expiration with `expires_at`            | `{"expires_at": "2023-04-30T23:59:59.000000Z"}`                             |

**Documentation Reference**: [Taking Payments Guide](https://docs.lemonsqueezy.com/guides/developer-guide/taking-payments)

#### Webhook Handling: Ensuring Real-Time Sync
Webhooks are critical for real-time updates, sending POST requests to your endpoint for events like `order_created`, `subscription_payment_success`, or `license_key_created`. There are 14 event types, including:

- `order_created`, `order_refunded`
- `subscription_created`, `subscription_updated`, `subscription_cancelled`, `subscription_resumed`, `subscription_expired`, `subscription_paused`, `subscription_unpaused`, `subscription_payment_failed`, `subscription_payment_success`, `subscription_payment_recovered`
- `license_key_created`, `license_key_updated`
- `affiliate_activated`

To set up, create a webhook via the dashboard at [https://app.lemonsqueezy.com/settings/webhooks] or API at `POST /v1/webhooks`, specifying `url`, `events` (e.g., `["order_created", "subscription_created"]`), and a `secret` for signing. The endpoint must return HTTP 200 for success; otherwise, Lemon Squeezy retries up to three times with exponential backoff (5s, 25s, 125s), then marks as failed, resendable manually.

Webhook data includes JSON:API objects (e.g., Subscription, Order) with `meta.custom_data` for custom checkout data. Verify requests using the `X-Signature` header, hashing the secret with the request body to match. Test mode allows simulating events, useful for testing `subscription_payment_*` after renewals, accessible via the subscription side panel.

**Table: Webhook Event Types and Use Cases**

| **Event Type**                  | **Description**                                      | **Use Case**                                      |
|---------------------------------|------------------------------------------------------|--------------------------------------------------|
| `order_created`                 | Triggered when a new order is placed                | Update order history in your app                 |
| `subscription_payment_success`  | Triggered on successful subscription payment         | Save billing history for customers               |
| `subscription_updated`          | Triggered on any subscription change                | Sync subscription status in your database        |
| `license_key_created`           | Triggered when a new license key is created         | Activate software for the customer               |

**Documentation Reference**: [Webhooks Guide](https://docs.lemonsqueezy.com/guides/developer-guide/webhooks), [Webhook Events](https://docs.lemonsqueezy.com/help/webhooks/event-types)

#### Subscription Management: Comprehensive Control
Subscription management is handled via the Subscriptions API, with endpoints for various actions. Key operations include:

- **Retrieve**: `GET /v1/subscriptions/{id}` to fetch subscription details.
- **Update**: `PATCH /v1/subscriptions/{id}` for changing plans, pausing, resuming, or updating billing. Include `variant_id` for plan changes, `pause` for pausing (e.g., `{"pause": {"mode": "free", "resumes_at": "2023-12-31"}}`), and set `pause: null` to unpause.
- **Cancel**: `DELETE /v1/subscriptions/{id}` sets `cancelled: true`, entering a grace period.
- **Resume**: `PATCH /v1/subscriptions/{id}` with `cancelled: false` during grace period.
- **Proration Handling**: Use `"invoice_immediately": true` for immediate invoices or `"disable_prorations": true` to disable, with `disable_prorations` overriding if both set.

Updating billing details uses `urls.update_payment_method` from the subscription object, a signed URL for customers to manage payment methods, recommended for in-app billing pages. Changing billing dates involves `billing_anchor` in updates, setting to `null` or `0` for current date, removing trials.

**Table: Subscription Management Actions and Endpoints**

| **Action**                     | **Method** | **Endpoint**                          | **Details**                                      |
|--------------------------------|------------|---------------------------------------|--------------------------------------------------|
| Change Plan                    | PATCH      | /v1/subscriptions/{id}                | Include new `variant_id`                         |
| Handle Proration               | PATCH      | /v1/subscriptions/{id}                | Use `"invoice_immediately": true` or disable     |
| Cancel Subscription            | DELETE     | /v1/subscriptions/{id}                | Sets `cancelled: true`, enters grace period      |
| Resume Subscription            | PATCH      | /v1/subscriptions/{id}                | Set `cancelled: false` during grace period       |
| Pause Subscription             | PATCH      | /v1/subscriptions/{id}                | Include `pause` object with mode and date        |
| Unpause Subscription           | PATCH      | /v1/subscriptions/{id}                | Set `pause: null`                                |
| Update Billing Details         | -          | `urls.update_payment_method`           | Use signed URL for customer updates              |

Store product data locally (e.g., `product_id`, `variant_id`, `name`, `price`) via `GET /api/variants#list-all-variants`, either manually or via background jobs, for plan switching.

**Documentation Reference**: [Subscription Management Guide](https://docs.lemonsqueezy.com/guides/developer-guide/managing-subscriptions)

#### Customer Portal Integration: No-Code Solution
The customer portal is a no-code, Lemon Squeezy-hosted solution for customers to manage subscriptions and billing, contrasting with My Orders (global account across stores). Access via:

- **Signed URL**: Retrieve from `GET /v1/subscriptions/{id}` or `GET /v1/customers/{id}`, valid for 24 hours, e.g., `[invalid url, do not cite]`. Request on user action (e.g., "Manage subscription") and redirect.
- **Unsigned URL**: Use `[invalid url, do not cite]`, requiring email login via magic link if not logged in.

Customize via dashboard at [Design » Customer Portal](https://app.lemonsqueezy.com/design/customer-portal), toggling features like subscription upgrades/downgrades, payment method management, and copy. Customers can view active/expired subscriptions, license keys, files, and billing history, with options to update billing info and tax ID.

Webhooks are essential for syncing, ensuring your app reflects portal changes, detailed at [Webhooks Guide](https://docs.lemonsqueezy.com/guides/developer-guide/webhooks).

**Documentation Reference**: [Customer Portal Guide](https://docs.lemonsqueezy.com/guides/developer-guide/customer-portal)