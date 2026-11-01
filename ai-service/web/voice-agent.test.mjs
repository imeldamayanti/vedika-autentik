import assert from "node:assert/strict";
import test from "node:test";

import {
  LiveEventReducer,
  VedikaVoiceSession,
  buildSetupMessage,
  createAgentApi,
  float32ToPcm16,
  parseServerMessage,
  reportWhenAllowed,
  runTask,
  waitForTask,
} from "./voice-agent.mjs";

const TASK = {
  id: "CALL-P-S1-2026-08",
  percobaan: 1,
  no_tujuan: "081200000000",
  skrip: { nama_penerima: "Andi Pratama", tanggal_libur: ["16 Agustus", "17 Agustus"] },
  wa: { lewati: false, teks: "Halo", tautan: "https://wa.me/6281200000000?text=Halo" },
  jeda_wa_menit: 1,
  batas_detik: 150,
};

function fakeApi({ statusReplies = {}, failTranscript = false } = {}) {
  const calls = [];
  return {
    calls,
    lapor: async (id, laporan) => {
      calls.push(["lapor", id, laporan]);
      const reply = statusReplies[laporan];
      if (reply instanceof Error) throw reply;
      return typeof reply === "function" ? reply() : reply ?? { status: laporan };
    },
    kirimTranskrip: async (id, baris) => {
      calls.push(["transkrip", id, baris]);
      if (failTranscript) throw new Error("bukan_berlangsung");
    },
    kirimHasil: async (id, hasil) => {
      calls.push(["hasil", id, hasil]);
      return { status: "membaca_jawaban" };
    },
  };
}

function fakeOperator({ answered = true } = {}) {
  const steps = [];
  return {
    steps,
    kirimWa: async (task) => steps.push(["kirimWa", task.wa.tautan]),
    telepon: async (task) => steps.push(["telepon", task.no_tujuan]),
    diangkat: async () => { steps.push(["diangkat"]); return answered; },
    kirimChatCadangan: async (chat) => steps.push(["kirimChatCadangan", chat.tautan]),
  };
}

test("createAgentApi sends the agent key, JSON reports, and treats 204 as no task", async () => {
  const calls = [];
  const replies = [
    { status: 204 },
    { status: 200, ok: true, json: async () => ({ status: "wa_terkirim" }) },
  ];
  const api = createAgentApi({
    baseUrl: "http://localhost:8000/",
    agentKey: "agen-rahasia",
    fetchImpl: async (...args) => { calls.push(args); return replies.shift(); },
  });

  assert.equal(await api.ambil(), null);
  assert.deepEqual(await api.lapor("CALL-P-S1-2026-08", "wa_terkirim"), { status: "wa_terkirim" });

  assert.equal(calls[0][0], "http://localhost:8000/api/v1/agen/ambil");
  assert.deepEqual(calls[0][1].headers, { "X-Kunci-Agen": "agen-rahasia" });
  assert.equal(calls[1][0], "http://localhost:8000/api/v1/panggilan/CALL-P-S1-2026-08/status");
  assert.equal(calls[1][1].headers["Content-Type"], "application/json");
  const body = JSON.parse(calls[1][1].body);
  assert.equal(body.laporan, "wa_terkirim");
  assert.ok(Date.parse(body.waktu));
});

test("createAgentApi exposes the contract error code", async () => {
  const api = createAgentApi({
    baseUrl: "http://api",
    agentKey: "k",
    fetchImpl: async () => ({
      status: 409,
      ok: false,
      json: async () => ({ galat: { kode: "jeda_belum_lewat", pesan: "Tunggu." } }),
    }),
  });

  await assert.rejects(api.lapor("CALL-1", "menelepon"), (error) => {
    assert.equal(error.status, 409);
    assert.equal(error.kode, "jeda_belum_lewat");
    return true;
  });
});

test("createAgentApi uploads the result as multipart recording, transcript, and duration", async () => {
  let sent;
  const api = createAgentApi({
    baseUrl: "http://api",
    agentKey: "k",
    fetchImpl: async (url, init) => {
      sent = [url, init];
      return { status: 202, ok: true, json: async () => ({ status: "membaca_jawaban" }) };
    },
  });
  const transkrip = [{ detik: 0, pembicara: "ai", teks: "Selamat siang." }];

  await api.kirimHasil("CALL-1", { transkrip, rekaman: new Blob(["audio"]), durasi: 92 });

  const [url, init] = sent;
  assert.equal(url, "http://api/api/v1/panggilan/CALL-1/hasil");
  assert.equal(init.headers["Content-Type"], undefined);
  assert.equal(init.body.get("rekaman").name, "CALL-1.webm");
  assert.deepEqual(JSON.parse(init.body.get("transkrip")), transkrip);
  assert.equal(init.body.get("durasi"), "92");
});

