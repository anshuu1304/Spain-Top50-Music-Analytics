# Spain Top 50 — Content Maturity, Release Lifecycle & Playlist Rotation Analysis

An end-to-end data analytics project exploring song lifecycle patterns, chart performance, content maturity, and playlist rotation using Spain Spotify Top 50 historical data.

**Live Dashboard:** https://spain-top50-analytics.streamlit.app/  
**GitHub Repository:** https://github.com/anshuu1304/Spain-Top50-Music-Analytics

---

## 1. Project Overview

This project analyzes historical Spain Top 50 chart snapshots to understand how songs enter, perform, sustain their positions, and eventually leave the chart.

It combines data cleaning, exploratory data analysis, lifecycle classification, playlist turnover analysis, statistical testing, and an interactive Streamlit dashboard.

The objective is to transform historical chart data into meaningful insights about music content maturity and playlist dynamics.

## 2. Problem Statement

A single chart snapshot only shows which tracks are popular on a particular date. It does not explain:

- Which songs are newly entering the chart?
- How long do songs remain on the chart?
- Which tracks reach the Top 10?
- How frequently does the playlist change?
- How do different lifecycle groups behave?
- Are observed differences statistically meaningful?

This project addresses these questions through longitudinal analysis of daily chart snapshots.

## 3. Dataset Description

The dataset contains the following:

| Attribute | Value |
|---|---|
| Total Records | 7,508 |
| Original Columns | 10 |
| Date Range | 18 May 2024 – 15 October 2024 |
| Unique Chart Dates | 151 |
| Complete Snapshots | 150 |
| Tracks per Complete Snapshot | 50 |
| Partial Final Snapshot | 8 records |

The final snapshot on 15 October 2024 contains only 8 records. It is excluded from complete-day playlist churn calculations to maintain consistency.

### Track Identification

Songs are identified using a combination of song title and artist name. This prevents different artists' songs with identical titles from being incorrectly merged.

Fourteen song titles have multiple artist credits and are retained separately for potential manual review.

## 4. Project Objectives

- Analyze historical chart performance.
- Identify song lifecycle stages.
- Measure chart entries and exits.
- Understand playlist rotation and turnover.
- Explore song popularity and chart-position patterns.
- Apply statistical methods to compare groups.
- Build an interactive analytics dashboard.
- Validate the analytical workflow through automated testing.

## 5. Data Cleaning and Preprocessing

The preprocessing workflow includes:

1. Loading and inspecting the dataset.
2. Validating required columns and data types.
3. Handling different date formats, including `dd-mm-yyyy` and ISO `yyyy-mm-dd`.
4. Identifying missing values and duplicate records.
5. Creating a consistent song-artist identity.
6. Preparing track-level historical appearances.
7. Handling incomplete chart snapshots.
8. Creating analysis-ready datasets.

**Important assumptions:**

- Popularity values of zero are treated as missing values based on an explicit analytical assumption.
- Tracks with identical titles but different artists remain separate.
- Incomplete snapshots are excluded from full-day churn calculations.

## 6. Song Lifecycle Analysis

Tracks are categorized into six lifecycle stages based on their observed chart history.

| Lifecycle Stage | Description |
|---|---|
| New Entry | Newly appearing tracks |
| Growth | Tracks showing continued presence or improving chart position |
| Peak | Tracks reaching the Top 10 |
| Mature | Tracks demonstrating sustained chart presence |
| Decline | Tracks showing a weakening chart trajectory |
| Insufficient History | Tracks with fewer than four observed appearances |

These categories are operational definitions developed for this project and should not be interpreted as universal music-industry standards.

### Lifecycle Considerations

- Release dates are unavailable, so actual release age cannot be calculated.
- Left-censoring may occur when a track was already present before the observation period.
- Right-censoring may occur when a track remains on the chart after the observation period ends.
- Lifecycle stages represent observed chart behavior, not complete commercial lifetimes.

## 7. Playlist Rotation Analysis

Playlist rotation measures how frequently tracks enter and leave the Top 50.

The project calculates:

- Daily new entries.
- Daily exits.
- Tracks retained from previous snapshots.
- Playlist turnover.

### Turnover Formula

`Turnover = (Entries + Exits) / 2`

