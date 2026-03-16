"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { clientFetch } from "@/lib/client-fetch";
import { CheckCircle2 } from "lucide-react";
import styles from "./page.module.css";

interface Package {
  id: number;
  name: string;
  price: string;
  recommendation: string;
  features: string[];
}

export default function PackageListPage() {
  const [packages, setPackages] = useState<Package[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    clientFetch("/api/package")
      .then((res) => res.json())
      .then((data) => {
        setPackages(data);
        setLoading(false);
      });
  }, []);

  const handleSelect = (id: number) => {
    router.push(`/package/${id}`);
  };

  if (loading) return <div className={styles.loading}>Loading Packages...</div>;

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>All Packages</h1>
      <div className={styles.grid}>
        {packages.map((pkg) => (
          <div key={pkg.id} className={styles.card}>
            <div className={styles.tag}>{pkg.recommendation || "Plan"}</div>
            <h2 className={styles.packageName}>{pkg.name}</h2>
            <div className={styles.price}>
              ฿{pkg.price}
              <span>/month</span>
            </div>
            <button
              className={styles.buyBtn}
              onClick={() => handleSelect(pkg.id)}
            >
              Get Started
            </button>
            <ul className={styles.featureList}>
              {pkg.features?.map((feat, i) => (
                <li key={i} className={styles.featureItem}>
                  <CheckCircle2 size={16} /> {feat}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
