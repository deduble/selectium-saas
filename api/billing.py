"""
Lemon Squeezy API client and subscription management for Selextract Cloud.
Handles subscription creation, updates, cancellation, and customer portal management.
Based on Lemon Squeezy API v1 specifications.
"""
import os
import json
import hmac
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode
import requests
from sqlalchemy.orm import Session
from sqlalchemy import select

from database import get_db
from models import User, UserSubscription, SubscriptionPlan, UsageAnalytics
from schemas import SubscriptionResponse

logger = logging.getLogger(__name__)

# Valid subscription statuses from Lemon Squeezy API
VALID_SUBSCRIPTION_STATUSES = [
    'on_trial', 'active', 'paused', 'past_due',
    'unpaid', 'cancelled', 'expired'
]

class LemonSqueezyError(Exception):
    """Custom exception for Lemon Squeezy API errors"""
    pass

class LemonSqueezyClient:
    """
    Client for interacting with the Lemon Squeezy API v1.
    Implements checkout sessions, webhook verification, subscription management, and customer portal.
    """
    
    def __init__(self):
        self.api_key = os.environ.get("LEMON_SQUEEZY_API_KEY")
        if not self.api_key:
            raise ValueError("LEMON_SQUEEZY_API_KEY environment variable is required")
        
        self.store_id = os.environ.get("LEMON_SQUEEZY_STORE_ID")
        if not self.store_id:
            raise ValueError("LEMON_SQUEEZY_STORE_ID environment variable is required")
        
        self.webhook_secret = os.environ.get("LEMON_SQUEEZY_WEBHOOK_SECRET")
        if not self.webhook_secret:
            raise ValueError("LEMON_SQUEEZY_WEBHOOK_SECRET environment variable is required")
        
        self.base_url = "https://api.lemonsqueezy.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/vnd.api+json",
            "Content-Type": "application/vnd.api+json"
        }
        
        # Product variant IDs for different plans (these should match your Lemon Squeezy setup)
        self.plan_variants = {
            "starter": os.environ.get("LEMON_SQUEEZY_STARTER_VARIANT_ID"),
            "professional": os.environ.get("LEMON_SQUEEZY_PROFESSIONAL_VARIANT_ID"),
            "enterprise": os.environ.get("LEMON_SQUEEZY_ENTERPRISE_VARIANT_ID")
        }
        
        # Test mode check
        self.test_mode = os.environ.get("ENVIRONMENT", "production") != "production"

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to Lemon Squeezy API"""
        url = f"{self.base_url}/{endpoint}"
        
        # Log the exact request being made
        logger.info(f"Making {method} request to {url}")
        logger.info(f"Headers: {self.headers}")
        logger.info(f"Request data: {data}")
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                timeout=30
            )
            
            # Log the response status and content
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            logger.info(f"Response content: {response.text}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Lemon Squeezy API request failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status code: {e.response.status_code}")
                logger.error(f"Response headers: {dict(e.response.headers)}")
                logger.error(f"Response text: {e.response.text}")
                try:
                    error_detail = e.response.json()
                    logger.error(f"API error details: {error_detail}")
                except:
                    pass
            raise LemonSqueezyError(f"API request failed: {str(e)}")

    def create_checkout_session(self, user: User, plan_id: str, success_url: str, cancel_url: str) -> Dict[str, Any]:
        """
        Create a checkout session for a subscription plan.
        Returns the checkout URL and session details.
        """
        if plan_id not in self.plan_variants:
            raise LemonSqueezyError(f"Invalid plan ID: {plan_id}")
        
        variant_id = self.plan_variants[plan_id]
        if not variant_id:
            raise LemonSqueezyError(f"Variant ID not configured for plan: {plan_id}")
        
        # Checkout data following JSON:API specification
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
                    "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat().replace('+00:00', 'Z'),
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
        
        # Add redirect URLs through product options
        if success_url or cancel_url:
            checkout_data["data"]["attributes"]["product_options"] = {}
            if success_url:
                checkout_data["data"]["attributes"]["product_options"]["redirect_url"] = success_url
            # Note: cancel_url would be handled through checkout_options if supported
        
        response = self._make_request("POST", "checkouts", checkout_data)
        
        checkout_url = response["data"]["attributes"]["url"]
        checkout_id = response["data"]["id"]
        
        logger.info(f"Created checkout session for user {user.id}, plan {plan_id}: {checkout_id}")
        
        return {
            "checkout_url": checkout_url,
            "checkout_id": checkout_id,
            "expires_at": checkout_data["data"]["attributes"]["expires_at"]
        }

    def get_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Get subscription details from Lemon Squeezy"""
        response = self._make_request("GET", f"subscriptions/{subscription_id}")
        return response["data"]

    def update_subscription(self, subscription_id: str, variant_id: str, invoice_immediately: bool = True) -> Dict[str, Any]:
        """Update subscription to a different plan variant"""
        update_data = {
            "data": {
                "type": "subscriptions",
                "id": subscription_id,
                "attributes": {
                    "variant_id": int(variant_id),
                    "invoice_immediately": invoice_immediately
                }
            }
        }
        
        response = self._make_request("PATCH", f"subscriptions/{subscription_id}", update_data)
        logger.info(f"Updated subscription {subscription_id} to variant {variant_id}")
        return response["data"]

    def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Cancel a subscription (enters grace period)"""
        response = self._make_request("DELETE", f"subscriptions/{subscription_id}")
        logger.info(f"Cancelled subscription {subscription_id}")
        return response["data"]

    def resume_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Resume a cancelled subscription during grace period"""
        resume_data = {
            "data": {
                "type": "subscriptions",
                "id": subscription_id,
                "attributes": {
                    "cancelled": False
                }
            }
        }
        
        response = self._make_request("PATCH", f"subscriptions/{subscription_id}", resume_data)
        logger.info(f"Resumed subscription {subscription_id}")
        return response["data"]

    def pause_subscription(self, subscription_id: str, mode: str = "void", resumes_at: Optional[str] = None) -> Dict[str, Any]:
        """Pause a subscription"""
        pause_data = {
            "data": {
                "type": "subscriptions",
                "id": subscription_id,
                "attributes": {
                    "pause": {
                        "mode": mode  # "void" or "free"
                    }
                }
            }
        }
        
        if resumes_at:
            pause_data["data"]["attributes"]["pause"]["resumes_at"] = resumes_at
        
        response = self._make_request("PATCH", f"subscriptions/{subscription_id}", pause_data)
        logger.info(f"Paused subscription {subscription_id} with mode {mode}")
        return response["data"]

    def unpause_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Unpause a subscription"""
        unpause_data = {
            "data": {
                "type": "subscriptions",
                "id": subscription_id,
                "attributes": {
                    "pause": None
                }
            }
        }
        
        response = self._make_request("PATCH", f"subscriptions/{subscription_id}", unpause_data)
        logger.info(f"Unpaused subscription {subscription_id}")
        return response["data"]

    def get_customer_portal_url(self, subscription_id: str) -> str:
        """Get signed customer portal URL (valid for 24 hours)"""
        subscription = self.get_subscription(subscription_id)
        portal_url = subscription["attributes"]["urls"]["customer_portal"]
        
        if not portal_url:
            raise LemonSqueezyError("Customer portal URL not available")
        
        return portal_url

    def get_customer_by_id(self, customer_id: str) -> Dict[str, Any]:
        """Get customer details from Lemon Squeezy"""
        response = self._make_request("GET", f"customers/{customer_id}")
        return response["data"]

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature using HMAC SHA256"""
        if not self.webhook_secret:
            logger.error("Webhook secret not configured")
            return False
        
        try:
            # Remove 'sha256=' prefix if present
            if signature.startswith('sha256='):
                signature = signature[7:]
            
            expected_signature = hmac.new(
                self.webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, signature)
            
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {str(e)}")
            return False

    def get_invoices_for_customer(self, customer_id: str) -> List[Dict[str, Any]]:
        """Get orders (invoices) for a customer"""
        params = {"filter[customer_id]": customer_id}
        query_string = urlencode(params)
        endpoint = f"orders?{query_string}"
        
        response = self._make_request("GET", endpoint)
        return response["data"]

    def get_invoices_for_subscription(self, subscription_id: str) -> List[Dict[str, Any]]:
        """Get orders (invoices) for a subscription"""
        params = {"filter[subscription_id]": subscription_id}
        query_string = urlencode(params)
        endpoint = f"orders?{query_string}"
        
        response = self._make_request("GET", endpoint)
        return response["data"]

    def list_variants(self) -> List[Dict[str, Any]]:
        """List all variants for the store (useful for plan management)"""
        params = {"filter[store_id]": self.store_id}
        query_string = urlencode(params)
        endpoint = f"variants?{query_string}"
        
        response = self._make_request("GET", endpoint)
        return response["data"]

