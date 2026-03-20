"use client";

import { useEffect, useState } from "react";
import { clientFetch } from "@/lib/client-fetch";
import {
  Mail,
  Lock,
  Trash2,
  Edit2,
  Eye,
  EyeOff,
  Coins,
  ShoppingBag,
} from "lucide-react";
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
type FieldErrors = Record<string, string>;

export default function ProfilePage() {
  const router = useRouter();
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isSuccessModalOpen, setIsSuccessModalOpen] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isFailedModalOpen, setIsFailedModalOpen] = useState(false);
  const [failedMsg, setFailedMsg] = useState("");
  const [editMode, setEditMode] = useState<EditMode>(null);
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    old_password: "",
    new_password: "",
  });
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
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
        setFormData((p) => ({
          ...p,
          username: data.username,
          email: data.email,
        }));
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

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

  const parseBackendErrors = (result: any): FieldErrors => {
    const errors: FieldErrors = {};
    if (typeof result !== "object" || result === null) return errors;
    for (const key of Object.keys(result)) {
      const val = result[key];
      errors[key] = Array.isArray(val) ? val[0] : String(val);
    }
    return errors;
  };

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
      )
        payload.old_password = formData.old_password;

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
        const parsed = parseBackendErrors(result);
        if (Object.keys(parsed).length > 0) setFieldErrors(parsed);
        else {
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

  if (loading)
    return (
      <div className={styles.loadingState}>
        <div className={styles.loadingBar}>
          <div className={styles.loadingFill} />
        </div>
        <span>Loading Profile…</span>
      </div>
    );
  if (!profile) return <div className={styles.loading}>No data found.</div>;

  const initials = profile.username.slice(0, 2).toUpperCase();

  return (
    <div className={styles.container}>
      <div className={styles.pageHead}>
        <h1 className={styles.pageTitle}>Profile</h1>
        <p className={styles.pageSubtitle}>
          Manage your account details and credits
        </p>
      </div>

      <div className={styles.grid}>
        {/* ── LEFT: Identity card ── */}
        <div className={styles.identityCard}>
          <div className={styles.avatarBlock}>
            <div className={styles.avatar}>{initials}</div>
            <div className={styles.avatarInfo}>
              <div className={styles.usernameRow}>
                <h2 className={styles.username}>{profile.username}</h2>
                <button
                  className={styles.editIconBtn}
                  onClick={() => {
                    if (!profile.has_password) {
                      setFailedMsg("Please set password first.");
                      setIsFailedModalOpen(true);
                      return;
                    }
                    openEdit("username");
                  }}
                >
                  <Edit2 size={14} />
                </button>
              </div>
              <span className={styles.roleBadge}>{profile.role}</span>
            </div>
          </div>

          <div className={styles.separator} />

          {/* Email */}
          <div className={styles.fieldRow}>
            <div className={styles.fieldIcon}>
              <Mail size={15} />
            </div>
            <div className={styles.fieldContent}>
              <p className={styles.fieldLabel}>Email</p>
              <p className={styles.fieldValue}>{profile.email}</p>
            </div>
            <button
              className={styles.editIconBtn}
              onClick={() => {
                if (!profile.has_password) {
                  setFailedMsg("Please set password first.");
                  setIsFailedModalOpen(true);
                  return;
                }
                openEdit("email");
              }}
            >
              <Edit2 size={14} />
            </button>
          </div>

          {/* Password */}
          <div className={styles.fieldRow}>
            <div className={styles.fieldIcon}>
              <Lock size={15} />
            </div>
            <div className={styles.fieldContent}>
              <p className={styles.fieldLabel}>Password</p>
              <p className={styles.fieldValue}>
                {profile.has_password ? "••••••••" : "Not set"}
              </p>
            </div>
            <button
              className={styles.editIconBtn}
              onClick={() => openEdit("password")}
            >
              <Edit2 size={14} />
            </button>
          </div>

          <div className={styles.separator} />

          {/* Danger zone */}
          <button
            className={styles.deleteBtn}
            onClick={() => {
              if (!profile.has_password) {
                setFailedMsg("You must set password before deleting account.");
                setIsFailedModalOpen(true);
                return;
              }
              setIsDeleteModalOpen(true);
            }}
          >
            <Trash2 size={14} />
            Delete Account
          </button>
        </div>

        {/* ── RIGHT: Credits card ── */}
        <div className={styles.creditsCard}>
          <div className={styles.creditsTop}>
            <div className={styles.creditsIconWrap}>
              <Coins size={20} />
            </div>
            <p className={styles.creditsLabel}>Available Credits</p>
          </div>
          <div className={styles.creditsAmount}>
            {profile.credits.toLocaleString()}
          </div>
          <p className={styles.creditsHint}>
            Used for generating images, voice, and video from your stories.
          </p>

          <div className={styles.creditsMeter}>
            <div
              className={styles.creditsMeterFill}
              style={{
                width: `${Math.min((profile.credits / 5000) * 100, 100)}%`,
              }}
            />
          </div>

          <button
            className={styles.buyBtn}
            onClick={() => router.push("/package")}
          >
            <ShoppingBag size={15} />
            Buy Credits
          </button>
        </div>
      </div>

      {/* ── Edit Modal ── */}
      {editMode && (
        <div className={styles.overlay} onClick={closeEdit}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h3 className={styles.modalTitle}>
              {editMode === "password"
                ? profile.has_password
                  ? "Change Password"
                  : "Set Password"
                : `Edit ${editMode.charAt(0).toUpperCase() + editMode.slice(1)}`}
            </h3>

            <form onSubmit={handleUpdate}>
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

              {editMode === "password" && (
                <div className={styles.inputGroup}>
                  <label>New Password</label>
                  <div className={styles.pwWrap}>
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
                        <EyeOff size={15} />
                      ) : (
                        <Eye size={15} />
                      )}
                    </button>
                  </div>
                  {fieldErrors.new_password && (
                    <p className={styles.fieldError}>
                      {fieldErrors.new_password}
                    </p>
                  )}
                </div>
              )}

              {profile.has_password && (
                <div className={styles.inputGroup}>
                  <label>
                    {editMode === "password"
                      ? "Current Password"
                      : "Confirm with Password"}
                  </label>
                  <div className={styles.pwWrap}>
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
                        <EyeOff size={15} />
                      ) : (
                        <Eye size={15} />
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
            This action is <strong>permanent</strong>. Enter your password to
            confirm.
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
