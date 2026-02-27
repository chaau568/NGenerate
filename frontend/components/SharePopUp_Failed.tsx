"use client";

import { XCircle } from "lucide-react";
import styles from "./SharePopUp_Failed.module.css";

interface SharePopUpFailedProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  message?: string;
}

export default function SharePopUpFailed({
  isOpen,
  onClose,
  title = "Update Failed",
  message = "Something went wrong.",
}: SharePopUpFailedProps) {
  if (!isOpen) return null;

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
        <div className={styles.modalIcon}>
          <XCircle size={60} color="#ef4444" strokeWidth={2.5} />
        </div>

        <h3 className={styles.title}>{title}</h3>

        <p className={styles.message}>{message}</p>

        <div className={styles.modalActions}>
          <button className={styles.okBtn} onClick={onClose}>
            Try Again
          </button>
        </div>
      </div>
    </div>
  );
}
