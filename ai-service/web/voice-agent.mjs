const INPUT_RATE = 16000;
const OUTPUT_RATE = 24000;

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
// Gemini Live waits for incoming speech; this text cue makes the AI open the call itself.
const OPENING_CUE = "Panggilan sudah tersambung dan penerima sudah mengangkat. Mulai sekarang dengan pembuka (langkah A), lalu akhiri giliran ini dengan pertanyaan langkah B.";
const AUDIO_EXTENSIONS = { "audio/mpeg": "mp3", "audio/mp4": "m4a", "audio/ogg": "ogg", "audio/wav": "wav" };
const audioExtension = (blob) => AUDIO_EXTENSIONS[blob.type.split(";")[0]] || "webm";

export const AUDIO_BLOCKED = "Chrome memblokir audio; jalankan lewat stasiun.sh";
export const ANSWER_TIMEOUT_MS = 40000;
export const DIAL_GRACE_MS = 5000;
export const LINE_POLL_MS = 1000;
export const CLOSING_HANGUP_MS = 3000;
export const SILENCE_HANGUP_MS = 10000;
// Sent to the model after the first silence following its question: on a phone line the answer is
// often missed, so the AI asks once more before the call is ended.
export const SILENCE_NUDGE = "Penerima belum terdengar menjawab. Sapa singkat, lalu ulangi pertanyaan terakhir. "
  + "Jangan menganggap penerima sudah menjawab atau membenarkan.";
// After the network reports the call as answered, how long the recipient may stay silent before
// the AI opens the conversation itself.
export const PICKUP_SILENCE_MS = 3000;

const normalize = (teks) => String(teks || "").toLowerCase().replace(/[^\p{L}\p{N}\s]/gu, " ").replace(/\s+/g, " ").trim();
const ANNOUNCEMENTS = [
  "nomor yang anda tuju", "tidak dapat dihubungi", "tidak aktif", "sedang sibuk", "di luar jangkauan", "berada di luar",
  "kotak suara", "mailbox", "silakan tinggalkan pesan", "silakan coba", "the number you", "is not active", "is busy",
  "cannot be reached",
];

// A carrier recording ("Nomor yang Anda tuju…") is speech on the line but not an answer.
export const isOperatorAnnouncement = (teks) => {
  const text = normalize(teks);
  return ANNOUNCEMENTS.some((phrase) => text.includes(phrase));
};

// The AI's goodbye: a time-of-day farewell at the end of the turn, "sudah kami catat", or the script's
// closing promise that the answer does not affect service or dues (step F). A question is never one.
export const isClosingLine = (teks) => {
  if (String(teks || "").trim().endsWith("?")) return false;
  const text = normalize(teks);
  return text.includes("sudah kami catat") || text.includes("tidak memengaruhi layanan")
    || /selamat (pagi|siang|sore|malam)/.test(text.slice(-60));
};

// The officer cancelled or the backend released the call: nothing more may be reported for it.
export const isCallGone = (error) => error?.status === 404
  || (error?.status === 409 && ["urutan_salah", "bukan_berlangsung"].includes(error.kode));

export const pickDevice = (devices, kind, hint) => (hint
  ? devices.find((device) => device.kind === kind && device.label.includes(hint)) || null
  : null);

export function createAgentApi({ baseUrl, agentKey, fetchImpl = fetch }) {
  const send = async (path, body) => {
    const isForm = body instanceof FormData;
    const headers = { "X-Kunci-Agen": agentKey };
    if (body !== undefined && !isForm) headers["Content-Type"] = "application/json";
    const response = await fetchImpl(`${baseUrl.replace(/\/$/, "")}/api/v1${path}`, {
      method: "POST",
      headers,
      body: body === undefined || isForm ? body : JSON.stringify(body),
    });
    if (response.status === 204) return null;
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      throw Object.assign(new Error(payload?.galat?.pesan || `API ${response.status}`), {
        status: response.status,
        kode: payload?.galat?.kode,
      });
    }
    return payload;
  };
  const call = (id) => `/panggilan/${encodeURIComponent(id)}`;
  return {
    ambil: () => send("/agen/ambil"),
    detak: (keadaan) => send("/agen/detak", keadaan),
    lapor: (id, laporan) => send(`${call(id)}/status`, { laporan, waktu: new Date().toISOString() }),
    kirimTranskrip: (id, baris) => send(`${call(id)}/transkrip`, { baris }),
    kirimHasil: (id, { transkrip, rekaman, durasi }) => {
      const form = new FormData();
      if (rekaman) form.append("rekaman", rekaman, `${id}.${audioExtension(rekaman)}`);
      form.append("transkrip", JSON.stringify(transkrip));
      form.append("durasi", String(durasi));
      return send(`${call(id)}/hasil`, form);
    },
  };
}

