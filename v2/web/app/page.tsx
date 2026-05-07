"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import {
  getCurrentUser,
  getGoogleOAuthStatus,
  googleOAuthStartUrl,
  login,
  registerOrLogin,
} from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function EntryPage() {
  const router = useRouter();
  const { t } = useI18n();
  const [startOpen, setStartOpen] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "register">("register");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [googleConfigured, setGoogleConfigured] = useState(false);
  const emailInputRef = useRef<HTMLInputElement>(null);
  const passwordInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getGoogleOAuthStatus()
      .then((status) => setGoogleConfigured(status.configured))
      .catch(() => setGoogleConfigured(false));
    getCurrentUser()
      .then((user) => {
        if (user) router.replace("/dashboard");
      })
      .catch(() => {});
  }, [router]);

  async function submitAuth() {
    setError("");
    setStatus("");
    if (
      !email.trim()
      || password.length < 8
      || (authMode === "register" && !displayName.trim())
    ) {
      setError(t("fillRequiredFields"));
      return;
    }
    try {
      setStatus(t(authMode === "login" ? "signingIn" : "creatingAccount"));
      await (authMode === "login"
        ? login({ email, password })
        : registerOrLogin({ email, password, display_name: displayName }));
      window.location.href = "/dashboard";
    } catch (authError) {
      setError(authError instanceof Error ? authError.message : t("authenticationFailed"));
      setStatus("");
    }
  }

  function openStart(nextMode: "login" | "register") {
    setAuthMode(nextMode);
    setStartOpen(true);
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

  return (
    <main className="min-h-screen bg-surface px-6 py-8 text-ink">
      <section className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-5xl flex-col justify-between">
        <nav className="flex items-center justify-between border-b border-line pb-4">
          <div className="text-lg font-semibold">GolfRaiders</div>
          <button
            className="rounded-md border border-line px-4 py-2 text-sm font-medium hover:border-green-700"
            onClick={() => openStart("login")}
          >
            {t("login")}
          </button>
        </nav>

        <div className="grid gap-10 py-14 md:grid-cols-[1.1fr_0.9fr] md:items-center">
          <div>
            <p className="mb-3 text-sm font-semibold uppercase tracking-wide text-green-700">
              {t("entryEyebrow")}
            </p>
            <h1 className="mb-5 text-4xl font-semibold leading-tight md:text-6xl">
              GolfRaiders
            </h1>
            <p className="max-w-2xl text-lg leading-8 text-muted">
              {t("entryIntro")}
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <button className="rounded-md bg-green-700 px-5 py-3 text-sm font-semibold text-white" onClick={() => openStart("register")}>
                {t("getStarted")}
              </button>
              <Link className="rounded-md border border-line px-5 py-3 text-sm font-semibold" href="#sample">
                {t("sampleAnalysis")}
              </Link>
            </div>
          </div>

          <div className="rounded-md border border-line bg-white p-5 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <span className="text-sm font-semibold">{t("roundWorkspace")}</span>
              <span className="rounded-full bg-surface px-3 py-1 text-xs text-muted">{t("private")}</span>
            </div>
            <dl className="grid gap-4 text-sm">
              <div className="flex justify-between border-b border-line pb-3">
                <dt className="text-muted">{t("navUpload")}</dt>
                <dd className="font-medium">{t("parseShots")}</dd>
              </div>
              <div className="flex justify-between border-b border-line pb-3">
                <dt className="text-muted">{t("analysis")}</dt>
                <dd className="font-medium">{t("scoreImpact")}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted">{t("sharing")}</dt>
                <dd className="font-medium">{t("linkOnly")}</dd>
              </div>
            </dl>
          </div>
        </div>

        <section className="pb-12" id="sample">
          <div className="mb-4">
            <h2 className="text-2xl font-semibold">{t("samplePreview")}</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">{t("samplePreviewIntro")}</p>
          </div>
          <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="rounded-md border border-line bg-white p-4">
              <div className="grid gap-3 sm:grid-cols-3">
                <SampleMetric label={t("avgScore")} value="89.7" />
                <SampleMetric label={t("bestScore")} value="86" />
                <SampleMetric label={t("avgPutts")} value="31.3" />
              </div>
              <div className="mt-5 h-48 rounded-md bg-surface p-4">
                <svg className="h-full w-full" preserveAspectRatio="none" viewBox="0 0 100 100">
                  <line className="stroke-line" x1="4" x2="96" y1="82" y2="82" />
                  <line className="stroke-line" x1="4" x2="96" y1="50" y2="50" />
                  <line className="stroke-line" x1="4" x2="96" y1="18" y2="18" />
                  <path d="M 8 28 L 50 44 L 92 70" fill="none" stroke="#15803d" strokeLinecap="round" strokeWidth="3" vectorEffect="non-scaling-stroke" />
                  <circle cx="8" cy="28" fill="#15803d" r="2" />
                  <circle cx="50" cy="44" fill="#15803d" r="2" />
                  <circle cx="92" cy="70" fill="#15803d" r="2" />
                </svg>
              </div>
              <div className="mt-3 grid gap-2 text-sm sm:grid-cols-3">
                <SampleRound course={t("sampleRoundA")} score="92" />
                <SampleRound course={t("sampleRoundB")} score="91" />
                <SampleRound course={t("sampleRoundC")} score="86" />
              </div>
            </div>

            <div className="rounded-md border border-line bg-white">
              {[t("sampleInsightOne"), t("sampleInsightTwo")].map((insight) => (
                <article className="border-b border-line p-4 last:border-b-0" key={insight}>
                  <p className="text-xs font-semibold uppercase text-green-700">{t("priorityInsights")}</p>
                  <h3 className="mt-1 text-base font-semibold">{insight}</h3>
                  <p className="mt-2 text-sm leading-6 text-muted">{t("convertToPracticePlan")}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <p className="border-t border-line pt-4 text-sm text-muted">
          {t("entryFooter")}
        </p>
      </section>
      {startOpen && (
        <div className="fixed inset-0 z-30 grid place-items-center bg-black/30 px-4">
          <div className="w-full max-w-md rounded-md border border-line bg-white p-5 shadow-lg">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">{t("startTitle")}</h2>
                <p className="mt-1 text-sm leading-6 text-muted">{t("startIntro")}</p>
              </div>
              <button className="rounded-md border border-line px-2 py-1 text-sm font-semibold" onClick={() => setStartOpen(false)}>
                X
              </button>
            </div>
            <div className="mt-4 flex gap-2">
              <button className={authMode === "register" ? activeButton : idleButton} onClick={() => setAuthMode("register")}>
                {t("register")}
              </button>
              <button className={authMode === "login" ? activeButton : idleButton} onClick={() => setAuthMode("login")}>
                {t("login")}
              </button>
            </div>
            <div className="mt-4 space-y-3">
              <input
                className={inputClass}
                onChange={(event) => setEmail(event.target.value)}
                onKeyDown={handleEmailKeyDown}
                placeholder={t("email")}
                ref={emailInputRef}
                value={email}
              />
              {authMode === "register" && (
                <input className={inputClass} placeholder={t("displayName")} value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
              )}
              <input
                className={inputClass}
                onChange={(event) => setPassword(event.target.value)}
                onKeyDown={handlePasswordKeyDown}
                placeholder={t("password")}
                ref={passwordInputRef}
                type="password"
                value={password}
              />
              <p className="text-xs text-muted">{t("passwordHelp")}</p>
              <button
                className="w-full rounded-md bg-green-700 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-[#9bb5a6]"
                disabled={Boolean(status)}
                onClick={submitAuth}
              >
                {authMode === "register" ? t("createAccount") : t("signIn")}
              </button>
              {googleConfigured ? (
                <a className="block rounded-md border border-line px-4 py-2 text-center text-sm font-semibold" href={googleOAuthStartUrl}>
                  {t("continueWithGoogle")}
                </a>
              ) : (
                <p className="rounded-md border border-line bg-surface px-3 py-2 text-sm text-muted">
                  {t("googleLoginUnavailable")}
                </p>
              )}
              {status && <p className="text-sm text-muted">{status}</p>}
              {error && <p className="text-sm text-[#a34242]">{error}</p>}
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

function SampleMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-surface p-3">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
    </div>
  );
}

function SampleRound({ course, score }: { course: string; score: string }) {
  return (
    <div className="rounded-md border border-line px-3 py-2">
      <p className="font-semibold">{course}</p>
      <p className="text-muted">{score}</p>
    </div>
  );
}

const inputClass = "w-full rounded-md border border-line px-3 py-2 text-sm";
const activeButton = "rounded-md bg-green-700 px-3 py-1.5 text-sm font-semibold text-white";
const idleButton = "rounded-md border border-line px-3 py-1.5 text-sm font-semibold";
