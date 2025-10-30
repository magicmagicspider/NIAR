from typing import List, Optional

from sqlmodel import select
from sqlmodel import Session

from app.models.device import Device


class DeviceRepository:
    def __init__(self, session: Session):
        self.session = session

    def list(self, keyword: Optional[str] = None) -> List[Device]:
        statement = select(Device)
        if keyword:
            like = f"%{keyword}%"
            statement = statement.where(
                (Device.ip.like(like))
                | (Device.hostname.like(like))
                | (Device.mac.like(like))
            )
        return list(self.session.exec(statement))

    def get(self, device_id: int) -> Optional[Device]:
        return self.session.get(Device, device_id)

    def get_by_ip(self, ip: str) -> Optional[Device]:
        statement = select(Device).where(Device.ip == ip)
        return self.session.exec(statement).first()

    def create(self, device: Device) -> Device:
        self.session.add(device)
        self.session.commit()
        self.session.refresh(device)
        return device

    def update(self, device: Device) -> Device:
        self.session.add(device)
        self.session.commit()
        self.session.refresh(device)
        return device

    def delete(self, device: Device) -> None:
        self.session.delete(device)
        self.session.commit()


