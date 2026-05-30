import os
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"

def get_calendar_service():
    """
    Authenticate and return a Google Calendar API service.
    First run: opens browser for OAuth login → saves token.json.
    Subsequent runs: loads token.json silently.
    """
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def push_event(title: str, date: str, description: str = "",
               color_id: str = "1", reminder_minutes: int = 60) -> dict:
    """
    Create an all-day event in Google Calendar.
    date format: YYYY-MM-DD
    color_id: 1=blue, 2=green, 3=purple, 4=red, 5=yellow, 6=orange, 9=blueberry, 10=basil, 11=tomato
    Returns the created event dict.
    """
    service = get_calendar_service()

    event = {
        "summary": title,
        "description": description,
        "start":  {"date": date, "timeZone": "America/New_York"},
        "end":    {"date": date, "timeZone": "America/New_York"},
        "colorId": color_id,
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup",  "minutes": reminder_minutes},
                {"method": "email",  "minutes": reminder_minutes * 24},
            ],
        },
    }

    created = service.events().insert(calendarId="primary", body=event).execute()
    return created


def push_timed_event(title: str, date: str, time: str, duration_minutes: int = 60,
                     description: str = "", color_id: str = "9") -> dict:
    """
    Create a timed event (e.g. interview, networking call).
    date: YYYY-MM-DD, time: HH:MM (24h)
    """
    service = get_calendar_service()

    start_dt = datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    end_dt   = start_dt + datetime.timedelta(minutes=duration_minutes)

    event = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": "America/New_York"},
        "end":   {"dateTime": end_dt.isoformat(),   "timeZone": "America/New_York"},
        "colorId": color_id,
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 30},
                {"method": "email", "minutes": 60},
            ],
        },
    }

    created = service.events().insert(calendarId="primary", body=event).execute()
    return created


def push_all_deadlines(tasks: list[dict], applications: list[dict]) -> dict:
    """
    Bulk-push all tasks with due dates + application deadlines to Google Calendar.
    Returns counts of what was pushed.
    """
    category_color = {
        "uni_exam":        "11",  # tomato red
        "uni_assignment":  "6",   # orange
        "uni_project":     "5",   # banana yellow
        "uni_class":       "5",   # banana
        "job_interview":   "9",   # blueberry
        "job_application": "1",   # lavender blue
        "networking":      "2",   # sage green
        "general":         "8",   # graphite
    }

    pushed_tasks = 0
    pushed_apps  = 0
    errors       = []

    for t in tasks:
        if not t.get("due_date"):
            continue
        try:
            push_event(
                title=f"{'🔴 ' if t['priority'] == 'high' else ''}[{t['category'].replace('_', ' ').title()}] {t['title']}",
                date=t["due_date"],
                description=t.get("notes") or "",
                color_id=category_color.get(t["category"], "8"),
            )
            pushed_tasks += 1
        except Exception as e:
            errors.append(f"Task '{t['title']}': {e}")

    for a in applications:
        if not a.get("deadline"):
            continue
        try:
            push_event(
                title=f"⏰ App deadline: {a['role']} @ {a['company']}",
                date=a["deadline"],
                description=f"Status: {a['status']}\n{a.get('url') or ''}\n{a.get('notes') or ''}".strip(),
                color_id="9",  # blueberry for job stuff
            )
            pushed_apps += 1
        except Exception as e:
            errors.append(f"App '{a['company']}': {e}")

    return {"tasks": pushed_tasks, "applications": pushed_apps, "errors": errors}
