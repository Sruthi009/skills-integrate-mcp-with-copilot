"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path
import json
import uuid
import time
from typing import Optional
from pydantic import BaseModel

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# Load teachers from JSON
current_dir = Path(__file__).parent
teachers_file = current_dir / "teachers.json"
teachers_data = {"teachers": []}
if teachers_file.exists():
    try:
        with open(teachers_file, "r", encoding="utf-8") as f:
            teachers_data = json.load(f)
    except Exception:
        teachers_data = {"teachers": []}

# Simple in-memory admin token store: token -> {username, expiry}
active_admin_tokens = {}


class LoginPayload(BaseModel):
    username: str
    password: str


def _verify_admin_token(token: Optional[str]) -> bool:
    if not token:
        return False
    entry = active_admin_tokens.get(token)
    if not entry:
        return False
    # expiry check (allow 24h)
    if entry.get("expiry", 0) < time.time():
        del active_admin_tokens[token]
        return False
    return True


@app.post("/admin/login")
def admin_login(payload: LoginPayload):
    # check credentials against teachers_data
    for t in teachers_data.get("teachers", []):
        if t.get("username") == payload.username and t.get("password") == payload.password:
            token = uuid.uuid4().hex
            # expire in 24 hours
            active_admin_tokens[token] = {"username": payload.username, "expiry": time.time() + 24 * 3600}
            return {"token": token}
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.post("/admin/logout")
def admin_logout(admin_token: Optional[str] = None, authorization: Optional[str] = Header(None)):
    token = admin_token
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(None, 1)[1]
    if token and token in active_admin_tokens:
        del active_admin_tokens[token]
    return {"message": "logged out"}

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str, admin_token: Optional[str] = None, authorization: Optional[str] = Header(None)):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Verify admin token from either query param or Authorization header
    token = admin_token
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(None, 1)[1]

    if not _verify_admin_token(token):
        raise HTTPException(status_code=403, detail="Admin authorization required to unregister students")

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
