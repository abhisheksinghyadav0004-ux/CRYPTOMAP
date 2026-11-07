from sqlalchemy.orm import Session
from app.models.models import Asset, AuditEvent, Dependency, Finding, MigrationTask, Workspace


def ensure_demo_workspace(db: Session) -> Workspace:
    workspace = db.query(Workspace).filter_by(name="CryptoMap Demo Workspace").first()
    if workspace:
        _ensure_demo_dependencies(db, workspace)
        return workspace
    workspace = Workspace(name="CryptoMap Demo Workspace", is_demo=True)
    db.add(workspace)
    db.flush()
    demo_assets = [
        ("Payments API", "application", "medium", "RSA TLS certificate; AES-256 at rest"),
        ("Partner Gateway", "service", "high", "ECDSA TLS certificate; SHA-1 legacy signature"),
        ("Archive Service", "application", "critical", "3DES legacy encryption"),
        ("Identity Platform", "service", "low", "Ed25519; modern key exchange"),
        ("Unknown Legacy Connector", "service", "unknown", "No authorized dependency evidence recorded"),
    ]
    created = []
    for name, asset_type, risk, evidence in demo_assets:
        asset = Asset(workspace_id=workspace.id, name=name, asset_type=asset_type, risk=risk, source="synthetic-demo", metadata_json={"notice": "Synthetic demo record"})
        db.add(asset)
        created.append((asset, evidence))
    db.flush()
    for asset, evidence in created:
        for algorithm in (["RSA", "AES-256"] if asset.name == "Payments API" else ["ECDSA", "SHA-1"] if asset.name == "Partner Gateway" else ["3DES"] if asset.name == "Archive Service" else ["ED25519"] if asset.name == "Identity Platform" else []):
            from app.rules.crypto_rules import classify
            rule = classify(algorithm)
            db.add(Finding(asset_id=asset.id, title=f"{algorithm} detected", algorithm=algorithm, category=rule.category, risk=rule.risk, quantum_relevance=rule.quantum_relevance, recommendation=rule.recommendation, evidence=f"Synthetic demo: {evidence}", source="synthetic-demo"))
    db.add(MigrationTask(workspace_id=workspace.id, asset_id=created[2][0].id, title="Replace legacy 3DES archive encryption", concern="3DES is deprecated for new designs.", direction="Assess AES-256 migration and archival compatibility.", priority="Critical", status="Identified", notes="Synthetic demo task."))
    db.add(MigrationTask(workspace_id=workspace.id, asset_id=created[0][0].id, title="Assess RSA TLS hybrid migration", concern="RSA is future quantum-vulnerable, not currently broken.", direction="Document TLS dependencies and evaluate hybrid migration options.", priority="Medium", status="Planned", notes="Synthetic demo task."))
    db.add(AuditEvent(workspace_id=workspace.id, action="demo.workspace.seeded", target=workspace.name, detail="Synthetic demo workspace initialized."))
    db.commit()
    _ensure_demo_dependencies(db, workspace)
    return workspace


def _ensure_demo_dependencies(db: Session, workspace: Workspace) -> None:
    if db.query(Dependency).filter_by(workspace_id=workspace.id).first():
        return
    assets = {asset.name: asset for asset in db.query(Asset).filter_by(workspace_id=workspace.id).all()}
    payments = assets.get("Payments API")
    partner = assets.get("Partner Gateway")
    if not payments or not partner:
        return
    db.add(Dependency(
        workspace_id=workspace.id,
        source_asset_id=payments.id,
        target_asset_id=partner.id,
        relation="uses trusted gateway",
        evidence="Synthetic demo relationship documented in the demo workspace architecture.",
        is_inferred=False,
    ))
    db.add(AuditEvent(workspace_id=workspace.id, action="demo.dependency.seeded", target="Payments API -> Partner Gateway", detail="Synthetic demo dependency recorded with explicit evidence."))
    db.commit()
