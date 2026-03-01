from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any, Dict
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=6)


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class EligibilityInfo(BaseModel):
    min_turnover: Optional[float] = None
    years_experience: Optional[int] = None
    required_certifications: List[str] = []
    msme_preference: bool = False
    past_project_requirement: Optional[str] = None
    min_single_project_value: Optional[float] = None


class TenderExtractedData(BaseModel):
    tender_id: Optional[str] = None
    title: str
    issuing_authority: str
    deadline: Optional[str] = None
    estimated_value: Optional[float] = None
    eligibility: EligibilityInfo
    documents_required: List[str] = []
    key_clauses: List[str] = []
    sector: str


class TenderOut(BaseModel):
    id: int
    filename: str
    title: Optional[str]
    issuing_authority: Optional[str]
    deadline: Optional[str]
    sector: Optional[str]
    estimated_value: Optional[float]
    status: str
    extracted_data: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


class TenderListItem(BaseModel):
    id: int
    filename: str
    title: Optional[str]
    issuing_authority: Optional[str]
    deadline: Optional[str]
    sector: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class PastProject(BaseModel):
    name: str
    client: str
    value: float
    year: int
    sector: Optional[str] = None


class CompanyProfileCreate(BaseModel):
    name: str = Field(..., min_length=2)
    registration_number: Optional[str] = None
    pan_number: Optional[str] = None
    gst_number: Optional[str] = None
    annual_turnover: float = Field(..., gt=0, description="In INR Lakhs")
    net_worth: Optional[float] = None
    years_in_operation: int = Field(..., ge=0)
    certifications: List[str] = []
    sectors: List[str] = []
    past_projects: List[PastProject] = []
    available_documents: List[str] = []
    msme_category: Optional[str] = None


class CompanyProfileUpdate(BaseModel):
    name: Optional[str] = None
    annual_turnover: Optional[float] = None
    net_worth: Optional[float] = None
    years_in_operation: Optional[int] = None
    certifications: Optional[List[str]] = None
    sectors: Optional[List[str]] = None
    past_projects: Optional[List[PastProject]] = None
    available_documents: Optional[List[str]] = None
    msme_category: Optional[str] = None


class CompanyProfileOut(BaseModel):
    id: int
    name: str
    registration_number: Optional[str]
    pan_number: Optional[str]
    gst_number: Optional[str]
    annual_turnover: float
    net_worth: Optional[float]
    years_in_operation: int
    certifications: List[str]
    sectors: List[str]
    past_projects: List[Any]
    max_single_project_value: float
    available_documents: List[str]
    msme_category: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ComplianceGap(BaseModel):
    field: str
    required: Any
    actual: Any
    severity: str
    deduction: float
    note: Optional[str] = None


class ComplianceRequest(BaseModel):
    tender_id: int
    company_id: int


class ComplianceReportOut(BaseModel):
    id: int
    tender_id: int
    company_id: int
    score: float
    verdict: str
    gaps: List[Any]
    recommendations: List[str]
    ai_analysis: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class DraftRequest(BaseModel):
    tender_id: int
    company_id: int
    additional_context: Optional[str] = None


class BidDraftOut(BaseModel):
    id: int
    tender_id: int
    draft_text: str
    version: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class CopilotMessage(BaseModel):
    role: str
    content: str


class CopilotAskRequest(BaseModel):
    tender_id: int
    session_id: Optional[int] = None
    question: str


class CopilotResponse(BaseModel):
    session_id: int
    answer: str
    conversation: List[CopilotMessage]


class SuccessResponse(BaseModel):
    success: bool = True
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None


class DraftRequest(BaseModel):
    tender_id: int
    company_id: int
    additional_context: Optional[str] = None


class BidDraftOut(BaseModel):
    id: int
    tender_id: int
    draft_text: str
    version: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True



class CopilotMessage(BaseModel):
    role: str
    content: str


class CopilotAskRequest(BaseModel):
    tender_id: int
    session_id: Optional[int] = None
    question: str


class CopilotResponse(BaseModel):
    session_id: int
    answer: str
    conversation: List[CopilotMessage]



class SuccessResponse(BaseModel):
    success: bool = True
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None
