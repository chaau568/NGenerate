"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { useRouter } from "next/navigation";
import styles from "./page.module.css";

type RegisterForm = {
  email: string;
  password: string;
  confirm_password: string;
};

export default function RegisterPage() {
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<RegisterForm>();

  const onSubmit = async (data: RegisterForm) => {
    try {
      const res = await fetch("/api/register", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      const result = await res.json();

      if (!res.ok) {
        throw result;
      }

      router.push("/library"); // register แล้ว login ให้อัตโนมัติ
    } catch (error: any) {
      const apiErrors = error;

      if (apiErrors) {
        Object.keys(apiErrors).forEach((field) => {
          setError(field as keyof RegisterForm, {
            message: apiErrors[field][0],
          });
        });
      }
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

      <h1 className={styles.title}>Create Account</h1>

      <form onSubmit={handleSubmit(onSubmit)}>
        <label className={styles.label}>Email</label>
        <input
          className={styles.input}
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

        <label className={styles.label}>Confirm Password</label>
        <div className={styles.passwordWrapper}>
          <input
            className={styles.input}
            type={showConfirmPassword ? "text" : "password"}
            {...register("confirm_password", {
              required: "Confirm password is required",
            })}
          />
          <button
            type="button"
            className={styles.toggleButton}
            onMouseEnter={() => setShowConfirmPassword(true)}
            onMouseLeave={() => setShowConfirmPassword(false)}
          >
            {showConfirmPassword ? "Hide" : "Show"}
          </button>
        </div>
        {errors.confirm_password && (
          <p className={styles.error}>{errors.confirm_password.message}</p>
        )}

        <button className={styles.button} type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Creating..." : "Create Account"}
        </button>
      </form>

      <p className={styles.footerText}>
        Already have an account?{" "}
        <span className={styles.link} onClick={() => router.push("/login")}>
          Sign in here
        </span>
      </p>
    </div>
  );
}
