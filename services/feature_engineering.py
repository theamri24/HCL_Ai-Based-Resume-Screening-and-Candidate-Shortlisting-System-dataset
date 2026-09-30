import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
"""
services/feature_engineering.py
Convert resume + job info into numerical features for ML model.
"""

import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from services.nlp_service import (
    extract_skills,
    extract_keywords,
    extract_experience_years,
    clean_text,
)


FEATURE_ORDER = [
    "skill_match_percentage",
    "similarity_score",
    "experience_years",
    "matched_skills_count",
    "missing_skills_count",
    "resume_length",
    "keyword_count",
    "required_skill_ratio",
]


def _normalize_name(s: str) -> str:
    return s.lower().strip()


def compute_skill_match(resume_skills, required_skills):
    resume_set = {_normalize_name(s) for s in resume_skills}
    req_set = [_normalize_name(s) for s in required_skills]

    matched, missing = [], []
    for req in req_set:
        if req in resume_set:
            matched.append(req)
        else:
            missing.append(req)

    total = len(req_set)
    matched_count = len(matched)
    pct = (matched_count / total * 100.0) if total > 0 else 0.0

    return {
        "matched_skills": matched,
        "missing_skills": missing,
        "total_required": total,
        "matched_count": matched_count,
        "missing_count": len(missing),
        "skill_match_percentage": round(pct, 2),
    }


def compute_similarity(resume_text, job_description):
    if not resume_text or not job_description:
        return 0.0
    r = clean_text(resume_text)
    j = clean_text(job_description)
    if not r or not j:
        return 0.0
    try:
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        tfidf = vectorizer.fit_transform([r, j])
        sim = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
        return round(float(sim) * 100.0, 2)
    except Exception:
        return 0.0


def build_features(resume_text, job_description, required_skills):
    resume_skills = [s["skill"] for s in extract_skills(resume_text)]
    keywords = extract_keywords(resume_text, top_n=20)
    experience = extract_experience_years(resume_text)

    match_info = compute_skill_match(resume_skills, required_skills)
    similarity = compute_similarity(resume_text, job_description)

    resume_length = len(resume_text or "")
    keyword_count = len(keywords)
    required_skill_ratio = match_info["matched_count"] / max(len(required_skills), 1)

    features = {
        "skill_match_percentage": match_info["skill_match_percentage"],
        "similarity_score": similarity,
        "experience_years": experience,
        "matched_skills_count": match_info["matched_count"],
        "missing_skills_count": match_info["missing_count"],
        "resume_length": resume_length,
        "keyword_count": keyword_count,
        "required_skill_ratio": round(required_skill_ratio, 4),
    }

    vector = [features[k] for k in FEATURE_ORDER]

    return {
        "features": features,
        "vector": vector,
        "meta": {
            "matched_skills": match_info["matched_skills"],
            "missing_skills": match_info["missing_skills"],
            "resume_skills": resume_skills,
            "experience_years": experience,
            "keywords": keywords,
        },
    }


if __name__ == "__main__":
    resume_text = """
    ARJUN SHARMA
    AI/ML Engineer | Machine Learning | NLP | Python

    Computer Science graduate with 2 years of experience in Python,
    machine learning, NLP, data preprocessing and model deployment.
    Skilled in AI solutions using Scikit-learn, TensorFlow, Pandas, Streamlit.

    SKILLS
    Python, C++, SQL, Scikit-learn, TensorFlow, Keras, NLP, Pandas,
    NumPy, Matplotlib, Seaborn, MySQL, MongoDB, Streamlit, Jupyter, Git
    """

    job_description = """
    We are hiring a Machine Learning Engineer with strong experience in
    Python, Machine Learning, Deep Learning, NLP, TensorFlow or PyTorch,
    SQL, and Docker deployment. Minimum 1 year experience.
    """

    required_skills = ["Python", "Machine Learning", "NLP", "SQL", "TensorFlow", "Docker"]

    print("=" * 60)
    result = build_features(resume_text, job_description, required_skills)
    print("FEATURES:")
    for k, v in result["features"].items():
        print(f"  {k:25s}: {v}")
    print()
    print("VECTOR:", result["vector"])
    print()
    print("MATCHED:", result["meta"]["matched_skills"])
    print("MISSING:", result["meta"]["missing_skills"])
    print("=" * 60)