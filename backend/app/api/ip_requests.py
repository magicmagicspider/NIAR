from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.models.db import get_session
from app.models.ip_request import IPRequest, IPRequestStatus
from app.repositories.ip_request_repo import IPRequestRepository
from app.schemas.ip_request import IPRequestCreate, IPRequestRead, IPRequestReview
from typing import List, Optional
from app.dependencies.auth import get_current_user, get_current_user_optional


router = APIRouter(prefix="/api/ip-requests", tags=["IP申请"])


@router.post("/", response_model=IPRequestRead)
def create_ip_request(payload: IPRequestCreate, session: Session = Depends(get_session)):
  repo = IPRequestRepository(session)
  obj = IPRequest(
    ip=payload.ip,
    purpose=payload.purpose,
    applicant_name=payload.applicant_name,
    contact=payload.contact,
  )
  obj = repo.create(obj)
  return IPRequestRead(
    id=obj.id,
    ip=obj.ip,
    purpose=obj.purpose,
    applicant_name=obj.applicant_name,
    contact=obj.contact,
    status=obj.status,
    created_at=obj.created_at,
  )


@router.get("/", response_model=List[IPRequestRead])
def list_ip_requests(
    status: Optional[str] = None, 
    session: Session = Depends(get_session), 
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
  """
  查询IP申请列表（可选鉴权）
  - 未登录：可查看所有申请记录
  - 已登录：可查看所有申请记录（未来可按权限过滤）
  """
  repo = IPRequestRepository(session)
  items = repo.list(status)
  return [
    IPRequestRead(
      id=o.id,
      ip=o.ip,
      purpose=o.purpose,
      applicant_name=o.applicant_name,
      contact=o.contact,
      status=o.status,
      created_at=o.created_at,
      review_comment=o.review_comment,
      reviewer=o.reviewer,
      updated_at=o.updated_at,
    ) for o in items
  ]


@router.put("/{request_id}")
def review_ip_request(request_id: int, payload: IPRequestReview, session: Session = Depends(get_session), current_user: dict = Depends(get_current_user)):
  repo = IPRequestRepository(session)
  obj = repo.get(request_id)
  if not obj:
    raise HTTPException(status_code=404, detail="IP申请不存在")
  obj.status = payload.status
  obj.review_comment = payload.review_comment
  obj.reviewer = current_user.get("username") if current_user else None
  repo.update(obj)
  return {"success": True}


