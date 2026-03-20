"use client";

import { RotateCcw, AlertCircle } from "lucide-react";
import styles from "./SharePopUp_Retry.module.css";

interface SharePopUpRetryProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isLoading?: boolean;
  title?: string;
  sessionName?: string;
  warningHighlight?: string;
}

export default function SharePopUpRetry({
  isOpen,
  onClose,
  onConfirm,
  isLoading = false,
  title = "Retry this task?",
  sessionName,
  warningHighlight = "Previous progress will be deleted and the task will restart from the beginning.",
}: SharePopUpRetryProps) {
  if (!isOpen) return null;

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
        <div className={styles.modalIcon}>
          <RotateCcw size={24} />
        </div>

        <h3 className={styles.title}>{title}</h3>

        {sessionName && <p className={styles.sessionName}>"{sessionName}"</p>}

        <div className={styles.warningBox}>
          <AlertCircle size={14} className={styles.warningIcon} />
          <p className={styles.warningText}>{warningHighlight}</p>
        </div>

        <div className={styles.modalActions}>
          <button
            className={styles.cancelBtn}
            onClick={onClose}
            disabled={isLoading}
          >
            Cancel
          </button>
          <button
            className={styles.confirmBtn}
            onClick={onConfirm}
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <span className={styles.spinner} /> Retrying…
              </>
            ) : (
              <>
                <RotateCcw size={13} /> Retry
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
