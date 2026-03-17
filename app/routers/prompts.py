from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Prompt
from app.schemas import PromptOut, PromptUpdate

router = APIRouter(tags=["prompts"])

@router.get("/prompts", response_model=list[PromptOut])
def list_prompts(industry: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Prompt)
    if industry:
        q = q.filter(Prompt.industry == industry)
    return q.all()

@router.get("/prompts/{prompt_id}", response_model=PromptOut)
def get_prompt(prompt_id: int, db: Session = Depends(get_db)):
    prompt = db.get(Prompt, prompt_id)
    if not prompt:
        raise HTTPException(404, "Prompt not found")
    return prompt

@router.patch("/prompts/{prompt_id}", response_model=PromptOut)
def update_prompt(prompt_id: int, body: PromptUpdate, db: Session = Depends(get_db)):
    prompt = db.get(Prompt, prompt_id)
    if not prompt:
        raise HTTPException(404, "Prompt not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(prompt, field, value)
    db.commit()
    db.refresh(prompt)
    return prompt
