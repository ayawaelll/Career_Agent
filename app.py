import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from agent.orchestrator import agent
from agent.database import (
    init_db, list_applications, list_tasks,
    update_application, add_application, add_task, complete_task
)

from dotenv import load_dotenv
load_dotenv()


st.set_page_config(
    page_title="Job & Uni Agent",
    page_icon="🎯",
    layout="wide",
)

init_db()

# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🎯 Job & Uni Agent")
    st.caption("Your AI chief of staff for final semester.")
    st.divider()

    all_apps = list_applications()
    pending_tasks = list_tasks(done=False)

    col1, col2 = st.columns(2)
    col1.metric("Applications", len(all_apps))
    col2.metric("Open tasks", len(pending_tasks))

    st.divider()

    status_emoji = {
        "wishlist": "💭", "applied": "📤", "screening": "📞",
        "interview": "🎤", "offer": "🎉", "rejected": "❌"
    }

    if all_apps:
        st.markdown("**Applications**")
        for a in all_apps[:6]:
            st.caption(f"{status_emoji.get(a['status'], '•')} {a['role']} @ {a['company']}")

    st.divider()

    urgent = [t for t in pending_tasks if t["priority"] == "high"]
    if urgent:
        st.markdown("**High priority**")
        for t in urgent[:5]:
            st.caption(f"🔴 {t['title']}" + (f" — {t['due_date']}" if t.get("due_date") else ""))

    st.divider()
    st.markdown("**Quick prompts**")
    if st.button("📆 Export all to Google Calendar"):
        st.session_state.quick_prompt = "Export all my tasks and application deadlines to Google Calendar"
    if st.button("📅 What should I focus on this week?"):
        st.session_state.quick_prompt = "What should I focus on this week given my applications and tasks?"
    if st.button("😓 I'm feeling overwhelmed"):
        st.session_state.quick_prompt = "I'm feeling overwhelmed right now. Can you help me figure out what to focus on?"
    if st.button("🗑️ Clear chat"):
        st.session_state.messages = []
        st.rerun()



# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_chat, tab_kanban, tab_calendar, tab_tasks, tab_resume = st.tabs([
    "💬 Chat", "📋 Applications", "📅 Calendar", "✅ Tasks", "📄 Resume"
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — CHAT
# ══════════════════════════════════════════════════════════════════════════════
with tab_chat:
    st.markdown("### Chat")

    for msg in st.session_state.messages:
        if isinstance(msg, HumanMessage):
            with st.chat_message("user"):
                st.write(msg.content)
        elif isinstance(msg, AIMessage) and msg.content:
            with st.chat_message("assistant"):
                st.write(msg.content)

    if "quick_prompt" in st.session_state:
        prompt = st.session_state.pop("quick_prompt")
        st.session_state.messages.append(HumanMessage(content=prompt))
        with st.chat_message("user"):
            st.write(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = agent.invoke({"messages": st.session_state.messages})
                response = result["messages"][-1]
                st.write(response.content)
                st.session_state.messages = result["messages"]
        st.rerun()

    if prompt := st.chat_input("Ask me anything about your applications, tasks, or schedule..."):
        st.session_state.messages.append(HumanMessage(content=prompt))
        with st.chat_message("user"):
            st.write(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = agent.invoke({"messages": st.session_state.messages})
                response = result["messages"][-1]
                st.write(response.content)
                st.session_state.messages = result["messages"]
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — KANBAN BOARD
# ══════════════════════════════════════════════════════════════════════════════
with tab_kanban:
    st.markdown("### Application tracker")

    with st.expander("➕ Add new application"):
        c1, c2 = st.columns(2)
        new_company  = c1.text_input("Company", key="new_company")
        new_role     = c2.text_input("Role", key="new_role")
        c3, c4       = st.columns(2)
        new_status   = c3.selectbox("Status", ["wishlist", "applied", "screening", "interview", "offer", "rejected"], key="new_status")
        new_deadline = c4.text_input("Deadline (YYYY-MM-DD)", key="new_deadline")
        new_url      = st.text_input("Job URL", key="new_url")
        new_notes    = st.text_area("Notes", key="new_notes", height=80)
        if st.button("Add application", type="primary"):
            if new_company and new_role:
                add_application(
                    company=new_company, role=new_role, status=new_status,
                    url=new_url or None, notes=new_notes or None,
                    deadline=new_deadline or None
                )
                st.success(f"Added {new_role} @ {new_company}")
                st.rerun()
            else:
                st.warning("Company and role are required.")

    st.divider()

    all_apps = list_applications()
    statuses = [
        ("wishlist",  "💭 Wishlist"),
        ("applied",   "📤 Applied"),
        ("screening", "📞 Screening"),
        ("interview", "🎤 Interview"),
        ("offer",     "🎉 Offer"),
        ("rejected",  "❌ Rejected"),
    ]
    by_status = {}
    for a in all_apps:
        by_status.setdefault(a["status"], []).append(a)

    for row in [statuses[:3], statuses[3:]]:
        cols = st.columns(3)
        for col, (status_key, status_label) in zip(cols, row):
            with col:
                apps_in_col = by_status.get(status_key, [])
                st.markdown(f"**{status_label}** `{len(apps_in_col)}`")
                for app in apps_in_col:
                    with st.container(border=True):
                        st.markdown(f"**{app['role']}**")
                        st.caption(f"🏢 {app['company']}")
                        if app.get("deadline"):
                            st.caption(f"⏰ Deadline: {app['deadline']}")
                        if app.get("notes"):
                            notes_preview = app['notes'][:60] + ("..." if len(app['notes']) > 60 else "")
                            st.caption(f"📝 {notes_preview}")
                        if app.get("url"):
                            st.markdown(f"[View posting]({app['url']})")
                        new_s = st.selectbox(
                            "Move to",
                            ["wishlist", "applied", "screening", "interview", "offer", "rejected"],
                            index=["wishlist", "applied", "screening", "interview", "offer", "rejected"].index(app["status"]),
                            key=f"status_{app['id']}"
                        )
                        if new_s != app["status"]:
                            update_application(app["id"], status=new_s)
                            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — CALENDAR
# ══════════════════════════════════════════════════════════════════════════════
with tab_calendar:
    st.markdown("### Calendar")

    # Google Calendar export
    gcal_col1, gcal_col2 = st.columns([3, 1])
    gcal_col1.caption("Push all your deadlines and tasks to Google Calendar in one click.")
    if gcal_col2.button("📆 Export to Google Calendar", type="primary"):
        with st.spinner("Connecting to Google Calendar..."):
            try:
                from agent.gcal import push_all_deadlines
                all_t = list_tasks(done=False)
                all_a = list_applications()
                result = push_all_deadlines(all_t, all_a)
                st.success(f"Exported {result['tasks']} tasks and {result['applications']} application deadlines to Google Calendar!")
                if result["errors"]:
                    st.warning(f"Some failed: {'; '.join(result['errors'])}")
            except Exception as e:
                st.error(f"Export failed: {e}. Make sure credentials.json is in your project folder.")
    st.divider()

    all_tasks_cal = list_tasks(done=False)
    all_apps_cal  = list_applications()

    category_colors = {
        "uni_exam":        "#E24B4A",
        "uni_assignment":  "#D85A30",
        "uni_project":     "#BA7517",
        "uni_class":       "#EF9F27",
        "job_interview":   "#534AB7",
        "job_application": "#378ADD",
        "networking":      "#1D9E75",
        "general":         "#888780",
    }

    events = []
    for t in all_tasks_cal:
        if t.get("due_date"):
            events.append({
                "title": t["title"],
                "start": t["due_date"],
                "end":   t["due_date"],
                "color": category_colors.get(t["category"], "#888780"),
            })
    for a in all_apps_cal:
        if a.get("deadline"):
            events.append({
                "title": f"⏰ {a['role']} @ {a['company']}",
                "start": a["deadline"],
                "end":   a["deadline"],
                "color": "#534AB7",
            })

    # Legend
    leg = st.columns(4)
    leg[0].markdown('<span style="color:#E24B4A">● Exam</span> &nbsp; <span style="color:#D85A30">● Assignment</span>', unsafe_allow_html=True)
    leg[1].markdown('<span style="color:#BA7517">● Project</span> &nbsp; <span style="color:#EF9F27">● Class</span>', unsafe_allow_html=True)
    leg[2].markdown('<span style="color:#534AB7">● Interview / deadline</span>', unsafe_allow_html=True)
    leg[3].markdown('<span style="color:#1D9E75">● Networking</span>', unsafe_allow_html=True)
    st.divider()

    try:
        from streamlit_calendar import calendar as st_calendar
        st_calendar(
            events=events,
            options={
                "headerToolbar": {
                    "left": "prev,next today",
                    "center": "title",
                    "right": "dayGridMonth,timeGridWeek,listWeek"
                },
                "initialView": "dayGridMonth",
                "height": 600,
            },
            key="main_calendar"
        )
    except ImportError:
        st.info("💡 For a visual calendar, run: `pip install streamlit-calendar` then restart.\n\nShowing list view for now:")
        if not events:
            st.caption("No upcoming deadlines yet.")
        else:
            for e in sorted(events, key=lambda x: x["start"]):
                st.markdown(
                    f'<span style="color:{e["color"]}; font-size:16px">●</span> '
                    f'**{e["start"]}** — {e["title"]}',
                    unsafe_allow_html=True
                )

    st.divider()
    with st.expander("➕ Add deadline"):
        tc1, tc2   = st.columns(2)
        t_title    = tc1.text_input("Title", key="cal_title")
        t_due      = tc2.text_input("Due date (YYYY-MM-DD)", key="cal_due")
        tc3, tc4   = st.columns(2)
        t_category = tc3.selectbox("Category", list(category_colors.keys()), key="cal_cat")
        t_priority = tc4.selectbox("Priority", ["high", "medium", "low"], key="cal_pri")
        if st.button("Add to calendar", type="primary"):
            if t_title:
                add_task(t_title, t_category, t_priority, t_due or None)
                st.success(f"Added: {t_title}")
                st.rerun()
            else:
                st.warning("Title is required.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — TASKS
# ══════════════════════════════════════════════════════════════════════════════
with tab_tasks:
    st.markdown("### All tasks")

    filter_cat = st.selectbox("Filter by category", [
        "all", "uni_exam", "uni_assignment", "uni_project", "uni_class",
        "job_interview", "job_application", "networking", "general"
    ], key="task_filter")

    cat_arg   = None if filter_cat == "all" else filter_cat
    tasks     = list_tasks(category=cat_arg, done=False)
    done_tasks = list_tasks(category=cat_arg, done=True)

    priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}

    if not tasks:
        st.caption("No pending tasks. Add some via chat or the calendar tab.")
    else:
        for t in tasks:
            ca, cb, cc = st.columns([5, 2, 1])
            due_str = f" · due {t['due_date']}" if t.get("due_date") else ""
            ca.markdown(
                f"{priority_icon.get(t['priority'], '⚪')} **{t['title']}**  \n"
                f"<span style='font-size:12px;color:#888'>{t['category']}{due_str}</span>",
                unsafe_allow_html=True
            )
            cb.caption(t.get("notes") or "")
            if cc.button("✓", key=f"done_{t['id']}"):
                complete_task(t["id"])
                st.rerun()

    if done_tasks:
        with st.expander(f"Completed ({len(done_tasks)})"):
            for t in done_tasks:
                st.caption(f"✓ {t['title']}")

    st.divider()
    with st.expander("➕ Add task manually"):
        m1, m2  = st.columns(2)
        m_title = m1.text_input("Title", key="manual_title")
        m_due   = m2.text_input("Due date (YYYY-MM-DD)", key="manual_due")
        m3, m4  = st.columns(2)
        m_cat   = m3.selectbox("Category", [
            "uni_exam", "uni_assignment", "uni_project", "uni_class",
            "job_interview", "job_application", "networking", "general"
        ], key="manual_cat")
        m_pri   = m4.selectbox("Priority", ["high", "medium", "low"], key="manual_pri")
        if st.button("Add task", type="primary", key="manual_add"):
            if m_title:
                add_task(m_title, m_cat, m_pri, m_due or None)
                st.success(f"Added: {m_title}")
                st.rerun()
            else:
                st.warning("Title is required.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — RESUME TAILORING
# ══════════════════════════════════════════════════════════════════════════════
with tab_resume:
    st.markdown("### Resume tailoring")
    st.caption("Upload your master resume once, then paste any job description to get tailored bullets.")

    # ── Step 1: ingest master resume ─────────────────────────────────────────
    st.markdown("#### Step 1 — Upload master resume")
    try:
        from agent.resume_rag import resume_is_ingested, ingest_resume
        already_ingested = resume_is_ingested()
    except Exception:
        already_ingested = False

    if already_ingested:
        st.success("Master resume is loaded. Upload a new file to replace it.")

    uploaded_pdf = st.file_uploader(
        "Master resume (PDF)",
        type="pdf",
        help="Upload once. Re-upload any time to update.",
        key="resume_upload",
    )
    if uploaded_pdf is not None:
        if st.button("Ingest resume", type="primary", key="ingest_btn"):
            import tempfile, os
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_pdf.read())
                tmp_path = tmp.name
            try:
                with st.spinner("Reading and embedding resume..."):
                    n = ingest_resume(tmp_path)
                st.success(f"Ingested {n} sections from your resume.")
            except Exception as e:
                st.error(f"Ingestion failed: {e}")
            finally:
                os.unlink(tmp_path)

    st.divider()

    # ── Step 2: tailor to a JD ───────────────────────────────────────────────
    st.markdown("#### Step 2 — Paste job description")
    jd_input = st.text_area(
        "Job description",
        height=220,
        placeholder="Paste the full job description here...",
        key="jd_input",
    )
    if st.button("Generate tailored bullets", type="primary", key="tailor_btn"):
        if not jd_input.strip():
            st.warning("Paste a job description first.")
        elif not resume_is_ingested():
            st.warning("Upload and ingest your resume first (Step 1).")
        else:
            with st.spinner("Retrieving relevant experience and rewriting bullets..."):
                try:
                    from agent.resume_rag import run_tailoring_pipeline
                    result = run_tailoring_pipeline(jd_input)
                    st.session_state["tailored_output"] = result
                except Exception as e:
                    st.error(f"Tailoring failed: {e}")

    if "tailored_output" in st.session_state:
        st.divider()
        st.markdown("#### Tailored bullets")
        st.markdown(st.session_state["tailored_output"])
        st.download_button(
            label="Copy as .txt",
            data=st.session_state["tailored_output"],
            file_name="tailored_bullets.txt",
            mime="text/plain",
        )
