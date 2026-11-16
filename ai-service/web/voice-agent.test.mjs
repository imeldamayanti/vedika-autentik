import assert from "node:assert/strict";
import test from "node:test";

import {
  ANSWER_TIMEOUT_MS,
  AUDIO_BLOCKED,
  CLOSING_HANGUP_MS,
  GOODBYE_TAIL_MS,
  LINE_POLL_MS,
  LiveEventReducer,
  PICKUP_SILENCE_MS,
  SILENCE_HANGUP_MS,
  SILENCE_NUDGE,
  REPLY_NUDGE,
  VOICE_ACTIVITY_RMS,
  VedikaVoiceSession,
  buildSetupMessage,
  createAgentApi,
  createLineApi,
  createStationOperator,
  isCallGone,
  isClosingLine,
  isGoodbyePhrase,
  isOperatorAnnouncement,
  pickDevice,
  stationTick,
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

function fakeOperator(api) {
  const steps = [];
  const note = (step) => { steps.push(step); api?.calls.push(["operator", step[0]]); };
  return {
    steps,
    kirimWa: async (task) => note(["kirimWa", task.wa.tautan]),
    telepon: async (task) => note(["telepon", task.no_tujuan]),
    kirimChatCadangan: async (chat) => note(["kirimChatCadangan", chat.tautan]),
    batal: async () => note(["batal"]),
  };
}

const SERVER_TASK = { ...TASK, wa: { lewati: true, dikirim_server: true, status: "terkirim", teks: "Halo" } };
const gone = (status, kode) => Object.assign(new Error(kode || "tidak ada"), { status, kode });

const unanswered = async () => ({ answered: false, transkrip: [], rekaman: null, durasi: 0 });

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

test("runTask reports menelepon before dialing and then follows the contract order", async () => {
  const api = fakeApi();
  const operator = fakeOperator(api);
  const hasil = { answered: true, transkrip: [], rekaman: new Blob(["audio"]), durasi: 90 };

  const reply = await runTask({
    api,
    task: TASK,
    operator,
    converse: async (task, { onAnswered, onTurn }) => {
      assert.equal(task, TASK);
      onTurn({ detik: 0, pembicara: "ai", teks: "Selamat siang." });
      await onAnswered();
      onTurn({ detik: 0, pembicara: "penerima", teks: "Halo?" });
      return hasil;
    },
  });

  assert.deepEqual(reply, { status: "membaca_jawaban" });
  assert.deepEqual(operator.steps.map(([name]) => name), ["kirimWa", "telepon"]);
  assert.deepEqual(api.calls, [
    ["operator", "kirimWa"],
    ["lapor", TASK.id, "wa_terkirim"],
    ["lapor", TASK.id, "menelepon"],
    ["operator", "telepon"],
    ["lapor", TASK.id, "tersambung"],
    ["lapor", TASK.id, "merekam"],
    ["transkrip", TASK.id, [{ detik: 0, pembicara: "ai", teks: "Selamat siang." }]],
    ["transkrip", TASK.id, [{ detik: 0, pembicara: "penerima", teks: "Halo?" }]],
    ["hasil", TASK.id, hasil],
  ]);
});

test("runTask skips WA on the second attempt and sends the fallback chat when nobody speaks", async () => {
  const chat = { teks: "Kami belum berhasil menelepon.", tautan: "https://wa.me/62812?text=Kami" };
  const api = fakeApi({
    statusReplies: {
      tidak_diangkat: { status: "tidak_terhubung", percobaan: 2, chat_cadangan: chat },
    },
  });
  const operator = fakeOperator();

  const reply = await runTask({
    api,
    task: { ...TASK, percobaan: 2, wa: { ...TASK.wa, lewati: true } },
    operator,
    converse: unanswered,
  });

  assert.equal(reply.status, "tidak_terhubung");
  assert.deepEqual(operator.steps, [
    ["telepon", TASK.no_tujuan],
    ["kirimChatCadangan", chat.tautan],
  ]);
  assert.deepEqual(api.calls.map(([, , laporan]) => laporan), [
    "menelepon",
    "tidak_diangkat",
    "chat_cadangan_terkirim",
  ]);
});

test("runTask skips WA the server already sent and waits out the delay before dialing", async () => {
  const early = Object.assign(new Error("Tunggu."), { status: 409, kode: "jeda_belum_lewat" });
  let tries = 0;
  const api = fakeApi({ statusReplies: { menelepon: () => { tries += 1; if (tries < 3) throw early; return { status: "menelepon" }; } } });
  const operator = fakeOperator(api);
  const sleeps = [];

  await runTask({ api, task: SERVER_TASK, operator, converse: unanswered, sleep: async (ms) => sleeps.push(ms) });

  assert.deepEqual(sleeps, [1000, 1000]);
  assert.deepEqual(api.calls.map((call) => call.at(-1)), ["menelepon", "menelepon", "menelepon", "telepon", "tidak_diangkat"]);
  assert.equal(operator.steps.some(([name]) => name === "kirimWa"), false);
});

test("runTask leaves a server-sent fallback chat alone", async () => {
  const api = fakeApi({
    statusReplies: {
      tidak_diangkat: { status: "tidak_terhubung", percobaan: 2, chat_cadangan: { teks: "Kami", dikirim_server: true, status: "terkirim" } },
    },
  });
  const operator = fakeOperator();

  const reply = await runTask({ api, task: { ...SERVER_TASK, percobaan: 2 }, operator, converse: unanswered });

  assert.equal(reply.status, "tidak_terhubung");
  assert.deepEqual(operator.steps, [["telepon", TASK.no_tujuan]]);
  assert.equal(api.calls.some((call) => call[2] === "chat_cadangan_terkirim"), false);
});

test("runTask counts a failed dial as an unanswered attempt", async () => {
  const api = fakeApi({ statusReplies: { tidak_diangkat: { status: "antre", percobaan: 1, chat_cadangan: null } } });
  const errors = [];
  let conversed = false;

  const reply = await runTask({
    api,
    task: SERVER_TASK,
    operator: { ...fakeOperator(), telepon: async () => { throw new Error("adb_gagal"); } },
    converse: async () => { conversed = true; return unanswered(); },
    onError: (error) => errors.push(error.message),
  });

  assert.equal(reply.status, "antre");
  assert.equal(conversed, false);
  assert.deepEqual(errors, ["adb_gagal"]);
  assert.deepEqual(api.calls.map((call) => call[2]), ["menelepon", "tidak_diangkat"]);
});

for (const [name, error] of [
  ["409 urutan_salah", gone(409, "urutan_salah")],
  ["409 bukan_berlangsung", gone(409, "bukan_berlangsung")],
  ["404", gone(404, "panggilan_tidak_ada")],
]) {
  test(`runTask stops quietly when the backend answers ${name} to a status report`, async () => {
    const api = fakeApi({ statusReplies: { menelepon: error } });
    const operator = fakeOperator();
    const logs = [];

    const reply = await runTask({ api, task: SERVER_TASK, operator, converse: unanswered, onLog: (line) => logs.push(line) });

    assert.deepEqual(reply, { status: "dibatalkan" });
    assert.deepEqual(operator.steps, [["batal"]]); // never dialed, session stopped and line hung up
    assert.equal(logs.length, 1);
    assert.match(logs[0], /CALL-P-S1-2026-08: dibatalkan/);
  });
}

test("runTask stops the session when the answer report finds the call cancelled", async () => {
  const api = fakeApi({ statusReplies: { tersambung: gone(409, "urutan_salah") } });
  const operator = fakeOperator();
  const logs = [];
  const errors = [];

  const reply = await runTask({
    api,
    task: SERVER_TASK,
    operator,
    onLog: (line) => logs.push(line),
    onError: (error) => errors.push(error),
    converse: async (_task, { onAnswered, onTurn }) => {
      await onAnswered();
      onTurn({ detik: 0, pembicara: "penerima", teks: "Halo?" });
      return { answered: true, transkrip: [], rekaman: null, durasi: 2 };
    },
  });

  assert.deepEqual(reply, { status: "dibatalkan" });
  assert.deepEqual(operator.steps.map(([name]) => name), ["telepon", "batal"]);
  assert.equal(logs.length, 1);
  assert.deepEqual(errors, []);
  assert.equal(api.calls.some(([kind]) => kind === "hasil"), false);
});

test("runTask stops without uploading when a transcript line or the result is refused as cancelled", async () => {
  for (const failing of ["kirimTranskrip", "kirimHasil"]) {
    const api = fakeApi();
    api[failing] = async () => { throw gone(409, "bukan_berlangsung"); };
    const operator = fakeOperator();
    const logs = [];

    const reply = await runTask({
      api,
      task: SERVER_TASK,
      operator,
      onLog: (line) => logs.push(line),
      converse: async (_task, { onAnswered, onTurn }) => {
        await onAnswered();
        onTurn({ detik: 0, pembicara: "penerima", teks: "Halo?" });
        return { answered: true, transkrip: [], rekaman: null, durasi: 2 };
      },
    });

    assert.deepEqual(reply, { status: "dibatalkan" }, failing);
    assert.equal(operator.steps.at(-1)[0], "batal", failing);
    assert.equal(logs.length, 1, failing);
  }
});

test("runTask still raises errors that are not a cancellation", async () => {
  const api = fakeApi({ statusReplies: { menelepon: gone(500, "galat") } });

  await assert.rejects(runTask({ api, task: SERVER_TASK, operator: fakeOperator(), converse: unanswered }), /galat/);
  assert.equal(isCallGone(gone(409, "jeda_belum_lewat")), false);
  assert.equal(isCallGone(new Error("jaringan")), false);
});

test("runTask returns a first-attempt no-answer to the queue without a fallback chat", async () => {
  const api = fakeApi({
    statusReplies: { tidak_diangkat: { status: "antre", percobaan: 1, chat_cadangan: null } },
  });
  const operator = fakeOperator();

  const reply = await runTask({ api, task: TASK, operator, converse: unanswered });

  assert.equal(reply.status, "antre");
  assert.equal(operator.steps.some(([name]) => name === "kirimChatCadangan"), false);
  assert.equal(api.calls.some(([kind]) => kind === "transkrip" || kind === "hasil"), false);
});

test("runTask still uploads the result when a live transcript line is rejected", async () => {
  const api = fakeApi({ failTranscript: true });
  const errors = [];

  await runTask({
    api,
    task: TASK,
    operator: fakeOperator(),
    onError: (error) => errors.push(error.message),
    converse: async (_task, { onAnswered, onTurn }) => {
      await onAnswered();
      onTurn({ detik: 0, pembicara: "penerima", teks: "Halo." });
      return { answered: true, transkrip: [], rekaman: null, durasi: 3 };
    },
  });

  assert.deepEqual(errors, ["bukan_berlangsung"]);
  assert.equal(api.calls.at(-1)[0], "hasil");
});

const frame = (content) => JSON.stringify({ serverContent: content });

test("session counts the recipient's first completed turn as the answer and restarts the clock", async () => {
  const events = [];
  const lines = [];
  const session = new VedikaVoiceSession({
    greetFirst: false,
    onSpeech: (pembicara) => events.push(`speech:${pembicara}`),
    onAnswer: () => events.push("answer"),
    onTranscript: (turn) => { lines.push(turn); events.push(`line:${turn.pembicara}`); },
  });
  const sent = [];
  session.socket = { send: (m) => sent.push(m) };
  session.startedAt = performance.now() - 20_000;

  await session.handleMessage(JSON.stringify({ setupComplete: {} }));
  await session.handleMessage(frame({ inputTranscription: { text: "Halo?" } }));
  await session.handleMessage(frame({ inputTranscription: { text: " Iya." } }));

  assert.equal(sent.length, 0);
  assert.deepEqual(events, ["speech:penerima", "speech:penerima"]); // fragments alone are not an answer
  await session.handleMessage(frame({ outputTranscription: { text: "Selamat siang." } }));

  assert.deepEqual(events.slice(2), ["answer", "line:penerima", "speech:ai"]);
  assert.deepEqual(lines, [{ detik: 0, pembicara: "penerima", teks: "Halo? Iya." }]);
  assert.ok(performance.now() - session.startedAt < 1000);
  await session.stop();
  assert.deepEqual(lines.at(-1), { detik: 0, pembicara: "ai", teks: "Selamat siang." });
});

test("session asks acceptAnswer per completed recipient turn and keeps the clock on a rejection", async () => {
  const asked = [];
  const answers = [];
  const rejected = [];
  const session = new VedikaVoiceSession({
    greetFirst: false,
    acceptAnswer: (teks) => { asked.push(teks); return !isOperatorAnnouncement(teks); },
    onAnswer: () => answers.push(true),
    onRejectedAnswer: (turn) => rejected.push(turn.teks),
  });
  const dialedAt = performance.now() - 12_000;
  session.startedAt = dialedAt;

  await session.handleMessage(frame({ inputTranscription: { text: "Nomor yang Anda tuju" } }));
  await session.handleMessage(frame({ inputTranscription: { text: " tidak dapat dihubungi." }, turnComplete: true }));

  assert.deepEqual(asked, ["Nomor yang Anda tuju tidak dapat dihubungi."]);
  assert.deepEqual(rejected, asked);
  assert.equal(answers.length, 0);
  assert.equal(session.startedAt, dialedAt);
  assert.equal(session.transkrip[0].detik, 12);

  await session.handleMessage(frame({ inputTranscription: { text: "Halo?" }, turnComplete: true }));
  await session.handleMessage(frame({ inputTranscription: { text: "Siapa ini?" }, turnComplete: true }));

  assert.equal(answers.length, 1);
  assert.equal(asked.length, 2); // not asked again once answered
  await session.stop();
});

test("session joins streamed fragments into one line per speaking turn", async () => {
  const lines = [];
  const session = new VedikaVoiceSession({ onTranscript: (turn) => lines.push(turn) });
  session.startedAt = performance.now() - 45_500;

  await session.handleMessage(frame({ outputTranscription: { text: "Berapa" } }));
  await session.handleMessage(frame({ outputTranscription: { text: " kali?" } }));
  await session.handleMessage(frame({ inputTranscription: { text: "Tiga" } }));
  await session.handleMessage(frame({ inputTranscription: { text: " kali." }, turnComplete: true }));
  await session.handleMessage(frame({ outputTranscription: { text: "Baik." } }));
  const result = await session.stop();

  assert.deepEqual(lines, [
    { detik: 45, pembicara: "ai", teks: "Berapa kali?" },
    { detik: 0, pembicara: "penerima", teks: "Tiga kali." },
    { detik: 0, pembicara: "ai", teks: "Baik." },
  ]);
  assert.deepEqual(result.transkrip, lines);
  assert.ok(result.durasi <= 1);
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
  assert.equal(message.setup.generationConfig.temperature, 0.4);
  assert.deepEqual(message.setup.inputAudioTranscription, { languageCodes: ["id-ID"] });
  assert.equal(message.setup.realtimeInputConfig.automaticActivityDetection.startOfSpeechSensitivity, "START_SENSITIVITY_HIGH");
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

  await assert.rejects(startWithContext(context, errors), /Chrome memblokir audio; jalankan lewat stasiun\.sh/);

  assert.equal(errors[0], AUDIO_BLOCKED);
});

test("session passes lineConstraints through for speaker mode", async () => {
  let constraints;
  const session = new VedikaVoiceSession({
    lineConstraints: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
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
    audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
  });
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

test("isOperatorAnnouncement recognises carrier recordings in any case and punctuation", () => {
  for (const teks of [
    "Nomor yang Anda tuju tidak dapat dihubungi.",
    "NOMOR YANG ANDA TUJU, sedang sibuk!",
    "Mohon maaf, nomor ini tidak aktif.",
    "Telepon yang Anda hubungi sedang sibuk.",
    "…berada di luar jangkauan. Silakan coba beberapa saat lagi.",
    "Pelanggan berada di luar service area",
    "Anda terhubung ke kotak suara.",
    "Mailbox penuh.",
    "Silakan tinggalkan pesan setelah nada berikut.",
    "Silakan   coba\nlagi nanti",
    "The number you are calling is not active.",
    "The number you have dialed is busy",
    "The subscriber cannot be reached at the moment.",
    "the number is not active",
  ]) assert.equal(isOperatorAnnouncement(teks), true, teks);
  for (const teks of ["Halo?", "Iya, saya sendiri.", "Halo, ini siapa ya?", "Tiga kali.", "Nomor saya yang ini.", "", null]) {
    assert.equal(isOperatorAnnouncement(teks), false, String(teks));
  }
});

test("isClosingLine matches a farewell at the end of a turn or 'sudah kami catat'", () => {
  for (const teks of [
    "Terima kasih, Bapak Andi. Jawaban ini tidak memengaruhi layanan atau iuran. Selamat siang.",
    "Baik, terima kasih. Selamat sore!",
    "Jawaban Ibu sudah kami catat. Terima kasih.",
    "Baik, sudah kami catat, tiga kali ya. Terima kasih banyak atas waktunya.",
    "SELAMAT MALAM",
    "Terima kasih banyak atas informasinya. Informasi ini tidak memengaruhi layanan atau iuran Bapak.",
    "Baik, Bapak, sudah saya catat. Jawaban ini tidak akan memengaruhi layanan atau iuran Anda. Terima kasih atas waktunya.",
    "Terima kasih atas waktunya.",
  ]) assert.equal(isClosingLine(teks), true, teks);
  for (const teks of [
    "Selamat siang, saya asisten otomatis dari BPJS Kesehatan. Panggilan ini direkam. Ini bukan tagihan, dan kami tidak meminta NIK, OTP, rekening, atau uang.",
    "Selamat siang. Apakah benar saya berbicara dengan Bapak Andi?",
    "Tiga kali, sudah kami catat. Apakah Bapak terapi pada tanggal 16 Agustus?",
    "Kira-kira berapa kali?",
    "",
  ]) assert.equal(isClosingLine(teks), false, teks);
});

test("pickDevice finds a device by label substring and falls back to the default", () => {
  const devices = [
    { kind: "audioinput", label: "MacBook Pro Microphone", deviceId: "mic" },
    { kind: "audioinput", label: "BlackHole 2ch (Virtual)", deviceId: "bh2" },
    { kind: "audiooutput", label: "BlackHole 2ch (Virtual)", deviceId: "out2" },
  ];

  assert.equal(pickDevice(devices, "audioinput", "BlackHole 2ch").deviceId, "bh2");
  assert.equal(pickDevice(devices, "audiooutput", "BlackHole 2ch").deviceId, "out2");
  assert.equal(pickDevice(devices, "audioinput", "USB Audio"), null);
  assert.equal(pickDevice(devices, "audioinput", null), null);
});

test("createLineApi talks to the same-origin Phone helper and exposes its error codes", async () => {
  const calls = [];
  const replies = [
    { ok: true, status: 200, json: async () => ({ ok: true }) },
    { ok: false, status: 404, json: async () => ({ detail: "Not Found" }) },
    { ok: false, status: 502, json: async () => ({ galat: { kode: "adb_gagal", pesan: "Perintah ke HP saluran gagal." } }) },
  ];
  const line = createLineApi({ fetchImpl: async (...args) => { calls.push(args); return replies.shift(); } });

  assert.deepEqual(await line.panggil("081200000000"), { ok: true });
  await assert.rejects(line.konfigurasi(), (error) => error.status === 404);
  await assert.rejects(line.tutup(), (error) => error.kode === "adb_gagal" && /HP saluran/.test(error.message));

  assert.equal(calls[0][0], "/v1/saluran/panggil");
  assert.equal(calls[0][1].method, "POST");
  assert.deepEqual(JSON.parse(calls[0][1].body), { nomor: "081200000000" });
  assert.deepEqual(calls[1], ["/v1/saluran/konfigurasi", { method: "GET", headers: {}, body: undefined }]);
});

test("createAgentApi posts the station heartbeat", async () => {
  let sent;
  const api = createAgentApi({
    baseUrl: "http://api",
    agentKey: "k",
    fetchImpl: async (url, init) => { sent = [url, init]; return { status: 204 }; },
  });

  assert.equal(await api.detak({ siap: true, alasan: null, perangkat: "Pixel 7" }), null);
  assert.equal(sent[0], "http://api/api/v1/agen/detak");
  assert.deepEqual(JSON.parse(sent[1].body), { siap: true, alasan: null, perangkat: "Pixel 7" });
});

test("stationTick sends health as the heartbeat and claims a task only when ready", async () => {
  const run = async ({ sehat, audio = true, task = TASK }) => {
    const calls = [];
    const result = await stationTick({
      line: { kesehatan: async () => { if (sehat instanceof Error) throw sehat; return sehat; } },
      api: { detak: async (body) => { calls.push(["detak", body]); }, ambil: async () => { calls.push(["ambil"]); return task; } },
      audioReady: () => audio,
    });
    return { calls, result };
  };

  const ready = await run({ sehat: { siap: true, alasan: null, perangkat: "Pixel 7", sim: "READY" } });
  assert.deepEqual(ready.calls, [["detak", { siap: true, alasan: null, perangkat: "Pixel 7" }], ["ambil"]]);
  assert.equal(ready.result.task, TASK);

  const noSim = await run({ sehat: { siap: false, alasan: "SIM tidak siap", perangkat: "Pixel 7" } });
  assert.deepEqual(noSim.calls, [["detak", { siap: false, alasan: "SIM tidak siap", perangkat: "Pixel 7" }]]);
  assert.equal(noSim.result.task, null);

  const blocked = await run({ sehat: { siap: true, alasan: null, perangkat: "Pixel 7" }, audio: false });
  assert.deepEqual(blocked.calls, [["detak", { siap: false, alasan: AUDIO_BLOCKED, perangkat: "Pixel 7" }]]);

  const helperDown = await run({ sehat: new Error("fetch failed") });
  assert.deepEqual(helperDown.calls, [["detak", { siap: false, alasan: "Phone helper tidak menjawab", perangkat: null }]]);
});

test("stationTick survives a backend that is down", async () => {
  const errors = [];
  const result = await stationTick({
    line: { kesehatan: async () => ({ siap: true, alasan: null, perangkat: "Pixel 7" }) },
    api: { detak: async () => { throw new Error("detak gagal"); }, ambil: async () => { throw new Error("ambil gagal"); } },
    onError: (error) => errors.push(error.message),
  });

  assert.equal(result.task, null);
  assert.deepEqual(errors, ["detak gagal", "ambil gagal"]);
});

// ---- automatic operator: fake helper, fake session, fake timers ----

function stationRig(t, { status = ["offhook"], playbackMs = 0 } = {}) {
  t.mock.timers.enable({ apis: ["setTimeout", "setInterval", "Date"] });
  const lineCalls = [];
  const states = [...status];
  const line = {
    panggil: async (nomor) => { lineCalls.push(["panggil", nomor]); },
    tutup: async () => { lineCalls.push(["tutup"]); },
    status: async () => {
      const state = states.length > 1 ? states.shift() : states[0];
      return typeof state === "string" ? { panggilan: state } : state;
    },
  };
  const rig = { line, lineCalls, states, logs: [], phases: [], stops: [], options: null, opened: 0, nudges: [], released: 0, playbackMs };
  const operator = createStationOperator({
    line,
    onLog: (entry) => rig.logs.push(entry),
    onPhase: (phase) => rig.phases.push(phase),
    startSession: (options) => {
      rig.options = options;
      return {
        playbackRemainingMs: () => rig.playbackMs,
        openFirst: () => { rig.opened += 1; options.onAnswer(); return true; },
        nudge: (text) => { rig.nudges.push(text); return true; },
        releaseInput: () => { rig.released += 1; },
        stop: async (reason) => {
          if (rig.stops.length) return;
          rig.stops.push(reason);
          options.onComplete({ transkrip: [{ detik: 0, pembicara: "penerima", teks: "Halo?" }], recording: "rekaman", durasi: 7 });
        },
      };
    },
  });
  const hooks = { answered: 0, turns: [] };
  rig.operator = operator;
  rig.result = operator.converse(SERVER_TASK, {
    onAnswered: async () => { hooks.answered += 1; },
    onTurn: (turn) => hooks.turns.push(turn),
  });
  rig.hooks = hooks;
  // Let pending promise callbacks (status polls, hang-up) settle between timer steps.
  rig.tick = async (ms) => {
    t.mock.timers.tick(ms);
    for (let i = 0; i < 5; i += 1) await new Promise((resolve) => setImmediate(resolve));
  };
  rig.say = (pembicara, teks) => { rig.options.onSpeech(pembicara); rig.options.onTranscript({ detik: 1, pembicara, teks }); };
  rig.answer = () => { rig.options.onAnswer(); rig.say("penerima", "Halo?"); };
  return rig;
}

test("station operator dials through the helper and refuses manual WhatsApp steps", async () => {
  const calls = [];
  const operator = createStationOperator({ line: { panggil: async (nomor) => calls.push(nomor), tutup: async () => {} }, startSession: () => ({}) });

  await operator.telepon(SERVER_TASK);

  assert.deepEqual(calls, [TASK.no_tujuan]);
  await assert.rejects(operator.kirimWa(TASK), /tidak didukung/);
  await assert.rejects(operator.kirimChatCadangan({}), /tidak didukung/);
});

test("station operator starts the session with the script and rejects announcements as answers", async (t) => {
  const rig = stationRig(t);

  assert.equal(rig.options.greetFirst, false);
  assert.equal(rig.options.context, SERVER_TASK.skrip);
  assert.equal(rig.options.acceptAnswer("Halo?"), true);
  assert.equal(rig.options.acceptAnswer("Nomor yang Anda tuju tidak dapat dihubungi"), false);

  rig.options.onTranscript({ detik: 6, pembicara: "penerima", teks: "Nomor yang Anda tuju tidak dapat dihubungi" });
  rig.options.onRejectedAnswer();
  const hasil = await rig.result;

  assert.equal(hasil.answered, false);
  assert.deepEqual(rig.stops, ["tidak_diangkat"]);
  assert.equal(rig.hooks.answered, 0);
  assert.ok(rig.lineCalls.filter(([name]) => name === "tutup").length >= 1);
  assert.match(rig.logs[0], /pengumuman operator/);
});

test("station operator reports no answer after 40 seconds of ringing", async (t) => {
  const rig = stationRig(t);

  await rig.tick(ANSWER_TIMEOUT_MS - 1);
  assert.deepEqual(rig.stops, []);
  await rig.tick(1);
  const hasil = await rig.result;

  assert.equal(hasil.answered, false);
  assert.deepEqual(rig.stops, ["tidak_diangkat"]);
  assert.deepEqual(rig.lineCalls.at(-1), ["tutup"]);
});

test("station operator gives up at once when the line goes idle before an answer", async (t) => {
  const rig = stationRig(t, { status: ["offhook", "offhook", "idle"] });

  await rig.tick(LINE_POLL_MS);
  await rig.tick(LINE_POLL_MS);
  assert.deepEqual(rig.stops, []);
  await rig.tick(LINE_POLL_MS);
  const hasil = await rig.result;

  assert.equal(hasil.answered, false);
  assert.deepEqual(rig.stops, ["tidak_diangkat"]);
  assert.match(rig.logs[0], /sebelum dijawab/);
});

test("station operator allows the phone a few seconds to leave idle after dialing", async (t) => {
  const rig = stationRig(t, { status: ["idle"] });

  for (let i = 0; i < 5; i += 1) await rig.tick(LINE_POLL_MS);
  assert.deepEqual(rig.stops, []);
  await rig.tick(LINE_POLL_MS);

  assert.deepEqual(rig.stops, ["tidak_diangkat"]);
  assert.equal((await rig.result).answered, false);
});

test("station operator uploads the call when the recipient hangs up", async (t) => {
  const rig = stationRig(t, { status: ["offhook", "offhook", "idle"] });

  await rig.tick(LINE_POLL_MS);
  rig.answer();
  await rig.tick(LINE_POLL_MS);
  assert.deepEqual(rig.stops, []);
  await rig.tick(LINE_POLL_MS);
  const hasil = await rig.result;

  assert.deepEqual(rig.stops, ["selesai"]);
  assert.deepEqual(hasil, { answered: true, transkrip: [{ detik: 0, pembicara: "penerima", teks: "Halo?" }], rekaman: "rekaman", durasi: 7 });
  assert.equal(rig.hooks.answered, 1);
  assert.deepEqual(rig.phases, ["menelepon", "tersambung", "selesai"]);
  assert.match(rig.logs[0], /penerima menutup telepon/);
});

test("station operator hangs up three seconds after the AI's closing line", async (t) => {
  const rig = stationRig(t);

  rig.answer();
  rig.say("ai", "Selamat siang, saya asisten otomatis BPJS Kesehatan. Selamat siang."); // opener never closes
  rig.say("penerima", "Iya.");
  for (let i = 0; i < 5; i += 1) { // 40 s of conversation: the no-answer clock stopped at the answer
    await rig.tick(8000);
    rig.say("ai", "Kira-kira berapa kali?");
    rig.say("penerima", "Tiga kali.");
  }
  rig.say("ai", "Terima kasih, sudah kami catat. Selamat siang.");
  await rig.tick(CLOSING_HANGUP_MS - 1);
  assert.deepEqual(rig.stops, []);
  await rig.tick(1);
  const hasil = await rig.result;

  assert.equal(hasil.answered, true);
  assert.deepEqual(rig.stops, ["selesai"]);
  assert.deepEqual(rig.lineCalls.filter(([name]) => name === "tutup").length >= 1, true);
  assert.match(rig.logs[0], /AI menutup panggilan/);
});

test("station operator waits for the AI's goodbye to finish playing before hanging up", async (t) => {
  const rig = stationRig(t, { playbackMs: 4000 });

  rig.answer();
  rig.say("ai", "Baik.");
  rig.say("ai", "Terima kasih. Selamat siang.");
  await rig.tick(CLOSING_HANGUP_MS + 3999);
  assert.deepEqual(rig.stops, []);
  rig.playbackMs = 0; // the goodbye has finished playing
  await rig.tick(1);

  assert.deepEqual(rig.stops, ["selesai"]);
  await rig.result;
});

test("station operator hangs up after ten silent seconds following an AI turn", async (t) => {
  const rig = stationRig(t);

  rig.answer();
  rig.say("ai", "Kira-kira berapa kali?");
  await rig.tick(SILENCE_HANGUP_MS - 1);
  rig.options.onSpeech("penerima"); // the recipient starts answering: no repeat of the question
  await rig.tick(SILENCE_HANGUP_MS - 1);
  assert.deepEqual(rig.nudges, []);

  rig.say("penerima", "Tiga kali.");
  rig.say("ai", "Baik, tiga kali.");
  await rig.tick(SILENCE_HANGUP_MS - 1);
  assert.deepEqual(rig.stops, []);
  await rig.tick(1); // first silence: the AI asks again instead of hanging up

  assert.deepEqual(rig.stops, []);
  assert.deepEqual(rig.nudges, [SILENCE_NUDGE]);
  assert.match(rig.logs[0], /AI mengulang pertanyaan/);
  await rig.tick(SILENCE_HANGUP_MS); // still silent after the repeat: end the call

  assert.deepEqual(rig.stops, ["selesai"]);
  assert.match(rig.logs[1], /hening 10 detik setelah giliran AI/);
  assert.equal((await rig.result).answered, true);
});

test("station operator hangs up when the session ends by itself and when cancelled", async (t) => {
  const rig = stationRig(t);
  rig.answer();
  rig.options.onComplete({ transkrip: [], recording: null, durasi: 150 }); // session's own time cap
  assert.equal((await rig.result).durasi, 150);
  assert.deepEqual(rig.lineCalls, [["tutup"]]);
  await rig.tick(SILENCE_HANGUP_MS * 3); // no timer fires afterwards
  assert.deepEqual(rig.stops, []);
  t.mock.timers.reset();

  const second = stationRig(t);
  second.answer();
  await second.operator.batal();
  assert.deepEqual(second.stops, ["dibatalkan"]);
  assert.ok(second.lineCalls.filter(([name]) => name === "tutup").length >= 2);
  await second.result;
});

test("station operator lets the AI open when the network says answered and the recipient is silent", async (t) => {
  const rig = stationRig(t, { status: [{ panggilan: "offhook", tersambung: false }, { panggilan: "offhook", tersambung: true }] });

  await rig.tick(LINE_POLL_MS * 2);
  await rig.tick(PICKUP_SILENCE_MS - 1);
  assert.equal(rig.opened, 0);
  await rig.tick(1);

  assert.equal(rig.opened, 1);
  assert.equal(rig.hooks.answered, 1);
  assert.match(rig.logs[0], /diangkat tanpa suara/);
  await rig.tick(ANSWER_TIMEOUT_MS); // the no-answer clock is gone once answered
  assert.deepEqual(rig.stops.filter((reason) => reason === "tidak_diangkat"), []);
  await rig.operator.batal();
  await rig.result;
});

test("station operator waits for the recipient's words when they speak right after picking up", async (t) => {
  const rig = stationRig(t, { status: [{ panggilan: "offhook", tersambung: true }] });

  await rig.tick(LINE_POLL_MS);
  rig.options.onSpeech("penerima"); // "Halo?" still streaming in
  await rig.tick(PICKUP_SILENCE_MS * 2);
  assert.equal(rig.opened, 0);
  await rig.operator.batal();
  await rig.result;
});

test("station operator never opens on a call that is only ringing", async (t) => {
  const rig = stationRig(t, { status: [{ panggilan: "offhook", tersambung: false }] });

  await rig.tick(ANSWER_TIMEOUT_MS);

  assert.equal(rig.opened, 0);
  assert.deepEqual(rig.stops, ["tidak_diangkat"]);
  assert.equal((await rig.result).answered, false);
});

test("voice session openFirst counts the call as answered and sends the opening cue once", () => {
  const sent = [];
  const answers = [];
  const session = new VedikaVoiceSession({ greetFirst: false, onAnswer: () => answers.push(1) });

  assert.equal(session.openFirst(), true);
  assert.equal(session.openWhenReady, true); // socket not ready yet: cue waits for setupComplete
  assert.deepEqual(answers, [1]);
  session.socket = { send: (raw) => sent.push(JSON.parse(raw)) };
  session.ready = true;
  session.sendOpeningCue();
  assert.equal(session.openFirst(), false);
  assert.equal(sent.length, 1);
  assert.match(sent[0].clientContent.turns[0].parts[0].text, /pembuka/);
});

test("station operator repeats the question once per silence and again after the recipient speaks", async (t) => {
  const rig = stationRig(t);
  rig.answer();
  rig.say("ai", "Apakah benar saya berbicara dengan Bapak Andi Pratama?");
  await rig.tick(SILENCE_HANGUP_MS);
  assert.equal(rig.nudges.length, 1);

  rig.say("ai", "Halo, Bapak? Apakah benar ini Bapak Andi Pratama?"); // the repeat resets the clock
  rig.say("penerima", "Iya, saya sendiri.");
  rig.say("ai", "Kira-kira berapa kali Bapak terapi?");
  await rig.tick(SILENCE_HANGUP_MS);
  assert.equal(rig.nudges.length, 2); // a new question earns a new repeat
  assert.deepEqual(rig.stops, []);
  await rig.operator.batal();
  await rig.result;
});

test("voice session nudge sends a user turn only while the socket is ready", () => {
  const sent = [];
  const session = new VedikaVoiceSession({ greetFirst: false });
  assert.equal(session.nudge("ulangi"), false);
  session.socket = { send: (raw) => sent.push(JSON.parse(raw)) };
  session.ready = true;
  assert.equal(session.nudge("ulangi"), true);
  assert.equal(sent[0].clientContent.turns[0].parts[0].text, "ulangi");
});

test("station operator holds the microphone until the network reports the call as answered", async (t) => {
  const rig = stationRig(t, { status: [
    { panggilan: "offhook", tersambung: false },
    { panggilan: "offhook", tersambung: false },
    { panggilan: "offhook", tersambung: true },
  ] });

  assert.equal(rig.options.holdInput, true);
  await rig.tick(LINE_POLL_MS * 2);
  assert.equal(rig.released, 0); // ringing: Gemini hears nothing
  await rig.tick(LINE_POLL_MS);
  assert.ok(rig.released >= 1);
  await rig.operator.batal();
  await rig.result;
});

test("station operator listens at once on a line that cannot report answering", async (t) => {
  const rig = stationRig(t, { status: [{ panggilan: "offhook", tersambung: null }] });
  await rig.tick(LINE_POLL_MS);
  assert.ok(rig.released >= 1);
  assert.equal(rig.opened, 0); // unknown is not "answered": no AI opening without the recipient
  await rig.operator.batal();
  await rig.result;
});

test("voice session drops microphone audio while input is held", () => {
  const session = new VedikaVoiceSession({ holdInput: true });
  assert.equal(session.inputHeld, true);
  session.releaseInput();
  assert.equal(session.inputHeld, false);
  assert.equal(new VedikaVoiceSession({}).inputHeld, false);
});

test("station operator counts the 40 s answer window from the first ring on a slow network", async (t) => {
  const rig = stationRig(t, { status: [
    ...Array(30).fill({ panggilan: "offhook", tersambung: false, berdering: false }),
    { panggilan: "offhook", tersambung: false, berdering: true },
  ] });

  await rig.tick(ANSWER_TIMEOUT_MS - LINE_POLL_MS); // the far end started ringing at about 30 s
  assert.deepEqual(rig.stops, []);
  await rig.tick(ANSWER_TIMEOUT_MS - 10 * LINE_POLL_MS);
  assert.deepEqual(rig.stops, []); // 70 s after dialing, still inside 40 s of ringing
  await rig.tick(15 * LINE_POLL_MS);

  assert.deepEqual(rig.stops, ["tidak_diangkat"]);
  assert.equal((await rig.result).answered, false);
});

test("station operator never asks again after the AI has said goodbye", async (t) => {
  const rig = stationRig(t, { playbackMs: 20000 });
  rig.answer();
  rig.say("ai", "Kira-kira berapa kali?");
  rig.say("penerima", "Tiga kali.");
  rig.say("ai", "Jawaban ini tidak akan memengaruhi layanan atau iuran Anda. Terima kasih atas waktunya.");
  rig.say("penerima", "Aduh."); // noise after the goodbye must not earn a repeat question
  await rig.tick(SILENCE_HANGUP_MS + 20000);
  rig.playbackMs = 0;
  await rig.tick(20000 + GOODBYE_TAIL_MS + CLOSING_HANGUP_MS);

  assert.deepEqual(rig.nudges, []);
  assert.deepEqual(rig.stops, ["selesai"]);
  assert.match(rig.logs.at(-1), /AI menutup panggilan|hening 10 detik/);
});

test("station operator does not nudge while the recipient is still talking", async (t) => {
  const rig = stationRig(t);
  rig.answer();
  rig.say("ai", "Kira-kira berapa kali?");
  for (let i = 0; i < 6; i += 1) { // a long answer whose transcript has not arrived yet
    await rig.tick(SILENCE_HANGUP_MS - 1000);
    rig.options.onVoiceActivity();
  }
  assert.deepEqual(rig.nudges, []);
  await rig.tick(SILENCE_HANGUP_MS); // then real silence
  assert.equal(rig.nudges.length, 1);
  assert.doesNotMatch(SILENCE_NUDGE, /sapa singkat/i);
  await rig.operator.batal();
  await rig.result;
});

test("voice session reports activity only for speech-level audio, at most every 250 ms", () => {
  const hits = [];
  const session = new VedikaVoiceSession({ onVoiceActivity: () => hits.push(1) });
  session.reportVoiceActivity(new Float32Array(1024).fill(VOICE_ACTIVITY_RMS / 2));
  assert.equal(hits.length, 0);
  session.reportVoiceActivity(new Float32Array(1024).fill(0.2));
  session.reportVoiceActivity(new Float32Array(1024).fill(0.2));
  assert.equal(hits.length, 1);
});

test("station operator keeps the line open while a goodbye that arrived early is still playing", async (t) => {
  const rig = stationRig(t);
  rig.answer();
  rig.say("ai", "Kira-kira berapa kali?");
  rig.say("penerima", "Lima atau enam.");
  rig.say("ai", "Baik. Jawaban ini tidak memengaruhi layanan atau iuran. Terima kasih atas waktunya.");
  rig.playbackMs = 6000; // audio of the goodbye kept streaming after its transcript was flushed
  await rig.tick(CLOSING_HANGUP_MS);
  assert.deepEqual(rig.stops, []); // not cut mid-sentence
  rig.playbackMs = 0;
  await rig.tick(6000 + GOODBYE_TAIL_MS);

  assert.deepEqual(rig.stops, ["selesai"]);
  assert.match(rig.logs.at(-1), /AI menutup panggilan/);
});

test("station operator asks the AI to respond when it stays silent after the recipient's answer", async (t) => {
  const rig = stationRig(t);
  rig.answer();
  rig.say("ai", "Apakah Bapak terapi tanggal 9 Agustus?");
  rig.say("penerima", "Lho, Minggu ya libur to mas."); // Gemini never closes this turn
  await rig.tick(SILENCE_HANGUP_MS);

  assert.deepEqual(rig.nudges, [REPLY_NUDGE]);
  assert.match(rig.logs[0], /AI diminta menanggapi jawaban/);
  rig.say("ai", "Baik. Jawaban ini tidak memengaruhi layanan atau iuran. Terima kasih atas waktunya.");
  await rig.tick(CLOSING_HANGUP_MS + GOODBYE_TAIL_MS);

  assert.deepEqual(rig.stops, ["selesai"]);
  assert.match(rig.logs.at(-1), /AI menutup panggilan/);
});

test("station operator ends a call whose AI never answers even after being asked", async (t) => {
  const rig = stationRig(t);
  rig.answer();
  rig.say("ai", "Kira-kira berapa kali?");
  rig.say("penerima", "Tiga kali.");
  await rig.tick(SILENCE_HANGUP_MS); // first: the AI is asked to respond
  assert.deepEqual(rig.nudges, [REPLY_NUDGE]);
  await rig.tick(SILENCE_HANGUP_MS); // still nothing: end the call

  assert.deepEqual(rig.stops, ["selesai"]);
  assert.match(rig.logs.at(-1), /AI tidak menanggapi jawaban/);
});

test("station operator hangs up after the goodbye phrase even when Gemini never closes the turn", async (t) => {
  const rig = stationRig(t);
  rig.answer();
  rig.say("ai", "Apakah Bapak terapi tanggal 9 Agustus?");
  rig.say("penerima", "Enggak, kan hari Minggu libur.");
  rig.options.onPartial({ pembicara: "ai", teks: "Baik. Jawaban ini tidak memengaruhi layanan atau iuran Bapak." });
  assert.deepEqual(rig.stops, []);
  rig.options.onPartial({ pembicara: "ai", teks: "Baik. Jawaban ini tidak memengaruhi layanan atau iuran Bapak. Terima kasih atas waktunya." });
  await rig.tick(CLOSING_HANGUP_MS);

  assert.deepEqual(rig.stops, ["selesai"]);
  assert.match(rig.logs.at(-1), /AI menutup panggilan/);
});

test("isGoodbyePhrase only matches the mandatory last sentence", () => {
  assert.equal(isGoodbyePhrase("Terima kasih atas waktunya."), true);
  assert.equal(isGoodbyePhrase("terima kasih atas waktu Bapak"), true);
  assert.equal(isGoodbyePhrase("Terima kasih, Pak. Kira-kira berapa kali?"), false);
});

test("voice session reports each fragment of the turn in progress", () => {
  const partial = [];
  const session = new VedikaVoiceSession({ onPartial: (turn) => partial.push(turn.teks) });
  session.appendFragment({ pembicara: "ai", teks: "Terima kasih " });
  session.appendFragment({ pembicara: "ai", teks: "atas waktunya." });
  assert.deepEqual(partial, ["Terima kasih ", "Terima kasih atas waktunya."]);
});
