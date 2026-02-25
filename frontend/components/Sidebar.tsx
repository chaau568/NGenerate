"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { clientFetch } from "@/lib/client-fetch";
import {
  BookOpen,
  Search,
  Bell,
  Receipt,
  Crown,
  User,
  LogOut,
} from "lucide-react";
import Link from "next/link";
import styles from "./Sidebar.module.css";

type Notification = {
  id: number;
  is_read: boolean;
};

type Profile = {
  user_id: number;
  username: string;
  role: string;
  package: string;
};

export default function Sidebar() {
  const router = useRouter();
  const pathname = usePathname();

  const [notificationCount, setNotificationCount] = useState(0);
  const [profile, setProfile] = useState<Profile | null>(null);

  const isActive = (path: string) => pathname.startsWith(path);

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

  useEffect(() => {
    const fetchNotifications = async () => {
      try {
        const res = await clientFetch("/api/notification");
        if (!res.ok) return;

        const data = await res.json();

        const unread = data.notifications.filter(
          (n: Notification) => !n.is_read,
        ).length;

        setNotificationCount(unread);
      } catch (err) {
        console.error("Notification fetch failed");
      }
    };

    const fetchProfile = async () => {
      try {
        const res = await clientFetch("/api/profile");
        if (!res.ok) return;

        const data = await res.json();
        setProfile(data);
      } catch (err) {
        console.error("Profile fetch failed");
      }
    };

    fetchNotifications();
    fetchProfile();
  }, []);

  return (
    <aside className={styles.sidebar}>
      {/* Logo */}
      <div className={styles.logoContainer}>
        <div className={styles.logoWrapper}>
          <div className={styles.logoBox}>N</div>
          <span className={styles.logoText}>GENERATE</span>
        </div>
      </div>

      {/* Menu */}
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
          href="/session"
          className={`${styles.item} ${
            isActive("/session") ? styles.active : ""
          }`}
        >
          <Search size={20} />
          <span>History</span>
        </Link>

        <Link
          href="/notification"
          className={`${styles.item} ${
            isActive("/notification") ? styles.active : ""
          }`}
        >
          <Bell size={20} />
          <span>Notification</span>

          {notificationCount > 0 && (
            <div className={styles.badge}>{notificationCount}</div>
          )}
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
          href="/subscription"
          className={`${styles.item} ${
            isActive("/subscription") ? styles.active : ""
          } ${styles.gold}`}
        >
          <Crown size={20} />
          <span>Subscription</span>
        </Link>
      </nav>

      <div className={styles.divider} />

      {/* Logout Button (อยู่เหนือ Profile) */}
      <button onClick={handleLogout} className={styles.logoutButton}>
        <LogOut size={20} />
        <span>Logout</span>
      </button>

      {/* Profile (Clickable) */}
      <Link href="/profile" className={styles.profile}>
        <div className={styles.profileIconWrapper}>
          <User size={20} className={styles.profileIcon} />
        </div>

        <div className={styles.profileInfo}>
          <div className={styles.username}>{profile?.username ?? "Admin"}</div>
          <div className={styles.package}>
            {profile?.package ?? "Premium User"}
          </div>
        </div>
      </Link>
    </aside>
  );
}
