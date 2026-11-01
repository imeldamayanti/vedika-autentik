import { describe, expect, mock, spyOn, test } from "bun:test";

import { ENGINE_VERSION, READER_VERSION, handle } from "../src/app.js";
import { buildPrompt, isValidAnswer, parseReadRequest } from "../src/reader.js";
import { buildVoiceInstruction, parseVoiceContext } from "../src/voice.js";
import parity from "./parity.json";

const VALID = parity.answers[0].answer;
const BACA = parity.prompts[0].request;
const SKRIP = parity.instructions[0].context;

const gemini = (text) => async () => ({
  ok: true,
  json: async () => ({ candidates: [{ content: { parts: [{ text }] } }] }),
});
const call = (path, { body, env = {}, fetchImpl, headers = {}, method } = {}) =>
  handle(
    new Request(`https://vedika-ai.test${path}`, {
      method: method ?? (body === undefined ? "GET" : "POST"),
      headers: { "Content-Type": "application/json", ...headers },
      body: body === undefined ? undefined : typeof body === "string" ? body : JSON.stringify(body),
    }),
    { GEMINI_API_KEY: "server-key", ...env },
    fetchImpl ?? (async () => { throw new Error("unexpected provider call"); }),
  );

describe("parity with the Python reference (scripts/export_worker_fixtures.py)", () => {
  test("versions", () => {
    expect(ENGINE_VERSION).toBe(parity.engine_version);
    expect(READER_VERSION).toBe(parity.reader_version);
  });

  test.each(parity.prompts.map((p, i) => [i, p]))("reader prompt %i", (_i, { request, prompt }) => {
    expect(buildPrompt(parseReadRequest(request))).toBe(prompt);
  });

  test.each(parity.instructions.map((p, i) => [i, p]))("call script %i", (_i, { context, instruction }) => {
    expect(buildVoiceInstruction(parseVoiceContext(context))).toBe(instruction);
  });

  test.each(parity.answers.map((a, i) => [i, a]))("answer validation %i", (_i, { answer, valid }) => {
    expect(isValidAnswer(answer)).toBe(valid);
  });
});

describe("GET /v1/kesehatan", () => {
  test("reports ok and reader readiness", async () => {
    const response = await call("/v1/kesehatan");
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({
      status: "ok", versi_mesin: ENGINE_VERSION, versi_pembaca: READER_VERSION, pembaca_siap: true,
    });
    expect(response.headers.get("X-Request-ID")).toBeTruthy();
  });

  test("requires X-Kunci-Layanan only when configured", async () => {
    const env = { AI_SERVICE_KEY: "secret" };
    const missing = await call("/v1/kesehatan", { env });
    expect(missing.status).toBe(401);
    expect((await missing.json()).galat.kode).toBe("kunci_salah");
    expect((await call("/v1/kesehatan", { env, headers: { "X-Kunci-Layanan": "secret" } })).status).toBe(200);
  });

  test("logs why a key was rejected without logging the key", async () => {
    const env = { AI_SERVICE_KEY: "secret" };
    const logs = [];
    const log = spyOn(console, "log").mockImplementation((line) => logs.push(JSON.parse(line)));
    try {
      await call("/v1/kesehatan", { env });
      await call("/v1/kesehatan", { env, headers: { "X-Kunci-Layanan": "wrong-value" } });
    } finally {
      log.mockRestore();
    }
    expect(logs.map((l) => l.key)).toEqual(["missing", "mismatch length 11 expected 6"]);
    expect(JSON.stringify(logs)).not.toContain("wrong-value");
  });
});