For a fixed-size chart containing 50 unique tracks in both consecutive snapshots, entries and exits are equal. Therefore, this turnover measure equals the number of entries.

Only complete 50-track snapshots are used for full-day churn comparisons.

## 8. Statistical Analysis

The project uses multiple statistical techniques to investigate chart behavior.

| Method | Purpose |
|---|---|
| Kaplan–Meier | Estimate continued chart-presence probability |
| Log-rank Test | Compare chart-presence survival patterns between groups |
| Mann–Whitney U Test | Compare distributions between two independent groups |
| Spearman Correlation | Measure monotonic relationships between variables |
| Holm Correction | Adjust for multiple statistical comparisons |

Statistical significance is interpreted alongside sample sizes, assumptions, and practical relevance.

The analysis is observational. Correlation and group differences do not establish causation.

## 9. Important Analytical Observations

The following data characteristics are considered during interpretation:

- The dataset covers a limited observation period.
- Some tracks may have entered before the first available snapshot.
- Some tracks may remain present after the last available snapshot.
- Fourteen song titles have multiple artist credits.
- The 15 October snapshot is incomplete.
- The 14 October entry wave is dominated by one artist and may influence album-level and lifecycle comparisons.

These factors are considered to avoid overstating analytical conclusions.

## 10. Interactive Streamlit Dashboard

The project includes an interactive Streamlit dashboard designed to make the analysis accessible and easy to explore.

### Dashboard Features

- Summary KPIs.
- Interactive charts and visualizations.
- Date-based filtering.
- Chart performance exploration.
- Song lifecycle analysis.
- Playlist rotation analysis.
- Data-driven insights.

**Access the live dashboard:**

https://spain-top50-analytics.streamlit.app/

The deployed application uses the committed processed dataset as a fallback when the raw local dataset is unavailable in the cloud environment.

## 11. Testing and Validation

The project underwent automated testing and independent consistency checks.

| Validation | Result |
|---|---:|
| Automated Tests Passed | 80 |
| Automated Tests Failed | 0 |
| Independent Audit Checks Agreed | 23/23 |

Testing covered data-loading behavior, application smoke checks, and support for raw and processed dataset availability.

These results represent the recorded validation run and do not guarantee the absence of every possible defect.

## 12. Technology Stack

- **Programming Language:** Python
- **Data Analysis:** Pandas, NumPy
- **Visualization:** Plotly
- **Dashboard:** Streamlit
- **Statistical Analysis:** Survival Analysis and Non-parametric Statistical Testing
- **Testing:** Pytest
- **Version Control:** Git and GitHub

## 13. Repository and Data Availability

The repository contains the application source code, data validation components, automated tests, and processed dataset required by the deployed dashboard.

The raw source file `data/raw/Atlantic_Spain.csv` is maintained locally and is not tracked by Git.

The processed dataset `data/processed/spain_top50_clean.csv` is committed to the repository to support cloud deployment.

## 14. Limitations

1. The analysis is limited to Spain Top 50 chart data.
2. The observation window does not cover the complete lifetime of every track.
3. Release dates are unavailable for direct release-age analysis.
4. Lifecycle classification depends on project-defined rules.
5. Left- and right-censoring affect lifetime interpretation.
6. Artist-level concentration may influence certain comparisons.
7. Some metadata requires manual review.
8. Observational relationships cannot establish causality.

## 15. Future Scope

Potential improvements include:

- Extending the historical observation period.
- Integrating verified song release dates.
- Adding audio features such as energy, danceability, tempo, and acousticness.
- Comparing multiple country charts.
- Expanding artist-level and album-level analysis.
- Improving sensitivity analysis for lifecycle classification.
- Adding more detailed statistical reporting.

## 16. Project Deliverables

| Deliverable | Link |
|---|---|
| Live Streamlit Dashboard | https://spain-top50-analytics.streamlit.app/ |
| GitHub Repository | https://github.com/anshuu1304/Spain-Top50-Music-Analytics |
| Project Explanation Video | https://drive.google.com/file/d/1V7JTug5dgIa6ABfwjURB30hSbv97AyrA/view?usp=sharing |

---

## Research and Publication Status

This document is technical project documentation describing the implementation, methodology, and analysis.

It is not a peer-reviewed research paper and has not been represented as journal-approved or published research.