"""
Webhook handlers for Lemon Squeezy subscription events.
Processes webhook events and updates subscription status, compute units, and user data.
"""
import json
import logging
from typing import Dict, Any
from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from billing import SubscriptionManager, verify_webhook_signature
from database import get_db

logger = logging.getLogger(__name__)

# Valid subscription statuses from Lemon Squeezy API
VALID_SUBSCRIPTION_STATUSES = [
    'on_trial', 'active', 'paused', 'past_due',
    'unpaid', 'cancelled', 'expired'
]

# Webhook event types from Lemon Squeezy
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
    "license_key_created": "handle_license_key_created",
    "license_key_updated": "handle_license_key_updated",
    "affiliate_activated": "handle_affiliate_activated"
}

class WebhookProcessor:
    """
    Processes Lemon Squeezy webhook events and updates local database state.
    """
    
    def __init__(self, db):
        self.db = db
        self.subscription_manager = SubscriptionManager(db)

    async def process_webhook(self, request: Request) -> Dict[str, str]:
        """
        Process incoming webhook from Lemon Squeezy.
        Verifies signature and routes to appropriate handler.
        """
        # Get the raw payload
        payload = await request.body()
        
        # Get signature from headers
        signature = request.headers.get("X-Signature")
        if not signature:
            logger.error("Missing X-Signature header in webhook")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing X-Signature header"
            )
        
        # Verify webhook signature
        if not verify_webhook_signature(payload, signature):
            logger.error("Invalid webhook signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
        
        # Parse JSON payload
        try:
            webhook_data = json.loads(payload.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in webhook payload: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload"
            )
        
        # Extract event type
        event_name = webhook_data.get("meta", {}).get("event_name")
        if not event_name:
            logger.error("Missing event_name in webhook meta")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing event_name in webhook meta"
            )
        
        # Route to appropriate handler
        if event_name not in WEBHOOK_EVENTS:
            logger.warning(f"Unknown webhook event: {event_name}")
            return {"status": "ignored", "event": event_name}
        
        handler_method = getattr(self, WEBHOOK_EVENTS[event_name])
        
        try:
            result = await handler_method(webhook_data)
            logger.info(f"Successfully processed webhook event: {event_name}")
            return {"status": "processed", "event": event_name, "result": result}
            
        except Exception as e:
            logger.error(f"Failed to process webhook event {event_name}: {str(e)}")
            # Don't raise exception to avoid webhook retries for application errors
            return {"status": "error", "event": event_name, "error": str(e)}

    async def handle_order_created(self, webhook_data: Dict[str, Any]) -> str:
        """Handle order created event (one-time purchases)"""
        order_data = webhook_data["data"]
        logger.info(f"Order created: {order_data['id']}")
        
        # For subscription service, we primarily care about subscription events
        # One-time purchases could be handled here if needed
        return "order_logged"

    async def handle_order_refunded(self, webhook_data: Dict[str, Any]) -> str:
        """Handle order refunded event"""
        order_data = webhook_data["data"]
        logger.info(f"Order refunded: {order_data['id']}")
        
        # Handle refund logic if needed
        # For subscriptions, this might involve reverting compute units
        return "refund_processed"

    async def handle_subscription_created(self, webhook_data: Dict[str, Any]) -> str:
        """Handle subscription created event"""
        try:
            subscription = self.subscription_manager.create_subscription_from_webhook(webhook_data)
            return f"subscription_created_{subscription.id}"
        except Exception as e:
            logger.error(f"Failed to create subscription from webhook: {str(e)}")
            raise

    async def handle_subscription_updated(self, webhook_data: Dict[str, Any]) -> str:
        """Handle subscription updated event (plan changes, etc.)"""
        try:
            self.subscription_manager.handle_subscription_updated(webhook_data)
            return "subscription_updated"
        except Exception as e:
            logger.error(f"Failed to update subscription from webhook: {str(e)}")
            raise

    async def handle_subscription_cancelled(self, webhook_data: Dict[str, Any]) -> str:
        """Handle subscription cancelled event"""
        try:
            self.subscription_manager.handle_subscription_cancelled(webhook_data)
            return "subscription_cancelled"
        except Exception as e:
            logger.error(f"Failed to handle subscription cancellation: {str(e)}")
            raise

    async def handle_subscription_resumed(self, webhook_data: Dict[str, Any]) -> str:
        """Handle subscription resumed event"""
        subscription_data = webhook_data["data"]
        subscription_id = subscription_data["id"]
        new_status = subscription_data["attributes"]["status"]
        
        # Validate status
        if new_status not in VALID_SUBSCRIPTION_STATUSES:
            logger.warning(f"Invalid subscription status received: {new_status}")
            new_status = 'active'  # Default to active for resumed subscriptions
        
        # Find and update subscription
        from models import UserSubscription
        subscription = self.db.query(UserSubscription).filter(
            UserSubscription.lemon_squeezy_subscription_id == subscription_id
        ).first()
        
        if subscription:
            subscription.status = new_status
            subscription.cancel_at_period_end = False
            self.db.commit()
            logger.info(f"Resumed subscription: {subscription_id} with status: {new_status}")
        
        return "subscription_resumed"

    async def handle_subscription_expired(self, webhook_data: Dict[str, Any]) -> str:
        """Handle subscription expired event"""
        subscription_data = webhook_data["data"]
        subscription_id = subscription_data["id"]
        new_status = subscription_data["attributes"]["status"]
        
        # Validate status
        if new_status not in VALID_SUBSCRIPTION_STATUSES:
            logger.warning(f"Invalid subscription status received: {new_status}")
            new_status = 'expired'  # Default to expired for this event
        
        # Find and update subscription
        from models import UserSubscription, SubscriptionPlan
        subscription = self.db.query(UserSubscription).filter(
            UserSubscription.lemon_squeezy_subscription_id == subscription_id
        ).first()
        
        if subscription:
            subscription.status = new_status
            # Downgrade user to free plan
            subscription.user.subscription_tier = 'free'
            
            # Reset to free plan compute units
            free_plan = self.db.query(SubscriptionPlan).filter(SubscriptionPlan.id == 'free').first()
            if free_plan:
                subscription.user.reset_compute_units(free_plan.monthly_compute_units)
            
            self.db.commit()
            logger.info(f"Expired subscription: {subscription_id} with status: {new_status}")
        
        return "subscription_expired"

    async def handle_subscription_paused(self, webhook_data: Dict[str, Any]) -> str:
        """Handle subscription paused event"""
        subscription_data = webhook_data["data"]
        subscription_id = subscription_data["id"]
        new_status = subscription_data["attributes"]["status"]
        
        # Validate status
        if new_status not in VALID_SUBSCRIPTION_STATUSES:
            logger.warning(f"Invalid subscription status received: {new_status}")
            new_status = 'paused'  # Default to paused for this event
        
        # Find and update subscription
        from models import UserSubscription
        subscription = self.db.query(UserSubscription).filter(
            UserSubscription.lemon_squeezy_subscription_id == subscription_id
        ).first()
        
        if subscription:
            subscription.status = new_status
            self.db.commit()
            logger.info(f"Paused subscription: {subscription_id} with status: {new_status}")
        
        return "subscription_paused"

    async def handle_subscription_unpaused(self, webhook_data: Dict[str, Any]) -> str:
        """Handle subscription unpaused event"""
        subscription_data = webhook_data["data"]
        subscription_id = subscription_data["id"]
        new_status = subscription_data["attributes"]["status"]
        
        # Validate status
        if new_status not in VALID_SUBSCRIPTION_STATUSES:
            logger.warning(f"Invalid subscription status received: {new_status}")
            new_status = 'active'  # Default to active for unpaused subscriptions
        
        # Find and update subscription
        from models import UserSubscription
        subscription = self.db.query(UserSubscription).filter(
            UserSubscription.lemon_squeezy_subscription_id == subscription_id
        ).first()
        
        if subscription:
            subscription.status = new_status
            self.db.commit()
            logger.info(f"Unpaused subscription: {subscription_id} with status: {new_status}")
        
        return "subscription_unpaused"

    async def handle_subscription_payment_failed(self, webhook_data: Dict[str, Any]) -> str:
        """Handle subscription payment failed event"""
        try:
            self.subscription_manager.handle_subscription_payment_failed(webhook_data)
            return "payment_failure_handled"
        except Exception as e:
            logger.error(f"Failed to handle payment failure: {str(e)}")
            raise

    async def handle_subscription_payment_success(self, webhook_data: Dict[str, Any]) -> str:
        """Handle subscription payment success event"""
        try:
            self.subscription_manager.handle_subscription_payment_success(webhook_data)
            return "payment_success_handled"
        except Exception as e:
            logger.error(f"Failed to handle payment success: {str(e)}")
            raise

    async def handle_subscription_payment_recovered(self, webhook_data: Dict[str, Any]) -> str:
        """Handle subscription payment recovered event (after failed payment)"""
        subscription_data = webhook_data["data"]
        subscription_id = subscription_data["id"]
        
        # Find and update subscription
        from models import UserSubscription
        subscription = self.db.query(UserSubscription).filter(
            UserSubscription.lemon_squeezy_subscription_id == subscription_id
        ).first()
        
        if subscription:
            subscription.status = 'active'
            
            # Reset compute units as this is essentially a successful payment
            plan = subscription.plan
            if plan:
                subscription.user.reset_compute_units(plan.monthly_compute_units)
            
            self.db.commit()
            logger.info(f"Payment recovered for subscription: {subscription_id}")
        
        return "payment_recovered"

    async def handle_license_key_created(self, webhook_data: Dict[str, Any]) -> str:
        """Handle license key created event"""
        license_data = webhook_data["data"]
        logger.info(f"License key created: {license_data['id']}")
        
        # If using license keys for API access or features, handle here
        return "license_key_logged"

    async def handle_license_key_updated(self, webhook_data: Dict[str, Any]) -> str:
        """Handle license key updated event"""
        license_data = webhook_data["data"]
        logger.info(f"License key updated: {license_data['id']}")
        
        # Handle license key updates if needed
        return "license_key_updated"

    async def handle_affiliate_activated(self, webhook_data: Dict[str, Any]) -> str:
        """Handle affiliate activated event"""
        affiliate_data = webhook_data["data"]
        logger.info(f"Affiliate activated: {affiliate_data['id']}")
        
        # Handle affiliate program if implemented
        return "affiliate_logged"

