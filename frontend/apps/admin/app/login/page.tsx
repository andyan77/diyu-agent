"use client";

import { type FormEvent, useState } from "react";

interface AdminLoginState {
  email: string;
  password: string;
  twoFactorCode: string;
  error: string | null;
  loading: boolean;
  requiresTwoFactor: boolean;
}

export default function AdminLoginPage() {
  const [state, setState] = useState<AdminLoginState>({
    email: "",
    password: "",
    twoFactorCode: "",
    error: null,
    loading: false,
    requiresTwoFactor: false,
  });

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setState((prev) => ({ ...prev, error: null, loading: true }));

    try {
      const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api";
      const payload: Record<string, string> = {
        email: state.email,
        password: state.password,
      };

      // 2FA slot: include code if the server previously requested it
      if (state.requiresTwoFactor && state.twoFactorCode) {
        payload.two_factor_code = state.twoFactorCode;
      }

      const res = await fetch(`${apiBase}/v1/admin/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));

        // 2FA required response (future implementation)
        if (res.status === 403 && body.requires_two_factor) {
          setState((prev) => ({
            ...prev,
            requiresTwoFactor: true,
            loading: false,
            error: null,
          }));
          return;
        }

        throw new Error(body.message ?? `Admin login failed (${res.status})`);
      }

      const data: { token: string } = await res.json();
      if (typeof window !== "undefined") {
        sessionStorage.setItem("diyu_admin_token", data.token);
      }

      window.location.href = "/";
    } catch (err) {
      const message = err instanceof Error ? err.message : "Login failed";
      setState((prev) => ({ ...prev, error: message, loading: false }));
    }
  }

  return (
    <main
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        minHeight: "100vh",
      }}
    >
      <form
        onSubmit={handleSubmit}
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "1rem",
          width: "100%",
          maxWidth: "400px",
          padding: "2rem",
        }}
        aria-label="Admin login form"
      >
        <h1>Diyu Admin</h1>

        {state.error && (
          <div role="alert" style={{ color: "red" }}>
            {state.error}
          </div>
        )}

        <label htmlFor="admin-email">Email</label>
        <input
          id="admin-email"
          name="email"
          type="email"
          required
          autoComplete="email"
          value={state.email}
          onChange={(e) =>
            setState((prev) => ({ ...prev, email: e.target.value }))
          }
        />

        <label htmlFor="admin-password">Password</label>
        <input
          id="admin-password"
          name="password"
          type="password"
          required
          autoComplete="current-password"
          value={state.password}
          onChange={(e) =>
            setState((prev) => ({ ...prev, password: e.target.value }))
          }
        />

        {state.requiresTwoFactor && (
          <>
            <label htmlFor="two-factor-code">2FA Code</label>
            <input
              id="two-factor-code"
              name="twoFactorCode"
              type="text"
              inputMode="numeric"
              pattern="[0-9]{6}"
              maxLength={6}
              required
              autoComplete="one-time-code"
              placeholder="000000"
              value={state.twoFactorCode}
              onChange={(e) =>
                setState((prev) => ({
                  ...prev,
                  twoFactorCode: e.target.value,
                }))
              }
            />
          </>
        )}

        <button type="submit" disabled={state.loading}>
          {state.loading ? "Logging in..." : "Admin Login"}
        </button>
      </form>
    </main>
  );
}
