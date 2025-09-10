import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sqlalchemy as sa
from datetime import datetime, timedelta
import io
import base64
import zipfile
import json
import os
from utils.data_processing import (
    load_roster_data, load_equipment_data, load_events_data, load_event_equip_data,
    time_str_to_minutes, minutes_to_time_str, military_time_to_minutes, 
    calculate_duration_minutes, minutes_to_mmss
)
from utils.calculations import (
    calculate_initial_difficulty, calculate_actual_difficulty,
    calculate_target_difficulty, adjust_equipment_weight, adjust_distance,
    predict_team_success
)
from utils.reshuffling import reshuffle_teams
from utils.visualization import (
    plot_difficulty_trends, plot_team_difficulty_distribution,
    plot_final_difficulty_scores
)

# Create data directory if it doesn't exist
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(os.path.dirname(script_dir), 'data')
save_dir = os.path.join(os.path.dirname(script_dir), 'saved_sessions')
os.makedirs(data_dir, exist_ok=True)
os.makedirs(save_dir, exist_ok=True)

# Create sample data files if they don't exist
def ensure_sample_data_exists():
    """Create sample data files if they don't exist"""
    from utils.data_processing import (
        create_default_roster, create_default_event_equipment
    )
    
    # Check and create roster data
    roster_path = os.path.join(data_dir, 'sample_roster.csv')
    if not os.path.exists(roster_path):
        roster_df = create_default_roster()
        roster_df.to_csv(roster_path, index=False)
    
    # Check and create event equipment data
    event_equipment_path = os.path.join(data_dir, 'event_equipment.csv')
    if not os.path.exists(event_equipment_path):
        event_equipment_df = create_default_event_equipment()
        event_equipment_df.to_csv(event_equipment_path, index=False)

# Call the function to ensure sample data exists
ensure_sample_data_exists()

# Page configuration
st.set_page_config(
    page_title="Team Performance Management",
    page_icon="📊",
    layout="wide"
)

# Initialize session state variables
if 'roster_data' not in st.session_state:
    st.session_state.roster_data = None
if 'equipment_data' not in st.session_state:
    st.session_state.equipment_data = None
if 'events_data' not in st.session_state:
    st.session_state.events_data = None
if 'event_records' not in st.session_state:
    st.session_state.event_records = pd.DataFrame(columns=[
        'Team', 'Day', 'Event_Number', 'Event_Name', 'Equipment_Name', 'Equipment_Weight',
        'Number_of_Equipment', 'Distance_km', 'Heat_Category', 'Time_Limit',
        'Start_Time', 'End_Time', 'Time_Actual', 'Time_Actual_Minutes',
        'Initial_Participants', 'Drops', 'Initial_Difficulty', 'Actual_Difficulty',
        'Temperature_Multiplier'
    ])
if 'drop_data' not in st.session_state:
    st.session_state.drop_data = pd.DataFrame(columns=[
        'Team', 'Participant_Name', 'Roster_Number', 'Event_Name', 'Drop_Time', 
        'Day', 'Event_Number'
    ])
if 'reshuffled_teams' not in st.session_state:
    st.session_state.reshuffled_teams = None
if 'session_name' not in st.session_state:
    st.session_state.session_name = "default_session"
if 'four_day_plan' not in st.session_state:
    st.session_state.four_day_plan = {1: [], 2: [], 3: [], 4: []}
if 'structured_four_day_plan' not in st.session_state:
    st.session_state.structured_four_day_plan = None

# Functions for session state persistence
def save_session_state(session_name=None):
    """Save session state to disk with an optional session name"""
    if session_name:
        st.session_state.session_name = session_name
    
    # Create a directory for this session
    session_dir = os.path.join(save_dir, st.session_state.session_name)
    os.makedirs(session_dir, exist_ok=True)
    
    # Save DataFrames to CSV files
    if st.session_state.roster_data is not None:
        st.session_state.roster_data.to_csv(os.path.join(session_dir, 'roster_data.csv'), index=False)
    
    if st.session_state.equipment_data is not None:
        st.session_state.equipment_data.to_csv(os.path.join(session_dir, 'equipment_data.csv'), index=False)
    
    if st.session_state.events_data is not None:
        st.session_state.events_data.to_csv(os.path.join(session_dir, 'events_data.csv'), index=False)
    
    if not st.session_state.event_records.empty:
        st.session_state.event_records.to_csv(os.path.join(session_dir, 'event_records.csv'), index=False)
    
    if not st.session_state.drop_data.empty:
        st.session_state.drop_data.to_csv(os.path.join(session_dir, 'drop_data.csv'), index=False)
    
    if st.session_state.reshuffled_teams is not None:
        st.session_state.reshuffled_teams.to_csv(os.path.join(session_dir, 'reshuffled_teams.csv'), index=False)
    
    # Save the 4-day plan
    if st.session_state.structured_four_day_plan is not None:
        st.session_state.structured_four_day_plan.to_csv(os.path.join(session_dir, 'four_day_plan.csv'), index=False)
    
    # Save a JSON file with the four_day_plan dictionary
    with open(os.path.join(session_dir, 'four_day_plan_dict.json'), 'w') as f:
        json.dump(st.session_state.four_day_plan, f)
    
    # Save a metadata file with timestamp
    metadata = {
        'session_name': st.session_state.session_name,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'has_roster': st.session_state.roster_data is not None,
        'has_equipment': st.session_state.equipment_data is not None,
        'has_events': st.session_state.events_data is not None,
        'has_event_records': not st.session_state.event_records.empty,
        'has_drop_data': not st.session_state.drop_data.empty,
        'has_reshuffled_teams': st.session_state.reshuffled_teams is not None,
        'has_four_day_plan': st.session_state.structured_four_day_plan is not None
    }
    
    with open(os.path.join(session_dir, 'metadata.json'), 'w') as f:
        json.dump(metadata, f)
    
    return True

def load_session_state(session_name):
    """Load session state from disk using a session name"""
    try:
        # Create the session directory path
        session_dir = os.path.join(save_dir, session_name)
        
        if not os.path.exists(session_dir):
            st.error(f"Session '{session_name}' not found.")
            return False
        
        # Load the metadata file
        with open(os.path.join(session_dir, 'metadata.json'), 'r') as f:
            metadata = json.load(f)
        
        # Load roster data if it exists
        roster_path = os.path.join(session_dir, 'roster_data.csv')
        if os.path.exists(roster_path):
            st.session_state.roster_data = pd.read_csv(roster_path)
        
        # Load equipment data if it exists
        equipment_path = os.path.join(session_dir, 'equipment_data.csv')
        if os.path.exists(equipment_path):
            st.session_state.equipment_data = pd.read_csv(equipment_path)
        
        # Load events data if it exists
        events_path = os.path.join(session_dir, 'events_data.csv')
        if os.path.exists(events_path):
            st.session_state.events_data = pd.read_csv(events_path)
        
        # Load event records if they exist
        event_records_path = os.path.join(session_dir, 'event_records.csv')
        if os.path.exists(event_records_path):
            st.session_state.event_records = pd.read_csv(event_records_path)
        
        # Load drop data if it exists
        drop_data_path = os.path.join(session_dir, 'drop_data.csv')
        if os.path.exists(drop_data_path):
            st.session_state.drop_data = pd.read_csv(drop_data_path)
        
        # Load reshuffled teams if they exist
        reshuffled_teams_path = os.path.join(session_dir, 'reshuffled_teams.csv')
        if os.path.exists(reshuffled_teams_path):
            st.session_state.reshuffled_teams = pd.read_csv(reshuffled_teams_path)
        
        # Load the 4-day plan if it exists
        four_day_plan_path = os.path.join(session_dir, 'four_day_plan.csv')
        if os.path.exists(four_day_plan_path):
            st.session_state.structured_four_day_plan = pd.read_csv(four_day_plan_path)
        
        # Load the four_day_plan dictionary if it exists
        four_day_plan_dict_path = os.path.join(session_dir, 'four_day_plan_dict.json')
        if os.path.exists(four_day_plan_dict_path):
            with open(four_day_plan_dict_path, 'r') as f:
                plan_dict = json.load(f)
                # Convert string keys to integers
                st.session_state.four_day_plan = {int(k): v for k, v in plan_dict.items()}
        else:
            # Initialize empty plan if not found
            st.session_state.four_day_plan = {1: [], 2: [], 3: [], 4: []}
        
        # Update session name
        st.session_state.session_name = session_name
        
        return True
    except Exception as e:
        st.error(f"Error loading session: {str(e)}")
        return False

