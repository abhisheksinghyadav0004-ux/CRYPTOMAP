import json
import re
from datetime import datetime, timezone
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import Encoding
from app.rules.crypto_rules import classify

SUPPORTED_SUFFIXES = {".pem", ".crt", ".cer", ".json", ".yaml", ".yml", ".txt", ".conf", ".config"}
ALGORITHM_PATTERNS = {
    "RSA": r"\brsa\b",
    "ECDSA": r"\becdsa\b",
    "ECC": r"\becc\b|\belliptic[- ]curve\b",
    "ECDH": r"\becdh\b",
    "ED25519": r"\bed25519\b",
    "AES-256": r"\baes[-_ ]?256\b",
    "AES-128": r"\baes[-_ ]?128\b",
    "3DES": r"\b3des\b|\btripledes\b",
    "DES": r"\bdes\b",
    "SHA-1": r"\bsha[-_ ]?1\b",
    "SHA-256": r"\bsha[-_ ]?256\b",
    "SHA-384": r"\bsha[-_ ]?384\b",
    "SHA-512": r"\bsha[-_ ]?512\b",
    "MD5": r"\bmd5\b",
    "ML-KEM": r"\bml[-_ ]?kem\b",
    "ML-DSA": r"\bml[-_ ]?dsa\b",
    "SLH-DSA": r"\bslh[-_ ]?dsa\b",
}


def text_findings(text: str) -> list[dict]:
    findings = []
    for algorithm, pattern in ALGORITHM_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            rule = classify(algorithm)
            if rule:
                findings.append({"title": f"{algorithm} detected", "algorithm": algorithm, "category": rule.category, "risk": rule.risk, "quantum_relevance": rule.quantum_relevance, "recommendation": rule.recommendation, "evidence": f"Matched authorized uploaded configuration content for {algorithm}."})
    return findings


def parse_certificate(data: bytes) -> tuple[dict, list[dict]]:
    try:
        certificate = x509.load_pem_x509_certificate(data)
    except ValueError:
        certificate = x509.load_der_x509_certificate(data)
    public_key = certificate.public_key()
    key_size = getattr(public_key, "key_size", None)
    signature = certificate.signature_hash_algorithm.name.upper() if certificate.signature_hash_algorithm else "unknown"
    key_name = public_key.__class__.__name__.replace("PublicKey", "").upper()
    metadata = {
        "subject": certificate.subject.rfc4514_string(),
        "issuer": certificate.issuer.rfc4514_string(),
        "serial_number": format(certificate.serial_number, "X"),
        "not_valid_before": certificate.not_valid_before_utc.isoformat(),
        "not_valid_after": certificate.not_valid_after_utc.isoformat(),
        "signature_algorithm": signature,
        "public_key_algorithm": key_name,
        "public_key_size": key_size,
        "sha256_fingerprint": certificate.fingerprint(hashes.SHA256()).hex(),
        "is_self_signed": certificate.subject == certificate.issuer,
    }
    findings = text_findings(f"{signature} {key_name}")
    now = datetime.now(timezone.utc)
    if certificate.not_valid_after_utc < now:
        findings.append({"title": "Certificate expired", "algorithm": None, "category": "certificate", "risk": "critical", "quantum_relevance": "not applicable", "recommendation": "Replace the expired certificate and validate the replacement chain.", "evidence": f"Certificate expired {metadata['not_valid_after']}."})
    elif (certificate.not_valid_after_utc - now).days <= 30:
        findings.append({"title": "Certificate expires within 30 days", "algorithm": None, "category": "certificate", "risk": "high", "quantum_relevance": "not applicable", "recommendation": "Schedule certificate renewal and validate the deployment path.", "evidence": f"Certificate expires {metadata['not_valid_after']}."})
    if key_size and key_name == "RSA" and key_size < 2048:
        findings.append({"title": "Insufficient RSA key size", "algorithm": "RSA", "category": "certificate", "risk": "high", "quantum_relevance": "future quantum-vulnerable", "recommendation": "Replace with at least RSA-2048 while evaluating future PQC migration requirements.", "evidence": f"Certificate public key size is {key_size} bits."})
    return metadata, findings


def parse_upload(filename: str, data: bytes) -> tuple[str, dict, list[dict]]:
    lower = filename.lower()
    if lower.endswith((".pem", ".crt", ".cer")):
        metadata, findings = parse_certificate(data)
        return "certificate", metadata, findings
    text = data.decode("utf-8", errors="replace")
    metadata = {"content_type": "configuration", "bytes": len(data)}
    if lower.endswith(".json"):
        json.loads(text)
        metadata["format"] = "json"
    elif lower.endswith((".yaml", ".yml")):
        metadata["format"] = "yaml"
    else:
        metadata["format"] = "text"
    return "configuration", metadata, text_findings(text)
