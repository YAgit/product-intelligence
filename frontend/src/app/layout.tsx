import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Product Intelligence Platform",
  description: "Evidence-first drug and medical-device product intelligence.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
