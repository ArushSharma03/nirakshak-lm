import json
from fastapi import APIRouter, Query
from app.engine.profiles import RULES_FILE
from app.engine.profiles import load_rules, select_profile
from app.schemas.analysis import Profile, ProfileRequest

router = APIRouter(prefix="/profiles", tags=["Compliance profiles"])


@router.get("/regulations")
def regulation_index(q: str = Query(default="", max_length=200)):
    """Search source records and document titles; retain scope and currency limits."""
    index = json.loads(RULES_FILE.with_name("regulation-index.json").read_text())
    query = q.strip().casefold()
    if query:
        index["sources"] = [source for source in index["sources"]
                            if query in json.dumps(source, ensure_ascii=False).casefold()]
        index["documents"] = [document for document in index["documents"]
                              if query in json.dumps(document, ensure_ascii=False).casefold()]
    return index


@router.get("/")
def list_profiles():
    return load_rules()


@router.post("/select", response_model=Profile)
def select_compliance_profile(request: ProfileRequest):
    return select_profile(request)
