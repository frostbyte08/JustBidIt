from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
import models
import schemas
from services import gemini_client

router = APIRouter(
    prefix="/copilot",
    tags=["AI Copilot & Draft Generation"]
)

@router.post("/ask", response_model=schemas.CopilotResponse)
def ask_copilot(
    request: schemas.CopilotAskRequest,
    db: Session = Depends(get_db)
):
    """
    Ask AI copilot a question about a specific tender.
    Maintains conversation history within a session.
    """

    tender = db.query(models.Tender).filter(
        models.Tender.id == request.tender_id
    ).first()

    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    if not tender.extracted_data:
        raise HTTPException(
            status_code=422,
            detail="Tender has not been extracted yet."
        )

    session = None

    if request.session_id:
        session = db.query(models.CopilotSession).filter(
            models.CopilotSession.id == request.session_id
        ).first()

    if not session:
        session = models.CopilotSession(
            tender_id=request.tender_id,
            messages=[]
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    messages = list(session.messages or [])
    messages.append({
        "role": "user",
        "content": request.question
    })

    try:
        answer = gemini_client.copilot_answer(
            tender_data=tender.extracted_data,
            question=request.question,
            conversation_history=messages[:-1]
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI processing failed: {str(e)}"
        )

    if not answer:
        answer = "AI could not generate a response. Please try again."

    messages.append({
        "role": "assistant",
        "content": answer
    })

    session.messages = messages
    db.commit()

    return schemas.CopilotResponse(
        session_id=session.id,
        answer=answer,
        conversation=[
            schemas.CopilotMessage(role=m["role"], content=m["content"])
            for m in messages
        ]
    )

@router.get("/sessions/{session_id}", response_model=schemas.CopilotResponse)
def get_session(session_id: int, db: Session = Depends(get_db)):
    """
    Retrieve full copilot conversation history.
    """

    session = db.query(models.CopilotSession).filter(
        models.CopilotSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = session.messages or []

    last_answer = ""
    if messages and messages[-1]["role"] == "assistant":
        last_answer = messages[-1]["content"]

    return schemas.CopilotResponse(
        session_id=session.id,
        answer=last_answer,
        conversation=[
            schemas.CopilotMessage(role=m["role"], content=m["content"])
            for m in messages
        ]
    )



@router.post(
    "/generate-draft",
    response_model=schemas.BidDraftOut,
    status_code=status.HTTP_201_CREATED
)
def generate_draft(
    request: schemas.DraftRequest,
    db: Session = Depends(get_db)
):
    """
    Generate a structured professional bid draft.
    """

    tender = db.query(models.Tender).filter(
        models.Tender.id == request.tender_id
    ).first()

    if not tender or not tender.extracted_data:
        raise HTTPException(
            status_code=404,
            detail="Tender not found or not yet extracted"
        )

    company = db.query(models.CompanyProfile).filter(
        models.CompanyProfile.id == request.company_id
    ).first()

    if not company:
        raise HTTPException(status_code=404, detail="Company profile not found")

    company_dict = {
        "name": company.name,
        "annual_turnover": company.annual_turnover,
        "years_in_operation": company.years_in_operation,
        "certifications": company.certifications or [],
        "sectors": company.sectors or [],
        "past_projects": company.past_projects or [],
        "msme_category": company.msme_category,
        "registration_number": company.registration_number,
        "gst_number": company.gst_number,
    }

    try:
        draft_text = gemini_client.generate_bid_draft(
            tender_data=tender.extracted_data,
            company_data=company_dict,
            additional_context=request.additional_context
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Draft generation failed: {str(e)}"
        )

    existing_count = db.query(models.BidDraft).filter(
        models.BidDraft.tender_id == request.tender_id,
        models.BidDraft.company_id == request.company_id
    ).count()

    draft = models.BidDraft(
        tender_id=request.tender_id,
        company_id=request.company_id,
        draft_text=draft_text,
        version=existing_count + 1,
        status="ready"
    )

    db.add(draft)
    db.commit()
    db.refresh(draft)

    return draft



@router.get("/drafts/{draft_id}", response_model=schemas.BidDraftOut)
def get_draft(draft_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a specific bid draft.
    """

    draft = db.query(models.BidDraft).filter(
        models.BidDraft.id == draft_id
    ).first()

    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    return draft




@router.get("/drafts", response_model=List[schemas.BidDraftOut])
def list_drafts(
    tender_id: Optional[int] = None,
    company_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    List all generated drafts with optional filtering.
    """

    query = db.query(models.BidDraft)

    if tender_id:
        query = query.filter(models.BidDraft.tender_id == tender_id)

    if company_id:
        query = query.filter(models.BidDraft.company_id == company_id)

    return query.all()
