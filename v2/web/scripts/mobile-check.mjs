import { readFile } from "node:fs/promises";

const root = new URL("..", import.meta.url);
const corePages = [
  "app/dashboard/page.tsx",
  "app/rounds/page.tsx",
  "app/rounds/[id]/page.tsx",
  "app/analysis/page.tsx",
  "app/ask/page.tsx",
  "app/upload/page.tsx",
  "app/upload/[id]/review/page.tsx",
  "app/admin/uploads/errors/page.tsx",
  "app/s/[token]/page.tsx",
];

const failures = [];

await checkAppShell();
for (const page of corePages) {
  await checkPage(page);
}

if (failures.length > 0) {
  console.error(failures.map((failure) => `- ${failure}`).join("\n"));
  process.exit(1);
}

console.log(`Mobile guardrails checked for ${corePages.length} core pages`);

async function checkAppShell() {
  const path = "app/components/AppShell.tsx";
  const source = await readSource(path);
  requireIncludes(source, path, "md:hidden", "mobile bottom navigation");
  requireIncludes(source, path, "md:block", "desktop sidebar breakpoint");
  requireIncludes(source, path, "pb-20", "bottom nav content padding");
}

async function checkPage(path) {
  const source = await readSource(path);
  const hasResponsiveClass = /\b(sm|md|lg|xl):/.test(source);
  if (!hasResponsiveClass) {
    failures.push(`${path} has no responsive breakpoint classes`);
  }

  if (source.includes("<table") && !source.includes("overflow-x-auto")) {
    failures.push(`${path} renders a table without an overflow-x-auto wrapper`);
  }

  if (source.includes("min-w-[") && !source.includes("overflow-x-auto")) {
    failures.push(`${path} uses min-width content without an overflow-x-auto wrapper`);
  }
}

async function readSource(path) {
  return readFile(new URL(path, root), "utf8");
}

function requireIncludes(source, path, token, reason) {
  if (!source.includes(token)) {
    failures.push(`${path} is missing ${token} for ${reason}`);
  }
}