test("createAgentApi names the recording after its MediaRecorder type", async () => {
  const names = [];
  const api = createAgentApi({
    baseUrl: "http://api",
    agentKey: "k",
    fetchImpl: async (_url, init) => {
      names.push(init.body.get("rekaman").name);
      return { status: 202, ok: true, json: async () => ({}) };
    },
  });

  for (const type of ["audio/webm;codecs=opus", "audio/mp4", "audio/mpeg", ""]) {
    await api.kirimHasil("CALL-1", { transkrip: [], rekaman: new Blob(["a"], { type }), durasi: 1 });
  }

  assert.deepEqual(names, ["CALL-1.webm", "CALL-1.m4a", "CALL-1.mp3", "CALL-1.webm"]);
});

test("waitForTask polls every three seconds until the backend hands out a task", async () => {
  const replies = [null, null, TASK];
  const sleeps = [];

  const task = await waitForTask(
    { ambil: async () => replies.shift() },
    { sleep: async (ms) => sleeps.push(ms) },
  );

  assert.equal(task, TASK);
  assert.deepEqual(sleeps, [3000, 3000]);
});

test("reportWhenAllowed retries each second only while the WA delay has not passed", async () => {
  const early = Object.assign(new Error("Tunggu."), { kode: "jeda_belum_lewat" });
  let attempts = 0;
  const sleeps = [];
  const api = {
    lapor: async () => {
      attempts += 1;
      if (attempts < 3) throw early;
      return { status: "menelepon" };
    },
  };

  assert.deepEqual(
    await reportWhenAllowed(api, "CALL-1", "menelepon", { sleep: async (ms) => sleeps.push(ms) }),
    { status: "menelepon" },
  );
  assert.deepEqual(sleeps, [1000, 1000]);

  const wrongOrder = Object.assign(new Error("Urutan."), { kode: "urutan_salah" });
  await assert.rejects(
    reportWhenAllowed({ lapor: async () => { throw wrongOrder; } }, "CALL-1", "menelepon"),
    /Urutan/,
  );
});

test("runTask reports an answered first attempt in contract order and uploads the result", async () => {
  const api = fakeApi();
  const operator = fakeOperator();
  const hasil = { transkrip: [], rekaman: new Blob(["audio"]), durasi: 90 };

  const reply = await runTask({
    api,
    task: TASK,
    operator,
    converse: async (task, { onStarted, onTurn }) => {
      assert.equal(task, TASK);
      await onStarted();
      onTurn({ detik: 0, pembicara: "ai", teks: "Selamat siang." });
      onTurn({ detik: 4, pembicara: "penerima", teks: "Iya." });
      return hasil;
    },
  });

  assert.deepEqual(reply, { status: "membaca_jawaban" });
  assert.deepEqual(operator.steps.map(([name]) => name), ["kirimWa", "telepon", "diangkat"]);
  assert.deepEqual(api.calls, [
    ["lapor", TASK.id, "wa_terkirim"],
    ["lapor", TASK.id, "menelepon"],
    ["lapor", TASK.id, "tersambung"],
    ["lapor", TASK.id, "merekam"],
    ["transkrip", TASK.id, [{ detik: 0, pembicara: "ai", teks: "Selamat siang." }]],
    ["transkrip", TASK.id, [{ detik: 4, pembicara: "penerima", teks: "Iya." }]],
    ["hasil", TASK.id, hasil],
  ]);
});

