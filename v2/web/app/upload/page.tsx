"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/app/components/AppShell";
import {
  getCurrentUser,
  uploadRoundFile,
  type ApiUser,
} from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function UploadPage() {
  const router = useRouter();
  const { t } = useI18n();
  const [user, setUser] = useState<ApiUser | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string>("");

  useEffect(() => {
    getCurrentUser()
      .then(setUser)
      .catch(() => setUser(null));
    function refreshUser() {
      getCurrentUser()
        .then(setUser)
        .catch(() => setUser(null));
    }
    window.addEventListener("golfraiders-auth-change", refreshUser);
    return () => window.removeEventListener("golfraiders-auth-change", refreshUser);
  }, []);

  async function handleUpload() {
    if (!file) {
      setError(t("selectRoundFile"));
      return;
    }
    setError("");
    setStatus(t("uploadingAndParsing"));
    try {
      const uploaded = await uploadRoundFile(file);
      router.push(`/upload/${uploaded.upload_review_id}/review`);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : t("uploadFailed"));
      setStatus("");
    }
  }

  return (
    <AppShell eyebrow={t("uploadEyebrow")} title={t("uploadTitle")}>
      <div className="mt-5 space-y-5">
        <p className="max-w-3xl text-sm leading-6 text-muted">{t("uploadIntro")}</p>
        <div className="grid gap-4">
          <section className="rounded-md border border-line bg-white p-4">
            <h2 className="text-lg font-semibold">{t("uploadFile")}</h2>
            {!user && <p className="mt-3 rounded-md bg-surface p-3 text-sm text-muted">{t("signInFromHeader")}</p>}
            {user && <p className="mt-3 text-sm text-muted">{t("signedInAs")}: {user.email}</p>}
            <div className="mt-4 rounded-md border border-dashed border-line bg-surface p-5">
              <input
                accept=".txt,text/plain"
                className="w-full text-sm"
                disabled={!user}
                type="file"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
              <p className="mt-3 text-sm text-muted">{t("uploadFileHelp")}</p>
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                className="rounded-md bg-green-700 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-[#9bb5a6]"
                disabled={!user || !file}
                onClick={handleUpload}
              >
                {t("uploadAndReview")}
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
      </div>
    </AppShell>
  );
}