export async function waitForTask(api, { sleep = delay, isRunning = () => true, onError } = {}) {
  while (isRunning()) {
    try {
      const task = await api.ambil();
      if (task) return task;
    } catch (error) {
      onError?.(error);
    }
    await sleep(3000);
  }
  return null;
}

export async function reportWhenAllowed(api, id, laporan, { sleep = delay } = {}) {
  for (;;) {
    try {
      return await api.lapor(id, laporan);
    } catch (error) {
      if (error.kode !== "jeda_belum_lewat") throw error;
      await sleep(1000);
    }
  }
}

// Runs one Kontrak B1 task. The backend decides delays, retries, and labels; the agent only reports.
export async function runTask({ api, task, operator, converse, sleep = delay, onError, onLog }) {
  const cancelled = { status: "dibatalkan" };
  let halting = null;
  const lost = (error) => {
    if (!isCallGone(error)) return false;
    if (!halting) {
      onLog?.(`${task.id}: dibatalkan petugas atau dilepas backend; panggilan dihentikan`);
      halting = Promise.resolve().then(() => operator.batal?.()).catch(() => {});
    }
    return true;
  };
  try {
    if (!task.wa.dikirim_server && !task.wa.lewati) {
      await operator.kirimWa(task);
      await api.lapor(task.id, "wa_terkirim");
    }
    // The backend holds "menelepon" until the WA delay has passed, so report first and dial after.
    await reportWhenAllowed(api, task.id, "menelepon", { sleep });
    let dialed = true;
    try {
      await operator.telepon(task);
    } catch (error) {
      dialed = false;
      onError?.(error);
    }
    // Lines spoken before the answer wait, because the backend only accepts transcript once
    // "tersambung"; for a no-answer they are never sent.
    let answered = null;
    let sent = Promise.resolve();
    const early = [];
    const send = (baris) => {
      sent = sent
        .then(() => api.kirimTranskrip(task.id, [baris]))
        .catch((error) => { if (!lost(error)) onError?.(error); });
    };
    const hasil = dialed ? await converse(task, {
      onAnswered: () => {
        answered = api.lapor(task.id, "tersambung")
          .then(() => api.lapor(task.id, "merekam"))
          .catch((error) => { if (!lost(error)) throw error; });
        sent = answered;
        early.splice(0).forEach(send);
        return answered;
      },
      onTurn: (baris) => (answered ? send(baris) : early.push(baris)),
    }) : { answered: false };
    if (!hasil.answered && !halting) {
      const status = await api.lapor(task.id, "tidak_diangkat");
      if (status.chat_cadangan && !status.chat_cadangan.dikirim_server) {
        await operator.kirimChatCadangan(status.chat_cadangan);
        await api.lapor(task.id, "chat_cadangan_terkirim");
      }
      return status;
    }
    await sent;
    if (halting) {
      await halting;
      return cancelled;
    }
    return await api.kirimHasil(task.id, hasil);
  } catch (error) {
    if (!lost(error)) throw error;
    await halting;
    return cancelled;
  }
}

