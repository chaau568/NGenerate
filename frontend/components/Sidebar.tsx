"use client";

import { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  BookOpen,
  Folder,
  Bell,
  Receipt,
  Crown,
  User,
  LogOut,
} from "lucide-react";
import { fetchUnreadCount } from "@/app/services/notification";
import { fetchProfile } from "@/app/services/profile";
import Link from "next/link";
import styles from "./Sidebar.module.css";

export default function Sidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const [showLogoutModal, setShowLogoutModal] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);

  const isActive = (path: string) => pathname.startsWith(path);

  const { data: unreadCount = 0 } = useQuery({
    queryKey: ["notification-unread-count"],
    queryFn: fetchUnreadCount,
    refetchInterval: 15000,
    refetchOnWindowFocus: true,
  });

  const { data: profile } = useQuery({
    queryKey: ["profile"],
    queryFn: fetchProfile,
    staleTime: 1000 * 60 * 5,
    refetchOnWindowFocus: true,
  });

  const handleLogout = async () => {
    setLoggingOut(true);
    try {
      const res = await fetch("/api/logout", { method: "POST" });
      if (res.ok) {
        router.push("/login");
      }
    } catch (err) {
      console.error("Logout failed", err);
    } finally {
      setLoggingOut(false);
      setShowLogoutModal(false);
    }
  };

  const NAV_ITEMS = [
    { href: "/library", icon: <BookOpen size={18} />, label: "Library" },
    { href: "/project", icon: <Folder size={18} />, label: "Project" },
    {
      href: "/notification",
      icon: <Bell size={18} />,
      label: "Notification",
      badge: unreadCount,
    },
    { href: "/transaction", icon: <Receipt size={18} />, label: "Transaction" },
    {
      href: "/package",
      icon: <Crown size={18} />,
      label: "Package",
      gold: true,
    },
  ];

  return (
    <>
      <aside className={styles.sidebar}>
        {/* ── Logo ── */}
        <div className={styles.logo}>
          <div className={styles.logoMark}>N</div>
          <span className={styles.logoText}>GENERATE</span>
        </div>

        {/* ── Nav ── */}
        <nav className={styles.nav}>
          {NAV_ITEMS.map(({ href, icon, label, badge, gold }) => (
            <Link
              key={href}
              href={href}
              className={`${styles.item} ${isActive(href) ? styles.active : ""} ${gold ? styles.gold : ""}`}
            >
              <span className={styles.itemIcon}>{icon}</span>
              <span className={styles.itemLabel}>{label}</span>
              {badge != null && badge > 0 && (
                <span className={styles.badge}>
                  {badge > 99 ? "99+" : badge}
                </span>
              )}
            </Link>
          ))}
        </nav>

        {/* ── Bottom ── */}
        <div className={styles.bottom}>
          <div className={styles.divider} />

          {/* Logout */}
          <button
            className={`${styles.item} ${styles.logoutBtn}`}
            onClick={() => setShowLogoutModal(true)}
          >
            <span className={styles.itemIcon}>
              <LogOut size={18} />
            </span>
            <span className={styles.itemLabel}>Logout</span>
          </button>

          {/* Profile */}
          <Link
            href="/profile"
            className={`${styles.item} ${styles.profileItem} ${isActive("/profile") ? styles.active : ""}`}
          >
            <div className={styles.avatar}>
              <User size={14} />
            </div>
            <span className={styles.itemLabel}>
              {profile?.username ?? "Profile"}
            </span>
          </Link>
        </div>
      </aside>

      {/* ── Logout Confirmation Modal ── */}
      {showLogoutModal && (
        <div
          className={styles.modalOverlay}
          onClick={() => setShowLogoutModal(false)}
        >
          <div
            className={styles.modalContent}
            onClick={(e) => e.stopPropagation()}
          >
            <div className={styles.modalIconWrap}>
              <LogOut size={28} />
            </div>
            <h3 className={styles.modalTitle}>Sign out?</h3>
            <p className={styles.modalDesc}>
              You'll be returned to the login screen.
            </p>
            <div className={styles.modalActions}>
              <button
                className={styles.modalCancel}
                onClick={() => setShowLogoutModal(false)}
                disabled={loggingOut}
              >
                Cancel
              </button>
              <button
                className={styles.modalConfirm}
                onClick={handleLogout}
                disabled={loggingOut}
              >
                {loggingOut ? "Signing out…" : "Sign out"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
