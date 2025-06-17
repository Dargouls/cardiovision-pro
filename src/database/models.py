from sqlalchemy import Column, String, Integer, Enum
from .database import Base
import enum

# Opcional: usar Enum para status
class StatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class AnalysisProgress(Base):
    __tablename__ = "analysis_progress"  # nome da tabela existente no Postgres

    study_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)
    status = Column(Enum(StatusEnum), nullable=False)
    current_step = Column(Integer, nullable=False)