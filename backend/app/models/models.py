import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.session import Base


def uid() -> str:
    return str(uuid.uuid4())


class Workspace(Base):
    __tablename__ = "workspaces"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    assets: Mapped[list["Asset"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")


class Asset(Base):
    __tablename__ = "assets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    asset_type: Mapped[str] = mapped_column(String(80))
    source: Mapped[str] = mapped_column(String(32), default="uploaded")
    risk: Mapped[str] = mapped_column(String(24), default="unknown")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    workspace: Mapped[Workspace] = relationship(back_populates="assets")
    findings: Mapped[list["Finding"]] = relationship(back_populates="asset", cascade="all, delete-orphan")


class Scan(Base):
    __tablename__ = "scans"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="completed")
    parser: Mapped[str] = mapped_column(String(80))
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Finding(Base):
    __tablename__ = "findings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    algorithm: Mapped[str | None] = mapped_column(String(80), nullable=True)
    category: Mapped[str] = mapped_column(String(80))
    risk: Mapped[str] = mapped_column(String(24))
    quantum_relevance: Mapped[str] = mapped_column(String(80))
    recommendation: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(40), default="parser")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    asset: Mapped[Asset] = relationship(back_populates="findings")


class Dependency(Base):
    __tablename__ = "dependencies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    source_asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"))
    target_asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"))
    relation: Mapped[str] = mapped_column(String(80))
    evidence: Mapped[str] = mapped_column(Text)
    is_inferred: Mapped[bool] = mapped_column(Boolean, default=False)


class MigrationTask(Base):
    __tablename__ = "migration_tasks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    concern: Mapped[str] = mapped_column(Text)
    direction: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(24))
    status: Mapped[str] = mapped_column(String(32), default="Identified")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    action: Mapped[str] = mapped_column(String(120))
    target: Mapped[str] = mapped_column(String(255))
    detail: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
