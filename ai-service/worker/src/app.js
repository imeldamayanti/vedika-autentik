// Vedika AI Worker: Kontrak B2 answer reader and the voice agent's token endpoint.
// The agent page (/voice/) is served from static assets before this code runs.
import { fail, galat, json } from "./errors.js";
import { parseReadRequest, readAnswer } from "./reader.js";
import { issueToken, parseVoiceContext } from "./voice.js";

export const ENGINE_VERSION = "pramana-0.5.0";
export const READER_VERSION = "pembaca-0.5.0";
const DEFAULT_TEXT_MODEL = "gemini-3.5-flash-lite";
const DEFAULT_LIVE_MODEL = "gemini-3.8-live";

const encoder = new TextEncoder();
function sameSecret(supplied, expected) {
  const a = encoder.encode(supplied);
  const b = encoder.encode(expected);
  if (a.byteLength !== b.byteLength) return false;
  if (crypto.subtle.timingSafeEqual) return crypto.subtle.timingSafeEqual(a, b);
  return a.every((byte, index) => byte === b[index]);
}

const readJson = (request) =>
  request.json().catch(() => {
    throw fail(422, "validasi", "Permintaan tidak valid.");
  });

const apiKey = (env, what) => {
  if (!env.GEMINI_API_KEY) throw fail(503, "gemini_tidak_dikonfigurasi", `${what} belum dikonfigurasi.`);
  return env.GEMINI_API_KEY;
};

async function route(request, env, fetchImpl) {
  const { pathname } = new URL(request.url);
  if (!pathname.startsWith("/v1/")) return json({ detail: "Not Found" }, 404);
  const supplied = request.headers.get("X-Kunci-Layanan");
  if (env.AI_SERVICE_KEY && !sameSecret(supplied ?? "", env.AI_SERVICE_KEY)) {
    // Say why, never what: missing header or wrong length helps debug a misconfigured caller.
    const why = supplied === null
      ? "missing"
      : `mismatch length ${supplied.length} expected ${env.AI_SERVICE_KEY.length}`;
    throw Object.assign(fail(401, "kunci_salah", "Header X-Kunci-Layanan kosong atau salah."), { why });
  }
  if (pathname === "/v1/kesehatan" && request.method === "GET") {
    return json({
      status: "ok",
      versi_mesin: ENGINE_VERSION,
      versi_pembaca: READER_VERSION,
      pembaca_siap: Boolean(env.GEMINI_API_KEY),
    });
  }
  if (pathname === "/v1/baca" && request.method === "POST") {
    const parsed = parseReadRequest(await readJson(request));
    const answer = await readAnswer(parsed, {
      apiKey: apiKey(env, "Pembaca jawaban"),
      model: env.GEMINI_TEXT_MODEL || DEFAULT_TEXT_MODEL,
      fetchImpl,
    });
    return json({ ...answer, versi_pembaca: READER_VERSION });
  }
  if (pathname === "/v1/suara/token" && request.method === "POST") {
    const context = parseVoiceContext(await readJson(request));
    return json(await issueToken(context, {
      apiKey: apiKey(env, "Agen suara"),
      model: env.GEMINI_LIVE_MODEL || DEFAULT_LIVE_MODEL,
      fetchImpl,
    }));
  }
  if (["/v1/kesehatan", "/v1/baca", "/v1/suara/token"].includes(pathname)) {
    return json({ detail: "Method Not Allowed" }, 405);
  }
  return json({ detail: "Not Found" }, 404);
}

// Logs carry route, status, duration, and error code only; never transcripts or names.
export async function handle(request, env, fetchImpl = fetch) {
  const started = Date.now();
  const requestId = crypto.randomUUID().replaceAll("-", "");
  let response;
  let code = null;
  let key;
  try {
    response = await route(request, env, fetchImpl);
  } catch (error) {
    if (!error.kode) throw error;
    code = error.kode;
    key = error.why;
    response = galat(error);
  }
  response.headers.set("X-Request-ID", requestId);
  console.log(JSON.stringify({
    event: "request_completed",
    request_id: requestId,
    method: request.method,
    path: new URL(request.url).pathname,
    status: response.status,
    code,
    key,
    duration_ms: Date.now() - started,
  }));
  return response;
}
