# หลักการทำงาน:
# 1. generate_and_send()  — สร้าง OTP 6 หลัก, เก็บ DB, ส่ง email
# 2. verify()             — เช็ค OTP ถูกต้องไหม, mark is_used=True
#
# Security:
# - OTP เก่าของ email นั้นถูกลบทุกครั้งก่อนสร้างใหม่ (ป้องกันใช้อันเก่า)
# - OTP หมดอายุตาม OTP_EXPIRE_MINUTES
# - ใช้ได้ครั้งเดียว (is_used flag)

import random
import string
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from users.models import OTPCode


class OTPService:

    @staticmethod
    def generate_and_send(email: str, purpose: str) -> None:
        """
        สร้าง OTP และส่งไปทาง email

        Args:
            email: email ที่จะส่ง OTP ไป
            purpose: "google_login"
        """
        # ลบ OTP เก่าของ email + purpose นี้ก่อนเสมอ
        OTPCode.objects.filter(email=email, purpose=purpose).delete()

        # สร้าง OTP ตัวเลข 6 หลัก
        length = getattr(settings, "OTP_LENGTH", 6)
        code = "".join(random.choices(string.digits, k=length))

        # คำนวณเวลาหมดอายุ
        expire_min = getattr(settings, "OTP_EXPIRE_MINUTES", 10)
        expire_at = timezone.now() + timedelta(minutes=expire_min)

        # เก็บลง DB
        OTPCode.objects.create(
            email=email,
            code=code,
            purpose=purpose,
            expire_at=expire_at,
        )

        # ส่ง email
        OTPService._send_email(email, code, expire_min, purpose)

    @staticmethod
    def verify(email: str, code: str, purpose: str) -> bool:
        """
        เช็ค OTP ถูกต้องไหม

        Returns:
            True ถ้าถูกต้อง — และ mark is_used=True ทันที
            False ถ้าผิดหรือหมดอายุ
        """
        try:
            otp = OTPCode.objects.get(
                email=email,
                code=code,
                purpose=purpose,
                is_used=False,
            )
        except OTPCode.DoesNotExist:
            return False

        if not otp.is_valid():
            return False

        # Mark ว่าใช้แล้ว ป้องกันใช้ซ้ำ
        otp.is_used = True
        otp.save(update_fields=["is_used"])

        return True

    @staticmethod
    def _send_email(email: str, code: str, expire_min: int, purpose: str) -> None:
        """ส่ง OTP email"""

        purpose_label = {
            "google_login": "Google Login Verification",
        }.get(purpose, "Verification")

        subject = f"[NGenerate] Your OTP Code — {purpose_label}"

        message = f"""
Your OTP code for {purpose_label}:

  {code}

This code will expire in {expire_min} minutes.
Do not share this code with anyone.

If you did not request this, please ignore this email.

— NGenerate Team
        """.strip()

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
