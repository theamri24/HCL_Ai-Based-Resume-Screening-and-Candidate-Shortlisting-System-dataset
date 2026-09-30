"""
app.py
Main application - Login + Dashboard
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from passlib.hash import bcrypt

from services.database import fetch_one, fetch_all, execute

st.set_page_config(
    page_title="Resume Screening Platform",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------
# Bootstrap model + seed data on first cloud run
# ------------------------------------------------------------
try:
    from services.bootstrap_model import ensure_model
    ensure_model()
except Exception:
    pass

try:
    from services.seed_data import seed
    seed()
except Exception:
    pass

# ------------------------------------------------------------
# Load custom CSS
# ------------------------------------------------------------
css_path = BASE_DIR / "assets" / "style.css"
if css_path.exists():
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ------------------------------------------------------------
# Session state
# ------------------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None


# ------------------------------------------------------------
# Admin bootstrap
# ------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def ensure_admin_user():
    try:
        user = fetch_one(
            "SELECT id, password_hash FROM users WHERE email = :e",
            {"e": "admin@resume.com"},
        )
        if user and user.get("password_hash"):
            return True

        new_hash = bcrypt.hash("admin123")
        if user:
            execute(
                "UPDATE users SET password_hash = :p WHERE email = :e",
                {"p": new_hash, "e": "admin@resume.com"},
            )
        else:
            execute(
                """INSERT INTO users (name, email, password_hash, role)
                   VALUES (:n, :e, :p, :r)""",
                {"n": "Admin User", "e": "admin@resume.com",
                 "p": new_hash, "r": "admin"},
            )
        return True
    except Exception:
        return False


def do_login(email: str, password: str) -> bool:
    user = fetch_one(
        """SELECT id, name, email, password_hash, role
           FROM users WHERE email = :e AND is_active = 1""",
        {"e": email.strip().lower()},
    )
    if not user:
        return False
    try:
        if bcrypt.verify(password, user["password_hash"]):
            st.session_state.logged_in = True
            st.session_state.user = {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"],
            }
            return True
    except Exception:
        return False
    return False


def login_screen():
    col1, col2, col3 = st.columns([1, 1.05, 1])
    with col2:
        st.markdown('<div style="height: 8vh;"></div>', unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            st.markdown(
                """
                <div class="brand-mark">RS</div>
                <div class="login-title">Resume Screening</div>
                <div class="login-subtitle">Sign in to recruiter console</div>
                """,
                unsafe_allow_html=True,
            )

            email = st.text_input("Email address", placeholder="you@company.com")
            password = st.text_input("Password", type="password",
                                     placeholder="Enter your password")
            submit = st.form_submit_button("Sign in", use_container_width=True)

            st.markdown(
                """
                <div class="login-footer-divider"></div>
                <div class="login-hint">
                    <div class="login-hint-label">Demo access</div>
                    <code>admin@resume.com</code> &nbsp;/&nbsp; <code>admin123</code>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if submit:
            if not email or not password:
                st.error("Email and password are required.")
            elif do_login(email, password):
                st.rerun()
            else:
                st.error("Invalid credentials. Please try again.")


# ------------------------------------------------------------
# Charts
# ------------------------------------------------------------
def chart_decision_breakdown(shortlisted, review, rejected):
    total = shortlisted + review + rejected
    data = pd.DataFrame({
        "Decision": ["Shortlisted", "In Review", "Rejected"],
        "Count": [shortlisted, review, rejected],
        "Color": ["#15803d", "#b45309", "#b91c1c"],
    })

    fig = go.Figure()
    for _, row in data.iterrows():
        pct = (row["Count"] / total * 100) if total else 0
        fig.add_trace(go.Bar(
            y=[row["Decision"]],
            x=[row["Count"]],
            orientation="h",
            marker=dict(color=row["Color"], line=dict(width=0)),
            text=f"  {row['Count']}  ({pct:.0f}%)",
            textposition="outside",
            textfont=dict(size=13, color="#0f172a", family="Inter"),
            hovertemplate=(
                f"<b>{row['Decision']}</b><br>"
                f"Count: {row['Count']}<br>"
                f"Share: {pct:.1f}%<extra></extra>"
            ),
            width=0.55,
        ))

    max_count = max(data["Count"]) if len(data) else 1
    fig.update_layout(
        height=260,
        margin=dict(l=10, r=60, t=10, b=10),
        xaxis=dict(
            showgrid=True, gridcolor="#f1f5f9", zeroline=False,
            showticklabels=False,
            range=[0, max_count * 1.35 if total else 1],
        ),
        yaxis=dict(
            showgrid=False, zeroline=False,
            tickfont=dict(size=13, color="#334155", family="Inter"),
        ),
        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
        showlegend=False, bargap=0.4,
    )
    return fig


