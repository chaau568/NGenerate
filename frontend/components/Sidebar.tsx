"use client";

import Link from "next/link";
import styles from "./Sidebar.module.css";

export default function Sidebar() {
  return (
    <aside className={styles.sidebar}>
      <h2>NGenerate</h2>

      <nav>
        <Link href="/library">Library</Link>
        <Link href="/session">Session</Link>
        <Link href="/admin">Admin</Link>
      </nav>
    </aside>
  );
}