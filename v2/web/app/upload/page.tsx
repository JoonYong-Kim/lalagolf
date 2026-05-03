"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { getCurrentUser, login, registerOrLogin, uploadRoundFile, type ApiUser } from "@/lib/api";

export default function UploadPage() {
  const router = useRouter();
  const [user, setUser] = useState<ApiUser | null>(null);
  const [email, setEmail] = useState("owner@example.com");
  const [password, setPassword] = useState("password");
  const [displayName, setDisplayName] = useState("Import Owner");
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string>("");

  useEffect(() => {
    getCurrentUser()
      .then(setUser)
      .catch(() => setUser(null));
  }, []);

  async function handleAuth() {
    setError("");
    setStatus("Authenticating...");
    try {
      const authenticated =
        authMode === "login"
          ? await login({ email, password })
          : await registerOrLogin({ email, password, display_name: displayName });
      setUser(authenticated);
      setStatus(`Signed in as ${authenticated.email}`);
    } catch (authError) {
      setError(authError instanceof Error ? authError.message : "Authentication failed");
      setStatus("");
    }
  }

  async function handleUpload() {
    if (!file) {
      setError("Select a round text file first.");
      return;
    }
    setError("");
    setStatus("Uploading and parsing...");
    try {
      const uploaded = await uploadRoundFile(file);
      router.push(`/upload/${uploaded.upload_review_id}/review`);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Upload failed");
      setStatus("");
    }
  }

  return (
    <main className="min-h-screen bg-surface p-5 text-ink">
      <section className="mx-auto max-w-5xl">
        <div className="mb-5 border-b border-line pb-4">
          <p className="text-sm font-medium text-green-700">Upload Review Flow</p>
          <h1 className="mt-2 text-3xl font-semibold">Round Upload</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
            Upload a v1-style round text file, review parsed holes and warnings, then commit it as a
            private round.
          </p>
        </div>

        <div className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
          <section className="rounded-md border border-line bg-white p-4">
            <h2 className="text-lg font-semibold">1. Session</h2>
            {user ? (
              <div className="mt-4 rounded-md bg-[#edf7f1] p-3 text-sm">
                Signed in as <strong>{user.email}</strong>
              </div>
            ) : (
              <div className="mt-4 space-y-3">
                <div className="flex gap-2">
                  <button
                    className={authMode === "login" ? activeButton : idleButton}
                    onClick={() => setAuthMode("login")}
                  >
                    Login
                  </button>
                  <button
                    className={authMode === "register" ? activeButton : idleButton}
                    onClick={() => setAuthMode("register")}
                  >
                    Register
                  </button>
                </div>
                <label className="block text-sm font-medium">
                  Email
                  <input className={inputClass} value={email} onChange={(event) => setEmail(event.target.value)} />
                </label>
                {authMode === "register" && (
                  <label className="block text-sm font-medium">
                    Display name
                    <input
                      className={inputClass}
                      value={displayName}
                      onChange={(event) => setDisplayName(event.target.value)}
                    />
                  </label>
                )}
                <label className="block text-sm font-medium">
                  Password
                  <input
                    className={inputClass}
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                  />
                </label>
                <button className="rounded-md bg-green-700 px-4 py-2 text-sm font-semibold text-white" onClick={handleAuth}>
                  Continue
                </button>
              </div>
            )}
          </section>

          <section className="rounded-md border border-line bg-white p-4">
            <h2 className="text-lg font-semibold">2. Upload file</h2>
            <div className="mt-4 rounded-md border border-dashed border-line bg-surface p-5">
              <input
                accept=".txt,text/plain"
                className="w-full text-sm"
                disabled={!user}
                type="file"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
              <p className="mt-3 text-sm text-muted">
                Text files up to the configured upload limit are stored outside public static paths.
              </p>
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                className="rounded-md bg-green-700 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-[#9bb5a6]"
                disabled={!user || !file}
                onClick={handleUpload}
              >
                Upload and review
              </button>
              {status && <span className="text-sm text-muted">{status}</span>}
            </div>

            {error && (
              <div className="mt-4 rounded-md border border-[#e4c0bd] bg-[#fff2f0] p-3 text-sm text-[#a34242]">
                {error}
              </div>
            )}
          </section>
        </div>
      </section>
    </main>
  );
}

const inputClass = "mt-1 w-full rounded-md border border-line px-3 py-2 text-sm";
const activeButton = "rounded-md bg-green-700 px-3 py-1.5 text-sm font-semibold text-white";
const idleButton = "rounded-md border border-line px-3 py-1.5 text-sm font-semibold";
