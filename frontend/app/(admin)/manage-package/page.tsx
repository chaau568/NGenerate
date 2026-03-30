"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { clientFetch } from "@/lib/client-fetch";
import {
  Plus,
  Pencil,
  Trash2,
  RefreshCw,
  X,
  Check,
  Zap,
  Star,
  ToggleLeft,
  ToggleRight,
  Package,
  Sparkles,
} from "lucide-react";
import styles from "./page.module.css";

/* ── Types ── */
interface PkgFeature {
  text: string;
}

interface Package {
  id: number;
  name: string;
  price: number;
  credits: number;
  recommendation: string | null;
  features: string[];
  is_active: boolean;
  created_at: string;
}

type FormData = {
  name: string;
  price: string;
  credits: string;
  recommendation: string;
  features: string;
  is_active: boolean;
};

const EMPTY_FORM: FormData = {
  name: "",
  price: "",
  credits: "",
  recommendation: "",
  features: "",
  is_active: true,
};

/* ── API ── */
const fetchPackages = async (): Promise<Package[]> => {
  const res = await clientFetch("/api/admin/manage-package");
  if (!res.ok) throw new Error("Failed");
  return res.json();
};

const createPackage = async (body: object) => {
  const res = await clientFetch("/api/admin/manage-package", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
};

const updatePackage = async ({ id, body }: { id: number; body: object }) => {
  const res = await clientFetch(`/api/admin/manage-package/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
};

const deletePackage = async (id: number) => {
  const res = await clientFetch(`/api/admin/manage-package/${id}`, {
    method: "DELETE",
  });
  if (!res.ok && res.status !== 204) throw new Error("Delete failed");
};

/* ── Helpers ── */
const fmt = (n: number) =>
  n >= 1000 ? `${(n / 1000).toFixed(1)}K` : String(n);
const fmtPrice = (n: number) => `฿${Number(n).toLocaleString()}`;

function formToPayload(f: FormData) {
  return {
    name: f.name.trim(),
    price: parseFloat(f.price),
    credits: parseInt(f.credits, 10),
    recommendation: f.recommendation.trim() || null,
    features: f.features
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean),
    is_active: f.is_active,
  };
}

/* ── Component ── */
export default function ManagePackage() {
  const qc = useQueryClient();
  const [modal, setModal] = useState<"create" | "edit" | "delete" | null>(null);
  const [selected, setSelected] = useState<Package | null>(null);
  const [form, setForm] = useState<FormData>(EMPTY_FORM);
  const [error, setError] = useState("");

  const {
    data: packages = [],
    isLoading,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ["admin-packages"],
    queryFn: fetchPackages,
  });

  const invalidate = () =>
    qc.invalidateQueries({ queryKey: ["admin-packages"] });

  const createMut = useMutation({
    mutationFn: createPackage,
    onSuccess: () => {
      invalidate();
      closeModal();
    },
    onError: (e: Error) => setError(e.message),
  });

  const updateMut = useMutation({
    mutationFn: updatePackage,
    onSuccess: () => {
      invalidate();
      closeModal();
    },
    onError: (e: Error) => setError(e.message),
  });

  const deleteMut = useMutation({
    mutationFn: deletePackage,
    onSuccess: () => {
      invalidate();
      closeModal();
    },
  });

  const openCreate = () => {
    setForm(EMPTY_FORM);
    setError("");
    setModal("create");
  };

  const openEdit = (pkg: Package) => {
    setSelected(pkg);
    setForm({
      name: pkg.name,
      price: String(pkg.price),
      credits: String(pkg.credits),
      recommendation: pkg.recommendation ?? "",
      features: (pkg.features ?? []).join("\n"),
      is_active: pkg.is_active,
    });
    setError("");
    setModal("edit");
  };

  const openDelete = (pkg: Package) => {
    setSelected(pkg);
    setModal("delete");
  };

  const closeModal = () => {
    setModal(null);
    setSelected(null);
    setError("");
  };

  const handleSubmit = () => {
    setError("");
    if (!form.name || !form.price || !form.credits) {
      setError("Name, Price and Credits are required");
      return;
    }
    const payload = formToPayload(form);
    if (modal === "create") createMut.mutate(payload);
    if (modal === "edit" && selected)
      updateMut.mutate({ id: selected.id, body: payload });
  };

  const isPending = createMut.isPending || updateMut.isPending;

  return (
    <div className={styles.page}>
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.headerText}>
          <p className={styles.eyebrow}>ADMIN CONSOLE</p>
          <h1 className={styles.title}>Package Manager</h1>
          <p className={styles.subtitle}>
            Create and manage credit packages for users
          </p>
        </div>
        <div className={styles.headerRefresh}>
          <button
            className={`${styles.refreshBtn} ${isFetching ? styles.spinning : ""}`}
            onClick={() => refetch()}
          >
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
        <div className={styles.headerNewPackage}>
          <button className={styles.createBtn} onClick={openCreate}>
            <Plus size={15} /> New Package
          </button>
        </div>
      </header>

      {/* Stats strip */}
      <div className={styles.statsRow}>
        <div className={styles.statChip}>
          <Package size={13} style={{ color: "#3b82f6" }} />
          <span className={styles.statLabel}>Total</span>
          <span className={styles.statVal}>{packages.length}</span>
        </div>
        <div className={styles.statChip}>
          <Check size={13} style={{ color: "#10b981" }} />
          <span className={styles.statLabel}>Active</span>
          <span className={styles.statVal} style={{ color: "#10b981" }}>
            {packages.filter((p) => p.is_active).length}
          </span>
        </div>
        <div className={styles.statChip}>
          <X size={13} style={{ color: "#6b7280" }} />
          <span className={styles.statLabel}>Inactive</span>
          <span className={styles.statVal} style={{ color: "#6b7280" }}>
            {packages.filter((p) => !p.is_active).length}
          </span>
        </div>
      </div>

      {/* Package grid */}
      {isLoading ? (
        <div className={styles.skeletonGrid}>
          {Array(4)
            .fill(null)
            .map((_, i) => (
              <div key={i} className={styles.skeletonCard} />
            ))}
        </div>
      ) : packages.length === 0 ? (
        <div className={styles.empty}>
          <Sparkles size={40} strokeWidth={1.2} />
          <p>No packages yet. Create your first one.</p>
        </div>
      ) : (
        <div className={styles.grid}>
          {packages.map((pkg) => (
            <div
              key={pkg.id}
              className={`${styles.card} ${!pkg.is_active ? styles.cardInactive : ""}`}
            >
              {/* Glow accent */}
              <div className={styles.cardGlow} />

              {/* Badge row */}
              <div className={styles.cardTop}>
                <span
                  className={`${styles.activeBadge} ${pkg.is_active ? styles.badgeOn : styles.badgeOff}`}
                >
                  {pkg.is_active ? (
                    <ToggleRight size={11} />
                  ) : (
                    <ToggleLeft size={11} />
                  )}
                  {pkg.is_active ? "Active" : "Inactive"}
                </span>
                {pkg.recommendation && (
                  <span className={styles.recBadge}>
                    <Star size={9} fill="currentColor" /> {pkg.recommendation}
                  </span>
                )}
              </div>

              {/* Name + price */}
              <p className={styles.cardName}>{pkg.name}</p>
              <p className={styles.cardPrice}>{fmtPrice(pkg.price)}</p>

              {/* Credits */}
              <div className={styles.creditsRow}>
                <Zap size={13} style={{ color: "#3b82f6" }} />
                <span className={styles.creditsVal}>{fmt(pkg.credits)}</span>
                <span className={styles.creditsLabel}>credits</span>
              </div>

              {/* Features */}
              {pkg.features?.length > 0 && (
                <ul className={styles.featureList}>
                  {pkg.features.slice(0, 4).map((f, i) => (
                    <li key={i} className={styles.featureItem}>
                      <span className={styles.featureDot} /> {f}
                    </li>
                  ))}
                  {pkg.features.length > 4 && (
                    <li className={styles.featureMore}>
                      +{pkg.features.length - 4} more
                    </li>
                  )}
                </ul>
              )}

              {/* Actions */}
              <div className={styles.cardActions}>
                <button
                  className={styles.editBtn}
                  onClick={() => openEdit(pkg)}
                >
                  <Pencil size={13} /> Edit
                </button>
                <button
                  className={styles.deleteBtn}
                  onClick={() => openDelete(pkg)}
                >
                  <Trash2 size={13} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── MODAL OVERLAY ── */}
      {modal && (
        <div className={styles.overlay} onClick={closeModal}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            {/* Delete confirm */}
            {modal === "delete" && selected && (
              <>
                <div className={styles.modalHeader}>
                  <h2 className={styles.modalTitle}>Delete Package</h2>
                  <button className={styles.closeBtn} onClick={closeModal}>
                    <X size={16} />
                  </button>
                </div>
                <p className={styles.deleteDesc}>
                  Delete <strong>{selected.name}</strong>? This action cannot be
                  undone.
                </p>
                <div className={styles.modalFooter}>
                  <button className={styles.cancelBtn} onClick={closeModal}>
                    Cancel
                  </button>
                  <button
                    className={styles.confirmDeleteBtn}
                    onClick={() => deleteMut.mutate(selected.id)}
                    disabled={deleteMut.isPending}
                  >
                    {deleteMut.isPending ? "Deleting…" : "Delete"}
                  </button>
                </div>
              </>
            )}

            {/* Create / Edit form */}
            {(modal === "create" || modal === "edit") && (
              <>
                <div className={styles.modalHeader}>
                  <h2 className={styles.modalTitle}>
                    {modal === "create" ? "New Package" : "Edit Package"}
                  </h2>
                  <button className={styles.closeBtn} onClick={closeModal}>
                    <X size={16} />
                  </button>
                </div>

                <div className={styles.formGrid}>
                  <div className={styles.field}>
                    <label className={styles.label}>Package Name *</label>
                    <input
                      className={styles.input}
                      placeholder="e.g. Starter Pack"
                      value={form.name}
                      onChange={(e) =>
                        setForm({ ...form, name: e.target.value })
                      }
                    />
                  </div>

                  <div className={styles.fieldRow}>
                    <div className={styles.field}>
                      <label className={styles.label}>Price (THB) *</label>
                      <input
                        className={styles.input}
                        type="number"
                        placeholder="299"
                        value={form.price}
                        onChange={(e) =>
                          setForm({ ...form, price: e.target.value })
                        }
                      />
                    </div>
                    <div className={styles.field}>
                      <label className={styles.label}>Credits *</label>
                      <input
                        className={styles.input}
                        type="number"
                        placeholder="100"
                        value={form.credits}
                        onChange={(e) =>
                          setForm({ ...form, credits: e.target.value })
                        }
                      />
                    </div>
                  </div>

                  <div className={styles.field}>
                    <label className={styles.label}>Recommendation Tag</label>
                    <input
                      className={styles.input}
                      placeholder="e.g. Most Popular"
                      value={form.recommendation}
                      onChange={(e) =>
                        setForm({ ...form, recommendation: e.target.value })
                      }
                    />
                  </div>

                  <div className={styles.field}>
                    <label className={styles.label}>
                      Features (one per line)
                    </label>
                    <textarea
                      className={styles.textarea}
                      rows={4}
                      placeholder={
                        "HD video generation\nUnlimited revisions\nPriority support"
                      }
                      value={form.features}
                      onChange={(e) =>
                        setForm({ ...form, features: e.target.value })
                      }
                    />
                  </div>

                  <div className={styles.toggleField}>
                    <span className={styles.label}>Active</span>
                    <button
                      type="button"
                      className={`${styles.toggleBtn} ${form.is_active ? styles.toggleOn : styles.toggleOff}`}
                      onClick={() =>
                        setForm({ ...form, is_active: !form.is_active })
                      }
                    >
                      {form.is_active ? (
                        <ToggleRight size={20} />
                      ) : (
                        <ToggleLeft size={20} />
                      )}
                      <span>{form.is_active ? "Enabled" : "Disabled"}</span>
                    </button>
                  </div>
                </div>

                {error && <p className={styles.errorMsg}>{error}</p>}

                <div className={styles.modalFooter}>
                  <button className={styles.cancelBtn} onClick={closeModal}>
                    Cancel
                  </button>
                  <button
                    className={styles.submitBtn}
                    onClick={handleSubmit}
                    disabled={isPending}
                  >
                    {isPending
                      ? modal === "create"
                        ? "Creating…"
                        : "Saving…"
                      : modal === "create"
                        ? "Create Package"
                        : "Save Changes"}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
