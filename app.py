import streamlit as st
import pandas as pd
import plotly.express as px
import ast
from pathlib import Path


# ------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------

st.set_page_config(
    page_title="Science-Policy Capacity Dashboard",
    page_icon="🌍",
    layout="wide"
)


# ------------------------------------------------------------
# DATA PATHS
# ------------------------------------------------------------

DATA_DIR = Path("data")

# Country capacity files
COUNTRY_CAPACITY_PERIOD = DATA_DIR / "country_capacity_period_summary_categorized.csv"
COUNTRY_CAPACITY_INDICATOR = DATA_DIR / "country_capacity_indicator_summary.csv"
COUNTRY_CAPACITY_DOCS = DATA_DIR / "country_capacity_doc_level_deduped.csv"

# UNEP-attributed capacity files
UNEP_CAPACITY_PERIOD = DATA_DIR / "capacity_country_period_summary.csv"
UNEP_CAPACITY_INDICATOR = DATA_DIR / "capacity_indicator_summary.csv"
UNEP_CAPACITY_DOCS = DATA_DIR / "capacity_doc_level_deduped.csv"


# ------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------

@st.cache_data
def load_csv(path):
    if path.exists():
        return pd.read_csv(path, encoding="utf-8-sig")
    return pd.DataFrame()


country_period = load_csv(COUNTRY_CAPACITY_PERIOD)
country_indicator = load_csv(COUNTRY_CAPACITY_INDICATOR)
country_docs = load_csv(COUNTRY_CAPACITY_DOCS)

unep_period = load_csv(UNEP_CAPACITY_PERIOD)
unep_indicator = load_csv(UNEP_CAPACITY_INDICATOR)
unep_docs = load_csv(UNEP_CAPACITY_DOCS)


# ------------------------------------------------------------
# BASIC CLEANING AND HELPERS
# ------------------------------------------------------------

def clean_timewindow(df):
    if df.empty or "TimeWindow" not in df.columns:
        return df

    df["TimeWindow"] = df["TimeWindow"].astype(str)
    df["TimeWindow"] = df["TimeWindow"].str.replace("â€“", "-", regex=False)
    df["TimeWindow"] = df["TimeWindow"].str.replace("–", "-", regex=False)
    return df


country_period = clean_timewindow(country_period)
country_indicator = clean_timewindow(country_indicator)
country_docs = clean_timewindow(country_docs)

unep_period = clean_timewindow(unep_period)
unep_indicator = clean_timewindow(unep_indicator)
unep_docs = clean_timewindow(unep_docs)


def bool_from_value(x):
    return str(x).strip().lower() in ["true", "1", "yes"]


def safe_get(row, col, default=""):
    if col in row.index:
        value = row[col]
        if pd.isna(value):
            return default
        return value
    return default


def parse_evidence_phrases(value):
    if pd.isna(value):
        return []

    if isinstance(value, list):
        return value

    try:
        parsed = ast.literal_eval(str(value))
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass

    return [str(value)] if str(value).strip() else []