def chart_score_buckets(df_scores):
    ranges = [
        ("Excellent (75-100)", 75, 101, "#15803d"),
        ("Good (50-74)", 50, 75, "#1e40af"),
        ("Fair (25-49)", 25, 50, "#b45309"),
        ("Poor (0-24)", 0, 25, "#b91c1c"),
    ]

    counts, labels, colors = [], [], []
    for label, lo, hi, color in ranges:
        cnt = len(df_scores[(df_scores >= lo) & (df_scores < hi)])
        labels.append(label)
        counts.append(cnt)
        colors.append(color)

    fig = go.Figure()
    for label, cnt, color in zip(labels, counts, colors):
        fig.add_trace(go.Bar(
            y=[label],
            x=[cnt],
            orientation="h",
            marker=dict(color=color, line=dict(width=0)),
            text=f"  {cnt}",
            textposition="outside",
            textfont=dict(size=13, color="#0f172a", family="Inter"),
            hovertemplate=f"<b>{label}</b><br>Candidates: {cnt}<extra></extra>",
            width=0.6,
        ))

    max_count = max(counts) if counts else 1
    fig.update_layout(
        height=260,
        margin=dict(l=10, r=50, t=10, b=10),
        xaxis=dict(
            showgrid=True, gridcolor="#f1f5f9", zeroline=False,
            showticklabels=False,
            range=[0, max_count * 1.35],
        ),
        yaxis=dict(
            showgrid=False, zeroline=False,
            tickfont=dict(size=13, color="#334155", family="Inter"),
        ),
        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
        showlegend=False, bargap=0.4,
    )
    return fig


def render_skills_html(skills_data):
    if not skills_data:
        return '<div class="empty-state">No skills recorded yet.</div>'

    max_val = max([s["cnt"] for s in skills_data]) if skills_data else 1

    parts = ['<div class="skills-panel">']
    for s in skills_data:
        pct = (s["cnt"] / max_val * 100) if max_val else 0
        parts.append(
            '<div class="skill-row">'
            f'<div class="skill-name">{s["skill_name"]}</div>'
            '<div class="skill-bar-track">'
            f'<div class="skill-bar-fill" style="width:{pct:.0f}%"></div>'
            '</div>'
            f'<div class="skill-count">{s["cnt"]}</div>'
            '</div>'
        )
    parts.append('</div>')
    return "".join(parts)


# ------------------------------------------------------------
# Dashboard stats (cached)
# ------------------------------------------------------------
@st.cache_data(ttl=30, show_spinner=False)
def get_dashboard_stats():
    return {
        "total_candidates": fetch_one("SELECT COUNT(*) AS c FROM candidates")["c"],
        "total_resumes": fetch_one("SELECT COUNT(*) AS c FROM resumes")["c"],
        "total_jobs": fetch_one("SELECT COUNT(*) AS c FROM jobs")["c"],
        "shortlisted": fetch_one(
            "SELECT COUNT(*) AS c FROM predictions WHERE decision='Shortlisted'"
        )["c"],
        "review": fetch_one(
            "SELECT COUNT(*) AS c FROM predictions WHERE decision='Review'"
        )["c"],
        "rejected": fetch_one(
            "SELECT COUNT(*) AS c FROM predictions WHERE decision='Rejected'"
        )["c"],
        "avg_score": (fetch_one("SELECT AVG(resume_score) AS a FROM predictions") or {}).get("a") or 0,
        "recent": fetch_all("""
            SELECT c.name, j.title AS job_title, p.resume_score, p.decision
            FROM predictions p
            JOIN candidates c ON c.id = p.candidate_id
            JOIN jobs j ON j.id = p.job_id
            ORDER BY p.created_at DESC
            LIMIT 6
        """),
        "top_candidates": fetch_all("""
            SELECT c.name, p.resume_score, p.decision,
                   p.skill_match_percentage
            FROM predictions p
            JOIN candidates c ON c.id = p.candidate_id
            ORDER BY p.resume_score DESC
            LIMIT 5
        """),
        "scores": fetch_all("SELECT resume_score FROM predictions"),
        "skills": fetch_all("""
            SELECT s.skill_name, COUNT(cs.id) AS cnt
            FROM skills s
            LEFT JOIN candidate_skills cs ON cs.skill_id = s.id
            GROUP BY s.id, s.skill_name
            HAVING cnt > 0
            ORDER BY cnt DESC
            LIMIT 10
        """),
    }


