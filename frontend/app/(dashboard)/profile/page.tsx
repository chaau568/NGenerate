"use client";

import { useEffect, useState } from "react";
import { clientFetch } from "@/lib/client-fetch";
import { User, Mail, Lock, Trash2, Edit2, Eye, EyeOff } from "lucide-react";
import SharePopUpDelete from "@/components/SharePopUp_Delete";
import SharePopUpSuccess from "@/components/SharePopUp_Success";
import SharePopUpFailed from "@/components/SharePopUp_Failed";
import { useRouter } from "next/navigation";
import styles from "./page.module.css";

interface ProfileData {
  user_id: number;
  email: string;
  username: string;
  role: string;
  status: string;
  credits: number;
  has_password: boolean;
}

type EditMode = "username" | "email" | "password" | null;

// Error จาก backend มาเป็น { field: string[] | string }
type FieldErrors = Record<string, string>;

export default function ProfilePage() {
  const router = useRouter();

  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);

  // Modals
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isSuccessModalOpen, setIsSuccessModalOpen] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isFailedModalOpen, setIsFailedModalOpen] = useState(false);
  const [failedMsg, setFailedMsg] = useState("");

  // Edit
  const [editMode, setEditMode] = useState<EditMode>(null);
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    old_password: "",
    new_password: "",
  });

  // ✅ per-field errors แสดงใต้ input ที่ถูก
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});

  // ✅ show/hide password toggle แยกแต่ละช่อง
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showOldPassword, setShowOldPassword] = useState(false);

  const [deletePassword, setDeletePassword] = useState("");

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const res = await clientFetch("/api/profile");
      const data = await res.json();
      if (res.ok) {
        setProfile(data);
        setFormData((prev) => ({
          ...prev,
          username: data.username,
          email: data.email,
        }));
      }
    } catch (error) {
      console.error("Fetch profile error:", error);
    } finally {
      setLoading(false);
    }
  };

  // ── reset modal state เมื่อเปิด/ปิด ──────────────────────
  const openEdit = (mode: EditMode) => {
    setEditMode(mode);
    setFieldErrors({});
    setShowNewPassword(false);
    setShowOldPassword(false);
    setFormData((p) => ({ ...p, old_password: "", new_password: "" }));
  };

  const closeEdit = () => {
    setEditMode(null);
    setFieldErrors({});
    setFormData((p) => ({ ...p, old_password: "", new_password: "" }));
  };

  // ── parse backend errors → FieldErrors ───────────────────
  const parseBackendErrors = (result: any): FieldErrors => {
    const errors: FieldErrors = {};
    if (typeof result !== "object" || result === null) return errors;

    for (const key of Object.keys(result)) {
      const val = result[key];
      if (Array.isArray(val)) {
        errors[key] = val[0];
      } else if (typeof val === "string") {
        errors[key] = val;
      }
    }
    return errors;
  };

  // ── submit update ─────────────────────────────────────────
  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setFieldErrors({});

    if (
      (editMode === "username" || editMode === "email") &&
      !profile?.has_password
    ) {
      setFailedMsg("Please set password first.");
      setIsFailedModalOpen(true);
      return;
    }

    try {
      setIsSubmitting(true);

      const payload: Record<string, string> = {};

      if (editMode === "username") payload.username = formData.username;
      if (editMode === "email") payload.email = formData.email;

      if (editMode === "password") {
        if (profile?.has_password) payload.old_password = formData.old_password;
        payload.new_password = formData.new_password;
      }

      if (
        (editMode === "username" || editMode === "email") &&
        profile?.has_password
      ) {
        payload.old_password = formData.old_password;
      }

      const res = await clientFetch("/api/profile", {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      const result = await res.json();

      if (res.ok) {
        setProfile(result);
        setSuccessMsg(`Update ${editMode} successful!`);
        setIsSuccessModalOpen(true);
        closeEdit();
      } else {
        // ✅ parse per-field errors แสดงใต้ input
        const parsed = parseBackendErrors(result);

        if (Object.keys(parsed).length > 0) {
          setFieldErrors(parsed);
        } else {
          setFailedMsg("Update failed.");
          setIsFailedModalOpen(true);
        }
      }
    } catch {
      setFailedMsg("Something went wrong.");
      setIsFailedModalOpen(true);
    } finally {
      setIsSubmitting(false);
    }
  };

  // ── delete account ────────────────────────────────────────
  const handleDeleteAccount = async () => {
    try {
      const res = await clientFetch("/api/profile", {
        method: "DELETE",
        body: JSON.stringify(
          profile?.has_password ? { password: deletePassword } : {},
        ),
      });

      if (res.status === 204) {
        setDeletePassword("");
        window.location.href = "/login";
        return;
      }

      const result = await res.json();
      setFailedMsg(result.detail || result.password || "Delete failed.");
      setIsFailedModalOpen(true);
    } catch {
      setFailedMsg("Something went wrong.");
      setIsFailedModalOpen(true);
    }
  };

  if (loading) return <div className={styles.loading}>Loading Profile...</div>;
  if (!profile) return <div className={styles.loading}>No data found.</div>;

  return (
    <div className={styles.container}>
      <h1 className={styles.pageTitle}>Profile</h1>

      <div className={styles.profileCard}>
        {/* Top Info */}
        <div className={styles.topSection}>
          <div className={styles.avatarWrapper}>
            <div className={styles.avatar}>
              <User size={40} />
            </div>
          </div>
          <div className={styles.infoWrapper}>
            <div className={styles.nameHeader}>
              <div className={styles.usernameGroup}>
                <h2>{profile.username}</h2>
                <button
                  className={styles.iconEditBtn}
                  onClick={() => {
                    if (!profile.has_password) {
                      setFailedMsg("Please set password first.");
                      setIsFailedModalOpen(true);
                      return;
                    }
                    openEdit("username");
                  }}
                >
                  <Edit2 size={16} />
                </button>
              </div>
              <div className={styles.actionButtons}>
                <button
                  className={styles.passwordBtn}
                  onClick={() => openEdit("password")}
                >
                  <Lock size={16} />
                  <span>
                    {profile.has_password ? "Change Password" : "Set Password"}
                  </span>
                </button>
                <button
                  className={styles.deleteBtn}
                  onClick={() => {
                    if (!profile.has_password) {
                      setFailedMsg(
                        "You must set password before deleting account.",
                      );
                      setIsFailedModalOpen(true);
                      return;
                    }
                    setIsDeleteModalOpen(true);
                  }}
                >
                  <Trash2 size={18} />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Credit Section */}
        <div className={styles.creditSection}>
          <div className={styles.creditWallet}>
            <span className={styles.creditTitle}>Your Credits</span>
            <div className={styles.creditAmount}>
              {profile.credits.toLocaleString()}
            </div>
            <p className={styles.creditHint}>
              Credits are used for generating stories, images, and audio.
            </p>
          </div>
          <button
            className={styles.buyCreditBtn}
            onClick={() => router.push("/package")}
          >
            Buy Credits
          </button>
        </div>

        {/* Email Section */}
        <div className={styles.emailContainer}>
          <div className={styles.emailContent}>
            <Mail size={18} className={styles.emailIcon} />
            <div className={styles.emailText}>
              <label>Email Address</label>
              <p>{profile.email}</p>
            </div>
            <button
              className={styles.iconEditBtn}
              onClick={() => {
                if (!profile.has_password) {
                  setFailedMsg("Please set password first.");
                  setIsFailedModalOpen(true);
                  return;
                }
                openEdit("email");
              }}
            >
              <Edit2 size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* ── Edit Modal ── */}
      {editMode && (
        <div className={styles.modalOverlay} onClick={closeEdit}>
          <div
            className={styles.modalContent}
            onClick={(e) => e.stopPropagation()}
          >
            <div className={styles.modalHeader}>
              <h3>
                Edit {editMode.charAt(0).toUpperCase() + editMode.slice(1)}
              </h3>
            </div>

            <form onSubmit={handleUpdate}>
              {/* Username field */}
              {editMode === "username" && (
                <div className={styles.inputGroup}>
                  <label>New Username</label>
                  <input
                    type="text"
                    value={formData.username}
                    onChange={(e) =>
                      setFormData({ ...formData, username: e.target.value })
                    }
                    required
                  />
                  {fieldErrors.username && (
                    <p className={styles.fieldError}>{fieldErrors.username}</p>
                  )}
                </div>
              )}

              {/* Email field */}
              {editMode === "email" && (
                <div className={styles.inputGroup}>
                  <label>New Email Address</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) =>
                      setFormData({ ...formData, email: e.target.value })
                    }
                    required
                  />
                  {fieldErrors.email && (
                    <p className={styles.fieldError}>{fieldErrors.email}</p>
                  )}
                </div>
              )}

              {/* New Password field ✅ มี show/hide */}
              {editMode === "password" && (
                <div className={styles.inputGroup}>
                  <label>New Password</label>
                  <div className={styles.passwordWrapper}>
                    <input
                      type={showNewPassword ? "text" : "password"}
                      placeholder="11–50 characters, uppercase, number, symbol"
                      value={formData.new_password}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          new_password: e.target.value,
                        })
                      }
                      required
                    />
                    <button
                      type="button"
                      className={styles.eyeBtn}
                      onClick={() => setShowNewPassword((v) => !v)}
                    >
                      {showNewPassword ? (
                        <EyeOff size={16} />
                      ) : (
                        <Eye size={16} />
                      )}
                    </button>
                  </div>
                  {/* ✅ แสดง regex error จาก backend */}
                  {fieldErrors.new_password && (
                    <p className={styles.fieldError}>
                      {fieldErrors.new_password}
                    </p>
                  )}
                </div>
              )}

              {/* Current Password field ✅ มี show/hide */}
              {profile.has_password && (
                <div className={styles.inputGroup}>
                  <label>
                    {editMode === "password"
                      ? "Current Password"
                      : "Confirm with Password"}
                  </label>
                  <div className={styles.passwordWrapper}>
                    <input
                      type={showOldPassword ? "text" : "password"}
                      value={formData.old_password}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          old_password: e.target.value,
                        })
                      }
                      required
                    />
                    <button
                      type="button"
                      className={styles.eyeBtn}
                      onClick={() => setShowOldPassword((v) => !v)}
                    >
                      {showOldPassword ? (
                        <EyeOff size={16} />
                      ) : (
                        <Eye size={16} />
                      )}
                    </button>
                  </div>
                  {fieldErrors.old_password && (
                    <p className={styles.fieldError}>
                      {fieldErrors.old_password}
                    </p>
                  )}
                </div>
              )}

              {/* General error (detail) */}
              {fieldErrors.detail && (
                <p className={styles.fieldError}>{fieldErrors.detail}</p>
              )}
              {fieldErrors.non_field_errors && (
                <p className={styles.fieldError}>
                  {fieldErrors.non_field_errors}
                </p>
              )}

              <div className={styles.modalActions}>
                <button
                  type="button"
                  className={styles.cancelBtn}
                  onClick={closeEdit}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className={styles.confirmBtn}
                  disabled={isSubmitting}
                >
                  {isSubmitting ? "Saving..." : "Save Changes"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <SharePopUpDelete
        isOpen={isDeleteModalOpen}
        onClose={() => {
          setIsDeleteModalOpen(false);
          setDeletePassword("");
        }}
        onConfirm={handleDeleteAccount}
        isLoading={isSubmitting}
        title="Delete Account?"
        description={
          <p>
            This action is <strong>permanent</strong>. Please enter your
            password to confirm account deletion.
          </p>
        }
        showPasswordInput={profile?.has_password}
        passwordValue={deletePassword}
        onPasswordChange={setDeletePassword}
      />

      <SharePopUpSuccess
        isOpen={isSuccessModalOpen}
        onClose={() => setIsSuccessModalOpen(false)}
        title={successMsg}
      />

      <SharePopUpFailed
        isOpen={isFailedModalOpen}
        onClose={() => setIsFailedModalOpen(false)}
        message={failedMsg}
      />
    </div>
  );
}
