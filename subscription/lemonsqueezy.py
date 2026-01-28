"""
Lemon Squeezy API Integration Module

Provides wrapper for Lemon Squeezy API for:
- Creating subscription checkouts (all in USD)
- Managing subscriptions
- Handling API errors gracefully

All functions return Result<T> for consistent error handling.
All transactions are processed in USD globally.
"""

import os
import requests
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class LemonSqueezyClient:
    """
    Wrapper for Lemon Squeezy API operations.
    
    Handles subscription creation, cancellation, and error handling.
    Reads configuration from environment variables.
    Uses Lemon Squeezy REST API for communication.
    
    All pricing is in USD regardless of customer location.
    Lemon Squeezy acts as merchant of record, handling taxes and compliance.
    """
    
    BASE_URL = "https://api.lemonsqueezy.com/v1"
    
    def __init__(self):
        """
        Initialize Lemon Squeezy client with API key from environment.
        
        Raises:
            ValueError: If LEMONSQUEEZY_API_KEY not set
        """
        self.api_key = os.getenv("LEMONSQUEEZY_API_KEY")
        if not self.api_key:
            logger.error("LEMONSQUEEZY_API_KEY not configured")
            raise ValueError("LEMONSQUEEZY_API_KEY environment variable not set")
        
        self.store_id = os.getenv("LEMONSQUEEZY_STORE_ID")
        self.variant_id = os.getenv("LEMONSQUEEZY_VARIANT_ID")  # Pro plan variant ID
        
        if not self.store_id or not self.variant_id:
            logger.error("LEMONSQUEEZY_STORE_ID/LEMONSQUEEZY_VARIANT_ID not configured")
            raise ValueError("LEMONSQUEEZY_STORE_ID and LEMONSQUEEZY_VARIANT_ID must be set")
        
        # Standard headers for all requests
        self.headers = {
            "Accept": "application/vnd.api+json",
            "Content-Type": "application/vnd.api+json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def create_subscription(
        self,
        email: str,
        customer_name: str,
        callback_url: str,
        user_id: int
    ) -> Dict:
        """
        Create a Lemon Squeezy checkout for Pro subscription.
        
        Creates a checkout URL that customers can use to subscribe.
        Pricing is always in USD ($49/month) regardless of location.
        
        Args:
            email: Customer email address
            customer_name: Full name of customer
            callback_url: URL to redirect after successful payment
            user_id: Internal user ID (stored in custom data)
        
        Returns:
            Result containing:
            - checkout_url: Lemon Squeezy checkout page URL
            - checkout_id: Checkout ID for tracking
            
            Or error if API request fails
        
        Example:
            client = LemonSqueezyClient()
            result = client.create_subscription(
                email="user@example.com",
                customer_name="John Doe",
                callback_url="https://app.com/success",
                user_id=123
            )
            if result["success"]:
                print(result["data"]["checkout_url"])
        """
        try:
            logger.debug("Creating Lemon Squeezy checkout")
            # Create checkout with Lemon Squeezy API
            payload = {
                "data": {
                    "type": "checkouts",
                    "attributes": {
                        "checkout_data": {
                            "email": email,
                            "name": customer_name,
                            "custom": {
                                "user_id": str(user_id)  # Store our internal user ID
                            }
                        },
                        "product_options": {
                            "redirect_url": callback_url
                        },
                        "checkout_options": {
                            "embed": False,
                            "media": True,
                            "logo": True,
                            "desc": True,
                            "discount": True,
                            "subscription_preview": True
                        }
                    },
                    "relationships": {
                        "store": {
                            "data": {
                                "type": "stores",
                                "id": self.store_id
                            }
                        },
                        "variant": {
                            "data": {
                                "type": "variants",
                                "id": self.variant_id
                            }
                        }
                    }
                }
            }
            
            response = requests.post(
                f"{self.BASE_URL}/checkouts",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 201:
                data = response.json()
                checkout_url = data["data"]["attributes"]["url"]
                checkout_id = data["data"]["id"]
                
                logger.info("Lemon Squeezy checkout created")
                return {
                    "success": True,
                    "data": {
                        "checkout_url": checkout_url,
                        "checkout_id": checkout_id
                    }
                }
            else:
                error_data = response.json()
                error_message = error_data.get("errors", [{}])[0].get("detail", "Unknown error")
                logger.warning("Lemon Squeezy API error during checkout creation", extra={"status_code": response.status_code})
                return {
                    "success": False,
                    "error": f"Lemon Squeezy API error: {error_message}"
                }
        
        except requests.RequestException as e:
            logger.exception("Failed to create Lemon Squeezy checkout")
            return {
                "success": False,
                "error": f"Failed to create checkout: {str(e)}"
            }
        except Exception as e:
            logger.exception("Unexpected error creating Lemon Squeezy checkout")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    def cancel_subscription(self, subscription_id: str) -> Dict:
        """
        Cancel an active subscription on Lemon Squeezy.
        
        Cancels the subscription at the end of the current billing period.
        Customer retains access until period ends.
        
        Args:
            subscription_id: Lemon Squeezy subscription ID
        
        Returns:
            Result indicating success or error
        
        Example:
            client = LemonSqueezyClient()
            result = client.cancel_subscription("123456")
            if result["success"]:
                print("Subscription cancelled")
        """
        try:
            logger.debug("Cancelling Lemon Squeezy subscription")
            # Cancel subscription using PATCH request
            payload = {
                "data": {
                    "type": "subscriptions",
                    "id": subscription_id,
                    "attributes": {
                        "cancelled": True
                    }
                }
            }
            
            response = requests.patch(
                f"{self.BASE_URL}/subscriptions/{subscription_id}",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info("Lemon Squeezy subscription cancellation requested")
                return {
                    "success": True,
                    "data": {
                        "message": "Subscription cancelled successfully"
                    }
                }
            else:
                error_data = response.json()
                error_message = error_data.get("errors", [{}])[0].get("detail", "Unknown error")
                logger.warning("Lemon Squeezy API error during cancellation", extra={"status_code": response.status_code})
                return {
                    "success": False,
                    "error": f"Lemon Squeezy API error: {error_message}"
                }
        
        except requests.RequestException as e:
            logger.exception("Failed to cancel Lemon Squeezy subscription")
            return {
                "success": False,
                "error": f"Failed to cancel subscription: {str(e)}"
            }
        except Exception as e:
            logger.exception("Unexpected error cancelling Lemon Squeezy subscription")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    def get_subscription(self, subscription_id: str) -> Dict:
        """
        Fetch subscription details from Lemon Squeezy.
        
        Args:
            subscription_id: Lemon Squeezy subscription ID
        
        Returns:
            Result containing subscription details or error
        """
        try:
            logger.debug("Fetching Lemon Squeezy subscription")
            response = requests.get(
                f"{self.BASE_URL}/subscriptions/{subscription_id}",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info("Lemon Squeezy subscription fetched")
                return {
                    "success": True,
                    "data": data["data"]
                }
            else:
                error_data = response.json()
                error_message = error_data.get("errors", [{}])[0].get("detail", "Unknown error")
                logger.warning("Lemon Squeezy API error fetching subscription", extra={"status_code": response.status_code})
                return {
                    "success": False,
                    "error": f"Lemon Squeezy API error: {error_message}"
                }
        
        except requests.RequestException as e:
            logger.exception("Failed to fetch Lemon Squeezy subscription")
            return {
                "success": False,
                "error": f"Failed to fetch subscription: {str(e)}"
            }
        except Exception as e:
            logger.exception("Unexpected error fetching Lemon Squeezy subscription")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
