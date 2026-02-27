"use client";

import { useEffect, useState } from "react";
import { clientFetch } from "@/lib/client-fetch";
import { User, Mail, Lock, Trash2, Edit2, Crown, X } from "lucide-react";
import SharePopUpDelete from "@/components/SharePopUp_Delete";
import SharePopUpSuccess from "@/components/SharePopUp_Success";
import SharePopUpFailed from "@/components/SharePopUp_Failed";
import styles from "./page.module.css";

interface ProfileData {
  user_id: number;
  email: string;
  username: string;
  role: string;
  package: string;
  credits: number;
  limit_credits: number;
  has_password: boolean;
}

type EditMode = "username" | "email" | "password" | null;

export default function ProfilePage() {
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);

  // Modals State
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isSuccessModalOpen, setIsSuccessModalOpen] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Edit State
  const [editMode, setEditMode] = useState<EditMode>(null);
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    old_password: "",
    new_password: "",
  });

  const [isFailedModalOpen, setIsFailedModalOpen] = useState(false);
  const [failedMsg, setFailedMsg] = useState("");

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

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();

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

      const payload: any = {};

      if (editMode === "username") payload.username = formData.username;
      if (editMode === "email") payload.email = formData.email;

      if (editMode === "password") {
        if (profile?.has_password) {
          payload.old_password = formData.old_password;
        }
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
        setEditMode(null);
        setFormData((p) => ({
          ...p,
          old_password: "",
          new_password: "",
        }));
      } else {
        let errorMessage = "Update failed.";

        if (typeof result === "object") {
          const firstKey = Object.keys(result)[0];
          if (Array.isArray(result[firstKey])) {
            errorMessage = result[firstKey][0];
          } else if (typeof result[firstKey] === "string") {
            errorMessage = result[firstKey];
          }
        }

        setFailedMsg(errorMessage);
        setIsFailedModalOpen(true);
      }
    } catch (error) {
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
    } catch (error) {
      setFailedMsg("Something went wrong.");
      setIsFailedModalOpen(true);
    }
  };

  if (loading) return <div className={styles.loading}>Loading Profile...</div>;
  if (!profile) return <div className={styles.loading}>No data found.</div>;

  const creditPercentage =
    profile.limit_credits > 0
      ? (profile.credits / profile.limit_credits) * 100
      : 0;

  return (
    <div className={styles.container}>
      <h1 className={styles.pageTitle}>Profile</h1>

      <div className={styles.profileCard}>
        {/* Top Info Section */}
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
                    setEditMode("username");
                  }}
                >
                  <Edit2 size={16} />
                </button>
              </div>
              <div className={styles.actionButtons}>
                <button
                  className={styles.passwordBtn}
                  onClick={() => setEditMode("password")}
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
            <div className={styles.badgeWrapper}>
              <div className={styles.premiumBadge}>
                <Crown size={14} />
                <span>{profile.package.toUpperCase()} USER</span>
              </div>
            </div>
          </div>
        </div>

        {/* Credit Section */}
        <div className={styles.creditSection}>
          <div className={styles.creditLabelGroup}>
            <span>Credits Remaining</span>
            <span className={styles.creditValue}>
              <strong>{profile.credits.toLocaleString()}</strong>/
              {profile.limit_credits.toLocaleString()}
            </span>
          </div>
          <div className={styles.progressContainer}>
            <div
              className={styles.progressBar}
              style={{ width: `${creditPercentage}%` }}
            />
          </div>
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
                setEditMode("email");
              }}
            >
              <Edit2 size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* EDIT POPUP (Modal) */}
      {editMode && (
        <div className={styles.modalOverlay} onClick={() => setEditMode(null)}>
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
                </div>
              )}

              {editMode === "password" && (
                <div className={styles.inputGroup}>
                  <label>New Password</label>
                  <input
                    type="password"
                    placeholder="At least 8 characters"
                    value={formData.new_password}
                    onChange={(e) =>
                      setFormData({ ...formData, new_password: e.target.value })
                    }
                    required
                  />
                </div>
              )}

              {/* แสดงช่องรหัสผ่านเดิมเสมอถ้า user มีรหัสผ่านอยู่แล้ว เพื่อความปลอดภัย */}
              {profile.has_password && (
                <div className={styles.inputGroup}>
                  <label>
                    {editMode === "password"
                      ? "Current Password"
                      : "Confirm with Password"}
                  </label>
                  <input
                    type="password"
                    value={formData.old_password}
                    onChange={(e) =>
                      setFormData({ ...formData, old_password: e.target.value })
                    }
                    required
                  />
                </div>
              )}

              <div className={styles.modalActions}>
                <button
                  type="button"
                  className={styles.cancelBtn}
                  onClick={() => {
                    setEditMode(null);
                    setFormData((p) => ({
                      ...p,
                      old_password: "",
                      new_password: "",
                    }));
                  }}
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
