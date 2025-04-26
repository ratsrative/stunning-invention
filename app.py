# app.py
import streamlit as st
import pandas as pd
import plotly.express as px # For plotting mood trends
from datetime import date # To get today's date for the date input default value

# Import modules
import auth
import sheets

# --- App Configuration ---
st.set_page_config(page_title="Garba Practice Tracker", layout="wide")

# --- Authentication ---
# This function handles the OAuth flow and returns the user_id if successful
user_id = auth.authenticate_user()

# If user is not authenticated, display a message and stop execution
if user_id is None:
    st.info("Please log in with Google to use the Garba Practice Tracker.")
    st.stop() # Stop the app execution until authenticated

# --- Main App Logic (after successful authentication) ---

st.title("Garba Practice Session Tracker")

# Sidebar Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Log Session", "Dashboard", "Manage Sessions"])

# --- Load User Data ---
# Use Streamlit's caching feature to avoid re-reading data on every script rerun
# Cache expires after 300 seconds (5 minutes) or when input (user_id) changes
@st.cache_data(ttl=300)
def load_user_data(current_user_id):
    """Loads and caches session data for the current user."""
    st.info("Loading session data...") # Optional: show loading message
    data = sheets.get_all_sessions(current_user_id)
    st.empty() # Optional: clear loading message
    return data

# Load the data for the logged-in user
user_sessions_df = load_user_data(user_id)

# --- Page Content ---

if page == "Log Session":
    st.header("Log a New Practice Session")

    # Use a Streamlit form for better input handling and submission
    with st.form("session_form"):
        col1, col2 = st.columns(2)
        with col1:
            # Default date to today
            session_date = st.date_input("Date", value=date.today())
            session_duration = st.number_input("Duration (minutes)", min_value=1, max_value=300, value=60, step=5)
            session_intensity = st.selectbox("Intensity", ["Low", "Medium", "High"])
        with col2:
            session_mood = st.selectbox("Mood After Session", ["Energized", "Happy", "Tired", "Neutral", "Achieved"])
            session_calories = st.number_input("Estimated Calories Burned", min_value=0, value=300, step=10)
            session_songs = st.text_area("Songs/Steps Practiced (Optional)", help="List the songs you danced to or steps you focused on.")

        # Submit button for the form
        submitted = st.form_submit_button("Log Session")

        if submitted:
            # Prepare data dictionary to be sent to the sheets module
            new_session_data = {
                'Date': session_date.strftime('%Y-%m-%d'), # Format date as YYYY-MM-DD string
                'Duration': session_duration,
                'Intensity': session_intensity,
                'Songs': session_songs,
                'Mood': session_mood,
                'Calories': session_calories
                # UserID and SessionID columns are handled within sheets.add_session
            }
            # Call the function to add data to Google Sheet
            if sheets.add_session(user_id, new_session_data):
                 # If adding is successful, clear the cache so the dashboard/manage pages reload the new data
                 load_user_data.clear()
                 # Rerun the script to refresh the page and show updated data/clear form
                 st.rerun()


elif page == "Dashboard":
    st.header("Your Practice Dashboard")

    if user_sessions_df.empty:
        st.info("Log some sessions to see your dashboard!")
    else:
        # --- Statistics ---
        st.subheader("Summary Statistics")
        # Ensure columns exist before accessing them to prevent errors
        total_sessions = len(user_sessions_df)
        total_hours = user_sessions_df['Duration'].sum() / 60 if 'Duration' in user_sessions_df.columns else 0
        avg_duration = user_sessions_df['Duration'].mean() if 'Duration' in user_sessions_df.columns else 0
        total_calories = user_sessions_df['Calories'].sum() if 'Calories' in user_sessions_df.columns else 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Sessions", total_sessions)
        col2.metric("Total Hours Practiced", f"{total_hours:.1f}")
        col3.metric("Average Duration (min)", f"{avg_duration:.1f}")
        col4.metric("Total Calories Burned", f"{total_calories:.0f}")

        st.markdown("---") # Separator

        # --- Mood Trends Plot ---
        st.subheader("Mood Trends Over Time")
        # Check if necessary columns exist and data is suitable for plotting
        if 'Date' in user_sessions_df.columns and 'Mood' in user_sessions_df.columns and not user_sessions_df.empty:
            # Create a copy to avoid modifying the original cached DataFrame
            df_mood = user_sessions_df.copy()
            # Ensure 'Date' column is datetime objects
            df_mood['Date'] = pd.to_datetime(df_mood['Date'], errors='coerce')
            df_mood.dropna(subset=['Date'], inplace=True) # Remove rows with invalid dates

            if not df_mood.empty: # Check if data is still available after dropping NaNs
                 # Map mood to numerical values for plotting a line trend
                 mood_mapping = {"Tired": 1, "Neutral": 2, "Achieved": 3, "Happy": 4, "Energized": 5}
                 # Handle potential moods not in mapping (e.g., from old data)
                 df_mood['MoodValue'] = df_mood['Mood'].map(mood_mapping).fillna(2.5) # Map unknown moods to a neutral value

                 fig = px.line(df_mood, x='Date', y='MoodValue', title='Mood After Session Over Time', markers=True)
                 # Set Y-axis ticks to display mood names instead of numbers
                 fig.update_layout(yaxis = dict(
                    tickmode = 'array',
                    tickvals = list(mood_mapping.values()),
                    ticktext = list(mood_mapping.keys())
                 ))
                 st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Not enough valid date data for mood trend plot.")
        else:
             st.info("Date or Mood column missing or no data for mood trend plot.")

        st.markdown("---") # Separator

        # --- Intensity Distribution Plot ---
        st.subheader("Intensity Distribution")
        if 'Intensity' in user_sessions_df.columns and not user_sessions_df.empty:
             # Count occurrences of each intensity level
             intensity_counts = user_sessions_df['Intensity'].value_counts().reset_index()
             intensity_counts.columns = ['Intensity', 'Count']
             # Create a pie chart
             fig_intensity = px.pie(intensity_counts, values='Count', names='Intensity', title='Session Intensity Distribution')
             st.plotly_chart(fig_intensity, use_container_width=True)
        else:
             st.info("Intensity column missing or no data for intensity distribution plot.")

        # Add more plots/visualizations here as desired (e.g., duration over time, calories vs duration)