export function createLineApi({ fetchImpl = (...args) => fetch(...args), baseUrl = "" } = {}) {
  const send = async (method, path, body) => {
    const response = await fetchImpl(`${baseUrl}/v1/saluran${path}`, {
      method,
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      throw Object.assign(new Error(payload?.galat?.pesan || `saluran ${response.status}`), {
        status: response.status,
        kode: payload?.galat?.kode,
      });
    }
    return payload;
  };
  return {
    konfigurasi: () => send("GET", "/konfigurasi"),
    kesehatan: () => send("GET", "/kesehatan"),
    status: () => send("GET", "/status"),
    panggil: (nomor) => send("POST", "/panggil", { nomor }),
    tutup: () => send("POST", "/tutup"),
  };
}

// One loop turn of the station: phone health, heartbeat to the backend, then claim a task if ready.
export async function stationTick({ line, api, audioReady = () => true, onError }) {
  const sehat = await line.kesehatan().catch((error) => {
    onError?.(error);
    return { siap: false, alasan: "Phone helper tidak menjawab", perangkat: null, sim: null };
  });
  const blocked = !audioReady();
  const siap = Boolean(sehat.siap) && !blocked;
  await api.detak({ siap, alasan: blocked ? AUDIO_BLOCKED : sehat.alasan ?? null, perangkat: sehat.perangkat ?? null })
    .catch((error) => onError?.(error));
  let task = null;
  if (siap) task = await api.ambil().catch((error) => { onError?.(error); return null; });
  return { sehat, siap, blocked, task };
}

// The automatic operator: dials through the Phone helper, decides answered / not answered / when
// to hang up, and always releases the line. `startSession(options)` returns a started-or-starting
// VedikaVoiceSession-like object with stop(reason) and playbackRemainingMs().
export function createStationOperator({ line, startSession, onPhase, onLog, onError }) {
  let current = null;
  const hangUp = () => line.tutup().catch((error) => onError?.(error));
  const unsupported = async () => { throw new Error("tidak didukung"); };

  const converse = (task, { onAnswered, onTurn }) => new Promise((resolve) => {
    const dialedAt = Date.now();
    let answered = false;
    let ended = false;
    let seenOffhook = false;
    let aiTurns = 0;
    let closing = null;
    let silence = null;
    let pickup = null;
    let heardRecipient = false;
    let nudged = false;
    let session = null;
    const clearTimers = () => {
      clearTimeout(noAnswer);
      clearTimeout(closing);
      clearTimeout(silence);
      clearTimeout(pickup);
      clearInterval(poll);
    };
    const end = (reason, note) => {
      if (ended) return;
      ended = true;
      clearTimers();
      if (note) onLog?.(`${task.id}: ${note}`);
      hangUp();
      Promise.resolve(session?.stop(reason)).catch((error) => onError?.(error));
    };
    const noAnswerAfter = () => setTimeout(() => end("tidak_diangkat", "tidak ada jawaban dalam 40 detik"), ANSWER_TIMEOUT_MS);
    let noAnswer = noAnswerAfter();
    let ringingSeen = false;
    const poll = setInterval(async () => {
      const reply = await line.status().catch(() => null);
      const state = reply?.panggilan;
      if (ended || !state) return;
      if (state !== "idle") {
        seenOffhook = true;
        // Some networks take 30 s before the recipient's phone rings; the 40 s answer window counts
        // from the first ring, not from dialing.
        if (reply.berdering && !ringingSeen && !answered) {
          ringingSeen = true;
          clearTimeout(noAnswer);
          noAnswer = noAnswerAfter();
        }
        // tersambung true: answered. null/absent: this line cannot tell (fake phone), so listen now.
        if (reply.tersambung !== false) session?.releaseInput?.();
        // Carrier announcements play before the call is answered, so a network "answered" here is
        // a person (or voicemail), never the operator.
        if (reply.tersambung && !answered && !heardRecipient && !pickup) {
          pickup = setTimeout(() => {
            if (!answered && !ended && !heardRecipient && session?.openFirst?.()) {
              onLog?.(`${task.id}: diangkat tanpa suara; AI membuka lebih dulu`);
            }
          }, PICKUP_SILENCE_MS);
        }
        return;
      }
      if (answered) end("selesai", "penerima menutup telepon");
      else if (seenOffhook || Date.now() - dialedAt > DIAL_GRACE_MS) end("tidak_diangkat", "panggilan berakhir sebelum dijawab");
    }, LINE_POLL_MS);
    const afterPlayback = (ms) => ms + (session?.playbackRemainingMs?.() || 0);
    // First silence after an AI turn: the AI asks again. Second silence in a row: end the call.
    const onSilence = () => {
      if (ended) return;
      if (!nudged && session?.nudge?.(SILENCE_NUDGE)) {
        nudged = true;
        onLog?.(`${task.id}: hening 10 detik; AI mengulang pertanyaan`);
        silence = setTimeout(onSilence, afterPlayback(SILENCE_HANGUP_MS));
        return;
      }
      end("selesai", "hening 10 detik setelah giliran AI");
    };

    current = { stop: (reason) => end(reason) };
    onPhase?.("menelepon");
    session = startSession({
      greetFirst: false,
      holdInput: true,
      context: task.skrip,
      acceptAnswer: (teks) => !isOperatorAnnouncement(teks),
      onRejectedAnswer: () => end("tidak_diangkat", "pengumuman operator, bukan jawaban"),
      onAnswer: () => {
        answered = true;
        clearTimeout(noAnswer);
        onPhase?.("tersambung");
        Promise.resolve(onAnswered()).catch((error) => onError?.(error));
      },
      onSpeech: (pembicara) => {
        clearTimeout(silence);
        if (pembicara === "penerima") { heardRecipient = true; nudged = false; clearTimeout(pickup); }
      },
      onTranscript: (turn) => {
        onTurn(turn);
        if (!answered || ended || turn.pembicara !== "ai") return;
        aiTurns += 1;
        clearTimeout(silence);
        silence = setTimeout(onSilence, afterPlayback(SILENCE_HANGUP_MS));
        // The opener can start with "Selamat siang"; only a later turn can close the call.
        if (aiTurns > 1 && isClosingLine(turn.teks) && !closing) {
          closing = setTimeout(() => end("selesai", "AI menutup panggilan"), afterPlayback(CLOSING_HANGUP_MS));
        }
      },
      onError,
      onComplete: ({ transkrip, recording, durasi }) => {
        ended = true;
        clearTimers();
        current = null;
        onPhase?.("selesai");
        hangUp().finally(() => resolve({ answered, transkrip, rekaman: recording, durasi }));
      },
    });
  });

  return {
    kirimWa: unsupported,
    kirimChatCadangan: unsupported,
    telepon: (task) => line.panggil(task.no_tujuan),
    batal: async () => {
      current?.stop("dibatalkan");
      await hangUp();
    },
    converse,
  };
}

export function float32ToPcm16(samples) {
  const bytes = new Uint8Array(samples.length * 2);
  const view = new DataView(bytes.buffer);
  for (let index = 0; index < samples.length; index += 1) {
    const clamped = Math.max(-1, Math.min(1, samples[index]));
    const value = clamped < 0 ? clamped * 32768 : clamped * 32767;
    view.setInt16(index * 2, Math.trunc(value), true);
  }
  return bytes;
}

function resample(samples, fromRate, toRate) {
  if (fromRate === toRate) return samples;
  const outputLength = Math.max(1, Math.round(samples.length * toRate / fromRate));
  const output = new Float32Array(outputLength);
  const ratio = fromRate / toRate;
  for (let index = 0; index < outputLength; index += 1) {
    const position = index * ratio;
    const left = Math.floor(position);
    const right = Math.min(left + 1, samples.length - 1);
    const fraction = position - left;
    output[index] = samples[left] * (1 - fraction) + samples[right] * fraction;
  }
  return output;
}

function bytesToBase64(bytes) {
  let binary = "";
  for (let index = 0; index < bytes.length; index += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(index, index + 0x8000));
  }
  return btoa(binary);
}

