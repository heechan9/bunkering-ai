import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "병커시유 · Ocean Lab",
  description: "합성 항차의 급유·소비·잔량을 실제 실험 기록으로 탐색하는 3D 연구 공간.",
  other: {
    "codex-preview": "development",
  },
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body className="antialiased">{children}</body>
    </html>
  );
}
