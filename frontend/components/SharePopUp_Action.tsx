"use client";

import { CheckCircle2, XCircle, AlertTriangle } from "lucide-react";
import styles from "./SharePopUp_Action.module.css";

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

const CONFIG = {
  success: {
    Icon: CheckCircle2,
    iconClass: "iconSuccess",
    btnClass: "btnSuccess",
  },
  error: {
    Icon: XCircle,
    iconClass: "iconError",
    btnClass: "btnError",
  },
  session: {
    Icon: AlertTriangle,
    iconClass: "iconSession",
    btnClass: "btnSession",
  },
} as const;

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

  const { Icon, iconClass, btnClass } = CONFIG[type];

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
        <div className={`${styles.modalIcon} ${styles[iconClass]}`}>
          <Icon size={24} />
        </div>

        <h3 className={styles.title}>{title}</h3>
        {description && <p className={styles.message}>{description}</p>}

        {(primaryText || secondaryText) && (
          <div className={styles.modalActions}>
            {secondaryText && (
              <button className={styles.secondaryBtn} onClick={onSecondary}>
                {secondaryText}
              </button>
            )}
            {primaryText && (
              <button
                className={`${styles.primaryBtn} ${styles[btnClass]}`}
                onClick={onPrimary}
              >
                {primaryText}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
