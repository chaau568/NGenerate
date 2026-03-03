"use client";

import { Play, X } from "lucide-react";
import styles from "./SharePopUp_Video.module.css";

interface SharePopUpVideoProps {
  isOpen: boolean;
  onClose: () => void;
  videoData: {
    session_id: number;
    video_id: number;
    session_name: string;
    version: number | string;
    file_size: number | string;
    created_at: string;
    duration?: string;
  } | null;
}

export default function SharePopUpVideo({
  isOpen,
  onClose,
  videoData,
}: SharePopUpVideoProps) {
  if (!isOpen || !videoData) return null;

  const videoSrc = `/api/project/${videoData.session_id}?watch=${videoData.video_id}`;

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
        {/* ปุ่ม X ขวาสุดแบบเล็ก */}
        <button className={styles.closeBtn} onClick={onClose} title="Close">
          <X size={16} />
        </button>

        {/* Header */}
        <div className={styles.modalHeader}>
          <div className={styles.headerLeft}>
            <div className={styles.playIconWrapper}>
              <Play size={18} fill="#3b82f6" color="#3b82f6" />
            </div>
            <div className={styles.titleGroup}>
              <h3>{videoData.session_name}</h3>
              <p>version {videoData.version}</p>
            </div>
          </div>
        </div>

        {/* Video Player */}
        <div className={styles.videoContainer}>
          <video className={styles.mainVideo} controls autoPlay>
            <source src={videoSrc} type="video/mp4" />
            Your browser does not support the video tag.
          </video>
        </div>

        {/* Footer Info */}
        <div className={styles.modalFooter}>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>Size</span>
            <span className={styles.infoValue}>{videoData.file_size} MB</span>
          </div>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>Date</span>
            <span className={styles.infoValue}>
              {new Date(videoData.created_at).toLocaleDateString("en-GB")}
            </span>
          </div>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>Duration</span>
            <span className={styles.infoValue}>
              {videoData.duration || "--:--"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
