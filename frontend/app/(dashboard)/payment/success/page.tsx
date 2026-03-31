"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { clientFetch } from "@/lib/client-fetch";
import {
  CheckCircle2,
  XCircle,
  Loader2,
  Sparkles,
  ArrowRight,
} from "lucide-react";
import styles from "./page.module.css";

export default function PaymentSuccessPage() {
  const params = useSearchParams();
  const router = useRouter();
  const sessionId = params.get("session_id");

  const [status, setStatus] = useState<"loading" | "success" | "error">(
    "loading",
  );

  useEffect(() => {
    if (!sessionId) {
      setStatus("error");
      return;
    }

    const check = async () => {
      try {
        const res = await clientFetch(`/api/payment/verify-session`, {
          method: "POST",
          body: JSON.stringify({ session_id: sessionId }),
        });
        if (!res.ok) throw new Error();
        setStatus("success");
      } catch {
        setStatus("error");
      }
    };
    check();
  }, [sessionId]);

  return (
    <main className={styles.container}>
      {/* Background Decor */}
      <div className={styles.glowBg} />

      <div className={styles.contentCard}>
        {status === "loading" && (
          <div className={styles.stateWrapper}>
            <div className={styles.loaderContainer}>
              <Loader2 className={styles.iconSpin} size={48} />
              <Sparkles className={styles.iconSparkle} size={24} />
            </div>
            <div className={styles.textContent}>
              <h2 className={styles.title}>Verifying Payment</h2>
              <p className={styles.description}>
                Syncing with neural networks...
              </p>
            </div>
          </div>
        )}

        {status === "success" && (
          <div className={`${styles.stateWrapper} ${styles.fadeIn}`}>
            <div className={`${styles.iconCircle} ${styles.successCircle}`}>
              <CheckCircle2 size={40} />
            </div>
            <h1 className={styles.heroTitle}>Payment Successful</h1>
            <p className={styles.description}>
              Your credits have been recharged.
            </p>
            <div className={styles.divider} />
            <button
              onClick={() => router.push("/library")}
              className={styles.primaryButton}
            >
              <span>Go To Library</span>
              <ArrowRight size={18} />
            </button>
          </div>
        )}

        {status === "error" && (
          <div className={`${styles.stateWrapper} ${styles.fadeIn}`}>
            <div className={`${styles.iconCircle} ${styles.errorCircle}`}>
              <XCircle size={40} />
            </div>
            <h2 className={styles.title}>Verification Failed</h2>
            <p className={styles.description}>
              We couldn't confirm your transaction. Please contact support if
              the issue persists.
            </p>
            <button
              onClick={() => router.push("/package")}
              className={styles.ghostButton}
            >
              Back to Packages
            </button>
          </div>
        )}
      </div>
    </main>
  );
}