function base64ToBytes(value) {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}

export function buildSetupMessage(model, instruction) {
  return {
    setup: {
      model: `models/${model.replace(/^models\//, "")}`,
      generationConfig: {
        responseModalities: ["AUDIO"],
        speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: "Kore" } }, languageCode: "id-ID" },
      },
      inputAudioTranscription: { languageCodes: ["id-ID"] },
      realtimeInputConfig: {
        automaticActivityDetection: {
          startOfSpeechSensitivity: "START_SENSITIVITY_HIGH",
          endOfSpeechSensitivity: "END_SENSITIVITY_LOW",
          prefixPaddingMs: 200,
          silenceDurationMs: 800,
        },
      },
      outputAudioTranscription: {},
      systemInstruction: { parts: [{ text: instruction }] },
    },
  };
}

async function decodeServerFrame(raw) {
  if (typeof raw === "string") return raw;
  if (typeof Blob !== "undefined" && raw instanceof Blob) {
    return new TextDecoder().decode(await raw.arrayBuffer());
  }
  if (raw instanceof ArrayBuffer) return new TextDecoder().decode(raw);
  if (ArrayBuffer.isView(raw)) {
    return new TextDecoder().decode(
      raw.buffer.slice(raw.byteOffset, raw.byteOffset + raw.byteLength),
    );
  }
  return raw;
}

