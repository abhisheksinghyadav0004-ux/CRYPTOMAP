from dataclasses import dataclass


@dataclass(frozen=True)
class AlgorithmRule:
    risk: str
    category: str
    quantum_relevance: str
    recommendation: str


RULES = {
    "MD5": AlgorithmRule("critical", "hash", "deprecated", "Remove MD5. Use SHA-256 or stronger for integrity use cases."),
    "SHA-1": AlgorithmRule("high", "hash", "not a PQC concern", "Retire SHA-1 signatures and use SHA-256 or stronger."),
    "DES": AlgorithmRule("critical", "symmetric", "not a PQC concern", "Replace DES with AES-128 or AES-256."),
    "3DES": AlgorithmRule("high", "symmetric", "not a PQC concern", "Plan replacement with AES; 3DES is deprecated for new designs."),
    "RSA": AlgorithmRule("medium", "public-key", "future quantum-vulnerable", "Inventory usage and plan a standards-based hybrid migration assessment."),
    "ECDSA": AlgorithmRule("medium", "signature", "future quantum-vulnerable", "Assess certificate and protocol support before a hybrid or PQC signature migration."),
    "ECC": AlgorithmRule("medium", "public-key", "future quantum-vulnerable", "Document dependencies and evaluate migration paths; not currently broken by quantum computers."),
    "ECDH": AlgorithmRule("medium", "key exchange", "future quantum-vulnerable", "Assess protocol support for hybrid key establishment such as ML-KEM integration."),
    "AES-128": AlgorithmRule("low", "symmetric", "configuration dependent", "Assess data lifetime and consider AES-256 for long-term confidentiality."),
    "AES-256": AlgorithmRule("info", "symmetric", "reduced quantum margin", "Currently accepted for intended use; retain key-management controls."),
    "SHA-256": AlgorithmRule("info", "hash", "reduced quantum margin", "Currently accepted for intended use; retain sound implementation controls."),
    "SHA-384": AlgorithmRule("info", "hash", "reduced quantum margin", "Currently accepted for intended use."),
    "SHA-512": AlgorithmRule("info", "hash", "reduced quantum margin", "Currently accepted for intended use."),
    "ED25519": AlgorithmRule("info", "signature", "future quantum-vulnerable", "Currently accepted; include in longer-term PQC planning."),
    "ML-KEM": AlgorithmRule("info", "key encapsulation", "PQC standard: FIPS 203", "Use only after protocol compatibility and implementation review."),
    "ML-DSA": AlgorithmRule("info", "signature", "PQC standard: FIPS 204", "Use only after protocol compatibility and implementation review."),
    "SLH-DSA": AlgorithmRule("info", "signature", "PQC standard: FIPS 205", "Use only after protocol compatibility and implementation review."),
}


def classify(algorithm: str) -> AlgorithmRule | None:
    normalized = algorithm.upper().replace("_", "-")
    return RULES.get(normalized)
