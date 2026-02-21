import qrcode
import base64
from io import BytesIO
from promptpay import qrcode as pp_qrcode
from django.conf import settings


class QRService:

    @staticmethod
    def generate_promptpay_qr(amount: float, ref: str) -> str:
        promptpay_id = settings.PROMPTPAY_ID

        payload = pp_qrcode.generate_payload(promptpay_id, float(amount))

        img = qrcode.make(payload)

        buffered = BytesIO()
        img.save(buffered, format="PNG")

        img_str = base64.b64encode(buffered.getvalue()).decode()

        return f"data:image/png;base64,{img_str}"