test("runTask skips WA on the second attempt and sends the fallback chat when unanswered", async () => {
  const chat = { teks: "Kami belum berhasil menelepon.", tautan: "https://wa.me/62812?text=Kami" };
  const api = fakeApi({
    statusReplies: {
      tidak_diangkat: { status: "tidak_terhubung", percobaan: 2, chat_cadangan: chat },
    },
  });
  const operator = fakeOperator({ answered: false });

  const reply = await runTask({
    api,
    task: { ...TASK, percobaan: 2, wa: { ...TASK.wa, lewati: true } },
    operator,
    converse: async () => assert.fail("unanswered calls never start the voice agent"),
  });

  assert.equal(reply.status, "tidak_terhubung");
  assert.deepEqual(operator.steps, [
    ["telepon", TASK.no_tujuan],
    ["diangkat"],
    ["kirimChatCadangan", chat.tautan],
  ]);
  assert.deepEqual(api.calls.map(([, , laporan]) => laporan), [
    "menelepon",
    "tidak_diangkat",
    "chat_cadangan_terkirim",
  ]);
});

test("runTask returns a first-attempt no-answer to the queue without a fallback chat", async () => {
  const api = fakeApi({
    statusReplies: { tidak_diangkat: { status: "antre", percobaan: 1, chat_cadangan: null } },
  });
  const operator = fakeOperator({ answered: false });

  const reply = await runTask({ api, task: TASK, operator, converse: async () => ({}) });

  assert.equal(reply.status, "antre");
  assert.equal(operator.steps.some(([name]) => name === "kirimChatCadangan"), false);
});

test("runTask still uploads the result when a live transcript line is rejected", async () => {
  const api = fakeApi({ failTranscript: true });
  const errors = [];

  await runTask({
    api,
    task: TASK,
    operator: fakeOperator(),
    onError: (error) => errors.push(error.message),
    converse: async (_task, { onTurn }) => {
      onTurn({ detik: 0, pembicara: "ai", teks: "Halo." });
      return { transkrip: [], rekaman: null, durasi: 3 };
    },
  });

  assert.deepEqual(errors, ["bukan_berlangsung"]);
  assert.equal(api.calls.at(-1)[0], "hasil");
});

test("session joins streamed fragments into one line per speaking turn", async () => {
  const lines = [];
  const session = new VedikaVoiceSession({ onTranscript: (turn) => lines.push(turn) });
  session.startedAt = performance.now() - 45_500;
  const frame = (content) => JSON.stringify({ serverContent: content });

  await session.handleMessage(frame({ outputTranscription: { text: "Berapa" } }));
  await session.handleMessage(frame({ outputTranscription: { text: " kali?" } }));
  await session.handleMessage(frame({ inputTranscription: { text: "Tiga" } }));
  await session.handleMessage(frame({ inputTranscription: { text: " kali." }, turnComplete: true }));
  await session.handleMessage(frame({ outputTranscription: { text: "Baik." } }));
  const result = await session.stop();

  assert.deepEqual(lines, [
    { detik: 45, pembicara: "ai", teks: "Berapa kali?" },
    { detik: 45, pembicara: "penerima", teks: "Tiga kali." },
    { detik: 45, pembicara: "ai", teks: "Baik." },
  ]);
  assert.deepEqual(result.transkrip, lines);
  assert.ok(result.durasi >= 45 && result.durasi <= 47);
});

test("float32ToPcm16 clamps and converts little-endian samples", () => {
  const bytes = float32ToPcm16(new Float32Array([-2, -0.5, 0, 0.5, 2]));
  const values = new Int16Array(bytes.buffer);

  assert.deepEqual([...values], [-32768, -16384, 0, 16383, 32767]);
});

test("buildSetupMessage enables audio plus both finalized transcriptions", () => {
  const message = buildSetupMessage("gemini-live-test", "Instruksi aman");

  assert.equal(message.setup.model, "models/gemini-live-test");
  assert.deepEqual(message.setup.generationConfig.responseModalities, ["AUDIO"]);
  assert.deepEqual(message.setup.inputAudioTranscription, {});
  assert.deepEqual(message.setup.outputAudioTranscription, {});
  assert.equal(message.setup.systemInstruction.parts[0].text, "Instruksi aman");
});

test("parseServerMessage returns audio, finalized turns, and interruption", async () => {
  const audio = Buffer.from(new Int16Array([1, -1]).buffer).toString("base64");
  const parsed = await parseServerMessage(
    JSON.stringify({
      serverContent: {
        inputTranscription: { text: "Tiga kali." },
        outputTranscription: { text: "Baik, tiga kali." },
        interrupted: true,
        turnComplete: true,
        modelTurn: { parts: [{ inlineData: { data: audio } }] },
      },
    }),
  );

  assert.equal(parsed.audioChunks.length, 1);
  assert.deepEqual(parsed.turns, [
    { pembicara: "penerima", teks: "Tiga kali." },
    { pembicara: "ai", teks: "Baik, tiga kali." },
  ]);
  assert.equal(parsed.interrupted, true);
  assert.equal(parsed.turnComplete, true);
});

