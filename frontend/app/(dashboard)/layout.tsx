import Sidebar from "@/components/Sidebar";
import Providers from "@/app/providers";
import styles from "./layout.module.css";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <Providers>
      <div className={styles.wrapper}>
        <Sidebar />
        <main className={styles.content}>{children}</main>
      </div>
    </Providers>
  );
}