# ------------------------------------------------------------
# Dashboard
# ------------------------------------------------------------
def dashboard_home():
    st.markdown(
        """
        <div class="page-header">
            <h1>Dashboard</h1>
            <p>Overview of screening activity and candidate pipeline</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        stats = get_dashboard_stats()
    except Exception as e:
        st.error(f"Database error: {e}")
        return

    total_candidates = stats["total_candidates"]
    total_resumes = stats["total_resumes"]
    total_jobs = stats["total_jobs"]
    shortlisted = stats["shortlisted"]
    review = stats["review"]
    rejected = stats["rejected"]
    avg_score = stats["avg_score"]
    recent = stats["recent"]
    top_candidates = stats["top_candidates"]
    scores_df = stats["scores"]
    skills_data = stats["skills"]

    total_pred = shortlisted + review + rejected

    st.markdown(
        f"""
        <div class="kpi-grid">
            <div class="kpi-card accent-blue">
                <div class="kpi-label">Total Candidates</div>
                <div class="kpi-value">{total_candidates}</div>
                <div class="kpi-sub">{total_resumes} resumes processed</div>
            </div>
            <div class="kpi-card accent-green">
                <div class="kpi-label">Shortlisted</div>
                <div class="kpi-value">{shortlisted}</div>
                <div class="kpi-sub">{f"{(shortlisted/total_pred*100):.0f}% of total" if total_pred else "No data yet"}</div>
            </div>
            <div class="kpi-card accent-amber">
                <div class="kpi-label">In Review</div>
                <div class="kpi-value">{review}</div>
                <div class="kpi-sub">{f"{(review/total_pred*100):.0f}% of total" if total_pred else "No data yet"}</div>
            </div>
            <div class="kpi-card accent-red">
                <div class="kpi-label">Rejected</div>
                <div class="kpi-value">{rejected}</div>
                <div class="kpi-sub">{f"{(rejected/total_pred*100):.0f}% of total" if total_pred else "No data yet"}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="kpi-grid" style="grid-template-columns: repeat(3, 1fr);">
            <div class="kpi-card">
                <div class="kpi-label">Average Score</div>
                <div class="kpi-value">{avg_score:.1f}</div>
                <div class="kpi-sub">Across all predictions</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Active Jobs</div>
                <div class="kpi-value">{total_jobs}</div>
                <div class="kpi-sub">Open positions</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Total Predictions</div>
                <div class="kpi-value">{total_pred}</div>
                <div class="kpi-sub">All-time runs</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div style="height: 8px;"></div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-title">Decision Breakdown</div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="section-subtitle">Count and share by outcome</div>',
                    unsafe_allow_html=True)

        if total_pred > 0:
            fig = chart_decision_breakdown(shortlisted, review, rejected)
            st.plotly_chart(fig, use_container_width=True,
                            config={"displayModeBar": False})
        else:
            st.markdown(
                '<div class="empty-state">No prediction data yet.<br>'
                'Upload resumes to see breakdown.</div>',
                unsafe_allow_html=True,
            )

    with col2:
        st.markdown('<div class="section-title">Score Distribution</div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="section-subtitle">Candidates grouped by score band</div>',
                    unsafe_allow_html=True)

        if total_pred > 0 and scores_df:
            scores = pd.Series([r["resume_score"] for r in scores_df])
            fig = chart_score_buckets(scores)
            st.plotly_chart(fig, use_container_width=True,
                            config={"displayModeBar": False})
        else:
            st.markdown(
                '<div class="empty-state">No scores available yet.</div>',
                unsafe_allow_html=True,
            )

    col3, col4 = st.columns([1.3, 1])

    with col3:
        st.markdown('<div class="section-title">Recent Activity</div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="section-subtitle">Latest resume screenings</div>',
                    unsafe_allow_html=True)

        if recent:
            rows_html = ""
            for r in recent:
                badge_class = {
                    "Shortlisted": "badge-shortlist",
                    "Review": "badge-review",
                    "Rejected": "badge-reject",
                }.get(r["decision"], "badge-review")

                rows_html += (
                    '<div class="activity-row">'
                    f'<div class="activity-name">{r["name"]}</div>'
                    f'<div class="activity-job">{r["job_title"][:32]}</div>'
                    f'<div class="activity-score">{r["resume_score"]:.1f}</div>'
                    '<div class="activity-badge">'
                    f'<span class="badge {badge_class}">{r["decision"]}</span>'
                    '</div>'
                    '</div>'
                )
            st.markdown(rows_html, unsafe_allow_html=True)
        else:
            st.markdown(
                '<div class="empty-state">No activity yet.</div>',
                unsafe_allow_html=True,
            )

    with col4:
        st.markdown('<div class="section-title">Top Candidates</div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="section-subtitle">Highest scoring resumes</div>',
                    unsafe_allow_html=True)

        if top_candidates:
            rows_html = ""
            for idx, r in enumerate(top_candidates, 1):
                badge_class = {
                    "Shortlisted": "badge-shortlist",
                    "Review": "badge-review",
                    "Rejected": "badge-reject",
                }.get(r["decision"], "badge-review")

                rows_html += (
                    '<div class="activity-row">'
                    f'<div style="width:20px;color:#94a3b8;font-size:11px;font-weight:600;">{idx}</div>'
                    '<div class="activity-name" style="flex:1.5;">'
                    f'{r["name"][:18]}'
                    '<div style="font-size:11px;color:#94a3b8;font-weight:400;">'
                    f'{r["skill_match_percentage"]:.0f}% skills match'
                    '</div>'
                    '</div>'
                    f'<div class="activity-score">{r["resume_score"]:.1f}</div>'
                    '<div class="activity-badge">'
                    f'<span class="badge {badge_class}">{r["decision"][:4]}</span>'
                    '</div>'
                    '</div>'
                )
            st.markdown(rows_html, unsafe_allow_html=True)
        else:
            st.markdown(
                '<div class="empty-state">No candidates yet.</div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div style="height: 20px;"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Most Common Skills</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Skills that appear most across candidates</div>',
                unsafe_allow_html=True)

    try:
        st.markdown(render_skills_html(skills_data), unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"Skills panel unavailable: {e}")


def render_sidebar():
    with st.sidebar:
        st.markdown(
            """
            <div style="padding: 4px 8px 16px 8px;">
                <div style="font-size: 16px; font-weight: 600; color: #ffffff;">
                    Resume Screening
                </div>
                <div style="font-size: 12px; color: #94a3b8; margin-top: 2px;">
                    Recruiter Console
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")

        st.page_link("app.py", label="Dashboard")
        st.page_link("pages/1_Jobs.py", label="Jobs")
        st.page_link("pages/2_Upload_Resume.py", label="Upload Resume")
        st.page_link("pages/3_Candidates.py", label="Candidates")
        st.page_link("pages/4_Analytics.py", label="Analytics")

        st.markdown("---")

        user = st.session_state.user
        st.markdown(
            f"""
            <div style="padding: 8px; font-size: 13px;">
                <div style="color: #ffffff; font-weight: 500;">
                    {user['name']}
                </div>
                <div style="color: #94a3b8; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em;">
                    {user['role']}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("Sign out", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.rerun()


def main():
    ensure_admin_user()
    if not st.session_state.logged_in:
        login_screen()
        return
    render_sidebar()
    dashboard_home()


if __name__ == "__main__":
    main()