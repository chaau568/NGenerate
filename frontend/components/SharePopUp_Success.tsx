"use client";

import { CheckCircle2 } from "lucide-react";
import styles from "./SharePopUp_Success.module.css";

interface SharePopUpSuccessProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  message?: string;
}

export default function SharePopUpSuccess({
  isOpen,
  onClose,
  title = "Done!",
  message,
}: SharePopUpSuccessProps) {
  if (!isOpen) return null;

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
        <div className={styles.modalIcon}>
          <CheckCircle2 size={26} />
        </div>

        <h3 className={styles.title}>{title}</h3>
        {message && <p className={styles.message}>{message}</p>}

        <button className={styles.okBtn} onClick={onClose}>
          Done
        </button>
      </div>
    </div>
  );
}
