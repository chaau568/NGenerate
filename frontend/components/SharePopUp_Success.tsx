"use client";

import { CheckCircle2 } from "lucide-react";
import styles from "./SharePopUp_Success.module.css";

interface SharePopUpSuccessProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
}

export default function SharePopUpSuccess({
  isOpen,
  onClose,
  title = "Success!",
}: SharePopUpSuccessProps) {
  if (!isOpen) return null;

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
        <div className={styles.modalIcon}>
          <CheckCircle2 size={60} color="#22c55e" strokeWidth={2.5} />
        </div>
        <h3 className={styles.title}>{title}</h3>
        <div className={styles.modalActions}>
          <button className={styles.okBtn} onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
