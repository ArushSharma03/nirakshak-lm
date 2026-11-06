from fastapi import APIRouter
from app.engine.profiles import load_rules, select_profile
from app.schemas.analysis import Profile, ProfileRequest

router = APIRouter(prefix="/profiles", tags=["Compliance profiles"])


@router.get("/")
def list_profiles():
    return load_rules()


@router.post("/select", response_model=Profile)
def select_compliance_profile(request: ProfileRequest):
    return select_profile(request)
