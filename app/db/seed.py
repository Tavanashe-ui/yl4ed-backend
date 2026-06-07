# app/db/seed.py
from sqlalchemy.orm import Session
from app.db import models

# Adjusted to exact 2-character shorthand codes to comply with VARCHAR(2) constraints
ZIMBABWE_GEOGRAPHY = {
    "Harare": {
        "code": "HA",
        "districts": ["Harare Central", "Chitungwiza", "Epworth", "Highfield", "Mbare", "Seke"]
    },
    "Bulawayo": {
        "code": "BY",
        "districts": ["Bulawayo Central", "Mzilikazi", "Reigate", "Khami"]
    },
    "Manicaland": {
        "code": "MA",
        "districts": ["Mutare", "Rusape", "Nyanga", "Chipinge", "Chimanimani", "Buhera", "Mutasa"]
    },
    "Midlands": {
        "code": "MI",
        "districts": ["Gweru", "Kwekwe", "Shurugwi", "Zvishavane", "Mberengwa", "Gokwe North", "Gokwe South"]
    },
    "Mashonaland West": {
        "code": "MW",
        "districts": ["Chinhoyi", "Kadoma", "Kariba", "Chegutu", "Hurungwe", "Makonde", "Zvimba"]
    },
    "Mashonaland East": {
        "code": "ME",
        "districts": ["Marondera", "Goromonzi", "Murewa", "Mutoko", "Seke", "Wedza", "Mudzi"]
    },
    "Mashonaland Central": {
        "code": "MC",
        "districts": ["Bindura", "Mazowe", "Mount Darwin", "Guruve", "Shamva", "Rushinga", "Muzarabani"]
    },
    "Masvingo": {
        "code": "MV",
        "districts": ["Masvingo", "Chiredzi", "Chivi", "Bikita", "Gutu", "Mwenezi", "Zaka"]
    },
    "Matabeleland North": {
        "code": "MN",
        "districts": ["Lupane", "Hwange", "Binga", "Tsholotsho", "Nkayi", "Bubi", "Umguza"]
    },
    "Matabeleland South": {
        "code": "MS",
        "districts": ["Gwanda", "Beitbridge", "Plumtree", "Insiza", "Matobo", "Filabusi", "Mangwe"]
    }
}

def seed_geography_data(db: Session):
    """Populates provinces and districts if they don't already exist."""
    print("Checking database geographic reference data...")
    
    for province_name, data in ZIMBABWE_GEOGRAPHY.items():
        province_code = data["code"]
        districts = data["districts"]
        
        # Check or create province
        db_province = db.query(models.Province).filter(models.Province.name == province_name).first()
        if not db_province:
            db_province = models.Province(name=province_name, code=province_code)
            db.add(db_province)
            db.commit()
            db.refresh(db_province)
            print(f"-> Seeded Province: {province_name} ({province_code})")

        # Check or create districts within this province
        for district_name in districts:
            db_district = db.query(models.District).filter(
                models.District.name == district_name,
                models.District.province_id == db_province.id
            ).first()
            if not db_district:
                db_district = models.District(name=district_name, province_id=db_province.id)
                db.add(db_district)
                print(f"   + Seeded District: {district_name}")
                
    db.commit()
    print("Geographic initialization complete.")