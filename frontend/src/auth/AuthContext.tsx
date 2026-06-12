/**
 * AuthContext - app-wide auth state (Phase 9).
 * Location: frontend/src/auth/AuthContext.tsx
 *
 * Holds the current user + token, rehydrates from localStorage on load, and
 * exposes login/signup/logout. Wrap the app in <AuthProvider>. The anonymous
 * mock-interview flow works without ever touching this (no token = no user).
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { authApi, getToken, setToken, type PublicUser, type UserRole } from "../api/platform";

interface AuthState {
  user: PublicUser | null;
  loading: boolean;
  login: (emailOrUsername: string, password: string) => Promise<PublicUser>;
  signup: (body: {
    email: string;
    username: string;
    password: string;
    full_name?: string;
    role: UserRole;
    organization_name?: string;
  }) => Promise<PublicUser>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<PublicUser | null>(null);
  const [loading, setLoading] = useState(true);

  // Rehydrate session from a stored token.
  useEffect(() => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    authApi
      .me()
      .then(setUser)
      .catch(() => {
        setToken(null);
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (emailOrUsername: string, password: string) => {
    const res = await authApi.login({ email_or_username: emailOrUsername, password });
    setToken(res.access_token);
    setUser(res.user);
    return res.user;
  }, []);

  const signup = useCallback<AuthState["signup"]>(async (body) => {
    const res = await authApi.signup(body);
    setToken(res.access_token);
    setUser(res.user);
    return res.user;
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
