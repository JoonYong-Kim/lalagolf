import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { relative } from "node:path";

const repoRoot = new URL("../..", import.meta.url);
const files = execFileSync("git", ["ls-files", "--cached", "--others", "--exclude-standard"], {
  cwd: repoRoot,
  encoding: "utf8",
})
  .split("\n")
  .filter(Boolean)
  .filter((path) => path.startsWith("v2/") || path.startsWith("docs/"))
  .filter((path) => !shouldSkip(path));

const findings = [];

for (const file of files) {
  const text = readFileSync(new URL(file, repoRoot), "utf8");
  const lines = text.split(/\r?\n/);
  lines.forEach((line, index) => checkLine(file, index + 1, line));
}

if (findings.length > 0) {
  console.error(findings.map((finding) => `- ${finding}`).join("\n"));
  process.exit(1);
}

console.log(`Secret scan checked ${files.length} files`);

function shouldSkip(path) {
  return (
    path.includes("/node_modules/") ||
    path.includes("/.next/") ||
    path.includes("/.venv/") ||
    path.includes("/.pytest_cache/") ||
    path.includes("/.ruff_cache/") ||
    path.endsWith("package-lock.json") ||
    path.endsWith(".pyc") ||
    path.endsWith(".png") ||
    path.endsWith(".jpg") ||
    path.endsWith(".jpeg") ||
    path.endsWith(".gif") ||
    path.endsWith(".pdf")
  );
}

function checkLine(file, lineNumber, line) {
  if (/BEGIN (RSA |OPENSSH |EC |DSA )?PRIVATE KEY/.test(line)) {
    add(file, lineNumber, "private key material");
  }
  if (/\b(sk-[A-Za-z0-9_-]{20,}|xox[baprs]-[A-Za-z0-9-]{20,})\b/.test(line)) {
    add(file, lineNumber, "API token pattern");
  }
  if (/\b(AWS_SECRET_ACCESS_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY)\s*=/.test(line)) {
    add(file, lineNumber, "provider secret env var");
  }

  const secretKey = line.match(/^\s*SECRET_KEY\s*[:=]\s*["']?([^"'\s#]+)["']?/);
  if (secretKey && !["change-me", "change-me-in-local-env"].includes(secretKey[1])) {
    add(file, lineNumber, "non-placeholder SECRET_KEY");
  }

  const postgresPassword = line.match(/^\s*POSTGRES_PASSWORD\s*[:=]\s*["']?([^"'\s#]+)["']?/);
  if (postgresPassword && postgresPassword[1] !== "lalagolf") {
    add(file, lineNumber, "non-placeholder POSTGRES_PASSWORD");
  }
}

function add(file, lineNumber, reason) {
  findings.push(`${relative(repoRoot.pathname, new URL(file, repoRoot).pathname)}:${lineNumber} ${reason}`);
}
