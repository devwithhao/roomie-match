import urllib.parse
import hmac
import hashlib
from datetime import datetime

from app.core.config import settings

class VNPAYService:
    @staticmethod
    def create_payment_url(order_id: str, amount_cents: int, order_desc: str, ip_addr: str) -> str:
        """Create a VNPAY payment URL for an order."""
        tmn_code = settings.vnpay_tmn_code
        secret_key = settings.vnpay_hash_secret
        vnp_url = settings.vnpay_url
        return_url = settings.vnpay_return_url
        
        if not tmn_code or not secret_key:
            raise ValueError("VNPAY is not configured")

        vnp_Amount = amount_cents * 100
        
        now = datetime.now()
        vnp_CreateDate = now.strftime('%Y%m%d%H%M%S')
        expire_date = datetime.fromtimestamp(now.timestamp() + 15 * 60)
        vnp_ExpireDate = expire_date.strftime('%Y%m%d%H%M%S')

        input_data = {
            "vnp_Version": "2.1.0",
            "vnp_Command": "pay",
            "vnp_TmnCode": tmn_code,
            "vnp_Amount": str(vnp_Amount),
            "vnp_CurrCode": "VND",
            "vnp_TxnRef": str(order_id),
            "vnp_OrderInfo": order_desc,
            "vnp_OrderType": "other",
            "vnp_Locale": "vn",
            "vnp_ReturnUrl": return_url,
            "vnp_IpAddr": ip_addr,
            "vnp_CreateDate": vnp_CreateDate,
            "vnp_ExpireDate": vnp_ExpireDate
        }

        input_data = dict(sorted(input_data.items()))
        query_string = urllib.parse.urlencode(input_data)

        hash_data = query_string.encode('utf-8')
        secure_hash = hmac.new(secret_key.encode('utf-8'), hash_data, hashlib.sha512).hexdigest()
        
        payment_url = f"{vnp_url}?{query_string}&vnp_SecureHash={secure_hash}"
        return payment_url

    @staticmethod
    def verify_payment(query_params: dict) -> bool:
        """Verify VNPAY checksum."""
        secret_key = settings.vnpay_hash_secret
        if not secret_key:
            return False

        secure_hash = query_params.get('vnp_SecureHash')
        if not secure_hash:
            return False

        if 'vnp_SecureHash' in query_params:
            del query_params['vnp_SecureHash']
        if 'vnp_SecureHashType' in query_params:
            del query_params['vnp_SecureHashType']

        input_data = dict(sorted(query_params.items()))
        query_string = urllib.parse.urlencode(input_data)
        
        hash_data = query_string.encode('utf-8')
        calculated_hash = hmac.new(secret_key.encode('utf-8'), hash_data, hashlib.sha512).hexdigest()

        return secure_hash == calculated_hash
