"use client";

import { clientFetch } from "@/lib/client-fetch";
import { useState, useEffect, useRef } from "react";
import { useForm } from "react-hook-form";
import { useRouter } from "next/navigation";
import { Eye, EyeOff } from "lucide-react";
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

  // ── Normal Login ──────────────────────────────────────────
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

  // ── Google Step 1 ─────────────────────────────────────────
  const handleGoogleResponse = async (response: any) => {
    try {
      const res = await clientFetch("/api/login-google", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_token: response.credential }),
      });
      const result = await res.json();
      if (!res.ok) throw result;
      sessionStorage.setItem("otp_email", result.email);
      googleEmailRef.current = result.email;
      setGoogleEmail(result.email);
      setStep("otp");
      setTimeout(() => setFocus("otp"), 100);
    } catch (error: any) {
      setError("email", { message: error.error || "Google login failed" });
    }
  };

  // ── Google Step 2: verify OTP ─────────────────────────────
  const onOtpSubmit = async (data: OtpForm) => {
    const email =
      googleEmailRef.current || sessionStorage.getItem("otp_email") || "";
    setOtpError("");
    setOtpLoading(true);
    try {
      const res = await clientFetch("/api/login-google/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, otp: data.otp }),
      });
      const result = await res.json();
      if (!res.ok) {
        setOtpError(result.error || "Invalid OTP. Please try again.");
        return;
      }
      sessionStorage.removeItem("otp_email");
      router.push("/library");
    } catch {
      setOtpError("Something went wrong. Please try again.");
    } finally {
      setOtpLoading(false);
    }
  };

  // ── Restore from sessionStorage ───────────────────────────
  useEffect(() => {
    const saved = sessionStorage.getItem("otp_email");
    if (saved) {
      googleEmailRef.current = saved;
      setGoogleEmail(saved);
      setStep("otp");
    }
  }, []);

  return (
    <div className={styles.page}>
      {/* Ambient glow orbs */}
      <div className={styles.orb1} />
      <div className={styles.orb2} />

      <div className={styles.card}>
        {/* ── Logo ── */}
        <div className={styles.logo}>
          <div className={styles.logoMark}>N</div>
          <span className={styles.logoText}>GENERATE</span>
        </div>

        {/* ══ LOGIN STEP ══ */}
        {step === "login" && (
          <>
            <div className={styles.headGroup}>
              <h1 className={styles.title}>Welcome back</h1>
              <p className={styles.subtitle}>Sign in to continue creating</p>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className={styles.form}>
              {/* Email */}
              <div className={styles.field}>
                <label className={styles.label}>Email</label>
                <input
                  className={`${styles.input} ${errors.email ? styles.inputError : ""}`}
                  type="email"
                  placeholder="you@example.com"
                  {...register("email", { required: "Email is required" })}
                />
                {errors.email && (
                  <p className={styles.errorMsg}>{errors.email.message}</p>
                )}
              </div>

              {/* Password */}
              <div className={styles.field}>
                <label className={styles.label}>Password</label>
                <div className={styles.inputWrap}>
                  <input
                    className={`${styles.input} ${errors.password ? styles.inputError : ""}`}
                    type={showPassword ? "text" : "password"}
                    placeholder="••••••••"
                    {...register("password", {
                      required: "Password is required",
                    })}
                  />
                  <button
                    type="button"
                    className={styles.eyeBtn}
                    onClick={() => setShowPassword((v) => !v)}
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
                {errors.password && (
                  <p className={styles.errorMsg}>{errors.password.message}</p>
                )}
              </div>

              <button
                className={styles.btn}
                type="submit"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <span className={styles.btnInner}>
                    <span className={styles.spinner} /> Signing in…
                  </span>
                ) : (
                  "Sign In"
                )}
              </button>
            </form>

            {/* Divider */}
            <div className={styles.divider}>
              <span>or continue with</span>
            </div>

            <div className={styles.googleWrap}>
              <div id="googleButton" />
            </div>

            <p className={styles.footer}>
              Don&apos;t have an account?{" "}
              <span
                className={styles.footerLink}
                onClick={() => router.push("/register")}
              >
                Create one for free
              </span>
            </p>
          </>
        )}

        {/* ══ OTP STEP ══ */}
        {step === "otp" && (
          <>
            <div className={styles.headGroup}>
              <h1 className={styles.title}>Check your inbox</h1>
              <p className={styles.subtitle}>
                We sent a 6-digit code to
                <br />
                <strong className={styles.emailHighlight}>{googleEmail}</strong>
              </p>
            </div>

            <form
              onSubmit={handleOtpSubmit(onOtpSubmit)}
              className={styles.form}
            >
              <div className={styles.field}>
                <label className={styles.label}>OTP Code</label>
                <input
                  className={`${styles.input} ${styles.otpInput} ${otpErrors.otp || otpError ? styles.inputError : ""}`}
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  placeholder="000000"
                  {...registerOtp("otp", {
                    required: "OTP is required",
                    pattern: {
                      value: /^\d{6}$/,
                      message: "OTP must be 6 digits",
                    },
                  })}
                />
                {(otpErrors.otp || otpError) && (
                  <p className={styles.errorMsg}>
                    {otpErrors.otp?.message || otpError}
                  </p>
                )}
              </div>

              <button
                className={styles.btn}
                type="submit"
                disabled={otpLoading}
              >
                {otpLoading ? (
                  <span className={styles.btnInner}>
                    <span className={styles.spinner} /> Verifying…
                  </span>
                ) : (
                  "Verify Code"
                )}
              </button>
            </form>

            <p className={styles.footer}>
              <span
                className={styles.footerLink}
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
    </div>
  );
}
