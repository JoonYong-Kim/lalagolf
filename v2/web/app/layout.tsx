import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LalaGolf",
  description: "Private-first golf performance analysis"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
