# เช็ค email จริงด้วย 3 ขั้นตอน:
# 1. Format check — DRF EmailField ทำอยู่แล้ว
# 2. Disposable domain check — บล็อก mailinator, tempmail ฯลฯ
# 3. MX record check — เช็คว่า domain มี mail server จริงไหม

import dns.resolver
from rest_framework import serializers


# โหลด disposable domains list
try:
    from disposable_email_domains import blocklist as DISPOSABLE_DOMAINS
except ImportError:
    DISPOSABLE_DOMAINS = set()


def validate_email_exists(email: str) -> str:
    """
    Validate ว่า email domain มีจริงและไม่ใช่ disposable

    ใช้ใน serializer:
        from users.services.email_validator import validate_email_exists

        def validate_email(self, value):
            return validate_email_exists(value)
    """
    email = email.lower().strip()
    domain = email.split("@")[-1]

    # ── Step 1: บล็อก disposable email ──────────────────────
    if domain in DISPOSABLE_DOMAINS:
        raise serializers.ValidationError("Disposable email addresses are not allowed.")

    # ── Step 2: เช็ค MX record ──────────────────────────────
    # MX record คือการประกาศของ domain ว่า "ฉันรับ email ได้"
    # ถ้าไม่มี MX record = domain นั้นไม่มี mail server = email ใช้ไม่ได้
    try:
        dns.resolver.resolve(domain, "MX")
    except dns.resolver.NXDOMAIN:
        # domain ไม่มีอยู่จริงในโลก
        raise serializers.ValidationError(f"Email domain '{domain}' does not exist.")
    except dns.resolver.NoAnswer:
        # domain มีอยู่ แต่ไม่มี MX record = ไม่รับ email
        raise serializers.ValidationError(
            f"Email domain '{domain}' cannot receive emails."
        )
    except dns.exception.Timeout:
        # DNS timeout — ในกรณีนี้ให้ผ่านไปก่อน ไม่บล็อก user
        # เพราะอาจเป็นปัญหา network ชั่วคราว
        pass
    except Exception:
        # DNS error อื่นๆ — ให้ผ่านไปก่อนเช่นกัน
        pass

    return email
