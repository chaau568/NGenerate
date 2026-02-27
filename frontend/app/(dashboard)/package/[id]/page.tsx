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

export default function PaymentPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const router = useRouter();
  const { id } = use(params);

  const [paymentData, setPaymentData] = useState<any>(null);
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
          const message =
            data?.detail ||
            data?.message ||
            "Something went wrong. Please try again.";

          setFailedMessage(message);
          setShowFailed(true);
          return;
        }

        setPaymentData(data);
        setTimeLeft(data.expire_in_minutes * 60);
      } catch (err: any) {
        setFailedMessage(err?.message || "Unable to connect to server.");
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
    refetchInterval: 3000,
  });

  useEffect(() => {
    if (!paymentStatus) return;

    if (paymentStatus.payment_status === "success") {
      setShowSuccess(true);
    }

    if (paymentStatus.payment_status === "failed") {
      setShowFailed(true);
      setFailedMessage("Payment was not successful.");
    }
  }, [paymentStatus]);

  useEffect(() => {
    if (!timeLeft) return;

    const timer = setInterval(() => {
      setTimeLeft((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);

    return () => clearInterval(timer);
  }, [timeLeft]);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s < 10 ? "0" : ""}${s}`;
  };

  // 🔥 Loading Screen
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

  // 🔥 ถ้า failed ไม่ต้อง render checkout
  if (showFailed) {
    return (
      <>
        <SharePopUpFailed
          isOpen={showFailed}
          onClose={() => {
            setShowFailed(false);
            router.push("/package");
          }}
          title="Payment Failed"
          message={failedMessage}
        />
      </>
    );
  }

  // 🔥 กัน null 100%
  if (!paymentData) {
    return null;
  }

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

        <div className={styles.amountBox}>
          <span className={styles.amountLabel}>AMOUNT TO PAY</span>
          <div className={styles.amountValue}>
            ฿
            {Number(paymentData.amount ?? 0).toLocaleString(undefined, {
              minimumFractionDigits: 2,
            })}
          </div>
        </div>

        <div className={styles.qrSection}>
          <img
            src={paymentData.qr}
            alt="Payment QR Code"
            className={styles.qrImage}
          />
        </div>

        <div className={styles.expiryBadge}>
          <Clock size={16} />
          <span>
            Expires in{" "}
            <span className={styles.timerText}>{formatTime(timeLeft)}</span>
          </span>
        </div>

        <button className={styles.cancelBtn} onClick={() => router.back()}>
          Cancel
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
