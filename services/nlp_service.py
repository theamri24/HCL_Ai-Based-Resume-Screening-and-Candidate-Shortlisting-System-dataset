"""
services/nlp_service.py
-----------------------
Text cleaning, skill extraction, keyword extraction, experience parsing.
Uses regex + vocabulary matching (no heavy models needed).
"""

import re
from collections import Counter


# ------------------------------------------------------------
# Skill Vocabulary — extend as needed
# ------------------------------------------------------------
SKILL_VOCABULARY = {
    # Programming
    "python": "Programming",
    "java": "Programming",
    "c++": "Programming",
    "c#": "Programming",
    "javascript": "Programming",
    "typescript": "Programming",
    "go": "Programming",
    "rust": "Programming",
    "php": "Programming",
    "ruby": "Programming",
    "kotlin": "Programming",
    "swift": "Programming",
    "r": "Programming",
    "matlab": "Programming",
    "scala": "Programming",

    # Frontend
    "html": "Frontend",
    "css": "Frontend",
    "react": "Frontend",
    "angular": "Frontend",
    "vue": "Frontend",
    "next.js": "Frontend",
    "streamlit": "Frontend",
    "flask": "Backend",
    "django": "Backend",
    "fastapi": "Backend",
    "node.js": "Backend",
    "express": "Backend",
    "spring boot": "Backend",
    "rest api": "Backend",
    "graphql": "Backend",

    # Database
    "sql": "Database",
    "mysql": "Database",
    "postgresql": "Database",
    "mongodb": "Database",
    "sqlite": "Database",
    "oracle": "Database",
    "redis": "Database",
    "cassandra": "Database",

    # AI/ML
    "machine learning": "AI/ML",
    "deep learning": "AI/ML",
    "nlp": "AI/ML",
    "natural language processing": "AI/ML",
    "computer vision": "AI/ML",
    "tensorflow": "AI/ML",
    "pytorch": "AI/ML",
    "keras": "AI/ML",
    "scikit-learn": "AI/ML",
    "sklearn": "AI/ML",
    "xgboost": "AI/ML",
    "lightgbm": "AI/ML",
    "opencv": "AI/ML",
    "hugging face": "AI/ML",
    "transformers": "AI/ML",
    "bert": "AI/ML",
    "gpt": "AI/ML",
    "llm": "AI/ML",
    "regression": "AI/ML",
    "classification": "AI/ML",
    "clustering": "AI/ML",
    "random forest": "AI/ML",
    "svm": "AI/ML",
    "knn": "AI/ML",
    "neural network": "AI/ML",
    "cnn": "AI/ML",
    "rnn": "AI/ML",
    "lstm": "AI/ML",

    # Data
    "pandas": "Data",
    "numpy": "Data",
    "matplotlib": "Data",
    "seaborn": "Data",
    "plotly": "Data",
    "power bi": "Data",
    "tableau": "Data",
    "excel": "Data",
    "data analysis": "Data",
    "data visualization": "Data",
    "eda": "Data",

    # DevOps
    "docker": "DevOps",
    "kubernetes": "DevOps",
    "git": "DevOps",
    "github": "DevOps",
    "gitlab": "DevOps",
    "jenkins": "DevOps",
    "ci/cd": "DevOps",
    "linux": "DevOps",
    "bash": "DevOps",
    "shell": "DevOps",

    # Cloud
    "aws": "Cloud",
    "azure": "Cloud",
    "gcp": "Cloud",
    "google cloud": "Cloud",
    "heroku": "Cloud",

    # Tools
    "jupyter": "Tools",
    "vs code": "Tools",
    "pycharm": "Tools",
    "postman": "Tools",
    "jira": "Tools",
    "confluence": "Tools",
}

# Aliases → canonical form
SKILL_ALIASES = {
    "scikit learn": "scikit-learn",
    "sk-learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "machine-learning": "machine learning",
    "deep-learning": "deep learning",
    "natural-language processing": "natural language processing",
    "nodejs": "node.js",
    "node js": "node.js",
    "nextjs": "next.js",
    "next js": "next.js",
    "rest-api": "rest api",
    "powerbi": "power bi",
    "power-bi": "power bi",
    "google-cloud": "google cloud",
    "googlecloud": "google cloud",
    "postgres": "postgresql",
    "mongo": "mongodb",
    "ci cd": "ci/cd",
    "cicd": "ci/cd",
}


# ------------------------------------------------------------
# Text cleaning
# ------------------------------------------------------------
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "should", "could", "can", "may", "might", "must", "shall",
    "this", "that", "these", "those", "i", "you", "he", "she", "it", "we",
    "they", "them", "their", "my", "your", "his", "her", "its", "our",
    "am", "not", "no", "yes", "if", "then", "else", "when", "where", "why",
    "how", "what", "which", "who", "whom", "also", "using", "use", "used",
    "work", "worked", "working", "project", "projects", "experience",
    "experienced", "year", "years", "month", "months",
}


