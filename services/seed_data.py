"""
services/seed_data.py
Seeds demo jobs + candidates on first run (SQLite only).
"""

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from services.database import fetch_one, execute, DB_TYPE


DEMO_JOBS = [
    ("AI Engineer",
     "We are looking for an AI Engineer to design and deploy intelligent systems at scale. Strong Python, ML, NLP, and deployment experience required.",
     "Python, Machine Learning, NLP, SQL, TensorFlow, PyTorch, Docker", 2),
    ("Data Scientist",
     "Analyze large datasets, build predictive models, and communicate insights. Strong statistics and programming required.",
     "Python, SQL, Machine Learning, Deep Learning, Pandas, NumPy, Scikit-learn", 3),
    ("Full Stack Developer",
     "Build modern web apps with React, Node.js, REST APIs, and SQL databases.",
     "React, Node.js, JavaScript, SQL, REST API, Git, Docker", 2),
    ("Cybersecurity Analyst",
     "Protect systems and data. Monitor threats, conduct vulnerability assessments, implement security policies.",
     "Cybersecurity, Ethical Hacking, Networking, Linux, Python, SQL", 1),
    ("AI Research Intern",
     "Internship for AI research on NLP and Deep Learning. Strong fundamentals required.",
     "Python, Deep Learning, NLP, PyTorch, TensorFlow", 0),
]

DEMO_CANDIDATES = [
    ("Aarav Sharma", "aarav@example.com", "B.Tech", 3.0,
     "Aarav Sharma, B.Tech CS. 3 years experience in Python, Machine Learning, NLP, SQL, TensorFlow. Skilled in Pandas, NumPy, Docker."),
    ("Priya Patel", "priya@example.com", "M.Tech", 4.5,
     "Priya Patel, M.Tech Data Science. Expert in Python, TensorFlow, Deep Learning, NLP, SQL, PyTorch, Pandas."),
    ("Rohan Verma", "rohan@example.com", "B.Tech", 2.0,
     "Rohan Verma, Full Stack Developer. React, Node.js, SQL, REST API, Git, Docker."),
    ("Neha Singh", "neha@example.com", "MBA", 5.0,
     "Neha Singh, Cybersecurity Analyst. Ethical Hacking, Networking, Linux, Python, SQL."),
    ("Vikram Reddy", "vikram@example.com", "B.Sc", 1.5,
     "Vikram Reddy, Junior ML Engineer. Python, Machine Learning, SQL, Pandas, NumPy."),
    ("Ananya Iyer", "ananya@example.com", "PhD", 6.0,
     "Dr. Ananya Iyer, AI Research Scientist. Python, Deep Learning, ML, NLP, PyTorch, TensorFlow, SQL."),
    ("Karan Mehta", "karan@example.com", "B.Tech", 3.5,
     "Karan Mehta, ML Engineer. Python, Machine Learning, NLP, TensorFlow, SQL."),
    ("Sneha Kapoor", "sneha@example.com", "M.Tech", 2.5,
     "Sneha Kapoor, Data Analyst. Python, SQL, Pandas, NumPy, Machine Learning."),
    ("Meera Nair", "meera@example.com", "M.Tech", 4.0,
     "Meera Nair, Data Scientist. Python, ML, Deep Learning, NLP, SQL, TensorFlow."),
    ("Pooja Desai", "pooja@example.com", "PhD", 7.0,
     "Dr. Pooja Desai, Senior AI Researcher. Python, ML, DL, NLP, PyTorch, TensorFlow, SQL, Docker."),
]


def seed():
    if DB_TYPE != "sqlite":
        return

    existing_user = fetch_one(
        "SELECT id FROM users WHERE email = :e",
        {"e": "admin@resume.com"},
    )
    if existing_user:
        return

    from passlib.hash import bcrypt
    new_hash = bcrypt.hash("admin123")
    execute(
        """INSERT INTO users (name, email, password_hash, role)
           VALUES (:n, :e, :p, :r)""",
        {"n": "Admin User", "e": "admin@resume.com",
         "p": new_hash, "r": "admin"},
    )

    job_ids = []
    for title, desc, skills, exp in DEMO_JOBS:
        jid = execute(
            """INSERT INTO jobs (title, description, required_skills,
                                 minimum_experience, created_by)
               VALUES (:t, :d, :rs, :me, :cb)""",
            {"t": title, "d": desc, "rs": skills, "me": exp, "cb": 1},
        )
        job_ids.append(jid)

    from services.prediction_service import predict_score

    for idx, (name, email, edu, exp, resume_text) in enumerate(DEMO_CANDIDATES):
        job_id = job_ids[idx % len(job_ids)]

        cid = execute(
            """INSERT INTO candidates (name, email, education, experience)
               VALUES (:n, :e, :ed, :ex)""",
            {"n": name, "e": email, "ed": edu, "ex": exp},
        )

        rid = execute(
            """INSERT INTO resumes
               (candidate_id, job_id, original_filename, file_path,
                file_type, extracted_text)
               VALUES (:cid, :jid, :fn, :fp, :ft, :et)""",
            {"cid": cid, "jid": job_id,
             "fn": f"{name.replace(' ', '_')}.pdf",
             "fp": f"uploads/demo_{cid}.pdf",
             "ft": "pdf", "et": resume_text},
        )

        pred = predict_score(
            resume_text=resume_text,
            job_role="Data Scientist",
            projects_count=3 + (idx % 5),
            salary_expectation=60000 + idx * 3000,
        )

        execute(
            """INSERT INTO predictions
               (resume_id, job_id, candidate_id, resume_score,
                skill_match_percentage, similarity_score,
                matched_skills, missing_skills, decision, model_version)
               VALUES (:rid, :jid, :cid, :rs, :sm, :sim, :ms, :mis, :dec, :mv)""",
            {"rid": rid, "jid": job_id, "cid": cid,
             "rs": pred["score"], "sm": 60.0, "sim": 55.0,
             "ms": "Python, SQL", "mis": "Docker",
             "dec": pred["decision"], "mv": "v1"},
        )


if __name__ == "__main__":
    seed()