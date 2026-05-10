"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell } from "@/app/components/AppShell";
import { createFollow, getPublicRounds, type PublicRoundCard } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function PublicRoundsPage() {
  const [course, setCourse] = useState("");
  const [handle, setHandle] = useState("");
  const [keyword, setKeyword] = useState("");
  const [year, setYear] = useState("");
  const [results, setResults] = useState<PublicRoundCard[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const { t } = useI18n();

  useEffect(() => {
    void search();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function search() {
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const payload = await getPublicRounds({
        course: course || undefined,
        handle: handle || undefined,
        keyword: keyword || undefined,
        year: year ? Number(year) : undefined,
        limit: 20,
      });
      setResults(payload.items);
      setTotal(payload.total);
    } catch (searchError) {
      setError(searchError instanceof Error ? searchError.message : t("loadingRounds"));
    } finally {
      setLoading(false);
    }
  }

  async function followOwner(ownerId: string) {
    setError("");
    setMessage("");
    try {
      await createFollow(ownerId);
      setMessage(t("saved"));
    } catch (followError) {
      setError(followError instanceof Error ? followError.message : t("follow"));
    }
  }

  return (
    <AppShell eyebrow={t("publicRounds")} title={t("publicRounds")}>
      <div className="mt-5 space-y-5">
        {error && <div className="rounded-md border border-[#e4c0bd] bg-[#fff2f0] p-3 text-sm text-[#a34242]">{error}</div>}
        {message && <div className="rounded-md border border-[#b7dec4] bg-[#eef8f1] p-3 text-sm text-green-700">{message}</div>}

        <section className="rounded-md border border-line bg-white p-4">
          <div className="grid gap-3 md:grid-cols-4">
            <input
              className="rounded-md border border-line px-3 py-2 text-sm"
              placeholder={t("course")}
              value={course}
              onChange={(event) => setCourse(event.target.value)}
            />
            <input
              className="rounded-md border border-line px-3 py-2 text-sm"
              placeholder={t("owner")}
              value={handle}
              onChange={(event) => setHandle(event.target.value)}
            />
            <input
              className="rounded-md border border-line px-3 py-2 text-sm"
              placeholder={t("search")}
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
            />
            <input
              className="rounded-md border border-line px-3 py-2 text-sm"
              placeholder={t("year")}
              value={year}
              onChange={(event) => setYear(event.target.value)}
            />
          </div>
          <div className="mt-3 flex justify-end">
            <button className="rounded-md border border-line px-3 py-2 text-sm font-semibold" onClick={search}>
              {t("search")}
            </button>
          </div>
        </section>

        <section className="rounded-md border border-line bg-white">
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <h2 className="text-base font-semibold">{t("publicRounds")}</h2>
            <span className="text-sm text-muted">{loading ? t("loadingRounds") : `${total}`}</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="bg-surface text-muted">
                <tr>
                  <th className="px-4 py-2 font-medium">{t("date")}</th>
                  <th className="px-4 py-2 font-medium">{t("course")}</th>
                  <th className="px-4 py-2 font-medium">{t("owner")}</th>
                  <th className="px-4 py-2 font-medium">{t("score")}</th>
                  <th className="px-4 py-2 font-medium">{t("toPar")}</th>
                  <th className="px-4 py-2 font-medium">{t("follow")}</th>
                </tr>
              </thead>
              <tbody>
                {results.map((round) => (
                  <tr className="border-t border-line" key={round.id}>
                    <td className="px-4 py-3">{round.play_date}</td>
                    <td className="px-4 py-3">
                      <Link className="font-semibold text-green-700" href={`/rounds/${round.id}`}>
                        {round.course_name}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      {round.owner_display_name}
                      {round.owner_handle ? ` (@${round.owner_handle})` : ""}
                    </td>
                    <td className="px-4 py-3">{round.total_score ?? "-"}</td>
                    <td className="px-4 py-3">{round.score_to_par ?? "-"}</td>
                    <td className="px-4 py-3">
                      <button
                        className="rounded-md border border-line px-3 py-2 text-xs font-semibold"
                        onClick={() => followOwner(round.owner_id)}
                      >
                        {t("follow")}
                      </button>
                    </td>
                  </tr>
                ))}
                {!loading && results.length === 0 && (
                  <tr>
                    <td className="px-4 py-6 text-sm text-muted" colSpan={6}>
                      {t("noRoundsMatch")}
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