def get_numeric(value, default=0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def prepare_download_text(lines):
    return "\n".join([str(x) for x in lines])


def filter_country_capacity_docs(docs_df, country, period):
    if docs_df.empty:
        return pd.DataFrame()

    df = clean_timewindow(docs_df.copy())

    if "Entity" not in df.columns or "TimeWindow" not in df.columns:
        return pd.DataFrame()

    df = df[
        (df["Entity"] == country)
        & (df["TimeWindow"] == period)
    ].copy()

    if df.empty:
        return df

    # Keep relevant positive evidence only.
    if "capacity_evidence_doc" in df.columns:
        df = df[
            df["capacity_evidence_doc"].astype(str).str.lower().isin(["true", "1", "yes"])
        ]
    elif "capacity_relevant" in df.columns:
        df = df[
            df["capacity_relevant"].astype(str).str.lower().isin(["true", "1", "yes"])
        ]

    if "cd" in df.columns:
        df["cd"] = pd.to_numeric(df["cd"], errors="coerce").fillna(0)
        df = df[df["cd"] > 0]
        df = df.sort_values("cd", ascending=False)
    elif "capacity_score" in df.columns:
        df["capacity_score"] = pd.to_numeric(df["capacity_score"], errors="coerce").fillna(0)
        df = df[df["capacity_score"] > 0]
        df = df.sort_values("capacity_score", ascending=False)

    return df


def filter_unep_capacity_docs(docs_df, country, period):
    if docs_df.empty:
        return pd.DataFrame()

    df = clean_timewindow(docs_df.copy())

    if "Entity" not in df.columns or "TimeWindow" not in df.columns:
        return pd.DataFrame()

    df = df[
        (df["Entity"] == country)
        & (df["TimeWindow"] == period)
    ].copy()

    if df.empty:
        return df

    # Keep relevant UNEP-attributed evidence only.
    if "attributable_relevant_doc" in df.columns:
        df = df[
            df["attributable_relevant_doc"].astype(str).str.lower().isin(["true", "1", "yes"])
        ]
    else:
        if "capacity_relevant" in df.columns:
            df = df[
                df["capacity_relevant"].astype(str).str.lower().isin(["true", "1", "yes"])
            ]
        if "unep_attributed" in df.columns:
            df = df[
                df["unep_attributed"].astype(str).str.lower().isin(["true", "1", "yes"])
            ]

    if "sd" in df.columns:
        df["sd"] = pd.to_numeric(df["sd"], errors="coerce").fillna(0)
        df = df[df["sd"] > 0]
        df = df.sort_values("sd", ascending=False)
    elif "unep_attribution_score" in df.columns:
        df["unep_attribution_score"] = pd.to_numeric(df["unep_attribution_score"], errors="coerce").fillna(0)
        df = df[df["unep_attribution_score"] > 0]
        df = df.sort_values("unep_attribution_score", ascending=False)

    return df


# ------------------------------------------------------------
# SIDEBAR FILTERS
# ------------------------------------------------------------

st.sidebar.title("Filters")

all_periods = sorted(
    list(
        set(country_period.get("TimeWindow", pd.Series(dtype=str)).dropna().unique())
        | set(unep_period.get("TimeWindow", pd.Series(dtype=str)).dropna().unique())
    )
)

selected_period = st.sidebar.selectbox(
    "Select period",
    all_periods if all_periods else ["No data"]
)

all_countries = sorted(
    list(
        set(country_period.get("Entity", pd.Series(dtype=str)).dropna().unique())
        | set(unep_period.get("Entity", pd.Series(dtype=str)).dropna().unique())
    )
)

selected_country = st.sidebar.selectbox(
    "Select country",
    all_countries if all_countries else ["No data"]
)


# ------------------------------------------------------------
# TABS
# ------------------------------------------------------------

tabs = st.tabs([
    "Executive Overview",
    "Countries Assessed Map",
    "Country Capacity",
    "UNEP-attributed Capacity",
    "Country-Period Report",
    "Evidence Explorer",
    "Methodology"
])


# ------------------------------------------------------------
# TAB 1: EXECUTIVE OVERVIEW
# ------------------------------------------------------------

with tabs[0]:
    st.title("🌍 Science-Policy Capacity Dashboard")

    st.markdown(
        """
        This dashboard summarizes documented evidence on countries' capacity to develop
        environmental data, environmental statistics, scientific assessments, monitoring systems,
        early warning data inputs, environmental information platforms, and national reporting frameworks.

        It compares two views:

        1. **General documented country capacity evidence**
        2. **UNEP-attributed capacity evidence**
        """
    )

    c1, c2, c3, c4 = st.columns(4)

    countries_assessed = len(all_countries)
    periods_assessed = len(all_periods)

    if not country_period.empty and "evidence_of_country_capacity" in country_period.columns:
        country_with_evidence = int(
            country_period["evidence_of_country_capacity"]
            .astype(str)
            .str.lower()
            .isin(["true", "1", "yes"])
            .sum()
        )
    else:
        country_with_evidence = 0

    if not unep_period.empty and "evidence_of_unep_attributed_capacity_strengthening" in unep_period.columns:
        unep_with_evidence = int(
            unep_period["evidence_of_unep_attributed_capacity_strengthening"]
            .astype(str)
            .str.lower()
            .isin(["true", "1", "yes"])
            .sum()
        )
    else:
        unep_with_evidence = 0

    c1.metric("Countries assessed", countries_assessed)
    c2.metric("Periods assessed", periods_assessed)
    c3.metric("Country-periods with capacity evidence", country_with_evidence)
    c4.metric("Country-periods with UNEP-attributed evidence", unep_with_evidence)

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Country capacity evidence by period")

        if not country_indicator.empty:
            y_col = "number_entities_with_country_capacity_evidence"

            if y_col in country_indicator.columns:
                fig = px.bar(
                    country_indicator,
                    x="TimeWindow",
                    y=y_col,
                    text=y_col,
                    title="Countries with documented capacity evidence"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.dataframe(country_indicator, use_container_width=True)
        else:
            st.warning("Country capacity indicator file not found or empty.")

    with col2:
        st.subheader("UNEP-attributed capacity evidence by period")

        if not unep_indicator.empty:
            y_candidates = [
                "number_entities_with_unep_attributed_capacity_strengthening_evidence",
                "number_entities_with_sufficient_unep_attributed_capacity_evidence"
            ]

            y_col = next((c for c in y_candidates if c in unep_indicator.columns), None)

            if y_col:
                fig = px.bar(
                    unep_indicator,
                    x="TimeWindow",
                    y=y_col,
                    text=y_col,
                    title="Countries with UNEP-attributed capacity evidence"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.dataframe(unep_indicator, use_container_width=True)
        else:
            st.warning("UNEP-attributed indicator file not found or empty.")


# ------------------------------------------------------------
# TAB 2: COUNTRIES ASSESSED MAP
# ------------------------------------------------------------

with tabs[1]:
    st.header("🗺️ Countries Assessed")

    if country_period.empty and unep_period.empty:
        st.warning("No country-period data available.")
    else:
        map_base = pd.DataFrame({"Entity": all_countries})
        map_base["assessed"] = "Assessed"

        fig = px.choropleth(
            map_base,
            locations="Entity",
            locationmode="country names",
            color="assessed",
            hover_name="Entity",
            title="Countries included in the assessment"
        )

        fig.update_layout(
            geo=dict(showframe=False, showcoastlines=True),
            height=600
        )

        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(map_base, use_container_width=True)


# ------------------------------------------------------------
# TAB 3: COUNTRY CAPACITY
# ------------------------------------------------------------

with tabs[2]:
    st.header("📊 Documented Country Capacity")

    if country_period.empty:
        st.warning("No country capacity data available.")
    else:
        dfp = country_period[country_period["TimeWindow"] == selected_period].copy()

        if dfp.empty:
            st.warning(f"No country capacity data for {selected_period}.")
        else:
            score_col = "Ci_t_country_capacity"
            label_col = "capacity_score_4_range_category"

            st.subheader(f"Country capacity map — {selected_period}")

            fig = px.choropleth(
                dfp,
                locations="Entity",
                locationmode="country names",
                color=score_col if score_col in dfp.columns else None,
                hover_name="Entity",
                hover_data=[
                    c for c in [
                        "TimeWindow",
                        score_col,
                        label_col,
                        "count_capacity_evidence_docs"
                    ] if c in dfp.columns
                ],
                color_continuous_scale="Viridis",
                range_color=[0, 100],
                title=f"Average documented country capacity evidence score — {selected_period}"
            )

            fig.update_layout(
                geo=dict(showframe=False, showcoastlines=True),
                height=600
            )

            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Country capacity table")

            display_cols = [
                c for c in [
                    "Entity",
                    "TimeWindow",
                    "Ci_t_country_capacity",
                    "capacity_score_4_range_category",
                    "count_capacity_evidence_docs",
                    "best_evidence_title",
                    "best_evidence_link",
                    "best_evidence_capacity_justification"
                ] if c in dfp.columns
            ]

            st.dataframe(
                dfp[display_cols].sort_values("Ci_t_country_capacity", ascending=False),
                use_container_width=True
            )


# ------------------------------------------------------------
# TAB 4: UNEP-ATTRIBUTED CAPACITY
# ------------------------------------------------------------

with tabs[3]:
    st.header("🌱 UNEP-attributed Capacity Evidence")

    if unep_period.empty:
        st.warning("No UNEP-attributed capacity data available.")
    else:
        dfu = unep_period[unep_period["TimeWindow"] == selected_period].copy()

        if dfu.empty:
            st.warning(f"No UNEP-attributed capacity data for {selected_period}.")
        else:
            score_col = "Ci_t_UNEP"
            label_col = "extent_of_unep_attributed_capacity_evidence"

            st.subheader(f"UNEP-attributed capacity map — {selected_period}")

            fig = px.choropleth(
                dfu,
                locations="Entity",
                locationmode="country names",
                color=score_col if score_col in dfu.columns else None,
                hover_name="Entity",
                hover_data=[
                    c for c in [
                        "TimeWindow",
                        score_col,
                        label_col,
                        "count_attributable_docs_nonzero_unep"
                    ] if c in dfu.columns
                ],
                color_continuous_scale="YlGn",
                range_color=[0, 100],
                title=f"UNEP-attributed capacity evidence score — {selected_period}"
            )

            fig.update_layout(
                geo=dict(showframe=False, showcoastlines=True),
                height=600
            )

            st.plotly_chart(fig, use_container_width=True)

            st.subheader("UNEP-attributed capacity table")

            display_cols = [
                c for c in [
                    "Entity",
                    "TimeWindow",
                    "Ci_t_UNEP",
                    "extent_of_unep_attributed_capacity_evidence",
                    "count_attributable_docs_nonzero_unep",
                    "best_evidence_title",
                    "best_evidence_link",
                    "best_evidence_capacity_justification",
                    "best_evidence_unep_justification",
                    "best_evidence_phrases"
                ] if c in dfu.columns
            ]

            st.dataframe(
                dfu[display_cols].sort_values("Ci_t_UNEP", ascending=False),
                use_container_width=True
            )


# ------------------------------------------------------------
# TAB 5: COUNTRY-PERIOD REPORT
# ------------------------------------------------------------

with tabs[4]:
    st.header("📄 Country-Period Report")

    st.markdown(
        """
        Select a country and period to generate an executive-style snapshot combining
        general documented country capacity evidence and UNEP-attributed contribution evidence.
        """
    )

    country_data = country_period[
        (country_period.get("Entity", "") == selected_country)
        & (country_period.get("TimeWindow", "") == selected_period)
    ]

    unep_data = unep_period[
        (unep_period.get("Entity", "") == selected_country)
        & (unep_period.get("TimeWindow", "") == selected_period)
    ]

    st.subheader(f"{selected_country} — {selected_period}")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Documented country capacity")

        if country_data.empty:
            st.info("No documented country capacity evidence found for this country-period.")
        else:
            r = country_data.iloc[0]

            st.metric(
                "Country capacity evidence score",
                safe_get(r, "Ci_t_country_capacity", 0)
            )

            st.write(
                "**Evidence level:**",
                safe_get(r, "capacity_score_4_range_category", "N/A")
            )

            st.write(
                "**Evidence documents:**",
                safe_get(r, "count_capacity_evidence_docs", 0)
            )

            st.write(
                "**Best evidence title:**",
                safe_get(r, "best_evidence_title", "N/A")
            )

            link = safe_get(r, "best_evidence_link", "")
            if link:
                st.markdown(f"[Open best evidence link]({link})")

            with st.expander("Capacity justification"):
                st.write(
                    safe_get(
                        r,
                        "best_evidence_capacity_justification",
                        "No justification available."
                    )
                )

            with st.expander("Evidence phrases"):
                phrases = parse_evidence_phrases(
                    safe_get(r, "best_evidence_phrases", "[]")
                )

                if phrases:
                    for p in phrases:
                        st.markdown(f"- {p}")
                else:
                    st.write("No evidence phrases available.")

    with col2:
        st.markdown("### UNEP-attributed capacity evidence")

        if unep_data.empty:
            st.info("No UNEP-attributed capacity evidence found for this country-period.")
        else:
            r = unep_data.iloc[0]

            st.metric(
                "UNEP-attributed capacity evidence score",
                safe_get(r, "Ci_t_UNEP", 0)
            )

            st.write(
                "**Evidence level:**",
                safe_get(r, "extent_of_unep_attributed_capacity_evidence", "N/A")
            )

            st.write(
                "**Attributable evidence documents:**",
                safe_get(r, "count_attributable_docs_nonzero_unep", 0)
            )

            st.write(
                "**Best evidence title:**",
                safe_get(r, "best_evidence_title", "N/A")
            )

            link = safe_get(r, "best_evidence_link", "")
            if link:
                st.markdown(f"[Open best evidence link]({link})")

            with st.expander("Capacity justification"):
                st.write(
                    safe_get(
                        r,
                        "best_evidence_capacity_justification",
                        "No capacity justification available."
                    )
                )

            with st.expander("UNEP attribution justification"):
                st.write(
                    safe_get(
                        r,
                        "best_evidence_unep_justification",
                        "No UNEP justification available."
                    )
                )

            with st.expander("Evidence phrases"):
                phrases = parse_evidence_phrases(
                    safe_get(r, "best_evidence_phrases", "[]")
                )

                if phrases:
                    for p in phrases:
                        st.markdown(f"- {p}")
                else:
                    st.write("No evidence phrases available.")

    st.divider()

    st.markdown("### Executive interpretation")

    if country_data.empty and unep_data.empty:
        st.write("No evidence was found for this country-period in the processed datasets.")
    else:
        capacity_score = (
            country_data.iloc[0]["Ci_t_country_capacity"]
            if not country_data.empty and "Ci_t_country_capacity" in country_data.columns
            else 0
        )

        unep_score = (
            unep_data.iloc[0]["Ci_t_UNEP"]
            if not unep_data.empty and "Ci_t_UNEP" in unep_data.columns
            else 0
        )

        st.write(
            f"""
            For **{selected_country}** during **{selected_period}**, the dashboard identifies
            a documented country capacity evidence score of **{capacity_score}** and a
            UNEP-attributed capacity evidence score of **{unep_score}**.

            These scores should be interpreted as evidence-based indicators derived from
            mined documents, not as a full independent measurement of national capacity.
            The detailed evidence sections below provide the source links, justifications,
            and key evidence phrases behind the assessment.
            """
        )

    # ------------------------------------------------------------
    # Detailed evidence highlights
    # ------------------------------------------------------------

    st.divider()
    st.markdown("## 📚 Detailed Evidence Highlights")

    st.markdown(
        """
        This section lists the relevant evidence documents used in the assessment for the selected
        country-period. It is designed to help executives review the source links, justifications,
        and evidence phrases behind the scores.
        """
    )

    country_evidence = filter_country_capacity_docs(
        country_docs,
        selected_country,
        selected_period
    )

    unep_evidence = filter_unep_capacity_docs(
        unep_docs,
        selected_country,
        selected_period
    )

    # -----------------------------
    # A. Country capacity evidence
    # -----------------------------

    st.markdown("### 1. General country capacity evidence")

    if country_evidence.empty:
        st.info("No relevant general country capacity evidence documents found for this country-period.")
    else:
        st.write(
            f"Relevant country capacity evidence documents found: **{len(country_evidence)}**"
        )

        for _, row in country_evidence.iterrows():
            title = safe_get(row, "Title", "Untitled document")
            link = safe_get(row, "Link", "")
            score = safe_get(row, "cd", safe_get(row, "capacity_score", "N/A"))
            justification = safe_get(row, "capacity_justification", "No justification available.")
            phrases = parse_evidence_phrases(safe_get(row, "evidence_phrases", "[]"))

            with st.expander(f"📄 {title} — capacity evidence score: {score}"):
                if link:
                    st.markdown(f"**Source link:** [Open document]({link})")
                else:
                    st.write("**Source link:** Not available")

                st.write("**Capacity evidence score:**", score)

                st.markdown("**Capacity justification:**")
                st.write(justification)

                st.markdown("**Key evidence phrases:**")
                if phrases:
                    for phrase in phrases:
                        st.markdown(f"- {phrase}")
                else:
                    st.write("No evidence phrases available.")

    # -----------------------------
    # B. UNEP-attributed evidence
    # -----------------------------

    st.markdown("### 2. UNEP-attributed capacity evidence")

    if unep_evidence.empty:
        st.info("No relevant UNEP-attributed capacity evidence documents found for this country-period.")
    else:
        st.write(
            f"Relevant UNEP-attributed evidence documents found: **{len(unep_evidence)}**"
        )

        for _, row in unep_evidence.iterrows():
            title = safe_get(row, "Title", "Untitled document")
            link = safe_get(row, "Link", "")
            contribution_score = safe_get(row, "sd", "N/A")
            capacity_score = safe_get(row, "capacity_score", "N/A")
            attribution_score = safe_get(row, "unep_attribution_score", "N/A")
            capacity_justification = safe_get(
                row,
                "capacity_justification",
                "No capacity justification available."
            )
            unep_justification = safe_get(
                row,
                "unep_justification",
                "No UNEP attribution justification available."
            )
            phrases = parse_evidence_phrases(safe_get(row, "evidence_phrases", "[]"))

            with st.expander(
                f"🌱 {title} — UNEP-attributed contribution score: {contribution_score}"
            ):
                if link:
                    st.markdown(f"**Source link:** [Open document]({link})")
                else:
                    st.write("**Source link:** Not available")

                col_a, col_b, col_c = st.columns(3)
                col_a.metric("Contribution score", contribution_score)
                col_b.metric("Capacity score", capacity_score)
                col_c.metric("UNEP attribution score", attribution_score)

                st.markdown("**Capacity justification:**")
                st.write(capacity_justification)

                st.markdown("**UNEP attribution justification:**")
                st.write(unep_justification)

                st.markdown("**Key evidence phrases:**")
                if phrases:
                    for phrase in phrases:
                        st.markdown(f"- {phrase}")
                else:
                    st.write("No evidence phrases available.")

    # -----------------------------
    # C. Download evidence highlights
    # -----------------------------

    st.markdown("### Download evidence highlights")

    report_lines = []

    report_lines.append("# Evidence Highlights Report")
    report_lines.append(f"Country: {selected_country}")
    report_lines.append(f"Period: {selected_period}")
    report_lines.append("")
    report_lines.append("## General country capacity evidence")

    if country_evidence.empty:
        report_lines.append("No relevant general country capacity evidence documents found.")
    else:
        for _, row in country_evidence.iterrows():
            title = safe_get(row, "Title", "Untitled document")
            link = safe_get(row, "Link", "")
            score = safe_get(row, "cd", safe_get(row, "capacity_score", "N/A"))
            justification = safe_get(row, "capacity_justification", "No justification available.")
            phrases = parse_evidence_phrases(safe_get(row, "evidence_phrases", "[]"))

            report_lines.append(f"### {title}")
            report_lines.append(f"Score: {score}")
            report_lines.append(f"Link: {link}")
            report_lines.append(f"Justification: {justification}")
            report_lines.append("Evidence phrases:")

            if phrases:
                for phrase in phrases:
                    report_lines.append(f"- {phrase}")
            else:
                report_lines.append("- No evidence phrases available.")

            report_lines.append("")

    report_lines.append("")
    report_lines.append("## UNEP-attributed capacity evidence")

    if unep_evidence.empty:
        report_lines.append("No relevant UNEP-attributed capacity evidence documents found.")
    else:
        for _, row in unep_evidence.iterrows():
            title = safe_get(row, "Title", "Untitled document")
            link = safe_get(row, "Link", "")
            contribution_score = safe_get(row, "sd", "N/A")
            capacity_score = safe_get(row, "capacity_score", "N/A")
            attribution_score = safe_get(row, "unep_attribution_score", "N/A")
            capacity_justification = safe_get(
                row,
                "capacity_justification",
                "No capacity justification available."
            )
            unep_justification = safe_get(
                row,
                "unep_justification",
                "No UNEP attribution justification available."
            )
            phrases = parse_evidence_phrases(safe_get(row, "evidence_phrases", "[]"))

            report_lines.append(f"### {title}")
            report_lines.append(f"UNEP-attributed contribution score: {contribution_score}")
            report_lines.append(f"Capacity score: {capacity_score}")
            report_lines.append(f"UNEP attribution score: {attribution_score}")
            report_lines.append(f"Link: {link}")
            report_lines.append(f"Capacity justification: {capacity_justification}")
            report_lines.append(f"UNEP attribution justification: {unep_justification}")
            report_lines.append("Evidence phrases:")

            if phrases:
                for phrase in phrases:
                    report_lines.append(f"- {phrase}")
            else:
                report_lines.append("- No evidence phrases available.")

            report_lines.append("")

    report_text = prepare_download_text(report_lines)

    st.download_button(
        "Download country-period evidence highlights report",
        report_text,
        file_name=f"{selected_country}_{selected_period}_evidence_highlights.md".replace(" ", "_"),
        mime="text/markdown"
    )


# ------------------------------------------------------------
# TAB 6: EVIDENCE EXPLORER
# ------------------------------------------------------------

with tabs[5]:
    st.header("🔎 Evidence Explorer")

    dataset_choice = st.radio(
        "Choose evidence dataset",
        ["Country capacity evidence", "UNEP-attributed evidence"],
        horizontal=True
    )

    if dataset_choice == "Country capacity evidence":
        evidence_df = country_docs.copy()
        score_col = "cd" if "cd" in evidence_df.columns else "capacity_score"
    else:
        evidence_df = unep_docs.copy()
        score_col = "sd" if "sd" in evidence_df.columns else "unep_attribution_score"

    if evidence_df.empty:
        st.warning("Selected evidence dataset is empty.")
    else:
        evidence_df = clean_timewindow(evidence_df)

        c1, c2, c3 = st.columns(3)

        with c1:
            evidence_country = st.selectbox(
                "Evidence country",
                sorted(evidence_df["Entity"].dropna().unique())
            )

        with c2:
            evidence_period = st.selectbox(
                "Evidence period",
                sorted(evidence_df["TimeWindow"].dropna().unique())
            )

        with c3:
            keyword = st.text_input("Keyword search in title/justification", "")

        filtered = evidence_df[
            (evidence_df["Entity"] == evidence_country)
            & (evidence_df["TimeWindow"] == evidence_period)
        ].copy()

        if keyword:
            keyword_lower = keyword.lower()
            text_cols = [
                c for c in [
                    "Title",
                    "capacity_justification",
                    "unep_justification",
                    "evidence_phrases"
                ] if c in filtered.columns
            ]

            mask = pd.Series(False, index=filtered.index)
            for c in text_cols:
                mask = mask | filtered[c].astype(str).str.lower().str.contains(keyword_lower, na=False)

            filtered = filtered[mask]

        if score_col in filtered.columns:
            filtered[score_col] = pd.to_numeric(filtered[score_col], errors="coerce").fillna(0)
            filtered = filtered.sort_values(score_col, ascending=False)

        st.write(f"Documents found: {len(filtered)}")

        display_cols = [
            c for c in [
                "Entity",
                "TimeWindow",
                "Title",
                "Link",
                score_col,
                "capacity_relevant",
                "unep_attributed",
                "capacity_score",
                "unep_attribution_score",
                "capacity_justification",
                "unep_justification",
                "evidence_phrases"
            ] if c in filtered.columns
        ]

        st.dataframe(filtered[display_cols], use_container_width=True)

        csv_download = filtered.to_csv(index=False, encoding="utf-8-sig")

        st.download_button(
            "Download filtered evidence CSV",
            csv_download,
            file_name="filtered_evidence.csv",
            mime="text/csv"
        )


# ------------------------------------------------------------
# TAB 7: METHODOLOGY
# ------------------------------------------------------------

with tabs[6]:
    st.header("📘 Methodology")

    st.markdown(
        """
        ### 1. Country capacity evidence

        The country capacity score summarizes documented evidence that a country has
        institutional or technical capacity to develop environmental data, environmental
        statistics, scientific assessments, monitoring systems, early warning data inputs,
        environmental information platforms, and reporting frameworks.

        The score is based on the average score of relevant documents identified through
        the mining and classification pipeline.

        ### 2. UNEP-attributed capacity evidence

        The UNEP-attributed capacity score combines two elements:

        - the strength of the capacity evidence;
        - the strength of the explicit attribution to UNEP support, contribution, or enabling role.

        The document-level contribution score is:

        `capacity evidence score × UNEP attribution score / 100`

        The country-period UNEP-attributed score is the average of these document-level
        contribution scores.

        ### 3. Important interpretation note

        These scores reflect **documented evidence found through the mining process**.
        They should not be interpreted as a complete independent measurement of national
        capacity or as proof that UNEP was the only causal factor.

        ### 4. Evidence audit trail

        The dashboard keeps source links, justifications, evidence phrases, and document-level
        scores so users can review the basis for each country-period result.

        ### 5. Dashboard outputs

        The dashboard uses country-period summaries and document-level deduplicated evidence
        generated by the analysis pipeline. The evidence report section allows users to see
        not only the best evidence document, but all relevant evidence documents available
        for the selected country and period.
        """
    )