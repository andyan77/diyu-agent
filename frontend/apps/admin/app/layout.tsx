import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Diyu Admin",
  description: "Diyu Agent administration console",
};

export default function AdminLayout({
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
