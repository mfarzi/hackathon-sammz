import { spawn } from "node:child_process";
import path from "node:path";

// This proxies to the real backend: `../ask` fans a query out over Flower to
// every hospital node, waits for the panel to attack the answers, and prints
// the report. Nothing here re-implements or simulates that — this route only
// starts the process and forwards its already-filtered output byte for byte.
export const runtime = "nodejs";

// The repo root, one level up from the Next.js app.
const REPO_ROOT = path.resolve(process.cwd(), "..");

const MAX_CASE_CHARS = 800;

export async function POST(request: Request) {
  let body: { case?: string; dryRun?: boolean; federation?: string };
  try {
    body = await request.json();
  } catch {
    return new Response("Invalid JSON body.", { status: 400 });
  }

  const caseText = (body.case ?? "").trim();
  if (!caseText) {
    // `ask` with no case argument drops into an interactive REPL that reads
    // stdin, which a spawned process here has none of - it would hang rather
    // than fail, so this has to be caught before the process ever starts.
    return new Response("A case description is required.", { status: 400 });
  }
  if (caseText.length > MAX_CASE_CHARS) {
    return new Response(`Case description too long (max ${MAX_CASE_CHARS} chars).`, {
      status: 400,
    });
  }

  const args = ["--federation", body.federation || "local-sim"];
  if (body.dryRun) args.push("--dry-run");
  if (caseText) args.push(caseText);

  const child = spawn(path.join(REPO_ROOT, "ask"), args, {
    cwd: REPO_ROOT,
    env: { ...process.env, PYTHONUNBUFFERED: "1" },
  });

  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      const onData = (chunk: Buffer) => {
        try {
          controller.enqueue(chunk);
        } catch {
          // Controller already closed (client disconnected); ignore.
        }
      };
      child.stdout.on("data", onData);
      child.stderr.on("data", onData);
      child.on("close", (code) => {
        try {
          controller.enqueue(
            Buffer.from(`\n\n[process exited with code ${code ?? "unknown"}]\n`),
          );
          controller.close();
        } catch {
          // Already closed.
        }
      });
      child.on("error", (err) => {
        try {
          controller.enqueue(Buffer.from(`\n[failed to start: ${err.message}]\n`));
          controller.close();
        } catch {
          // Already closed.
        }
      });
    },
    cancel() {
      // The browser navigated away or aborted the fetch: stop the run rather
      // than leaving an orphaned `flwr run` behind.
      child.kill("SIGINT");
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      "X-Accel-Buffering": "no",
    },
  });
}
