// Automated station call: real Chrome station page, real BlackHole routing, real Gemini Live,
// the fake phone (SALURAN_ADB=palsu), and a robot in place of the recipient.
//
//   node scripts/agent_e2e.mjs S1            # answered call, expects the scenario's label
//   node scripts/agent_e2e.mjs S5            # never answered: two attempts, fallback chat, tidak_terhubung
//   node scripts/agent_e2e.mjs pengumuman    # carrier announcement: never tersambung, attempt 2 scheduled
//   node scripts/agent_e2e.mjs pengumuman S4 # same, on another scenario's call (default S3)
//
// Needs the stack running with the fake phone and cable audio, and no other station page open:
//
//   SALURAN_ADB=palsu SALURAN_AUDIO=kabel SALURAN_INPUT="BlackHole 2ch" SALURAN_OUTPUT="BlackHole 16ch" \
//     SALURAN_AGEN_KEY="$(grep '^AGEN_KEY=' backend/.env | cut -d= -f2-)" ./dev.sh
//
// The robot hears the AI on BlackHole 16ch and speaks the recipient's lines from
// data-uji-konfirmasi/transkrip_uji/<S>.txt into BlackHole 2ch (macOS voice "Damayanti").
// Nobody clicks anything: the station dials, detects the answer, and hangs up by itself.
import { execFileSync, spawn, spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const REPO = new URL("../../", import.meta.url).pathname;
const ANNOUNCEMENT = process.argv[2] === "pengumuman";
const SCENARIO = ANNOUNCEMENT ? process.argv[3] || "S3" : process.argv[2] || "S1";
const API = "http://localhost:8000";
const AI = "http://localhost:8001";
const STATION_PAGE = `${AI}/voice/?mulai=1`;
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const DEBUG_PORT = 9333;
const SPEAKING_LEVEL = 0.02;
const TURN_END_MS = 1500;
const ANNOUNCEMENT_TEXT = "Nomor yang Anda tuju tidak dapat dihubungi. Silakan coba beberapa saat lagi.";

const t0 = Date.now();
const log = (...a) => console.log(`[${((Date.now() - t0) / 1000).toFixed(1).padStart(6)}s]`, ...a);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const json = async (url, init) => (await fetch(url, init)).json();
const put = (body) => json(`${API}/api/v1/pengaturan`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

const scenario = JSON.parse(readFileSync(join(REPO, "data-uji-konfirmasi/skenario_uji.json"), "utf8"))
  .find((s) => s.id_skenario === SCENARIO);
if (!scenario) throw new Error(`unknown scenario ${SCENARIO}`);
const callId = `CALL-${scenario.id_peserta}-${scenario.bulan_layanan}`;
const lines = ANNOUNCEMENT || SCENARIO === "S5" ? []
  : readFileSync(join(REPO, `data-uji-konfirmasi/transkrip_uji/${SCENARIO}.txt`), "utf8")
    .split("\n").filter((l) => l.startsWith("Penerima: ")).map((l) => l.slice("Penerima: ".length));

const config = await fetch(`${AI}/v1/saluran/konfigurasi`).then((r) => (r.ok ? r.json() : null)).catch(() => null);
if (!config || config.audio !== "kabel" || !config.kunci_agen) {
  throw new Error("ai-service must run with SALURAN_ADB=palsu SALURAN_AUDIO=kabel and SALURAN_AGEN_KEY (see the top of this file)");
}
const health = await json(`${AI}/v1/saluran/kesehatan`);
if (health.perangkat !== "HP palsu") throw new Error("refusing to run against a real phone: start ai-service with SALURAN_ADB=palsu");

const getCall = () => json(`${API}/api/v1/panggilan/${callId}`);
const before = await getCall();
if (before.status !== "antre" || before.percobaan !== 0) {
  throw new Error(`${callId} is ${before.status} (percobaan ${before.percobaan}); press "Mulai ulang demo" on the website first`);
}

// Recipient voice clips.
const work = mkdtempSync(join(tmpdir(), "agent-e2e-"));
const say = (name, text) => {
  const file = join(work, `${name}.aiff`);
  execFileSync("say", ["-v", "Damayanti", "-r", "170", "-o", file, text]);
  return file;
};
const halo = say("halo", "Halo?");
const announcement = say("pengumuman", ANNOUNCEMENT_TEXT);
const clips = lines.map((text, i) => say(`p${i}`, text));
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
// Indonesian ringback (425 Hz, 1 s on / 3 s off) while the phone "rings": it must not count as an answer.
const ringback = (seconds) => new Promise((resolve) => {
  spawn("ffmpeg", ["-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
    `aevalsrc=0.3*sin(2*PI*425*t)*lt(mod(t\\,4)\\,1):d=${seconds}:s=48000`, "-af", "aformat=sample_fmts=s16",
    "-f", "audiotoolbox", "-audio_device_index", blackhole2, "-"])
    .on("close", resolve);
});

// Only this call may run: automatic mode off, the call moved to the front, mode restored at the end.
const settings = await json(`${API}/api/v1/pengaturan`);
await put({ mode_otomatis: false });
const cleanup = [];
process.on("exit", () => cleanup.forEach((f) => f()));

// Chrome like stasiun.sh starts it, with a throwaway profile; devices are real.
const chrome = spawn(CHROME, [
  `--remote-debugging-port=${DEBUG_PORT}`, `--user-data-dir=${join(work, "chrome")}`,
  "--no-first-run", "--no-default-browser-check", "--use-fake-ui-for-media-stream",
  "--autoplay-policy=no-user-gesture-required", "--new-window", STATION_PAGE,
], { stdio: "ignore" });
cleanup.push(() => chrome.kill());

let target;
for (let i = 0; i < 40 && !target; i += 1) {
  await sleep(250);
  target = await fetch(`http://127.0.0.1:${DEBUG_PORT}/json`).then((r) => r.json())
    .then((ts) => ts.find((t) => t.type === "page" && t.url.startsWith(`${AI}/voice/`))).catch(() => null);
}
if (!target) throw new Error("Chrome station page did not open");
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
  const r = await cdp("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
  if (r.result?.exceptionDetails) throw new Error(r.result.exceptionDetails.text);
  return r.result?.result?.value;
};
const text = (id) => page(`document.getElementById(${JSON.stringify(id)})?.textContent || ""`);

let ready = false;
for (let i = 0; i < 80 && !ready; i += 1) {
  await sleep(250);
  ready = (await text("status")).startsWith("siap");
}
log("station page:", await text("status"), "|", await text("audio"));
if (!ready) throw new Error(`station page is not ready: ${await text("status")} ${await text("galat")} ${await text("pesan")}`);
if (!(await text("audio")).includes("BlackHole 2ch") || !(await text("audio")).includes("BlackHole 16ch")) {
  throw new Error("station page did not pick the BlackHole devices");
}

await fetch(`${API}/api/v1/panggilan/${callId}/mulai`, { method: "POST" });
log(`${SCENARIO} (${callId}) didahulukan; expected: ${ANNOUNCEMENT ? "announcement, attempt 2 scheduled" : scenario.expected_label}`);

// Robot ears: level meter on BlackHole 16ch (what the recipient would hear).
let aiSpoke = false, lastLoud = 0, aiAudioFrames = 0;
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
    if (peak > SPEAKING_LEVEL) { aiSpoke = true; lastLoud = Date.now(); aiAudioFrames += 1; }
  }
});
const lineIdle = async () => (await json(`${AI}/v1/saluran/status`)).panggilan === "idle";
const waitForAiTurnEnd = async (timeoutMs) => {
  const start = Date.now();
  aiSpoke = false;
  while (Date.now() - start < timeoutMs) {
    if (aiSpoke && Date.now() - lastLoud > TURN_END_MS) return true;
    if (await lineIdle()) return false; // the station hung up
    await sleep(100);
  }
  return false;
};

