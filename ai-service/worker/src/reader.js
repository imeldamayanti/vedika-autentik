// Kontrak B2 answer reader, ported from ai-service/src/vedika_ai/answer_reader.py.
// Parity with the Python reference is enforced by test/parity.json.
import schema from "./answer-schema.json";
import { fail, isText, length } from "./errors.js";

const READ_TIMEOUT_MS = 25_000; // The backend waits 30 s per /v1/baca attempt.
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
const STATUS = ["terjawab", "tidak_terhubung", "menolak"];
const RECIPIENT = ["peserta", "keluarga"];
const RELATIONSHIP = ["anak", "orang tua", "pasangan"];
const CONFIDENCE = ["tinggi", "rendah"];
const DANGER = ["tanda_tangan_tanpa_layanan", "diminta_membayar", "layanan_berbeda"];

const invalid = () => fail(422, "validasi", "Permintaan tidak valid.");
const isDate = (value) =>
  typeof value === "string" && ISO_DATE.test(value) && !Number.isNaN(Date.parse(`${value}T00:00:00Z`))
  && new Date(`${value}T00:00:00Z`).toISOString().startsWith(value);
const isCount = (value) => typeof value === "number" && Number.isInteger(value) && value >= 0;
const optional = (value, check) => value === null || value === undefined || check(value);

export function parseReadRequest(body) {
  if (typeof body !== "object" || body === null || !Array.isArray(body.transkrip)) throw invalid();
  const transkrip = body.transkrip.map((turn) => {
    if (
      typeof turn !== "object" || turn === null
      || typeof turn.detik !== "number" || turn.detik < 0
      || !["ai", "penerima"].includes(turn.pembicara)
      || typeof turn.teks !== "string" || length(turn.teks) > 2000
    ) throw invalid();
    return { detik: turn.detik, pembicara: turn.pembicara, teks: turn.teks };
  });
  const konteks = body.konteks ?? {};
  if (
    typeof konteks !== "object"
    || !optional(konteks.sesi_ditagih, isCount)
    || !optional(konteks.tanggal_libur, (v) => Array.isArray(v) && v.every(isDate))
    || !optional(konteks.nama_pasien, (v) => typeof v === "string")
    || !optional(konteks.bulan, (v) => typeof v === "string")
    || !optional(body.id, (v) => typeof v === "string")
  ) throw invalid();
  return {
    id: body.id ?? null,
    transkrip,
    konteks: {
      sesi_ditagih: konteks.sesi_ditagih ?? null,
      tanggal_libur: konteks.tanggal_libur ?? [],
      nama_pasien: konteks.nama_pasien ?? null,
      bulan: konteks.bulan ?? null,
    },
  };
}

export function buildPrompt({ transkrip, konteks }) {
  const transcript = transkrip
    .filter((turn) => turn.teks.trim())
    .map((turn) => `${turn.pembicara}: ${turn.teks}`)
    .join("\n");
  const holidays = konteks.tanggal_libur.join(", ") || "tidak ada";
  return (
    "Ekstrak percakapan konfirmasi fisioterapi berikut ke JSON sesuai skema. "
    + "Jangan menebak. Gunakan null untuk jumlah yang tidak disebut. "
    + "Keyakinan rendah jika penerima ragu atau tidak ingat. Kutipan harus berasal dari "
    + "transkrip. Tanda bahaya hanya boleh memakai enum pada skema. "
    + "status_panggilan menolak bila penerima menolak menjawab pertanyaan konfirmasi "
    + "atau minta berhenti, tidak_terhubung bila tidak ada percakapan dengan penerima, "
    + "selain itu terjawab. "
    + "hubungan diisi anak, orang tua, atau pasangan bila penerima keluarga, selain itu null. "
    + "membantah_tanggal_libur true bila penerima menyangkal terapi pada tanggal libur, "
    + "false bila membenarkan, null bila tidak dibahas.\n\n"
    + `Pasien: ${konteks.nama_pasien || "-"}\n`
    + `Bulan layanan: ${konteks.bulan || "-"}\n`
    + `Tanggal libur yang ditanyakan: ${holidays}\n\n`
    + `TRANSKRIP:\n${transcript}`
  );
}

