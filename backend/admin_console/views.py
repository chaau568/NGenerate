from datetime import timedelta

from django.db.models import Sum
from django.db.models.functions import Abs
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from payments.models import CreditLog, Transaction
from ngenerate_sessions.models import Session

# ─────────────────────────────────────────────────────────────────────────────
#  MAIN DASHBOARD  —  GET /admin-console/main-dashboard/
# ─────────────────────────────────────────────────────────────────────────────


@api_view(["GET"])
@permission_classes([IsAdminUser])
def main_dashboard(request):

    # ── Stats ───────────────────────────────────────────
    # ใช้ Abs() เพราะ lock logs เก็บเป็น negative amount
    total_credits_used = (
        CreditLog.objects.filter(
            type__in=["analysis_lock", "generation_lock"]
        ).aggregate(total=Sum(Abs("amount")))["total"]
        or 0
    )

    total_incomes = (
        Transaction.objects.filter(payment_status="success").aggregate(
            total=Sum("amount")
        )["total"]
        or 0
    )

    # นับ user ที่มี session ที่ active จริงๆ (ไม่นับ deleted user)
    active_users = (
        Session.objects.filter(novel__user__is_active=True)
        .values("novel__user")
        .distinct()
        .count()
    )

    # ── Credit usage history (last 7 days) ─────────────
    today = timezone.now().date()
    credit_history = []
    income_history = []

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)

        day_start = timezone.make_aware(timezone.datetime(day.year, day.month, day.day))
        day_end = day_start + timedelta(days=1)

        # ใช้ Abs() เช่นกัน เพื่อให้ได้ค่าบวก
        c_total = (
            CreditLog.objects.filter(
                type__in=["analysis_lock", "generation_lock"],
                created_at__gte=day_start,
                created_at__lt=day_end,
            ).aggregate(total=Sum(Abs("amount")))["total"]
            or 0
        )

        credit_history.append(
            {
                "date": day.isoformat(),
                "total": int(c_total),
            }
        )

        i_total = (
            Transaction.objects.filter(
                payment_status="success",
                created_at__gte=day_start,
                created_at__lt=day_end,
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        income_history.append({"date": day.isoformat(), "total": int(i_total)})

    return Response(
        {
            "stats": {
                "total_credits_used": int(total_credits_used),
                "total_incomes": int(total_incomes),
                "active_users": active_users,
            },
            "credit_usage_history": credit_history,
            "incomes_history": income_history,
        }
    )


# ─────────────────────────────────────────────────────────────────────────────
#  ACTIVITY DASHBOARD  —  GET /admin-console/activity-dashboard/
# ─────────────────────────────────────────────────────────────────────────────

PAGE_SIZE = 20

ANALYSIS_STATUS_MAP = {
    "analyzing": "processing",
    "analyzed": "completed",
    "failed": "failed",
    "draft": "processing",
}

ACTION_MAP = {
    "analysis_lock": "Analyze",
    "generation_lock": "Generate",
    "topup": "Topup",
    "refund": "Refund",
}


def _resolve_status(log):
    """
    คำนวณ status ของ activity จาก log type และ session/run status
    แสดงเฉพาะ lock, topup, refund rows (ไม่มี complete rows แล้ว)
    """
    t = log.type

    if t in ("topup", "refund"):
        return "completed"

    if t == "analysis_lock":
        if log.session is None:
            return "completed"
        return ANALYSIS_STATUS_MAP.get(log.session.status, "processing")

    if t == "generation_lock":
        if log.session is None:
            return "completed"
        latest_run = log.session.generation_runs.order_by("-version").first()
        if not latest_run:
            return "processing"
        return {
            "pending": "processing",
            "generating": "processing",
            "generated": "completed",
            "failed": "failed",
        }.get(latest_run.status, "processing")

    return "completed"


def _details_for(log):
    if log.type == "topup":
        return (
            log.transaction.package.name
            if log.transaction and log.transaction.package
            else "-"
        )
    sname = (log.session.name if log.session else None) or log.session_name or "-"
    if log.type == "refund":
        return f"{sname} (refunded)"
    return sname


def _credits_for(log):
    """
    Credits sign จากมุมมองระบบ (admin):
    - analyze / generate → ระบบ "ได้รับ" credits จาก user → แสดง +
    - refund / topup     → ระบบ "จ่าย" credits ออกไป → แสดง -
    """
    amount = abs(float(log.amount))
    if log.type in ("refund", "topup"):
        return -amount
    return amount


@api_view(["GET"])
@permission_classes([IsAdminUser])
def activity_dashboard(request):
    page = int(request.query_params.get("page", 1))
    type_filter = request.query_params.get("type", "all")
    status_filter = request.query_params.get("status", "all")

    # ── Summary counts ────────────────────────────────────────────────────
    summary = {
        "total_analysis": CreditLog.objects.filter(type="analysis_lock").count(),
        "total_generation": CreditLog.objects.filter(type="generation_lock").count(),
        "total_topup": CreditLog.objects.filter(type="topup").count(),
        "total_refund": CreditLog.objects.filter(type="refund").count(),
    }

    # ── Base queryset: แสดงเฉพาะ lock, topup, refund — ตัด complete ออก ──
    SHOW_TYPES = ["analysis_lock", "generation_lock", "topup", "refund"]

    logs = (
        CreditLog.objects.filter(type__in=SHOW_TYPES)
        .select_related("user", "session", "transaction__package")
        .order_by("-created_at")
    )

    # Filter by type
    TYPE_MAP = {
        "analysis_lock": ["analysis_lock"],
        "generation_lock": ["generation_lock"],
        "topup": ["topup"],
        "refund": ["refund"],
    }
    if type_filter in TYPE_MAP:
        logs = logs.filter(type__in=TYPE_MAP[type_filter])

    # ── Build result list ─────────────────────────────────────────────────
    all_items = []
    for log in logs:
        resolved_status = _resolve_status(log)
        if status_filter != "all" and resolved_status != status_filter:
            continue
        all_items.append(
            {
                "id": log.id,
                "date_time": log.created_at,
                "username": log.user.username if log.user else "—",
                "activate": ACTION_MAP.get(log.type, log.type),
                "details": _details_for(log),
                "credits": _credits_for(log),
                "status": resolved_status,
                "type": log.type,
            }
        )

    total_count = len(all_items)
    total_pages = max(1, (total_count + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(1, min(page, total_pages))
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    paginated = all_items[start:end]

    return Response(
        {
            "results": paginated,
            "total_count": total_count,
            "total_pages": total_pages,
            "page": page,
            "summary": summary,
        }
    )
