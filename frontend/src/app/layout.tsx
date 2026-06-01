import type { Metadata } from "next";
import Link from "next/link";
import { ClipboardList, DatabaseZap, Upload, UserRoundCog } from "lucide-react";
import { AuthStatus } from "@/components/AuthStatus";
import "./globals.css";

export const metadata: Metadata = {
  title: "ElecBidSpec AI",
  description: "Bid intelligence and proposal prep for electrical infrastructure opportunities"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <div className="app-shell">
          <aside className="sidebar">
            <Link href="/" className="brand" aria-label="ElecBidSpec AI dashboard">
              <DatabaseZap size={24} />
              <span>ElecBidSpec AI</span>
            </Link>
            <nav className="nav-links" aria-label="Primary">
              <Link href="/">
                <ClipboardList size={18} />
                Dashboard
              </Link>
              <Link href="/upload">
                <Upload size={18} />
                Upload
              </Link>
              <Link href="/profile">
                <UserRoundCog size={18} />
                Profile
              </Link>
            </nav>
            <AuthStatus />
          </aside>
          <main className="main-content">{children}</main>
        </div>
      </body>
    </html>
  );
}
