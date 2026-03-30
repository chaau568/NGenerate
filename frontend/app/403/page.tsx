"use client";

import { useRouter } from "next/navigation";
import { ShieldAlert, ArrowLeft, Sparkles } from "lucide-react";
import styles from "./page.module.css";

export default function ForbiddenPage() {
  const router = useRouter();

  const handleReturn = () => {
    router.push("/library");
  };

  return (
    <div className={styles.container}>
      <div className={styles.blob} />

      <div className={styles.modal}>
        <div className={styles.iconWrapper}>
          <ShieldAlert size={40} strokeWidth={1.5} className={styles.icon} />
          <Sparkles size={20} className={styles.sparkle} />
        </div>

        <h1 className={styles.title}>Access Restricted</h1>

        <p className={styles.description}>
          Our AI security layer has identified that you don't have the necessary
          clearance to view this neural module.
        </p>

        <div className={styles.divider} />

        <button className={styles.backBtn} onClick={handleReturn}>
          <ArrowLeft size={16} />
          <span>Return to Safety</span>
        </button>

        <span className={styles.errorCode}>
          ERROR_CODE: 403_FORBIDDEN_VOICE
        </span>
      </div>
    </div>
  );
}
