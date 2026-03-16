"use client";

import { clientFetch } from "@/lib/client-fetch";
import { useState, useEffect, useRef } from "react";
import { useForm } from "react-hook-form";
import { useRouter } from "next/navigation";
import styles from "./page.module.css";

declare global {
  interface Window {
    google: any;
  }
}

type LoginForm = { email: string; password: string };
type OtpForm = { otp: string };
type Step = "login" | "otp";

export default function LoginPage() {
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const [step, setStep] = useState<Step>("login");
  const [googleEmail, setGoogleEmail] = useState("");
  const googleEmailRef = useRef("");
  const [otpError, setOtpError] = useState("");
  const [otpLoading, setOtpLoading] = useState(false);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>();

  const {
    register: registerOtp,
    handleSubmit: handleOtpSubmit,
    formState: { errors: otpErrors },
    setFocus,
  } = useForm<OtpForm>();

  // ── Normal Login ─────────────────────────────────────────
  const onSubmit = async (data: LoginForm) => {
    try {
      const res = await clientFetch("/api/login", {
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

  // ── Load Google Button ────────────────────────────────────
  useEffect(() => {
    const loadGoogle = () => {
      if (!window.google || !process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID) return;
      window.google.accounts.id.initialize({
        client_id: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID,
        callback: handleGoogleResponse,
      });
      window.google.accounts.id.renderButton(
        document.getElementById("googleButton"),
        { theme: "outline", size: "large", width: 340 },
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

  // ── Google Step 1: ส่ง id_token → รอ OTP ────────────────
  const handleGoogleResponse = async (response: any) => {
    try {
      const res = await clientFetch("/api/login-google", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_token: response.credential }),
      });
      const result = await res.json();
      console.log("google login result:", result);
      if (!res.ok) throw result;

      // ✅ เก็บใน sessionStorage แทน state/ref
      sessionStorage.setItem("otp_email", result.email);

      googleEmailRef.current = result.email;
      setGoogleEmail(result.email);
      setStep("otp");
      setTimeout(() => setFocus("otp"), 100);
    } catch (error: any) {
      setError("email", { message: error.error || "Google login failed" });
    }
  };

  // ── Google Step 2: verify OTP → JWT ─────────────────────
  const onOtpSubmit = async (data: OtpForm) => {
    // ✅ อ่านจาก sessionStorage เป็น fallback
    const email =
      googleEmailRef.current || sessionStorage.getItem("otp_email") || "";

    setOtpError("");
    setOtpLoading(true);

    try {
      const res = await clientFetch("/api/verify-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, otp: data.otp }),
      });
      const result = await res.json();

      if (!res.ok) {
        setOtpError(result.error || "Invalid OTP. Please try again.");
        return;
      }

      // ✅ ล้างหลัง verify สำเร็จ
      sessionStorage.removeItem("otp_email");
      router.push("/library");
    } catch {
      setOtpError("Something went wrong. Please try again.");
    } finally {
      setOtpLoading(false);
    }
  };

  // ── restore state จาก sessionStorage เผื่อ page reload ──
  useEffect(() => {
    const savedEmail = sessionStorage.getItem("otp_email");
    if (savedEmail) {
      googleEmailRef.current = savedEmail;
      setGoogleEmail(savedEmail);
      setStep("otp");
    }
  }, []);

  // ── Single JSX block — ป้องกัน unmount/remount ──────────
  return (
    <div className={styles.card}>
      {/* Logo — แสดงทุก step */}
      <div className={styles.logoContainer}>
        <div className={styles.logoWrapper}>
          <div className={styles.logoBox}>N</div>
          <span className={styles.logoText}>GENERATE</span>
        </div>
      </div>

      {/* ── Login Step ── */}
      {step === "login" && (
        <>
          <h1 className={styles.title}>Welcome Back</h1>

          <form onSubmit={handleSubmit(onSubmit)}>
            <label className={styles.label}>Email</label>
            <input
              className={styles.input}
              type="email"
              {...register("email", { required: "Email is required" })}
            />
            {errors.email && (
              <p className={styles.error}>{errors.email.message}</p>
            )}

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

            <button
              className={styles.button}
              type="submit"
              disabled={isSubmitting}
            >
              {isSubmitting ? "Signing In..." : "Sign In"}
            </button>
          </form>

          <div className={styles.googleContainer}>
            <div id="googleButton" />
          </div>

          <p className={styles.footerText}>
            Don't have an account?{" "}
            <span
              className={styles.link}
              onClick={() => router.push("/register")}
            >
              Create one for free
            </span>
          </p>
        </>
      )}

      {/* ── OTP Step ── */}
      {step === "otp" && (
        <>
          <h1 className={styles.title}>Verify Your Email</h1>

          <p
            style={{
              textAlign: "center",
              color: "#94a3b8",
              fontSize: 14,
              marginBottom: 24,
            }}
          >
            We sent a 6-digit OTP to
            <br />
            <strong style={{ color: "white" }}>{googleEmail}</strong>
          </p>

          <form onSubmit={handleOtpSubmit(onOtpSubmit)}>
            <label className={styles.label}>OTP Code</label>
            <input
              className={styles.input}
              type="text"
              inputMode="numeric"
              maxLength={6}
              placeholder="000000"
              style={{ textAlign: "center", fontSize: 24, letterSpacing: 8 }}
              {...registerOtp("otp", {
                required: "OTP is required",
                pattern: {
                  value: /^\d{6}$/,
                  message: "OTP must be 6 digits",
                },
              })}
            />
            {(otpErrors.otp || otpError) && (
              <p className={styles.error}>
                {otpErrors.otp?.message || otpError}
              </p>
            )}

            <button
              className={styles.button}
              type="submit"
              disabled={otpLoading}
            >
              {otpLoading ? "Verifying..." : "Verify OTP"}
            </button>
          </form>

          <p className={styles.footerText}>
            <span
              className={styles.link}
              onClick={() => {
                setStep("login");
                setOtpError("");
              }}
            >
              ← Back to login
            </span>
          </p>
        </>
      )}
    </div>
  );
}
