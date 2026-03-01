from sqlalchemy import (
    Column, Integer, String, Float, Text,
    DateTime, JSON, Boolean, ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    email         = Column(String, unique=True, index=True, nullable=False)
    full_name     = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=func.now())

    company_profiles = relationship("CompanyProfile", back_populates="owner")
    tenders          = relationship("Tender", back_populates="uploaded_by")


class Tender(Base):
    __tablename__ = "tenders"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=True)
    filename        = Column(String, nullable=False)

    raw_text        = Column(Text)

    extracted_data  = Column(JSON)

    title           = Column(String)
    issuing_authority = Column(String)
    deadline        = Column(String)
    sector          = Column(String)
    estimated_value = Column(Float, nullable=True)

    status          = Column(String, default="pending")
    error_message   = Column(Text, nullable=True)

    created_at      = Column(DateTime, default=func.now())

    uploaded_by       = relationship("User", back_populates="tenders")
    compliance_reports = relationship("ComplianceReport", back_populates="tender")
    bid_drafts         = relationship("BidDraft", back_populates="tender")
    copilot_sessions   = relationship("CopilotSession", back_populates="tender")


class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    id                  = Column(Integer, primary_key=True, index=True)
    user_id             = Column(Integer, ForeignKey("users.id"), nullable=True)

    name                = Column(String, nullable=False)
    registration_number = Column(String)
    pan_number          = Column(String)
    gst_number          = Column(String)

    annual_turnover     = Column(Float)
    net_worth           = Column(Float)
    years_in_operation  = Column(Integer)

    certifications      = Column(JSON, default=list)

    sectors             = Column(JSON, default=list)

    past_projects       = Column(JSON, default=list)

    max_single_project_value = Column(Float, default=0.0)

    available_documents = Column(JSON, default=list)

    msme_category       = Column(String)

    created_at          = Column(DateTime, default=func.now())
    updated_at          = Column(DateTime, default=func.now(), onupdate=func.now())

    owner              = relationship("User", back_populates="company_profiles")
    compliance_reports = relationship("ComplianceReport", back_populates="company")


class ComplianceReport(Base):
    __tablename__ = "compliance_reports"

    id         = Column(Integer, primary_key=True, index=True)
    tender_id  = Column(Integer, ForeignKey("tenders.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("company_profiles.id"), nullable=False)

    score      = Column(Float)

    verdict    = Column(String)

    gaps       = Column(JSON, default=list)

    recommendations = Column(JSON, default=list)

    ai_analysis     = Column(Text, nullable=True)

    created_at = Column(DateTime, default=func.now())

    tender  = relationship("Tender", back_populates="compliance_reports")
    company = relationship("CompanyProfile", back_populates="compliance_reports")


class BidDraft(Base):
    __tablename__ = "bid_drafts"

    id         = Column(Integer, primary_key=True, index=True)
    tender_id  = Column(Integer, ForeignKey("tenders.id"), nullable=False)
    company_id = Column(Integer, nullable=True)

    draft_text = Column(Text)

    version    = Column(Integer, default=1)

    status     = Column(String, default="ready")

    created_at = Column(DateTime, default=func.now())

    tender = relationship("Tender", back_populates="bid_drafts")


class CopilotSession(Base):
    __tablename__ = "copilot_sessions"

    id        = Column(Integer, primary_key=True, index=True)
    tender_id = Column(Integer, ForeignKey("tenders.id"), nullable=False)

    messages  = Column(JSON, default=list)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    tender = relationship("Tender", back_populates="copilot_sessions")
