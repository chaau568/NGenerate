"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { useRouter } from "next/navigation";
import styles from "./page.module.css";

declare global {
  interface Window {
    google: any;
  }
}

type LoginForm = {
  email: string;
  password: string;
};

export default function LoginPage() {
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>();

  const onSubmit = async (data: LoginForm) => {
    try {
      const res = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      const result = await res.json();
      if (!res.ok) throw result;

      router.push("/library");
    } catch (error: any) {
      setError("email", {
        message: error.error || "Invalid email or password",
      });
    }
  };

  useEffect(() => {
    const loadGoogle = () => {
      if (!window.google || !process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID) {
        return;
      }

      window.google.accounts.id.initialize({
        client_id: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID,
        callback: handleGoogleResponse,
      });

      window.google.accounts.id.renderButton(
        document.getElementById("googleButton"),
        {
          theme: "outline",
          size: "large",
          width: 340,
        },
      );
    };

    const interval = setInterval(() => {
      if (window.google) {
        loadGoogle();
        clearInterval(interval);
      }
    }, 300);

    return () => clearInterval(interval);
  }, []);

  const handleGoogleResponse = async (response: any) => {
    try {
      const res = await fetch("/api/login-google", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_token: response.credential }),
      });

      const result = await res.json();
      if (!res.ok) throw result;

      router.push("/library");
    } catch (error: any) {
      setError("email", {
        message: error.error || "Google login failed",
      });
    }
  };

  return (
    <div className={styles.card}>
      <div className={styles.logoContainer}>
        <div className={styles.logoWrapper}>
          <div className={styles.logoBox}>N</div>
          <span className={styles.logoText}>GENERATE</span>
        </div>
      </div>

      <h1 className={styles.title}>Welcome Back</h1>

      <form onSubmit={handleSubmit(onSubmit)}>
        <label className={styles.label}>Email</label>
        <input
          className={styles.input}
          type="email"
          {...register("email", { required: "Email is required" })}
        />
        {errors.email && <p className={styles.error}>{errors.email.message}</p>}

        <label className={styles.label}>Password</label>
        <div className={styles.passwordWrapper}>
          <input
            className={styles.input}
            type={showPassword ? "text" : "password"}
            {...register("password", { required: "Password is required" })}
          />
          <button
            type="button"
            className={styles.toggleButton}
            onMouseEnter={() => setShowPassword(true)}
            onMouseLeave={() => setShowPassword(false)}
          >
            {showPassword ? "Hide" : "Show"}
          </button>
        </div>
        {errors.password && (
          <p className={styles.error}>{errors.password.message}</p>
        )}

        <button className={styles.button} type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Signing In..." : "Sign In"}
        </button>
      </form>

      {/* GOOGLE BUTTON CONTAINER */}
      <div className={styles.googleContainer}>
        <div id="googleButton"></div>
      </div>

      {/* REGISTER LINK */}
      <p className={styles.footerText}>
        Don’t have an account?{" "}
        <span className={styles.link} onClick={() => router.push("/register")}>
          Create one for free
        </span>
      </p>
    </div>
  );
}
