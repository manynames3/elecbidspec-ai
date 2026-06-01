import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ElecBidSpec AI",
  description: "Bid intelligence and proposal prep for electrical infrastructure opportunities"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
