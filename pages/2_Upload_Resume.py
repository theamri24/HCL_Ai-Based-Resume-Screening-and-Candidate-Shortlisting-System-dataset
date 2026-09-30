"""
pages/2_Upload_Resume.py
Upload resume, analyze, and store results.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import streamlit as st
import pandas as pd

from services.database import fetch_all, fetch_one, execute
from services.resume_parser import save_upload, extract_resume_text, allowed_file
from services.nlp_service import analyze_resume
from services.feature_engineering import build_features
from services.prediction_service import predict_score

if not st.session_state.get("logged_in"):
    st.warning("Please login first.")
    st.stop()

st.set_page_config(page_title="Upload Resume", layout="wide")

css_path = BASE_DIR / "assets" / "style.css"
if css_path.exists():
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


@st.cache_data(ttl=60, show_spinner=False)
def get_jobs_list():
    return fetch_all("SELECT id, title FROM jobs ORDER BY created_at DESC")


@st.cache_data(ttl=300, show_spinner=False)
def get_skills_lookup():
    rows = fetch_all("SELECT id, skill_name FROM skills")
    return {r["skill_name"].lower(): r["id"] for r in rows}


def clear_dashboard_cache():
    try:
        import app as app_module
        if hasattr(app_module, "get_dashboard_stats"):
            app_module.get_dashboard_stats.clear()
    except Exception:
        pass


st.markdown(
    """
    <div class="page-header">
        <h1>Upload Resume</h1>
        <p>Analyze candidate resume against a job posting</p>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    jobs = get_jobs_list()
except Exception as e:
    st.error(f"Failed to load jobs: {e}")
    st.stop()

if not jobs:
    st.warning("No jobs available. Please create a job first from the Jobs page.")
    st.stop()

job_options = {f"{j['title']} (ID: {j['id']})": j["id"] for j in jobs}

st.markdown('<div class="section-title">Candidate Details</div>',
            unsafe_allow_html=True)

