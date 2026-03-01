from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from auth import get_optional_user
import models, schemas

router = APIRouter(prefix="/companies", tags=["Company Profiles"])


def _compute_max_project_value(past_projects: List[dict]) -> float:
    if not past_projects:
        return 0.0
    return max(p.get("value", 0) for p in past_projects)


@router.post("/", response_model=schemas.CompanyProfileOut, status_code=201)
def create_company_profile(
    data: schemas.CompanyProfileCreate,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_user)
):
    past_projects = [p.dict() for p in data.past_projects]
    max_project   = _compute_max_project_value(past_projects)

    company = models.CompanyProfile(
        user_id                  = current_user.id if current_user else None,
        name                     = data.name,
        registration_number      = data.registration_number,
        pan_number               = data.pan_number,
        gst_number               = data.gst_number,
        annual_turnover          = data.annual_turnover,
        net_worth                = data.net_worth,
        years_in_operation       = data.years_in_operation,
        certifications           = data.certifications,
        sectors                  = data.sectors,
        past_projects            = past_projects,
        max_single_project_value = max_project,
        available_documents      = data.available_documents,
        msme_category            = data.msme_category
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.get("/", response_model=List[schemas.CompanyProfileOut])
def list_companies(
    skip:  int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    return db.query(models.CompanyProfile).offset(skip).limit(limit).all()


@router.get("/{company_id}", response_model=schemas.CompanyProfileOut)
def get_company(company_id: int, db: Session = Depends(get_db)):
    company = db.query(models.CompanyProfile).filter(
        models.CompanyProfile.id == company_id
    ).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company profile {company_id} not found"
        )
    return company


@router.put("/{company_id}", response_model=schemas.CompanyProfileOut)
def update_company(
    company_id: int,
    data: schemas.CompanyProfileUpdate,
    db: Session = Depends(get_db)
):
    company = db.query(models.CompanyProfile).filter(
        models.CompanyProfile.id == company_id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company profile not found")

    update_data = data.dict(exclude_unset=True)

    if "past_projects" in update_data:
        update_data["past_projects"] = [
            p.dict() if hasattr(p, "dict") else p
            for p in update_data["past_projects"]
        ]
        update_data["max_single_project_value"] = _compute_max_project_value(
            update_data["past_projects"]
        )

    for key, value in update_data.items():
        setattr(company, key, value)

    db.commit()
    db.refresh(company)
    return company


@router.delete("/{company_id}", response_model=schemas.SuccessResponse)
def delete_company(company_id: int, db: Session = Depends(get_db)):
    company = db.query(models.CompanyProfile).filter(
        models.CompanyProfile.id == company_id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company profile not found")
    db.delete(company)
    db.commit()
    return {"success": True, "message": f"Company {company_id} deleted"}
