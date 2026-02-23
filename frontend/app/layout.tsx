import Script from "next/script";

import { Roboto } from "next/font/google"; 
import "./globals.css";

const roboto = Roboto({
  weight: ["400", "700", "900"],
  subsets: ["latin"],
  display: "swap",
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={roboto.className}>
      <body>
        {children}
        <Script
          src="https://accounts.google.com/gsi/client"
          strategy="afterInteractive"
        />
      </body>
    </html>
  );
}