test("parseServerMessage decodes Blob and ArrayBuffer frames", async () => {
  const payload = JSON.stringify({ setupComplete: {} });

  assert.equal((await parseServerMessage(new Blob([payload]))).setupComplete, true);
  assert.equal(
    (await parseServerMessage(new TextEncoder().encode(payload).buffer)).setupComplete,
    true,
  );
});

test("session handles a binary setup frame before marking itself ready", async () => {
  const statuses = [];
  const session = new VedikaVoiceSession({ onStatus: (status) => statuses.push(status) });

  await session.handleMessage(new Blob([JSON.stringify({ setupComplete: {} })]));

  assert.equal(session.ready, true);
  assert.deepEqual(statuses, ["tersambung"]);
});

test("session cues the AI to open the call once the session is set up", async () => {
  const sent = [];
  const session = new VedikaVoiceSession({});
  session.socket = { send: (message) => sent.push(JSON.parse(message)) };

  await session.handleMessage(JSON.stringify({ setupComplete: {} }));
  await session.handleMessage(JSON.stringify({ setupComplete: {} }));

  assert.equal(sent.length, 1);
  assert.equal(sent[0].clientContent.turnComplete, true);
  assert.equal(sent[0].clientContent.turns[0].role, "user");
  assert.match(sent[0].clientContent.turns[0].parts[0].text, /pembuka/);
});

function startWithContext(audioContext, errors) {
  return new VedikaVoiceSession({
    audioContext,
    fetchImpl: async () => ({
      ok: true,
      json: async () => ({ token: "t", websocket_url: "wss://example", model: "live" }),
    }),
    AudioContextImpl: class { constructor() { throw new Error("must reuse the click-time context"); } },
    mediaDevices: { getUserMedia: async () => { throw new Error("stop after audio setup"); } },
    onError: (error) => errors.push(error.message),
  }).start();
}

test("session reuses the audio context created at the operator's click", async () => {
  const errors = [];
  const context = { state: "running", close: async () => {} };

  await assert.rejects(startWithContext(context, errors), /stop after audio setup/);

  assert.deepEqual(errors, ["stop after audio setup"]);
});

test("session reports a locked browser audio context instead of failing silently", async () => {
  const errors = [];
  const context = { state: "suspended", resume: async () => {}, close: async () => {} };

  await assert.rejects(startWithContext(context, errors), /audio Chrome terkunci/);

  assert.match(errors[0], /audio Chrome terkunci/);
});

test("session captures the call line without Chrome echo cancellation or processing", async () => {
  let constraints;
  const session = new VedikaVoiceSession({
    inputDeviceId: "bh2",
    audioContext: { state: "running", close: async () => {} },
    fetchImpl: async () => ({
      ok: true,
      json: async () => ({ token: "t", websocket_url: "wss://example", model: "live" }),
    }),
    mediaDevices: {
      getUserMedia: async (requested) => {
        constraints = requested;
        throw new Error("stop after capture");
      },
    },
  });

  await assert.rejects(session.start(), /stop after capture/);

  assert.deepEqual(constraints, {
    audio: {
      deviceId: { exact: "bh2" },
      channelCount: 1,
      echoCancellation: false,
      noiseSuppression: false,
      autoGainControl: false,
    },
  });
});

test("stopping an actual session closes a CONNECTING socket", async () => {
  class ConnectingSocket {
    static CONNECTING = 0;
    static OPEN = 1;

    constructor() {
      this.readyState = ConnectingSocket.CONNECTING;
      this.listeners = new Map();
      this.closed = false;
    }

    addEventListener(name, callback) {
      this.listeners.set(name, callback);
    }

    close() {
      this.closed = true;
    }
  }

  const session = new VedikaVoiceSession({ WebSocketImpl: ConnectingSocket });
  const socket = new ConnectingSocket();
  session.socket = socket;

  await session.stop("dibatalkan");

  assert.equal(socket.closed, true);
});

