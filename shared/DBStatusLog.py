import os
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

raw_url = os.environ.get("POSTGRES_URL")
DB_URL = raw_url.replace("postgres://", "postgresql://", 1) if raw_url else None
eng = create_engine(DB_URL) if DB_URL else None
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=eng) if eng else None
Base = declarative_base()

class DBMember(Base):
    __tablename__ = "lab_members_v2" 
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    status = Column(String, default="帰宅")
    is_admin = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.now)
    order_index = Column(Integer, default=0)

class DBSettings(Base):
    __tablename__ = "lab_settings_v2"
    id = Column(Integer, primary_key=True)
    show_duration = Column(Boolean, default=True)
    status_list = Column(String, default="在席,食事,外出,帰宅") 

class DBStatusLog(Base):
    __tablename__ = "lab_status_logs"
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, index=True)
    status = Column(String)
    timestamp = Column(DateTime, default=datetime.now)

if eng:
    Base.metadata.create_all(bind=eng) # これが新しい表を自動で作ってくれます

class MemberCreate(BaseModel):
    name: str
    is_admin: bool = False

class StatusUpdate(BaseModel):
    id: int
    status: str

class SettingUpdate(BaseModel):
    show_duration: bool
    status_list: str

class MemberReorder(BaseModel):
    ordered_ids: list[int]

def get_db():
    if SessionLocal is None: return
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()