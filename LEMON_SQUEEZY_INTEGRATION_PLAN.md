# Lemon Squeezy Integration Plan

This document outlines the plan to complete the Lemon Squeezy billing integration for Selextract Cloud. The plan is based on a comprehensive review of the existing codebase and the official Lemon Squeezy documentation.

## 1. Current Implementation Analysis

The current implementation provides a solid foundation for the Lemon Squeezy integration. The backend correctly handles most of the core API interactions, and the frontend has the necessary pages in place. However, several key areas need to be addressed to ensure a correct and robust billing system.

*   **Backend ([`api/billing.py`](api/billing.py:1), [`api/webhooks.py`](api/webhooks.py:1)):** The backend has a well-structured `LemonSqueezyClient` that correctly handles most of the core API interactions, including checkout creation, subscription management, and webhook signature verification. The `SubscriptionManager` effectively manages the local database state based on webhook events.
*   **Frontend ([`frontend/pages/billing.tsx`](frontend/pages/billing.tsx:1), [`frontend/pages/billing/plans.tsx`](frontend/pages/billing/plans.tsx:1)):** The frontend pages for billing and plans are in place, but several API calls and UI components are marked with `// TODO:` and are not fully functional.
*   **Documentation Alignment:** The implementation aligns with the core concepts of the Lemon Squeezy documentation, such as using checkout sessions, handling webhooks, and managing subscriptions. However, some details, like fetching a list of plans and invoices, are missing.

## 2. Proposed Plan for Completion

To finalize the Lemon Squeezy integration, the following steps will be taken. This plan will address the identified gaps and ensure all features are fully implemented and tested.

### 2.1. Implement Missing Backend Endpoints

Create the necessary API endpoints to support the frontend, including fetching subscription plans and invoice history.

*   **File to Modify:** [`api/main.py`](api/main.py:1)
*   **New Endpoints:**
    *   `GET /api/v1/billing/plans`: Fetches all available subscription plans.
    *   `GET /api/v1/billing/invoices`: Fetches the current user's invoice history.
    *   `POST /api/v1/billing/subscription/resume`: Resumes a cancelled subscription.

### 2.2. Complete Frontend API Client

Implement the missing methods in the frontend `ApiClient` to fetch plans, invoices, and handle subscription resumption.

*   **File to Modify:** [`frontend/lib/api.ts`](frontend/lib/api.ts:1)
*   **New Methods:**
    *   `getPlans()`: Fetches the list of subscription plans.
    *   `getInvoices()`: Fetches the user's invoice history.
    *   `resumeSubscription()`: Resumes a cancelled subscription.

### 2.3. Finalize Billing and Plans Pages

Complete the UI and logic for the billing and plans pages, ensuring all data is dynamically loaded and all user actions are functional.

*   **Files to Modify:**
    *   [`frontend/pages/billing.tsx`](frontend/pages/billing.tsx:1)
    *   [`frontend/pages/billing/plans.tsx`](frontend/pages/billing/plans.tsx:1)
*   **Tasks:**
    *   Fetch and display the list of subscription plans on the plans page.
    *   Fetch and display the user's invoice history on the billing page.
    *   Implement the "Resume Subscription" functionality on the billing page.
    *   Ensure all buttons and links are fully functional and correctly handle user interactions.

### 2.4. Enhance Proration and Plan Change Logic

Refine the proration logic to rely more on Lemon Squeezy's invoicing and ensure compute unit adjustments are accurate.

*   **File to Modify:** [`api/billing.py`](api/billing.py:1)
*   **Tasks:**
    *   Review and update the `_handle_plan_change` method to ensure it correctly calculates and applies prorated compute units.
    *   Leverage Lemon Squeezy's `invoice_immediately` flag to ensure correct billing when plans are changed.

### 2.5. Conduct End-to-End Testing

Perform thorough testing of the entire billing workflow, from checkout to subscription management and webhook processing.

*   **Testing Scenarios:**
    *   New user subscribes to a paid plan.
    *   Existing user upgrades their plan.
    *   Existing user downgrades their plan.
    *   User cancels their subscription.
    *   User resumes a cancelled subscription.
    *   Webhook events are correctly processed and the database is updated accordingly.

## 3. Mermaid Diagram of the Billing Workflow

```mermaid
graph TD
    A[User clicks "Upgrade Plan"] --> B{Create Checkout Session};
    B --> C[Redirect to Lemon Squeezy];
    C --> D{User completes payment};
    D --> E[Lemon Squeezy sends webhook];
    E --> F{Backend processes webhook};
    F --> G[Update user subscription in DB];
    G --> H[User redirected to success page];
```
