"""
services/prediction_service.py
Load trained model and predict resume score + decision.
Cached with Streamlit cache_resource.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import re
import joblib
import numpy as np

try:
    import streamlit as st
    HAS_ST = True
except ImportError:
    HAS_ST = False

MODEL_PATH = BASE_DIR / "ml" / "model.pkl"
ENCODERS_PATH = BASE_DIR / "ml" / "encoders.pkl"
FEATURE_COLS_PATH = BASE_DIR / "ml" / "feature_columns.pkl"

THRESHOLDS = {
    "shortlist": 75,
    "review": 50,
}


def _load_artifacts_impl():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found: {MODEL_PATH}. Run ml/train_model.py first."
        )
    model = joblib.load(MODEL_PATH)
    encoders = joblib.load(ENCODERS_PATH)
    feature_cols = joblib.load(FEATURE_COLS_PATH)
    return model, encoders, feature_cols


if HAS_ST:
    @st.cache_resource(show_spinner=False)
    def _load_artifacts():
        return _load_artifacts_impl()
else:
    _cached = None
    def _load_artifacts():
        global _cached
        if _cached is None:
            _cached = _load_artifacts_impl()
        return _cached


SKILL_KEYWORDS = {
    "python": ["python"],
    "sql": ["sql"],
    "machine_learning": ["machine learning"],
    "deep_learning": ["deep learning"],
    "nlp": ["nlp"],
    "tensorflow": ["tensorflow"],
    "pytorch": ["pytorch"],
    "cybersecurity": ["cybersecurity"],
    "networking": ["networking"],
    "linux": ["linux"],
    "java": ["java"],
    "cpp": ["c++"],
    "react": ["react"],
    "ethical_hacking": ["ethical hacking"],
}

SKILL_CATEGORIES = {
    "prog": ["python", "java", "c++", "javascript"],
    "ai_ml": ["machine learning", "deep learning", "nlp", "tensorflow",
              "pytorch", "keras"],
    "data": ["pandas", "numpy", "matplotlib", "seaborn"],
    "db": ["sql", "mysql", "mongodb"],
    "fe": ["react", "html", "css"],
    "be": ["django", "flask", "node"],
    "devops": ["docker", "kubernetes", "git", "linux"],
    "security": ["cybersecurity", "ethical hacking", "networking"],
}


def _parse_skills_from_text(text: str):
    if not text:
        return []
    tokens = re.split(r"[,\n;|/•·]+", text.lower())
    return [t.strip() for t in tokens if t.strip()]


def _extract_experience_years(text: str) -> float:
    if not text:
        return 0.0
    t = text.lower()
    patterns = [
        r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience",
        r"experience\s*(?:of|:)?\s*(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)",
        r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)",
    ]
    for pat in patterns:
        m = re.search(pat, t)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
    return 0.0


def _detect_education(text: str) -> str:
    if not text:
        return "B.Tech"
    t = text.lower()
    for edu in ["phd", "ph.d", "m.tech", "mba", "b.tech", "b.sc", "m.sc"]:
        if edu in t:
            if edu in ("phd", "ph.d"):
                return "PhD"
            return edu.upper().replace(".", ".").title().replace("Tech", "Tech").replace("Sc", "Sc")
    return "B.Tech"


def _detect_certifications(text: str) -> str:
    if not text:
        return "None"
    t = text.lower()
    if "aws" in t and "certif" in t:
        return "AWS Certified"
    if "google" in t and ("ml" in t or "machine" in t):
        return "Google ML"
    if "deep learning" in t and "specialization" in t:
        return "Deep Learning Specialization"
    if "deep learning specialization" in t:
        return "Deep Learning Specialization"
    if "aws certified" in t:
        return "AWS Certified"
    if "google ml" in t:
        return "Google ML"
    return "None"


def _encode_safe(encoder, value, default_class):
    try:
        return int(encoder.transform([value])[0])
    except Exception:
        try:
            return int(encoder.transform([default_class])[0])
        except Exception:
            return 0


def _has_keyword(text: str, keywords) -> int:
    t = text.lower()
    for kw in keywords:
        if kw in t:
            return 1
    return 0


def _count_category(text: str, keywords) -> int:
    t = text.lower()
    return sum(1 for kw in keywords if kw in t)


def build_features(resume_text, job_role="Data Scientist",
                   projects_count=5, salary_expectation=75000):
    _, encoders, _ = _load_artifacts()

    skills_list = _parse_skills_from_text(resume_text)
    joined_text = " ".join(skills_list) + " " + (resume_text or "").lower()

    experience_years = _extract_experience_years(resume_text)
    num_skills = len(skills_list)

    education = _detect_education(resume_text)
    certification = _detect_certifications(resume_text)

    Education_enc = _encode_safe(encoders["Education"], education, "B.Tech")
    Certifications_enc = _encode_safe(
        encoders["Certifications"], certification, "None"
    )
    JobRole_enc = _encode_safe(encoders["Job Role"], job_role, "Data Scientist")

    features = {
        "experience_years": experience_years,
        "projects_count": projects_count,
        "salary_expectation": salary_expectation,
        "num_skills": num_skills,
        "Education_enc": Education_enc,
        "Certifications_enc": Certifications_enc,
        "Job Role_enc": JobRole_enc,
    }

    for feat_name, kws in SKILL_KEYWORDS.items():
        features[f"has_{feat_name}"] = _has_keyword(joined_text, kws)

    for cat_name, kws in SKILL_CATEGORIES.items():
        features[f"cat_{cat_name}"] = _count_category(joined_text, kws)

    return features


def predict_score(resume_text, job_role="Data Scientist",
                  projects_count=5, salary_expectation=75000):
    model, _, feature_cols = _load_artifacts()

    features = build_features(
        resume_text, job_role, projects_count, salary_expectation
    )

    vector = [features[col] for col in feature_cols]
    X = np.array([vector], dtype=float)

    raw_score = float(model.predict(X)[0])
    score = float(np.clip(raw_score, 0, 100))

    if score >= THRESHOLDS["shortlist"]:
        decision = "Shortlisted"
    elif score >= THRESHOLDS["review"]:
        decision = "Review"
    else:
        decision = "Rejected"

    return {
        "score": round(score, 2),
        "decision": decision,
        "features": features,
        "vector": vector,
    }


if __name__ == "__main__":
    sample_resume = """
    ARJUN SHARMA
    AI/ML Engineer | Python | Machine Learning | NLP

    2 years of experience in Python, machine learning, NLP, and SQL.
    Skilled in Scikit-learn, TensorFlow, Pandas, NumPy.

    EDUCATION
    B.Tech in Computer Science

    CERTIFICATIONS
    AWS Certified

    SKILLS
    Python, SQL, Machine Learning, Deep Learning, NLP, TensorFlow,
    Pytorch, Pandas, NumPy, React, Java
    """

    print("=" * 60)
    result = predict_score(
        sample_resume, job_role="Data Scientist",
        projects_count=4, salary_expectation=80000,
    )
    print(f"Score    : {result['score']} / 100")
    print(f"Decision : {result['decision']}")
    print("=" * 60)