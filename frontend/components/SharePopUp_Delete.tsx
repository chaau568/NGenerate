"use client";

import React from "react";
import { AlertTriangle } from "lucide-react";
import styles from "./SharePopUp_Delete.module.css"; // แยกไฟล์ CSS เพื่อความเป็นระเบียบ

interface SharePopUpDeleteProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => Promise<void>;
  title?: string;
  description?: React.ReactNode; // ใช้ ReactNode เพื่อให้ใส่ <strong> ได้
  confirmText?: string;
  isLoading?: boolean;
}

export default function SharePopUpDelete({
  isOpen,
  onClose,
  onConfirm,
  title = "Confirm Delete?",
  description = "Are you sure you want to delete this item? This action cannot be undone.",
  confirmText = "Delete Permanently",
  isLoading = false,
}: SharePopUpDeleteProps) {
  if (!isOpen) return null;

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      {/* stopPropagation เพื่อไม่ให้คลิกที่เนื้อหาแล้วปิด Modal */}
      <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
        <div className={styles.modalIcon}>
          <AlertTriangle size={48} color="#ef4444" />
        </div>

        <h3>{title}</h3>

        <div className={styles.modalDescription}>
          {typeof description === "string" ? <p>{description}</p> : description}
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
            className={styles.confirmDeleteBtn}
            onClick={onConfirm}
            disabled={isLoading}
          >
            {isLoading ? "Deleting..." : confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
