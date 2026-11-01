import io
import json

from pydantic import ValidationError

from vedika_ai import config
from vedika_ai.answers import JawabanTerstruktur
from vedika_ai.errors import ServiceError
from vedika_ai.evaluation import EvaluationCase, _default_reader, evaluate_cases, main


class FakeReader:
    def read(self, request):
        del request
        return JawabanTerstruktur(
            status_panggilan="terjawab",
            penerima="peserta",
            hubungan=None,
            hadir=True,
            jumlah_min=3,
            jumlah_maks=3,
            keyakinan="tinggi",
            tanda_bahaya=[],
            membantah_tanggal_libur=False,
            kutipan_kunci="Tiga kali.",
            ringkasan="Peserta menyatakan hadir tiga kali.",
        )


class UnavailableReader:
    def __init__(self):
        self.calls = 0

    def read(self, request):
        del request
        self.calls += 1
        raise ServiceError(502, "llm_gagal", "Pembaca jawaban gagal.")


class MalformedOutputReader:
    def read(self, request):
        del request
        try:
            JawabanTerstruktur.model_validate_json("{}")
        except ValidationError as error:
            raise ServiceError(502, "llm_gagal", "Keluaran tidak sesuai skema.") from error


class RecipientAccuracyReader:
    def __init__(self):
        self.calls = 0

    def read(self, request):
        del request
        self.calls += 1
        return JawabanTerstruktur(
            status_panggilan="terjawab",
            penerima="keluarga" if self.calls <= 7 else "peserta",
            hubungan=None,
            hadir=True,
            jumlah_min=10,
            jumlah_maks=10,
            keyakinan="tinggi",
            tanda_bahaya=[],
            membantah_tanggal_libur=False,
            kutipan_kunci="Sepuluh kali.",
            ringkasan="Penerima menyatakan sepuluh sesi.",
        )


def test_cli_reports_field_accuracy_and_does_not_echo_transcript(tmp_path):
    secret = "NIK-SECRET-123456789"
    cases = [
        {
            "id": "case-1",
            "sesi_ditagih": 11,
            "transkrip": [{"detik": 0, "pembicara": "penerima", "teks": secret}],
            "expected": {
                "hasil": {"hadir": True, "jumlah_maks": 3, "keyakinan": "rendah"},
                "label": "Tidak sesuai",
            },
        }
    ]
    source = tmp_path / "cases.json"
    source.write_text(json.dumps(cases), encoding="utf-8")
    output = io.StringIO()

    exit_code = main(
        [str(source), "--threshold", "0.90"],
        reader=FakeReader(),
        stdout=output,
    )

    report = json.loads(output.getvalue())
    assert exit_code == 1
    assert report["correct_fields"] == 2
    assert report["total_fields"] == 3
    assert report["accuracy"] == 0.666667
    assert report["label_accuracy"] == 1.0
    assert report["cases"] == [
        {"id": "case-1", "correct": 2, "total": 3, "label_correct": True}
    ]
    assert secret not in output.getvalue()


def test_cli_returns_success_at_or_above_threshold(tmp_path):
    source = tmp_path / "cases.json"
    source.write_text(
        json.dumps(
            [
                {
                    "id": "case-1",
                    "sesi_ditagih": 11,
                    "transkrip": [],
                    "expected": {"hasil": {"jumlah_maks": 3}, "label": "Tidak sesuai"},
                }
            ]
        ),
        encoding="utf-8",
    )

    assert main([str(source), "--threshold", "1"], reader=FakeReader(), stdout=io.StringIO()) == 0


