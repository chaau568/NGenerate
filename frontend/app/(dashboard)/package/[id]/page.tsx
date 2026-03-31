"use client";

import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter, useParams } from "next/navigation";
import { clientFetch } from "@/lib/client-fetch";
import styles from "./page.module.css";

export default function PaymentPage() {
  const router = useRouter();
  const params = useParams();

  const id = params.id as string;

  const { data, isLoading, isError } = useQuery({
    queryKey: ["payment", id],
    enabled: !!id,
    queryFn: async () => {
      const res = await clientFetch(`/api/package/${id}`);
      const json = await res.json();

      if (!res.ok) {
        throw new Error(json?.message || "Failed to fetch payment");
      }

      return json;
    },
  });

  useEffect(() => {
    if (data?.checkout_url) {
      window.location.href = data.checkout_url;
    }
  }, [data]);

  useEffect(() => {
    if (isError) {
      router.push("/package");
    }
  }, [isError]);

  if (isLoading)
    return (
      <div className={styles.loadingState}>
        <div className={styles.loadingBar}>
          <div className={styles.loadingFill} />
        </div>
        <span>Redirecting to payment...</span>
      </div>
    );

  return null;
}
