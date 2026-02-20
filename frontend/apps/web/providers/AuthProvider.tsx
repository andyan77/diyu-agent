"use client";

/**
 * AuthProvider + PermissionGate
 *
 * Task card: FW1-2
 * - Unauthenticated -> redirect to /login
 * - Missing permission -> render 403 component
 * - Provides user/org context to child components
 *
 * Dependencies: FW1-1 (Login page)
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";

// --- Types ---

interface AuthUser {
  userId: string;
  orgId: string;
  role: string;
  permissions: string[];
}

interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  logout: () => void;
}

// --- Context ---

const AuthContext = createContext<AuthContextValue>({
  user: null,
  isLoading: true,
  isAuthenticated: false,
  logout: () => {},
});

export function useAuth(): AuthContextValue {
  return useContext(AuthContext);
}

// --- Provider ---

interface AuthProviderProps {
  children: ReactNode;
}

/**
 * Wraps application tree. Reads token from storage,
 * decodes claims, and provides auth state.
 * Redirects to /login when unauthenticated.
 */
export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    try {
      const token =
        typeof window !== "undefined"
          ? sessionStorage.getItem("token")
          : null;

      if (!token) {
        router.replace("/login");
        setIsLoading(false);
        return;
      }

      // Decode JWT payload (base64url, no verification -- server validates)
      const parts = token.split(".");
      if (parts.length !== 3) {
        sessionStorage.removeItem("token");
        router.replace("/login");
        setIsLoading(false);
        return;
      }

      const payload = JSON.parse(atob(parts[1]));
      const now = Math.floor(Date.now() / 1000);
      if (payload.exp && payload.exp < now) {
        sessionStorage.removeItem("token");
        router.replace("/login");
        setIsLoading(false);
        return;
      }

      setUser({
        userId: payload.sub,
        orgId: payload.org,
        role: payload.role ?? "member",
        permissions: payload.permissions ?? [],
      });
    } catch {
      sessionStorage.removeItem("token");
      router.replace("/login");
    } finally {
      setIsLoading(false);
    }
  }, [router]);

  const logout = useCallback(() => {
    sessionStorage.removeItem("token");
    setUser(null);
    router.replace("/login");
  }, [router]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isLoading,
      isAuthenticated: user !== null,
      logout,
    }),
    [user, isLoading, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// --- PermissionGate ---

interface PermissionGateProps {
  /** Required permission string (e.g. "admin:access") */
  required: string;
  /** Content to render when permission is granted */
  children: ReactNode;
  /** Optional fallback for denied access. Defaults to 403 message. */
  fallback?: ReactNode;
}

/**
 * Renders children only if the current user holds the required permission.
 * Otherwise renders a 403 forbidden component.
 */
export function PermissionGate({
  required,
  children,
  fallback,
}: PermissionGateProps) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return null;
  }

  if (!user || !user.permissions.includes(required)) {
    return (
      fallback ?? (
        <div role="alert" data-testid="permission-denied">
          <h2>403 - Forbidden</h2>
          <p>You do not have permission to access this resource.</p>
        </div>
      )
    );
  }

  return <>{children}</>;
}
