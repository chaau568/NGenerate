"use client";

import { Play, X, Clock, HardDrive, Calendar } from "lucide-react";
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
        {/* Header */}
        <div className={styles.header}>
          <div className={styles.headerLeft}>
            <div className={styles.playIcon}>
              <Play size={15} fill="currentColor" />
            </div>
            <div>
              <h3 className={styles.sessionName}>{videoData.session_name}</h3>
              <p className={styles.version}>Version {videoData.version}</p>
            </div>
          </div>
          <button className={styles.closeBtn} onClick={onClose}>
            <X size={15} />
          </button>
        </div>

        {/* Video */}
        <div className={styles.videoWrap}>
          <video className={styles.video} controls autoPlay>
            <source src={videoSrc} type="video/mp4" />
          </video>
        </div>

        {/* Footer */}
        <div className={styles.footer}>
          <div className={styles.infoItem}>
            <HardDrive size={12} className={styles.infoIcon} />
            <span className={styles.infoLabel}>Size</span>
            <span className={styles.infoValue}>{videoData.file_size} MB</span>
          </div>
          <div className={styles.sep} />
          <div className={styles.infoItem}>
            <Calendar size={12} className={styles.infoIcon} />
            <span className={styles.infoLabel}>Date</span>
            <span className={styles.infoValue}>
              {new Date(videoData.created_at).toLocaleDateString("en-GB")}
            </span>
          </div>
          <div className={styles.sep} />
          <div className={styles.infoItem}>
            <Clock size={12} className={styles.infoIcon} />
            <span className={styles.infoLabel}>Duration</span>
            <span className={styles.infoValue}>
              {videoData.duration || "—"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
