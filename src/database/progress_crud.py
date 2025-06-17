from sqlalchemy.orm import Session
from fastapi import HTTPException
from . import models
import logging

logger = logging.getLogger(__name__)

# 1) Update de progresso
def update_progress(db: Session, study_id: str, update_data: dict):
    prog = db.query(models.AnalysisProgress).filter(models.AnalysisProgress.study_id == study_id).one_or_none()
    if not prog:
        raise HTTPException(status_code=404, detail="Progresso não encontrado")
    for key, value in update_data.items():
        setattr(prog, key, value)
    db.commit()
    db.refresh(prog)
    return prog

# 2) Inserção de novo registro
def create_progress(db: Session, study_id: str, user_id: str):
    prog = models.AnalysisProgress(
        study_id=study_id,
        user_id=user_id,
        status=models.StatusEnum.PROCESSING,
        current_step=0,
    )
    db.add(prog)
    db.commit()
    db.refresh(prog)
    return prog

# 3) Leitura de status
def get_progress(db: Session, study_id: str):
    prog = db.query(models.AnalysisProgress).filter(models.AnalysisProgress.study_id == study_id).one_or_none()
    if not prog:
        raise HTTPException(status_code=404, detail="Análise não encontrada")
    return prog