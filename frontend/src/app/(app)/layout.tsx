import Link from "next/link";
import { ClipboardList, DatabaseZap, Upload, UserRoundCog } from "lucide-react";
import { AuthStatus } from "@/components/AuthStatus";

export default function AppLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
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
  );
}
