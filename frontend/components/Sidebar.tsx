"use client";

import Link from "next/link";
import styles from "./Sidebar.module.css";

export default function Sidebar() {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.logoContainer}>
        <div className={styles.logoWrapper}>
          <div className={styles.logoBox}>N</div>
          <span className={styles.logoText}>GENERATE</span>
        </div>
      </div>

      <nav>
        <Link href="/library">Library</Link>
        <Link href="/session">Session</Link>
        <Link href="/admin">Admin</Link>
      </nav>
    </aside>
  );
}