export async function parseServerMessage(raw) {
  const decoded = await decodeServerFrame(raw);
  const message = typeof decoded === "string" ? JSON.parse(decoded) : decoded;
  const content = message.serverContent || {};
  const audioChunks = [];
  for (const part of content.modelTurn?.parts || []) {
    if (part.inlineData?.data) audioChunks.push(base64ToBytes(part.inlineData.data));
  }
  const turns = [];
  if (content.inputTranscription?.text?.trim()) {
    turns.push({ pembicara: "penerima", teks: content.inputTranscription.text });
  }
  if (content.outputTranscription?.text?.trim()) {
    turns.push({ pembicara: "ai", teks: content.outputTranscription.text });
  }
  return {
    setupComplete: Boolean(message.setupComplete),
    audioChunks,
    turns,
    interrupted: Boolean(content.interrupted),
    turnComplete: Boolean(content.turnComplete),
  };
}

export class LiveEventReducer {
  constructor() {
    this.status = "menelepon";
  }

  reduce(event) {
    let clearPlayback = false;
    if (event.setupComplete) this.status = "tersambung";
    if (event.turns?.some((turn) => turn.pembicara === "penerima")) this.status = "merekam";
    if (event.interrupted) clearPlayback = true;
    if (event.turnComplete) this.status = "membaca_jawaban";
    return { status: this.status, clearPlayback };
  }

  close() {
    this.status = "selesai";
    return { status: this.status, clearPlayback: true };
  }
}

export class VedikaVoiceSession {
  constructor(options) {
    this.options = options;
    this.fetchImpl = options.fetchImpl || ((...args) => fetch(...args));
    this.WebSocketImpl = options.WebSocketImpl || WebSocket;
    this.AudioContextImpl = options.AudioContextImpl || globalThis.AudioContext;
    this.AudioImpl = options.AudioImpl || globalThis.Audio;
    this.MediaRecorderImpl = options.MediaRecorderImpl || globalThis.MediaRecorder;
    this.mediaDevices = options.mediaDevices || navigator.mediaDevices;
    this.reducer = new LiveEventReducer();
    this.transkrip = [];
    this.pendingTurn = null;
    this.recording = null;
    this.recordedChunks = [];
    this.scheduledSources = new Set();
    this.startedAt = 0;
    this.endedAt = 0;
    this.nextPlayTime = 0;
    this.stopping = false;
    this.completed = false;
    this.started = false;
    this.stopReason = null;
    this.cleanupPromise = null;
    this.messageQueue = Promise.resolve();
    this.stoppedTracks = new Set();
    // Station calls hold the microphone until the phone network reports the call as answered, so
    // ringback, room noise or a carrier recording never reach Gemini as the recipient's words.
    this.inputHeld = Boolean(options.holdInput);
  }

  releaseInput() {
    this.inputHeld = false;
  }

  emitStatus(status) {
    this.options.onStatus?.(status);
  }

