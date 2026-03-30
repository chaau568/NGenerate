"use client";

import { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { LayoutDashboard, Activity, LogOut, Crown } from "lucide-react";
import Link from "next/link";
import styles from "./SidebarAdmin.module.css";

export default function SidebarAdmin() {
  const router = useRouter();
  const pathname = usePathname();
  const [showLogoutModal, setShowLogoutModal] = useState(false);

  const isActive = (path: string) => pathname === path;

  const handleLogout = async () => {
    const res = await fetch("/api/logout", { method: "POST" });
    if (res.ok) router.push("/login");
  };

  const NAV_ITEMS = [
    {
      href: "/main-dashboard",
      icon: <LayoutDashboard size={18} />,
      label: "Overview",
    },
    {
      href: "/activity-dashboard",
      icon: <Activity size={18} />,
      label: "Activity Logs",
    },
    {
      href: "/manage-package",
      icon: <Crown size={18} />,
      label: "Manage Packages",
      isGold: true,
    },
  ];

  return (
    <>
      <aside className={styles.sidebar}>
        <div className={styles.logo}>
          <div className={styles.logoMark}>N</div>
          <span className={styles.logoText}>GENERATE</span>
        </div>

        <nav className={styles.nav}>
          {NAV_ITEMS.map(({ href, icon, label, isGold }) => (
            <Link
              key={href}
              href={href}
              className={`
      ${styles.item} 
      ${isActive(href) ? styles.active : ""} 
      ${isGold ? styles.gold : ""}
    `}
            >
              <span className={styles.itemIcon}>{icon}</span>
              <span className={styles.itemLabel}>{label}</span>
            </Link>
          ))}
        </nav>

        <div className={styles.bottom}>
          <div className={styles.divider} />
          <button
            className={`${styles.item} ${styles.logoutBtn}`}
            onClick={() => setShowLogoutModal(true)}
          >
            <span className={styles.itemIcon}>
              <LogOut size={18} />
            </span>
            <span className={styles.itemLabel}>Exit Console</span>
          </button>
        </div>
      </aside>

      {showLogoutModal && (
        <div
          className={styles.modalOverlay}
          onClick={() => setShowLogoutModal(false)}
        >
          <div
            className={styles.modalContent}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className={styles.modalTitle}>Exit Admin Console?</h3>
            <div className={styles.modalActions}>
              <button
                className={styles.modalCancel}
                onClick={() => setShowLogoutModal(false)}
              >
                Stay
              </button>
              <button className={styles.modalConfirm} onClick={handleLogout}>
                Logout
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
