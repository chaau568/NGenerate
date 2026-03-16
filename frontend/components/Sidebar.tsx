"use client";

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

  const isActive = (path: string) => pathname.startsWith(path);

  // =========================
  // UNREAD COUNT ONLY (15 วิ)
  // =========================
  const { data: unreadCount = 0 } = useQuery({
    queryKey: ["notification-unread-count"],
    queryFn: fetchUnreadCount,
    refetchInterval: 15000,
    refetchOnWindowFocus: true,
  });

  // =========================
  // PROFILE (cache 5 นาที)
  // =========================
  const { data: profile } = useQuery({
    queryKey: ["profile"],
    queryFn: fetchProfile,
    staleTime: 1000 * 60 * 5,
    refetchOnWindowFocus: true,
  });

  const handleLogout = async () => {
    try {
      const res = await fetch("/api/logout", { method: "POST" });
      if (res.ok) {
        router.push("/login");
      }
    } catch (err) {
      console.error("Logout failed", err);
    }
  };

  return (
    <aside className={styles.sidebar}>
      <div className={styles.logoContainer}>
        <div className={styles.logoWrapper}>
          <div className={styles.logoBox}>N</div>
          <span className={styles.logoText}>GENERATE</span>
        </div>
      </div>

      <nav className={styles.nav}>
        <Link
          href="/library"
          className={`${styles.item} ${
            isActive("/library") ? styles.active : ""
          }`}
        >
          <BookOpen size={20} />
          <span>Library</span>
        </Link>

        <Link
          href="/project"
          className={`${styles.item} ${
            isActive("/project") ? styles.active : ""
          }`}
        >
          <Folder size={20} />
          <span>Project</span>
        </Link>

        <Link
          href="/notification"
          className={`${styles.item} ${
            isActive("/notification") ? styles.active : ""
          }`}
        >
          <Bell size={20} />
          <span>Notification</span>

          {unreadCount > 0 && <div className={styles.badge}>{unreadCount}</div>}
        </Link>

        <Link
          href="/transaction"
          className={`${styles.item} ${
            isActive("/transaction") ? styles.active : ""
          }`}
        >
          <Receipt size={20} />
          <span>Transaction</span>
        </Link>

        <Link
          href="/package"
          className={`${styles.item} ${
            isActive("/package") ? styles.active : ""
          } ${styles.gold}`}
        >
          <Crown size={20} />
          <span>Package</span>
        </Link>
      </nav>

      <div className={styles.divider} />

      <button
        onClick={handleLogout}
        className={`${styles.item} ${styles.logout}`}
      >
        <LogOut size={20} />
        <span>Logout</span>
      </button>

      <Link href="/profile" className={styles.profile}>
        <div className={styles.profileIconWrapper}>
          <User size={20} className={styles.profileIcon} />
        </div>

        <div className={styles.profileInfo}>
          <div className={styles.username}>{profile?.username ?? "T_T"}</div>
        </div>
      </Link>
    </aside>
  );
}