  async start() {
    if (this.started || this.stopping) throw new Error("session already started");
    this.started = true;
    this.startedAt = performance.now();
    try {
      this.emitStatus("menelepon");
      const tokenResponse = await this.fetchImpl(
        this.options.tokenEndpoint || "/v1/suara/token",
        {
          method: "POST",
          headers: { "Content-Type": "application/json", ...(this.options.headers || {}) },
          body: JSON.stringify(this.options.context),
        },
      );
      this.ensureActive();
      if (!tokenResponse.ok) throw new Error(`token endpoint ${tokenResponse.status}`);
      const credentials = await tokenResponse.json();
      this.ensureActive();

      // Chrome keeps an AudioContext suspended (silent both ways) unless a user gesture or the
      // launcher's --autoplay-policy=no-user-gesture-required allows it. Each call gets a fresh one.
      this.audioContext = this.options.audioContext || new this.AudioContextImpl();
      if (this.audioContext.state === "suspended") {
        await Promise.race([this.audioContext.resume?.(), delay(1000)]);
        if (this.audioContext.state !== "running") throw new Error(AUDIO_BLOCKED);
      }
      // Default (cable): the input is the call line, so Chrome's processing stays off. Speaker
      // mode passes lineConstraints with echo cancellation on, or the AI would hear itself.
      const line = {
        channelCount: 1,
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: false,
        ...(this.options.lineConstraints || {}),
      };
      const inputStream = await this.mediaDevices.getUserMedia({
        audio: this.options.inputDeviceId
          ? { deviceId: { exact: this.options.inputDeviceId }, ...line }
          : line,
      });
      if (this.stopping) {
        this.stopStream(inputStream);
        throw new Error("session stopped");
      }
      this.inputStream = inputStream;
      this.inputSource = this.audioContext.createMediaStreamSource(this.inputStream);
      this.recordDestination = this.audioContext.createMediaStreamDestination();
      this.playDestination = this.audioContext.createMediaStreamDestination();
      this.inputSource.connect(this.recordDestination);

      this.outputElement = new this.AudioImpl();
      this.outputElement.autoplay = true;
      this.outputElement.srcObject = this.playDestination.stream;
      if (this.options.outputDeviceId && this.outputElement.setSinkId) {
        await this.outputElement.setSinkId(this.options.outputDeviceId);
        this.ensureActive();
      }
      await this.outputElement.play();
      this.ensureActive();

      this.recorder = new this.MediaRecorderImpl(this.recordDestination.stream);
      this.recorder.addEventListener("dataavailable", (event) => {
        if (event.data?.size) this.recordedChunks.push(event.data);
      });
      this.recorder.start(1000);

      this.socket = new this.WebSocketImpl(
        `${credentials.websocket_url}?access_token=${encodeURIComponent(credentials.token)}`,
      );
      this.socket.binaryType = "arraybuffer";
      this.socket.addEventListener("open", () => {
        if (this.stopping) return;
        this.socket.send(
          JSON.stringify(buildSetupMessage(credentials.model, credentials.instruksi)),
        );
      });
      this.socket.addEventListener("message", (event) => this.enqueueMessage(event.data));
      this.socket.addEventListener("error", () => {
        if (this.stopping) return;
        const error = new Error("live socket error");
        this.options.onError?.(error);
        this.stop("galat_koneksi").catch((stopError) => this.options.onError?.(stopError));
      });
      this.socket.addEventListener("close", () => {
        this.handleSocketClose().catch((error) => this.options.onError?.(error));
      });

      this.processor = this.audioContext.createScriptProcessor(2048, 1, 1);
      this.silentGain = this.audioContext.createGain();
      this.silentGain.gain.value = 0;
      this.processor.onaudioprocess = (event) => {
        if (
          this.stopping
          || !this.ready
          || this.inputHeld
          || this.socket?.readyState !== this.WebSocketImpl.OPEN
        ) return;
        const downsampled = resample(
          event.inputBuffer.getChannelData(0),
          this.audioContext.sampleRate,
          INPUT_RATE,
        );
        const pcm = float32ToPcm16(downsampled);
        this.socket.send(JSON.stringify({
          realtimeInput: {
            audio: { data: bytesToBase64(pcm), mimeType: `audio/pcm;rate=${INPUT_RATE}` },
          },
        }));
      };
      this.inputSource.connect(this.processor);
      this.processor.connect(this.silentGain);
      this.silentGain.connect(this.audioContext.destination);

      this.timeoutId = setTimeout(
        () => this.stop("batas_waktu").catch((error) => this.options.onError?.(error)),
        credentials.maks_durasi_detik * 1000,
      );
      return this;
    } catch (error) {
      if (!this.stopping) this.options.onError?.(error);
      await this.stop(this.stopping ? this.stopReason || "dibatalkan" : "gagal_memulai");
      throw error;
    }
  }

