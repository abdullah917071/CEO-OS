import type { Metadata } from "next";
import { DashboardShell } from "../components/dashboard-shell";
import "./styles.css";

export const metadata: Metadata = {
  title: "CEO OS",
  description: "Local-first personal AI operating system",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body><DashboardShell>{children}</DashboardShell></body>
    </html>
  );
}