def get_available_sessions():
    """Get a list of available saved sessions"""
    sessions = []
    
    # Check if the save directory exists
    if not os.path.exists(save_dir):
        return sessions
    
    # List all subdirectories in the save directory
    for item in os.listdir(save_dir):
        item_path = os.path.join(save_dir, item)
        if os.path.isdir(item_path):
            # Check if this is a valid session (has metadata file)
            if os.path.exists(os.path.join(item_path, 'metadata.json')):
                sessions.append(item)
    
    return sessions

# Title and description
st.title("Team Performance Management and Analysis")
st.markdown("Manage roster, equipment, events, and analyze team performance for a 4-day event.")

# Session management in the sidebar
st.sidebar.header("Session Management")

# Session name input
new_session_name = st.sidebar.text_input(
    "Session Name",
    value=st.session_state.session_name
)

# Save current session
if st.sidebar.button("Save Current Session"):
    if save_session_state(new_session_name):
        st.sidebar.success(f"Session '{new_session_name}' saved successfully!")

# Load a previous session
available_sessions = get_available_sessions()
if available_sessions:
    session_to_load = st.sidebar.selectbox(
        "Select Session to Load",
        options=available_sessions
    )
    
    if st.sidebar.button("Load Selected Session"):
        if load_session_state(session_to_load):
            st.sidebar.success(f"Session '{session_to_load}' loaded successfully!")
else:
    st.sidebar.info("No saved sessions found.")

# Create tabs for different sections
tabs = st.tabs(["Data Upload", "Set 4 Day Plan", "Event Recording", "Drop Management", "Team Reshuffling",
                "Adjust Difficulty", "Final Scores", "Visualizations", "Predictive Analytics"])

# Tab 1: Data Upload
with tabs[0]:
    st.header("Upload Data")
    
    # Roster Upload
    st.subheader("Roster Upload")
    
    use_default_roster = st.checkbox("Use default roster data", value=True)
    
    if use_default_roster:
        st.session_state.roster_data = load_roster_data()
        if st.session_state.roster_data is not None and len(st.session_state.roster_data) > 0:
            st.success(f"Default roster loaded with {len(st.session_state.roster_data)} participants.")
        else:
            st.error("Failed to load default roster data. Check the logs for details.")
    else:
        upload_method = st.radio("Choose upload method for roster:", ["CSV File", "SQL Server"])
        
        if upload_method == "CSV File":
            roster_file = st.file_uploader("Upload Roster CSV", type="csv")
            if roster_file:
                st.session_state.roster_data = load_roster_data(roster_file)
                st.success(f"Roster uploaded successfully with {len(st.session_state.roster_data)} participants.")
        else:
            st.text_input("SQL Server Connection String")
            sql_query = st.text_area("SQL Query for Roster")
            if st.button("Connect and Load Roster"):
                # Placeholder for SQL connection
                st.error("SQL connection not implemented in this demo. Please use CSV upload.")
    
    # Event Equipment Data Upload
    st.subheader("Event Equipment Data")
    
    use_default_event_data = st.checkbox("Use default event data", value=True)
    
    if use_default_event_data:
        # Load both equipment and events data from the event equipment data
        event_equipment_data = load_event_equip_data()
        st.session_state.equipment_data = load_equipment_data()
        st.session_state.events_data = load_events_data()
        
        st.success(f"Default event equipment data loaded.")
        st.success(f"Generated equipment data with {len(st.session_state.equipment_data)} items.")
        st.success(f"Generated events data with {len(st.session_state.events_data)} events.")
    else:
        upload_method = st.radio("Choose upload method for event data:", ["CSV File", "SQL Server"])
        
        if upload_method == "CSV File":
            event_equip_file = st.file_uploader("Upload Event Equipment CSV", type="csv")
            if event_equip_file:
                # Load both equipment and events data from the event equipment data
                event_equipment_data = load_event_equip_data(event_equip_file)
                st.session_state.equipment_data = load_equipment_data(event_equip_file)
                st.session_state.events_data = load_events_data(event_equip_file)
                
                st.success(f"Event equipment data uploaded successfully.")
                st.success(f"Generated equipment data with {len(st.session_state.equipment_data)} items.")
                st.success(f"Generated events data with {len(st.session_state.events_data)} events.")
        else:
            st.text_input("SQL Server Connection String for Event Data")
            sql_query_events = st.text_area("SQL Query for Event Data")
            if st.button("Connect and Load Event Data"):
                st.error("SQL connection not implemented in this demo. Please use CSV upload.")
    
    # Display uploaded data
    if st.session_state.roster_data is not None:
        st.subheader("Roster Data")
        st.dataframe(st.session_state.roster_data)
    
    if st.session_state.equipment_data is not None:
        st.subheader("Equipment Data")
        st.dataframe(st.session_state.equipment_data)
    
    if st.session_state.events_data is not None:
        st.subheader("Events Data")
        st.dataframe(st.session_state.events_data)
    
    # Option to view raw event equipment data
    if use_default_event_data or ('event_equip_file' in locals() and event_equip_file is not None):
        if st.checkbox("Show Raw Event Equipment Data"):
            st.subheader("Raw Event Equipment Data")
            event_equipment_data = load_event_equip_data()
            st.dataframe(event_equipment_data)

