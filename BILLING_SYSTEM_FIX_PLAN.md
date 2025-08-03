# Billing System Complete Fix Plan

## Executive Summary

This document outlines the comprehensive plan to fix the entire billing system for Selextract Cloud. The billing system is currently broken due to multiple issues including Next.js Link component errors, incomplete API integrations, and missing Lemon Squeezy functionality.

**Status**: Critical - billing system non-functional  
**Priority**: P0 - Immediate fix required  
**Estimated Effort**: 8-12 hours  
**Complexity**: High - Full-stack fixes required

## Critical Issues Identified

### 1. 🚨 Immediate Runtime Error (P0)
- **Issue**: Next.js 13+ Link component incompatibility
- **Error**: `Invalid <Link> with <a> child. Please remove <a> or use <Link legacyBehavior>`
- **Impact**: Billing pages crash immediately
- **Files Affected**: All billing pages with Link components

### 2. 🔧 Missing Frontend API Methods (P0)
- **Issue**: Critical API methods are stubbed with TODOs
- **Missing Methods**:
  - `getPlans()` - Returns empty array
  - `getInvoices()` - Commented out implementation
  - `resumeSubscription()` - Completely missing
- **Impact**: Billing functionality incomplete

### 3. ⚙️ Incomplete Lemon Squeezy Integration (P1)
- **Issue**: Missing webhook events and incorrect status handling
- **Missing Events**: `subscription_resumed`, `subscription_expired`, `subscription_paused`, `subscription_unpaused`
- **Incorrect Statuses**: Using incomplete status list
- **Impact**: Subscription lifecycle not properly handled

### 4. 📊 Empty Component Data (P1)
- **Issue**: Billing pages show empty arrays instead of real data
- **Components Affected**: Plans display, invoice history, usage charts
- **Impact**: Poor user experience, no functional billing interface

### 5. 🔐 Environment Configuration (P2)
- **Issue**: Missing proper Lemon Squeezy configuration
- **Impact**: External service integration not ready for production

## Implementation Strategy

### Phase 1: Immediate Error Resolution (2-3 hours)

#### 1.1 Fix Next.js Link Components
**Objective**: Resolve runtime errors preventing billing pages from loading

**Files to Fix**:
- `frontend/pages/billing.tsx` (lines 386-391, 403-408)
- `frontend/pages/billing/plans.tsx` (lines 228-233, 239-242)
- `frontend/pages/billing/success.tsx` (lines 263-268, 270-274)
- `frontend/pages/billing/cancelled.tsx` (lines 139-143, 155-159, 230-234, 238-242)

**Fix Pattern**:
```tsx
// BEFORE (BROKEN):
<Link href="/billing">
  <a className="...">Back to Billing</a>
</Link>

// AFTER (FIXED):
<Link href="/billing" className="...">
  Back to Billing
</Link>
```

#### 1.2 Validate Basic Page Loading
- Test all billing pages load without errors
- Verify navigation works between billing pages
- Confirm responsive design intact

### Phase 2: Frontend API Integration (3-4 hours)

#### 2.1 Complete API Client Methods
**File**: `frontend/lib/api.ts`

**Missing Methods to Implement**:

```typescript
// Add to ApiClient class
async getPlans(): Promise<SubscriptionPlan[]> {
  return this.request<SubscriptionPlan[]>({
    method: 'GET',
    url: '/billing/plans',
  });
}

async getInvoices(): Promise<Invoice[]> {
  return this.request<Invoice[]>({
    method: 'GET',
    url: '/billing/invoices',
  });
}

async resumeSubscription(): Promise<{ message: string }> {
  return this.request<{ message: string }>({
    method: 'POST',
    url: '/billing/subscription/resume',
  });
}
```

#### 2.2 Update TypeScript Types
**File**: `frontend/types/api.ts`

**Add Missing Types**:
```typescript
export interface SubscriptionPlan {
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

export interface Invoice {
  id: string;
  amount: number;
  currency: string;
  status: string;
  created_at: string;
  receipt_url?: string;
  invoice_url?: string;
}
```

#### 2.3 Fix Component Data Loading
**Files**:
- `frontend/pages/billing.tsx` - Connect to real API calls
- `frontend/pages/billing/plans.tsx` - Load actual plans from backend
- Update loading states and error handling

