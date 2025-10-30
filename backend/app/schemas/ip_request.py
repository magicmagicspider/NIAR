from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class IPRequestCreate(BaseModel):
  ip: str = Field(..., description="申请的IP地址")
  purpose: str
  applicant_name: str
  contact: str


class IPRequestRead(BaseModel):
  id: int
  ip: str
  purpose: str
  applicant_name: str
  contact: str
  status: str
  created_at: datetime
  review_comment: Optional[str] = None
  reviewer: Optional[str] = None
  updated_at: Optional[datetime] = None


class IPRequestReview(BaseModel):
  status: Literal['approved', 'rejected']
  review_comment: Optional[str] = None


