"use client";

/**
 * Billing & recharge page.
 *
 * Task card: FW4-5
 * XNode: XF4-1 (quota exhaustion -> recharge -> balance update)
 */

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

interface BudgetInfo {
  total_tokens: number;
  used_tokens: number;
  remaining_tokens: number;
  status: string;
}

interface RechargeResult {
  budget_id: string;
  new_total: number;
  status: string;
}

export default function BillingPage() {
  const router = useRouter();
  const [budget, setBudget] = useState<BudgetInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [recharging, setRecharging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rechargeAmount, setRechargeAmount] = useState("100000");

  const apiBase =
    process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8001";

  const getToken = useCallback((): string | null => {
    return sessionStorage.getItem("token");
  }, []);

  const fetchBudget = useCallback(async () => {
    const token = getToken();
    if (!token) {
      router.push("/login");
      return;
    }

    try {
      setLoading(true);
      const res = await fetch(`${apiBase}/api/v1/billing/budget`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.status === 401) {
        sessionStorage.removeItem("token");
        router.push("/login");
        return;
      }

      if (!res.ok) {
        throw new Error(`Failed to fetch budget (${res.status})`);
      }

      const data: BudgetInfo = await res.json();
      setBudget(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load budget");
    } finally {
      setLoading(false);
    }
  }, [apiBase, getToken, router]);

  useEffect(() => {
    fetchBudget();
  }, [fetchBudget]);

  const handleRecharge = useCallback(async () => {
    const token = getToken();
    if (!token) return;

    const amount = parseInt(rechargeAmount, 10);
    if (isNaN(amount) || amount <= 0) {
      setError("Please enter a valid recharge amount");
      return;
    }

    try {
      setRecharging(true);
      const res = await fetch(`${apiBase}/api/v1/billing/recharge`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ tokens: amount }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.message ?? `Recharge failed (${res.status})`);
      }

      const _result: RechargeResult = await res.json();
      setError(null);
      await fetchBudget(); // Refresh balance
    } catch (err) {
      setError(err instanceof Error ? err.message : "Recharge failed");
    } finally {
      setRecharging(false);
    }
  }, [apiBase, getToken, rechargeAmount, fetchBudget]);

  const usagePercent = budget
    ? Math.round((budget.used_tokens / budget.total_tokens) * 100)
    : 0;

  return (
    <main style={{ maxWidth: 600, margin: "40px auto", padding: "0 16px" }}>
      <h1 data-testid="billing-title" style={{ fontSize: 24, marginBottom: 24 }}>
        Billing & Usage
      </h1>

      {loading && <p data-testid="loading">Loading budget...</p>}

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

      {budget && (
        <div data-testid="budget-info">
          <div
            style={{
              background: "#f9fafb",
              border: "1px solid #e5e7eb",
              borderRadius: 8,
              padding: 20,
              marginBottom: 24,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
              <span>Status</span>
              <span
                data-testid="budget-status"
                style={{
                  color: budget.status === "active" ? "#16a34a" : "#dc2626",
                  fontWeight: 600,
                }}
              >
                {budget.status}
              </span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
              <span>Total tokens</span>
              <span data-testid="total-tokens">{budget.total_tokens.toLocaleString()}</span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
              <span>Used</span>
              <span data-testid="used-tokens">{budget.used_tokens.toLocaleString()}</span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
              <span>Remaining</span>
              <span
                data-testid="remaining-tokens"
                style={{ fontWeight: 600 }}
              >
                {budget.remaining_tokens.toLocaleString()}
              </span>
            </div>

            {/* Usage bar */}
            <div
              style={{
                background: "#e5e7eb",
                borderRadius: 4,
                height: 8,
                overflow: "hidden",
              }}
            >
              <div
                data-testid="usage-bar"
                style={{
                  background: usagePercent > 90 ? "#dc2626" : "#3b82f6",
                  width: `${Math.min(usagePercent, 100)}%`,
                  height: "100%",
                  transition: "width 0.3s",
                }}
              />
            </div>
            <p style={{ fontSize: 12, color: "#6b7280", marginTop: 4 }}>
              {usagePercent}% used
            </p>
          </div>

          {/* Recharge section */}
          <div
            style={{
              border: "1px solid #e5e7eb",
              borderRadius: 8,
              padding: 20,
            }}
          >
            <h2 style={{ fontSize: 18, marginBottom: 16 }}>Recharge</h2>
            <div style={{ display: "flex", gap: 8 }}>
              <input
                data-testid="recharge-input"
                type="number"
                value={rechargeAmount}
                onChange={(e) => setRechargeAmount(e.target.value)}
                min="1"
                aria-label="Recharge amount in tokens"
                style={{
                  flex: 1,
                  padding: "8px 12px",
                  border: "1px solid #d1d5db",
                  borderRadius: 8,
                }}
              />
              <button
                data-testid="recharge-button"
                onClick={handleRecharge}
                disabled={recharging || budget.status === "suspended"}
                aria-label="Recharge tokens"
                style={{
                  padding: "8px 24px",
                  background: "#16a34a",
                  color: "white",
                  border: "none",
                  borderRadius: 8,
                  cursor:
                    recharging || budget.status === "suspended"
                      ? "not-allowed"
                      : "pointer",
                  opacity:
                    recharging || budget.status === "suspended" ? 0.5 : 1,
                }}
              >
                {recharging ? "Processing..." : "Recharge"}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
