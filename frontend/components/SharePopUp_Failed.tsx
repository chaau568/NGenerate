"use client";

import { AlertCircle } from "lucide-react";
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
  title = "Something went wrong",
  message = "An unexpected error occurred. Please try again.",
}: SharePopUpFailedProps) {
  if (!isOpen) return null;

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
        <div className={styles.modalIcon}>
          <AlertCircle size={24} />
        </div>

        <h3 className={styles.title}>{title}</h3>
        <p className={styles.message}>{message}</p>

        <button className={styles.okBtn} onClick={onClose}>
          Try Again
        </button>
      </div>
    </div>
  );
}