# Tab 2: Set 4 Day Plan
with tabs[1]:
    st.header("Set 4 Day Plan")
    # Check if event data is loaded
    if st.session_state.events_data is not None:
        # Initialize four_day_plan in session state if it doesn't exist
        if 'four_day_plan' not in st.session_state:
            st.session_state.four_day_plan = {1: [], 2: [], 3: [], 4: []}
        
        # Display instructions
        st.markdown("""
        Select 3 events for each day of the 4-day event. These events will be used as defaults for all teams.
        Each team can later modify their specific event details during event recording.
        """)
        
        # Get all unique events
        all_events = sorted(st.session_state.events_data['Event_Name'].unique())
        
        # Create columns for each day
        day_cols = st.columns(4)
        
        # For each day, create a selection interface
        for day in range(1, 5):
            with day_cols[day-1]:
                st.subheader(f"Day {day}")
                st.markdown("<small>Note: If you select JUNK YARD, it must be the only event for that day.</small>", unsafe_allow_html=True)
                
                # Initialize day events if not exists
                if f"day_{day}_events" not in st.session_state:
                    st.session_state[f"day_{day}_events"] = []
                
                # Display current selections
                st.write(f"**Selected Events ({len(st.session_state[f'day_{day}_events'])}/3):**")
                for i, event in enumerate(st.session_state[f"day_{day}_events"], 1):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.write(f"{i}. {event}")
                    with col2:
                        if st.button("🗑️", key=f"remove_{day}_{event}"):
                            st.session_state[f"day_{day}_events"].remove(event)
                            st.session_state.four_day_plan[day] = st.session_state[f"day_{day}_events"]
                            st.rerun()
                
                # Clear all button
                if st.button("Clear All", key=f"clear_all_{day}"):
                    st.session_state[f"day_{day}_events"] = []
                    st.session_state.four_day_plan[day] = []
                    st.rerun()
                
                # Add events section
                st.write("**Add Events:**")
                
                # Special handling for JUNK YARD
                if "JUNK YARD" in all_events:
                    if st.button("Add JUNK YARD (exclusive)", key=f"add_junkyard_{day}"):
                        st.session_state[f"day_{day}_events"] = ["JUNK YARD"]
                        st.session_state.four_day_plan[day] = ["JUNK YARD"]
                        st.rerun()
                
                # Add other events
                # Only show if JUNK YARD is not selected or max not reached
                if "JUNK YARD" not in st.session_state[f"day_{day}_events"] and len(st.session_state[f"day_{day}_events"]) < 3:
                    # Available events (excluding already selected ones and JUNK YARD)
                    available_events = [e for e in all_events if e != "JUNK YARD" and e not in st.session_state[f"day_{day}_events"]]
                    
                    if available_events:
                        selected_event = st.selectbox("Select an event to add:", available_events, key=f"event_select_{day}")
                        if st.button("Add Event", key=f"add_event_{day}"):
                            st.session_state[f"day_{day}_events"].append(selected_event)
                            st.session_state.four_day_plan[day] = st.session_state[f"day_{day}_events"]
                            st.rerun()
                
                # Update the main four_day_plan
                st.session_state.four_day_plan[day] = st.session_state[f"day_{day}_events"]
        
        # Button to save the 4-day plan
        st.markdown("---")
        if st.button("Save 4 Day Plan"):
            # Validate that each day has exactly 3 events (except for day with JUNK YARD)
            valid_plan = True
            junk_yard_day = None
            
            # Check if JUNK YARD is in any day's plan
            for day in range(1, 5):
                if 'JUNK YARD' in st.session_state.four_day_plan[day]:
                    junk_yard_day = day
                    # If JUNK YARD is selected, it should be the only event for that day
                    if len(st.session_state.four_day_plan[day]) > 1:
                        st.error(f"Day {day} has JUNK YARD selected. JUNK YARD must be the only event for its day.")
                        valid_plan = False
                        break
            
            # For all other days, ensure exactly 3 events
            for day in range(1, 5):
                if day != junk_yard_day:
                    if len(st.session_state.four_day_plan[day]) != 3:
                        st.error(f"Day {day} must have exactly 3 events. Please select exactly 3 events for each day without JUNK YARD.")
                        valid_plan = False
                        break
            
            if valid_plan:
                # Create a structured 4-day plan
                structured_plan = []
                
                for day in range(1, 5):
                    # If this is the JUNK YARD day, it's a special case
                    if day == junk_yard_day:
                        event_name = 'JUNK YARD'
                        event_details = st.session_state.events_data[
                            st.session_state.events_data['Event_Name'] == event_name
                        ].iloc[0].to_dict() if event_name in st.session_state.events_data['Event_Name'].values else None
                        
                        if event_details:
                            plan_entry = {
                                'Day': day,
                                'Event_Number': 1,  # Only event for this day
                                'Event_Name': event_name,
                                'Equipment_Name': event_details.get('Equipment_Name', 'MIXED EQUIPMENT'),
                                'Equipment_Weight': event_details.get('Equipment_Weight', 0),
                                'Number_of_Equipment': event_details.get('Number_of_Equipment', 0),
                                'Time_Limit': event_details.get('Time_Limit', '00:00'),
                                'Initial_Participants': event_details.get('Initial_Participants', 18),
                                'Distance': event_details.get('Distance', 0)
                            }
                            structured_plan.append(plan_entry)
                    else:
                        # Normal day with 3 events
                        for event_num, event_name in enumerate(st.session_state.four_day_plan[day], 1):
                            event_details = st.session_state.events_data[
                                st.session_state.events_data['Event_Name'] == event_name
                            ].iloc[0].to_dict() if event_name in st.session_state.events_data['Event_Name'].values else None
                            
                            if event_details:
                                plan_entry = {
                                    'Day': day,
                                    'Event_Number': event_num,
                                    'Event_Name': event_name,
                                    'Equipment_Name': event_details.get('Equipment_Name', 'MIXED EQUIPMENT'),
                                    'Equipment_Weight': event_details.get('Equipment_Weight', 0),
                                    'Number_of_Equipment': event_details.get('Number_of_Equipment', 0),
                                    'Time_Limit': event_details.get('Time_Limit', '00:00'),
                                    'Initial_Participants': event_details.get('Initial_Participants', 18),
                                    'Distance': event_details.get('Distance', 0)
                                }
                                structured_plan.append(plan_entry)
                
                # Store the structured plan
                st.session_state.structured_four_day_plan = pd.DataFrame(structured_plan)
                
                # Save the session to preserve the plan
                save_session_state()
                
                st.success("4 Day Plan saved successfully! These events will now be available as defaults for each team.")
                
                # Display the structured plan
                st.subheader("Structured 4 Day Plan")
                st.dataframe(st.session_state.structured_four_day_plan)
                
                # Add a download button
                csv = st.session_state.structured_four_day_plan.to_csv(index=False)
                b64 = base64.b64encode(csv.encode()).decode()
                href = f'<a href="data:file/csv;base64,{b64}" download="four_day_plan.csv">Download 4 Day Plan CSV</a>'
                st.markdown(href, unsafe_allow_html=True)
    else:
        st.warning("Please upload or select event data first to set up the 4-day plan.")

