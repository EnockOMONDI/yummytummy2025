"""
M-Pesa Integration Service for YummyTummy Django E-commerce

This module provides M-Pesa STK Push functionality for processing payments
in the YummyTummy e-commerce application.
"""

import base64
import json
import requests
from datetime import datetime
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class MPesaService:
    """
    M-Pesa payment service for handling STK Push transactions
    """
    
    def __init__(self):
        self.business_short_code = settings.MPESA_BUSINESS_SHORT_CODE
        self.passkey = settings.MPESA_PASSKEY
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.base_url = settings.MPESA_BASE_URL
        
        # API endpoints
        self.auth_url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        self.stk_push_url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
        
    def get_access_token(self):
        """
        Generate M-Pesa access token for API authentication
        """
        try:
            # Create basic auth header
            credentials = f"{self.consumer_key}:{self.consumer_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(self.auth_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            access_token = result.get('access_token')
            
            if not access_token:
                logger.error("Failed to get M-Pesa access token")
                return None
                
            logger.info("M-Pesa access token generated successfully")
            return access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"M-Pesa auth request failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"M-Pesa auth error: {str(e)}")
            return None
    
    def generate_password(self):
        """
        Generate M-Pesa password for STK Push
        """
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_string = f"{self.business_short_code}{self.passkey}{timestamp}"
        password = base64.b64encode(password_string.encode()).decode()
        return password, timestamp
    
    def format_phone_number(self, phone):
        """
        Format phone number to M-Pesa required format (254XXXXXXXXX)
        """
        # Remove any spaces, dashes, or plus signs
        phone = phone.replace(' ', '').replace('-', '').replace('+', '')
        
        # Handle different formats
        if phone.startswith('0'):
            # Convert 0712345678 to 254712345678
            phone = '254' + phone[1:]
        elif phone.startswith('7') or phone.startswith('1'):
            # Convert 712345678 to 254712345678
            phone = '254' + phone
        elif not phone.startswith('254'):
            # Add 254 if not present
            phone = '254' + phone
            
        return phone
    
    def initiate_stk_push(self, phone_number, amount, order_id, callback_url):
        """
        Initiate M-Pesa STK Push payment
        
        Args:
            phone_number (str): Customer phone number
            amount (float): Payment amount
            order_id (int): Order ID for reference
            callback_url (str): URL for M-Pesa callback
            
        Returns:
            dict: Response from M-Pesa API
        """
        try:
            # Get access token
            access_token = self.get_access_token()
            if not access_token:
                return {
                    'success': False,
                    'error': 'Failed to authenticate with M-Pesa'
                }
            
            # Generate password and timestamp
            password, timestamp = self.generate_password()
            
            # Format phone number
            formatted_phone = self.format_phone_number(phone_number)
            
            # Prepare request headers
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Prepare request payload
            # IMPORTANT: TransactionType must match your shortcode configuration
            # - CustomerPayBillOnline: For Paybill Numbers
            # - CustomerBuyGoodsOnline: For Till Numbers
            # CONFIRMED: Shortcode 6319470 is a Till Number (CustomerBuyGoodsOnline)
            payload = {
                'BusinessShortCode': int(self.business_short_code),
                'Password': password,
                'Timestamp': timestamp,
                'TransactionType': getattr(settings, 'MPESA_TRANSACTION_TYPE', 'CustomerBuyGoodsOnline'),
                'Amount': int(float(amount)),  # M-Pesa requires integer amount
                'PartyA': formatted_phone,
                'PartyB': int(self.business_short_code),
                'PhoneNumber': formatted_phone,
                'CallBackURL': callback_url,
                'AccountReference': f'YummyTummy-{order_id}',
                'TransactionDesc': f'Payment for YummyTummy Order #{order_id}'
            }
            
            logger.info(f"Initiating M-Pesa STK Push for order {order_id}, amount {amount}")
            logger.debug(f"M-Pesa payload: {payload}")

            # Make STK Push request
            response = requests.post(
                self.stk_push_url,
                headers=headers,
                json=payload,
                timeout=30
            )

            logger.debug(f"M-Pesa response status: {response.status_code}")
            logger.debug(f"M-Pesa response text: {response.text}")

            response.raise_for_status()
            result = response.json()
            
            # Check if request was successful
            if result.get('ResponseCode') == '0':
                logger.info(f"M-Pesa STK Push initiated successfully for order {order_id}")
                return {
                    'success': True,
                    'checkout_request_id': result.get('CheckoutRequestID'),
                    'merchant_request_id': result.get('MerchantRequestID'),
                    'response_code': result.get('ResponseCode'),
                    'response_description': result.get('ResponseDescription'),
                    'customer_message': result.get('CustomerMessage')
                }
            else:
                logger.error(f"M-Pesa STK Push failed for order {order_id}: {result}")
                return {
                    'success': False,
                    'error': result.get('ResponseDescription', 'STK Push failed'),
                    'response_code': result.get('ResponseCode')
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"M-Pesa STK Push request failed for order {order_id}: {str(e)}")

            # Parse M-Pesa specific errors for better diagnostics
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_code = error_data.get('errorCode', 'Unknown')
                    error_message = error_data.get('errorMessage', str(e))

                    logger.error(f"M-Pesa API Error for order {order_id}: {error_code} - {error_message}")

                    # Return specific M-Pesa error with code for better handling
                    return {
                        'success': False,
                        'error': f'M-Pesa API Error {error_code}: {error_message}',
                        'error_code': error_code,
                        'error_message': error_message
                    }
                except (ValueError, KeyError):
                    # If response is not valid JSON, fall through to generic error
                    pass

            # Fallback to generic network error
            return {
                'success': False,
                'error': 'Network error occurred while processing payment'
            }
        except Exception as e:
            logger.error(f"M-Pesa STK Push error for order {order_id}: {str(e)}")
            return {
                'success': False,
                'error': 'An error occurred while processing payment'
            }
    
    def verify_transaction(self, checkout_request_id):
        """
        Verify M-Pesa transaction status
        
        Args:
            checkout_request_id (str): Checkout request ID from STK Push
            
        Returns:
            dict: Transaction verification result
        """
        try:
            # Get access token
            access_token = self.get_access_token()
            if not access_token:
                return {
                    'success': False,
                    'error': 'Failed to authenticate with M-Pesa'
                }
            
            # Generate password and timestamp
            password, timestamp = self.generate_password()
            
            # Prepare request headers
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Prepare request payload
            payload = {
                'BusinessShortCode': self.business_short_code,
                'Password': password,
                'Timestamp': timestamp,
                'CheckoutRequestID': checkout_request_id
            }
            
            # Make verification request
            verify_url = f"{self.base_url}/mpesa/stkpushquery/v1/query"
            response = requests.post(
                verify_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            return {
                'success': True,
                'result_code': result.get('ResultCode'),
                'result_desc': result.get('ResultDesc'),
                'response_code': result.get('ResponseCode')
            }
            
        except Exception as e:
            logger.error(f"M-Pesa transaction verification failed: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to verify transaction'
            }


# Convenience function for easy import
def initiate_mpesa_payment(phone_number, amount, order_id, callback_url):
    """
    Convenience function to initiate M-Pesa payment
    """
    service = MPesaService()
    return service.initiate_stk_push(phone_number, amount, order_id, callback_url)
