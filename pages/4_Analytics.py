"""
pages/4_Analytics.py
Analytics dashboard.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from services.database import fetch_all

if not st.session_state.get("logged_in"):
    st.warning("Please login first.")
    st.stop()

st.set_page_config(page_title="Analytics", layout="wide")

css_path = BASE_DIR / "assets" / "style.css"
if css_path.exists():
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown(
    """
    <div class="page-header">
        <h1>Analytics</h1>
        <p>Insights and statistics about screening activity</p>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    preds = fetch_all("""
        SELECT p.resume_score, p.skill_match_percentage, p.similarity_score,
               p.decision, p.created_at,
               c.name, c.experience, c.education,
               j.title AS job_title
        FROM predictions p
        JOIN candidates c ON c.id = p.candidate_id
        JOIN jobs j ON j.id = p.job_id
        ORDER BY p.created_at DESC
    """)
except Exception as e:
    st.error(f"Failed to fetch analytics: {e}")
    st.stop()

if not preds:
    st.markdown('<div class="empty-state">No predictions yet.</div>',
                unsafe_allow_html=True)
    st.stop()

df = pd.DataFrame(preds)

total = len(df)
shortlisted = len(df[df["decision"] == "Shortlisted"])
review = len(df[df["decision"] == "Review"])
rejected = len(df[df["decision"] == "Rejected"])
avg_score = df["resume_score"].mean()
max_score = df["resume_score"].max()
min_score = df["resume_score"].min()
avg_match = df["skill_match_percentage"].mean()

