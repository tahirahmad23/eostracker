"""
Paystack API Integration Module

Provides a wrapper around pypaystack2 for:
- Creating subscription checkouts
- Managing subscriptions
- Handling API errors gracefully

All functions return Result<T> for consistent error handling.
"""

import os
from typing import Dict
from pypaystack2 import PaystackClient as PyPaystackClient


class PaystackClient:
    """
    Wrapper for Paystack API operations.
    
    Handles subscription creation, cancellation, and error handling.
    Reads configuration from environment variables.
    Uses pypaystack2 PaystackClient for API communication.
    """
    
    def __init__(self):
        """
        Initialize Paystack client with secret key from environment.
        
        Raises:
            ValueError: If PAYSTACK_SECRET_KEY not set
        """
        self.secret_key = os.getenv("PAYSTACK_SECRET_KEY")
        if not self.secret_key:
            raise ValueError("PAYSTACK_SECRET_KEY environment variable not set")
        
        self.public_key = os.getenv("PAYSTACK_PUBLIC_KEY")
        self.plan_code = os.getenv("PRO_PLAN_CODE")
        self.plan_amount = int(os.getenv("PRO_PLAN_AMOUNT", "4900"))  # $49.00 in cents
        
        # Initialize pypaystack2 client
        self.client = PyPaystackClient(secret_key=self.secret_key)
    
    def create_subscription(
        self,
        email: str,
        customer_name: str,
        callback_url: str
    ) -> Dict:
        """
        Create a Paystack subscription checkout session.
        
        Initializes a subscription transaction for the Pro plan.
        Returns authorization URL for redirecting user to payment page.
        
        Args:
            email: Customer email address
            customer_name: Full name of customer
            callback_url: URL to redirect after payment
        
        Returns:
            Result containing:
            - authorization_url: Paystack payment page URL
            - reference: Transaction reference
            - access_code: Paystack access code
            
            Or error if API request fails
        
        Example:
            client = PaystackClient()
            result = client.create_subscription(
                email="user@example.com",
                customer_name="John Doe",
                callback_url="https://app.com/success"
            )
            if result["success"]:
                print(result["data"]["authorization_url"])
        """
        try:
            # Initialize transaction for subscription using pypaystack2
            response = self.client.transactions.initialize(
                email=email,
                amount=self.plan_amount,  # Amount in cents
                plan=self.plan_code,
                callback_url=callback_url,
                metadata={
                    "customer_name": customer_name,
                    "subscription_type": "pro_monthly"
                }
            )
            
            # pypaystack2 returns Response object with status, message, data
            if response.status:
                return {
                    "success": True,
                    "data": {
                        "authorization_url": response.data.authorization_url,
                        "reference": response.data.reference,
                        "access_code": response.data.access_code
                    }
                }
            else:
                return {
                    "success": False,
                    "error": f"Paystack API error: {response.message}"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create checkout session: {str(e)}"
            }
    
    def cancel_subscription(
        self,
        subscription_code: str,
        email_token: str
    ) -> Dict:
        """
        Cancel an active subscription on Paystack.
        
        Disables automatic renewal. Subscription remains active until
        the end of the current billing period.
        
        Args:
            subscription_code: Paystack subscription code
            email_token: Customer email token or code
        
        Returns:
            Result indicating success or error
        
        Example:
            client = PaystackClient()
            result = client.cancel_subscription(
                subscription_code="SUB_xxxxx",
                email_token="customer@email.com"
            )
            if result["success"]:
                print("Subscription cancelled")
        """
        try:
            # Disable subscription using pypaystack2
            response = self.client.subscriptions.disable(
                code=subscription_code,
                token=email_token
            )
            
            # pypaystack2 returns Response object
            if response.status:
                return {
                    "success": True,
                    "data": {
                        "message": "Subscription cancelled successfully"
                    }
                }
            else:
                return {
                    "success": False,
                    "error": f"Paystack API error: {response.message}"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to cancel subscription: {str(e)}"
            }
    
    def verify_transaction(self, reference: str) -> Dict:
        """
        Verify a transaction status.
        
        Used to confirm payment was successful after redirect.
        
        Args:
            reference: Transaction reference from initialization
        
        Returns:
            Result containing transaction details or error
        
        Example:
            client = PaystackClient()
            result = client.verify_transaction("TRX_xxxxx")
            if result["success"] and result["data"]["status"] == "success":
                print("Payment confirmed")
        """
        try:
            # Verify transaction using pypaystack2
            response = self.client.transactions.verify(reference=reference)
            
            # pypaystack2 returns Response object
            if response.status:
                return {
                    "success": True,
                    "data": {
                        "status": response.data.status,
                        "amount": response.data.amount,
                        "reference": response.data.reference,
                        "customer": response.data.customer
                    }
                }
            else:
                return {
                    "success": False,
                    "error": f"Paystack API error: {response.message}"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to verify transaction: {str(e)}"
            }