describe("POST /v1/baca (Kontrak B2)", () => {
  test("returns the flat answer with versi_pembaca and no label", async () => {
    const response = await call("/v1/baca", { body: { ...BACA, field_baru: 1 }, fetchImpl: gemini(JSON.stringify(VALID)) });
    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body).toEqual({ ...VALID, versi_pembaca: READER_VERSION });
    expect(Object.keys(body)).not.toContain("label");
  });

  test("sends the prompt, schema, and server key to Gemini", async () => {
    const fetchImpl = mock(gemini(JSON.stringify(VALID)));
    await call("/v1/baca", { body: BACA, fetchImpl, env: { GEMINI_TEXT_MODEL: "gemini-test" } });
    const [url, init] = fetchImpl.mock.calls[0];
    const sent = JSON.parse(init.body);
    expect(url).toBe("https://generativelanguage.googleapis.com/v1beta/models/gemini-test:generateContent");
    expect(init.headers["x-goog-api-key"]).toBe("server-key");
    expect(url).not.toContain("server-key");
    expect(sent.contents[0].parts[0].text).toBe(parity.prompts[0].prompt);
    expect(sent.generationConfig.responseJsonSchema.additionalProperties).toBe(false);
  });

  test("clears holiday denial when no holiday was asked", async () => {
    const body = { ...BACA, konteks: { ...BACA.konteks, tanggal_libur: [] } };
    const response = await call("/v1/baca", { body, fetchImpl: gemini(JSON.stringify(VALID)) });
    expect((await response.json()).membantah_tanggal_libur).toBeNull();
  });

  test.each([[[]], [[{ detik: 0, pembicara: "penerima", teks: "  " }]]])("empty transcript is 422 without calling Gemini", async (transkrip) => {
    const response = await call("/v1/baca", { body: { transkrip } });
    expect(response.status).toBe(422);
    expect((await response.json()).galat.kode).toBe("transkrip_kosong");
  });

  test.each([
    ["provider error", async () => ({ ok: false, status: 503 }), 502, "llm_gagal"],
    ["network error", async () => { throw new TypeError("fetch failed"); }, 502, "llm_gagal"],
    ["timeout", async () => { throw new DOMException("timed out", "TimeoutError"); }, 504, "batas_waktu"],
    ["not JSON", gemini("not-json"), 502, "llm_gagal"],
    ["schema mismatch", gemini(JSON.stringify({ ...VALID, hubungan: "tetangga" })), 502, "llm_gagal"],
  ])("%s maps to the contract error", async (_name, fetchImpl, status, kode) => {
    const response = await call("/v1/baca", { body: BACA, fetchImpl });
    expect(response.status).toBe(status);
    expect((await response.json()).galat.kode).toBe(kode);
  });

  test.each([
    ["not JSON", "{"],
    ["no transcript", { konteks: {} }],
    ["bad speaker", { transkrip: [{ detik: 0, pembicara: "agen", teks: "Halo" }] }],
    ["bad date", { ...BACA, konteks: { tanggal_libur: ["2026-02-30"] } }],
  ])("invalid request (%s) is 422 validasi", async (_name, body) => {
    const response = await call("/v1/baca", { body });
    expect(response.status).toBe(422);
    expect((await response.json()).galat.kode).toBe("validasi");
  });

  test("never logs transcript text", async () => {
    const secret = "NIK-SECRET-987654321";
    const logs = [];
    const log = spyOn(console, "log").mockImplementation((line) => logs.push(line));
    const warn = spyOn(console, "warn").mockImplementation((line) => logs.push(line));
    try {
      const body = { transkrip: [{ detik: 0, pembicara: "penerima", teks: secret }] };
      await call("/v1/baca", { body, fetchImpl: async () => ({ ok: false, status: 500 }) });
    } finally {
      log.mockRestore();
      warn.mockRestore();
    }
    expect(logs.join("\n")).not.toContain(secret);
    expect(logs.join("\n")).toContain("llm_gagal");
  });

  test("missing Gemini key is 503", async () => {
    const response = await call("/v1/baca", { body: BACA, env: { GEMINI_API_KEY: "" } });
    expect(response.status).toBe(503);
    expect((await response.json()).galat.kode).toBe("gemini_tidak_dikonfigurasi");
  });
});

describe("POST /v1/suara/token", () => {
  test("locks the call script and voice into a one-use token and never returns the key", async () => {
    const fetchImpl = mock(async () => ({ ok: true, json: async () => ({ name: "auth_tokens/one-use" }) }));
    const response = await call("/v1/suara/token", { body: { ...SKRIP, id: "x" }, fetchImpl });
    const body = await response.json();
    const sent = JSON.parse(fetchImpl.mock.calls[0][1].body);
    expect(response.status).toBe(200);
    expect(body.token).toBe("auth_tokens/one-use");
    expect(body.maks_durasi_detik).toBe(150);
    expect(body.websocket_url).toContain("BidiGenerateContentConstrained");
    expect(body.instruksi).toBe(parity.instructions[0].instruction);
    expect(JSON.stringify(body)).not.toContain("server-key");
    expect(sent.uses).toBe(1);
    expect(sent.bidiGenerateContentSetup.systemInstruction.parts[0].text).toBe(body.instruksi);
    expect(sent.bidiGenerateContentSetup.generationConfig.speechConfig.voiceConfig.prebuiltVoiceConfig.voiceName).toBe("Kore");
    expect(sent.liveConnectConstraints).toBeUndefined();
  });

  test.each([
    ["provider error", async () => ({ ok: false, status: 400 }), "penyedia_tidak_tersedia"],
    ["no token in reply", async () => ({ ok: true, json: async () => ({}) }), "respons_penyedia_tidak_valid"],
  ])("%s is 503", async (_name, fetchImpl, kode) => {
    const response = await call("/v1/suara/token", { body: SKRIP, fetchImpl });
    expect(response.status).toBe(503);
    expect((await response.json()).galat.kode).toBe(kode);
  });

  test("rejects an incomplete skrip", async () => {
    const response = await call("/v1/suara/token", { body: { nama_penerima: "Andi" } });
    expect(response.status).toBe(422);
  });
});

test("unknown paths are 404", async () => {
  expect((await call("/v1/analisis", { body: {} })).status).toBe(404);
});
