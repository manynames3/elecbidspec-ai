import Link from "next/link";
import { Activity, ClipboardList, DatabaseZap, Upload, UserRoundCog } from "lucide-react";
import { AuthStatus } from "@/components/AuthStatus";

export default function AppLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-header">
          <Link href="/" className="brand" aria-label="ElecBidSpec AI dashboard">
            <span className="brand-mark">
              <DatabaseZap size={22} />
            </span>
            <span className="brand-copy">
              <span>ElecBidSpec AI</span>
              <span className="brand-descriptor">For electrical contractors &amp; GCs</span>
            </span>
          </Link>
        </div>
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
          <Link href="/admin/sources">
            <Activity size={18} />
            Source Ops
          </Link>
        </nav>
        <div className="sidebar-footer">
          <AuthStatus />
          <p className="sidebar-legal">©2026 SUPREME AI VENTURES LLC</p>
        </div>
      </aside>
      <main className="main-content">{children}</main>
    </div>
  );
}