elif page == "Manage Sessions":
    st.header("Manage Your Sessions")

    if user_sessions_df.empty:
        st.info("You haven't logged any sessions yet.")
    else:
        # Display sessions in a sortable/filterable DataFrame
        # Drop UserID column as it's not relevant for the user view
        display_df = user_sessions_df.copy()
        if 'UserID' in display_df.columns:
             display_df = display_df.drop(columns=['UserID'])
        # Format Date for better display
        if 'Date' in display_df.columns:
             display_df['Date'] = display_df['Date'].dt.strftime('%Y-%m-%d') # Format datetime back to string for display

        st.dataframe(display_df, use_container_width=True)

        st.markdown("---") # Separator

        st.subheader("Edit or Delete Session")
        # Create a user-friendly identifier for selecting sessions in the dropdown
        # Combine Date, Duration, and a short part of the SessionID (if available)
        if 'SessionID' in user_sessions_df.columns:
            session_options = user_sessions_df.apply(
                lambda row: f"{row['Date'].strftime('%Y-%m-%d')} ({row['Duration']} min) - {str(row.get('SessionID', 'NoID'))[:8]}...",
                axis=1
            ).tolist()

            # Allow the user to select a session
            selected_option = st.selectbox("Select Session to Edit/Delete", options=session_options)

            # Find the actual SessionID from the selected option
            if selected_option:
                try:
                    # Extract the SessionID prefix from the selected string
                    selected_session_id_prefix = selected_option.split(' - ')[-1].replace('...', '')
                    # Find the row in the original DataFrame based on the prefix
                    # Use .astype(str) for robust comparison
                    selected_session_row = user_sessions_df[
                        user_sessions_df['SessionID'].astype(str).str.startswith(selected_session_id_prefix)
                    ].iloc[0] # Get the first match
                    selected_session_id = selected_session_row['SessionID'] # Get the full unique ID

                    st.write(f"Selected Session: **{selected_option}**")

                    # --- Edit Form ---
                    st.subheader("Edit Selected Session")
                    with st.form("edit_session_form"):
                        # Pre-fill form fields with the data from the selected session row
                        # Ensure default values match the data types expected by the input widgets
                        edit_date = st.date_input("Date", value=selected_session_row['Date'])
                        edit_duration = st.number_input("Duration (minutes)", min_value=1, max_value=300, value=int(selected_session_row['Duration']), step=5)
                        # Find the index of the current mood in the list for the selectbox default
                        mood_options = ["Energized", "Happy", "Tired", "Neutral", "Achieved"]
                        current_mood_index = mood_options.index(selected_session_row['Mood']) if selected_session_row['Mood'] in mood_options else 3 # Default to Neutral if not found
                        edit_mood = st.selectbox("Mood After Session", mood_options, index=current_mood_index)

                        intensity_options = ["Low", "Medium", "High"]
                        current_intensity_index = intensity_options.index(selected_session_row['Intensity']) if selected_session_row['Intensity'] in intensity_options else 1 # Default to Medium
                        edit_intensity = st.selectbox("Intensity", intensity_options, index=current_intensity_index)

                        edit_calories = st.number_input("Estimated Calories Burned", min_value=0, value=int(selected_session_row['Calories']), step=10)
                        edit_songs = st.text_area("Songs/Steps Practiced (Optional)", value=selected_session_row['Songs'])

                        update_submitted = st.form_submit_button("Update Session")

                        if update_submitted:
                            # Prepare updated data dictionary
                            updated_data = {
                                'Date': edit_date.strftime('%Y-%m-%d'),
                                'Duration': edit_duration,
                                'Intensity': edit_intensity,
                                'Songs': edit_songs,
                                'Mood': edit_mood,
                                'Calories': edit_calories
                                # SessionID and UserID are NOT included here as they are used for lookup
                            }
                            # Call the update function
                            if sheets.update_session(selected_session_id, updated_data):
                                load_user_data.clear() # Clear cache to show changes
                                st.rerun() # Rerun to refresh UI

                    st.markdown("---") # Separator

                    # --- Delete Button ---
                    st.subheader("Delete Selected Session")
                    # Use a form or st.button with key to ensure proper behavior
                    if st.button("Delete Session", help="This action cannot be undone.", key=f"delete_{selected_session_id}"):
                         # Add a confirmation step? (e.g., st.warning + another button) - Optional
                         if sheets.delete_session(selected_session_id):
                             load_user_data.clear() # Clear cache
                             st.rerun() # Rerun to remove the deleted session from the list

                except IndexError:
                    st.warning("Could not find the selected session data.")
                except Exception as e:
                    st.error(f"An error occurred while processing the selected session: {e}")

        else:
            st.warning("SessionID column not found in your data. Cannot edit or delete specific sessions.")