// Mirrors the strict Pydantic model JawabanTerstruktur.
export function isValidAnswer(answer) {
  if (typeof answer !== "object" || answer === null || Array.isArray(answer)) return false;
  const keys = Object.keys(schema.properties);
  if (Object.keys(answer).some((key) => !keys.includes(key))) return false;
  if (!keys.every((key) => key in answer)) return false;
  const a = answer;
  const nullableBool = (v) => v === null || typeof v === "boolean";
  const nullableCount = (v) => v === null || isCount(v);
  return STATUS.includes(a.status_panggilan)
    && (a.penerima === null || RECIPIENT.includes(a.penerima))
    && (a.hubungan === null || RELATIONSHIP.includes(a.hubungan))
    && nullableBool(a.hadir)
    && nullableCount(a.jumlah_min) && nullableCount(a.jumlah_maks)
    && (a.jumlah_min === null) === (a.jumlah_maks === null)
    && (a.jumlah_min === null || a.jumlah_min <= a.jumlah_maks)
    && (a.keyakinan === null || CONFIDENCE.includes(a.keyakinan))
    && Array.isArray(a.tanda_bahaya) && a.tanda_bahaya.every((flag) => DANGER.includes(flag))
    && nullableBool(a.membantah_tanggal_libur)
    && isText(a.kutipan_kunci, 0, 2000)
    && isText(a.ringkasan, 1, 500);
}

export async function readAnswer(request, { apiKey, model, fetchImpl = fetch, log = console }) {
  if (!request.transkrip.some((turn) => turn.teks.trim())) {
    throw fail(422, "transkrip_kosong", "Transkrip kosong tidak dapat dibaca.");
  }
  let raw;
  try {
    const response = await fetchImpl(
      `https://generativelanguage.googleapis.com/v1beta/models/${model.replace(/^models\//, "")}:generateContent`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", "x-goog-api-key": apiKey },
        body: JSON.stringify({
          contents: [{ role: "user", parts: [{ text: buildPrompt(request) }] }],
          generationConfig: { responseMimeType: "application/json", responseJsonSchema: schema, temperature: 0 },
        }),
        signal: AbortSignal.timeout(READ_TIMEOUT_MS),
      },
    );
    if (!response.ok) {
      log.warn(JSON.stringify({ event: "answer_extraction_failed", code: "penyedia_tidak_tersedia", status: response.status }));
      throw fail(502, "llm_gagal", "Pembaca jawaban gagal.");
    }
    raw = (await response.json())?.candidates?.[0]?.content?.parts?.[0]?.text;
  } catch (error) {
    if (error.kode) throw error;
    if (error.name === "TimeoutError" || error.name === "AbortError") {
      log.warn(JSON.stringify({ event: "answer_extraction_failed", code: "batas_waktu" }));
      throw fail(504, "batas_waktu", "Pembaca jawaban melewati batas waktu.");
    }
    log.warn(JSON.stringify({ event: "answer_extraction_failed", code: "penyedia_tidak_tersedia" }));
    throw fail(502, "llm_gagal", "Pembaca jawaban gagal.");
  }
  let answer;
  try {
    answer = JSON.parse(raw);
  } catch {
    answer = null;
  }
  if (!isValidAnswer(answer)) {
    log.warn(JSON.stringify({ event: "answer_extraction_failed", code: "ekstraksi_tidak_valid" }));
    throw fail(502, "llm_gagal", "Keluaran pembaca tidak sesuai skema.");
  }
  if (!request.konteks.tanggal_libur.length) answer.membantah_tanggal_libur = null;
  return answer;
}
