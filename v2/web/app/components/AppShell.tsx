"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import {
  getCurrentUser,
  getGoogleOAuthStatus,
  googleOAuthStartUrl,
  login,
  logout,
  registerOrLogin,
  type ApiUser,
} from "@/lib/api";
import { useI18n, type MessageKey } from "@/lib/i18n";

const navItems: Array<{ href: string; labelKey: MessageKey; adminOnly?: boolean }> = [
  { href: "/dashboard", labelKey: "navDashboard" },
  { href: "/rounds", labelKey: "navRounds" },
  { href: "/social", labelKey: "navSocial" },
  { href: "/analysis", labelKey: "navAnalysis" },
  { href: "/practice", labelKey: "navPractice" },
  { href: "/goals", labelKey: "navGoals" },
  { href: "/ask", labelKey: "navAsk" },
  { href: "/upload", labelKey: "navUpload" },
  { href: "/admin/analysis/jobs", labelKey: "navAdmin", adminOnly: true },
];

export function AppShell({
  children,
  eyebrow,
  title,
}: {
  children: React.ReactNode;
  eyebrow: string;
  title: string;
}) {
  const [user, setUser] = useState<ApiUser | null>(null);
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [authError, setAuthError] = useState("");
  const [googleConfigured, setGoogleConfigured] = useState(false);
  const emailInputRef = useRef<HTMLInputElement>(null);
  const passwordInputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const { locale, setLocale, t } = useI18n();
  const visibleNavItems = navItems.filter((item) => !item.adminOnly || user?.role === "admin");

  useEffect(() => {
    getGoogleOAuthStatus()
      .then((status) => setGoogleConfigured(status.configured))
      .catch(() => setGoogleConfigured(false));
    getCurrentUser()
      .then(setUser)
      .catch(() => setUser(null));
  }, []);

  async function submitAuth() {
    setAuthError("");
    try {
      const authenticated =
        authMode === "login"
          ? await login({ email, password })
          : await registerOrLogin({ email, password, display_name: displayName });
      setUser(authenticated);
      setAuthOpen(false);
      window.dispatchEvent(new CustomEvent("golfraiders-auth-change"));
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : t("authenticationFailed"));
    }
  }

  function openLogin() {
    setAuthMode("login");
    setAuthOpen(true);
    window.setTimeout(() => emailInputRef.current?.focus(), 0);
  }

  function handleEmailKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (authMode === "login" && event.key === "Enter") {
      event.preventDefault();
      passwordInputRef.current?.focus();
    }
  }

  function handlePasswordKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      event.preventDefault();
      submitAuth();
    }
  }

  async function submitLogout() {
    setAuthError("");
    try {
      await logout();
      setUser(null);
      window.dispatchEvent(new CustomEvent("golfraiders-auth-change"));
      router.replace("/");
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : t("authenticationFailed"));
    }
  }

  return (
    <main className="min-h-screen bg-surface text-ink">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl gap-6 px-4 py-4 pb-20 md:px-6 md:pb-6">
        <aside className="hidden w-52 shrink-0 border-r border-line pr-4 md:block">
          <div className="sticky top-4">
            <Link className="block text-lg font-semibold" href="/dashboard">
              GolfRaiders
            </Link>
            <nav className="mt-8 space-y-1">
              {visibleNavItems.map((item) => (
                <Link
                  className="block rounded-md px-3 py-2 text-sm font-medium text-muted hover:bg-white hover:text-ink"
                  href={item.href}
                  key={item.href}
                >
                  {t(item.labelKey)}
                </Link>
              ))}
            </nav>
          </div>
        </aside>

        <section className="min-w-0 flex-1">
          <header className="border-b border-line pb-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-green-700">{eyebrow}</p>
                <h1 className="mt-2 text-2xl font-semibold md:text-3xl">{title}</h1>
              </div>
              <div className="relative flex flex-wrap items-center justify-end gap-2">
                <div className="flex rounded-md border border-line bg-white p-1">
                  <button
                    className={locale === "ko" ? headerToggleActive : headerToggleIdle}
                    onClick={() => setLocale("ko")}
                    type="button"
                  >
                    KO
                  </button>
                  <button
                    className={locale === "en" ? headerToggleActive : headerToggleIdle}
                    onClick={() => setLocale("en")}
                    type="button"
                  >
                    EN
                  </button>
                </div>
                {user ? (
                  <div className="flex items-center gap-2">
                    <span className="max-w-48 truncate rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold">
                      {user.email}
                    </span>
                    <button className="rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold" onClick={submitLogout}>
                      {t("logout")}
                    </button>
                  </div>
                ) : (
                  <button
                    className="rounded-md bg-green-700 px-3 py-2 text-sm font-semibold text-white"
                    onClick={openLogin}
                  >
                    {t("login")}
                  </button>
                )}
                {authOpen && !user && (
                  <div className="absolute right-0 top-12 z-20 w-[min(90vw,360px)] rounded-md border border-line bg-white p-4 shadow-lg">
                    <div className="flex gap-2">
                      <button className={authMode === "login" ? activeToggle : idleToggle} onClick={() => setAuthMode("login")}>
                        {t("login")}
                      </button>
                      <button className={authMode === "register" ? activeToggle : idleToggle} onClick={() => setAuthMode("register")}>
                        {t("register")}
                      </button>
                    </div>
                    <div className="mt-3 space-y-3">
                      <input
                        className={authInput}
                        onChange={(event) => setEmail(event.target.value)}
                        onKeyDown={handleEmailKeyDown}
                        placeholder={t("email")}
                        ref={emailInputRef}
                        value={email}
                      />
                      {authMode === "register" && (
                        <input className={authInput} placeholder={t("displayName")} value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
                      )}
                      <input
                        className={authInput}
                        onChange={(event) => setPassword(event.target.value)}
                        onKeyDown={handlePasswordKeyDown}
                        placeholder={t("password")}
                        ref={passwordInputRef}
                        type="password"
                        value={password}
                      />
                      <button className="w-full rounded-md bg-green-700 px-3 py-2 text-sm font-semibold text-white" onClick={submitAuth}>
                        {authMode === "login" ? t("signIn") : t("createAccount")}
                      </button>
                      {googleConfigured ? (
                        <a className="block rounded-md border border-line px-3 py-2 text-center text-sm font-semibold" href={googleOAuthStartUrl}>
                          {t("continueWithGoogle")}
                        </a>
                      ) : (
                        <p className="rounded-md border border-line bg-surface px-3 py-2 text-sm text-muted">
                          {t("googleLoginUnavailable")}
                        </p>
                      )}
                      {authError && <p className="text-sm text-[#a34242]">{authError}</p>}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </header>
          {children}
        </section>
      </div>

      <nav className="fixed inset-x-0 bottom-0 flex overflow-x-auto border-t border-line bg-white md:hidden">
        {visibleNavItems.map((item) => (
          <Link className="min-w-20 px-2 py-3 text-center text-sm font-semibold" href={item.href} key={item.href}>
            {t(item.labelKey)}
          </Link>
        ))}
      </nav>
    </main>
  );
}

const activeToggle = "rounded-md bg-green-700 px-2 py-1.5 text-xs font-semibold text-white";
const idleToggle = "rounded-md border border-line px-2 py-1.5 text-xs font-semibold text-muted";
const headerToggleActive = "rounded px-2 py-1 text-xs font-semibold text-white bg-green-700";
const headerToggleIdle = "rounded px-2 py-1 text-xs font-semibold text-muted";
const authInput = "w-full rounded-md border border-line px-3 py-2 text-sm";
