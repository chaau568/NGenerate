import stripe
from django.conf import settings


class StripeService:

    @staticmethod
    def _init():
        stripe.api_key = settings.STRIPE_SECRET_KEY

    @staticmethod
    def create_checkout_session(transaction) -> dict:
        StripeService._init()

        session = stripe.checkout.Session.create(
            payment_method_types=["card", "promptpay"],
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": "thb",
                        "product_data": {
                            "name": transaction.package.name,
                        },
                        "unit_amount": int(transaction.amount * 100),
                    },
                    "quantity": 1,
                }
            ],
            metadata={
                "transaction_id": transaction.id,
                "payment_ref": transaction.payment_ref,
            },
            success_url=f"{settings.SITE_URL}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.SITE_URL}/package",
        )

        return {
            "session_id": session.id,
            "checkout_url": session.url,
        }

    @staticmethod
    def construct_event(payload, sig_header):
        return stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET,
        )
