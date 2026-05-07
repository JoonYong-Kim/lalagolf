import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GolfRaiders",
  description: "Private-first golf performance analysis"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
