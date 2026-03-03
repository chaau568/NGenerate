"use client";

import styles from "./SharePopUp_Action.module.css";
import { CheckCircle2, XCircle, AlertTriangle } from "lucide-react";

interface SharePopUpActionProps {
  isOpen: boolean;
  type: "success" | "error" | "session";
  title: string;
  description?: string;
  primaryText?: string;
  secondaryText?: string;
  onPrimary?: () => void;
  onSecondary?: () => void;
  onClose: () => void;
}

export default function SharePopUpAction({
  isOpen,
  type,
  title,
  description,
  primaryText,
  secondaryText,
  onPrimary,
  onSecondary,
  onClose,
}: SharePopUpActionProps) {
  if (!isOpen) return null;

  const renderIcon = () => {
    switch (type) {
      case "success":
        return <CheckCircle2 size={48} className={styles.successIcon} />;
      case "error":
        return <XCircle size={48} className={styles.errorIcon} />;
      case "session":
        return <AlertTriangle size={48} className={styles.sessionIcon} />;
    }
  };

  return (
    <div className={styles.overlay}>
      <div className={styles.modal}>
        {renderIcon()}
        <h2>{title}</h2>
        {description && <p>{description}</p>}

        <div className={styles.actions}>
          {secondaryText && (
            <button onClick={onSecondary} className={styles.secondaryBtn}>
              {secondaryText}
            </button>
          )}
          {primaryText && (
            <button onClick={onPrimary} className={styles.primaryBtn}>
              {primaryText}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
