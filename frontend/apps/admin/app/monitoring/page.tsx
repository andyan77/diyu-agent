"use client";

/**
 * System monitoring dashboard.
 *
 * Task card: FA4-1
 * XNode: XF4-2 (system monitoring dashboard)
 *
 * Displays real-time system metrics from /api/v1/admin/status endpoint.
 */

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

interface SystemStatus {
  healthy: boolean;
  uptime_seconds: number;
  version: string;
  services: {
    database: ServiceStatus;
    redis: ServiceStatus;
    neo4j: ServiceStatus;
    qdrant: ServiceStatus;
    celery: ServiceStatus;
  };
  metrics: {
    active_requests: number;
    total_requests: number;
    error_rate: number;
    p95_latency_ms: number;
    memory_mb: number;
  };
}

interface ServiceStatus {
  status: "healthy" | "degraded" | "down";
  latency_ms: number;
}

function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (days > 0) return `${days}d ${hours}h ${minutes}m`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, { bg: string; text: string }> = {
    healthy: { bg: "#dcfce7", text: "#16a34a" },
    degraded: { bg: "#fef3c7", text: "#d97706" },
    down: { bg: "#fef2f2", text: "#dc2626" },
  };
  const c = colors[status] ?? colors.down;
  return (
    <span
      data-testid={`status-${status}`}
      style={{
        background: c.bg,
        color: c.text,
        padding: "2px 8px",
        borderRadius: 12,
        fontSize: 12,
        fontWeight: 600,
      }}
    >
      {status}
    </span>
  );
}

export default function MonitoringPage() {
  const router = useRouter();
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const apiBase =
    process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8001";

  const fetchStatus = useCallback(async () => {
    const token = sessionStorage.getItem("admin_token");
    if (!token) {
      router.push("/login");
      return;
    }

    try {
      const res = await fetch(`${apiBase}/api/v1/admin/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.status === 401 || res.status === 403) {
        sessionStorage.removeItem("admin_token");
        router.push("/login");
        return;
      }

      if (!res.ok) {
        throw new Error(`Failed to fetch status (${res.status})`);
      }

      const data: SystemStatus = await res.json();
      setStatus(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connection failed");
    } finally {
      setLoading(false);
    }
  }, [apiBase, router]);

  useEffect(() => {
    fetchStatus();

    if (!autoRefresh) return;
    const interval = setInterval(fetchStatus, 10_000);
    return () => clearInterval(interval);
  }, [fetchStatus, autoRefresh]);

  return (
    <div style={{ maxWidth: 900, margin: "24px auto", padding: "0 16px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <h1 data-testid="monitoring-title" style={{ fontSize: 24 }}>
          System Monitoring
        </h1>
        <label style={{ fontSize: 14, display: "flex", alignItems: "center", gap: 6 }}>
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.target.checked)}
            data-testid="auto-refresh-toggle"
          />
          Auto-refresh (10s)
        </label>
      </div>

      {loading && <p data-testid="loading">Loading system status...</p>}

      {error && (
        <div
          data-testid="error-message"
          role="alert"
          style={{
            background: "#fef2f2",
            border: "1px solid #fecaca",
            padding: 12,
            borderRadius: 8,
            marginBottom: 16,
            color: "#dc2626",
          }}
        >
          {error}
        </div>
      )}

      {status && (
        <>
          {/* Overview cards */}
          <div
            data-testid="overview-cards"
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: 16,
              marginBottom: 24,
            }}
          >
            <div style={{ background: "#f9fafb", border: "1px solid #e5e7eb", borderRadius: 8, padding: 16 }}>
              <div style={{ fontSize: 12, color: "#6b7280" }}>Health</div>
              <div data-testid="overall-health" style={{ fontSize: 20, fontWeight: 600, marginTop: 4 }}>
                {status.healthy ? "Healthy" : "Unhealthy"}
              </div>
            </div>
            <div style={{ background: "#f9fafb", border: "1px solid #e5e7eb", borderRadius: 8, padding: 16 }}>
              <div style={{ fontSize: 12, color: "#6b7280" }}>Uptime</div>
              <div data-testid="uptime" style={{ fontSize: 20, fontWeight: 600, marginTop: 4 }}>
                {formatUptime(status.uptime_seconds)}
              </div>
            </div>
            <div style={{ background: "#f9fafb", border: "1px solid #e5e7eb", borderRadius: 8, padding: 16 }}>
              <div style={{ fontSize: 12, color: "#6b7280" }}>P95 Latency</div>
              <div data-testid="p95-latency" style={{ fontSize: 20, fontWeight: 600, marginTop: 4 }}>
                {status.metrics.p95_latency_ms}ms
              </div>
            </div>
            <div style={{ background: "#f9fafb", border: "1px solid #e5e7eb", borderRadius: 8, padding: 16 }}>
              <div style={{ fontSize: 12, color: "#6b7280" }}>Error Rate</div>
              <div data-testid="error-rate" style={{ fontSize: 20, fontWeight: 600, marginTop: 4 }}>
                {(status.metrics.error_rate * 100).toFixed(2)}%
              </div>
            </div>
          </div>

          {/* Service status table */}
          <div style={{ border: "1px solid #e5e7eb", borderRadius: 8, overflow: "hidden", marginBottom: 24 }}>
            <h2 style={{ fontSize: 16, padding: "12px 16px", background: "#f9fafb", margin: 0, borderBottom: "1px solid #e5e7eb" }}>
              Services
            </h2>
            <table data-testid="services-table" style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #e5e7eb" }}>
                  <th style={{ textAlign: "left", padding: "8px 16px", fontSize: 14 }}>Service</th>
                  <th style={{ textAlign: "left", padding: "8px 16px", fontSize: 14 }}>Status</th>
                  <th style={{ textAlign: "right", padding: "8px 16px", fontSize: 14 }}>Latency</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(status.services).map(([name, svc]) => (
                  <tr key={name} style={{ borderBottom: "1px solid #f3f4f6" }}>
                    <td style={{ padding: "8px 16px", fontSize: 14 }}>{name}</td>
                    <td style={{ padding: "8px 16px" }}>
                      <StatusBadge status={svc.status} />
                    </td>
                    <td style={{ padding: "8px 16px", textAlign: "right", fontSize: 14 }}>
                      {svc.latency_ms}ms
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Request metrics */}
          <div style={{ border: "1px solid #e5e7eb", borderRadius: 8, padding: 16 }}>
            <h2 style={{ fontSize: 16, marginBottom: 12 }}>Request Metrics</h2>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div>
                <span style={{ fontSize: 12, color: "#6b7280" }}>Active Requests</span>
                <div data-testid="active-requests" style={{ fontSize: 18, fontWeight: 600 }}>
                  {status.metrics.active_requests}
                </div>
              </div>
              <div>
                <span style={{ fontSize: 12, color: "#6b7280" }}>Total Requests</span>
                <div data-testid="total-requests" style={{ fontSize: 18, fontWeight: 600 }}>
                  {status.metrics.total_requests.toLocaleString()}
                </div>
              </div>
              <div>
                <span style={{ fontSize: 12, color: "#6b7280" }}>Memory Usage</span>
                <div data-testid="memory-usage" style={{ fontSize: 18, fontWeight: 600 }}>
                  {status.metrics.memory_mb} MB
                </div>
              </div>
              <div>
                <span style={{ fontSize: 12, color: "#6b7280" }}>Version</span>
                <div data-testid="version" style={{ fontSize: 18, fontWeight: 600 }}>
                  {status.version}
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
