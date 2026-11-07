from app.parsers.crypto_parser import parse_upload, text_findings


def test_detects_weak_and_pqc_relevant_algorithms() -> None:
    findings = text_findings("legacy sha1 RSA tls and AES-256 storage")
    by_algorithm = {item["algorithm"]: item for item in findings}
    assert by_algorithm["SHA-1"]["risk"] == "high"
    assert by_algorithm["RSA"]["quantum_relevance"] == "future quantum-vulnerable"
    assert by_algorithm["AES-256"]["risk"] == "info"


def test_json_upload_is_parsed_without_execution() -> None:
    asset_type, metadata, findings = parse_upload("authorized.json", b'{"tls":"RSA", "legacy":"MD5"}')
    assert asset_type == "configuration"
    assert metadata["format"] == "json"
    assert {item["algorithm"] for item in findings} == {"RSA", "MD5"}


def test_invalid_json_is_rejected() -> None:
    try:
        parse_upload("invalid.json", b"not json")
    except ValueError:
        return
    raise AssertionError("Invalid JSON must be rejected")
