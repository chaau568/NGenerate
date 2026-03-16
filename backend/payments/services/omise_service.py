"""
OmiseService
============
แทนที่ QRService เดิม โดยใช้ Omise API สร้าง PromptPay Charge

หลักการทำงาน:
1. create_promptpay_charge()
   - เรียก Omise API เพื่อสร้าง Charge แบบ PromptPay
   - Omise คืน charge_id + QR image (base64)
   - เราเก็บ charge_id ไว้ใน Transaction เพื่อใช้ match กับ Webhook ภายหลัง

2. Omise จะส่ง Webhook มาหาเราเมื่อลูกค้าจ่ายเงินสำเร็จ
   - Webhook จะมี charge_id ที่ match กับที่เราเก็บไว้
   - เราก็ mark_success() ได้เลยโดยอัตโนมัติ
"""

import omise
from django.conf import settings


class OmiseService:

    @staticmethod
    def _init():
        """Initialize Omise SDK ด้วย Secret Key"""
        omise.api_secret = settings.OMISE_SECRET_KEY

    @staticmethod
    def create_promptpay_charge(amount_thb: int, ref: str) -> dict:
        """
        สร้าง PromptPay Charge ที่ Omise

        Args:
            amount_thb: จำนวนเงิน (บาท) เช่น 299
            ref: payment_ref ของ Transaction เราเอง (เก็บใน metadata)

        Returns:
            {
                "charge_id": "chrg_test_xxx",   # เอาไปเก็บใน Transaction.omise_charge_id
                "qr_image": "data:image/png;base64,...",  # แสดงให้ user สแกน
                "expires_at": "2024-01-01T00:15:00Z"
            }
        """
        OmiseService._init()

        # Omise รับเป็น สตางค์ (satang) ต้อง * 100
        amount_satang = amount_thb * 100

        charge = omise.Charge.create(
            amount=amount_satang,
            currency="thb",
            source={"type": "promptpay"},
            metadata={
                "payment_ref": ref,  # เก็บ ref ของเราไว้ใน metadata เผื่อต้องการ debug
            },
            # capture=True คือหักเงินทันทีเมื่อจ่าย (ค่า default ของ promptpay)
        )

        # QR image อยู่ใน charge.source.scannable_code.image.download_uri
        # แต่ Omise ก็ให้ base64 มาตรงๆ ด้วย
        qr_image = None
        if (
            charge.source
            and hasattr(charge.source, "scannable_code")
            and charge.source.scannable_code
        ):
            scannable = charge.source.scannable_code
            if hasattr(scannable, "image") and scannable.image:
                # Omise คืน URL ของ QR image มา เราต้องดึงมาเป็น base64
                qr_image = OmiseService._fetch_qr_image(scannable.image.download_uri)

        return {
            "charge_id": charge.id,
            "qr_image": qr_image,
            "expires_at": charge.expires_at,
        }

    @staticmethod
    def _fetch_qr_image(image_url: str) -> str:
        """
        ดึง QR image จาก Omise URL แล้วแปลงเป็น base64
        เพื่อส่งให้ frontend แสดงผลโดยไม่ต้องเรียก URL ฝั่ง client

        Omise image URL ต้อง auth ด้วย secret key ด้วย
        """
        import requests
        import base64

        response = requests.get(
            image_url,
            auth=(settings.OMISE_SECRET_KEY, ""),  # Basic Auth
            timeout=10,
        )
        response.raise_for_status()

        img_base64 = base64.b64encode(response.content).decode()
        content_type = response.headers.get("Content-Type", "image/png")
        return f"data:{content_type};base64,{img_base64}"

    @staticmethod
    def retrieve_charge(charge_id: str) -> dict:
        """
        ดึงข้อมูล Charge จาก Omise (ใช้ตอน debug หรือ polling fallback)

        Returns status: "pending" | "successful" | "failed" | "expired"
        """
        OmiseService._init()
        charge = omise.Charge.retrieve(charge_id)
        return {
            "charge_id": charge.id,
            "status": charge.status,  # successful / failed / pending / expired
            "amount": charge.amount // 100,  # แปลงจาก satang กลับเป็น บาท
        }
