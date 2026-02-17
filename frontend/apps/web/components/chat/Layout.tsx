"use client";

/**
 * Chat dual-pane layout: left sidebar (history) + right chat area.
 *
 * Task card: FW2-1
 * - Responsive: sidebar collapses on mobile
 * - Accessible keyboard navigation
 */

import { useState, type ReactNode } from "react";

interface ChatLayoutProps {
  sidebar: ReactNode;
  children: ReactNode;
}

export function ChatLayout({ sidebar, children }: ChatLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div
      data-testid="chat-layout"
      style={{ display: "flex", height: "100vh", overflow: "hidden" }}
    >
      {/* Sidebar toggle (mobile) */}
      <button
        data-testid="sidebar-toggle"
        onClick={() => setSidebarOpen((prev) => !prev)}
        aria-label={sidebarOpen ? "Close sidebar" : "Open sidebar"}
        style={{
          position: "fixed",
          top: 12,
          left: 12,
          zIndex: 50,
          padding: "8px",
          background: "#f3f4f6",
          border: "1px solid #d1d5db",
          borderRadius: 4,
          cursor: "pointer",
          display: "none",
        }}
      >
        {sidebarOpen ? "<<" : ">>"}
      </button>

      {/* Left: History sidebar */}
      <aside
        data-testid="chat-sidebar"
        aria-label="Conversation history"
        style={{
          width: sidebarOpen ? 280 : 0,
          minWidth: sidebarOpen ? 280 : 0,
          borderRight: "1px solid #e5e7eb",
          overflow: "hidden",
          transition: "width 0.2s, min-width 0.2s",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {sidebar}
      </aside>

      {/* Right: Chat area */}
      <main
        data-testid="chat-main"
        role="main"
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        {children}
      </main>
    </div>
  );
}