# Utility functions for webhook processing
def create_webhook_processor(db) -> WebhookProcessor:
    """Create webhook processor instance"""
    return WebhookProcessor(db)

async def process_lemon_squeezy_webhook(request: Request, db) -> Dict[str, str]:
    """
    Main function to process Lemon Squeezy webhooks.
    This should be called from the API endpoint.
    """
    processor = WebhookProcessor(db)
    return await processor.process_webhook(request)

# Webhook validation utilities
def validate_webhook_payload(payload: Dict[str, Any]) -> bool:
    """Validate basic webhook payload structure"""
    required_fields = ["data", "meta"]
    
    for field in required_fields:
        if field not in payload:
            return False
    
    if "event_name" not in payload.get("meta", {}):
        return False
    
    if "type" not in payload.get("data", {}):
        return False
    
    return True

def extract_user_from_webhook(webhook_data: Dict[str, Any]) -> tuple[str, str]:
    """
    Extract user_id and plan_id from webhook custom data.
    Returns (user_id, plan_id) or raises ValueError if not found.
    """
    meta_custom = webhook_data.get("meta", {}).get("custom_data", {})
    user_id = meta_custom.get("user_id")
    plan_id = meta_custom.get("plan_id")
    
    if not user_id:
        raise ValueError("user_id not found in webhook custom_data")
    if not plan_id:
        raise ValueError("plan_id not found in webhook custom_data")
    
    return user_id, plan_id