# Tab 3: Event Recording
with tabs[2]:
    st.header("Event Data Recording")
    
    # First, select the team for which we're recording data
    if st.session_state.roster_data is not None:
        # Get unique teams from roster data
        team_options = st.session_state.roster_data['Initial_Team'].unique().tolist()
        
        # After Day 2, include reshuffled teams if available
        if st.session_state.reshuffled_teams is not None:
            # Get the days that have been recorded so far
            recorded_days = []
            if not st.session_state.event_records.empty:
                recorded_days = st.session_state.event_records['Day'].unique().tolist()
            
            # If Days 1-2 have been recorded, include new teams for Days 3-4
            if 1 in recorded_days and 2 in recorded_days:
                new_team_options = st.session_state.reshuffled_teams['New_Team'].unique().tolist()
                team_options.extend([f"{team} (Days 3-4)" for team in new_team_options])
        
        selected_team = st.selectbox("Select Team", options=team_options)
    else:
        st.warning("Please upload roster data first to select a team.")
        selected_team = None
    
    # Create a form for event data input
    if selected_team is not None:
        # Determine if we're using original or reshuffled teams based on the selection
        using_reshuffled = "(Days 3-4)" in selected_team
        
        # Extract the base team name
        if using_reshuffled:
            team_name = selected_team.replace(" (Days 3-4)", "")
        else:
            team_name = selected_team
        
        with st.form("event_data_form"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Set day options based on whether we're using reshuffled teams
                if using_reshuffled:
                    day_options = [3, 4]
                    default_day = 3
                else:
                    day_options = [1, 2]
                    default_day = 1
                day = st.selectbox("Day", options=day_options, index=day_options.index(default_day))
                
                # If we have a 4-day plan, use it to filter event options
                has_four_day_plan = ('structured_four_day_plan' in st.session_state and 
                                    st.session_state.structured_four_day_plan is not None and
                                    isinstance(st.session_state.structured_four_day_plan, pd.DataFrame) and
                                    not st.session_state.structured_four_day_plan.empty)
                
                if has_four_day_plan:
                    try:
                        # Filter for events on the selected day
                        day_events = st.session_state.structured_four_day_plan[
                            st.session_state.structured_four_day_plan['Day'] == day
                        ]
                        
                        if not day_events.empty:
                            event_number_options = day_events['Event_Number'].unique().tolist()
                            event_number = st.selectbox(
                                "Event Number",
                                options=event_number_options,
                                key=f"event_num_{team_name}_{day}"
                            )
                            
                            # Get the event details for this day and event number
                            filtered_events = day_events[day_events['Event_Number'] == event_number]
                            if not filtered_events.empty:
                                event_details = filtered_events.iloc[0]
                                event_name = event_details['Event_Name']
                                # Display the event name (not selectable)
                                st.write(f"Event Name: {event_name}")
                                # Auto-fill other event details based on the 4-day plan
                                selected_event = event_details
                            else:
                                st.warning(f"No events found for Day {day}, Event Number {event_number}")
                                event_number = st.selectbox("Event Number", options=[1, 2, 3])
                                # Fallback to original event data
                                original_event_data_fallback = True
                        else:
                            # Fallback to regular event selection
                            st.warning(f"No events defined for Day {day} in the 4-day plan")
                            event_number = st.selectbox("Event Number", options=[1, 2, 3])
                            # Fallback to original event data
                            original_event_data_fallback = True
                    except Exception as e:
                        st.error(f"Error processing 4-day plan: {str(e)}")
                        event_number = st.selectbox("Event Number", options=[1, 2, 3])
                        original_event_data_fallback = True
                else:
                    # No 4-day plan, use regular event selection
                    event_number = st.selectbox("Event Number", options=[1, 2, 3])
                    original_event_data_fallback = True
                
                # Use original event data as fallback if needed
                if 'original_event_data_fallback' in locals() and original_event_data_fallback:
                    # Filter events based on day and event number
                    if st.session_state.events_data is not None:
                        filtered_events = st.session_state.events_data[
                            (st.session_state.events_data['Day'] == day) &
                            (st.session_state.events_data['Event_Number'] == event_number)
                        ]
                        if not filtered_events.empty:
                            event_name = st.selectbox(
                                "Event Name",
                                options=filtered_events['Event_Name'].unique()
                            )
                            # Auto-fill other event details based on selection
                            selected_event = filtered_events[filtered_events['Event_Name'] == event_name].iloc[0]
                        else:
                            event_name = st.text_input("Event Name")
                            selected_event = None
                    else:
                        event_name = st.text_input("Event Name")
                        selected_event = None
            
            with col2:
                if selected_event is not None:
                    equipment_name = st.text_input(
                        "Equipment Name", 
                        value=selected_event.get('Equipment_Name', '')
                    )
                    equipment_weight = st.number_input(
                        "Equipment Weight (lbs)", 
                        value=float(selected_event.get('Equipment_Weight', 0))
                    )
                    num_equipment = st.number_input(
                        "Number of Equipment", 
                        value=int(selected_event.get('Number_of_Equipment', 1)),
                        min_value=1
                    )
                    distance_km = st.number_input(
                        "Distance (km)", 
                        value=float(selected_event.get('Distance', 0))
                    )
                else:
                    equipment_name = st.text_input("Equipment Name")
                    equipment_weight = st.number_input("Equipment Weight (lbs)", min_value=0.0)
                    num_equipment = st.number_input("Number of Equipment", min_value=1)
                    distance_km = st.number_input("Distance (km)", min_value=0.0)
            
            with col3:
                heat_category = st.selectbox("Heat Category", options=[1, 2, 3, 4, 5])
                
                if selected_event is not None:
                    time_limit_str = selected_event.get('Time_Limit', '00:00')
                else:
                    time_limit_str = '00:00'
                
                # Display time limit for reference
                st.text(f"Time Limit: {time_limit_str}")
                
                # Input start and end times in military format
                start_time = st.text_input("Start Time (HH:MM)", placeholder="e.g., 08:30")
                end_time = st.text_input("End Time (HH:MM)", placeholder="e.g., 11:45")
                
                # Get team size for initial participants default
                if using_reshuffled:
                    # Get count from reshuffled teams
                    team_size = len(st.session_state.reshuffled_teams[
                        st.session_state.reshuffled_teams['New_Team'] == team_name
                    ])
                else:
                    # Get count from original roster
                    team_size = len(st.session_state.roster_data[
                        st.session_state.roster_data['Initial_Team'] == team_name
                    ])
                
                initial_participants = st.number_input(
                    "Initial Participants", 
                    value=team_size,
                    min_value=0
                )
                drops = st.number_input("Drops", min_value=0)
            
            submit_button = st.form_submit_button("Record Event Data")
            
            if submit_button:
                # Calculate actual time duration from start and end times
                time_actual_min = calculate_duration_minutes(start_time, end_time)
                time_actual = minutes_to_mmss(time_actual_min)
                
                # Convert time limit to minutes for calculations
                time_limit_min = time_str_to_minutes(time_limit_str)
                
                # Calculate temperature multiplier based on heat category
                temp_multiplier = 1.0
                if heat_category == 4:
                    temp_multiplier = 1.15
                elif heat_category == 5:
                    temp_multiplier = 1.3
                
                # Calculate total weight
                total_weight = equipment_weight * num_equipment
                
                # Calculate difficulty scores
                initial_difficulty = calculate_initial_difficulty(
                    temp_multiplier, total_weight, initial_participants, 
                    distance_km, time_limit_min
                )
                
                # Filter drop data for this specific team and event
                team_drop_data = st.session_state.drop_data[
                    (st.session_state.drop_data['Team'] == team_name) &
                    (st.session_state.drop_data['Day'] == day) &
                    (st.session_state.drop_data['Event_Number'] == event_number) &
                    (st.session_state.drop_data['Event_Name'] == event_name)
                ] if 'Team' in st.session_state.drop_data.columns else pd.DataFrame()
                
                actual_difficulty = calculate_actual_difficulty(
                    temp_multiplier, total_weight, initial_participants, 
                    distance_km, time_actual_min, drops, 
                    team_drop_data, day, event_number, event_name,
                    start_time
                )
                
                # Create new record
                new_record = {
                    'Team': team_name,  # Store the team name
                    'Day': day,
                    'Event_Number': event_number,
                    'Event_Name': event_name,
                    'Equipment_Name': equipment_name,
                    'Equipment_Weight': equipment_weight,
                    'Number_of_Equipment': num_equipment,
                    'Distance_km': distance_km,
                    'Heat_Category': heat_category,
                    'Time_Limit': time_limit_str,
                    'Start_Time': start_time,
                    'End_Time': end_time,
                    'Time_Actual': time_actual,
                    'Time_Actual_Minutes': time_actual_min,
                    'Initial_Participants': initial_participants,
                    'Drops': drops,
                    'Initial_Difficulty': initial_difficulty,
                    'Actual_Difficulty': actual_difficulty,
                    'Temperature_Multiplier': temp_multiplier
                }
                
                # Check if we already have an entry for this team, day, event number, and event name
                existing_record = st.session_state.event_records[
                    (st.session_state.event_records['Team'] == team_name) &
                    (st.session_state.event_records['Day'] == day) &
                    (st.session_state.event_records['Event_Number'] == event_number) &
                    (st.session_state.event_records['Event_Name'] == event_name)
                ]
                
                if not existing_record.empty:
                    # Update the existing record
                    st.session_state.event_records.loc[existing_record.index[0]] = new_record
                    st.success(f"Event data updated for {team_name}, Day {day}, Event {event_number}: {event_name}")
                else:
                    # Add new record
                    st.session_state.event_records = pd.concat([
                        st.session_state.event_records, 
                        pd.DataFrame([new_record])
                    ], ignore_index=True)
                    st.success(f"Event data recorded for {team_name}, Day {day}, Event {event_number}: {event_name}")
                
                # Automatically save the session after recording data
                save_session_state()
        
        # After the form, display team-specific recorded events
        if not st.session_state.event_records.empty and 'Team' in st.session_state.event_records.columns:
            st.subheader(f"Recorded Events for {team_name}")
            
            # Filter event records for the selected team
            team_records = st.session_state.event_records[
                st.session_state.event_records['Team'] == team_name
            ]
            
            if not team_records.empty:
                st.dataframe(team_records)
            else:
                st.info(f"No events recorded yet for {team_name}.")
    
    # Display all recorded event data with team filter
    if not st.session_state.event_records.empty:
        st.subheader("All Recorded Event Data")
        
        if 'Team' in st.session_state.event_records.columns:
            # Get unique teams
            all_teams = st.session_state.event_records['Team'].unique().tolist()
            
            # Create a multiselect to filter by team
            selected_teams = st.multiselect(
                "Filter by Teams",
                options=all_teams,
                default=all_teams
            )
            
            # Filter event records by selected teams
            if selected_teams:
                filtered_records = st.session_state.event_records[
                    st.session_state.event_records['Team'].isin(selected_teams)
                ]
                st.dataframe(filtered_records)
            else:
                st.dataframe(st.session_state.event_records)
        else:
            st.dataframe(st.session_state.event_records)

# Tab 4: Drop Management
with tabs[3]:
    st.header("Drop Management")
    
    # First, select the team for which we're recording drops
    if st.session_state.roster_data is not None:
        # Get unique teams from roster data
        team_options = st.session_state.roster_data['Initial_Team'].unique().tolist()
        
        # After Day 2, include reshuffled teams if available
        if st.session_state.reshuffled_teams is not None:
            # Get the days that have been recorded so far
            recorded_days = []
            if not st.session_state.event_records.empty:
                recorded_days = st.session_state.event_records['Day'].unique().tolist()
            
            # If Days 1-2 have been recorded, include new teams for Days 3-4
            if 1 in recorded_days and 2 in recorded_days:
                new_team_options = st.session_state.reshuffled_teams['New_Team'].unique().tolist()
                team_options.extend([f"{team} (Days 3-4)" for team in new_team_options])
        
        selected_team = st.selectbox("Select Team", options=team_options, key="drop_team_select")
        
        # Determine if we're using original or reshuffled teams
        using_reshuffled = "(Days 3-4)" in selected_team
        
        # Extract the base team name
        if using_reshuffled:
            team_name = selected_team.replace(" (Days 3-4)", "")
        else:
            team_name = selected_team
    else:
        st.warning("Please upload roster data first to select a team.")
        selected_team = None
        team_name = None
    
    # Create a form for recording participant drops
    if selected_team is not None:
        with st.form("drop_data_form"):
            # Get participants for the selected team
            if using_reshuffled:
                # Get participants from reshuffled teams
                team_participants = st.session_state.reshuffled_teams[
                    st.session_state.reshuffled_teams['New_Team'] == team_name
                ]['Candidate_Name'].tolist()
            else:
                # Get participants from original roster
                team_participants = st.session_state.roster_data[
                    st.session_state.roster_data['Initial_Team'] == team_name
                ]['Candidate_Name'].tolist()
            
            participant = st.selectbox(
                "Participant", 
                options=team_participants
            )
            
            # Get roster number for the participant
            if using_reshuffled:
                roster_number = st.session_state.reshuffled_teams[
                    st.session_state.reshuffled_teams['Candidate_Name'] == participant
                ]['Roster_Number'].values[0]
            else:
                roster_number = st.session_state.roster_data[
                    st.session_state.roster_data['Candidate_Name'] == participant
                ]['Roster_Number'].values[0]
            
            # Select day based on team (Days 1-2 for original teams, Days 3-4 for reshuffled)
            day_options = [1, 2] if not using_reshuffled else [3, 4]
            day = st.selectbox("Day", options=day_options)
            
            # If we have a 4-day plan, use it to filter event options
            has_four_day_plan = ('structured_four_day_plan' in st.session_state and 
                                st.session_state.structured_four_day_plan is not None and
                                isinstance(st.session_state.structured_four_day_plan, pd.DataFrame) and
                                not st.session_state.structured_four_day_plan.empty)
            
            if has_four_day_plan:
                try:
                    day_events = st.session_state.structured_four_day_plan[
                        st.session_state.structured_four_day_plan['Day'] == day
                    ]
                    if not day_events.empty:
                        event_number = st.selectbox(
                            "Event Number",
                            options=day_events['Event_Number'].unique()
                        )
                        # Get the event details for this day and event number
                        event_details = day_events[
                            day_events['Event_Number'] == event_number
                        ]
                        if not event_details.empty:
                            event_name = st.selectbox(
                                "Event Name",
                                options=event_details['Event_Name'].unique()
                            )
                        else:
                            # Fallback to regular event selection
                            event_number = st.selectbox("Event Number", options=[1, 2, 3])
                            event_name = st.text_input("Event Name")
                    else:
                        # Fallback to regular event selection
                        event_number = st.selectbox("Event Number", options=[1, 2, 3])
                        event_name = st.text_input("Event Name")
                except Exception as e:
                    st.error(f"Error accessing 4-day plan: {str(e)}")
                    event_number = st.selectbox("Event Number", options=[1, 2, 3])
                    event_name = st.text_input("Event Name")
            else:
                # Fallback to regular event selection
                # Filter events for the selected day
                if st.session_state.events_data is not None:
                    day_events = st.session_state.events_data[
                        st.session_state.events_data['Day'] == day
                    ]
                    if not day_events.empty:
                        event_number = st.selectbox(
                            "Event Number",
                            options=day_events['Event_Number'].unique()
                        )
                        # Filter further by event number
                        event_options = day_events[
                            day_events['Event_Number'] == event_number
                        ]['Event_Name'].unique()
                        event_name = st.selectbox("Event Name", options=event_options)
                    else:
                        event_number = st.selectbox("Event Number", options=[1, 2, 3])
                        event_name = st.text_input("Event Name")
                else:
                    event_number = st.selectbox("Event Number", options=[1, 2, 3])
                    event_name = st.text_input("Event Name")
            
            # Check if there's an event record for this team and event
            if not st.session_state.event_records.empty and 'Team' in st.session_state.event_records.columns:
                team_event = st.session_state.event_records[
                    (st.session_state.event_records['Team'] == team_name) &
                    (st.session_state.event_records['Day'] == day) &
                    (st.session_state.event_records['Event_Number'] == event_number) &
                    (st.session_state.event_records['Event_Name'] == event_name)
                ]
                
                if not team_event.empty:
                    # Display event start time for reference
                    st.text(f"Event Start Time: {team_event.iloc[0]['Start_Time']}")
            
            # Input drop time in military format
            drop_time = st.text_input("Drop Time (HH:MM)", placeholder="e.g., 09:45")
            
            submit_drop = st.form_submit_button("Record Drop")
            
            if submit_drop:
                # Add to drop data
                new_drop = {
                    'Team': team_name,
                    'Participant_Name': participant,
                    'Roster_Number': roster_number,
                    'Event_Name': event_name,
                    'Drop_Time': drop_time,
                    'Day': day,
                    'Event_Number': event_number
                }
                
                st.session_state.drop_data = pd.concat([
                    st.session_state.drop_data, 
                    pd.DataFrame([new_drop])
                ], ignore_index=True)
                
                st.success(f"Drop recorded successfully for {participant} from {team_name} during {event_name}")
                
                # Automatically save the session after recording data
                save_session_state()
        
        # Display team-specific drop data
        if not st.session_state.drop_data.empty and 'Team' in st.session_state.drop_data.columns:
            st.subheader(f"Recorded Drops for {team_name}")
            
            # Filter drop data for the selected team
            team_drops = st.session_state.drop_data[
                st.session_state.drop_data['Team'] == team_name
            ]
            
            if not team_drops.empty:
                st.dataframe(team_drops)
            else:
                st.info(f"No drops recorded yet for {team_name}.")
    
    # Display all drop data with team filter
    if not st.session_state.drop_data.empty:
        st.subheader("All Recorded Drop Data")
        
        if 'Team' in st.session_state.drop_data.columns:
            # Get unique teams
            all_teams = st.session_state.drop_data['Team'].unique().tolist()
            
            # Create a multiselect to filter by team
            selected_teams = st.multiselect(
                "Filter by Teams",
                options=all_teams,
                default=all_teams,
                key="drop_team_filter"
            )
            
            # Filter drop data by selected teams
            if selected_teams:
                filtered_drops = st.session_state.drop_data[
                    st.session_state.drop_data['Team'].isin(selected_teams)
                ]
                st.dataframe(filtered_drops)
            else:
                st.dataframe(st.session_state.drop_data)
        else:
            st.dataframe(st.session_state.drop_data)

# Tab 5: Team Reshuffling
with tabs[4]:
    st.header("Team Reshuffling After Day 2")
    
    # Check if we have data for Days 1 and 2
    if not st.session_state.event_records.empty:
        days_1_2_data = st.session_state.event_records[
            st.session_state.event_records['Day'].isin([1, 2])
        ]
        
        if not days_1_2_data.empty and st.session_state.roster_data is not None:
            if st.button("Reshuffle Teams for Days 3 and 4"):
                # Get the list of participants who haven't dropped
                if not st.session_state.drop_data.empty:
                    all_drops = st.session_state.drop_data['Participant_Name'].unique()
                    active_participants = st.session_state.roster_data[
                        ~st.session_state.roster_data['Candidate_Name'].isin(all_drops)
                    ]
                else:
                    active_participants = st.session_state.roster_data.copy()
                
                # Calculate difficulty scores for each team
                if 'Team' in st.session_state.event_records.columns:
                    # Group by team and calculate average difficulty
                    team_difficulty = days_1_2_data.groupby('Team')['Actual_Difficulty'].mean().reset_index()
                    
                    # For teams without specific data, use overall average
                    overall_avg = days_1_2_data['Actual_Difficulty'].mean()
                    
                    # Get all teams from roster
                    all_teams = st.session_state.roster_data['Initial_Team'].unique()
                    
                    # Create a complete team difficulty dataframe
                    complete_team_difficulty = []
                    for team in all_teams:
                        if team in team_difficulty['Team'].values:
                            team_avg = team_difficulty[team_difficulty['Team'] == team]['Actual_Difficulty'].values[0]
                        else:
                            team_avg = overall_avg
                        
                        complete_team_difficulty.append({
                            'Team': team,
                            'Difficulty_Score': team_avg
                        })
                    
                    team_difficulty_df = pd.DataFrame(complete_team_difficulty)
                else:
                    # If no team-specific data, use overall event data
                    team_difficulty_scores = days_1_2_data.groupby(['Day', 'Event_Number'])['Actual_Difficulty'].mean().reset_index()
                    team_difficulty_df = None
                
                # Reshuffle teams based on difficulty scores
                st.session_state.reshuffled_teams = reshuffle_teams(
                    active_participants,
                    team_difficulty_df
                )
                
                st.success("Teams reshuffled successfully for Days 3 and 4!")
                
                # Automatically save the session after reshuffling
                save_session_state()
            
            # Display reshuffled teams if available
            if st.session_state.reshuffled_teams is not None:
                st.subheader("New Team Assignments for Days 3 and 4")
                st.dataframe(st.session_state.reshuffled_teams)
                
                # Download button for reshuffled teams
                csv = st.session_state.reshuffled_teams.to_csv(index=False)
                b64 = base64.b64encode(csv.encode()).decode()
                href = f'<a href="data:file/csv;base64,{b64}" download="reshuffled_teams.csv">Download Reshuffled Teams CSV</a>'
                st.markdown(href, unsafe_allow_html=True)
        else:
            st.warning("Please record event data for Days 1 and 2 before reshuffling teams.")
    else:
        st.warning("No event data available. Please record events for Days 1 and 2 first.")

# Tab 6: Adjust Difficulty
with tabs[5]:
    st.header("Adjust Difficulty for Days 3 and 4")
    
    # Check if teams have been reshuffled
    if st.session_state.reshuffled_teams is not None and not st.session_state.event_records.empty:
        st.subheader("Calculate Target Difficulty Scores")
        
        # Get the average difficulty scores from Days 1 and 2
        days_1_2_data = st.session_state.event_records[
            st.session_state.event_records['Day'].isin([1, 2])
        ]
        
        avg_difficulty = days_1_2_data['Actual_Difficulty'].mean()
        
        st.write(f"Average Difficulty Score from Days 1 and 2: {avg_difficulty:.2f}")
        
        # Form for adjusting difficulty
        with st.form("adjust_difficulty_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                day = st.selectbox("Day to Adjust", options=[3, 4])
                event_number = st.selectbox("Event Number to Adjust", options=[1, 2, 3])
                
                # Filter events based on day and event number
                if st.session_state.events_data is not None:
                    filtered_events = st.session_state.events_data[
                        (st.session_state.events_data['Day'] == day) & 
                        (st.session_state.events_data['Event_Number'] == event_number)
                    ]
                    
                    if not filtered_events.empty:
                        event_name = st.selectbox(
                            "Event Name", 
                            options=filtered_events['Event_Name'].unique()
                        )
                        
                        # Get event details
                        event_details = filtered_events[
                            filtered_events['Event_Name'] == event_name
                        ].iloc[0]
                    else:
                        st.warning(f"No events found for Day {day}, Event {event_number}")
                        event_name = st.text_input("Event Name")
                        event_details = None
                else:
                    event_name = st.text_input("Event Name")
                    event_details = None
            
            with col2:
                if event_details is not None:
                    # Display current values
                    st.write(f"Current Equipment: {event_details['Equipment_Name']}")
                    st.write(f"Current Weight: {event_details['Equipment_Weight']} lbs")
                    st.write(f"Current Distance: {event_details['Distance']} km")
                    st.write(f"Current Time Limit: {event_details['Time_Limit']}")
                    
                    # Get target difficulty
                    target_multiplier = st.slider(
                        "Difficulty Adjustment Multiplier", 
                        min_value=0.5, 
                        max_value=1.5, 
                        value=1.0, 
                        step=0.05
                    )
                    
                    target_difficulty = avg_difficulty * target_multiplier
                    st.write(f"Target Difficulty Score: {target_difficulty:.2f}")
                    
                    # Heat category for temperature multiplier
                    heat_category = st.selectbox(
                        "Heat Category", 
                        options=[1, 2, 3, 4, 5],
                        index=0
                    )
                    
                    # Calculate temperature multiplier
                    temp_multiplier = 1.0
                    if heat_category == 4:
                        temp_multiplier = 1.15
                    elif heat_category == 5:
                        temp_multiplier = 1.3
                    
                    # Number of participants
                    num_participants = st.number_input(
                        "Number of Participants",
                        value=int(event_details['Initial_Participants']),
                        min_value=1
                    )
                    
                    # Choose adjustment method
                    adjustment_method = st.radio(
                        "Adjustment Method",
                        options=["Adjust Weight", "Adjust Distance", "Adjust Both"]
                    )
                else:
                    st.warning("Please select a valid event to adjust difficulty.")
                    adjustment_method = st.radio(
                        "Adjustment Method",
                        options=["Adjust Weight", "Adjust Distance", "Adjust Both"]
                    )
            
            submit_adjustment = st.form_submit_button("Calculate Adjustments")
            
            if submit_adjustment and event_details is not None:
                # Get current values
                current_weight = event_details['Equipment_Weight'] * event_details['Number_of_Equipment']
                current_distance = event_details['Distance']
                time_limit_min = time_str_to_minutes(event_details['Time_Limit'])
                
                # Calculate adjustments based on method selected
                if adjustment_method == "Adjust Weight":
                    new_weight = adjust_equipment_weight(
                        target_difficulty, temp_multiplier, current_distance,
                        time_limit_min, num_participants
                    )
                    
                    st.success(f"New Equipment Weight: {new_weight:.2f} lbs total " + 
                               f"({new_weight / event_details['Number_of_Equipment']:.2f} lbs per item)")
                    
                    # Create adjusted event entry
                    adjusted_event = event_details.copy()
                    adjusted_event['Equipment_Weight'] = new_weight / event_details['Number_of_Equipment']
                    adjusted_event['Target_Difficulty'] = target_difficulty
                    
                elif adjustment_method == "Adjust Distance":
                    new_distance = adjust_distance(
                        target_difficulty, temp_multiplier, current_weight,
                        time_limit_min, num_participants
                    )
                    
                    st.success(f"New Distance: {new_distance:.2f} km")
                    
                    # Create adjusted event entry
                    adjusted_event = event_details.copy()
                    adjusted_event['Distance'] = new_distance
                    adjusted_event['Target_Difficulty'] = target_difficulty
                    
                else:  # Adjust Both
                    # Adjust both proportionally
                    weight_adjust_ratio = 0.5  # 50% adjustment to weight
                    distance_adjust_ratio = 0.5  # 50% adjustment to distance
                    
                    # Calculate intermediate target difficulty for each component
                    weight_target = avg_difficulty * (1 + (target_multiplier - 1) * weight_adjust_ratio)
                    distance_target = avg_difficulty * (1 + (target_multiplier - 1) * distance_adjust_ratio)
                    
                    new_weight = adjust_equipment_weight(
                        weight_target, temp_multiplier, current_distance,
                        time_limit_min, num_participants
                    )
                    
                    new_distance = adjust_distance(
                        distance_target, temp_multiplier, new_weight,
                        time_limit_min, num_participants
                    )
                    
                    st.success(f"New Equipment Weight: {new_weight:.2f} lbs total " + 
                               f"({new_weight / event_details['Number_of_Equipment']:.2f} lbs per item)")
                    st.success(f"New Distance: {new_distance:.2f} km")
                    
                    # Create adjusted event entry
                    adjusted_event = event_details.copy()
                    adjusted_event['Equipment_Weight'] = new_weight / event_details['Number_of_Equipment']
                    adjusted_event['Distance'] = new_distance
                    adjusted_event['Target_Difficulty'] = target_difficulty
                
                # Store adjusted event for reference
                if 'adjusted_events' not in st.session_state:
                    st.session_state.adjusted_events = []
                
                st.session_state.adjusted_events.append(adjusted_event)
                
                # Automatically save the session after adjusting difficulty
                save_session_state()
    else:
        st.warning("Please reshuffle teams first before adjusting difficulty for Days 3 and 4.")
    
    # Display adjusted events if available
    if 'adjusted_events' in st.session_state and st.session_state.adjusted_events:
        st.subheader("Adjusted Events for Days 3 and 4")
        adjusted_df = pd.DataFrame(st.session_state.adjusted_events)
        st.dataframe(adjusted_df)
        
        # Download button for adjusted events
        csv = adjusted_df.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="adjusted_events.csv">Download Adjusted Events CSV</a>'
        st.markdown(href, unsafe_allow_html=True)

# Tab 7: Final Scores
with tabs[6]:
    st.header("Final Difficulty Scores")
    
    if not st.session_state.event_records.empty:
        # Calculate final scores for each team
        if st.session_state.roster_data is not None and len(st.session_state.event_records) > 0:
            # Calculate team scores for days 1-2
            days_1_2_data = st.session_state.event_records[
                st.session_state.event_records['Day'].isin([1, 2])
            ]
            
            # Get original teams from roster data
            original_teams = st.session_state.roster_data[['Candidate_Name', 'Roster_Number', 'Initial_Team']].copy()
            original_teams['Team_Phase'] = 'Days 1-2'
            
            # Calculate difficulty scores by team for days 1-2
            if not days_1_2_data.empty:
                if 'Team' in days_1_2_data.columns:
                    # Calculate team-specific difficulty scores
                    team_difficulty_days_1_2 = days_1_2_data.groupby(['Team', 'Day'])['Actual_Difficulty'].mean().reset_index()
                    team_difficulty_days_1_2['Team_Phase'] = 'Days 1-2'
                else:
                    # Calculate overall difficulty scores by day
                    team_difficulty_days_1_2 = days_1_2_data.groupby('Day')['Actual_Difficulty'].mean().reset_index()
                    team_difficulty_days_1_2['Team_Phase'] = 'Days 1-2'
                
                st.subheader("Team Difficulty Scores for Days 1-2")
                st.dataframe(team_difficulty_days_1_2)
            
            # Calculate team scores for days 3-4
            days_3_4_data = st.session_state.event_records[
                st.session_state.event_records['Day'].isin([3, 4])
            ]
            
            if not days_3_4_data.empty and st.session_state.reshuffled_teams is not None:
                # Reshuffled teams data
                reshuffled_team_data = st.session_state.reshuffled_teams.copy()
                reshuffled_team_data['Team_Phase'] = 'Days 3-4'
                
                if 'Team' in days_3_4_data.columns:
                    # Calculate team-specific difficulty scores
                    team_difficulty_days_3_4 = days_3_4_data.groupby(['Team', 'Day'])['Actual_Difficulty'].mean().reset_index()
                    team_difficulty_days_3_4['Team_Phase'] = 'Days 3-4'
                else:
                    # Calculate overall difficulty scores by day
                    team_difficulty_days_3_4 = days_3_4_data.groupby('Day')['Actual_Difficulty'].mean().reset_index()
                    team_difficulty_days_3_4['Team_Phase'] = 'Days 3-4'
                
                st.subheader("Team Difficulty Scores for Days 3-4")
                st.dataframe(team_difficulty_days_3_4)
                
                # Combine all data for final scores
                all_team_difficulties = pd.concat([
                    team_difficulty_days_1_2,
                    team_difficulty_days_3_4
                ])
                
                # Calculate final team scores across all days
                if 'Team' in all_team_difficulties.columns:
                    final_team_scores = all_team_difficulties.groupby('Team')['Actual_Difficulty'].mean().reset_index()
                    final_team_scores.columns = ['Team', 'Average_Difficulty']
                    final_team_scores = final_team_scores.sort_values('Average_Difficulty', ascending=False)
                else:
                    final_team_scores = all_team_difficulties.groupby('Day')['Actual_Difficulty'].mean().reset_index()
                
                st.subheader("Final Team Difficulty Scores (All Days)")
                st.dataframe(final_team_scores)
                
                # Calculate individual participant scores
                st.subheader("Individual Participant Performance")
                st.write("Note: Individual participant scores are based on their team's performance.")
                
                # Create a combined dataframe with all participants and their teams
                all_participants = []
                
                # Add participants from Days 1-2
                for _, row in original_teams.iterrows():
                    participant_data = {
                        'Participant_Name': row['Candidate_Name'],
                        'Roster_Number': row['Roster_Number'],
                        'Team_Days_1_2': row['Initial_Team']
                    }
                    all_participants.append(participant_data)
                
                all_participants_df = pd.DataFrame(all_participants)
                
                # Add team assignments for Days 3-4
                if st.session_state.reshuffled_teams is not None:
                    reshuffled_assignments = st.session_state.reshuffled_teams[['Candidate_Name', 'New_Team']].copy()
                    reshuffled_assignments.columns = ['Participant_Name', 'Team_Days_3_4']
                    
                    # Merge with participant data
                    all_participants_df = pd.merge(
                        all_participants_df,
                        reshuffled_assignments,
                        on='Participant_Name',
                        how='left'
                    )
                
                # Display participant team assignments
                st.dataframe(all_participants_df)
            else:
                st.warning("Data for Days 3-4 not available yet or teams haven't been reshuffled.")
        else:
            st.warning("Please upload roster data and record event data to calculate final scores.")
    else:
        st.warning("No event data available. Please record events first.")

# Tab 8: Visualizations
with tabs[7]:
    st.header("Visualizations")
    
    if not st.session_state.event_records.empty:
        # 1. Difficulty score trends over 4 days
        st.subheader("Difficulty Score Trends Over 4 Days")
        
        difficulty_trends = st.session_state.event_records.groupby('Day')[['Initial_Difficulty', 'Actual_Difficulty']].mean().reset_index()
        
        fig1 = px.line(
            difficulty_trends, 
            x='Day', 
            y=['Initial_Difficulty', 'Actual_Difficulty'],
            title='Difficulty Score Trends Over 4 Days',
            labels={'value': 'Difficulty Score', 'variable': 'Type'},
            markers=True
        )
        st.plotly_chart(fig1, use_container_width=True)
        
        # 2. Team difficulty comparison (if team data is available)
        if 'Team' in st.session_state.event_records.columns:
            st.subheader("Team Difficulty Comparison")
            
            # Calculate average difficulty by team
            team_difficulty = st.session_state.event_records.groupby('Team')['Actual_Difficulty'].mean().reset_index()
            team_difficulty = team_difficulty.sort_values('Actual_Difficulty', ascending=False)
            
            fig_team = px.bar(
                team_difficulty,
                x='Team',
                y='Actual_Difficulty',
                title='Average Difficulty Score by Team',
                labels={'Actual_Difficulty': 'Average Difficulty Score'}
            )
            st.plotly_chart(fig_team, use_container_width=True)
        
        # 3. Team reshuffling visualization (if teams have been reshuffled)
        if st.session_state.reshuffled_teams is not None:
            st.subheader("Team Composition Before and After Reshuffling")
            
            # Get original team composition
            original_team_counts = st.session_state.roster_data.groupby('Initial_Team').size().reset_index(name='Count')
            original_team_counts['Phase'] = 'Before Reshuffling (Days 1-2)'
            
            # Get new team composition
            new_team_counts = st.session_state.reshuffled_teams.groupby('New_Team').size().reset_index(name='Count')
            new_team_counts = new_team_counts.rename(columns={'New_Team': 'Initial_Team'})
            new_team_counts['Phase'] = 'After Reshuffling (Days 3-4)'
            
            # Combine data
            team_composition = pd.concat([original_team_counts, new_team_counts])
            
            # Plot
            fig2 = px.bar(
                team_composition,
                x='Initial_Team',
                y='Count',
                color='Phase',
                barmode='group',
                title='Team Composition Before and After Reshuffling',
                labels={'Initial_Team': 'Team', 'Count': 'Number of Participants'}
            )
            st.plotly_chart(fig2, use_container_width=True)
            
            # 4. Difficulty score distributions by team
            st.subheader("Difficulty Score Distribution by Team")
            
            # For this visualization, we need to combine team information with event scores
            # For Days 1-2, use original teams
            if not st.session_state.event_records[st.session_state.event_records['Day'].isin([1, 2])].empty:
                days_1_2_events = st.session_state.event_records[st.session_state.event_records['Day'].isin([1, 2])]
                
                # Create a distribution plot for Days 1-2
                if 'Team' in days_1_2_events.columns:
                    fig3 = px.box(
                        days_1_2_events,
                        x='Team',
                        y='Actual_Difficulty',
                        title='Difficulty Score Distribution by Team for Days 1-2',
                        labels={'Actual_Difficulty': 'Difficulty Score'}
                    )
                else:
                    fig3 = px.box(
                        days_1_2_events,
                        x='Day',
                        y='Actual_Difficulty',
                        title='Difficulty Score Distribution for Days 1-2',
                        labels={'Actual_Difficulty': 'Difficulty Score'}
                    )
                st.plotly_chart(fig3, use_container_width=True)
            
            # For Days 3-4, use reshuffled teams
            if st.session_state.reshuffled_teams is not None and not st.session_state.event_records[st.session_state.event_records['Day'].isin([3, 4])].empty:
                days_3_4_events = st.session_state.event_records[st.session_state.event_records['Day'].isin([3, 4])]
                
                # Create a distribution plot for Days 3-4
                if 'Team' in days_3_4_events.columns:
                    fig4 = px.box(
                        days_3_4_events,
                        x='Team',
                        y='Actual_Difficulty',
                        title='Difficulty Score Distribution by Team for Days 3-4',
                        labels={'Actual_Difficulty': 'Difficulty Score'}
                    )
                else:
                    fig4 = px.box(
                        days_3_4_events,
                        x='Day',
                        y='Actual_Difficulty',
                        title='Difficulty Score Distribution for Days 3-4',
                        labels={'Actual_Difficulty': 'Difficulty Score'}
                    )
                st.plotly_chart(fig4, use_container_width=True)
        
        # 5. Final difficulty scores grouped by day
        st.subheader("Final Difficulty Scores by Day")
        
        if not st.session_state.event_records.empty:
            # Calculate average difficulty scores per day
            day_avg_difficulty = st.session_state.event_records.groupby('Day')['Actual_Difficulty'].mean().reset_index()
            
            # Plot
            fig5 = px.bar(
                day_avg_difficulty,
                x='Day',
                y='Actual_Difficulty',
                title='Final Average Difficulty Scores by Day',
                labels={'Actual_Difficulty': 'Average Difficulty Score'}
            )
            st.plotly_chart(fig5, use_container_width=True)
        
        # 6. Drops analysis
        if not st.session_state.drop_data.empty:
            st.subheader("Participant Drops Analysis")
            
            # Drops by day and event
            drops_by_day_event = st.session_state.drop_data.groupby(['Day', 'Event_Number']).size().reset_index(name='Number_of_Drops')
            
            fig6 = px.bar(
                drops_by_day_event,
                x='Day',
                y='Number_of_Drops',
                color='Event_Number',
                barmode='group',
                title='Number of Drops by Day and Event',
                labels={'Number_of_Drops': 'Number of Drops', 'Event_Number': 'Event Number'}
            )
            st.plotly_chart(fig6, use_container_width=True)
            
            # If team data is available, analyze drops by team
            if 'Team' in st.session_state.drop_data.columns:
                drops_by_team = st.session_state.drop_data.groupby('Team').size().reset_index(name='Number_of_Drops')
                drops_by_team = drops_by_team.sort_values('Number_of_Drops', ascending=False)
                
                fig7 = px.bar(
                    drops_by_team,
                    x='Team',
                    y='Number_of_Drops',
                    title='Number of Drops by Team',
                    labels={'Number_of_Drops': 'Number of Drops'}
                )
                st.plotly_chart(fig7, use_container_width=True)
    else:
        st.warning("No event data available for visualization. Please record events first.")

# Tab 9: Predictive Analytics
with tabs[8]:
    st.header("Predictive Analytics")
    
    if st.session_state.reshuffled_teams is not None and st.session_state.events_data is not None:
        st.subheader("Team Success Prediction")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Select team to analyze
            team_options = st.session_state.reshuffled_teams['New_Team'].unique()
            selected_team = st.selectbox("Select Team", options=team_options)
            
            # Get team composition
            team_composition = st.session_state.reshuffled_teams[
                st.session_state.reshuffled_teams['New_Team'] == selected_team
            ]
            
            st.write(f"Team Composition ({len(team_composition)} members):")
            st.write(f"OF Members: {sum(team_composition['Candidate_Type'] == 'OF')}")
            st.write(f"ADE Members: {sum(team_composition['Candidate_Type'] == 'ADE')}")
        
        with col2:
            # Select event to predict
            day_options = [3, 4]
            selected_day = st.selectbox("Select Day", options=day_options)
            
            event_options = st.session_state.events_data[
                st.session_state.events_data['Day'] == selected_day
            ]['Event_Name'].unique()
            
            selected_event = st.selectbox("Select Event", options=event_options)
            
            # Get event details
            event_details = st.session_state.events_data[
                (st.session_state.events_data['Day'] == selected_day) &
                (st.session_state.events_data['Event_Name'] == selected_event)
            ].iloc[0]
            
            # Calculate event difficulty
            heat_category = st.selectbox("Heat Category", options=[1, 2, 3, 4, 5])
            
            # Calculate temperature multiplier
            temp_multiplier = 1.0
            if heat_category == 4:
                temp_multiplier = 1.15
            elif heat_category == 5:
                temp_multiplier = 1.3
            
            # Calculate initial difficulty
            initial_difficulty = calculate_initial_difficulty(
                temp_multiplier, 
                event_details['Equipment_Weight'] * event_details['Number_of_Equipment'],
                event_details['Initial_Participants'],
                event_details['Distance'],
                time_str_to_minutes(event_details['Time_Limit'])
            )
            
            st.write(f"Event Difficulty: {initial_difficulty:.2f}")
        
        # Get past performance data if available
        past_performance = None
        if not st.session_state.event_records.empty:
            past_performance = st.session_state.event_records[
                st.session_state.event_records['Day'].isin([1, 2])
            ]
            
            # If we have team-specific data, filter for this team's original members
            if 'Team' in past_performance.columns:
                # Get original team for each member of the current team
                member_original_teams = []
                for _, member in team_composition.iterrows():
                    member_name = member['Candidate_Name']
                    if member_name in st.session_state.roster_data['Candidate_Name'].values:
                        original_team = st.session_state.roster_data[
                            st.session_state.roster_data['Candidate_Name'] == member_name
                        ]['Initial_Team'].values[0]
                        member_original_teams.append(original_team)
                
                # Filter past performance for these teams
                if member_original_teams:
                    past_performance = past_performance[
                        past_performance['Team'].isin(member_original_teams)
                    ]
        
        # Predict success rate
        success_rate = predict_team_success(team_composition, initial_difficulty, past_performance)
        
        # Display prediction
        st.subheader("Prediction Results")
        
        success_percentage = success_rate * 100
        
        # Create a gauge chart
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=success_percentage,
            title={'text': "Predicted Success Rate"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "green" if success_percentage > 70 else "yellow" if success_percentage > 50 else "red"},
                'steps': [
                    {'range': [0, 50], 'color': "lightgray"},
                    {'range': [50, 70], 'color': "gray"},
                    {'range': [70, 100], 'color': "darkgray"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 70
                }
            }
        ))
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Add interpretation
        if success_percentage > 80:
            st.success("This team has a high likelihood of success for this event.")
        elif success_percentage > 60:
            st.info("This team has a moderate likelihood of success for this event.")
        else:
            st.warning("This team may struggle with this event. Consider adjusting the event difficulty or team composition.")
        
        # Provide recommendations
        st.subheader("Recommendations")
        
        if success_percentage < 70:
            # Suggest difficulty adjustments
            st.write("Consider making one of the following adjustments:")
            
            # Calculate adjustments needed for 75% success rate
            target_difficulty = (team_composition.shape[0] * 0.9) * (1/3) - initial_difficulty
            
            # Suggest weight reduction
            weight_reduction = (initial_difficulty - target_difficulty) / (
                (event_details['Distance'] / time_str_to_minutes(event_details['Time_Limit'])) * 
                (temp_multiplier / event_details['Initial_Participants'])
            )
            
            if weight_reduction > 0:
                st.write(f"- Reduce equipment weight by approximately {abs(weight_reduction):.1f} lbs total")
            
            # Suggest distance reduction
            distance_reduction = (initial_difficulty - target_difficulty) / (
                (event_details['Equipment_Weight'] * event_details['Number_of_Equipment'] / 
                 event_details['Initial_Participants']) * 
                (temp_multiplier / time_str_to_minutes(event_details['Time_Limit']))
            )
            
            if distance_reduction > 0:
                st.write(f"- Reduce distance by approximately {abs(distance_reduction):.2f} km")
            
            # Suggest time extension
            time_extension = time_str_to_minutes(event_details['Time_Limit']) * (
                initial_difficulty / target_difficulty - 1
            )
            
            if time_extension > 0:
                extended_time = time_str_to_minutes(event_details['Time_Limit']) + time_extension
                st.write(f"- Extend time limit to approximately {minutes_to_mmss(extended_time)}")
        else:
            st.write("No adjustments needed. The team is well-prepared for this event.")
    else:
        st.warning("Please upload roster data, events data, and reshuffle teams first.")

