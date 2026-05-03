"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/app/components/AppShell";
import { getAdminUploadErrors, type AdminUploadError } from "@/lib/api";

export default function AdminUploadErrorsPage() {
  const [items, setItems] = useState<AdminUploadError[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getAdminUploadErrors()
      .then(setItems)
      .catch((uploadError) => {
        setError(uploadError instanceof Error ? uploadError.message : "Upload errors load failed");
      });
  }, []);

  return (
    <AppShell eyebrow="Admin" title="Upload Errors">
      <div className="mt-5 space-y-4 sm:space-y-5">
        {!items && !error && (
          <div className="rounded-md border border-line bg-white p-3 text-sm text-muted">
            Loading upload errors...
          </div>
        )}
        {error && (
          <div className="rounded-md border border-[#e4c0bd] bg-[#fff2f0] p-3 text-sm text-[#a34242]">
            {error}
          </div>
        )}

        <section className="rounded-md border border-line bg-white">
          <div className="border-b border-line px-4 py-3 text-sm text-muted">
            {items ? `${items.length} failed uploads` : "Failed uploads"}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-surface text-muted">
                <tr>
                  <th className="px-4 py-2 font-medium">Created</th>
                  <th className="px-4 py-2 font-medium">File</th>
                  <th className="px-4 py-2 font-medium">Status</th>
                  <th className="px-4 py-2 font-medium">Warnings</th>
                </tr>
              </thead>
              <tbody>
                {(items ?? []).map((item) => (
                  <tr className="border-t border-line" key={item.id}>
                    <td className="px-4 py-3">{formatDate(item.created_at)}</td>
                    <td className="px-4 py-3 font-medium">{item.filename ?? "-"}</td>
                    <td className="px-4 py-3">{item.status}</td>
                    <td className="px-4 py-3">
                      {item.warnings.map((warning) => warning.code).join(", ") || "-"}
                    </td>
                  </tr>
                ))}
                {items && items.length === 0 && (
                  <tr>
                    <td className="px-4 py-6 text-muted" colSpan={4}>
                      No failed uploads.
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
