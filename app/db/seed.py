# app/db/seed.py
from sqlalchemy.orm import Session
from app.db import models

# Adjusted to exact 2-character shorthand codes to comply with VARCHAR(2) constraints
ZIMBABWE_GEOGRAPHY = {
    "Harare": {
        "code": "HA",
        "districts": ["Harare"]   # Harare province is a metropolitan area with no further districts
    },
    "Bulawayo": {
        "code": "BY",
        "districts": ["Bulawayo"] # Bulawayo province is a metropolitan area with no further districts
    },
    "Manicaland": {
        "code": "MA",
        "districts": [
            "Buhera", "Chimanimani", "Chipinge", "Makoni", "Mutare", "Mutasa", "Nyanga"
        ]
    },
    "Midlands": {
        "code": "MI",
        "districts": [
            "Chirumhanzu", "Gokwe North", "Gokwe South", "Gweru", "Kwekwe",
            "Mberengwa", "Shurugwi", "Zvishavane"
        ]
    },
    "Mashonaland West": {
        "code": "MW",
        "districts": [
            "Chegutu", "Chinhoyi", "Hurungwe", "Kadoma", "Kariba", "Makonde", "Zvimba"
        ]
    },
    "Mashonaland East": {
        "code": "ME",
        "districts": [
            "Chikomba", "Goromonzi", "Hwedza", "Marondera", "Mudzi", "Murehwa",
            "Mutoko", "Seke", "Uzumba-Maramba-Pfungwe"
        ]
    },
    "Mashonaland Central": {
        "code": "MC",
        "districts": [
            "Bindura", "Guruve", "Mazowe", "Mbire", "Mount Darwin", "Muzarabani",
            "Rushinga", "Shamva"
        ]
    },
    "Masvingo": {
        "code": "MV",
        "districts": [
            "Bikita", "Chiredzi", "Chivi", "Gutu", "Masvingo", "Mwenezi", "Zaka"
        ]
    },
    "Matabeleland North": {
        "code": "MN",
        "districts": [
            "Binga", "Bubi", "Hwange", "Lupane", "Nkayi", "Tsholotsho", "Umguza"
        ]
    },
    "Matabeleland South": {
        "code": "MS",
        "districts": [
            "Beitbridge", "Bulilima", "Gwanda", "Insiza", "Mangwe", "Matobo", "Umzingwane"
        ]
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