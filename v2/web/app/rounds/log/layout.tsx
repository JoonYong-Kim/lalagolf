import type { Metadata, Viewport } from "next";

export const metadata: Metadata = {
  title: "라운드 기록"
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: "#f7f8f6"
};

export default function RoundLogLayout({ children }: { children: React.ReactNode }) {
  return <div className="min-h-screen bg-surface text-ink">{children}</div>;
}