### Phase 3: Backend API Validation (2-3 hours)

#### 3.1 Verify Backend Endpoints
**File**: `api/main.py`

**Endpoints to Validate**:
- ✅ `/api/v1/billing/subscription` (lines 1167-1179)
- ✅ `/api/v1/billing/plans` (lines 1182-1203)
- ✅ `/api/v1/billing/create-checkout` (lines 1206-1249)
- ✅ `/api/v1/billing/portal` (lines 1283-1305)
- ✅ `/api/v1/billing/subscription/cancel` (lines 1354-1376)
- ✅ `/api/v1/billing/subscription/resume` (lines 1379-1404)
- ✅ `/api/v1/billing/invoices` (lines 1268-1280)

**Validation Tasks**:
- Test each endpoint responds correctly
- Verify request/response schemas match frontend expectations
- Ensure error handling is comprehensive

#### 3.2 Database Plan Population
**Objective**: Ensure subscription plans exist in database

**Required Plans**:
```sql
INSERT INTO subscription_plans (id, name, price_cents, monthly_compute_units, max_concurrent_tasks, is_active) VALUES
('free', 'Free', 0, 100, 1, true),
('starter', 'Starter', 1900, 1000, 3, true),
('professional', 'Professional', 4900, 5000, 10, true),
('enterprise', 'Enterprise', 9900, 25000, 50, true);
```

### Phase 4: Lemon Squeezy Integration Enhancement (2-3 hours)

#### 4.1 Update Lemon Squeezy Client
**File**: `api/billing.py`

**Critical Fixes**:

1. **Add Missing Import**:
```python
from datetime import datetime, timedelta, timezone  # Add timezone import
```

2. **Update Webhook Events** (lines 17-33):
```python
WEBHOOK_EVENTS = {
    "order_created": "handle_order_created",
    "order_refunded": "handle_order_refunded", 
    "subscription_created": "handle_subscription_created",
    "subscription_updated": "handle_subscription_updated",
    "subscription_cancelled": "handle_subscription_cancelled",
    "subscription_resumed": "handle_subscription_resumed",
    "subscription_expired": "handle_subscription_expired", 
    "subscription_paused": "handle_subscription_paused",
    "subscription_unpaused": "handle_subscription_unpaused",
    "subscription_payment_failed": "handle_subscription_payment_failed",
    "subscription_payment_success": "handle_subscription_payment_success",
    "subscription_payment_recovered": "handle_subscription_payment_recovered",
    # ... existing events
}
```

3. **Update Subscription Statuses**:
```python
# Update status validation to include all Lemon Squeezy statuses
VALID_SUBSCRIPTION_STATUSES = [
    'on_trial', 'active', 'paused', 'past_due', 
    'unpaid', 'cancelled', 'expired'
]
```

#### 4.2 Fix Checkout Data Structure
**File**: `api/billing.py` (lines 102-144)

**Update Checkout Creation**:
```python
checkout_data = {
    "data": {
        "type": "checkouts",
        "attributes": {
            "checkout_data": {
                "email": user.email,
                "name": user.full_name or user.email.split('@')[0],
                "custom": {
                    "user_id": str(user.id),
                    "plan_id": plan_id
                }
            },
            "checkout_options": {
                "embed": False,
                "media": True,
                "logo": True,
                "desc": True,
                "discount": True,
                "dark": False,
                "subscription_preview": True,
                "button_color": "#2563eb"
            },
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat() + "Z",
            "preview": False,
            "test_mode": self.test_mode
        },
        "relationships": {
            "store": {
                "data": {
                    "type": "stores",
                    "id": str(self.store_id)
                }
            },
            "variant": {
                "data": {
                    "type": "variants", 
                    "id": str(variant_id)
                }
            }
        }
    }
}
```

### Phase 5: Component Integration & UX (1-2 hours)

#### 5.1 Fix Billing Components
**Files**:
- `frontend/components/SubscriptionCard.tsx`
- `frontend/components/UsageChart.tsx` 
- `frontend/components/PlanComparison.tsx`

**Updates Required**:
- Connect to real subscription data
- Handle all subscription statuses properly
- Add proper loading and error states
- Ensure responsive design works

