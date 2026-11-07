from collections import Counter
from io import BytesIO
from pathlib import Path
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import csv
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session
from app.analyzers import placeholder  # noqa: F401
from app.core.config import ALLOWED_ORIGINS, MAX_UPLOAD_BYTES
from app.database.session import Base, engine, get_db
from app.models.models import Asset, AuditEvent, Dependency, Finding, MigrationTask, Scan, Workspace
from app.parsers.crypto_parser import SUPPORTED_SUFFIXES, parse_upload
from app.services.seed import ensure_demo_workspace

app = FastAPI(title="CryptoMap API", version="0.1.0", description="Authorized cryptographic asset analysis and PQC readiness planning.")
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=False, allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    from app.database.session import SessionLocal
    db = SessionLocal()
    try:
        ensure_demo_workspace(db)
    finally:
        db.close()


def workspace_or_404(workspace_id: str, db: Session) -> Workspace:
    workspace = db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(404, "Workspace not found")
    return workspace


def serialize_asset(asset: Asset) -> dict:
    return {"id": asset.id, "name": asset.name, "asset_type": asset.asset_type, "source": asset.source, "risk": asset.risk, "metadata": asset.metadata_json, "created_at": asset.created_at.isoformat()}


def serialize_finding(finding: Finding) -> dict:
    return {"id": finding.id, "asset_id": finding.asset_id, "title": finding.title, "algorithm": finding.algorithm, "category": finding.category, "risk": finding.risk, "quantum_relevance": finding.quantum_relevance, "recommendation": finding.recommendation, "evidence": finding.evidence, "source": finding.source, "created_at": finding.created_at.isoformat()}


@app.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok", "service": "cryptomap-api"}


@app.get("/api/v1/workspaces")
def list_workspaces(db: Session = Depends(get_db)) -> list[dict]:
    return [{"id": item.id, "name": item.name, "is_demo": item.is_demo} for item in db.query(Workspace).order_by(Workspace.created_at).all()]


@app.get("/api/v1/dashboard")
def dashboard(workspace_id: str = Query(...), db: Session = Depends(get_db)) -> dict:
    workspace = workspace_or_404(workspace_id, db)
    assets = db.query(Asset).filter_by(workspace_id=workspace.id).all()
    findings = db.query(Finding).join(Asset).filter(Asset.workspace_id == workspace.id).all()
    tasks = db.query(MigrationTask).filter_by(workspace_id=workspace.id).all()
    risks = Counter(item.risk for item in findings)
    algorithms = Counter(item.algorithm or "Certificate" for item in findings)
    quantum = [item for item in findings if item.quantum_relevance == "future quantum-vulnerable"]
    score = max(0, 100 - risks["critical"] * 22 - risks["high"] * 12 - len(quantum) * 6)
    return {
        "workspace": {"id": workspace.id, "name": workspace.name, "is_demo": workspace.is_demo},
        "metrics": {"assets": len(assets), "critical": risks["critical"], "weak": risks["high"] + risks["critical"], "quantum_exposed": len(quantum), "awaiting_review": len([task for task in tasks if task.status in {"Identified", "Under Review"}]), "migration_progress": round((len([task for task in tasks if task.status == "Completed"]) / len(tasks) * 100) if tasks else 0), "pqc_score": score},
        "risk_distribution": [{"name": key.title(), "value": value} for key, value in risks.items()],
        "algorithm_distribution": [{"name": key, "value": value} for key, value in algorithms.items()],
        "recent_assets": [serialize_asset(asset) for asset in sorted(assets, key=lambda item: item.created_at, reverse=True)[:5]],
        "recommended_actions": [serialize_finding(item) for item in findings if item.risk in {"critical", "high"}][:5],
    }


