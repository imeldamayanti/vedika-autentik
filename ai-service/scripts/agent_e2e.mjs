// Automated Kontrak B1 call: real Chrome agent page, real BlackHole routing, real Gemini Live,
// and a phone robot in place of WhatsApp + the recipient.
//
//   node scripts/agent_e2e.mjs S1
//
// Needs ./dev.sh running and no other agent page running "Mulai agen".
// The robot hears the AI on BlackHole 16ch and speaks the recipient's lines from
// data-uji-konfirmasi/transkrip_uji/<S>.txt into BlackHole 2ch (macOS voice "Damayanti").
import { execFileSync, spawn, spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const REPO = new URL("../../", import.meta.url).pathname;
const SCENARIO = process.argv[2] || "S1";
const API = "http://localhost:8000";
const AGENT_PAGE = "http://localhost:8001/voice/";
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const DEBUG_PORT = 9333;
const SPEAKING_LEVEL = 0.02;
const TURN_END_MS = 1500;

const t0 = Date.now();
const log = (...a) => console.log(`[${((Date.now() - t0) / 1000).toFixed(1).padStart(6)}s]`, ...a);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const env = Object.fromEntries(
  readFileSync(join(REPO, "backend/.env"), "utf8").split("\n").filter((l) => l.includes("="))
    .map((l) => [l.slice(0, l.indexOf("=")), l.slice(l.indexOf("=") + 1).trim()]),
);
const scenario = JSON.parse(readFileSync(join(REPO, "data-uji-konfirmasi/skenario_uji.json"), "utf8"))
  .find((s) => s.id_skenario === SCENARIO);
if (!scenario) throw new Error(`unknown scenario ${SCENARIO}`);
const callId = `CALL-${scenario.id_peserta}-${scenario.bulan_layanan}`;
const lines = readFileSync(join(REPO, `data-uji-konfirmasi/transkrip_uji/${SCENARIO}.txt`), "utf8")
  .split("\n").filter((l) => l.startsWith("Penerima: ")).map((l) => l.slice("Penerima: ".length));

const getCall = async () => (await fetch(`${API}/api/v1/panggilan/${callId}`)).json();
const before = await getCall();
if (before.status !== "antre") {
  throw new Error(`${callId} is ${before.status}; press "Mulai ulang demo" on the website first`);
}

// Recipient voice clips.
const work = mkdtempSync(join(tmpdir(), "agent-e2e-"));
const clips = lines.map((text, i) => {
  const file = join(work, `p${i}.aiff`);
  execFileSync("say", ["-v", "Damayanti", "-r", "170", "-o", file, text]);
  return file;
});
const deviceIndex = (name) => {
  const { stdout, stderr } = spawnSync("ffmpeg", ["-hide_banner", "-f", "lavfi", "-i", "anullsrc", "-t", "0.01", "-f", "audiotoolbox", "-list_devices", "true", "-"], { encoding: "utf8" });
  const match = `${stdout}${stderr}`.split("\n").find((l) => new RegExp(`\\]\\s+${name},`).test(l));
  if (!match) throw new Error(`audio device not found: ${name}`);
  return match.match(/\[(\d+)\]\s+/)[1];
};
const blackhole2 = deviceIndex("BlackHole 2ch");
const speak = (file) => new Promise((resolve) => {
  spawn("ffmpeg", ["-hide_banner", "-loglevel", "error", "-i", file, "-f", "audiotoolbox", "-audio_device_index", blackhole2, "-"])
    .on("close", resolve);
});

// Chrome with its own throwaway profile; mic permission auto-granted, devices are real.
const chrome = spawn(CHROME, [
  `--remote-debugging-port=${DEBUG_PORT}`, `--user-data-dir=${join(work, "chrome")}`,
  "--no-first-run", "--no-default-browser-check", "--use-fake-ui-for-media-stream", "--new-window", AGENT_PAGE,
], { stdio: "ignore" });
const cleanup = [() => chrome.kill()];
process.on("exit", () => cleanup.forEach((f) => f()));

let target;
for (let i = 0; i < 40 && !target; i += 1) {
  await sleep(250);
  target = await fetch(`http://127.0.0.1:${DEBUG_PORT}/json`).then((r) => r.json())
    .then((ts) => ts.find((t) => t.type === "page" && t.url.startsWith(AGENT_PAGE))).catch(() => null);
}
if (!target) throw new Error("Chrome agent page did not open");
const cdpSocket = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r) => cdpSocket.addEventListener("open", r, { once: true }));
let nextId = 0;
const pending = new Map();
cdpSocket.addEventListener("message", (e) => {
  const msg = JSON.parse(e.data);
  if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
});
const cdp = (method, params = {}) => new Promise((resolve) => {
  nextId += 1; pending.set(nextId, resolve);
  cdpSocket.send(JSON.stringify({ id: nextId, method, params }));
});
const page = async (expression) => {
  const r = await cdp("Runtime.evaluate", { expression, awaitPromise: true, userGesture: true, returnByValue: true });
  if (r.result?.exceptionDetails) throw new Error(r.result.exceptionDetails.text);
  return r.result?.result?.value;
};
const click = (text) => page(`(() => {
  const b = [...document.querySelectorAll("button")].find((x) => x.textContent.trim() === ${JSON.stringify(text)} && !x.disabled);
  if (!b) return false; b.click(); return true; })()`);
const buttons = () => page(`[...document.querySelectorAll("#aksi button")].map((b) => b.textContent.trim())`);

