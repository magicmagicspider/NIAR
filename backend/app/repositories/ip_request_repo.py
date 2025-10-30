from __future__ import annotations

from typing import List, Optional
from sqlmodel import Session, select
from app.models.ip_request import IPRequest


class IPRequestRepository:
  def __init__(self, session: Session) -> None:
    self.session = session

  def create(self, obj: IPRequest) -> IPRequest:
    self.session.add(obj)
    self.session.commit()
    self.session.refresh(obj)
    return obj

  def list(self, status: Optional[str] = None) -> List[IPRequest]:
    statement = select(IPRequest)
    if status:
      statement = statement.where(IPRequest.status == status)
    statement = statement.order_by(IPRequest.created_at.desc())
    return list(self.session.exec(statement).all())

  def get(self, id_: int) -> Optional[IPRequest]:
    return self.session.get(IPRequest, id_)

  def update(self, obj: IPRequest) -> IPRequest:
    obj.mark_updated()
    self.session.add(obj)
    self.session.commit()
    self.session.refresh(obj)
    return obj


