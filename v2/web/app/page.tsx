"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { getCurrentUser } from "@/lib/api";

export default function EntryPage() {
  const router = useRouter();

  useEffect(() => {
    getCurrentUser()
      .then((user) => {
        if (user) router.replace("/dashboard");
      })
      .catch(() => {});
  }, [router]);

  return (
    <main className="min-h-screen bg-surface px-6 py-8 text-ink">
      <section className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-5xl flex-col justify-between">
        <nav className="flex items-center justify-between border-b border-line pb-4">
          <div className="text-lg font-semibold">LalaGolf</div>
          <Link
            className="rounded-md border border-line px-4 py-2 text-sm font-medium hover:border-green-700"
            href="/upload"
          >
            Login
          </Link>
        </nav>

        <div className="grid gap-10 py-14 md:grid-cols-[1.1fr_0.9fr] md:items-center">
          <div>
            <p className="mb-3 text-sm font-semibold uppercase tracking-wide text-green-700">
              Private-first analysis
            </p>
            <h1 className="mb-5 text-4xl font-semibold leading-tight md:text-6xl">
              LalaGolf
            </h1>
            <p className="max-w-2xl text-lg leading-8 text-muted">
              Upload round records, review parsed shots, and see score impact in a private
              workspace. Sharing is link-only and explicit.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link className="rounded-md bg-green-700 px-5 py-3 text-sm font-semibold text-white" href="/upload">
                Login / Upload
              </Link>
              <Link className="rounded-md border border-line px-5 py-3 text-sm font-semibold" href="/ui-review">
                UI preview
              </Link>
            </div>
          </div>

          <div className="rounded-lg border border-line bg-white p-5 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <span className="text-sm font-semibold">MVP Status</span>
              <span className="rounded-full bg-surface px-3 py-1 text-xs text-muted">P0</span>
            </div>
            <dl className="grid gap-4 text-sm">
              <div className="flex justify-between border-b border-line pb-3">
                <dt className="text-muted">Default visibility</dt>
                <dd className="font-medium">Private</dd>
              </div>
              <div className="flex justify-between border-b border-line pb-3">
                <dt className="text-muted">Core flow</dt>
                <dd className="font-medium">Upload to private analysis</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted">Sharing</dt>
                <dd className="font-medium">Link-only</dd>
              </div>
            </dl>
          </div>
        </div>

        <p className="border-t border-line pt-4 text-sm text-muted">
          MVP does not include public feeds or public profiles. Shared pages use public-safe fields.
        </p>
      </section>
    </main>
  );
}
