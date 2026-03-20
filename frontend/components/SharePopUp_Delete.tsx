"use client";

import React from "react";
import { Trash2 } from "lucide-react";
import styles from "./SharePopUp_Delete.module.css";

interface SharePopUpDeleteProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void | Promise<void>;
  title?: string;
  description?: React.ReactNode;
  confirmText?: string;
  isLoading?: boolean;
  showPasswordInput?: boolean;
  passwordValue?: string;
  onPasswordChange?: (value: string) => void;
}

export default function SharePopUpDelete({
  isOpen,
  onClose,
  onConfirm,
  title = "Delete this item?",
  description = "This action cannot be undone.",
  confirmText = "Delete",
  isLoading = false,
  showPasswordInput = false,
  passwordValue = "",
  onPasswordChange,
}: SharePopUpDeleteProps) {
  if (!isOpen) return null;

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
        <div className={styles.modalIcon}>
          <Trash2 size={24} />
        </div>

        <h3>{title}</h3>

        <div className={styles.modalDescription}>
          {typeof description === "string" ? <p>{description}</p> : description}
        </div>

        {showPasswordInput && (
          <div className={styles.passwordInputGroup}>
            <label htmlFor="delete-password">Confirm with password</label>
            <input
              id="delete-password"
              type="password"
              placeholder="Enter your password"
              value={passwordValue}
              onChange={(e) => onPasswordChange?.(e.target.value)}
              className={styles.passwordInput}
              autoFocus
            />
          </div>
        )}

        <div className={styles.modalActions}>
          <button
            className={styles.cancelBtn}
            onClick={onClose}
            disabled={isLoading}
          >
            Cancel
          </button>
          <button
            className={styles.confirmDeleteBtn}
            onClick={onConfirm}
            disabled={isLoading || (showPasswordInput && !passwordValue)}
          >
            {isLoading ? "Deleting…" : confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