#### 5.2 Complete Plan Display Logic
**File**: `frontend/pages/billing/plans.tsx`

**Connect to Backend**:
- Load plans from `/api/v1/billing/plans`
- Remove hardcoded empty array (line 54)
- Implement proper plan comparison logic
- Add upgrade/downgrade flow handling

### Phase 6: Environment & Configuration (1 hour)

#### 6.1 Environment Variable Documentation
**File**: `.env.example`

**Ensure Complete Configuration**:
```bash
# Lemon Squeezy Configuration
LEMON_SQUEEZY_API_KEY=your-lemonsqueezy-api-key-from-dashboard
LEMON_SQUEEZY_STORE_ID=your-store-id-from-lemonsqueezy-dashboard
LEMON_SQUEEZY_WEBHOOK_SECRET=your-webhook-signing-secret-from-lemonsqueezy

# Product Variant IDs
LEMON_SQUEEZY_STARTER_VARIANT_ID=12345-starter-plan-variant-id
LEMON_SQUEEZY_PROFESSIONAL_VARIANT_ID=12346-professional-plan-variant-id
LEMON_SQUEEZY_ENTERPRISE_VARIANT_ID=12347-enterprise-plan-variant-id
```

#### 6.2 Development Setup Instructions
**File**: `docs/BILLING_SETUP.md` (create new file)

Document the complete setup process for billing integration.

## Testing Strategy

### 1. Unit Testing
- Test all new API client methods
- Validate component rendering with real data
- Test error handling paths

### 2. Integration Testing
- Complete checkout flow (mock Lemon Squeezy responses)
- Webhook processing with test payloads
- Database state changes validation

### 3. E2E Testing
- Full user journey from plan selection to checkout
- Subscription management operations
- Invoice viewing and portal access

## Success Criteria

### ✅ Immediate Success (Phase 1)
- [ ] All billing pages load without React errors
- [ ] Navigation between billing pages works
- [ ] No console errors on billing pages

### ✅ Functional Success (Phases 2-3)
- [ ] Plans display real data from backend
- [ ] Subscription status shows accurate information
- [ ] Invoice history displays correctly
- [ ] All API endpoints return proper responses

### ✅ Integration Success (Phases 4-5)
- [ ] Checkout flow redirects to Lemon Squeezy
- [ ] Webhook processing updates database correctly
- [ ] Subscription management operations work
- [ ] Customer portal access functions

### ✅ Production Ready (Phase 6)
- [ ] Environment variables documented
- [ ] Setup instructions complete
- [ ] Error handling comprehensive
- [ ] Loading states implemented

## Risk Mitigation

### High Risk Areas
1. **Lemon Squeezy API Changes**: Mitigated by using confirmed API documentation
2. **Database Schema Conflicts**: Mitigated by following existing model patterns
3. **Frontend State Management**: Mitigated by incremental testing

### Rollback Strategy
- Each phase builds incrementally
- Database changes are additive only
- Frontend changes can be reverted individually
- Backup current working state before major changes

## Implementation Timeline

| Phase | Duration | Dependencies | Deliverable |
|-------|----------|--------------|-------------|
| 1     | 2-3h     | None         | Error-free billing pages |
| 2     | 3-4h     | Phase 1      | Complete frontend API |
| 3     | 2-3h     | Phase 2      | Validated backend endpoints |
| 4     | 2-3h     | Phase 3      | Enhanced Lemon Squeezy integration |
| 5     | 1-2h     | Phase 4      | Functional billing components |
| 6     | 1h       | Phase 5      | Production-ready configuration |

**Total Estimated Time**: 11-17 hours  
**Recommended Sprint**: 2-3 days with testing

## Post-Implementation Verification

### Checklist
- [ ] All 15 todo items completed and verified
- [ ] Frontend builds without errors
- [ ] Backend tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Documentation updated
- [ ] Environment setup validated

### Monitoring
- Monitor error rates on billing endpoints
- Track user engagement with billing features
- Verify webhook processing success rates
- Monitor Lemon Squeezy integration health

---

**Document Version**: 1.0  
**Last Updated**: 2025-01-02  
**Author**: Architect Mode  
**Review Status**: Ready for Implementation

This plan ensures zero-tolerance code completeness and follows all established patterns in `plan.md` and `rules.md`.