def test_cli_reports_safe_error_for_malformed_fixture_without_transcript(tmp_path):
    secret = "NIK-PRIVATE-99887766"
    source = tmp_path / "malformed.json"
    source.write_text(
        json.dumps(
            [
                {
                    "id": "case-bad",
                    "sesi_ditagih": 3,
                    "transkrip": [{"pembicara": "penerima", "teks": secret}],
                    "expected": {},
                }
            ]
        ),
        encoding="utf-8",
    )
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main(
        [str(source)],
        reader=FakeReader(),
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 2
    assert stdout.getvalue() == ""
    assert json.loads(stderr.getvalue()) == {"error": "fixture_tidak_valid"}
    assert secret not in stderr.getvalue()


def test_cli_reports_provider_failure_separately_from_model_accuracy(tmp_path):
    source = tmp_path / "cases.json"
    source.write_text(
        json.dumps(
            [
                {
                    "id": "case-provider-down",
                    "sesi_ditagih": 3,
                    "transkrip": [
                        {"detik": 0, "pembicara": "penerima", "teks": "Tiga kali."}
                    ],
                    "expected": {"hasil": {"jumlah_maks": 3}, "label": "Sesuai"},
                }
            ]
        ),
        encoding="utf-8",
    )
    stdout = io.StringIO()

    reader = UnavailableReader()
    exit_code = main([str(source)], reader=reader, stdout=stdout)

    report = json.loads(stdout.getvalue())
    assert exit_code == 2
    assert report["accuracy"] is None
    assert report["provider_errors"] == 1
    assert report["cases"] == [
        {"id": "case-provider-down", "error": "llm_gagal"}
    ]
    assert reader.calls == 1


def test_evaluation_aborts_after_first_provider_error():
    cases = [
        EvaluationCase.model_validate(
            {
                "id": f"case-{index}",
                "sesi_ditagih": 3,
                "transkrip": [
                    {"detik": 0, "pembicara": "penerima", "teks": "Tiga kali."}
                ],
                "expected": {"hasil": {"jumlah_maks": 3}},
            }
        )
        for index in range(3)
    ]
    reader = UnavailableReader()

    report = evaluate_cases(cases, reader)

    assert reader.calls == 1
    assert report["cases_evaluated"] == 1
    assert report["provider_errors"] == 1


def test_cli_reports_safe_configuration_error_when_gemini_key_is_missing(tmp_path, monkeypatch):
    source = tmp_path / "cases.json"
    source.write_text(
        json.dumps(
            [
                {
                    "id": "case-no-key",
                    "sesi_ditagih": 3,
                    "transkrip": [
                        {"detik": 0, "pembicara": "penerima", "teks": "Tiga kali."}
                    ],
                    "expected": {"hasil": {"jumlah_maks": 3}},
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "gemini_api_key", lambda: None)
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main([str(source)], stdout=stdout, stderr=stderr)

    assert exit_code == 2
    assert stdout.getvalue() == ""
    assert json.loads(stderr.getvalue()) == {"error": "gemini_tidak_dikonfigurasi"}


def test_cli_paces_requests_with_configured_interval(tmp_path):
    source = tmp_path / "cases.json"
    source.write_text(
        json.dumps(
            [
                {
                    "id": f"case-{index}",
                    "sesi_ditagih": 3,
                    "transkrip": [],
                    "expected": {"hasil": {"jumlah_maks": 3}},
                }
                for index in range(2)
            ]
        ),
        encoding="utf-8",
    )
    delays = []

    exit_code = main(
        [str(source), "--interval-seconds", "15"],
        reader=FakeReader(),
        stdout=io.StringIO(),
        sleeper=delays.append,
    )

    assert exit_code == 0
    assert delays == [15.0]


def test_live_evaluator_uses_case_interval_as_minimum_provider_backoff(monkeypatch):
    monkeypatch.setattr(config, "gemini_api_key", lambda: "key")
    monkeypatch.setattr(config, "gemini_text_model", lambda: "model")

    reader = _default_reader(interval_seconds=15)

    assert reader.generator.retry_delays == (15, 30, 60)


def test_cli_threshold_uses_key_fields_without_label_inflation(tmp_path):
    source = tmp_path / "cases.json"
    expected = {
        "hasil": {
            "status_panggilan": "terjawab",
            "penerima": "peserta",
            "hadir": True,
            "jumlah_maks": 10,
            "keyakinan": "tinggi",
            "tanda_bahaya": [],
        },
        "label": "Sesuai",
    }
    source.write_text(
        json.dumps(
            [
                {
                    "id": f"case-{index}",
                    "sesi_ditagih": 10,
                    "transkrip": [
                        {
                            "detik": 0,
                            "pembicara": "penerima",
                            "teks": "Saya pasiennya, sepuluh kali.",
                        }
                    ],
                    "expected": expected,
                }
                for index in range(10)
            ]
        ),
        encoding="utf-8",
    )
    stdout = io.StringIO()

    exit_code = main(
        [str(source), "--threshold", "0.90"],
        reader=RecipientAccuracyReader(),
        stdout=stdout,
    )

    report = json.loads(stdout.getvalue())
    assert exit_code == 1
    assert report["accuracy"] == 0.883333
    assert report["label_accuracy"] == 1.0
    assert report["correct_fields"] == 53
    assert report["total_fields"] == 60



def test_malformed_model_output_is_scored_as_a_miss_not_a_provider_outage():
    case = EvaluationCase.model_validate(
        {
            "id": "case-malformed",
            "sesi_ditagih": 3,
            "transkrip": [{"detik": 0, "pembicara": "penerima", "teks": "Tiga kali."}],
            "expected": {"hasil": {"jumlah_maks": 3}, "label": "Sesuai"},
        }
    )

    report = evaluate_cases([case], MalformedOutputReader())

    assert report["provider_errors"] == 0
    assert report["accuracy"] == 0.0
    assert report["cases"] == [
        {"id": "case-malformed", "correct": 0, "total": 1, "label_correct": False}
    ]
