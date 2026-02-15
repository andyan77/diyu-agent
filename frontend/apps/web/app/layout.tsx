import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Diyu Agent",
  description: "AI-powered intelligent work assistant",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
