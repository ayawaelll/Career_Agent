from langchain_core.tools import tool
from agent.database import (
    add_application, find_application, update_application, list_applications,
    add_task, complete_task, list_tasks
)


# ── Job Tracker Tools ─────────────────────────────────────────────────────────

@tool
def track_application(company: str, role: str, status: str = "applied",
                      url: str = None, notes: str = None,
                      date_applied: str = None, deadline: str = None) -> str:
    """
    Add a new job application to the tracker.
    Status options: wishlist, applied, screening, interview, offer, rejected.
    Date format: YYYY-MM-DD.
    """
    existing = find_application(company, role)
    if existing:
        return (
            f"Application already exists — #{existing['id']}: {existing['role']} at {existing['company']} "
            f"(status: {existing['status']}). Use update_application_status to modify it."
        )
    app_id = add_application(company, role, status, url, notes, date_applied, deadline)
    return f"Added application #{app_id}: {role} at {company} (status: {status})"


@tool
def update_application_status(app_id: int, status: str, notes: str = None) -> str:
    """
    Update the status of a job application by its ID.
    Status options: wishlist, applied, screening, interview, offer, rejected.
    Optionally add notes (e.g. 'Got a call from recruiter - call on Friday').
    """
    kwargs = {"status": status}
    if notes:
        kwargs["notes"] = notes
    success = update_application(app_id, **kwargs)
    if success:
        return f"Updated application #{app_id} to status: {status}"
    return f"Could not find application #{app_id}"


@tool
def get_applications(status: str = None) -> str:
    """
    List job applications. Optionally filter by status.
    Status options: wishlist, applied, screening, interview, offer, rejected.
    Leave status empty to get all applications.
    """
    apps = list_applications(status)
    if not apps:
        return "No applications found."
    lines = []
    for a in apps:
        line = f"#{a['id']} | {a['role']} @ {a['company']} | {a['status'].upper()}"
        if a.get("deadline"):
            line += f" | deadline: {a['deadline']}"
        if a.get("notes"):
            line += f" | notes: {a['notes']}"
        lines.append(line)
    return "\n".join(lines)


# ── Planner Tools ─────────────────────────────────────────────────────────────

@tool
def add_planner_task(title: str, category: str = "general",
                     priority: str = "medium", due_date: str = None,
                     notes: str = None) -> str:
    """
    Add a task to the planner.
    Categories: uni_exam, uni_assignment, uni_project, uni_class, 
                job_application, job_interview, networking, general.
    Priority: high, medium, low.
    Due date format: YYYY-MM-DD.
    """
    task_id = add_task(title, category, priority, due_date, notes)
    return f"Added task #{task_id}: '{title}' ({category}, {priority} priority)"


@tool
def get_tasks(category: str = None) -> str:
    """
    List all pending tasks, optionally filtered by category.
    Categories: uni_exam, uni_assignment, uni_project, uni_class,
                job_application, job_interview, networking, general.
    """
    tasks = list_tasks(category=category, done=False)
    if not tasks:
        return "No pending tasks found."
    lines = []
    for t in tasks:
        line = f"#{t['id']} | [{t['priority'].upper()}] {t['title']} | {t['category']}"
        if t.get("due_date"):
            line += f" | due: {t['due_date']}"
        lines.append(line)
    return "\n".join(lines)


@tool
def mark_task_done(task_id: int) -> str:
    """Mark a planner task as complete by its ID."""
    complete_task(task_id)
    return f"Task #{task_id} marked as done."


def get_tools():
    return [
        track_application,
        update_application_status,
        get_applications,
        add_planner_task,
        get_tasks,
        mark_task_done,
        add_to_google_calendar,
        schedule_interview_on_calendar,
        tailor_resume_to_jd,
    ]


@tool
def add_to_google_calendar(title: str, date: str, description: str = "") -> str:
    """
    Add an all-day event or deadline to the user's Google Calendar.
    Use for exam dates, assignment deadlines, application deadlines.
    date format: YYYY-MM-DD.
    """
    try:
        from agent.gcal import push_event
        event = push_event(title=title, date=date, description=description)
        return f"Added to Google Calendar: '{title}' on {date}. Link: {event.get('htmlLink', 'created')}"
    except Exception as e:
        return f"Could not add to Google Calendar: {e}"


@tool
def schedule_interview_on_calendar(company: str, role: str, date: str,
                                    time: str, duration_minutes: int = 60) -> str:
    """
    Schedule a timed interview event in Google Calendar.
    date: YYYY-MM-DD, time: HH:MM in 24h format (e.g. 14:00 for 2pm).
    """
    try:
        from agent.gcal import push_timed_event
        title = f"Interview: {role} @ {company}"
        desc  = f"Interview for {role} position at {company}"
        event = push_timed_event(title=title, date=date, time=time,
                                  duration_minutes=duration_minutes, description=desc)
        return f"Scheduled on Google Calendar: {title} on {date} at {time}. Link: {event.get('htmlLink', 'created')}"
    except Exception as e:
        return f"Could not schedule interview: {e}"


@tool
def tailor_resume_to_jd(job_description: str) -> str:
    """
    Tailor resume bullet points to a specific job description using RAG.
    Retrieves the most relevant sections from the ingested master resume and
    rewrites them to match the JD's required skills and keywords.
    The user must upload their master resume PDF in the Resume tab first.
    """
    from agent.resume_rag import resume_is_ingested, run_tailoring_pipeline
    if not resume_is_ingested():
        return (
            "No resume found in the vector store. "
            "Please upload your master resume PDF in the Resume tab first."
        )
    return run_tailoring_pipeline(job_description)
