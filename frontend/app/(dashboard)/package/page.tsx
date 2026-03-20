"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { clientFetch } from "@/lib/client-fetch";
import { CheckCircle2, Sparkles, Zap, Crown } from "lucide-react";
import styles from "./page.module.css";

interface Package {
  id: number;
  name: string;
  price: string;
  recommendation: string;
  features: string[];
}

const ICONS = [Zap, Sparkles, Crown];

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

  if (loading)
    return (
      <div className={styles.loadingState}>
        <div className={styles.loadingBar}>
          <div className={styles.loadingFill} />
        </div>
        <span>Loading Packages…</span>
      </div>
    );

  return (
    <div className={styles.container}>
      <div className={styles.headSection}>
        <p className={styles.eyebrow}>Pricing</p>
        <h1 className={styles.title}>Choose your package</h1>
        <p className={styles.subtitle}>
          Turn novels into AI-generated videos. Select a top-up package to get
          the credits you need.
        </p>
      </div>

      <div className={styles.grid}>
        {packages.map((pkg, i) => {
          const Icon = ICONS[i % ICONS.length];
          const isFeatured = pkg.recommendation
            ?.toLowerCase()
            .includes("best seller");

          return (
            <div
              key={pkg.id}
              className={`${styles.card} ${isFeatured ? styles.cardFeatured : ""}`}
            >
              {isFeatured && (
                <div className={styles.featuredBadge}>Most Popular</div>
              )}

              <div className={styles.cardTop}>
                <div
                  className={`${styles.iconWrap} ${isFeatured ? styles.iconWrapFeatured : ""}`}
                >
                  <Icon size={20} strokeWidth={1.8} />
                </div>
                <div className={styles.cardTag}>
                  {pkg.recommendation || "Plan"}
                </div>
              </div>

              <h2 className={styles.packageName}>{pkg.name}</h2>

              <div className={styles.priceRow}>
                <span className={styles.currency}>฿</span>
                <span className={styles.priceNum}>{pkg.price}</span>
                <span className={styles.priceSuffix}>/mo</span>
              </div>

              <button
                className={`${styles.buyBtn} ${isFeatured ? styles.buyBtnFeatured : ""}`}
                onClick={() => router.push(`/package/${pkg.id}`)}
              >
                Get Started
              </button>

              <div className={styles.divider} />

              <ul className={styles.featureList}>
                {pkg.features?.map((feat, j) => (
                  <li key={j} className={styles.featureItem}>
                    <CheckCircle2 size={14} className={styles.featureIcon} />
                    <span>{feat}</span>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </div>
  );
}
