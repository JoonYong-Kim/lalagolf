import { spawn } from "node:child_process";
import { once } from "node:events";
import { createServer } from "node:net";

const routes = [
  { path: "/", text: "GolfRaiders" },
  { path: "/dashboard", text: "대시보드" },
  { path: "/rounds", text: "라운드" },
  { path: "/analysis", text: "분석" },
  { path: "/practice", text: "연습 계획" },
  { path: "/goals", text: "다음 라운드 목표" },
  { path: "/ask", text: "질문" },
  { path: "/upload", text: "라운드 업로드" },
  { path: "/admin/uploads/errors", text: "업로드 오류" },
  { path: "/rounds/smoke-round", text: "라운드" },
  { path: "/upload/smoke-review/review", text: "업로드 검토" },
  { path: "/s/smoke-token", text: "공유 라운드" },
];

const port = await getOpenPort();
const baseUrl = `http://127.0.0.1:${port}`;
const nextBin = new URL("../node_modules/.bin/next", import.meta.url);
const server = spawn(nextBin.pathname, ["start", "-H", "127.0.0.1", "-p", String(port)], {
  cwd: new URL("..", import.meta.url),
  stdio: ["ignore", "pipe", "pipe"],
});

let output = "";
server.stdout.on("data", (chunk) => {
  output += chunk.toString();
});
server.stderr.on("data", (chunk) => {
  output += chunk.toString();
});

try {
  await waitForServer(baseUrl);

  for (const route of routes) {
    const response = await fetch(`${baseUrl}${route.path}`);
    if (!response.ok) {
      throw new Error(`${route.path} returned HTTP ${response.status}`);
    }

    const html = await response.text();
    if (!html.includes(route.text)) {
      throw new Error(`${route.path} did not include expected text: ${route.text}`);
    }
  }

  console.log(`Smoke checked ${routes.length} routes on ${baseUrl}`);
} finally {
  server.kill("SIGTERM");
  await Promise.race([
    once(server, "exit"),
    new Promise((resolve) => setTimeout(resolve, 1500)),
  ]);
}

async function getOpenPort() {
  const socket = createServer();
  socket.listen(0, "127.0.0.1");
  await once(socket, "listening");
  const address = socket.address();
  socket.close();
  await once(socket, "close");
  return address.port;
}

async function waitForServer(baseUrl) {
  const deadline = Date.now() + 15000;
  let lastError = null;

  while (Date.now() < deadline) {
    if (server.exitCode !== null) {
      throw new Error(`Next server exited early:\n${output}`);
    }

    try {
      const response = await fetch(baseUrl);
      if (response.ok) {
        return;
      }
      lastError = new Error(`HTTP ${response.status}`);
    } catch (error) {
      lastError = error;
    }

    await new Promise((resolve) => setTimeout(resolve, 250));
  }

  throw new Error(`Next server did not become ready: ${lastError?.message ?? "unknown error"}\n${output}`);
}
