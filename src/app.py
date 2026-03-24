"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import os
from pathlib import Path
import json
import secrets
from datetime import datetime, timezone
from typing import Optional

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")


def load_teacher_credentials() -> dict:
    """Load teacher credentials from local JSON file."""
    teachers_file = current_dir / "teachers.json"
    with teachers_file.open("r", encoding="utf-8") as file:
        return json.load(file)


teacher_credentials = load_teacher_credentials()
teacher_sessions: dict[str, str] = {}


class LoginRequest(BaseModel):
    username: str
    password: str


class AdvisorRequestCreate(BaseModel):
    student_email: str


def require_teacher_token(token: Optional[str]) -> str:
    if not token or token not in teacher_sessions:
        raise HTTPException(status_code=401, detail="Teacher authentication required")
    return teacher_sessions[token]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

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

# In-memory club advisor workflow data
teacher_clubs = {
    "mrs_clark": ["Chess Club", "Drama Club", "Debate Team"],
    "mr_chen": ["Math Club", "Programming Class"],
    "ms_rivera": ["Gym Class", "Soccer Team", "Basketball Team", "Art Club"]
}

club_advisors = {
    "Chess Club": "michael@mergington.edu",
    "Programming Class": "sophia@mergington.edu",
    "Gym Class": "john@mergington.edu",
    "Soccer Team": "liam@mergington.edu",
    "Basketball Team": "ava@mergington.edu",
    "Art Club": "amelia@mergington.edu",
    "Drama Club": "ella@mergington.edu",
    "Math Club": "james@mergington.edu",
    "Debate Team": "charlotte@mergington.edu"
}

advisor_requests = []
next_advisor_request_id = 1


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    result = {}
    for club_name, details in activities.items():
        club_data = details.copy()
        club_data["advisor"] = club_advisors.get(club_name)
        result[club_name] = club_data
    return result


@app.post("/clubs/{club_name}/advisor-requests")
def submit_advisor_request(club_name: str, payload: AdvisorRequestCreate):
    """Submit a request to become a club advisor."""
    global next_advisor_request_id

    if club_name not in activities:
        raise HTTPException(status_code=404, detail="Club not found")

    for existing_request in advisor_requests:
        if (
            existing_request["club_name"] == club_name
            and existing_request["student_email"] == payload.student_email
            and existing_request["status"] == "pending"
        ):
            raise HTTPException(
                status_code=400,
                detail="A pending advisor request already exists for this student and club"
            )

    request_record = {
        "id": next_advisor_request_id,
        "club_name": club_name,
        "student_email": payload.student_email,
        "status": "pending",
        "requested_at": utc_now_iso(),
        "resolved_at": None,
        "resolved_by": None
    }
    next_advisor_request_id += 1
    advisor_requests.append(request_record)
    return request_record


@app.get("/advisor-requests/pending")
def list_pending_advisor_requests(
    x_teacher_token: Optional[str] = Header(default=None, alias="X-Teacher-Token")
):
    """List pending advisor requests for clubs supervised by the logged-in teacher."""
    teacher_username = require_teacher_token(x_teacher_token)
    managed_clubs = set(teacher_clubs.get(teacher_username, []))

    return [
        request_record
        for request_record in advisor_requests
        if request_record["status"] == "pending" and request_record["club_name"] in managed_clubs
    ]


def get_request_by_id(request_id: int) -> dict:
    for request_record in advisor_requests:
        if request_record["id"] == request_id:
            return request_record
    raise HTTPException(status_code=404, detail="Advisor request not found")


def ensure_teacher_can_manage_request(teacher_username: str, request_record: dict) -> None:
    managed_clubs = set(teacher_clubs.get(teacher_username, []))
    if request_record["club_name"] not in managed_clubs:
        raise HTTPException(status_code=403, detail="You can only manage requests for your clubs")


@app.post("/advisor-requests/{request_id}/approve")
def approve_advisor_request(
    request_id: int,
    x_teacher_token: Optional[str] = Header(default=None, alias="X-Teacher-Token")
):
    teacher_username = require_teacher_token(x_teacher_token)
    request_record = get_request_by_id(request_id)
    ensure_teacher_can_manage_request(teacher_username, request_record)

    if request_record["status"] != "pending":
        raise HTTPException(status_code=400, detail="Only pending requests can be approved")

    request_record["status"] = "approved"
    request_record["resolved_by"] = teacher_username
    request_record["resolved_at"] = utc_now_iso()
    club_advisors[request_record["club_name"]] = request_record["student_email"]

    return {
        "message": "Advisor request approved",
        "request": request_record,
        "club_advisor": {
            "club_name": request_record["club_name"],
            "advisor": club_advisors[request_record["club_name"]]
        }
    }


@app.post("/advisor-requests/{request_id}/reject")
def reject_advisor_request(
    request_id: int,
    x_teacher_token: Optional[str] = Header(default=None, alias="X-Teacher-Token")
):
    teacher_username = require_teacher_token(x_teacher_token)
    request_record = get_request_by_id(request_id)
    ensure_teacher_can_manage_request(teacher_username, request_record)

    if request_record["status"] != "pending":
        raise HTTPException(status_code=400, detail="Only pending requests can be rejected")

    request_record["status"] = "rejected"
    request_record["resolved_by"] = teacher_username
    request_record["resolved_at"] = utc_now_iso()

    return {
        "message": "Advisor request rejected",
        "request": request_record
    }


@app.post("/auth/login")
def teacher_login(credentials: LoginRequest):
    expected_password = teacher_credentials.get(credentials.username)
    if expected_password != credentials.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = secrets.token_urlsafe(24)
    teacher_sessions[token] = credentials.username
    return {"token": token, "username": credentials.username}


@app.post("/auth/logout")
def teacher_logout(x_teacher_token: Optional[str] = Header(default=None, alias="X-Teacher-Token")):
    if x_teacher_token in teacher_sessions:
        teacher_sessions.pop(x_teacher_token)
    return {"message": "Logged out"}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    email: str,
    x_teacher_token: Optional[str] = Header(default=None, alias="X-Teacher-Token")
):
    """Sign up a student for an activity"""
    require_teacher_token(x_teacher_token)

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
def unregister_from_activity(
    activity_name: str,
    email: str,
    x_teacher_token: Optional[str] = Header(default=None, alias="X-Teacher-Token")
):
    """Unregister a student from an activity"""
    require_teacher_token(x_teacher_token)

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

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