# Test mode utilities
def is_test_webhook(webhook_data: Dict[str, Any]) -> bool:
    """Check if webhook is from test mode"""
    return webhook_data.get("meta", {}).get("test_mode", False)

def validate_subscription_status(status: str, default_status: str = "active") -> str:
    """
    Validate subscription status against Lemon Squeezy valid statuses.
    Returns the status if valid, otherwise returns the default status.
    """
    if status in VALID_SUBSCRIPTION_STATUSES:
        return status
    
    logger.warning(f"Invalid subscription status received: {status}, using default: {default_status}")
    return default_status

def test_webhook_signature_verification() -> bool:
    """
    Test webhook signature verification with a sample payload.
    Returns True if verification works correctly.
    """
    try:
        from billing import verify_webhook_signature
        
        # Test payload and signature
        test_payload = b'{"test": "data"}'
        test_secret = "test_secret_key"
        
        # Create expected signature
        import hmac
        import hashlib
        expected_signature = hmac.new(
            test_secret.encode('utf-8'),
            test_payload,
            hashlib.sha256
        ).hexdigest()
        
        # Test with environment override
        import os
        original_secret = os.environ.get("LEMON_SQUEEZY_WEBHOOK_SECRET")
        os.environ["LEMON_SQUEEZY_WEBHOOK_SECRET"] = test_secret
        
        try:
            # Test verification
            result = verify_webhook_signature(test_payload, expected_signature)
            return result
        finally:
            # Restore original secret
            if original_secret:
                os.environ["LEMON_SQUEEZY_WEBHOOK_SECRET"] = original_secret
            else:
                os.environ.pop("LEMON_SQUEEZY_WEBHOOK_SECRET", None)
                
    except Exception as e:
        logger.error(f"Webhook signature test failed: {str(e)}")
        return False

def log_webhook_event(event_name: str, webhook_data: Dict[str, Any], result: str = "success") -> None:
    """Log webhook event for debugging and monitoring"""
    logger.info(
        f"Webhook Event: {event_name}",
        extra={
            "event_name": event_name,
            "data_id": webhook_data.get("data", {}).get("id"),
            "test_mode": is_test_webhook(webhook_data),
            "result": result,
            "custom_data": webhook_data.get("meta", {}).get("custom_data", {})
        }
    )
