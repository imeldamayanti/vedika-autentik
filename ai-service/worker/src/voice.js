// Gemini Live call script and one-use token, ported from ai-service/src/vedika_ai/voice.py.
// Parity with the Python reference is enforced by test/parity.json.
import { fail, isText } from "./errors.js";

export const LIVE_WEBSOCKET_URL = "wss://generativelanguage.googleapis.com/ws/"
  + "google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContentConstrained";
const VOICE = "Kore";
const TOKEN_TIMEOUT_MS = 15_000;
const LIMITS = {
  nama_penerima: 120, sapaan_penerima: 20, hubungan: 40, nama_pasien: 120,
  sapaan_pasien: 20, nama_rs: 160, bulan: 40,
};

export function parseVoiceContext(body) {
  if (typeof body !== "object" || body === null) throw fail(422, "validasi", "Permintaan tidak valid.");
  const context = {};
  for (const [field, max] of Object.entries(LIMITS)) {
    if (!isText(body[field], 1, max)) throw fail(422, "validasi", "Permintaan tidak valid.");
    context[field] = body[field];
  }
  const holidays = body.tanggal_libur ?? [];
  if (!Array.isArray(holidays) || !holidays.every((day) => typeof day === "string")) {
    throw fail(422, "validasi", "Permintaan tidak valid.");
  }
  return { ...context, tanggal_libur: holidays };
}

const join = (items) => (items.length === 1 ? items[0] : `${items.slice(0, -1).join(", ")} dan ${items.at(-1)}`);

// ["16 Agustus", "17 Agustus"] -> "16 dan 17 Agustus".
function holidayText(values) {
  const parts = values.map((value) => {
    const space = value.indexOf(" ");
    return space === -1 ? [value, ""] : [value.slice(0, space), value.slice(space + 1)];
  });
  const months = new Set(parts.map(([, month]) => month));
  if (months.size === 1 && parts.every(([, month]) => month)) {
    return `${join(parts.map(([day]) => day))} ${parts[0][1]}`;
  }
  return join(values);
}

export function buildVoiceInstruction(c) {
  const holidayRule = c.tanggal_libur.length
    ? "E. Tanggal libur: tanyakan apakah pasien terapi pada tanggal libur yang perlu "
      + `ditanyakan: ${holidayText(c.tanggal_libur)}.`
    : "E. Jangan bertanya tentang tanggal libur karena tidak ada tanggal aktif.";
  const recipientRule = c.hubungan === "peserta"
    ? `Sapa ${c.sapaan_penerima} ${c.nama_penerima}.`
    : `Penerima adalah keluarga (${c.hubungan}) pasien. Sapa sebagai keluarga `
      + `${c.sapaan_pasien} ${c.nama_pasien.trim().split(/\s+/)[0]}.`;
  return `Peran: Kamu asisten otomatis BPJS Kesehatan yang menelepon untuk konfirmasi
singkat layanan fisioterapi.
Gunakan Bahasa Indonesia sopan, sederhana, dan santai.

Data panggilan:
- Penerima: ${c.sapaan_penerima} ${c.nama_penerima} (${c.hubungan})
- Pasien: ${c.sapaan_pasien} ${c.nama_pasien}
- Rumah sakit: ${c.nama_rs}
- Bulan layanan: ${c.bulan}

Urutan wajib:
A. Pembuka maksimal 45 detik. Katakan kamu asisten otomatis, panggilan direkam, ini bukan tagihan,
dan kamu tidak meminta NIK, OTP, rekening, atau uang.
B. Pastikan kamu berbicara dengan penerima yang benar. ${recipientRule}
C. Tanyakan apakah pasien hadir fisioterapi di rumah sakit dan bulan tersebut.
D. Tanyakan kira-kira berapa kali. Jangan menyebut atau menebak angka tagihan.
${holidayRule}
F. Ulangi jawaban penting, berterima kasih, dan katakan jawaban tidak memengaruhi
layanan atau iuran.

Aturan bicara:
- Ajukan satu pertanyaan per giliran. Setiap kalimat maksimal 20 kata.
- Maksimal tiga pertanyaan inti. Selesaikan seluruh panggilan dalam 150 detik.
- Jangan meminta data pribadi, NIK, OTP, rekening, pembayaran, atau uang.
- Jangan memakai kata curang atau fraud kepada penerima.
- Jangan berdebat, menilai jawaban, atau mengatakan jawaban berbeda dari tagihan.

Cabang wajib:
1. Jika bukan penerima yang benar, minta disambungkan sekali. Jika tidak bisa, tutup dengan sopan.
2. Jika tidak ingat atau ragu, tenangkan dan tanyakan sekali dengan rentang. Jika tetap ragu, tutup.
3. Jika khawatir penipuan, akui itu wajar. Tegaskan tidak meminta data atau uang.
Sarankan Care Center 165
atau Mobile JKN, lalu tawarkan sekali untuk lanjut. Jika menolak, tutup.
4. Jika diminta berhenti, langsung tutup dengan sopan.
5. Jika jawaban berbeda dari dugaan apa pun, catat tanpa mengoreksi atau berdebat.
6. Jika pertanyaan di luar topik, arahkan ke Care Center 165 lalu kembali ke pertanyaan konfirmasi.
7. Jika penerima berkata tidak pernah terapi di sana, catat apa adanya, jangan berdebat, lalu tutup.`;
}

export async function issueToken(context, { apiKey, model, fetchImpl = fetch, now = () => new Date() }) {
  const liveModel = model.replace(/^models\//, "");
  const instruction = buildVoiceInstruction(context);
  const issuedAt = now();
  const expireTime = new Date(issuedAt.getTime() + 5 * 60_000).toISOString();
  const body = {
    uses: 1,
    expireTime,
    newSessionExpireTime: new Date(issuedAt.getTime() + 60_000).toISOString(),
    // Gemini takes the whole session setup from the token and ignores the browser's
    // setup message, so the call script and voice must be locked in here.
    bidiGenerateContentSetup: {
      model: `models/${liveModel}`,
      generationConfig: {
        responseModalities: ["AUDIO"],
        speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: VOICE } } },
      },
      systemInstruction: { parts: [{ text: instruction }] },
      inputAudioTranscription: {},
      outputAudioTranscription: {},
    },
  };
  let response;
  try {
    response = await fetchImpl("https://generativelanguage.googleapis.com/v1beta/auth_tokens", {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-goog-api-key": apiKey },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(TOKEN_TIMEOUT_MS),
    });
  } catch {
    throw fail(503, "penyedia_tidak_tersedia", "Koneksi agen suara belum tersedia.");
  }
  if (!response.ok) throw fail(503, "penyedia_tidak_tersedia", "Koneksi agen suara belum tersedia.");
  const payload = await response.json().catch(() => null);
  if (typeof payload?.name !== "string") {
    throw fail(503, "respons_penyedia_tidak_valid", "Koneksi agen suara belum tersedia.");
  }
  return {
    token: payload.name,
    model: liveModel,
    websocket_url: LIVE_WEBSOCKET_URL,
    instruksi: instruction,
    kedaluwarsa: expireTime,
    maks_durasi_detik: 150,
  };
}
