"use client";

import { useEffect, useState } from "react";
import { clientFetch } from "@/lib/client-fetch";
import styles from "./page.module.css";

interface Billing {
  id: number;
  date_time: string;
  package: string;
  amount: string;
  status: string;
}

interface Activity {
  id: number;
  date_time: string;
  activate: string;
  details: string;
  credits: string;
  status: string;
}

export default function TransactionPage() {
  const [activeTab, setActiveTab] = useState<"billing" | "activity">("billing");
  const [data, setData] = useState<Billing[] | Activity[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async (type: "billing" | "activity") => {
    setLoading(true);
    try {
      const res = await clientFetch(`/api/transaction?type=${type}`);
      const result = await res.json();
      setData(result);
    } catch (err) {
      console.error("Fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(activeTab);
  }, [activeTab]);

  const formatDate = (date: string) => {
    return new Date(date).toLocaleString('en-US').replace(',', '')
    // return new Date(date).toLocaleString();
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1>Billing & Activity</h1>
        <div className={styles.tabs}>
          <button
            className={activeTab === "billing" ? styles.active : ""}
            onClick={() => setActiveTab("billing")}
          >
            Billing
          </button>
          <button
            className={activeTab === "activity" ? styles.active : ""}
            onClick={() => setActiveTab("activity")}
          >
            Activity
          </button>
        </div>
      </header>

      {loading ? (
        <div className={styles.statusText}>Loading...</div>
      ) : (
        <div className={styles.tableWrapper}>
          <table className={styles.table}>
            <thead>
              {activeTab === "billing" ? (
                <tr>
                  <th>Date</th>
                  <th>Package</th>
                  <th>Amount</th>
                  <th>Status</th>
                </tr>
              ) : (
                <tr>
                  <th>Date</th>
                  <th>Action</th>
                  <th>Details</th>
                  <th>Credits</th>
                  <th>Status</th>
                </tr>
              )}
            </thead>

            <tbody>
              {data.length === 0 ? (
                <tr>
                  <td colSpan={5} className={styles.empty}>
                    No records found.
                  </td>
                </tr>
              ) : activeTab === "billing" ? (
                (data as Billing[]).map((item) => (
                  <tr key={item.id}>
                    <td>{formatDate(item.date_time)}</td>
                    <td>{item.package}</td>
                    <td>{item.amount}</td>
                    <td>
                      <span
                        className={`${styles.status} ${styles[item.status]}`}
                      >
                        {item.status}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                (data as Activity[]).map((item) => (
                  <tr key={item.id}>
                    <td>{formatDate(item.date_time)}</td>
                    <td>{item.activate}</td>
                    <td>{item.details}</td>
                    <td>{item.credits}</td>
                    <td>
                      <span
                        className={`${styles.status} ${styles[item.status]}`}
                      >
                        {item.status}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
