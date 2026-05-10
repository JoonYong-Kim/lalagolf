"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell } from "@/app/components/AppShell";
import {
  getAdminAnalysisJobs,
  retryAdminAnalysisJob,
  type AdminAnalysisJob,
} from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function AdminAnalysisJobsPage() {
  const [items, setItems] = useState<AdminAnalysisJob[] | null>(null);
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const { t } = useI18n();

  useEffect(() => {
    loadJobs();
  }, []);

  async function loadJobs() {
    setError("");
    try {
      setItems(await getAdminAnalysisJobs());
    } catch (jobError) {
      setError(jobError instanceof Error ? jobError.message : t("loadingAnalysisJobs"));
    }
  }

  async function retryJob(jobId: string) {
    setRetryingId(jobId);
    setError("");
    setStatus("");
    try {
      await retryAdminAnalysisJob(jobId);
      setStatus(t("analysisJobRetryQueued"));
      await loadJobs();
    } catch (retryError) {
      setError(retryError instanceof Error ? retryError.message : t("analysisJobRetryFailed"));
    } finally {
      setRetryingId(null);
    }
  }

  return (
    <AppShell eyebrow={t("admin")} title={t("analysisJobs")}>
      <div className="mt-5 space-y-4 sm:space-y-5">
        <div className="flex flex-wrap gap-2">
          <Link className="rounded-md border border-line px-3 py-2 text-sm font-semibold" href="/admin/uploads/errors">
            {t("uploadErrors")}
          </Link>
          <button className="rounded-md border border-line px-3 py-2 text-sm font-semibold" onClick={loadJobs}>
            {t("refresh")}
          </button>
        </div>

        {!items && !error && (
          <div className="rounded-md border border-line bg-white p-3 text-sm text-muted">
            {t("loadingAnalysisJobs")}
          </div>
        )}
        {error && (
          <div className="rounded-md border border-[#e4c0bd] bg-[#fff2f0] p-3 text-sm text-[#a34242]">
            {error}
          </div>
        )}
        {status && (
          <div className="rounded-md border border-[#b7dec4] bg-[#eef8f1] p-3 text-sm text-green-700">
            {status}
          </div>
        )}

        <section className="rounded-md border border-line bg-white">
          <div className="border-b border-line px-4 py-3 text-sm text-muted">
            {items ? `${items.length} ${t("failedAnalysisJobs")}` : t("failedAnalysisJobs")}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[980px] text-left text-sm">
              <thead className="bg-surface text-muted">
                <tr>
                  <th className="px-4 py-2 font-medium">{t("created")}</th>
                  <th className="px-4 py-2 font-medium">{t("user")}</th>
                  <th className="px-4 py-2 font-medium">{t("round")}</th>
                  <th className="px-4 py-2 font-medium">{t("attempts")}</th>
                  <th className="px-4 py-2 font-medium">{t("error")}</th>
                  <th className="px-4 py-2 font-medium">{t("actions")}</th>
                </tr>
              </thead>
              <tbody>
                {(items ?? []).map((item) => (
                  <tr className="border-t border-line align-top" key={item.id}>
                    <td className="px-4 py-3">{formatDate(item.created_at)}</td>
                    <td className="px-4 py-3">{item.user_email}</td>
                    <td className="px-4 py-3">
                      <Link className="font-semibold text-green-700" href={`/rounds/${item.round_id}`}>
                        {item.course_name}
                      </Link>
                      <div className="mt-1 text-xs text-muted">{item.play_date}</div>
                    </td>
                    <td className="px-4 py-3">{item.attempts}</td>
                    <td className="max-w-[340px] px-4 py-3 text-[#a34242]">
                      <span className="line-clamp-3">{item.error_message ?? "-"}</span>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        className="rounded-md border border-line px-3 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
                        disabled={retryingId === item.id}
                        onClick={() => retryJob(item.id)}
                      >
                        {retryingId === item.id ? t("retrying") : t("retry")}
                      </button>
                    </td>
                  </tr>
                ))}
                {items && items.length === 0 && (
                  <tr>
                    <td className="px-4 py-6 text-muted" colSpan={6}>
                      {t("noFailedAnalysisJobs")}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </AppShell>
  );
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}
