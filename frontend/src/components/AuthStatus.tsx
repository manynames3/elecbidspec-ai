"use client";

import { FormEvent, useEffect, useState } from "react";
import { LogIn, LogOut } from "lucide-react";
import { apiFetch, clearAuthToken, setAuthToken } from "@/lib/api";
import type { AuthUser, LoginResponse } from "@/lib/types";

export function AuthStatus() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadMe() {
      try {
        setUser(await apiFetch<AuthUser>("/auth/me"));
      } catch {
        clearAuthToken();
      }
    }
    void loadMe();
  }, []);

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      const response = await apiFetch<LoginResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password })
      });
      setAuthToken(response.token);
      setUser(response.user);
      setPassword("");
      window.dispatchEvent(new Event("elecbidspec-auth-changed"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  }

  async function logout() {
    try {
      await apiFetch<{ status: string }>("/auth/logout", { method: "POST" });
    } catch {
      // Clearing the browser token is enough if the server session is already gone.
    }
    clearAuthToken();
    setUser(null);
    window.dispatchEvent(new Event("elecbidspec-auth-changed"));
  }

  if (user) {
    return (
      <div className="auth-card">
        <span className="field-label">Signed in</span>
        <strong>{user.email}</strong>
        <span className="source-pill">{user.role}</span>
        <button className="secondary-button compact-button" type="button" onClick={() => void logout()}>
          <LogOut size={15} />
          Sign out
        </button>
      </div>
    );
  }

  return (
    <form className="auth-card" onSubmit={login}>
      <span className="field-label">Start your free trial</span>
      <input value={email} onChange={(event) => setEmail(event.target.value)} placeholder="email" type="email" />
      <input value={password} onChange={(event) => setPassword(event.target.value)} placeholder="password" type="password" />
      {error ? <span className="form-error">{error}</span> : null}
      <button className="secondary-button compact-button" type="submit">
        <LogIn size={15} />
        Get free access
      </button>
      <span className="auth-microcopy">No credit card required. Bids refresh daily.</span>
    </form>
  );
}