let pageTranscript = "";
const robot = async (attempt) => {
  log(`robot: attempt ${attempt}, phone rings (ringback tone)`);
  if (ANNOUNCEMENT) {
    await ringback(4);
    log(`robot: carrier announcement -> "${ANNOUNCEMENT_TEXT}"`);
    await speak(announcement);
    return;
  }
  await ringback(8);
  if (!clips.length) { log("robot: recipient never picks up"); return; }
  log('robot: recipient picks up -> "Halo?"');
  await speak(halo);
  for (const [i, clip] of clips.entries()) {
    if (!(await waitForAiTurnEnd(40000))) { log("robot: AI went quiet or the station hung up; stopping"); break; }
    log(`robot: AI turn ended -> recipient says: "${lines[i]}"`);
    await speak(clip);
  }
  log("robot: recipient is done talking; the station must hang up by itself");
};

// One robot run per dial: the station reports "menelepon" right before it dials.
const deadline = Date.now() + 12 * 60 * 1000;
let handled = 0, done = false, call = before;
while (!done && Date.now() < deadline) {
  const galat = await text("galat");
  if (galat) log("station page:", galat);
  call = await getCall();
  if (call.status === "menelepon" && call.percobaan > handled && !(await lineIdle())) {
    handled = call.percobaan;
    log(`station dialled (attempt ${handled}); fake phone is offhook`);
    robot(handled).catch((e) => log("robot error:", e.message));
  }
  pageTranscript = (await text("transkrip")) || pageTranscript;
  if (ANNOUNCEMENT) done = handled >= 1 && call.status === "antre" && call.percobaan === 1;
  else done = (call.status === "selesai" || call.status === "tidak_terhubung") && !!call.label;
  if (!done) await sleep(500);
}

const j = call.jawaban || {};
const entries = (call.log || []).map((x) => `${x.status}${x.catatan ? `(${x.catatan})` : ""}`);
log("RESULT", JSON.stringify({
  status: call.status, percobaan: call.percobaan, label: call.label, coba_lagi_setelah: call.coba_lagi_setelah, log: entries,
  jawaban: { status_panggilan: j.status_panggilan, penerima: j.penerima, hadir: j.hadir, jumlah_maks: j.jumlah_maks, keyakinan: j.keyakinan, tanda_bahaya: j.tanda_bahaya },
  ai_audio_seconds_on_blackhole16: (aiAudioFrames / 10).toFixed(1), line_idle: await lineIdle(),
}));
if (pageTranscript) console.log(`\nStation page log:\n${pageTranscript}`);

const logHas = (status) => (call.log || []).some((x) => x.status === status);
let pass;
if (ANNOUNCEMENT) {
  pass = call.status === "antre" && call.percobaan === 1 && !!call.coba_lagi_setelah && !logHas("tersambung")
    && pageTranscript.includes("pengumuman operator");
} else if (SCENARIO === "S5") {
  pass = call.label === "tidak_terhubung" && call.percobaan === 2 && !logHas("tersambung")
    && (call.log || []).filter((x) => x.catatan === "tidak_diangkat").length === 2
    && (call.log || []).some((x) => x.status === "tidak_terhubung" && String(x.catatan).startsWith("chat:"));
} else {
  pass = !!call.label && call.label.replace("_", " ").toLowerCase() === scenario.expected_label.toLowerCase();
}
pass = pass && (await lineIdle());
await page(`document.getElementById("henti").click(); true`);
await put({ mode_otomatis: settings.mode_otomatis });
log(pass ? "PASS" : "FAIL");
process.exit(pass ? 0 : 1);
