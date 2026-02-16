"use client";

import { type FormEvent, useState } from "react";

interface LoginFormState {
  email: string;
  password: string;
  error: string | null;
  loading: boolean;
}

export default function LoginPage() {
  const [state, setState] = useState<LoginFormState>({
    email: "",
    password: "",
    error: null,
    loading: false,
  });

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setState((prev) => ({ ...prev, error: null, loading: true }));

    try {
      const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api";
      const res = await fetch(`${apiBase}/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: state.email,
          password: state.password,
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.message ?? `Login failed (${res.status})`);
      }

      const data: { token: string } = await res.json();
      if (typeof window !== "undefined") {
        sessionStorage.setItem("diyu_token", data.token);
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
        aria-label="Login form"
      >
        <h1>Diyu Agent</h1>

        {state.error && (
          <div role="alert" style={{ color: "red" }}>
            {state.error}
          </div>
        )}

        <label htmlFor="email">Email</label>
        <input
          id="email"
          name="email"
          type="email"
          required
          autoComplete="email"
          value={state.email}
          onChange={(e) =>
            setState((prev) => ({ ...prev, email: e.target.value }))
          }
        />

        <label htmlFor="password">Password</label>
        <input
          id="password"
          name="password"
          type="password"
          required
          autoComplete="current-password"
          value={state.password}
          onChange={(e) =>
            setState((prev) => ({ ...prev, password: e.target.value }))
          }
        />

        <button type="submit" disabled={state.loading}>
          {state.loading ? "Logging in..." : "Login"}
        </button>
      </form>
    </main>
  );
}
