"""Voice-agent prompt and short-lived Gemini Live credential provisioning."""

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field

from .gemini import GeminiError

LIVE_WEBSOCKET_URL = (
    "wss://generativelanguage.googleapis.com/ws/"
    "google.ai.generativelanguage.v1beta.GenerativeService."
    "BidiGenerateContentConstrained"
)
VOICE = "Kore"


class VoiceContext(BaseModel):
    """The `skrip` object from Kontrak B1 `agen/ambil`; unknown fields are ignored."""

    nama_penerima: str = Field(min_length=1, max_length=120)
    sapaan_penerima: str = Field(min_length=1, max_length=20)
    hubungan: str = Field(min_length=1, max_length=40)
    nama_pasien: str = Field(min_length=1, max_length=120)
    sapaan_pasien: str = Field(min_length=1, max_length=20)
    nama_rs: str = Field(min_length=1, max_length=160)
    bulan: str = Field(min_length=1, max_length=40)
    tanggal_libur: list[str] = Field(default_factory=list)


class VoiceTokenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str
    model: str
    websocket_url: str
    instruksi: str
    kedaluwarsa: datetime
    maks_durasi_detik: int = 150


def _join(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " dan " + items[-1]


def _holiday_text(values: list[str]) -> str:
    """["16 Agustus", "17 Agustus"] -> "16 dan 17 Agustus"."""

    days, months = zip(*(value.partition(" ")[::2] for value in values), strict=True)
    if len(set(months)) == 1 and all(months):
        return f"{_join(list(days))} {months[0]}"
    return _join(values)


def build_voice_instruction(context: VoiceContext) -> str:
    if context.tanggal_libur:
        holiday_rule = (
            "E. Tanggal libur: tanyakan apakah pasien terapi pada tanggal libur yang perlu "
            f"ditanyakan: {_holiday_text(context.tanggal_libur)}."
        )
    else:
        holiday_rule = "E. Jangan bertanya tentang tanggal libur karena tidak ada tanggal aktif."
    if context.hubungan == "peserta":
        recipient_rule = f"Sapa {context.sapaan_penerima} {context.nama_penerima}."
    else:
        recipient_rule = (
            f"Penerima adalah keluarga ({context.hubungan}) pasien. Sapa sebagai keluarga "
            f"{context.sapaan_pasien} {context.nama_pasien.split()[0]}."
        )

    return f"""Peran: Kamu asisten otomatis BPJS Kesehatan yang menelepon untuk konfirmasi
singkat layanan fisioterapi.
Gunakan Bahasa Indonesia sopan, sederhana, dan santai.

Data panggilan:
- Penerima: {context.sapaan_penerima} {context.nama_penerima} ({context.hubungan})
- Pasien: {context.sapaan_pasien} {context.nama_pasien}
- Rumah sakit: {context.nama_rs}
- Bulan layanan: {context.bulan}

Urutan wajib:
A. Pembuka maksimal 45 detik. Katakan kamu asisten otomatis, panggilan direkam, ini bukan tagihan,
dan kamu tidak meminta NIK, OTP, rekening, atau uang.
B. Pastikan kamu berbicara dengan penerima yang benar. {recipient_rule}
C. Tanyakan apakah pasien hadir fisioterapi di rumah sakit dan bulan tersebut.
D. Tanyakan kira-kira berapa kali. Jangan menyebut atau menebak angka tagihan.
{holiday_rule}
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
7. Jika penerima berkata tidak pernah terapi di sana, catat apa adanya, jangan berdebat, lalu tutup.
""".strip()


class GeminiTokenIssuer:
    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        timeout: float = 15,
        opener: Callable[..., Any] = urlopen,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        if not api_key:
            raise ValueError("Gemini API key is required")
        self.api_key = api_key
        self.model = model.removeprefix("models/")
        self.timeout = timeout
        self.opener = opener
        self.now = now

    def issue(self, context: VoiceContext) -> VoiceTokenResponse:
        instruction = build_voice_instruction(context)
        issued_at = self.now().astimezone(UTC)
        expire_time = issued_at + timedelta(minutes=5)
        new_session_expire_time = issued_at + timedelta(minutes=1)
        body = {
            "uses": 1,
            "expireTime": expire_time.isoformat().replace("+00:00", "Z"),
            "newSessionExpireTime": new_session_expire_time.isoformat().replace("+00:00", "Z"),
            # Gemini takes the whole session setup from the token and ignores the browser's
            # setup message, so the call script and voice must be locked in here.
            "bidiGenerateContentSetup": {
                "model": f"models/{self.model}",
                "generationConfig": {
                    "responseModalities": ["AUDIO"],
                    "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOICE}}},
                },
                "systemInstruction": {"parts": [{"text": instruction}]},
                "inputAudioTranscription": {},
                "outputAudioTranscription": {},
            },
        }
        request = Request(
            "https://generativelanguage.googleapis.com/v1beta/auth_tokens",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            },
            method="POST",
        )
        try:
            with self.opener(request, timeout=self.timeout) as response:
                payload = json.load(response)
            token = payload["name"]
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            raise GeminiError("penyedia_tidak_tersedia") from error
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise GeminiError("respons_penyedia_tidak_valid") from error

        return VoiceTokenResponse(
            token=token,
            model=self.model,
            websocket_url=LIVE_WEBSOCKET_URL,
            instruksi=instruction,
            kedaluwarsa=expire_time,
        )