# Add export functionality for all data
st.sidebar.header("Export Data")

if st.sidebar.button("Export All Data"):
    # Create a zip file with all data
    buffer = io.BytesIO()
    
    with zipfile.ZipFile(buffer, 'w') as zip_file:
        # Export roster data
        if st.session_state.roster_data is not None:
            zip_file.writestr('roster_data.csv', st.session_state.roster_data.to_csv(index=False))
        
        # Export equipment data
        if st.session_state.equipment_data is not None:
            zip_file.writestr('equipment_data.csv', st.session_state.equipment_data.to_csv(index=False))
        
        # Export events data
        if st.session_state.events_data is not None:
            zip_file.writestr('events_data.csv', st.session_state.events_data.to_csv(index=False))
        
        # Export event records
        if not st.session_state.event_records.empty:
            zip_file.writestr('event_records.csv', st.session_state.event_records.to_csv(index=False))
        
        # Export drop data
        if not st.session_state.drop_data.empty:
            zip_file.writestr('drop_data.csv', st.session_state.drop_data.to_csv(index=False))
        
        # Export reshuffled teams
        if st.session_state.reshuffled_teams is not None:
            zip_file.writestr('reshuffled_teams.csv', st.session_state.reshuffled_teams.to_csv(index=False))
        
        # Export 4-day plan
        if st.session_state.structured_four_day_plan is not None:
            zip_file.writestr('four_day_plan.csv', st.session_state.structured_four_day_plan.to_csv(index=False))
    
    # Provide download link
    buffer.seek(0)
    b64 = base64.b64encode(buffer.read()).decode()
    href = f'<a href="data:application/zip;base64,{b64}" download="team_performance_data.zip">Download All Data</a>'
    st.sidebar.markdown(href, unsafe_allow_html=True)

# About section in the sidebar
st.sidebar.header("About")
st.sidebar.info(
    """
    This app helps manage and analyze team performance during a 4-day event.
    
    Features:
    - Upload roster, equipment, and events data
    - Record event performance
    - Track participant drops
    - Reshuffle teams after Day 2
    - Adjust difficulty for Days 3 and 4
    - Calculate final scores
    - Visualize performance data
    """
)