st.markdown(
    f"""
    <div class="kpi-grid">
        <div class="kpi-card accent-blue">
            <div class="kpi-label">Total Analyses</div>
            <div class="kpi-value">{total}</div>
            <div class="kpi-sub">All-time</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Average Score</div>
            <div class="kpi-value">{avg_score:.1f}</div>
            <div class="kpi-sub">out of 100</div>
        </div>
        <div class="kpi-card accent-green">
            <div class="kpi-label">Highest Score</div>
            <div class="kpi-value">{max_score:.1f}</div>
            <div class="kpi-sub">Best candidate</div>
        </div>
        <div class="kpi-card accent-red">
            <div class="kpi-label">Lowest Score</div>
            <div class="kpi-value">{min_score:.1f}</div>
            <div class="kpi-sub">Weakest candidate</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="kpi-grid">
        <div class="kpi-card accent-green">
            <div class="kpi-label">Shortlisted</div>
            <div class="kpi-value">{shortlisted}</div>
            <div class="kpi-sub">{shortlisted/total*100:.0f}% of total</div>
        </div>
        <div class="kpi-card accent-amber">
            <div class="kpi-label">In Review</div>
            <div class="kpi-value">{review}</div>
            <div class="kpi-sub">{review/total*100:.0f}% of total</div>
        </div>
        <div class="kpi-card accent-red">
            <div class="kpi-label">Rejected</div>
            <div class="kpi-value">{rejected}</div>
            <div class="kpi-sub">{rejected/total*100:.0f}% of total</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Avg Skill Match</div>
            <div class="kpi-value">{avg_match:.1f}%</div>
            <div class="kpi-sub">Across all candidates</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ----- Score buckets -----
st.markdown('<div class="section-title">Score Distribution</div>',
            unsafe_allow_html=True)
st.markdown('<div class="section-subtitle">Candidates grouped by score band</div>',
            unsafe_allow_html=True)

ranges = [
    ("Excellent (75-100)", 75, 101, "#15803d"),
    ("Good (50-74)", 50, 75, "#1e40af"),
    ("Fair (25-49)", 25, 50, "#b45309"),
    ("Poor (0-24)", 0, 25, "#b91c1c"),
]
labels, counts, colors = [], [], []
for label, lo, hi, color in ranges:
    cnt = len(df[(df["resume_score"] >= lo) & (df["resume_score"] < hi)])
    labels.append(label)
    counts.append(cnt)
    colors.append(color)

fig = go.Figure()
for label, cnt, color in zip(labels, counts, colors):
    fig.add_trace(go.Bar(
        y=[label], x=[cnt], orientation="h",
        marker=dict(color=color, line=dict(width=0)),
        text=f"  {cnt}", textposition="outside",
        textfont=dict(size=13, color="#0f172a", family="Inter"),
        width=0.6,
    ))
max_count = max(counts) if counts else 1
fig.update_layout(
    height=280,
    margin=dict(l=10, r=50, t=10, b=10),
    xaxis=dict(showgrid=True, gridcolor="#f1f5f9", zeroline=False,
               showticklabels=False, range=[0, max_count * 1.35]),
    yaxis=dict(showgrid=False, zeroline=False,
               tickfont=dict(size=13, color="#334155", family="Inter")),
    paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
    showlegend=False, bargap=0.4,
)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ----- Job-wise bars -----
st.markdown('<div class="section-title" style="margin-top:24px;">Job-wise Analytics</div>',
            unsafe_allow_html=True)

job_stats = df.groupby("job_title").agg(
    candidates=("resume_score", "count"),
    avg_score=("resume_score", "mean"),
).reset_index()
job_stats["avg_score"] = job_stats["avg_score"].round(2)

col1, col2 = st.columns(2)

with col1:
    df_j = job_stats.sort_values("candidates", ascending=True)
    fig = go.Figure()
    for _, row in df_j.iterrows():
        fig.add_trace(go.Bar(
            y=[row["job_title"]], x=[row["candidates"]],
            orientation="h",
            marker=dict(color="#1e40af", line=dict(width=0)),
            text=f"  {int(row['candidates'])}",
            textposition="outside",
            textfont=dict(size=12, color="#0f172a", family="Inter"),
            width=0.55,
        ))
    mv = df_j["candidates"].max() if len(df_j) else 1
    fig.update_layout(
        height=max(220, len(df_j) * 50 + 80),
        margin=dict(l=10, r=50, t=10, b=10),
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9", zeroline=False,
                   showticklabels=False, range=[0, mv * 1.35]),
        yaxis=dict(showgrid=False, zeroline=False,
                   tickfont=dict(size=12, color="#334155", family="Inter"),
                   automargin=True),
        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
        showlegend=False, bargap=0.4,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with col2:
    df_j = job_stats.sort_values("avg_score", ascending=True)
    fig = go.Figure()
    for _, row in df_j.iterrows():
        fig.add_trace(go.Bar(
            y=[row["job_title"]], x=[row["avg_score"]],
            orientation="h",
            marker=dict(color="#15803d", line=dict(width=0)),
            text=f"  {row['avg_score']:.1f}",
            textposition="outside",
            textfont=dict(size=12, color="#0f172a", family="Inter"),
            width=0.55,
        ))
    mv = df_j["avg_score"].max() if len(df_j) else 1
    fig.update_layout(
        height=max(220, len(df_j) * 50 + 80),
        margin=dict(l=10, r=50, t=10, b=10),
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9", zeroline=False,
                   showticklabels=False, range=[0, mv * 1.35]),
        yaxis=dict(showgrid=False, zeroline=False,
                   tickfont=dict(size=12, color="#334155", family="Inter"),
                   automargin=True),
        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
        showlegend=False, bargap=0.4,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ----- Recent predictions table -----
st.markdown('<div class="section-title" style="margin-top:24px;">Recent Predictions</div>',
            unsafe_allow_html=True)

recent = df.head(20)[
    ["name", "job_title", "experience", "resume_score",
     "skill_match_percentage", "similarity_score", "decision"]
].copy()
recent.columns = ["Name", "Job", "Exp (yrs)", "Score",
                  "Skill Match %", "Similarity %", "Decision"]
recent["Score"] = recent["Score"].round(1)
recent["Skill Match %"] = recent["Skill Match %"].round(1)
recent["Similarity %"] = recent["Similarity %"].round(1)

st.dataframe(recent, use_container_width=True, hide_index=True)

st.caption("Analytics are AI-assisted. Final hiring decisions should be human-reviewed.")