def clean_text(text: str) -> str:
    """Normalize text for NLP."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[\u200b-\u200f\u202a-\u202e]", "", text)  # zero-width
    text = re.sub(r"[^\w\s\+\#\.\-\/]", " ", text)            # keep useful chars
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_skill(skill: str) -> str:
    """Convert alias → canonical form."""
    s = skill.lower().strip()
    return SKILL_ALIASES.get(s, s)


# ------------------------------------------------------------
# Skill extraction
# ------------------------------------------------------------
def extract_skills(text: str) -> list[dict]:
    """
    Return list of dicts: [{'skill': 'Python', 'category': 'Programming'}]
    Deduplicated, sorted.
    """
    if not text:
        return []

    cleaned = clean_text(text)
    found = {}

    # 1. Exact vocabulary matches (with word boundaries where possible)
    for skill_key, category in SKILL_VOCABULARY.items():
        # Escape special chars for regex
        pattern = r"(?<![a-z0-9])" + re.escape(skill_key) + r"(?![a-z0-9])"
        if re.search(pattern, cleaned):
            canonical = normalize_skill(skill_key)
            if canonical in SKILL_VOCABULARY:
                cat = SKILL_VOCABULARY[canonical]
            else:
                cat = category
            found[canonical] = cat

    # 2. Alias matches
    for alias, canonical in SKILL_ALIASES.items():
        pattern = r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])"
        if re.search(pattern, cleaned):
            if canonical in SKILL_VOCABULARY:
                found[canonical] = SKILL_VOCABULARY[canonical]

    # 3. Special: "R" language (avoid false positives)
    if re.search(r"\br\b(?:\s*,\s*|\s+programming|\s+language)", cleaned):
        found["r"] = "Programming"

    # Build output
    result = []
    for skill, category in sorted(found.items()):
        result.append({
            "skill": skill.title() if skill != "c++" and skill != "c#" else skill.upper(),
            "raw": skill,
            "category": category,
        })
    return result


def get_skill_names(text: str) -> list[str]:
    """Just the names, for quick comparison."""
    return [s["skill"] for s in extract_skills(text)]


# ------------------------------------------------------------
# Keyword extraction
# ------------------------------------------------------------
def extract_keywords(text: str, top_n: int = 20) -> list[str]:
    """Simple frequency-based keyword extraction."""
    if not text:
        return []

    cleaned = clean_text(text)
    tokens = re.findall(r"\b[a-z][a-z\+\#\.]{2,}\b", cleaned)
    tokens = [t for t in tokens if t not in STOPWORDS and len(t) > 2]

    freq = Counter(tokens)
    return [w for w, _ in freq.most_common(top_n)]


# ------------------------------------------------------------
# Experience extraction
# ------------------------------------------------------------
def extract_experience_years(text: str) -> float:
    """
    Try to extract years of experience from text.
    Returns float, default 0.0
    """
    if not text:
        return 0.0

    cleaned = text.lower()

    patterns = [
        r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience",
        r"experience\s*(?:of|:)?\s*(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)",
        r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\s+(?:in|working)",
    ]

    for pat in patterns:
        m = re.search(pat, cleaned)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass

    # Also look for "X years" standalone
    matches = re.findall(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)", cleaned)
    if matches:
        try:
            years = [float(x) for x in matches]
            return max(years) if years else 0.0
        except ValueError:
            pass

    return 0.0


# ------------------------------------------------------------
# Extra info extractors
# ------------------------------------------------------------
def extract_email(text: str) -> str | None:
    if not text:
        return None
    m = re.search(r"[\w\.\-]+@[\w\.\-]+\.\w+", text)
    return m.group(0) if m else None


def extract_phone(text: str) -> str | None:
    if not text:
        return None
    m = re.search(r"(?:\+?\d{1,3}[\s\-]?)?\d{10}", text)
    return m.group(0) if m else None


# ------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------
def analyze_resume(text: str) -> dict:
    """
    Run full NLP pipeline. Returns:
    {
        'skills': [{'skill': 'Python', 'category': 'Programming'}, ...],
        'skill_names': ['Python', 'SQL', ...],
        'keywords': [...],
        'experience_years': 2.0,
        'email': '...',
        'phone': '...',
    }
    """
    skills = extract_skills(text)
    return {
        "skills": skills,
        "skill_names": [s["skill"] for s in skills],
        "keywords": extract_keywords(text, top_n=20),
        "experience_years": extract_experience_years(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
    }


# ------------------------------------------------------------
# CLI test
# ------------------------------------------------------------
if __name__ == "__main__":
    sample = """
    ARJUN SHARMA
    AI/ML Engineer | Machine Learning | NLP | Python
    arjun.sharma.demo@email.com | +91-98765-43210

    SUMMARY
    Computer Science graduate with 2 years of experience in Python,
    machine learning, NLP, data preprocessing and model deployment.
    Skilled in building practical AI solutions using Scikit-learn,
    TensorFlow, Pandas and Streamlit.

    TECHNICAL SKILLS
    Languages: Python, C++, SQL
    ML/DL: Scikit-learn, Random Forest, XGBoost, SVM, KNN, TensorFlow, Keras
    NLP/Data: NLP, TF-IDF, Pandas, NumPy, Matplotlib, Seaborn
    Database/Tools: MySQL, MongoDB, Streamlit, Jupyter, Git, GitHub

    PROJECTS
    AI-Based Resume Screening System — used NLP, TF-IDF, and ML.
    """

    print("=" * 60)
    result = analyze_resume(sample)
    print("Skills found:", len(result["skills"]))
    for s in result["skills"]:
        print(f"  ✓ {s['skill']:20s} [{s['category']}]")
    print()
    print("Keywords:", result["keywords"][:10])
    print("Experience:", result["experience_years"], "years")
    print("Email:", result["email"])
    print("Phone:", result["phone"])
    print("=" * 60)