@app.get("/api/v1/assets")
def list_assets(workspace_id: str, q: str = "", risk: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    workspace_or_404(workspace_id, db)
    query = db.query(Asset).filter(Asset.workspace_id == workspace_id)
    if q:
        query = query.filter(Asset.name.ilike(f"%{q}%"))
    if risk:
        query = query.filter(Asset.risk == risk)
    return [serialize_asset(asset) for asset in query.order_by(Asset.created_at.desc()).all()]


@app.get("/api/v1/findings")
def list_findings(workspace_id: str, risk: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    workspace_or_404(workspace_id, db)
    query = db.query(Finding).join(Asset).filter(Asset.workspace_id == workspace_id)
    if risk:
        query = query.filter(Finding.risk == risk)
    return [serialize_finding(finding) for finding in query.order_by(Finding.created_at.desc()).all()]


@app.post("/api/v1/scans/upload")
async def upload_and_scan(workspace_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    workspace = workspace_or_404(workspace_id, db)
    filename = Path(file.filename or "upload").name
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise HTTPException(415, "Supported formats: PEM, CRT, CER, JSON, YAML, TXT, CONF, CONFIG")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"Upload exceeds the {MAX_UPLOAD_BYTES // 1024 // 1024} MB limit")
    scan = Scan(workspace_id=workspace.id, filename=filename, parser="certificate" if suffix in {".pem", ".crt", ".cer"} else "configuration")
    db.add(scan)
    try:
        asset_type, metadata, discovered = parse_upload(filename, data)
    except Exception as exc:
        scan.status = "failed"
        scan.error = "Unable to safely parse the uploaded content."
        db.add(AuditEvent(workspace_id=workspace.id, action="scan.failed", target=filename, detail=scan.error))
        db.commit()
        raise HTTPException(422, scan.error) from exc
    risk_order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
    overall_risk = max((item["risk"] for item in discovered), key=lambda value: risk_order.get(value, 0), default="info")
    asset = Asset(workspace_id=workspace.id, name=filename, asset_type=asset_type, source="uploaded", risk=overall_risk, metadata_json=metadata)
    db.add(asset)
    db.flush()
    created = []
    for item in discovered:
        finding = Finding(asset_id=asset.id, source="parser", **item)
        db.add(finding)
        created.append(finding)
    scan.status = "completed"
    db.add(AuditEvent(workspace_id=workspace.id, action="scan.completed", target=filename, detail=f"Authorized upload analyzed; {len(created)} findings recorded."))
    db.commit()
    return {"scan_id": scan.id, "asset": serialize_asset(asset), "findings": [serialize_finding(item) for item in created], "notice": "Analysis is limited to the uploaded content; this is not network discovery."}


@app.get("/api/v1/dependencies")
def dependencies(workspace_id: str, db: Session = Depends(get_db)) -> dict:
    workspace_or_404(workspace_id, db)
    assets = db.query(Asset).filter_by(workspace_id=workspace_id).all()
    links = db.query(Dependency).filter_by(workspace_id=workspace_id).all()
    nodes = [{"id": asset.id, "label": asset.name, "type": asset.asset_type, "risk": asset.risk, "source": asset.source} for asset in assets]
    edges = [{"id": item.id, "source": item.source_asset_id, "target": item.target_asset_id, "label": item.relation, "evidence": item.evidence, "inferred": item.is_inferred} for item in links]
    return {"nodes": nodes, "edges": edges, "notice": "Only stored, evidenced dependencies are visualized. Unknown relationships are not invented."}


@app.get("/api/v1/pqc")
def pqc(workspace_id: str, db: Session = Depends(get_db)) -> dict:
    workspace_or_404(workspace_id, db)
    findings = db.query(Finding).join(Asset).filter(Asset.workspace_id == workspace_id).all()
    exposed = [serialize_finding(item) for item in findings if item.quantum_relevance == "future quantum-vulnerable"]
    score = max(0, 100 - len(exposed) * 12 - len([item for item in findings if item.risk in {"critical", "high"}]) * 8)
    return {"readiness_score": score, "methodology": "Heuristic planning score based on stored algorithm findings, risk classifications and evidenced dependencies. It is not an official certification.", "exposed_findings": exposed, "standards": [{"name": "ML-KEM", "reference": "FIPS 203"}, {"name": "ML-DSA", "reference": "FIPS 204"}, {"name": "SLH-DSA", "reference": "FIPS 205"}], "next_steps": ["Inventory public-key cryptography dependencies.", "Prioritize weak and deprecated algorithms first.", "Evaluate hybrid migration only after protocol and compatibility review."]}


@app.get("/api/v1/migrations")
def list_migrations(workspace_id: str, db: Session = Depends(get_db)) -> list[dict]:
    workspace_or_404(workspace_id, db)
    return [{"id": item.id, "title": item.title, "concern": item.concern, "direction": item.direction, "priority": item.priority, "status": item.status, "notes": item.notes, "asset_id": item.asset_id} for item in db.query(MigrationTask).filter_by(workspace_id=workspace_id).order_by(MigrationTask.created_at.desc()).all()]


@app.post("/api/v1/migrations/{task_id}/status")
def update_migration_status(task_id: str, status: str, db: Session = Depends(get_db)) -> dict:
    allowed = {"Identified", "Planned", "In Progress", "Under Review", "Completed"}
    if status not in allowed:
        raise HTTPException(422, "Invalid migration status")
    task = db.get(MigrationTask, task_id)
    if not task:
        raise HTTPException(404, "Migration task not found")
    task.status = status
    db.add(AuditEvent(workspace_id=task.workspace_id, action="migration.status_updated", target=task.title, detail=f"Status set to {status}."))
    db.commit()
    return {"id": task.id, "status": task.status}


@app.get("/api/v1/audit")
def audit(workspace_id: str, db: Session = Depends(get_db)) -> list[dict]:
    workspace_or_404(workspace_id, db)
    return [{"id": item.id, "action": item.action, "target": item.target, "detail": item.detail, "created_at": item.created_at.isoformat()} for item in db.query(AuditEvent).filter_by(workspace_id=workspace_id).order_by(AuditEvent.created_at.desc()).limit(100).all()]


@app.get("/api/v1/reports/summary.pdf")
def summary_report(workspace_id: str, db: Session = Depends(get_db)) -> Response:
    workspace = workspace_or_404(workspace_id, db)
    assets = db.query(Asset).filter_by(workspace_id=workspace_id).all()
    findings = db.query(Finding).join(Asset).filter(Asset.workspace_id == workspace_id).all()
    stream = BytesIO()
    pdf = canvas.Canvas(stream, pagesize=letter)
    pdf.setTitle(f"CryptoMap report - {workspace.name}")
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(48, 750, "CryptoMap Cryptographic Intelligence Report")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(48, 730, f"Workspace: {workspace.name}{' (Synthetic demo data)' if workspace.is_demo else ''}")
    pdf.drawString(48, 714, f"Assets: {len(assets)} | Findings: {len(findings)}")
    y = 684
    for finding in findings[:26]:
        pdf.drawString(48, y, f"[{finding.risk.upper()}] {finding.title} - {finding.recommendation[:95]}")
        y -= 18
        if y < 58:
            pdf.showPage(); y = 750
    pdf.drawString(48, max(44, y - 10), "Limitation: Report reflects stored authorized uploads and documented demo records only.")
    pdf.save()
    return Response(stream.getvalue(), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=cryptomap-summary.pdf"})


@app.get("/api/v1/reports/findings.csv")
def findings_csv(workspace_id: str, db: Session = Depends(get_db)) -> Response:
    workspace_or_404(workspace_id, db)
    findings = db.query(Finding).join(Asset).filter(Asset.workspace_id == workspace_id).all()
    stream = BytesIO()
    text_stream = stream
    rows = [
        ["finding", "algorithm", "category", "risk", "quantum_relevance", "recommendation", "evidence", "source"],
        *[[item.title, item.algorithm or "", item.category, item.risk, item.quantum_relevance, item.recommendation, item.evidence, item.source] for item in findings],
    ]
    csv_text = "\ufeff" + "\r\n".join(
        ",".join('"' + str(value).replace('"', '""') + '"' for value in row) for row in rows
    )
    text_stream.write(csv_text.encode("utf-8"))
    return Response(stream.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=cryptomap-findings.csv"})