  ensureActive() {
    if (this.stopping) throw new Error("session stopped");
  }

  enqueueMessage(raw) {
    this.messageQueue = this.messageQueue
      .then(() => this.handleMessage(raw))
      .catch((error) => {
        if (this.stopping) return undefined;
        this.options.onError?.(error);
        return this.stop("pesan_tidak_valid");
      });
    return this.messageQueue;
  }

  async handleMessage(raw) {
    if (this.stopping) return;
    const event = await parseServerMessage(raw);
    if (this.stopping) return;
    const action = this.reducer.reduce(event);
    if (event.setupComplete && !this.ready && (this.options.greetFirst !== false || this.openWhenReady)) {
      this.sendOpeningCue();
    }
    this.ready ||= event.setupComplete;
    if (action.clearPlayback) this.clearPlayback();
    this.emitStatus(action.status);
    for (const turn of event.turns) this.appendFragment(turn);
    if (event.turnComplete || event.interrupted) this.flushTurn();
    for (const chunk of event.audioChunks) this.playPcm(chunk);
  }

  // Ask the model to speak again (for example after the recipient stayed silent).
  nudge(text) {
    if (this.stopping || !this.ready || !this.socket) return false;
    this.socket.send(JSON.stringify({
      clientContent: { turns: [{ role: "user", parts: [{ text }] }], turnComplete: true },
    }));
    return true;
  }

  sendOpeningCue() {
    this.openWhenReady = false;
    this.socket?.send(JSON.stringify({
      clientContent: { turns: [{ role: "user", parts: [{ text: OPENING_CUE }] }], turnComplete: true },
    }));
  }

  // The phone network says the call is up but the recipient has not said anything: many people
  // answer an unknown number and wait. Count the call as answered and let the AI open first.
  openFirst() {
    if (this.answered || this.stopping) return false;
    this.answered = true;
    this.startedAt = performance.now();
    this.options.onAnswer?.();
    if (this.ready) this.sendOpeningCue();
    else this.openWhenReady = true;
    return true;
  }

  // Gemini streams transcription in fragments; the backend wants one line per speaking turn.
  appendFragment({ pembicara, teks }) {
    if (this.pendingTurn?.pembicara !== pembicara) this.flushTurn();
    this.options.onSpeech?.(pembicara);
    if (this.pendingTurn) {
      this.pendingTurn.teks += teks;
      return;
    }
    const detik = Math.max(0, Math.floor((performance.now() - this.startedAt) / 1000));
    this.pendingTurn = { detik, pembicara, teks };
  }

  flushTurn() {
    const turn = this.pendingTurn;
    this.pendingTurn = null;
    if (!turn) return;
    turn.teks = turn.teks.trim().replace(/\s+/g, " ");
    // The call counts as answered when a completed recipient turn is accepted (a carrier
    // announcement is not); the clock restarts there so "detik" counts from the connection.
    if (turn.pembicara === "penerima" && !this.answered) {
      if ((this.options.acceptAnswer || (() => true))(turn.teks)) {
        this.answered = true;
        this.startedAt = performance.now();
        turn.detik = 0;
        this.options.onAnswer?.();
      } else {
        this.options.onRejectedAnswer?.(turn);
      }
    }
    this.transkrip.push(turn);
    this.options.onTranscript?.(turn, [...this.transkrip]);
  }

