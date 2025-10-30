from __future__ import annotations

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class IPRequestStatus:
  PENDING = "pending"
  APPROVED = "approved"
  REJECTED = "rejected"


class IPRequest(SQLModel, table=True):
  id: Optional[int] = Field(default=None, primary_key=True)
  ip: str = Field(index=True, description="申请的IP地址")
  purpose: str = Field(description="用途")
  applicant_name: str = Field(description="申请人姓名")
  contact: str = Field(description="联系方式")
  status: str = Field(default=IPRequestStatus.PENDING, index=True)
  reviewer: Optional[str] = Field(default=None, description="审核人")
  review_comment: Optional[str] = Field(default=None, description="审核备注")
  created_at: datetime = Field(default_factory=datetime.utcnow)
  updated_at: datetime = Field(default_factory=datetime.utcnow)

  def mark_updated(self) -> None:
    self.updated_at = datetime.utcnow()


