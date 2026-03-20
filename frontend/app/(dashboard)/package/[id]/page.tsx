"use client";

import { useQuery } from "@tanstack/react-query";
import { checkPaymentStatus } from "@/app/services/check_payment";
import SharePopUpSuccess from "@/components/SharePopUp_Success";
import SharePopUpFailed from "@/components/SharePopUp_Failed";
import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import { clientFetch } from "@/lib/client-fetch";
import {
  ChevronLeft,
  Clock,
  Loader2,
  ShieldCheck,
  Smartphone,
} from "lucide-react";
import styles from "./page.module.css";

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
        setFailedMessage(
          err instanceof Error ? err.message : "Unable to connect to server.",
        );
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
      if (status === "success" || status === "failed" || status === "expired")
        return false;
      return 3000;
    },
  });

  useEffect(() => {
    if (!paymentStatus) return;
    const status = paymentStatus.payment_status;
    if (status === "success") setShowSuccess(true);
    if (status === "failed") {
      setShowFailed(true);
      setFailedMessage("Payment was not successful. Please try again.");
    }
    if (status === "expired") {
      setShowFailed(true);
      setFailedMessage("QR Code has expired. Please create a new payment.");
    }
  }, [paymentStatus]);

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

  const pctLeft = paymentData
    ? (timeLeft / (paymentData.expire_in_minutes * 60)) * 100
    : 100;
  const isUrgent = timeLeft < 60;

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loadingState}>
          <div className={styles.loadingSpinner} />
          <p>Generating QR Code...</p>
        </div>
      </div>
    );
  }

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

  return (
    <div className={styles.container}>
      {/* Header */}
      <header className={styles.header}>
        <button onClick={() => router.back()} className={styles.backBtn}>
          <ChevronLeft size={18} />
        </button>
        <div>
          <p className={styles.headerEyebrow}>Payment</p>
          <p className={styles.headerTitle}>{paymentData.package_name}</p>
        </div>
      </header>

      {/* Card */}
      <div className={styles.card}>
        {/* Amount */}
        <div className={styles.amountSection}>
          <p className={styles.amountLabel}>Total amount</p>
          <p className={styles.amountValue}>
            ฿
            {Number(paymentData.amount ?? 0).toLocaleString(undefined, {
              minimumFractionDigits: 2,
            })}
          </p>
        </div>

        {/* QR */}
        <div className={styles.qrWrap}>
          <img
            src={paymentData.qr}
            alt="PromptPay QR"
            className={styles.qrImg}
          />
        </div>

        {/* Timer */}
        <div className={styles.timerSection}>
          <div className={styles.timerRow}>
            <div className={styles.timerLeft}>
              <Clock size={14} />
              <span>Expires in</span>
            </div>
            <span
              className={`${styles.timerValue} ${isUrgent ? styles.timerUrgent : ""}`}
            >
              {formatTime(timeLeft)}
            </span>
          </div>
          <div className={styles.timerBarTrack}>
            <div
              className={`${styles.timerBarFill} ${isUrgent ? styles.timerBarUrgent : ""}`}
              style={{ width: `${pctLeft}%` }}
            />
          </div>
        </div>

        {/* Polling */}
        <div className={styles.pollingRow}>
          <span className={styles.liveDot} />
          <span>Waiting for payment confirmation...</span>
        </div>

        {/* Hints */}
        <div className={styles.hintRow}>
          <div className={styles.hint}>
            <Smartphone size={14} />
            <span>Open your banking app and scan</span>
          </div>
          <div className={styles.hint}>
            <ShieldCheck size={14} />
            <span>Secured by PromptPay</span>
          </div>
        </div>

        <button className={styles.cancelBtn} onClick={() => router.back()}>
          Cancel Payment
        </button>

        <p className={styles.refText}>Ref: {paymentData.ref}</p>
      </div>

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