class SubscriptionManager:
    """
    Manages subscription lifecycle and compute unit allocation.
    Integrates with database models and Lemon Squeezy API.
    """
    
    def __init__(self, db):
        self.db = db
        self.lemon_client = LemonSqueezyClient()

    def create_subscription_from_webhook(self, webhook_data: Dict[str, Any]) -> UserSubscription:
        """Create or update subscription from Lemon Squeezy webhook"""
        subscription_data = webhook_data["data"]
        
        # Extract user information from custom data in meta
        meta_custom = webhook_data.get("meta", {}).get("custom_data", {})
        user_id = meta_custom.get("user_id")
        plan_id = meta_custom.get("plan_id")
        
        if not user_id or not plan_id:
            raise ValueError("Missing user_id or plan_id in webhook meta.custom_data")
        
        # Get user and plan
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User not found: {user_id}")
        
        plan = self.db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")
        
        # Parse subscription dates
        created_at = subscription_data["attributes"]["created_at"]
        renews_at = subscription_data["attributes"]["renews_at"]
        
        current_period_start = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        current_period_end = datetime.fromisoformat(renews_at.replace('Z', '+00:00'))
        
        # Create or update subscription
        existing_subscription = self.db.query(UserSubscription).filter(
            UserSubscription.lemon_squeezy_subscription_id == subscription_data["id"]
        ).first()
        
        if existing_subscription:
            # Update existing subscription
            existing_subscription.plan_id = plan_id
            existing_subscription.status = subscription_data["attributes"]["status"]
            existing_subscription.current_period_start = current_period_start
            existing_subscription.current_period_end = current_period_end
            subscription = existing_subscription
        else:
            # Create new subscription
            subscription = UserSubscription(
                user_id=user.id,
                plan_id=plan_id,
                lemon_squeezy_subscription_id=subscription_data["id"],
                status=subscription_data["attributes"]["status"],
                current_period_start=current_period_start,
                current_period_end=current_period_end
            )
            self.db.add(subscription)
        
        # Update user's subscription tier and compute units
        user.subscription_tier = plan_id
        user.reset_compute_units(plan.monthly_compute_units)
        
        self.db.commit()
        logger.info(f"Created/updated subscription for user {user_id}, plan {plan_id}")
        
        return subscription

    def handle_subscription_updated(self, webhook_data: Dict[str, Any]) -> None:
        """Handle subscription update webhook"""
        subscription_data = webhook_data["data"]
        subscription_id = subscription_data["id"]
        
        subscription = self.db.query(UserSubscription).filter(
            UserSubscription.lemon_squeezy_subscription_id == subscription_id
        ).first()
        
        if not subscription:
            logger.warning(f"Subscription not found for update: {subscription_id}")
            return
        
        # Update subscription status and dates
        subscription.status = subscription_data["attributes"]["status"]
        
        if subscription_data["attributes"].get("renews_at"):
            renews_at = subscription_data["attributes"]["renews_at"]
            subscription.current_period_end = datetime.fromisoformat(renews_at.replace('Z', '+00:00'))
        
        # Handle plan changes
        variant_id = str(subscription_data["attributes"]["variant_id"])
        new_plan = self._get_plan_by_variant_id(variant_id)
        if new_plan and new_plan.id != subscription.plan_id:
            old_plan_id = subscription.plan_id
            subscription.plan_id = new_plan.id
            subscription.user.subscription_tier = new_plan.id
            
            # Prorate compute units based on plan change
            self._handle_plan_change(subscription.user, old_plan_id, new_plan.id)
            
            logger.info(f"Plan changed from {old_plan_id} to {new_plan.id} for subscription {subscription_id}")
        
        self.db.commit()

    def handle_subscription_cancelled(self, webhook_data: Dict[str, Any]) -> None:
        """Handle subscription cancellation webhook"""
        subscription_data = webhook_data["data"]
        subscription_id = subscription_data["id"]
        
        subscription = self.db.query(UserSubscription).filter(
            UserSubscription.lemon_squeezy_subscription_id == subscription_id
        ).first()
        
        if not subscription:
            logger.warning(f"Subscription not found for cancellation: {subscription_id}")
            return
        
        # Update subscription status
        subscription.status = 'cancelled'
        subscription.cancel_at_period_end = True
        
        # Check if should downgrade immediately
        ends_at = subscription_data["attributes"].get("ends_at")
        if ends_at:
            ends_at_date = datetime.fromisoformat(ends_at.replace('Z', '+00:00'))
            if ends_at_date <= datetime.now(timezone.utc):
                # Immediate cancellation - downgrade to free
                subscription.user.subscription_tier = 'free'
                free_plan = self.db.query(SubscriptionPlan).filter(SubscriptionPlan.id == 'free').first()
                if free_plan:
                    subscription.user.reset_compute_units(free_plan.monthly_compute_units)
        
        self.db.commit()
        logger.info(f"Handled cancellation for subscription {subscription_id}")

    def handle_subscription_payment_success(self, webhook_data: Dict[str, Any]) -> None:
        """Handle successful subscription payment webhook"""
        subscription_data = webhook_data["data"]
        subscription_id = subscription_data["id"]
        
        subscription = self.db.query(UserSubscription).filter(
            UserSubscription.lemon_squeezy_subscription_id == subscription_id
        ).first()
        
        if not subscription:
            logger.warning(f"Subscription not found for payment success: {subscription_id}")
            return
        
        # Reset compute units for new billing period
        plan = subscription.plan
        if plan:
            subscription.user.reset_compute_units(plan.monthly_compute_units)
            logger.info(f"Reset compute units for user {subscription.user_id} after payment success")
        
        # Update subscription period if provided
        if subscription_data["attributes"].get("renews_at"):
            renews_at = subscription_data["attributes"]["renews_at"]
            subscription.current_period_end = datetime.fromisoformat(renews_at.replace('Z', '+00:00'))
        
        subscription.status = 'active'
        self.db.commit()

    def handle_subscription_payment_failed(self, webhook_data: Dict[str, Any]) -> None:
        """Handle failed subscription payment webhook"""
        subscription_data = webhook_data["data"]
        subscription_id = subscription_data["id"]
        
        subscription = self.db.query(UserSubscription).filter(
            UserSubscription.lemon_squeezy_subscription_id == subscription_id
        ).first()
        
        if not subscription:
            logger.warning(f"Subscription not found for payment failure: {subscription_id}")
            return
        
        subscription.status = 'past_due'
        self.db.commit()
        logger.info(f"Marked subscription {subscription_id} as past_due due to payment failure")

    def _get_plan_by_variant_id(self, variant_id: str) -> Optional[SubscriptionPlan]:
        """Get plan by Lemon Squeezy variant ID"""
        return self.db.query(SubscriptionPlan).filter(
            SubscriptionPlan.lemon_squeezy_variant_id == variant_id
        ).first()

    def _handle_plan_change(self, user: User, old_plan_id: str, new_plan_id: str) -> None:
        """Handle compute unit allocation when plan changes (proration)"""
        old_plan = self.db.query(SubscriptionPlan).filter(SubscriptionPlan.id == old_plan_id).first()
        new_plan = self.db.query(SubscriptionPlan).filter(SubscriptionPlan.id == new_plan_id).first()
        
        if not old_plan or not new_plan:
            logger.error(f"Plan not found during plan change: {old_plan_id} -> {new_plan_id}")
            return
        
        # Calculate proration based on remaining days in billing period
        days_remaining = (user.compute_units_reset_date - datetime.now(timezone.utc)).days
        total_days = 30  # Assuming monthly billing
        
        if days_remaining > 0:
            # Calculate prorated compute units
            old_daily_units = old_plan.monthly_compute_units / total_days
            new_daily_units = new_plan.monthly_compute_units / total_days
            
            remaining_old_units = old_daily_units * days_remaining
            remaining_new_units = new_daily_units * days_remaining
            
            # Adjust user's compute units
            adjustment = remaining_new_units - remaining_old_units
            user.compute_units_remaining = max(0, user.compute_units_remaining + int(adjustment))
            
            logger.info(f"Prorated compute units adjustment: {adjustment} for user {user.id}")

    def get_user_subscription_details(self, user: User) -> Dict[str, Any]:
        """Get comprehensive subscription details for a user"""
        active_subscription = user.get_active_subscription()
        
        if not active_subscription:
            # Return free plan details
            free_plan = self.db.query(SubscriptionPlan).filter(SubscriptionPlan.id == 'free').first()
            return {
                "plan": {
                    "id": "free",
                    "name": free_plan.name if free_plan else "Free",
                    "price_cents": 0,
                    "monthly_compute_units": free_plan.monthly_compute_units if free_plan else 100,
                    "max_concurrent_tasks": free_plan.max_concurrent_tasks if free_plan else 1
                },
                "subscription": None,
                "compute_units_remaining": user.compute_units_remaining,
                "compute_units_reset_date": user.compute_units_reset_date,
                "can_upgrade": True,
                "portal_url": None
            }
        
        # Get portal URL if available
        portal_url = None
        if active_subscription.lemon_squeezy_subscription_id:
            try:
                portal_url = self.lemon_client.get_customer_portal_url(
                    active_subscription.lemon_squeezy_subscription_id
                )
            except Exception as e:
                logger.warning(f"Could not get portal URL: {str(e)}")
        
        return {
            "plan": {
                "id": active_subscription.plan.id,
                "name": active_subscription.plan.name,
                "price_cents": active_subscription.plan.price_cents,
                "monthly_compute_units": active_subscription.plan.monthly_compute_units,
                "max_concurrent_tasks": active_subscription.plan.max_concurrent_tasks
            },
            "subscription": {
                "id": active_subscription.id,
                "status": active_subscription.status,
                "current_period_start": active_subscription.current_period_start,
                "current_period_end": active_subscription.current_period_end,
                "cancel_at_period_end": active_subscription.cancel_at_period_end,
                "days_until_renewal": active_subscription.days_until_renewal
            },
            "compute_units_remaining": user.compute_units_remaining,
            "compute_units_reset_date": user.compute_units_reset_date,
            "can_upgrade": active_subscription.plan.id != "enterprise",
            "portal_url": portal_url
        }

    def get_user_invoices(self, user: User) -> List[Dict[str, Any]]:
        """Get invoice history for a user"""
        active_subscription = user.get_active_subscription()
        if not active_subscription or not active_subscription.lemon_squeezy_subscription_id:
            return []
        
        try:
            invoices = self.lemon_client.get_invoices_for_subscription(
                active_subscription.lemon_squeezy_subscription_id
            )
            
            # Format invoices for frontend consumption
            formatted_invoices = []
            for invoice in invoices:
                formatted_invoices.append({
                    "id": invoice["id"],
                    "amount": invoice["attributes"]["total"],
                    "currency": invoice["attributes"]["currency"],
                    "status": invoice["attributes"]["status"],
                    "created_at": invoice["attributes"]["created_at"],
                    "receipt_url": invoice["attributes"].get("receipt_url"),
                    "invoice_url": invoice["attributes"].get("invoice_url")
                })
            
            return formatted_invoices
            
        except Exception as e:
            logger.error(f"Failed to get invoices for user {user.id}: {str(e)}")
            return []

# Utility functions
def get_subscription_manager(db) -> SubscriptionManager:
    """Get subscription manager instance"""
    return SubscriptionManager(db)

def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify webhook signature - utility function"""
    client = LemonSqueezyClient()
    return client.verify_webhook_signature(payload, signature)