  playPcm(bytes) {
    const sampleCount = Math.floor(bytes.byteLength / 2);
    const buffer = this.audioContext.createBuffer(1, sampleCount, OUTPUT_RATE);
    const output = buffer.getChannelData(0);
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    for (let index = 0; index < sampleCount; index += 1) {
      output[index] = view.getInt16(index * 2, true) / 32768;
    }
    const source = this.audioContext.createBufferSource();
    source.buffer = buffer;
    source.connect(this.playDestination);
    source.connect(this.recordDestination);
    source.addEventListener("ended", () => this.scheduledSources.delete(source));
    const startAt = Math.max(this.audioContext.currentTime, this.nextPlayTime);
    source.start(startAt);
    this.nextPlayTime = startAt + buffer.duration;
    this.scheduledSources.add(source);
  }

  playbackRemainingMs() {
    if (!this.audioContext) return 0;
    return Math.max(0, (this.nextPlayTime - this.audioContext.currentTime) * 1000) || 0;
  }

  clearPlayback() {
    for (const source of this.scheduledSources) {
      try { source.stop(); } catch (_) { /* source already ended */ }
    }
    this.scheduledSources.clear();
    if (this.audioContext) this.nextPlayTime = this.audioContext.currentTime;
  }

  async stop(reason = "selesai") {
    this.stopping = true;
    this.stopReason ||= reason;
    if (this.cleanupPromise) return this.cleanupPromise;
    this.cleanupPromise = this.cleanup(this.stopReason);
    try {
      return await this.cleanupPromise;
    } finally {
      this.cleanupPromise = null;
    }
  }

  async handleSocketClose() {
    if (this.stopping) return this.result(this.stopReason || "selesai");
    return this.stop("koneksi_terputus");
  }

  stopStream(stream) {
    for (const track of stream?.getTracks() || []) {
      if (this.stoppedTracks.has(track)) continue;
      this.stoppedTracks.add(track);
      track.stop();
    }
  }

  async cleanup(reason) {
    this.endedAt ||= performance.now();
    this.flushTurn();
    clearTimeout(this.timeoutId);
    this.timeoutId = null;
    this.ready = false;
    this.clearPlayback();

    const socket = this.socket;
    this.socket = null;
    if (socket?.readyState === this.WebSocketImpl.OPEN) {
      socket.send(JSON.stringify({ realtimeInput: { audioStreamEnd: true } }));
    }
    if (
      socket?.readyState === this.WebSocketImpl.CONNECTING
      || socket?.readyState === this.WebSocketImpl.OPEN
    ) {
      socket.close(1000, reason);
    }
    if (this.processor) this.processor.onaudioprocess = null;
    this.processor?.disconnect();
    this.processor = null;
    this.inputSource?.disconnect();
    this.inputSource = null;
    this.silentGain?.disconnect();
    this.silentGain = null;

    if (this.recorder && ["recording", "paused"].includes(this.recorder.state)) {
      await new Promise((resolve) => {
        this.recorder.addEventListener("stop", resolve, { once: true });
        this.recorder.stop();
      });
      this.recording = new Blob(this.recordedChunks, { type: this.recorder.mimeType || "audio/webm" });
    }
    this.recorder = null;

    this.stopStream(this.inputStream);
    this.stopStream(this.recordDestination?.stream);
    this.stopStream(this.playDestination?.stream);
    this.inputStream = null;

    this.outputElement?.pause();
    if (this.outputElement) this.outputElement.srcObject = null;
    this.outputElement = null;
    const audioContext = this.audioContext;
    this.audioContext = null;
    if (audioContext?.state !== "closed") await audioContext?.close();
    this.recordDestination = null;
    this.playDestination = null;

    const result = this.result(reason);
    if (!this.completed) {
      this.completed = true;
      const action = this.reducer.close();
      this.emitStatus(action.status);
      this.options.onComplete?.(result);
    }
    return result;
  }

  result(reason = "selesai") {
    const end = this.endedAt || performance.now();
    const durasi = this.startedAt ? Math.max(0, Math.round((end - this.startedAt) / 1000)) : 0;
    return { reason, transkrip: [...this.transkrip], recording: this.recording, durasi };
  }
}

