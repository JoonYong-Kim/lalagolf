"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/app/components/AppShell";
import { EmptyState } from "@/app/components/EmptyState";
import { getSocialFeed, type SocialFeedItem } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type FeedScope = "all" | "following" | "public";

export default function SocialPage() {
  const [scope, setScope] = useState<FeedScope>("all");
  const [items, setItems] = useState<SocialFeedItem[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { locale, t } = useI18n();

  useEffect(() => {
    void loadFeed(scope, null, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scope, locale]);

  async function loadFeed(nextScope: FeedScope, cursor: string | null, replace = false) {
    setLoading(true);
    setError("");
    try {
      const payload = await getSocialFeed({
        scope: nextScope,
        cursor,
        limit: 12,
        locale,
      });
      setItems((current) => (replace ? payload.items : [...current, ...payload.items]));
      setNextCursor(payload.next_cursor);
      setHasMore(payload.has_more);
    } catch (feedError) {
      setError(feedError instanceof Error ? feedError.message : t("loadingSocialFeed"));
      if (replace) {
        setItems([]);
        setNextCursor(null);
        setHasMore(false);
      }
    } finally {
      setLoading(false);
    }
  }

  const scopeOptions = useMemo(
    () =>
      [
        { value: "all" as const, label: t("socialAll") },
        { value: "following" as const, label: t("socialFollowing") },
        { value: "public" as const, label: t("socialPublic") },
      ],
    [t],
  );

  return (
    <AppShell eyebrow={t("socialFeed")} title={t("socialFeed")}>
      <div className="mt-5 space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex rounded-md border border-line bg-white p-1">
            {scopeOptions.map((option) => (
              <button
                className={scope === option.value ? activeScopeButton : idleScopeButton}
                key={option.value}
                onClick={() => setScope(option.value)}
                type="button"
              >
                {option.label}
              </button>
            ))}
          </div>
          <span className="text-sm text-muted">{loading ? t("loadingSocialFeed") : `${items.length}`}</span>
        </div>

        {error && <div className="rounded-md border border-[#e4c0bd] bg-[#fff2f0] p-3 text-sm text-[#a34242]">{error}</div>}

        <section className="space-y-3">
          {items.map((item) => (
            <FeedCard item={item} key={`${item.item_type}:${item.item_id}`} />
          ))}
          {!loading && items.length === 0 && (
            <EmptyState description={t("noSocialItemsHint")} title={t("noSocialItems")} />
          )}
        </section>

        {hasMore && (
          <div className="flex justify-center">
            <button
              className="rounded-md border border-line bg-white px-4 py-2 text-sm font-semibold"
              disabled={loading}
              onClick={() => loadFeed(scope, nextCursor)}
              type="button"
            >
              {loading ? t("loadingSocialFeed") : t("loadMore")}
            </button>
          </div>
        )}
      </div>
    </AppShell>
  );
}

function FeedCard({ item }: { item: SocialFeedItem }) {
  if (item.item_type === "round") {
    return <RoundFeedCard item={item} />;
  }
  if (item.item_type === "practice_diary") {
    return <DiaryFeedCard item={item} />;
  }
  return <GoalFeedCard item={item} />;
}

function RoundFeedCard({ item }: { item: SocialFeedItem }) {
  const { t } = useI18n();
  const content = (
    <>
      <FeedHeader item={item} label={t("round")} />
      <div className="mt-3 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">{item.course_name ?? "-"}</h2>
          <p className="mt-1 text-sm text-muted">{item.play_date ?? item.play_month ?? "-"}</p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-sm">
          <Metric label={t("score")} value={item.total_score ?? "-"} />
          <Metric label={t("toPar")} value={formatToPar(item.score_to_par)} />
          <Metric label={t("putts")} value={item.metrics.putts_total ?? "-"} />
        </div>
      </div>
      {item.top_insight?.problem && (
        <div className="mt-4 rounded-md border border-line bg-surface p-3">
          <p className="text-xs font-semibold uppercase text-green-700">{t("topIssue")}</p>
          <p className="mt-1 text-sm font-medium">{item.top_insight.problem}</p>
        </div>
      )}
      <div className="mt-4 flex flex-wrap gap-3 text-sm text-muted">
        <span>{t("like")} {item.like_count}</span>
        <span>{t("comments")} {item.comment_count}</span>
      </div>
    </>
  );

  if (item.round_id) {
    return (
      <Link className="block rounded-md border border-line bg-white p-4 hover:border-green-700" href={`/rounds/${item.round_id}`}>
        {content}
      </Link>
    );
  }
  return <article className="rounded-md border border-line bg-white p-4">{content}</article>;
}

function DiaryFeedCard({ item }: { item: SocialFeedItem }) {
  const { t } = useI18n();
  return (
    <article className="rounded-md border border-line bg-white p-4">
      <FeedHeader item={item} label={t("diary")} />
      <h2 className="mt-3 text-lg font-semibold">{item.title}</h2>
      <p className="mt-2 text-sm leading-6 text-ink">{item.body_preview}</p>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted">
        <span>{item.entry_date}</span>
        {item.category && <span>{item.category}</span>}
        {item.linked_round && <span>{item.linked_round.course_name}</span>}
      </div>
    </article>
  );
}

function GoalFeedCard({ item }: { item: SocialFeedItem }) {
  const { t } = useI18n();
  return (
    <article className="rounded-md border border-line bg-white p-4">
      <FeedHeader item={item} label={t("goal")} />
      <h2 className="mt-3 text-lg font-semibold">{item.title}</h2>
      {item.description && <p className="mt-2 text-sm leading-6 text-muted">{item.description}</p>}
      <div className="mt-3 flex flex-wrap gap-2 text-sm">
        {item.target && (
          <span className="rounded-md border border-line bg-surface px-2 py-1">
            {item.target.metric_key} {item.target.operator} {item.target.value ?? "-"}
          </span>
        )}
        {item.status && <span className="rounded-md border border-line bg-surface px-2 py-1">{item.status}</span>}
        {item.due_date && <span className="rounded-md border border-line bg-surface px-2 py-1">{item.due_date}</span>}
      </div>
    </article>
  );
}

function FeedHeader({ item, label }: { item: SocialFeedItem; label: string }) {
  const { t } = useI18n();
  const owner = item.owner.handle ? `${item.owner.display_name} (@${item.owner.handle})` : item.owner.display_name;
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-md bg-green-700 px-2 py-1 text-xs font-semibold text-white">{label}</span>
        <span className="font-semibold">{owner}</span>
        <span className="text-muted">{item.visibility}</span>
      </div>
      <span className="text-xs text-muted">
        {t("published")} {new Date(item.social_published_at).toLocaleDateString()}
      </span>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="min-w-16 rounded-md border border-line bg-surface px-3 py-2">
      <div className="text-xs text-muted">{label}</div>
      <div className="mt-1 font-semibold">{value}</div>
    </div>
  );
}

function formatToPar(value: number | null): string {
  if (value === null) return "-";
  if (value > 0) return `+${value}`;
  return String(value);
}

const activeScopeButton = "rounded px-3 py-1.5 text-sm font-semibold text-white bg-green-700";
const idleScopeButton = "rounded px-3 py-1.5 text-sm font-semibold text-muted";
