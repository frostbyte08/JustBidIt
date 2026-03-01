import os
import shutil
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from auth import get_optional_user
import models, schemas
from services import pdf_extractor, gemini_client

router = APIRouter(prefix="/tenders", tags=["Tenders"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf"}
MAX_FILE_SIZE_MB   = 20


@router.post("/upload", response_model=schemas.TenderOut, status_code=201)
async def upload_tender(
    file: UploadFile = File(...),
    db:   Session    = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_user)
):
    """
    Upload a tender PDF and trigger AI extraction.

    Steps:
    1. Validate file type (PDF only)
    2. Save file to uploads/ directory
    3. Extract text with pdfplumber
    4. Send to Gemini for structured extraction
    5. Save results to database
    6. Return structured tender data

    Authentication is optional — works without login for demo purposes.
    """

    filename  = file.filename or "upload.pdf"
    ext       = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only PDF files are accepted. Received: {ext}"
        )

    safe_filename = filename.replace(" ", "_")
    file_path     = os.path.join(UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as buffer:
        content = await file.read()

        size_mb = len(content) / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large ({size_mb:.1f}MB). Maximum allowed: {MAX_FILE_SIZE_MB}MB"
            )

        buffer.write(content)

    tender = models.Tender(
        filename = safe_filename,
        user_id  = current_user.id if current_user else None,
        status   = "pending"
    )
    db.add(tender)
    db.commit()
    db.refresh(tender)

    extraction_result = pdf_extractor.extract_text_from_pdf(file_path)

    if not extraction_result["success"]:
        tender.status        = "failed"
        tender.error_message = extraction_result.get("error", "PDF extraction failed")
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=tender.error_message
        )

    raw_text = extraction_result["full_text"]
    sections = extraction_result["sections"]

    tender.raw_text = raw_text
    db.commit()

    extracted = gemini_client.extract_tender_structure(raw_text, sections)

    if "error" in extracted:
        tender.status        = "failed"
        tender.error_message = extracted["error"]
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"PDF extracted but AI analysis failed: {extracted['error']}"
        )

    tender.extracted_data    = extracted
    tender.title             = extracted.get("title", "Untitled Tender")
    tender.issuing_authority = extracted.get("issuing_authority")
    tender.deadline          = extracted.get("deadline")
    tender.sector            = extracted.get("sector")
    tender.estimated_value   = extracted.get("estimated_value")
    tender.status            = "extracted"
    db.commit()
    db.refresh(tender)

    return tender


@router.get("/", response_model=List[schemas.TenderListItem])
def list_tenders(
    skip:  int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    List all uploaded tenders (paginated).
    Returns lightweight summary without full extracted_data.
    """
    tenders = db.query(models.Tender).offset(skip).limit(limit).all()
    return tenders


@router.get("/{tender_id}", response_model=schemas.TenderOut)
def get_tender(tender_id: int, db: Session = Depends(get_db)):
    """
    Get full details of a specific tender including extracted data.
    """
    tender = db.query(models.Tender).filter(models.Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tender with ID {tender_id} not found"
        )
    return tender


@router.get("/{tender_id}/raw-text")
def get_tender_raw_text(tender_id: int, db: Session = Depends(get_db)):
    """
    Return the raw extracted text from the PDF.
    Useful for debugging extraction quality.
    """
    tender = db.query(models.Tender).filter(models.Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    return {
        "tender_id": tender_id,
        "filename":  tender.filename,
        "raw_text":  tender.raw_text,
        "char_count": len(tender.raw_text or "")
    }


@router.delete("/{tender_id}", response_model=schemas.SuccessResponse)
def delete_tender(tender_id: int, db: Session = Depends(get_db)):
    """Delete a tender and its associated data."""
    tender = db.query(models.Tender).filter(models.Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    file_path = os.path.join(UPLOAD_DIR, tender.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    db.delete(tender)
    db.commit()
    return {"success": True, "message": f"Tender {tender_id} deleted successfully"}
