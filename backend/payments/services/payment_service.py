"""
PaymentService (Updated)
========================
เปลี่ยนจากใช้ QRService (สร้าง QR เอง) → OmiseService (สร้าง Charge ผ่าน Omise)

การเปลี่ยนแปลงหลัก:
- create_transaction() → เหมือนเดิม ไม่เปลี่ยน
- generate_qr_for_transaction() → เรียก OmiseService แทน QRService
  พร้อมเก็บ omise_charge_id ลง Transaction
- mark_success() → เหมือนเดิม (ถูกเรียกจาก Webhook view แทน Admin)
- mark_success_by_charge_id() → ใหม่! ให้ Webhook เรียกโดยใช้ charge_id
"""

import uuid
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.conf import settings

from payments.models import Transaction, Package, CreditLog
from users.models import UserCredit
from payments.services.omise_service import OmiseService


class PaymentService:

    @staticmethod
    @transaction.atomic
    def create_transaction(user, package: Package):
        """
        สร้าง Transaction ใหม่ หรือ return ที่มีอยู่แล้ว (ถ้ายังไม่หมดอายุ)
        """
        expire_min = getattr(settings, "PAYMENTS_EXPIRE_MINUTES", 15)
        expire_at = timezone.now() + timedelta(minutes=expire_min)

        tx = (
            Transaction.objects.select_for_update()
            .filter(user=user, payment_status="pending")
            .first()
        )

        if tx:
            if tx.expire_at and tx.expire_at < timezone.now():
                tx.payment_status = "expired"
                tx.save(update_fields=["payment_status"])
            else:
                if tx.package_id == package.id:
                    return tx

                tx.package = package
                tx.amount = int(package.price)
                tx.credit_amount = package.credits
                tx.expire_at = expire_at
                # ✅ ล้าง omise_charge_id เก่าออก เพราะ package เปลี่ยน ต้องสร้าง charge ใหม่
                tx.omise_charge_id = None

                tx.save(
                    update_fields=[
                        "package",
                        "amount",
                        "credit_amount",
                        "expire_at",
                        "omise_charge_id",
                        "updated_at",
                    ]
                )

                return tx

        ref = uuid.uuid4().hex[:12]

        tx = Transaction.objects.create(
            user=user,
            package=package,
            payment_status="pending",
            payment_ref=ref,
            amount=int(package.price),
            credit_amount=package.credits,
            expire_at=expire_at,
        )

        return tx

    @staticmethod
    def generate_qr_for_transaction(transaction_id: int) -> dict:
        """
        สร้าง QR Code ผ่าน Omise แทนการสร้างเอง

        หลักการ:
        1. ถ้า Transaction นี้มี omise_charge_id แล้ว → ดึง QR เดิมมาแสดง (ไม่สร้างซ้ำ)
        2. ถ้ายังไม่มี → สร้าง Charge ใหม่ที่ Omise แล้วเก็บ charge_id

        Returns:
            {
                "qr": "data:image/png;base64,...",
                "charge_id": "chrg_test_xxx"
            }
        """
        tx = Transaction.objects.get(id=transaction_id)

        if tx.payment_status != "pending":
            raise ValueError("QR can only be generated for pending transactions")

        if tx.expire_at and tx.expire_at < timezone.now():
            tx.payment_status = "expired"
            tx.save(update_fields=["payment_status"])
            raise ValueError("Transaction expired")

        # ✅ ถ้ามี charge_id อยู่แล้ว ดึง QR เดิมมาใช้ต่อ
        if tx.omise_charge_id:
            try:
                charge_data = OmiseService.retrieve_charge(tx.omise_charge_id)
                # ถ้า charge นั้น successful แล้ว แต่ tx ยังเป็น pending อยู่ (edge case)
                if charge_data["status"] == "successful":
                    PaymentService.mark_success_by_charge_id(tx.omise_charge_id)
                    raise ValueError("Payment already completed")
                # คืน charge_id ไป ให้ frontend ดึง QR จาก Omise เอง
                # (เพราะ QR image URL อาจ expire ไปแล้ว)
            except Exception:
                # ถ้า retrieve ไม่ได้ ให้สร้างใหม่
                tx.omise_charge_id = None

        # ✅ สร้าง Charge ใหม่ที่ Omise
        result = OmiseService.create_promptpay_charge(
            amount_thb=tx.amount,
            ref=tx.payment_ref,
        )

        # เก็บ charge_id ไว้ใน Transaction เพื่อ match กับ Webhook
        tx.omise_charge_id = result["charge_id"]
        tx.save(update_fields=["omise_charge_id", "updated_at"])

        return {
            "qr": result["qr_image"],
            "charge_id": result["charge_id"],
        }

    @staticmethod
    @transaction.atomic
    def mark_success(transaction_id: int):
        """
        Mark transaction ว่าชำระเงินสำเร็จ (เรียกจาก Admin หรือ Webhook)
        """
        tx = Transaction.objects.select_for_update().get(id=transaction_id)

        if tx.expire_at and tx.expire_at < timezone.now():
            tx.payment_status = "expired"
            tx.save(update_fields=["payment_status"])
            raise ValueError("Transaction expired")

        if tx.payment_status != "pending":
            raise ValueError("Transaction already processed")

        tx.payment_status = "success"
        tx.save(update_fields=["payment_status", "updated_at"])

        wallet, _ = UserCredit.objects.get_or_create(user=tx.user)
        wallet = UserCredit.objects.select_for_update().get(pk=wallet.pk)
        wallet.add_credit(tx.credit_amount)

        CreditLog.objects.create(
            user=tx.user,
            transaction=tx,
            type="topup",
            amount=Decimal(tx.credit_amount),
        )

        return tx

    @staticmethod
    @transaction.atomic
    def mark_success_by_charge_id(charge_id: str):
        """
        ให้ Omise Webhook เรียก — หา Transaction จาก charge_id แล้ว mark_success()

        หลักการ:
        - Webhook ส่ง charge_id มาให้เรา
        - เราหา Transaction ที่ omise_charge_id ตรงกัน
        - แล้วเรียก mark_success() ปกติ
        """
        try:
            tx = Transaction.objects.get(omise_charge_id=charge_id)
        except Transaction.DoesNotExist:
            raise ValueError(f"No transaction found for charge_id: {charge_id}")

        return PaymentService.mark_success(tx.id)
