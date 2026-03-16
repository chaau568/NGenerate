"use client";

import { useQuery } from "@tanstack/react-query";
import { checkPaymentStatus } from "@/app/services/check_payment";
import SharePopUpSuccess from "@/components/SharePopUp_Success";
import SharePopUpFailed from "@/components/SharePopUp_Failed";
import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import { clientFetch } from "@/lib/client-fetch";
import { ChevronLeft, Clock, Loader2 } from "lucide-react";
import styles from "./page.module.css";

// ── Types ─────────────────────────────────────────────────────────────────────

interface PaymentData {
  transaction_id: number;
  ref: string;
  qr: string; 
  charge_id: string; 
  amount: number;
  package_name: string;
  expire_at: string; 
  expire_in_minutes: number;
}


export default function PaymentPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const router = useRouter();
  const { id } = use(params);

  const [paymentData, setPaymentData] = useState<PaymentData | null>(null);
  const [loading, setLoading] = useState(true);
  const [timeLeft, setTimeLeft] = useState<number>(0);

  const [showSuccess, setShowSuccess] = useState(false);
  const [showFailed, setShowFailed] = useState(false);
  const [failedMessage, setFailedMessage] = useState<string>("");

  useEffect(() => {
    const createPayment = async () => {
      try {
        setLoading(true);

        const res = await clientFetch("/api/package", {
          method: "POST",
          body: JSON.stringify({ package_id: parseInt(id) }),
        });

        const data = await res.json();

        if (!res.ok) {
          setFailedMessage(
            data?.detail ||
              data?.message ||
              "Something went wrong. Please try again.",
          );
          setShowFailed(true);
          return;
        }

        setPaymentData(data as PaymentData);
        setTimeLeft(data.expire_in_minutes * 60);
      } catch (err: unknown) {
        const message =
          err instanceof Error ? err.message : "Unable to connect to server.";
        setFailedMessage(message);
        setShowFailed(true);
      } finally {
        setLoading(false);
      }
    };

    createPayment();
  }, [id]);

  const { data: paymentStatus } = useQuery({
    queryKey: ["payment-status", paymentData?.transaction_id],
    queryFn: () => checkPaymentStatus(paymentData!.transaction_id),
    enabled: Boolean(paymentData?.transaction_id),
    refetchInterval: (query) => {
      const status = query.state.data?.payment_status;
      if (status === "success" || status === "failed" || status === "expired") {
        return false;
      }
      return 3000;
    },
  });

  useEffect(() => {
    if (!paymentStatus) return;

    const status = paymentStatus.payment_status;

    if (status === "success") {
      setShowSuccess(true);
    }

    // ✅ แก้ไข: แยก failed และ expired ออกจากกัน
    if (status === "failed") {
      setShowFailed(true);
      setFailedMessage("Payment was not successful. Please try again.");
    }

    if (status === "expired") {
      setShowFailed(true);
      setFailedMessage("QR Code has expired. Please create a new payment.");
    }
  }, [paymentStatus]);

  // ── Countdown timer ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!timeLeft) return;

    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [timeLeft]);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s < 10 ? "0" : ""}${s}`;
  };

  // ── Loading screen ──────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loadingWrapper}>
          <Loader2 className="animate-spin" size={40} />
          <p>Generating QR Code...</p>
        </div>
      </div>
    );
  }

  // ── Failed / Expired → แสดง popup แล้ว redirect กลับ ──────────────────────
  if (showFailed) {
    return (
      <SharePopUpFailed
        isOpen={showFailed}
        onClose={() => {
          setShowFailed(false);
          router.push("/package");
        }}
        title="Payment Failed"
        message={failedMessage}
      />
    );
  }

  if (!paymentData) return null;

  // ── Main render ─────────────────────────────────────────────────────────────
  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <button onClick={() => router.back()} className={styles.backBtn}>
            <ChevronLeft size={22} />
          </button>
          <h1>Back to Subscription</h1>
        </div>
      </header>

      <div className={styles.checkoutCard}>
        <h2 className={styles.cardTitle}>Check Out</h2>
        <p className={styles.cardSub}>
          Scan the QR code to complete your purchase
        </p>

        {/* Amount */}
        <div className={styles.amountBox}>
          <span className={styles.amountLabel}>AMOUNT TO PAY</span>
          <div className={styles.amountValue}>
            ฿
            {Number(paymentData.amount ?? 0).toLocaleString(undefined, {
              minimumFractionDigits: 2,
            })}
          </div>
        </div>

        {/* QR Code */}
        <div className={styles.qrSection}>
          <img
            src={paymentData.qr}
            alt="PromptPay QR Code"
            className={styles.qrImage}
          />
        </div>

        {/* Expiry timer — แดงเมื่อเหลือน้อยกว่า 60 วินาที */}
        <div className={styles.expiryBadge}>
          <Clock size={16} />
          <span>
            Expires in{" "}
            <span
              className={styles.timerText}
              style={{ color: timeLeft < 60 ? "#f87171" : "#facc15" }}
            >
              {formatTime(timeLeft)}
            </span>
          </span>
        </div>

        {/* Polling indicator */}
        <div className={styles.pollingRow}>
          <span className={styles.dot} />
          <span>Waiting for payment...</span>
        </div>

        <button className={styles.cancelBtn} onClick={() => router.back()}>
          Cancel
        </button>

        <p className={styles.refText}>Ref: {paymentData.ref}</p>
      </div>

      {/* Success popup */}
      <SharePopUpSuccess
        isOpen={showSuccess}
        onClose={() => {
          setShowSuccess(false);
          router.push("/package");
        }}
        title="Payment Successful!"
      />
    </div>
  );
}
