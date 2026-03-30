import SidebarAdmin from "@/components/SidebarAdmin";
import Providers from "@/app/providers";
import styles from "./layout.module.css";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <Providers>
      <div className={styles.wrapper}>
        <SidebarAdmin />
        <main className={styles.content}>{children}</main>
      </div>
    </Providers>
  );
}
