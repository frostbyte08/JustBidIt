from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
import models
import schemas
from services import compliance_engine, gemini_client

router = APIRouter(prefix="/compliance", tags=["Compliance Scoring"])


@router.post("/score", response_model=schemas.ComplianceReportOut, status_code=201)
def run_compliance_score(
    request: schemas.ComplianceRequest,
    include_ai: bool = True,
    db: Session = Depends(get_db)
):
    tender = db.query(models.Tender).filter(models.Tender.id == request.tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    if not tender.extracted_data:
        raise HTTPException(status_code=422, detail="Tender not yet extracted. Upload PDF first.")

    company = db.query(models.CompanyProfile).filter(models.CompanyProfile.id == request.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    company_dict = {
        "name":                     company.name,
        "annual_turnover":          company.annual_turnover,
        "years_in_operation":       company.years_in_operation,
        "certifications":           company.certifications or [],
        "past_projects":            company.past_projects or [],
        "max_single_project_value": company.max_single_project_value or 0,
        "available_documents":      company.available_documents or [],
        "msme_category":            company.msme_category,
    }

    scoring = compliance_engine.score_compliance(tender.extracted_data, company_dict)

    ai_analysis = None
    if include_ai:
        ai_analysis = gemini_client.analyze_compliance_gaps(
            tender.extracted_data,
            company_dict,
            scoring["gaps"]
        )

    report = models.ComplianceReport(
        tender_id       = request.tender_id,
        company_id      = request.company_id,
        score           = scoring["score"],
        verdict         = scoring["verdict"],
        gaps            = scoring["gaps"],
        recommendations = scoring["recommendations"],
        ai_analysis     = ai_analysis
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("/quick-check")
def quick_check(tender_id: int, company_id: int, db: Session = Depends(get_db)):
    tender  = db.query(models.Tender).filter(models.Tender.id == tender_id).first()
    company = db.query(models.CompanyProfile).filter(models.CompanyProfile.id == company_id).first()

    if not tender or not tender.extracted_data:
        raise HTTPException(status_code=404, detail="Tender not found or not extracted")
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    company_dict = {
        "annual_turnover":          company.annual_turnover,
        "years_in_operation":       company.years_in_operation,
        "certifications":           company.certifications or [],
        "past_projects":            company.past_projects or [],
        "max_single_project_value": company.max_single_project_value or 0,
        "available_documents":      company.available_documents or [],
        "msme_category":            company.msme_category,
    }
    scoring = compliance_engine.score_compliance(tender.extracted_data, company_dict)
    return {
        "tender_id":  tender_id,
        "company_id": company_id,
        "score":      scoring["score"],
        "verdict":    scoring["verdict"],
        "gap_count":  len(scoring["gaps"]),
        "gaps_summary": [{"field": g["field"], "severity": g["severity"]} for g in scoring["gaps"]],
        "note": "Quick check only. POST /compliance/score for full AI analysis."
    }


@router.get("/reports", response_model=List[schemas.ComplianceReportOut])
def list_reports(
    tender_id:  Optional[int] = None,
    company_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    q = db.query(models.ComplianceReport)
    if tender_id:  q = q.filter(models.ComplianceReport.tender_id == tender_id)
    if company_id: q = q.filter(models.ComplianceReport.company_id == company_id)
    return q.offset(skip).limit(limit).all()


@router.get("/reports/{report_id}", response_model=schemas.ComplianceReportOut)
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(models.ComplianceReport).filter(models.ComplianceReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
