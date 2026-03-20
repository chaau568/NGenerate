"use client";

import { useState } from "react";
import { clientFetch } from "@/lib/client-fetch";
import { useForm } from "react-hook-form";
import { useRouter } from "next/navigation";
import { Eye, EyeOff } from "lucide-react";
import styles from "./page.module.css";

type RegisterForm = {
  email: string;
  password: string;
  confirm_password: string;
};
type OtpForm = { otp: string };
type Step = "form" | "otp";

export default function RegisterPage() {
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [step, setStep] = useState<Step>("form");
  const [pendingEmail, setPendingEmail] = useState("");
  const [otpError, setOtpError] = useState("");
  const [otpLoading, setOtpLoading] = useState(false);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<RegisterForm>();

  const {
    register: registerOtp,
    handleSubmit: handleOtpSubmit,
    formState: { errors: otpErrors },
  } = useForm<OtpForm>();

  // ── Step 1 ────────────────────────────────────────────────
  const onSubmit = async (data: RegisterForm) => {
    try {
      const res = await clientFetch("/api/register/request-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      const result = await res.json();

      if (!res.ok) {
        if (result && typeof result === "object") {
          Object.keys(result).forEach((field) => {
            const msg = Array.isArray(result[field])
              ? result[field][0]
              : result[field];
            setError(field as keyof RegisterForm, { message: msg });
          });
        }
        return;
      }

      setPendingEmail(result.email);
      sessionStorage.setItem("register_pending_email", result.email);
      setStep("otp");
    } catch {
      setError("email", { message: "Something went wrong. Please try again." });
    }
  };

  // ── Step 2 ────────────────────────────────────────────────
  const onOtpSubmit = async (data: OtpForm) => {
    const email =
      pendingEmail || sessionStorage.getItem("register_pending_email") || "";
    setOtpError("");
    setOtpLoading(true);
    try {
      const res = await clientFetch("/api/register/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, otp: data.otp }),
      });
      const result = await res.json();
      if (!res.ok) {
        setOtpError(result.error || "Invalid OTP. Please try again.");
        return;
      }
      sessionStorage.removeItem("register_pending_email");
      router.push("/library");
    } catch {
      setOtpError("Something went wrong. Please try again.");
    } finally {
      setOtpLoading(false);
    }
  };

  return (
    <div className={styles.page}>
      {/* Ambient orbs */}
      <div className={styles.orb1} />
      <div className={styles.orb2} />

      <div className={styles.card}>
        {/* ── Logo ── */}
        <div className={styles.logo}>
          <div className={styles.logoMark}>N</div>
          <span className={styles.logoText}>GENERATE</span>
        </div>

        {/* ══ REGISTER STEP ══ */}
        {step === "form" && (
          <>
            <div className={styles.headGroup}>
              <h1 className={styles.title}>Create account</h1>
              <p className={styles.subtitle}>
                Start generating your story today
              </p>
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

              {/* Confirm Password */}
              <div className={styles.field}>
                <label className={styles.label}>Confirm Password</label>
                <div className={styles.inputWrap}>
                  <input
                    className={`${styles.input} ${errors.confirm_password ? styles.inputError : ""}`}
                    type={showConfirmPassword ? "text" : "password"}
                    placeholder="••••••••"
                    {...register("confirm_password", {
                      required: "Confirm password is required",
                    })}
                  />
                  <button
                    type="button"
                    className={styles.eyeBtn}
                    onClick={() => setShowConfirmPassword((v) => !v)}
                    tabIndex={-1}
                  >
                    {showConfirmPassword ? (
                      <EyeOff size={15} />
                    ) : (
                      <Eye size={15} />
                    )}
                  </button>
                </div>
                {errors.confirm_password && (
                  <p className={styles.errorMsg}>
                    {errors.confirm_password.message}
                  </p>
                )}
              </div>

              <button
                className={styles.btn}
                type="submit"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <span className={styles.btnInner}>
                    <span className={styles.spinner} /> Sending OTP…
                  </span>
                ) : (
                  "Create Account"
                )}
              </button>
            </form>

            <p className={styles.footer}>
              Already have an account?{" "}
              <span
                className={styles.footerLink}
                onClick={() => router.push("/login")}
              >
                Sign in here
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
                <strong className={styles.emailHighlight}>
                  {pendingEmail}
                </strong>
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
                  setStep("form");
                  setOtpError("");
                }}
              >
                ← Back
              </span>
            </p>
          </>
        )}
      </div>
    </div>
  );
}
