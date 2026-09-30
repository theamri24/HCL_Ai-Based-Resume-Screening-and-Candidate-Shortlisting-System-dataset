"""
ml/train_model.py
-----------------
Train a RandomForestRegressor to predict AI Score (0-100)
from resume features.

Dataset columns:
Resume_ID, Name, Skills, Experience (Years), Education, Certifications,
Job Role, Recruiter Decision, Salary Expectation ($), Projects Count,
AI Score (0-100)
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder


# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------
DATASET_PATH = BASE_DIR / "dataset" / "AI_Resume_Screening.csv"
MODEL_PATH = BASE_DIR / "ml" / "model.pkl"
ENCODERS_PATH = BASE_DIR / "ml" / "encoders.pkl"
FEATURES_PATH = BASE_DIR / "ml" / "feature_columns.pkl"


# ------------------------------------------------------------
# Skill keyword lists
# ------------------------------------------------------------
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


# ------------------------------------------------------------
# Load & clean
# ------------------------------------------------------------
def load_data():
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found at {DATASET_PATH}")

    df = pd.read_csv(DATASET_PATH)
    print(f"✅ Loaded dataset: {df.shape[0]} rows × {df.shape[1]} columns")

    # Drop rows with missing target
    df = df.dropna(subset=["AI Score (0-100)"])

    return df


# ------------------------------------------------------------
# Feature engineering
# ------------------------------------------------------------
def parse_skills(skills_str):
    if pd.isna(skills_str):
        return []
    return [s.strip().lower() for s in str(skills_str).split(",") if s.strip()]


def has_keyword(skills_list, keywords):
    joined = " ".join(skills_list).lower()
    for kw in keywords:
        if kw in joined:
            return 1
    return 0


def count_category(skills_list, keywords):
    joined = " ".join(skills_list).lower()
    count = 0
    for kw in keywords:
        if kw in joined:
            count += 1
    return count


def build_features(df):
    print("🔧 Engineering features...")

    # Parse skills
    df["skills_list"] = df["Skills"].apply(parse_skills)

    # Number of skills
    df["num_skills"] = df["skills_list"].apply(len)

    # Skill presence flags
    for feat_name, kws in SKILL_KEYWORDS.items():
        df[f"has_{feat_name}"] = df["skills_list"].apply(
            lambda s: has_keyword(s, kws)
        )

    # Category counts
    for cat_name, kws in SKILL_CATEGORIES.items():
        df[f"cat_{cat_name}"] = df["skills_list"].apply(
            lambda s: count_category(s, kws)
        )

    # Numeric features
    df["experience_years"] = pd.to_numeric(
        df["Experience (Years)"], errors="coerce"
    ).fillna(0)
    df["projects_count"] = pd.to_numeric(
        df["Projects Count"], errors="coerce"
    ).fillna(0)
    df["salary_expectation"] = pd.to_numeric(
        df["Salary Expectation ($)"], errors="coerce"
    ).fillna(0)

    # Categorical encoding
    encoders = {}
    for col in ["Education", "Certifications", "Job Role"]:
        le = LabelEncoder()
        df[col + "_enc"] = le.fit_transform(df[col].astype(str))
        encoders[col] = le

    # Fill missing
    df = df.fillna(0)

    return df, encoders


# ------------------------------------------------------------
# Feature list (order matters!)
# ------------------------------------------------------------
def get_feature_columns():
    cols = [
        "experience_years",
        "projects_count",
        "salary_expectation",
        "num_skills",
        "Education_enc",
        "Certifications_enc",
        "Job Role_enc",
    ]
    # Add skill flags
    for feat_name in SKILL_KEYWORDS.keys():
        cols.append(f"has_{feat_name}")
    # Add category counts
    for cat_name in SKILL_CATEGORIES.keys():
        cols.append(f"cat_{cat_name}")
    return cols


# ------------------------------------------------------------
# Train
# ------------------------------------------------------------
def train():
    df = load_data()
    df, encoders = build_features(df)

    feature_cols = get_feature_columns()
    target_col = "AI Score (0-100)"

    X = df[feature_cols].values
    y = df[target_col].values

    print(f"📊 Features: {len(feature_cols)}")
    print(f"📊 Samples : {len(X)}")
    print(f"🎯 Target  : {target_col} (range {y.min():.0f} - {y.max():.0f})\n")

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"🔀 Train: {len(X_train)}, Test: {len(X_test)}\n")

    # Models to compare
    models = {
        "Linear Regression": LinearRegression(),
        "Random Forest": RandomForestRegressor(
            n_estimators=200, max_depth=15, random_state=42, n_jobs=-1
        ),
        "Gradient Boosting": GradientBoostingRegressor(
            n_estimators=200, max_depth=5, random_state=42
        ),
    }

    results = {}
    best_name = None
    best_score = -np.inf
    best_model = None

    print("=" * 60)
    print("MODEL COMPARISON")
    print("=" * 60)

    for name, model in models.items():
        model.fit(X_train, y_train)
        preds = model.predict(X_test)

        mae = mean_absolute_error(y_test, preds)
        rmse = np.sqrt(mean_squared_error(y_test, preds))
        r2 = r2_score(y_test, preds)

        results[name] = {"MAE": mae, "RMSE": rmse, "R2": r2}

        print(f"\n{name}:")
        print(f"   MAE  : {mae:.3f}")
        print(f"   RMSE : {rmse:.3f}")
        print(f"   R²   : {r2:.4f}")

        if r2 > best_score:
            best_score = r2
            best_name = name
            best_model = model

    print("\n" + "=" * 60)
    print(f"🏆 Best Model: {best_name} (R² = {best_score:.4f})")
    print("=" * 60)

    # Feature importance (for tree models)
    if hasattr(best_model, "feature_importances_"):
        print("\n📊 Feature Importance (Top 10):")
        imps = list(zip(feature_cols, best_model.feature_importances_))
        imps.sort(key=lambda x: x[1], reverse=True)
        for name, imp in imps[:10]:
            print(f"   {name:25s}: {imp:.4f}")

    # Save
    joblib.dump(best_model, MODEL_PATH)
    joblib.dump(encoders, ENCODERS_PATH)
    joblib.dump(feature_cols, FEATURES_PATH)

    print(f"\n✅ Saved model       → {MODEL_PATH}")
    print(f"✅ Saved encoders    → {ENCODERS_PATH}")
    print(f"✅ Saved feature cols→ {FEATURES_PATH}")

    # Quick sample prediction
    print("\n🔍 Sample prediction (first test row):")
    sample_pred = best_model.predict(X_test[:1])[0]
    sample_actual = y_test[0]
    print(f"   Predicted: {sample_pred:.2f}")
    print(f"   Actual   : {sample_actual:.2f}")

    return best_model, encoders, feature_cols


if __name__ == "__main__":
    train()