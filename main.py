"""Streamlit dashboard app for tracking and visualizing Dreaming Spanish progress.

This application provides an interactive interface to:
- Load and display viewing data from the Dreaming Spanish API
- Visualize viewing patterns
- Track progress towards learning milestones (50, 150, 300, 600, 1000, 1500 hours)
- Generate predictions for future milestone achievements
- Display statistics like streaks, best days, and goal completion rates
- Export viewing data to CSV format
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from src import components
from src.utils import (
    get_initial_time,
    get_user_info,
    load_data,
)

# Set pandas option for future compatibility
pd.set_option("future.no_silent_downcasting", True)  # noqa: FBT003

st.set_page_config(page_title="Dreaming Spanish Time Tracker", layout="wide")

title = "Dreaming Spanish Stats"
subheader = "Analyze your viewing habits and predict your progress"

# todo: temp removed as streamlit seems to silently err on deployment with this, but still runs fine
# if st.context.url.startswith("https://ds-stats-dev."):
#     title += " - :orange[Dev Build]"
# elif not st.context.url.startswith("https://ds-stats."):
#     title += " - :violet[Local Build]"

st.title(title)
st.subheader(subheader)

# Show warning for dev build
if st.context.url.startswith("https://ds-stats-dev."):
    st.warning(
        "You are viewing the development version of the application, meaning "
        "that it may not be fully functional, may contain bugs, or may be "
        "using experimental features.\n Resort to the production version if "
        "you encounter any issues.",
    )

button_col1, button_col2, button_col3 = st.columns([1, 1, 1])
with button_col1:
    st.link_button(
        "☁️ Official Progress",
        "https://app.dreaming.com/spanish/progress",
        use_container_width=True,
    )

with button_col2:
    st.link_button(
        "🪲 Report Issue",
        "http://github.com/HarryPeach/dreamingspanishstats/issues",
        use_container_width=True,
    )

with button_col3:
    st.link_button(
        "📖 Source Code",
        "http://github.com/HarryPeach/dreamingspanishstats",
        use_container_width=True,
    )

# Add token input and buttons in an aligned row
st.write("")  # Add some spacing
col1, col2 = st.columns([4, 1])
with col1:
    token = st.text_input(
        "Enter your bearer token:",
        type="password",
        key="token_input",
        label_visibility="collapsed",
    )
with col2:
    go_button = st.button("Go", type="primary", use_container_width=True)

if not token:
    st.warning("Please enter your bearer token above to fetch data")
    # Load and display README
    try:
        with Path("bearer_how_to.md").open() as file:
            readme_content = file.read()
            if readme_content:
                st.markdown(readme_content, unsafe_allow_html=True)
    except FileNotFoundError:
        pass
    st.stop()

# Load data when token is provided and button is clicked
if "data" not in st.session_state or go_button:
    with st.spinner("Fetching data..."):
        data = load_data(token)
        if data is None:
            st.error(
                "Failed to fetch data from the DreamingSpanish API."
                "Please check your bearer token, ensuring it doesn't contain "
                "anything extra such as 'token:' at the beginning.",
            )
            st.stop()
        st.session_state.data = data

result = st.session_state.data
df = result.df
initial_time = get_initial_time(token) or 0
user_info = get_user_info(token) or 0

df = result.df.rename(columns={"timeSeconds": "seconds"})

# Calculate cumulative seconds and streak
ds_watch_time = user_info['user']['cumulativeWatchTimes']['es']
external_watch_time = user_info['user']['externalTimeSummary']['es']['timeSeconds']
df["cumulative_seconds"] = ds_watch_time + external_watch_time
df["cumulative_minutes"] = df["cumulative_seconds"] / 60
df["cumulative_hours"] = df["cumulative_minutes"] / 60
df["streak"] = (df["seconds"] > 0).astype(int)

# Calculate current streak
df["streak_group"] = (df["streak"] != df["streak"].shift()).cumsum()
df["current_streak"] = df.groupby("streak_group")["streak"].cumsum()

# Calculate moving averages
df["7day_avg"] = df["seconds"].rolling(7, min_periods=1).mean()
df["30day_avg"] = df["seconds"].rolling(30, min_periods=1).mean()

current_7day_avg = df["7day_avg"].iloc[-1]
current_30day_avg = df["30day_avg"].iloc[-1]

components.progress_bar(df, user_info)

components.basic_stats(df, initial_time)

components.projected_growth(df)

components.additional_graphs(df)

components.expected_milestones(df)

general_insights_col, best_days_col = st.columns(2)
with general_insights_col:
    components.general_insights(df, result)

with best_days_col:
    components.best_days(result)

components.averaged_insights(df)

with st.container(border=True):
    st.subheader("Tools")
    result = st.session_state.data
    st.download_button(
        label="📥 Export Data to CSV",
        data=df.to_csv(index=False),
        file_name="dreaming_spanish_data.csv",
        mime="text/csv",
    )

st.caption(
    f"Data range: {df['date'].min().strftime('%Y-%m-%d')} to {
        df['date'].max().strftime('%Y-%m-%d')
    }",
)
