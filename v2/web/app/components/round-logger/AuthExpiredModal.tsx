"use client";

import { useState } from "react";

import { login } from "@/lib/api";

export type AuthExpiredModalProps = {
  onSuccess: () => void;
  onCancel?: () => void;
};

export function AuthExpiredModal({ onSuccess, onCancel }: AuthExpiredModalProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    if (!email.trim() || !password) {
      setError("이메일과 비밀번호를 입력하세요");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await login({ email: email.trim(), password });
      onSuccess();
    } catch (e) {
      setError(e instanceof Error ? e.message : "로그인 실패");
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-40 grid place-items-center bg-black/40 px-4">
      <div className="w-full max-w-sm rounded-md border border-line bg-white p-5 shadow-lg">
        <h2 className="text-base font-semibold">세션이 만료됐습니다</h2>
        <p className="mt-1 text-sm leading-6 text-muted">
          입력한 내용은 그대로 보관 중입니다. 다시 로그인하면 자동으로 동기화됩니다.
        </p>

        <div className="mt-4 space-y-2">
          <input
            autoFocus
            className="h-12 w-full rounded-md border border-line bg-white px-3 text-base"
            inputMode="email"
            onChange={(e) => setEmail(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                if (password) void submit();
                else (document.querySelector('input[type="password"]') as HTMLInputElement | null)?.focus();
              }
            }}
            placeholder="이메일"
            type="email"
            value={email}
          />
          <input
            className="h-12 w-full rounded-md border border-line bg-white px-3 text-base"
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void submit();
              }
            }}
            placeholder="비밀번호"
            type="password"
            value={password}
          />
        </div>

        {error && <p className="mt-2 text-sm text-[#a34242]">{error}</p>}

        <div className="mt-4 flex gap-2">
          {onCancel && (
            <button
              className="h-12 flex-1 rounded-md border border-line text-sm"
              disabled={submitting}
              onClick={onCancel}
            >
              나중에
            </button>
          )}
          <button
            className="h-12 flex-1 rounded-md bg-green-700 text-sm font-semibold text-white disabled:bg-line disabled:text-muted"
            disabled={submitting}
            onClick={submit}
          >
            {submitting ? "로그인 중…" : "다시 로그인"}
          </button>
        </div>
      </div>
    </div>
  );
}