test("failed startup rolls back an opened audio context", async () => {
  let contextClosed = false;
  class FakeAudioContext {
    async close() {
      contextClosed = true;
    }
  }
  const session = new VedikaVoiceSession({
    fetchImpl: async () => ({
      ok: true,
      json: async () => ({ token: "one-use", websocket_url: "wss://example", model: "live" }),
    }),
    AudioContextImpl: FakeAudioContext,
    mediaDevices: { getUserMedia: async () => { throw new Error("permission denied"); } },
  });

  await assert.rejects(session.start(), /permission denied/);

  assert.equal(contextClosed, true);
});

test("stopping during permission wait releases the late input stream", async () => {
  let resolveMedia;
  const mediaPromise = new Promise((resolve) => { resolveMedia = resolve; });
  let trackStopped = false;
  class FakeAudioContext {
    async close() {}
  }
  const session = new VedikaVoiceSession({
    fetchImpl: async () => ({
      ok: true,
      json: async () => ({ token: "one-use", websocket_url: "wss://example", model: "live" }),
    }),
    AudioContextImpl: FakeAudioContext,
    mediaDevices: { getUserMedia: () => mediaPromise },
  });

  const startPromise = session.start();
  await new Promise((resolve) => setTimeout(resolve, 0));
  await session.stop("dibatalkan");
  resolveMedia({ getTracks: () => [{ stop: () => { trackStopped = true; } }] });

  await assert.rejects(startPromise, /session stopped/);
  assert.equal(trackStopped, true);
});

test("unexpected socket close cleans active media exactly once", async () => {
  let inputStopped = 0;
  let contextClosed = 0;
  let completed = 0;
  const session = new VedikaVoiceSession({
    onComplete: () => { completed += 1; },
  });
  session.inputStream = { getTracks: () => [{ stop: () => { inputStopped += 1; } }] };
  session.audioContext = { currentTime: 0, close: async () => { contextClosed += 1; } };

  await session.handleSocketClose();
  await session.handleSocketClose();

  assert.equal(inputStopped, 1);
  assert.equal(contextClosed, 1);
  assert.equal(completed, 1);
});

test("cleanup stops a paused recorder and preserves its collected recording", async () => {
  let recorderStopped = 0;
  let stopListener;
  const session = new VedikaVoiceSession({});
  session.recordedChunks = [new Blob(["audio"])];
  session.recorder = {
    state: "paused",
    mimeType: "audio/webm",
    addEventListener: (name, callback) => {
      if (name === "stop") stopListener = callback;
    },
    stop: () => {
      recorderStopped += 1;
      stopListener();
    },
  };

  const result = await session.stop();

  assert.equal(recorderStopped, 1);
  assert.equal(result.recording.size, 5);
});

test("LiveEventReducer maps provider events to required lifecycle and clear action", () => {
  const reducer = new LiveEventReducer();

  assert.deepEqual(reducer.reduce({ setupComplete: true }), {
    status: "tersambung",
    clearPlayback: false,
  });
  assert.deepEqual(reducer.reduce({ turns: [{ pembicara: "penerima", teks: "Halo" }] }), {
    status: "merekam",
    clearPlayback: false,
  });
  assert.deepEqual(reducer.reduce({ interrupted: true }), {
    status: "merekam",
    clearPlayback: true,
  });
  assert.deepEqual(reducer.reduce({ turnComplete: true }), {
    status: "membaca_jawaban",
    clearPlayback: false,
  });
  assert.deepEqual(reducer.close(), { status: "selesai", clearPlayback: true });
});

function installStrictGlobalFetch(t) {
  const calls = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = function (url, init) {
    if (this !== undefined && this !== globalThis) throw new TypeError("Illegal invocation");
    calls.push([url, init]);
    return Promise.resolve({ ok: false, status: 503, json: async () => ({}) });
  };
  t.after(() => { globalThis.fetch = originalFetch; });
  return calls;
}

test("session calls the global fetch without rebinding it to the session", async (t) => {
  const calls = installStrictGlobalFetch(t);
  const session = new VedikaVoiceSession({ context: { nama_penerima: "Andi" } });

  await assert.rejects(session.start(), /token endpoint 503/);

  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], "/v1/suara/token");
});

test("createAgentApi calls the global fetch without rebinding it", async (t) => {
  const calls = installStrictGlobalFetch(t);
  const api = createAgentApi({ baseUrl: "http://api", agentKey: "k" });

  await assert.rejects(api.ambil(), /API 503/);

  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], "http://api/api/v1/agen/ambil");
});
