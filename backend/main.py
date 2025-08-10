from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import json, os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = FastAPI(title="Symptom-Check Pro API")

# CORS (welche Webseiten dürfen API anfragen)
origins_env = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins_env,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Provider laden
PROVIDERS: List[Dict] = []
try:
    with open(os.path.join(os.path.dirname(__file__), "providers.json"), "r", encoding="utf-8") as f:
        PROVIDERS = json.load(f)
except FileNotFoundError:
    print("providers.json nicht gefunden.")

# Datenmodelle
class Message(BaseModel):
    role: str
    content: str

class StartPayload(BaseModel):
    symptom_hint: Optional[str] = None

class ReplyPayload(BaseModel):
    session_id: Optional[str] = None
    history: List[Message]
    consent: bool = False

class SearchQuery(BaseModel):
    specialty: str
    city: Optional[str] = None
    urgency: Optional[str] = None

class BookIntent(BaseModel):
    provider_id: str
    reason_key: str
    note: Optional[str] = None

# Prompts
SYSTEM_PROMPT = (
    "Du bist ein klinischer Triage-Assistent in Deutschland. Du stellst KEINE Diagnosen.\n"
    "Ziele: 1) Max. 8 Fragen, um Dringlichkeit (A/B/C) und Fachrichtung zu bestimmen.\n"
    "2) Erkenne Notfälle und rate zu 112.\n"
    "3) Gib am Ende Triage-Stufe, Fachrichtung und Kurz-Zusammenfassung.\n"
)

DISCLAIMER = (
    "Hinweis: Dies ersetzt keine ärztliche Behandlung. Bei Gefahr 112 anrufen.\n"
    "Sind Sie einverstanden? (Ja/Nein)"
)

# Funktionen
def build_booking_link(provider: Dict, reason_key: str) -> str:
    url = provider.get("booking_url", "").rstrip("/")
    reason = provider.get("reason_map", {}).get(reason_key)
    if provider.get("booking_vendor") == "doctolib" and reason:
        url = f"{url}?reason={reason}"
    return url

# Endpunkte
@app.get("/")
def root():
    return {"ok": True}

@app.post("/symptom/start")
def symptom_start(payload: StartPayload):
    return {"session_id": "demo", "reply": DISCLAIMER}

@app.post("/symptom/reply")
def symptom_reply(payload: ReplyPayload):
    if not payload.consent:
        return {"reply": "Bitte bestätigen Sie mit 'Ja'."}
    if not client:
        return {"reply": "Verstanden. Können Sie Ihre Schmerzstärke (0–10) angeben?"}
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + [m.model_dump() for m in payload.history]
    resp = client.chat.completions.create(model="gpt-4o-mini", messages=messages, temperature=0.2)
    return {"reply": resp.choices[0].message.content}

@app.post("/providers/search")
def providers_search(q: SearchQuery):
    results = [p for p in PROVIDERS if p.get("specialty") == q.specialty and p.get("visible")]
    if q.city:
        results = [p for p in results if p.get("city", "").lower() == q.city.lower()]
    return {"providers": results}

@app.post("/book-intent")
def book_intent(data: BookIntent):
    provider = next((p for p in PROVIDERS if p.get("id") == data.provider_id), None)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider nicht gefunden")
    link = build_booking_link(provider, data.reason_key)
    return {"booking_url": link}