for (let i = 0; i < 40 && !(await page(`document.readyState === "complete" && !!document.getElementById("mulai")`)); i += 1) await sleep(250);
await page(`document.getElementById("apiUrl").value = ${JSON.stringify(API)}; document.getElementById("kunciAgen").value = ${JSON.stringify(env.AGEN_KEY)}; true`);
await click("Muat perangkat audio");
for (let i = 0; i < 40; i += 1) {
  if (await page(`[...document.getElementById("inputDevice").options].some((o) => o.text.includes("BlackHole 2ch"))`)) break;
  await sleep(250);
}
const chosen = await page(`(() => {
  const pick = (id, label) => { const s = document.getElementById(id); const o = [...s.options].find((x) => x.text.includes(label)); if (o) s.value = o.value; return o?.text; };
  return [pick("inputDevice", "BlackHole 2ch"), pick("outputDevice", "BlackHole 16ch")]; })()`);
log("agent page devices:", chosen.join(" / "));
if (chosen.includes(undefined) || chosen.includes(null)) throw new Error("BlackHole devices not available in Chrome");
await click("Mulai agen");

await fetch(`${API}/api/v1/panggilan/${callId}/mulai`, { method: "POST" });
log(`${SCENARIO} (${callId}) marked "Telepon sekarang"; expected label: ${scenario.expected_label}`);

// Phone robot: level meter on BlackHole 16ch (what the recipient would hear).
let level = 0, aiSpoke = false, lastLoud = 0, aiAudioFrames = 0;
// Keep all 16 channels: a mono downmix divides the voice by eight and hides it.
// 100 ms of 16 ch s16le at 8 kHz = 800 frames * 32 bytes.
const FRAME_BYTES = 16 * 2, BLOCK_BYTES = 800 * FRAME_BYTES;
const listener = spawn("ffmpeg", ["-hide_banner", "-loglevel", "error", "-f", "avfoundation", "-i", ":BlackHole 16ch", "-ar", "8000", "-f", "s16le", "-acodec", "pcm_s16le", "-"]);
cleanup.push(() => listener.kill());
let pendingAudio = Buffer.alloc(0);
listener.stdout.on("data", (chunk) => {
  pendingAudio = Buffer.concat([pendingAudio, chunk]);
  while (pendingAudio.length >= BLOCK_BYTES) {
    let peak = 0;
    for (let i = 0; i < BLOCK_BYTES; i += 2) peak = Math.max(peak, Math.abs(pendingAudio.readInt16LE(i)) / 32768);
    pendingAudio = pendingAudio.subarray(BLOCK_BYTES);
    level = peak;
    if (peak > SPEAKING_LEVEL) { aiSpoke = true; lastLoud = Date.now(); aiAudioFrames += 1; }
  }
});
const waitForAiTurnEnd = async (timeoutMs) => {
  const start = Date.now();
  aiSpoke = false;
  while (Date.now() - start < timeoutMs) {
    if (aiSpoke && Date.now() - lastLoud > TURN_END_MS) return true;
    await sleep(100);
  }
  return false;
};

let inCall = false, done = false, pageTranscript = "";
const robot = async () => {
  for (const [i, clip] of clips.entries()) {
    if (!(await waitForAiTurnEnd(40000))) { log("robot: AI went quiet / never spoke; stopping"); break; }
    log(`robot: AI turn ended -> recipient says: "${lines[i]}"`);
    await speak(clip);
  }
  await waitForAiTurnEnd(40000);
  pageTranscript = await page(`document.getElementById("transkrip").textContent`);
  log("robot: conversation finished -> Akhiri panggilan");
  await click("Akhiri panggilan");
};

const deadline = Date.now() + 6 * 60 * 1000;
while (!done && Date.now() < deadline) {
  const galat = await page(`document.getElementById("galat").textContent`);
  if (galat) log("agent page:", galat);
  const actions = await buttons();
  if (actions.includes("Pesan WA terkirim")) { log("operator: WA sent"); await click("Pesan WA terkirim"); }
  else if (actions.includes("Saya menelepon")) { log("operator: dialing"); await click("Saya menelepon"); }
  else if (actions.includes("Diangkat")) {
    const answer = clips.length ? "Diangkat" : "Tidak diangkat";
    log(`operator: ${answer}`); await click(answer);
  } else if (actions.includes("Chat cadangan terkirim")) { log("operator: fallback chat sent"); await click("Chat cadangan terkirim"); }
  else if (actions.includes("Akhiri panggilan") && !inCall) { inCall = true; log("call live; robot listening"); robot().catch((e) => log("robot error:", e.message)); }
  const call = await getCall();
  if (call.status === "selesai" || call.status === "tidak_terhubung") done = !!call.label;
  if (!done) await sleep(500);
}

const call = await getCall();
const j = call.jawaban || {};
log("RESULT", JSON.stringify({
  status: call.status, label: call.label, expected: scenario.expected_label,
  log: (call.log || []).map((x) => x.status),
  jawaban: { status_panggilan: j.status_panggilan, penerima: j.penerima, hadir: j.hadir, jumlah_maks: j.jumlah_maks, keyakinan: j.keyakinan, tanda_bahaya: j.tanda_bahaya },
  ai_audio_seconds_on_blackhole16: (aiAudioFrames / 10).toFixed(1),
}));
if (pageTranscript) console.log(`\nTranscript seen on the agent page:\n${pageTranscript}`);
await click("Hentikan agen");
const pass = call.label && call.label.replace("_", " ").toLowerCase() === scenario.expected_label.toLowerCase();
log(pass ? "PASS" : "FAIL");
process.exit(pass ? 0 : 1);
