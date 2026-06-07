from pydantic import BaseModel

from app.schemas.district import DistrictOut

class ProvinceBase(BaseModel):
    name: str

class ProvinceCreate(ProvinceBase):
    pass

class ProvinceOut(ProvinceBase):
    id: int

    class Config:
        from_attributes = True

class ProvinceTreeOut(ProvinceOut):
    districts: list['DistrictOut'] = []  # List of nested districts

    class Config:
        from_attributes = True