with st.form("upload_form", clear_on_submit=False):
    col1, col2 = st.columns(2)

    with col1:
        selected_job_label = st.selectbox("Select job", list(job_options.keys()))
        candidate_name = st.text_input("Candidate name", placeholder="Rahul Sharma")
        candidate_email = st.text_input("Email", placeholder="rahul@example.com")
        candidate_phone = st.text_input("Phone", placeholder="+91 98765 43210")

    with col2:
        education = st.selectbox(
            "Education",
            ["B.Tech", "B.Sc", "M.Tech", "MBA", "PhD", "M.Sc", "Other"],
        )
        experience = st.number_input(
            "Experience (years)",
            min_value=0.0, max_value=40.0, value=1.0, step=0.5,
        )
        projects_count = st.number_input(
            "Projects count",
            min_value=0, max_value=50, value=3, step=1,
        )
        salary_expectation = st.number_input(
            "Salary expectation ($)",
            min_value=0, max_value=500000, value=75000, step=1000,
        )

    st.markdown('<div class="section-title" style="margin-top:20px;">Resume File</div>',
                unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload PDF or DOCX", type=["pdf", "docx"])

    submitted = st.form_submit_button("Analyze resume", use_container_width=True)


if submitted:
    errors = []
    if not candidate_name.strip():
        errors.append("Candidate name is required.")
    if not candidate_email.strip():
        errors.append("Email is required.")
    if not uploaded_file:
        errors.append("Please upload a resume file.")
    elif not allowed_file(uploaded_file.name):
        errors.append("Only PDF and DOCX files are allowed.")

    if errors:
        for e in errors:
            st.error(e)
        st.stop()

    job_id = job_options[selected_job_label]

    try:
        job = fetch_one(
            "SELECT id, title, description, required_skills, minimum_experience "
            "FROM jobs WHERE id = :id",
            {"id": job_id},
        )
        if not job:
            st.error("Selected job not found.")
            st.stop()

        required_skills = [
            s.strip()
            for s in (job["required_skills"] or "").split(",")
            if s.strip()
        ]

        file_bytes = uploaded_file.read()
        saved_path = save_upload(file_bytes, uploaded_file.name)

        with st.spinner("Extracting text..."):
            resume_text = extract_resume_text(saved_path)

        with st.spinner("Extracting skills..."):
            nlp_result = analyze_resume(resume_text)
            resume_skills = nlp_result["skill_names"]

        with st.spinner("Computing features..."):
            feat_result = build_features(
                resume_text=resume_text,
                job_description=job["description"] or "",
                required_skills=required_skills,
            )

        matched_skills = feat_result["meta"]["matched_skills"]
        missing_skills = feat_result["meta"]["missing_skills"]
        skill_match_pct = feat_result["features"]["skill_match_percentage"]
        similarity = feat_result["features"]["similarity_score"]

        with st.spinner("Running model..."):
            pred = predict_score(
                resume_text=resume_text,
                job_role=job["title"],
                projects_count=int(projects_count),
                salary_expectation=float(salary_expectation),
            )

        score = pred["score"]
        decision = pred["decision"]

        with st.spinner("Saving to database..."):
            existing = fetch_one(
                "SELECT id FROM candidates WHERE email = :e",
                {"e": candidate_email.strip().lower()},
            )

            if existing:
                candidate_id = existing["id"]
                execute(
                    """UPDATE candidates
                       SET name = :n, phone = :p, education = :ed, experience = :ex
                       WHERE id = :id""",
                    {
                        "n": candidate_name.strip(),
                        "p": candidate_phone.strip() or None,
                        "ed": education,
                        "ex": float(experience),
                        "id": candidate_id,
                    },
                )
            else:
                candidate_id = execute(
                    """INSERT INTO candidates
                       (name, email, phone, education, experience)
                       VALUES (:n, :e, :p, :ed, :ex)""",
                    {
                        "n": candidate_name.strip(),
                        "e": candidate_email.strip().lower(),
                        "p": candidate_phone.strip() or None,
                        "ed": education,
                        "ex": float(experience),
                    },
                )

            file_type = uploaded_file.name.rsplit(".", 1)[-1].lower()
            resume_id = execute(
                """INSERT INTO resumes
                   (candidate_id, job_id, original_filename, file_path,
                    file_type, extracted_text)
                   VALUES (:cid, :jid, :fn, :fp, :ft, :et)""",
                {
                    "cid": candidate_id, "jid": job_id,
                    "fn": uploaded_file.name, "fp": str(saved_path),
                    "ft": file_type, "et": resume_text,
                },
            )

            execute(
                """INSERT INTO predictions
                   (resume_id, job_id, candidate_id, resume_score,
                    skill_match_percentage, similarity_score,
                    matched_skills, missing_skills, decision, model_version)
                   VALUES (:rid, :jid, :cid, :rs, :sm, :sim, :ms, :mis, :dec, :mv)""",
                {
                    "rid": resume_id, "jid": job_id, "cid": candidate_id,
                    "rs": float(score), "sm": float(skill_match_pct),
                    "sim": float(similarity),
                    "ms": ", ".join(matched_skills),
                    "mis": ", ".join(missing_skills),
                    "dec": decision, "mv": "v1",
                },
            )

            skill_lookup = get_skills_lookup()
            for sk in resume_skills:
                key = sk.lower()
                if key in skill_lookup:
                    existing_skill = fetch_one(
                        """SELECT id FROM candidate_skills
                           WHERE candidate_id = :cid AND skill_id = :sid""",
                        {"cid": candidate_id, "sid": skill_lookup[key]},
                    )
                    if not existing_skill:
                        try:
                            execute(
                                """INSERT INTO candidate_skills
                                   (candidate_id, skill_id, resume_id)
                                   VALUES (:cid, :sid, :rid)""",
                                {
                                    "cid": candidate_id,
                                    "sid": skill_lookup[key],
                                    "rid": resume_id,
                                },
                            )
                        except Exception:
                            pass

        clear_dashboard_cache()

        st.success("Resume analyzed successfully.")

        st.markdown('<div class="section-title" style="margin-top:24px;">Analysis Result</div>',
                    unsafe_allow_html=True)

        st.markdown(
            f"""
            <div class="kpi-grid">
                <div class="kpi-card accent-blue">
                    <div class="kpi-label">Resume Score</div>
                    <div class="kpi-value">{score:.1f}</div>
                    <div class="kpi-sub">out of 100</div>
                </div>
                <div class="kpi-card {'accent-green' if decision=='Shortlisted' else 'accent-amber' if decision=='Review' else 'accent-red'}">
                    <div class="kpi-label">Decision</div>
                    <div class="kpi-value" style="font-size:20px;">{decision}</div>
                    <div class="kpi-sub">{job['title']}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Skill Match</div>
                    <div class="kpi-value">{skill_match_pct:.1f}%</div>
                    <div class="kpi-sub">{len(matched_skills)} of {len(required_skills)} skills</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">JD Similarity</div>
                    <div class="kpi-value">{similarity:.1f}%</div>
                    <div class="kpi-sub">TF-IDF cosine</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="section-title" style="margin-top:24px;">Skills Analysis</div>',
                    unsafe_allow_html=True)
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("**Matched skills**")
            if matched_skills:
                for s in matched_skills:
                    st.markdown(f"- {s.title()}")
            else:
                st.caption("None")

        with col_b:
            st.markdown("**Missing skills**")
            if missing_skills:
                for s in missing_skills:
                    st.markdown(f"- {s.title()}")
            else:
                st.success("All required skills matched.")

        st.markdown('<div class="section-title" style="margin-top:24px;">Candidate Information</div>',
                    unsafe_allow_html=True)
        info_df = pd.DataFrame({
            "Field": ["Name", "Email", "Phone", "Education",
                      "Experience", "Projects", "Salary Expectation"],
            "Value": [
                candidate_name, candidate_email, candidate_phone or "—",
                education, f"{experience} years", projects_count,
                f"${salary_expectation:,}",
            ],
        })
        st.dataframe(info_df, use_container_width=True, hide_index=True)

        with st.expander("Extracted resume text"):
            st.text_area("text", resume_text, height=300,
                         label_visibility="collapsed")

        with st.expander(f"All extracted skills ({len(resume_skills)})"):
            st.write(", ".join(resume_skills) if resume_skills else "None found")

        st.caption("This is an AI-assisted screening output. "
                   "Final hiring decisions should be made by humans.")

    except Exception as e:
        st.error(f"Analysis failed: {e}")
        import traceback
        with st.expander("Debug info"):
            st.code(traceback.format_exc())