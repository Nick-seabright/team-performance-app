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
# Get the absolute path of the current file (main.py)
script_dir = os.path.dirname(os.path.abspath(__file__))

# Navigate up one level to the project root
project_root = os.path.dirname(script_dir)

# Define data and save directories relative to project root
data_dir = os.path.join(project_root, 'data')
save_dir = os.path.join(project_root, 'saved_sessions')

# Create directories if they don't exist
os.makedirs(data_dir, exist_ok=True)
os.makedirs(save_dir, exist_ok=True)

# Also create a data directory in the app folder for compatibility
app_data_dir = os.path.join(script_dir, 'data')
os.makedirs(app_data_dir, exist_ok=True)

print(f"Data directory: {data_dir}")
print(f"App data directory: {app_data_dir}")
print(f"Save directory: {save_dir}")

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

# Create in-memory session data for download
def create_downloadable_session():
    # Create a zip file with all session data
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zip_file:
        # Add all DataFrames as CSV files
        if st.session_state.roster_data is not None:
            zip_file.writestr('roster_data.csv', st.session_state.roster_data.to_csv(index=False))
        if st.session_state.equipment_data is not None:
            zip_file.writestr('equipment_data.csv', st.session_state.equipment_data.to_csv(index=False))
        if st.session_state.events_data is not None:
            zip_file.writestr('events_data.csv', st.session_state.events_data.to_csv(index=False))
        if not st.session_state.event_records.empty:
            zip_file.writestr('event_records.csv', st.session_state.event_records.to_csv(index=False))
        if not st.session_state.drop_data.empty:
            zip_file.writestr('drop_data.csv', st.session_state.drop_data.to_csv(index=False))
        if st.session_state.reshuffled_teams is not None:
            zip_file.writestr('reshuffled_teams.csv', st.session_state.reshuffled_teams.to_csv(index=False))
        if st.session_state.structured_four_day_plan is not None:
            zip_file.writestr('four_day_plan.csv', st.session_state.structured_four_day_plan.to_csv(index=False))
        
        # Save the four_day_plan dictionary as JSON
        zip_file.writestr('four_day_plan_dict.json', json.dumps(st.session_state.four_day_plan))
        
        # Save metadata
        metadata = {
            'session_name': new_session_name,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'has_roster': st.session_state.roster_data is not None,
            'has_equipment': st.session_state.equipment_data is not None,
            'has_events': st.session_state.events_data is not None,
            'has_event_records': not st.session_state.event_records.empty,
            'has_drop_data': not st.session_state.drop_data.empty,
            'has_reshuffled_teams': st.session_state.reshuffled_teams is not None,
            'has_four_day_plan': st.session_state.structured_four_day_plan is not None
        }
        zip_file.writestr('metadata.json', json.dumps(metadata))
    
    buffer.seek(0)
    return buffer

# Download session button
if st.sidebar.button("Download Session to Computer"):
    session_data = create_downloadable_session()
    b64 = base64.b64encode(session_data.read()).decode()
    download_filename = f"{new_session_name.replace(' ', '_')}_session.zip"
    href = f'<a href="data:application/zip;base64,{b64}" download="{download_filename}">Click to download {new_session_name} session</a>'
    st.sidebar.markdown(href, unsafe_allow_html=True)
    st.sidebar.success(f"Session '{new_session_name}' ready for download! Click the link above.")

# Upload session from computer
uploaded_session = st.sidebar.file_uploader("Upload Session from Computer", type="zip")
if uploaded_session is not None:
    try:
        with zipfile.ZipFile(uploaded_session) as zip_ref:
            # Extract and load all files
            file_list = zip_ref.namelist()
            
            # Load roster data
            if 'roster_data.csv' in file_list:
                with zip_ref.open('roster_data.csv') as file:
                    st.session_state.roster_data = pd.read_csv(file)
            
            # Load equipment data
            if 'equipment_data.csv' in file_list:
                with zip_ref.open('equipment_data.csv') as file:
                    st.session_state.equipment_data = pd.read_csv(file)
            
            # Load events data
            if 'events_data.csv' in file_list:
                with zip_ref.open('events_data.csv') as file:
                    st.session_state.events_data = pd.read_csv(file)
            
            # Load event records
            if 'event_records.csv' in file_list:
                with zip_ref.open('event_records.csv') as file:
                    st.session_state.event_records = pd.read_csv(file)
            
            # Load drop data
            if 'drop_data.csv' in file_list:
                with zip_ref.open('drop_data.csv') as file:
                    st.session_state.drop_data = pd.read_csv(file)
            
            # Load reshuffled teams
            if 'reshuffled_teams.csv' in file_list:
                with zip_ref.open('reshuffled_teams.csv') as file:
                    st.session_state.reshuffled_teams = pd.read_csv(file)
            
            # Load four day plan
            if 'four_day_plan.csv' in file_list:
                with zip_ref.open('four_day_plan.csv') as file:
                    st.session_state.structured_four_day_plan = pd.read_csv(file)
            
            # Load four day plan dictionary
            if 'four_day_plan_dict.json' in file_list:
                with zip_ref.open('four_day_plan_dict.json') as file:
                    plan_dict = json.load(file)
                    # Convert string keys to integers for the dictionary
                    st.session_state.four_day_plan = {int(k): v for k, v in plan_dict.items()}
            
            # Load metadata
            if 'metadata.json' in file_list:
                with zip_ref.open('metadata.json') as file:
                    metadata = json.load(file)
                    st.session_state.session_name = metadata.get('session_name', 'uploaded_session')
            
            st.sidebar.success(f"Session '{st.session_state.session_name}' uploaded successfully!")
    except Exception as e:
        st.sidebar.error(f"Error uploading session: {str(e)}")

# For backward compatibility, keep the server-side saving
if st.sidebar.button("Save Current Session (Server)"):
    if save_session_state(new_session_name):
        st.sidebar.success(f"Session '{new_session_name}' saved to server!")

# Also keep server-side loading for local development
available_sessions = get_available_sessions()
if available_sessions:
    session_to_load = st.sidebar.selectbox(
        "Select Session to Load from Server",
        options=available_sessions
    )
    if st.sidebar.button("Load Selected Session"):
        if load_session_state(session_to_load):
            st.sidebar.success(f"Session '{session_to_load}' loaded successfully!")
else:
    st.sidebar.info("No saved sessions found on server.")

# Create tabs without the redundant Drop Management tab
tabs = st.tabs(["Data Upload", "Set 4 Day Plan", "Event Recording (Days 1-2)", "Team Reshuffling",
                "Adjust Difficulty", "Event Recording (Days 3-4)", "Final Scores", "Visualizations"])

# Tab 1: Data Upload
with tabs[0]:
    st.header("Upload Data")
    
    # Roster Upload
    st.subheader("Roster Upload")
    use_default_roster = st.checkbox("Use default roster data", value=True)
    
    if use_default_roster:
        # Check if we need to load the data
        if st.session_state.roster_data is None:
            # Try to load from the data folder
            script_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(os.path.dirname(script_dir), 'data')
            roster_path = os.path.join(data_dir, 'sample_roster.csv')
            
            if os.path.exists(roster_path):
                try:
                    st.session_state.roster_data = pd.read_csv(roster_path)
                    st.success(f"Default roster loaded with {len(st.session_state.roster_data)} participants.")
                except Exception as e:
                    st.error(f"Error loading default roster: {str(e)}")
                    # Fall back to generated data
                    st.session_state.roster_data = load_roster_data()
            else:
                st.session_state.roster_data = load_roster_data()
                st.success(f"Generated default roster with {len(st.session_state.roster_data)} participants.")
        else:
            st.success(f"Using loaded roster with {len(st.session_state.roster_data)} participants.")
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
        # Check if we need to load the data
        if st.session_state.equipment_data is None or st.session_state.events_data is None:
            # Try to load from the data folder
            script_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(os.path.dirname(script_dir), 'data')
            event_equipment_path = os.path.join(data_dir, 'event_equipment.csv')
            
            if os.path.exists(event_equipment_path):
                try:
                    # Load the raw event equipment data directly
                    event_equipment_data = pd.read_csv(event_equipment_path)
                    
                    # Process it to get equipment and events data
                    st.session_state.equipment_data = load_equipment_data()
                    st.session_state.events_data = load_events_data()
                    
                    st.success(f"Default event equipment data loaded.")
                    st.success(f"Generated equipment data with {len(st.session_state.equipment_data)} items.")
                    st.success(f"Generated events data with {len(st.session_state.events_data)} events.")
                except Exception as e:
                    st.error(f"Error loading default event data: {str(e)}")
                    # Try to generate the data using the utility functions
                    event_equipment_data = load_event_equip_data()
                    st.session_state.equipment_data = load_equipment_data()
                    st.session_state.events_data = load_events_data()
            else:
                # Load using the utility functions
                event_equipment_data = load_event_equip_data()
                st.session_state.equipment_data = load_equipment_data()
                st.session_state.events_data = load_events_data()
                
                st.success(f"Generated default event equipment data.")
                st.success(f"Generated equipment data with {len(st.session_state.equipment_data)} items.")
                st.success(f"Generated events data with {len(st.session_state.events_data)} events.")
        else:
            st.success(f"Using loaded equipment data with {len(st.session_state.equipment_data)} items.")
            st.success(f"Using loaded events data with {len(st.session_state.events_data)} events.")
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
                        # Safely access event details
                        junk_yard_data = st.session_state.events_data[
                            st.session_state.events_data['Event_Name'] == event_name
                        ]
                        
                        if not junk_yard_data.empty:
                            event_details = junk_yard_data.iloc[0].to_dict()
                            
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
                            # Safely access event details
                            event_data = st.session_state.events_data[
                                st.session_state.events_data['Event_Name'] == event_name
                            ]
                            
                            if not event_data.empty:
                                event_details = event_data.iloc[0].to_dict()
                                
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
        
        # Determine if we're using original or reshuffled teams based on the selection
        using_reshuffled = "(Days 3-4)" in selected_team
        # Extract the base team name
        if using_reshuffled:
            team_name = selected_team.replace(" (Days 3-4)", "")
            day_range = [3, 4]
            day_label = "Days 3-4"
        else:
            team_name = selected_team
            day_range = [1, 2]
            day_label = "Days 1-2"
        
        st.subheader(f"Recording Events for {team_name} - {day_label}")
        
        # Get team size for initial participants default
        if using_reshuffled:
            # Get count from reshuffled teams
            team_roster = st.session_state.reshuffled_teams[
                st.session_state.reshuffled_teams['New_Team'] == team_name
            ]
            team_size = len(team_roster)
        else:
            # Get count from original roster
            team_roster = st.session_state.roster_data[
                st.session_state.roster_data['Initial_Team'] == team_name
            ]
            team_size = len(team_roster)
        
        # Check if we have a 4-day plan
        has_four_day_plan = ('structured_four_day_plan' in st.session_state and 
                           st.session_state.structured_four_day_plan is not None and 
                           isinstance(st.session_state.structured_four_day_plan, pd.DataFrame) and 
                           not st.session_state.structured_four_day_plan.empty)
        
        # Prepare heat category options
        heat_categories = {
            1: "Heat Category 1 (no multiplier)",
            2: "Heat Category 2 (no multiplier)",
            3: "Heat Category 3 (no multiplier)",
            4: "Heat Category 4 (1.15x multiplier)",
            5: "Heat Category 5 (1.3x multiplier)"
        }
        
        # Create tabs for each day in the range
        day_tabs = st.tabs([f"Day {day}" for day in day_range])
        
        for i, day in enumerate(day_range):
            with day_tabs[i]:
                # Get events for this day from the 4-day plan
                day_events = []
                event_details_by_name = {}
                
                if has_four_day_plan:
                    day_plan = st.session_state.structured_four_day_plan[
                        st.session_state.structured_four_day_plan['Day'] == day
                    ]
                    if not day_plan.empty:
                        # Sort by event number
                        day_plan = day_plan.sort_values('Event_Number')
                        day_events = day_plan['Event_Name'].tolist()
                        
                        # Create a mapping of event names to details
                        for _, event in day_plan.iterrows():
                            event_details_by_name[event['Event_Name']] = event
                
                if not day_events:
                    st.warning(f"No events defined for Day {day} in the 4-day plan. Please set up the 4-day plan first.")
                    continue
                
                st.write(f"### Events for Day {day}")
                
                # Create an expander for each event
                for event_idx, event_name in enumerate(day_events):
                    event_number = event_idx + 1
                    event_details = event_details_by_name.get(event_name, {})
                    
                    # Calculate adjusted initial participants based on previous events
                    # This happens EVERY time the UI renders, for EACH event
                    adjusted_initial_participants = team_size  # Default to full team size
                    previous_drops = []
                    
                    # Get all drops for this team across all events up to this one
                    if not st.session_state.drop_data.empty:
                        all_team_drops = st.session_state.drop_data[
                            st.session_state.drop_data['Team'] == team_name
                        ]
                        
                        # Get drops from previous events (earlier days or earlier events on same day)
                        prev_drops_query = (
                            # Earlier day
                            (all_team_drops['Day'] < day) |
                            # Same day but earlier event
                            ((all_team_drops['Day'] == day) & (all_team_drops['Event_Number'] < event_number))
                        )
                        previous_drops_df = all_team_drops[prev_drops_query]
                        previous_drops = previous_drops_df['Roster_Number'].unique().tolist()
                        
                        # Calculate adjusted participants by removing those who dropped in previous events
                        if previous_drops:
                            # Get the participant list excluding previously dropped
                            current_participants = team_roster.copy()
                            current_participants = current_participants[
                                ~current_participants['Roster_Number'].isin(previous_drops)
                            ]
                            adjusted_initial_participants = len(current_participants)
                    
                    # Store this value in session state for use in the form
                    if 'adjusted_participants' not in st.session_state:
                        st.session_state.adjusted_participants = {}
                    participants_key = f"{team_name}_{day}_{event_number}"
                    st.session_state.adjusted_participants[participants_key] = adjusted_initial_participants
                    
                    # Check if we already have a record for this event
                    existing_record = pd.DataFrame()  # Default to empty DataFrame
                    
                    if not st.session_state.event_records.empty and 'Team' in st.session_state.event_records.columns:
                        existing_record = st.session_state.event_records[
                            (st.session_state.event_records['Team'] == team_name) &
                            (st.session_state.event_records['Day'] == day) &
                            (st.session_state.event_records['Event_Number'] == event_number) &
                            (st.session_state.event_records['Event_Name'] == event_name)
                        ]
                    
                    # Set the expander title based on whether we have existing data
                    if not existing_record.empty:
                        expander_title = f"Event {event_number}: {event_name} ✓"
                        expander_open = False  # Default closed if already recorded
                    else:
                        expander_title = f"Event {event_number}: {event_name}"
                        expander_open = True  # Default open if not recorded
                    
                    with st.expander(expander_title, expanded=expander_open):
                        # If we have existing data, show a summary
                        if not existing_record.empty:
                            record = existing_record.iloc[0]
                            st.success("Event already recorded. You can update the data if needed.")
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.write("**Time:**", f"{record['Start_Time']} - {record['End_Time']}")
                                st.write("**Duration:**", record['Time_Actual'])
                            with col2:
                                st.write("**Distance:**", f"{record['Distance_km']} km")
                                st.write("**Heat Category:**", record['Heat_Category'])
                            with col3:
                                st.write("**Participants:**", record['Initial_Participants'])
                                st.write("**Drops:**", record['Drops'])
                                st.write("**Difficulty:**", f"{record['Actual_Difficulty']:.2f}")
                        
                        # Create tabs for event data and drops management
                        event_data_tab, drops_tab = st.tabs(["Event Data", "Manage Drops"])
                        
                        # Drops Management Tab
                        with drops_tab:
                            st.write(f"### Manage Drops for {event_name}")
                            
                            # Display the current participants
                            st.write("#### Current Participants")
                            
                            try:
                                # Get all drops for this team across all events
                                all_team_drops = pd.DataFrame()
                                if not st.session_state.drop_data.empty:
                                    all_team_drops = st.session_state.drop_data[
                                        st.session_state.drop_data['Team'] == team_name
                                    ]
                                
                                # Get drops from previous events (earlier days or earlier events on same day)
                                previous_drops_df = pd.DataFrame()
                                if not all_team_drops.empty:
                                    # Previous events drops query
                                    prev_drops_query = (
                                        # Earlier day
                                        (all_team_drops['Day'] < day) |
                                        # Same day but earlier event
                                        ((all_team_drops['Day'] == day) & (all_team_drops['Event_Number'] < event_number))
                                    )
                                    previous_drops_df = all_team_drops[prev_drops_query]
                                    previous_drops = previous_drops_df['Roster_Number'].unique().tolist()
                                
                                # Get drops specific to this event
                                current_drops = []
                                current_drops_df = pd.DataFrame()
                                if not all_team_drops.empty:
                                    current_drops_df = all_team_drops[
                                        (all_team_drops['Day'] == day) &
                                        (all_team_drops['Event_Number'] == event_number) &
                                        (all_team_drops['Event_Name'] == event_name)
                                    ]
                                    current_drops = current_drops_df['Roster_Number'].tolist()
                                
                                # Get the participant list from the team roster
                                current_participants = team_roster.copy()
                                
                                # Filter out previously dropped participants
                                if previous_drops:
                                    current_participants = current_participants[
                                        ~current_participants['Roster_Number'].isin(previous_drops)
                                    ]
                                
                                # Further filter out those who dropped in this specific event
                                active_participants = current_participants.copy()
                                if current_drops:
                                    active_participants = active_participants[
                                        ~active_participants['Roster_Number'].isin(current_drops)
                                    ]
                                
                                # Show the adjusted initial participants count that will be used
                                st.write(f"**Initial participants for this event: {adjusted_initial_participants}**")
                                st.write(f"**Current drops for this event: {len(current_drops)}**")
                                st.write(f"**Remaining active participants: {adjusted_initial_participants - len(current_drops)}**")
                                
                                # Show the active participants with drop option
                                if not active_participants.empty:
                                    st.write(f"{len(active_participants)} active participants for this event:")
                                    
                                    # Create a selection for the participant to drop
                                    with st.form(f"drop_form_{day}_{event_number}"):
                                        # Select a participant to drop
                                        participant_options = active_participants['Candidate_Name'].tolist()
                                        if participant_options:
                                            drop_participant = st.selectbox(
                                                "Select participant to mark as dropped:",
                                                options=participant_options
                                            )
                                            
                                            # Get the roster number for this participant
                                            drop_roster_number = active_participants[
                                                active_participants['Candidate_Name'] == drop_participant
                                            ]['Roster_Number'].values[0]
                                            
                                            # Create a unique session state key for this drop time
                                            drop_time_key = f"drop_time_{team_name}_{day}_{event_number}"
                        
                                            # Initialize session state for this drop time if it doesn't exist
                                            if drop_time_key not in st.session_state:
                                                # Default to event start time if available, otherwise empty
                                                start_time_val = ""
                                                if not existing_record.empty:
                                                    start_time_val = existing_record.iloc[0]['Start_Time']
                                                
                                                st.session_state[drop_time_key] = start_time_val
                        
                                            # Create a callback to update the session state when the input changes
                                            def update_drop_time():
                                                # This will be called when the input changes
                                                pass  # The session state is automatically updated by Streamlit
                        
                                            # Enter drop time using session state to persist the value
                                            drop_time = st.text_input(
                                                "Drop Time (HH:MM)",
                                                key=drop_time_key,  # This key connects to the session state
                                                placeholder="e.g., 09:15",
                                                on_change=update_drop_time
                                            )
                                            
                                            # Submit button
                                            drop_submit = st.form_submit_button("Record Drop")
                                            
                                            if drop_submit:
                                                if drop_time:
                                                    try:
                                                        # Add to drop data
                                                        new_drop = {
                                                            'Team': team_name,
                                                            'Participant_Name': drop_participant,
                                                            'Roster_Number': drop_roster_number,
                                                            'Event_Name': event_name,
                                                            'Drop_Time': drop_time,
                                                            'Day': day,
                                                            'Event_Number': event_number
                                                        }
                                                        
                                                        # Create the drop_data DataFrame if it doesn't exist or is empty
                                                        if 'drop_data' not in st.session_state or st.session_state.drop_data.empty:
                                                            st.session_state.drop_data = pd.DataFrame([new_drop])
                                                        else:
                                                            # Check if this drop already exists
                                                            existing_drop = st.session_state.drop_data[
                                                                (st.session_state.drop_data['Team'] == team_name) &
                                                                (st.session_state.drop_data['Roster_Number'] == drop_roster_number) &
                                                                (st.session_state.drop_data['Day'] == day) &
                                                                (st.session_state.drop_data['Event_Number'] == event_number) &
                                                                (st.session_state.drop_data['Event_Name'] == event_name)
                                                            ]
                                                            
                                                            if existing_drop.empty:
                                                                # Add the new drop
                                                                st.session_state.drop_data = pd.concat([
                                                                    st.session_state.drop_data,
                                                                    pd.DataFrame([new_drop])
                                                                ], ignore_index=True)
                                                            else:
                                                                # Update the existing drop
                                                                st.session_state.drop_data.loc[existing_drop.index[0], 'Drop_Time'] = drop_time
                                                        
                                                        # Update the corresponding event record if it exists
                                                        if not st.session_state.event_records.empty:
                                                            event_record = st.session_state.event_records[
                                                                (st.session_state.event_records['Team'] == team_name) &
                                                                (st.session_state.event_records['Day'] == day) &
                                                                (st.session_state.event_records['Event_Number'] == event_number) &
                                                                (st.session_state.event_records['Event_Name'] == event_name)
                                                            ]
                                                            
                                                            if not event_record.empty:
                                                                # Get the current drops count
                                                                drops_query = (
                                                                    (st.session_state.drop_data['Team'] == team_name) &
                                                                    (st.session_state.drop_data['Day'] == day) &
                                                                    (st.session_state.drop_data['Event_Number'] == event_number) &
                                                                    (st.session_state.drop_data['Event_Name'] == event_name)
                                                                )
                                                                drops_count = len(st.session_state.drop_data[drops_query])
                                                                
                                                                # Update the drops count in the event record
                                                                st.session_state.event_records.loc[event_record.index[0], 'Drops'] = drops_count
                                                                
                                                                # Recalculate the actual difficulty with the new drops count
                                                                record = event_record.iloc[0]
                                                                temp_multiplier = record['Temperature_Multiplier']
                                                                total_weight = record['Equipment_Weight'] * record['Number_of_Equipment']
                                                                initial_participants = record['Initial_Participants']
                                                                distance_km = record['Distance_km']
                                                                time_actual_min = record['Time_Actual_Minutes']
                                                                
                                                                # Recalculate actual difficulty
                                                                actual_difficulty = calculate_actual_difficulty(
                                                                    temp_multiplier, total_weight, initial_participants,
                                                                    distance_km, time_actual_min, drops_count,
                                                                    st.session_state.drop_data[drops_query], day, event_number, event_name,
                                                                    record['Start_Time']
                                                                )
                                                                
                                                                # Update the actual difficulty
                                                                st.session_state.event_records.loc[event_record.index[0], 'Actual_Difficulty'] = actual_difficulty
                                                                
                                                        # Update ALL subsequent event records for this team to reflect the drop
                                                        if not st.session_state.event_records.empty:
                                                            # Get all events for this team that occur after the current event
                                                            subsequent_events = st.session_state.event_records[
                                                                (st.session_state.event_records['Team'] == team_name) &
                                                                (
                                                                    # Later day
                                                                    (st.session_state.event_records['Day'] > day) |
                                                                    # Same day but later event
                                                                    ((st.session_state.event_records['Day'] == day) & 
                                                                     (st.session_state.event_records['Event_Number'] > event_number))
                                                                )
                                                            ]
                                                            
                                                            # For each subsequent event, update the initial participants count
                                                            for idx, event_record in subsequent_events.iterrows():
                                                                # Calculate the updated initial participants for this subsequent event
                                                                event_day = event_record['Day']
                                                                event_num = event_record['Event_Number']
                                                                
                                                                # Get drops from events before this one
                                                                prev_drops_to_event = st.session_state.drop_data[
                                                                    (st.session_state.drop_data['Team'] == team_name) &
                                                                    (
                                                                        # Earlier day
                                                                        (st.session_state.drop_data['Day'] < event_day) |
                                                                        # Same day but earlier event
                                                                        ((st.session_state.drop_data['Day'] == event_day) & 
                                                                         (st.session_state.drop_data['Event_Number'] < event_num))
                                                                    )
                                                                ]['Roster_Number'].unique()
                                                                
                                                                # Calculate new initial participants count
                                                                updated_initial_participants = team_size - len(prev_drops_to_event)
                                                                
                                                                # Update the event record
                                                                st.session_state.event_records.loc[idx, 'Initial_Participants'] = updated_initial_participants
                                                                
                                                                # Recalculate difficulty scores with the updated initial participants
                                                                record = st.session_state.event_records.loc[idx]
                                                                
                                                                # Get current drop count for this event
                                                                event_drops = st.session_state.drop_data[
                                                                    (st.session_state.drop_data['Team'] == team_name) &
                                                                    (st.session_state.drop_data['Day'] == event_day) &
                                                                    (st.session_state.drop_data['Event_Number'] == event_num) &
                                                                    (st.session_state.drop_data['Event_Name'] == record['Event_Name'])
                                                                ]
                                                                drops_count = len(event_drops)
                                                                
                                                                # Recalculate initial difficulty
                                                                initial_difficulty = calculate_initial_difficulty(
                                                                    record['Temperature_Multiplier'], 
                                                                    record['Equipment_Weight'] * record['Number_of_Equipment'],
                                                                    updated_initial_participants,
                                                                    record['Distance_km'], 
                                                                    time_str_to_minutes(record['Time_Limit'])
                                                                )
                                                                
                                                                # Recalculate actual difficulty
                                                                actual_difficulty = calculate_actual_difficulty(
                                                                    record['Temperature_Multiplier'],
                                                                    record['Equipment_Weight'] * record['Number_of_Equipment'],
                                                                    updated_initial_participants,
                                                                    record['Distance_km'],
                                                                    record['Time_Actual_Minutes'],
                                                                    drops_count,
                                                                    event_drops,
                                                                    event_day,
                                                                    event_num,
                                                                    record['Event_Name'],
                                                                    record['Start_Time']
                                                                )
                                                                
                                                                # Update difficulty scores
                                                                st.session_state.event_records.loc[idx, 'Initial_Difficulty'] = initial_difficulty
                                                                st.session_state.event_records.loc[idx, 'Actual_Difficulty'] = actual_difficulty
                                                        
                                                        st.success(f"{drop_participant} marked as dropped at {drop_time}") 
                                                        
                                                        # Save session
                                                        save_session_state()
                                                        
                                                        # Need to rerun to refresh the UI
                                                        st.rerun()
                                                    except Exception as e:
                                                        st.error(f"Error recording drop: {str(e)}")
                                                else:
                                                    st.error("Please enter a valid drop time.")
                                        else:
                                            st.write("No participants available to drop.")
                                    
                                    # Display current active participants in a table format
                                    st.write("#### Active Participants List")
                                    active_display = active_participants[['Candidate_Name', 'Candidate_Type', 'Roster_Number']]
                                    active_display.columns = ['Participant', 'Type', 'Roster #']
                                    st.dataframe(active_display)
                                else:
                                    if previous_drops:
                                        st.warning(f"Initial participants for this event: {adjusted_initial_participants}")
                                        if len(current_drops) == adjusted_initial_participants:
                                            st.info("All participants have dropped from this event.")
                                        else:
                                            st.info("No active participants remaining for this event.")
                                    else:
                                        st.info("All participants have dropped from this event.")
                                
                                # If there are participants who dropped from previous events, show them
                                if previous_drops:
                                    st.write("#### Participants Dropped from Previous Events")
                                    
                                    if not previous_drops_df.empty:
                                        # Group by participant to show their last drop
                                        participant_last_drops = previous_drops_df.sort_values(['Day', 'Event_Number'], ascending=False)
                                        participant_last_drops = participant_last_drops.drop_duplicates('Roster_Number')
                                        
                                        # Create a nice display table
                                        prev_drop_display = participant_last_drops[['Participant_Name', 'Day', 'Event_Number', 'Event_Name']].copy()
                                        prev_drop_display.columns = ['Participant', 'Day', 'Event #', 'Dropped During']
                                        prev_drop_display = prev_drop_display.sort_values(['Day', 'Event #'])
                                        
                                        st.dataframe(prev_drop_display)
                                        st.info(f"These {len(prev_drop_display)} participants dropped from previous events and are not eligible for this event.")
                                
                                # Display the participants who have dropped in this specific event
                                st.write("#### Dropped Participants (This Event)")
                                
                                if not current_drops_df.empty:
                                    # Create a table of dropped participants
                                    st.write(f"{len(current_drops_df)} participants have dropped from this event:")
                                    
                                    # Create a dataframe for display
                                    drop_display = current_drops_df[['Participant_Name', 'Drop_Time']].copy()
                                    drop_display.columns = ['Participant', 'Drop Time']
                                    
                                    # Display the dataframe with a "Remove" button column
                                    st.dataframe(drop_display)
                                    
                                    # Add a form to remove drops with a unique key
                                    with st.form(f"remove_drop_form_{day}_{event_number}"):
                                        st.write("Remove a participant from the drop list:")
                                        
                                        # Select a participant to remove from drops
                                        remove_options = current_drops_df['Participant_Name'].tolist()
                                        if remove_options:
                                            participant_to_remove = st.selectbox(
                                                "Select participant:", 
                                                options=remove_options
                                            )
                                            
                                            # Get the roster number
                                            remove_roster_number = current_drops_df[
                                                current_drops_df['Participant_Name'] == participant_to_remove
                                            ]['Roster_Number'].values[0]
                                            
                                            # Submit button
                                            remove_submit = st.form_submit_button("Remove Drop")
                                            
                                            if remove_submit:
                                                try:
                                                    # Remove this drop from the drop_data
                                                    st.session_state.drop_data = st.session_state.drop_data[
                                                        ~((st.session_state.drop_data['Team'] == team_name) &
                                                        (st.session_state.drop_data['Day'] == day) &
                                                        (st.session_state.drop_data['Event_Number'] == event_number) &
                                                        (st.session_state.drop_data['Event_Name'] == event_name) &
                                                        (st.session_state.drop_data['Roster_Number'] == remove_roster_number))
                                                    ]
                                                    
                                                    # Update the corresponding event record if it exists
                                                    if not st.session_state.event_records.empty:
                                                        event_record = st.session_state.event_records[
                                                            (st.session_state.event_records['Team'] == team_name) &
                                                            (st.session_state.event_records['Day'] == day) &
                                                            (st.session_state.event_records['Event_Number'] == event_number) &
                                                            (st.session_state.event_records['Event_Name'] == event_name)
                                                        ]
                                                        
                                                        if not event_record.empty:
                                                            # Recalculate the current drops count
                                                            drops_query = (
                                                                (st.session_state.drop_data['Team'] == team_name) &
                                                                (st.session_state.drop_data['Day'] == day) &
                                                                (st.session_state.drop_data['Event_Number'] == event_number) &
                                                                (st.session_state.drop_data['Event_Name'] == event_name)
                                                            )
                                                            drops_count = len(st.session_state.drop_data[drops_query])
                                                            
                                                            # Update the drops count in the event record
                                                            st.session_state.event_records.loc[event_record.index[0], 'Drops'] = drops_count
                                                            
                                                            # Recalculate the actual difficulty with the updated drops count
                                                            record = event_record.iloc[0]
                                                            temp_multiplier = record['Temperature_Multiplier']
                                                            total_weight = record['Equipment_Weight'] * record['Number_of_Equipment']
                                                            initial_participants = record['Initial_Participants']
                                                            distance_km = record['Distance_km']
                                                            time_actual_min = record['Time_Actual_Minutes']
                                                            
                                                            # Recalculate actual difficulty
                                                            actual_difficulty = calculate_actual_difficulty(
                                                                temp_multiplier, total_weight, initial_participants,
                                                                distance_km, time_actual_min, drops_count,
                                                                st.session_state.drop_data[drops_query], day, event_number, event_name,
                                                                record['Start_Time']
                                                            )
                                                            
                                                            # Update the actual difficulty
                                                            st.session_state.event_records.loc[event_record.index[0], 'Actual_Difficulty'] = actual_difficulty
                                                    
                                                    # Update ALL subsequent event records for this team to reflect the removed drop
                                                    if not st.session_state.event_records.empty:
                                                        # Get all events for this team that occur after the current event
                                                        subsequent_events = st.session_state.event_records[
                                                            (st.session_state.event_records['Team'] == team_name) &
                                                            (
                                                                # Later day
                                                                (st.session_state.event_records['Day'] > day) |
                                                                # Same day but later event
                                                                ((st.session_state.event_records['Day'] == day) & 
                                                                 (st.session_state.event_records['Event_Number'] > event_number))
                                                            )
                                                        ]
                                                        
                                                        # For each subsequent event, update the initial participants count
                                                        for idx, event_record in subsequent_events.iterrows():
                                                            # Calculate the updated initial participants for this subsequent event
                                                            event_day = event_record['Day']
                                                            event_num = event_record['Event_Number']
                                                            
                                                            # Get drops from events before this one
                                                            prev_drops_to_event = st.session_state.drop_data[
                                                                (st.session_state.drop_data['Team'] == team_name) &
                                                                (
                                                                    # Earlier day
                                                                    (st.session_state.drop_data['Day'] < event_day) |
                                                                    # Same day but earlier event
                                                                    ((st.session_state.drop_data['Day'] == event_day) & 
                                                                     (st.session_state.drop_data['Event_Number'] < event_num))
                                                                )
                                                            ]['Roster_Number'].unique()
                                                            
                                                            # Calculate new initial participants count
                                                            updated_initial_participants = team_size - len(prev_drops_to_event)
                                                            
                                                            # Update the event record
                                                            st.session_state.event_records.loc[idx, 'Initial_Participants'] = updated_initial_participants
                                                            
                                                            # Recalculate difficulty scores with the updated initial participants
                                                            record = st.session_state.event_records.loc[idx]
                                                            
                                                            # Get current drop count for this event
                                                            event_drops = st.session_state.drop_data[
                                                                (st.session_state.drop_data['Team'] == team_name) &
                                                                (st.session_state.drop_data['Day'] == event_day) &
                                                                (st.session_state.drop_data['Event_Number'] == event_num) &
                                                                (st.session_state.drop_data['Event_Name'] == record['Event_Name'])
                                                            ]
                                                            drops_count = len(event_drops)
                                                            
                                                            # Recalculate initial difficulty
                                                            initial_difficulty = calculate_initial_difficulty(
                                                                record['Temperature_Multiplier'], 
                                                                record['Equipment_Weight'] * record['Number_of_Equipment'],
                                                                updated_initial_participants,
                                                                record['Distance_km'], 
                                                                time_str_to_minutes(record['Time_Limit'])
                                                            )
                                                            
                                                            # Recalculate actual difficulty
                                                            actual_difficulty = calculate_actual_difficulty(
                                                                record['Temperature_Multiplier'],
                                                                record['Equipment_Weight'] * record['Number_of_Equipment'],
                                                                updated_initial_participants,
                                                                record['Distance_km'],
                                                                record['Time_Actual_Minutes'],
                                                                drops_count,
                                                                event_drops,
                                                                event_day,
                                                                event_num,
                                                                record['Event_Name'],
                                                                record['Start_Time']
                                                            )
                                                            
                                                            # Update difficulty scores
                                                            st.session_state.event_records.loc[idx, 'Initial_Difficulty'] = initial_difficulty
                                                            st.session_state.event_records.loc[idx, 'Actual_Difficulty'] = actual_difficulty
                                                    
                                                    st.success(f"Removed drop for {participant_to_remove}")
                                                    
                                                    # Save session and refresh
                                                    save_session_state()
                                                    st.rerun()
                                                except Exception as e:
                                                    st.error(f"Error removing drop: {str(e)}")
                                        else:
                                            st.write("No participants to remove.")
                                else:
                                    st.info("No participants have dropped from this specific event yet.")
                                
                            except Exception as e:
                                st.error(f"Error in drop management: {str(e)}")
                                st.info("Please try refreshing the page if you encounter issues with drop management.")
                        
                        # Event Data Tab
                        with event_data_tab:
                            # Create a form for each event
                            with st.form(f"event_form_{team_name}_{day}_{event_number}"):
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    # Display event details
                                    st.write(f"**Event Name:** {event_name}")
                                    time_limit = event_details.get('Time_Limit', '00:00')
                                    st.write(f"**Time Limit:** {time_limit}")
                                    
                                    # Get equipment details
                                    equipment_key = f"equipment_{day}_{event_name}_{event_number}"
                                    if equipment_key not in st.session_state:
                                        # Initialize equipment from event details or 4-day plan
                                        event_equipment = load_event_equip_data()
                                        if not event_equipment.empty and 'EventName' in event_equipment.columns:
                                            if event_name in event_equipment['EventName'].values:
                                                event_id = event_equipment[event_equipment['EventName'] == event_name]['EventID'].unique()[0]
                                                equipment_items = event_equipment[event_equipment['EventID'] == event_id]
                                                st.session_state[equipment_key] = equipment_items.copy()
                                            else:
                                                # Fallback to basic equipment
                                                basic_equipment = pd.DataFrame([{
                                                    'EquipmentName': event_details.get('Equipment_Name', 'Generic Equipment'),
                                                    'EquipWt': event_details.get('Equipment_Weight', 0),
                                                    'EquipNum': event_details.get('Number_of_Equipment', 1),
                                                    'AppRatio': 1,
                                                    'AppRatioWT': event_details.get('Equipment_Weight', 0) * event_details.get('Number_of_Equipment', 1)
                                                }])
                                                st.session_state[equipment_key] = basic_equipment
                                        else:
                                            # Fallback to basic equipment
                                            basic_equipment = pd.DataFrame([{
                                                'EquipmentName': event_details.get('Equipment_Name', 'Generic Equipment'),
                                                'EquipWt': event_details.get('Equipment_Weight', 0),
                                                'EquipNum': event_details.get('Number_of_Equipment', 1),
                                                'AppRatio': 1,
                                                'AppRatioWT': event_details.get('Equipment_Weight', 0) * event_details.get('Number_of_Equipment', 1)
                                            }])
                                            st.session_state[equipment_key] = basic_equipment
                                    
                                    # Display equipment list
                                    st.write("**Equipment:**")
                                    equipment_list = st.session_state[equipment_key]
                                    total_weight = 0
                                    
                                    for i, equip in enumerate(equipment_list.iterrows()):
                                        equip_idx = equip[0]
                                        equip = equip[1]
                                        
                                        col_name, col_weight, col_qty = st.columns([3, 1, 1])
                                        with col_name:
                                            st.text(equip['EquipmentName'])
                                        with col_weight:
                                            st.text(f"{equip['EquipWt']} lbs")
                                        with col_qty:
                                            # Set default qty from existing record if available
                                            default_qty = int(equip['EquipNum'])
                                            if not existing_record.empty:
                                                # Try to parse equipment details from existing record
                                                try:
                                                    equip_details = existing_record.iloc[0].get('Equipment_Details', '')
                                                    if equip_details:
                                                        import json
                                                        equip_details = json.loads(equip_details.replace("'", "\""))
                                                        for item in equip_details:
                                                            if item['Name'] == equip['EquipmentName']:
                                                                default_qty = int(item['Quantity'])
                                                                break
                                                except:
                                                    pass
                                            
                                            new_qty = st.number_input(
                                                f"Qty",
                                                value=default_qty,
                                                min_value=0,
                                                key=f"qty_{team_name}_{day}_{event_name}_{event_number}_{i}"
                                            )
                                            
                                            if new_qty != equip['EquipNum']:
                                                equipment_list.at[equip_idx, 'EquipNum'] = new_qty
                                                app_ratio = equip['AppRatio'] if 'AppRatio' in equip and equip['AppRatio'] > 0 else 1
                                                equipment_list.at[equip_idx, 'AppRatioWT'] = equip['EquipWt'] * new_qty * (app_ratio / 100 if app_ratio > 10 else app_ratio)
                                        
                                        # Calculate total for this item
                                        item_total = equipment_list.at[equip_idx, 'AppRatioWT']
                                        total_weight += item_total
                                    
                                    st.markdown(f"**Total Adjusted Weight: {total_weight:.2f} lbs**")
                                    
                                    # Distance input with default from existing record or event details
                                    default_distance = event_details.get('Distance', 0)
                                    if not existing_record.empty:
                                        default_distance = existing_record.iloc[0]['Distance_km']
                                    
                                    distance_km = st.number_input(
                                        "Distance (km)",
                                        value=float(default_distance),
                                        min_value=0.0,
                                        key=f"distance_{team_name}_{day}_{event_name}"
                                    )
                                
                                with col2:
                                    # Heat category with default from existing record
                                    default_heat = 1
                                    if not existing_record.empty:
                                        default_heat = existing_record.iloc[0]['Heat_Category']
                                    
                                    heat_category = st.selectbox(
                                        "Heat Category",
                                        options=list(heat_categories.keys()),
                                        format_func=lambda x: heat_categories[x],
                                        index=default_heat-1,
                                        key=f"heat_{team_name}_{day}_{event_name}"
                                    )
                                    
                                    # Start and end times with defaults from existing record
                                    default_start = ""
                                    default_end = ""
                                    if not existing_record.empty:
                                        default_start = existing_record.iloc[0]['Start_Time']
                                        default_end = existing_record.iloc[0]['End_Time']
                                    
                                    start_time = st.text_input(
                                        "Start Time (HH:MM)", 
                                        value=default_start,
                                        placeholder="e.g., 08:30",
                                        key=f"start_{team_name}_{day}_{event_name}"
                                    )
                                    
                                    end_time = st.text_input(
                                        "End Time (HH:MM)", 
                                        value=default_end,
                                        placeholder="e.g., 11:45",
                                        key=f"end_{team_name}_{day}_{event_name}"
                                    )
                                    
                                    # Initial participants with default based on the freshly calculated value
                                    # Calculate initial participants based on the ending count from the previous event
                                    default_participants = team_size  # Default to full team size for the first event
                                    
                                    # Determine the previous event (regardless of whether we have a record for it)
                                    prev_day = day
                                    prev_event_num = event_number - 1
                                    
                                    # If this is the first event of the day, look at the last event of the previous day
                                    if prev_event_num < 1:
                                        prev_day = day - 1
                                        # Assume 3 events per day as default
                                        prev_event_num = 3
                                        # Try to find the actual last event number for the previous day
                                        if not st.session_state.event_records.empty:
                                            prev_day_events = st.session_state.event_records[
                                                (st.session_state.event_records['Team'] == team_name) &
                                                (st.session_state.event_records['Day'] == prev_day)
                                            ]
                                            if not prev_day_events.empty:
                                                prev_event_num = int(prev_day_events['Event_Number'].max())
                                    
                                    # Now try to find a record for this previous event
                                    previous_event_record = None
                                    if not st.session_state.event_records.empty:
                                        prev_event_records = st.session_state.event_records[
                                            (st.session_state.event_records['Team'] == team_name) &
                                            (st.session_state.event_records['Day'] == prev_day) &
                                            (st.session_state.event_records['Event_Number'] == prev_event_num)
                                        ]
                                        if not prev_event_records.empty:
                                            previous_event_record = prev_event_records.iloc[0]
                                    
                                    # Calculate default participants based on previous event
                                    if previous_event_record is not None:
                                        # Extract values as scalars (not Series)
                                        try:
                                            prev_initial = int(previous_event_record['Initial_Participants'])
                                            prev_drops = int(previous_event_record['Drops'])
                                            default_participants = prev_initial - prev_drops
                                            
                                            # Display info about calculation
                                            st.info(f"Initial participants calculated from previous event: {prev_initial} participants - {prev_drops} drops = {default_participants} participants")
                                        except Exception as e:
                                            st.error(f"Error calculating from previous event: {str(e)}")
                                            # Fall back to default
                                            default_participants = team_size
                                    else:
                                        # No previous event record, calculate from drops data
                                        previous_drops = []
                                        if not st.session_state.drop_data.empty:
                                            prev_drops_query = (
                                                (st.session_state.drop_data['Team'] == team_name) &
                                                (
                                                    # Earlier day
                                                    (st.session_state.drop_data['Day'] < day) |
                                                    # Same day but earlier event
                                                    ((st.session_state.drop_data['Day'] == day) & 
                                                     (st.session_state.drop_data['Event_Number'] < event_number))
                                                )
                                            )
                                            if not st.session_state.drop_data[prev_drops_query].empty:
                                                previous_drops = st.session_state.drop_data[prev_drops_query]['Roster_Number'].unique().tolist()
                                            
                                            # Calculate initial participants excluding previous drops
                                            default_participants = team_size - len(previous_drops)
                                            
                                            if len(previous_drops) > 0:
                                                st.info(f"Initial participants set to {default_participants} based on {len(previous_drops)} drops from previous events")
                                    
                                    # If we have an existing record, use that value only if it was manually edited
                                    if not existing_record.empty:
                                        try:
                                            existing_participants = int(existing_record.iloc[0]['Initial_Participants'])
                                            if existing_participants != default_participants:
                                                # Only use existing value if it was manually edited
                                                if existing_participants != team_size and existing_participants != (team_size - len(previous_drops if 'previous_drops' in locals() else [])):
                                                    st.warning(f"Note: This event was previously recorded with {existing_participants} initial participants.")
                                                    default_participants = existing_participants
                                        except Exception as e:
                                            st.error(f"Error retrieving existing participants: {str(e)}")
                                    
                                    # Ensure default_participants is an integer
                                    try:
                                        default_participants = int(default_participants)
                                    except:
                                        default_participants = team_size
                                        st.error(f"Error converting participants to integer. Using team size: {team_size}")
                                    
                                    # Create a unique key for this field
                                    field_key = f"participants_{team_name}_{day}_{event_number}_{event_name}"
                                    
                                    # Force update the session state for this input field to ensure it shows the correct value
                                    if field_key not in st.session_state or st.session_state[field_key] != default_participants:
                                        st.session_state[field_key] = default_participants
                                    
                                    # Display the initial participants field
                                    initial_participants = st.number_input(
                                        "Initial Participants",
                                        value=st.session_state[field_key],  # Use the value from session state
                                        min_value=0,
                                        key=field_key
                                    )
                                    
                                    # Get current drop count from drop data
                                    drops = 0
                                    if not st.session_state.drop_data.empty:
                                        drops_query = (
                                            (st.session_state.drop_data['Team'] == team_name) &
                                            (st.session_state.drop_data['Day'] == day) &
                                            (st.session_state.drop_data['Event_Number'] == event_number) &
                                            (st.session_state.drop_data['Event_Name'] == event_name)
                                        )
                                        drops = len(st.session_state.drop_data[drops_query])
                                    
                                    st.write(f"**Drops (automatically calculated):** {drops}")
                                    
                                    # Calculate button time duration for preview
                                    if start_time and end_time:
                                        try:
                                            time_actual_min = calculate_duration_minutes(start_time, end_time)
                                            time_actual = minutes_to_mmss(time_actual_min)
                                            st.write(f"**Calculated Duration:** {time_actual}")
                                        except:
                                            st.warning("Please enter valid times (HH:MM)")
                                
                                # Submit button for this event
                                submit_button = st.form_submit_button(f"Save Event Data")
                                
                                if submit_button:
                                    if not start_time or not end_time:
                                        st.error("Please enter both start and end times.")
                                    else:
                                        try:
                                            # Calculate actual time duration
                                            time_actual_min = calculate_duration_minutes(start_time, end_time)
                                            time_actual = minutes_to_mmss(time_actual_min)
                                            
                                            # Convert time limit to minutes for calculations
                                            time_limit_min = time_str_to_minutes(time_limit)
                                            
                                            # Calculate temperature multiplier based on heat category
                                            temp_multiplier = 1.0
                                            if heat_category == 4:
                                                temp_multiplier = 1.15
                                            elif heat_category == 5:
                                                temp_multiplier = 1.3
                                            
                                            # Use the modified equipment data
                                            equipment_key = f"equipment_{day}_{event_name}_{event_number}"
                                            if equipment_key in st.session_state:
                                                equipment_data = st.session_state[equipment_key]
                                                if 'AppRatioWT' in equipment_data.columns:
                                                    total_weight = equipment_data['AppRatioWT'].sum()
                                                else:
                                                    # Fallback calculation
                                                    total_weight = sum(equipment_data['EquipWt'] * equipment_data['EquipNum'])
                                                
                                                # Store individual equipment details for reference
                                                equipment_details = []
                                                for _, equip in equipment_data.iterrows():
                                                    equipment_details.append({
                                                        'Name': equip['EquipmentName'],
                                                        'Weight': equip['EquipWt'],
                                                        'Quantity': equip['EquipNum'],
                                                        'AppRatio': equip['AppRatio'] if 'AppRatio' in equip else 1,
                                                        'TotalWeight': equip['AppRatioWT'] if 'AppRatioWT' in equip else (equip['EquipWt'] * equip['EquipNum'])
                                                    })
                                            else:
                                                # Fallback to simple calculation
                                                total_weight = event_details.get('Equipment_Weight', 0) * event_details.get('Number_of_Equipment', 1)
                                                equipment_details = [{
                                                    'Name': event_details.get('Equipment_Name', 'Generic Equipment'),
                                                    'Weight': event_details.get('Equipment_Weight', 0),
                                                    'Quantity': event_details.get('Number_of_Equipment', 1),
                                                    'TotalWeight': total_weight
                                                }]
                                            
                                            # Calculate difficulty scores
                                            initial_difficulty = calculate_initial_difficulty(
                                                temp_multiplier, total_weight, initial_participants,
                                                distance_km, time_limit_min
                                            )
                                            
                                            # Get current drop count from drop data
                                            drops = 0
                                            team_drop_data = pd.DataFrame()
                                            if not st.session_state.drop_data.empty:
                                                drops_query = (
                                                    (st.session_state.drop_data['Team'] == team_name) &
                                                    (st.session_state.drop_data['Day'] == day) &
                                                    (st.session_state.drop_data['Event_Number'] == event_number) &
                                                    (st.session_state.drop_data['Event_Name'] == event_name)
                                                )
                                                team_drop_data = st.session_state.drop_data[drops_query]
                                                drops = len(team_drop_data)
                                            
                                            actual_difficulty = calculate_actual_difficulty(
                                                temp_multiplier, total_weight, initial_participants,
                                                distance_km, time_actual_min, drops,
                                                team_drop_data, day, event_number, event_name,
                                                start_time
                                            )
                                            
                                            # Create new record
                                            new_record = {
                                                'Team': team_name,
                                                'Day': day,
                                                'Event_Number': event_number,
                                                'Event_Name': event_name,
                                                'Equipment_Name': ', '.join([ed['Name'] for ed in equipment_details]),
                                                'Equipment_Weight': total_weight / sum([ed['Quantity'] for ed in equipment_details]) if sum([ed['Quantity'] for ed in equipment_details]) > 0 else 0,
                                                'Number_of_Equipment': sum([ed['Quantity'] for ed in equipment_details]),
                                                'Distance_km': distance_km,
                                                'Heat_Category': heat_category,
                                                'Time_Limit': time_limit,
                                                'Start_Time': start_time,
                                                'End_Time': end_time,
                                                'Time_Actual': time_actual,
                                                'Time_Actual_Minutes': time_actual_min,
                                                'Initial_Participants': initial_participants,
                                                'Drops': drops,
                                                'Initial_Difficulty': initial_difficulty,
                                                'Actual_Difficulty': actual_difficulty,
                                                'Temperature_Multiplier': temp_multiplier,
                                                'Equipment_Details': str(equipment_details)  # Store as string for DataFrame
                                            }
                                            
                                            # Check if we already have an entry for this team, day, event number, and event name
                                            if not existing_record.empty:
                                                # Update the existing record
                                                st.session_state.event_records.loc[existing_record.index[0]] = new_record
                                                st.success(f"Event data updated for {event_name}")
                                            else:
                                                # Add new record
                                                st.session_state.event_records = pd.concat([
                                                    st.session_state.event_records,
                                                    pd.DataFrame([new_record])
                                                ], ignore_index=True)
                                                st.success(f"Event data recorded for {event_name}")
                                            
                                            # Automatically save the session after recording data
                                            save_session_state()
                                            
                                            # Rerun to refresh the UI
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error saving event data: {str(e)}")
                
                # After all event expanders, add a section to show completion status for this day
                st.write("---")
                st.write("### Day Completion Status")
                
                # Check how many events are recorded for this day and team
                recorded_events = []
                if not st.session_state.event_records.empty and 'Team' in st.session_state.event_records.columns:
                    day_records = st.session_state.event_records[
                        (st.session_state.event_records['Team'] == team_name) &
                        (st.session_state.event_records['Day'] == day)
                    ]
                    recorded_events = day_records['Event_Name'].tolist()
                
                # Display completion status for each event
                for event_idx, event_name in enumerate(day_events):
                    if event_name in recorded_events:
                        st.write(f"✅ Event {event_idx+1}: {event_name} - **Recorded**")
                    else:
                        st.write(f"❌ Event {event_idx+1}: {event_name} - **Not Recorded**")
                
                # Show completion percentage
                completion_pct = len(recorded_events) / len(day_events) * 100 if day_events else 0
                st.progress(completion_pct / 100)
                st.write(f"**Day {day} Completion: {completion_pct:.0f}%**")
        
        # After all day tabs, show a summary of all recorded events for this team
        st.write("---")
        st.subheader(f"Summary of All Recorded Events for {team_name}")
        
        if not st.session_state.event_records.empty and 'Team' in st.session_state.event_records.columns:
            team_records = st.session_state.event_records[
                st.session_state.event_records['Team'] == team_name
            ]
            
            if not team_records.empty:
                # Create a summary table
                summary_data = []
                for _, record in team_records.iterrows():
                    # Count drops for this event
                    drop_count = record['Drops']
                    
                    summary_data.append({
                        'Day': record['Day'],
                        'Event': f"Event {record['Event_Number']}: {record['Event_Name']}",
                        'Time': f"{record['Start_Time']} - {record['End_Time']} ({record['Time_Actual']})",
                        'Distance': f"{record['Distance_km']} km",
                        'Heat': record['Heat_Category'],
                        'Participants': f"{record['Initial_Participants'] - drop_count} / {record['Initial_Participants']}",
                        'Drops': drop_count,
                        'Difficulty': f"{record['Actual_Difficulty']:.2f}"
                    })
                
                # Convert to DataFrame and display
                summary_df = pd.DataFrame(summary_data)
                st.dataframe(summary_df.sort_values(['Day', 'Event']), use_container_width=True)
                
                # Add download button for team records
                csv = team_records.to_csv(index=False)
                b64 = base64.b64encode(csv.encode()).decode()
                href = f'<a href="data:file/csv;base64,{b64}" download="{team_name}_event_records.csv">Download {team_name} Event Records</a>'
                st.markdown(href, unsafe_allow_html=True)
            else:
                st.info(f"No events recorded yet for {team_name}.")
        
        # Show a summary of all drops for this team
        if not st.session_state.drop_data.empty:
            team_drops = st.session_state.drop_data[
                st.session_state.drop_data['Team'] == team_name
            ]
            
            if not team_drops.empty:
                st.subheader(f"All Drops for {team_name}")
                
                # Group drops by day and event
                drop_summary = team_drops.groupby(['Day', 'Event_Number', 'Event_Name']).size().reset_index(name='Count')
                
                # Create a nicer display
                for _, drop_group in drop_summary.iterrows():
                    st.write(f"**Day {drop_group['Day']}, Event {drop_group['Event_Number']}: {drop_group['Event_Name']}** - {drop_group['Count']} drops")
                    
                    # Get the drops for this event
                    event_drops = team_drops[
                        (team_drops['Day'] == drop_group['Day']) &
                        (team_drops['Event_Number'] == drop_group['Event_Number']) &
                        (team_drops['Event_Name'] == drop_group['Event_Name'])
                    ]
                    
                    # Display in a table
                    drop_display = event_drops[['Participant_Name', 'Drop_Time']].sort_values('Drop_Time')
                    drop_display.columns = ['Participant', 'Drop Time']
                    st.table(drop_display)
            else:
                st.info(f"No drops recorded for {team_name}.")
    
    # Display all recorded event data with team filter (outside the team selection)
    st.write("---")
    st.header("All Recorded Event Data")
    
    if not st.session_state.event_records.empty:
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
                
                # Add day and event type filters
                col1, col2 = st.columns(2)
                with col1:
                    days = st.multiselect(
                        "Filter by Days",
                        options=sorted(filtered_records['Day'].unique().tolist()),
                        default=sorted(filtered_records['Day'].unique().tolist())
                    )
                with col2:
                    events = st.multiselect(
                        "Filter by Events",
                        options=sorted(filtered_records['Event_Name'].unique().tolist()),
                        default=sorted(filtered_records['Event_Name'].unique().tolist())
                    )
                
                # Apply additional filters
                if days:
                    filtered_records = filtered_records[filtered_records['Day'].isin(days)]
                if events:
                    filtered_records = filtered_records[filtered_records['Event_Name'].isin(events)]
                
                # Display the filtered data
                if not filtered_records.empty:
                    # Select which columns to display
                    display_cols = ['Team', 'Day', 'Event_Number', 'Event_Name', 'Distance_km', 
                                   'Time_Actual', 'Initial_Participants', 'Drops', 'Actual_Difficulty']
                    st.dataframe(filtered_records[display_cols], use_container_width=True)
                    
                    # Add a download button for the filtered data
                    csv = filtered_records.to_csv(index=False)
                    b64 = base64.b64encode(csv.encode()).decode()
                    href = f'<a href="data:file/csv;base64,{b64}" download="filtered_event_records.csv">Download Filtered Data as CSV</a>'
                    st.markdown(href, unsafe_allow_html=True)
                    
                    # Show drop data for the filtered teams
                    if not st.session_state.drop_data.empty:
                        filtered_drops = st.session_state.drop_data[
                            (st.session_state.drop_data['Team'].isin(selected_teams))
                        ]
                        
                        if days:
                            filtered_drops = filtered_drops[filtered_drops['Day'].isin(days)]
                        if events:
                            filtered_drops = filtered_drops[filtered_drops['Event_Name'].isin(events)]
                        
                        if not filtered_drops.empty:
                            st.subheader("Drops for Selected Teams/Events")
                            
                            # Group by team, day, event
                            drop_summary = filtered_drops.groupby(['Team', 'Day', 'Event_Number', 'Event_Name']).size().reset_index(name='Drop_Count')
                            
                            # Display as a table
                            drop_summary = drop_summary.sort_values(['Team', 'Day', 'Event_Number'])
                            st.dataframe(drop_summary, use_container_width=True)
                            
                            # Option to view detailed drop data
                            if st.checkbox("View detailed drop data"):
                                st.dataframe(filtered_drops.sort_values(['Team', 'Day', 'Event_Number', 'Drop_Time']), use_container_width=True)
                                
                                # Add download button for drop data
                                csv = filtered_drops.to_csv(index=False)
                                b64 = base64.b64encode(csv.encode()).decode()
                                href = f'<a href="data:file/csv;base64,{b64}" download="filtered_drop_data.csv">Download Drop Data</a>'
                                st.markdown(href, unsafe_allow_html=True)
                else:
                    st.info("No records match the selected filters.")
            else:
                st.info("Please select at least one team to view records.")
        else:
            st.dataframe(st.session_state.event_records, use_container_width=True)
    else:
        st.info("No event records available yet. Use the form above to record events.")

# Tab 4: Team Reshuffling
with tabs[3]:
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

# Tab 5: Adjust Difficulty
with tabs[4]:
    st.header("Adjust Difficulty for Days 3-4")
    
    # Check if teams have been reshuffled
    if st.session_state.reshuffled_teams is not None and not st.session_state.event_records.empty:
        st.subheader("Team Balance Analysis")
        
        # Get the data we need
        reshuffled_teams_df = st.session_state.reshuffled_teams
        event_records_df = st.session_state.event_records
        days_1_2_data = event_records_df[event_records_df['Day'].isin([1, 2])]
        
        # Step 1: Analyze the reshuffled teams
        st.write("### Team Composition Analysis")
        
        # Get team sizes
        team_sizes = reshuffled_teams_df.groupby('New_Team').size().reset_index(name='Team_Size')
        team_sizes = team_sizes.sort_values('Team_Size')
        
        # Get team composition (OF vs ADE)
        team_composition = reshuffled_teams_df.groupby(['New_Team', 'Candidate_Type']).size().reset_index(name='Count')
        team_composition_pivot = team_composition.pivot(index='New_Team', columns='Candidate_Type', values='Count').reset_index()
        team_composition_pivot = team_composition_pivot.fillna(0)
        
        # Ensure both OF and ADE columns exist
        if 'OF' not in team_composition_pivot.columns:
            team_composition_pivot['OF'] = 0
        if 'ADE' not in team_composition_pivot.columns:
            team_composition_pivot['ADE'] = 0
            
        # Calculate OF:ADE ratio
        team_composition_pivot['OF_ADE_Ratio'] = team_composition_pivot['OF'] / team_composition_pivot['ADE'].replace(0, 1)
        team_composition_pivot['Total'] = team_composition_pivot['OF'] + team_composition_pivot['ADE']
        
        # Merge with team sizes
        team_analysis = pd.merge(team_sizes, team_composition_pivot, left_on='New_Team', right_on='New_Team')
        
        # Display team composition
        st.dataframe(team_analysis[['New_Team', 'Team_Size', 'OF', 'ADE', 'OF_ADE_Ratio']], use_container_width=True)
        
        # Step 2: Analyze team performance from Days 1-2
        st.write("### Team Performance Analysis (Days 1-2)")
        
        # Calculate average difficulty by original team
        if 'Team' in days_1_2_data.columns:
            team_difficulty = days_1_2_data.groupby('Team')['Actual_Difficulty'].mean().reset_index()
            team_difficulty = team_difficulty.sort_values('Actual_Difficulty', ascending=False)
            
            # Calculate overall average difficulty
            avg_overall_difficulty = days_1_2_data['Actual_Difficulty'].mean()
            
            # Display team performance
            st.dataframe(team_difficulty, use_container_width=True)
            st.write(f"Overall Average Difficulty: {avg_overall_difficulty:.2f}")
            
            # Step 3: Analyze individual performance
            st.write("### Individual Performance Analysis")
            
            # Merge roster data with team performance to get individual performance
            roster_data = st.session_state.roster_data
            
            # Merge with team difficulty to get each person's original team performance
            individual_performance = pd.merge(
                roster_data,
                team_difficulty,
                left_on='Initial_Team',
                right_on='Team'
            )
            
            # Merge with reshuffled teams to see where they are now
            individual_performance = pd.merge(
                individual_performance,
                reshuffled_teams_df[['Candidate_Name', 'New_Team']],
                left_on='Candidate_Name',
                right_on='Candidate_Name',
                how='inner'
            )
            
            # Calculate performance metrics by new team
            new_team_projected_difficulty = individual_performance.groupby('New_Team')['Actual_Difficulty'].mean().reset_index()
            new_team_projected_difficulty = new_team_projected_difficulty.sort_values('Actual_Difficulty')
            
            # Display projected team performance
            st.write("#### Projected Team Performance for Days 3-4 (Without Adjustments)")
            st.dataframe(new_team_projected_difficulty, use_container_width=True)
            
            # Calculate the range of team difficulties
            min_difficulty = new_team_projected_difficulty['Actual_Difficulty'].min()
            max_difficulty = new_team_projected_difficulty['Actual_Difficulty'].max()
            difficulty_range = max_difficulty - min_difficulty
            
            st.write(f"Range of Projected Team Difficulties: {difficulty_range:.2f} ({min_difficulty:.2f} to {max_difficulty:.2f})")
            
            # Plot the projected team performance
            fig = px.bar(
                new_team_projected_difficulty,
                x='New_Team',
                y='Actual_Difficulty',
                title='Projected Team Difficulty for Days 3-4 (Without Adjustments)',
                labels={'Actual_Difficulty': 'Projected Difficulty', 'New_Team': 'Team'}
            )
            
            # Add a horizontal line for the overall average
            fig.add_hline(
                y=avg_overall_difficulty,
                line_dash="dash",
                line_color="red",
                annotation_text=f"Overall Avg: {avg_overall_difficulty:.2f}",
                annotation_position="bottom right"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Step 4: Calculate needed adjustments for each team
            st.write("### Recommended Adjustments for Days 3-4")
            
            # Get Days 3-4 events from the 4-day plan
            has_four_day_plan = ('structured_four_day_plan' in st.session_state and 
                               st.session_state.structured_four_day_plan is not None and 
                               isinstance(st.session_state.structured_four_day_plan, pd.DataFrame) and 
                               not st.session_state.structured_four_day_plan.empty)
            
            if has_four_day_plan:
                days_3_4_plan = st.session_state.structured_four_day_plan[
                    st.session_state.structured_four_day_plan['Day'].isin([3, 4])
                ]
                
                # Choose an adjustment approach
                adjustment_method = st.radio(
                    "Adjustment Method",
                    options=["Balance to Average", "Normalize to Hardest Team", "Custom Target Difficulty"],
                    horizontal=True
                )
                
                if adjustment_method == "Balance to Average":
                    target_difficulty = avg_overall_difficulty
                    st.write(f"Target Difficulty: {target_difficulty:.2f} (Overall Average)")
                elif adjustment_method == "Normalize to Hardest Team":
                    target_difficulty = max_difficulty
                    st.write(f"Target Difficulty: {target_difficulty:.2f} (Hardest Team)")
                else:  # Custom
                    target_difficulty = st.slider(
                        "Set Custom Target Difficulty",
                        min_value=float(min_difficulty * 0.8),
                        max_value=float(max_difficulty * 1.2),
                        value=float(avg_overall_difficulty),
                        step=0.01
                    )
                    st.write(f"Custom Target Difficulty: {target_difficulty:.2f}")
                
                # Calculate adjustment factors for each team
                new_team_projected_difficulty['Adjustment_Factor'] = target_difficulty / new_team_projected_difficulty['Actual_Difficulty']
                new_team_projected_difficulty['Adjustment_Percentage'] = (new_team_projected_difficulty['Adjustment_Factor'] - 1) * 100
                
                # Display adjustment factors
                st.write("#### Required Adjustment Factors by Team")
                adjustment_display = new_team_projected_difficulty[['New_Team', 'Actual_Difficulty', 'Adjustment_Factor', 'Adjustment_Percentage']]
                adjustment_display = adjustment_display.sort_values('Adjustment_Percentage')
                
                # Format for display
                adjustment_display['Actual_Difficulty'] = adjustment_display['Actual_Difficulty'].map(lambda x: f"{x:.2f}")
                adjustment_display['Adjustment_Factor'] = adjustment_display['Adjustment_Factor'].map(lambda x: f"{x:.2f}x")
                adjustment_display['Adjustment_Percentage'] = adjustment_display['Adjustment_Percentage'].map(lambda x: f"{x:+.1f}%")
                
                st.dataframe(adjustment_display, use_container_width=True)
                
                # Let user select which events to adjust
                st.write("### Apply Adjustments to Specific Events")
                
                days_3_4_events = []
                if not days_3_4_plan.empty:
                    # Group events by day
                    for day in [3, 4]:
                        day_events = days_3_4_plan[days_3_4_plan['Day'] == day]
                        if not day_events.empty:
                            day_events_list = day_events['Event_Name'].unique().tolist()
                            days_3_4_events.extend([f"Day {day}: {event}" for event in day_events_list])
                
                selected_events = st.multiselect(
                    "Select Events to Adjust",
                    options=days_3_4_events,
                    default=days_3_4_events
                )
                
                if selected_events:
                    # Choose adjustment type
                    adjustment_type = st.radio(
                        "What to Adjust",
                        options=["Weight Only", "Distance Only", "Both Weight and Distance"],
                        horizontal=True
                    )
                    
                    # Calculate specific adjustments for each team and event
                    st.write("### Specific Adjustments by Team and Event")
                    
                    # Create tabs for each selected event
                    event_tabs = st.tabs(selected_events)
                    
                    for i, event_str in enumerate(selected_events):
                        with event_tabs[i]:
                            # Parse day and event name
                            day = int(event_str.split(":")[0].replace("Day ", ""))
                            event_name = event_str.split(": ")[1]
                            
                            # Get event details
                            event_details = days_3_4_plan[
                                (days_3_4_plan['Day'] == day) & 
                                (days_3_4_plan['Event_Name'] == event_name)
                            ]
                            
                            if not event_details.empty:
                                event_detail = event_details.iloc[0]
                                st.write(f"#### {event_str}")
                                
                                # Calculate and display adjustments for each team
                                adjustment_results = []
                                
                                for _, team_row in new_team_projected_difficulty.iterrows():
                                    team_name = team_row['New_Team']
                                    team_adj_factor = team_row['Adjustment_Factor']
                                    team_adj_percent = team_row['Adjustment_Percentage']
                                    
                                    # Base values
                                    base_weight = event_detail['Equipment_Weight'] * event_detail['Number_of_Equipment']
                                    base_distance = event_detail['Distance']
                                    
                                    # Calculate adjusted values based on adjustment type
                                    if adjustment_type == "Weight Only":
                                        adj_weight = base_weight * team_adj_factor
                                        adj_distance = base_distance
                                        weight_change_pct = (team_adj_factor - 1) * 100
                                        distance_change_pct = 0
                                    elif adjustment_type == "Distance Only":
                                        adj_weight = base_weight
                                        adj_distance = base_distance * team_adj_factor
                                        weight_change_pct = 0
                                        distance_change_pct = (team_adj_factor - 1) * 100
                                    else:  # Both
                                        # Split adjustment between weight and distance
                                        # Use square root to distribute the effect
                                        split_factor = np.sqrt(team_adj_factor)
                                        adj_weight = base_weight * split_factor
                                        adj_distance = base_distance * split_factor
                                        weight_change_pct = (split_factor - 1) * 100
                                        distance_change_pct = (split_factor - 1) * 100
                                    
                                    # Add to results
                                    adjustment_results.append({
                                        'Team': team_name,
                                        'Adjustment_Factor': team_adj_factor,
                                        'Adjustment_Percentage': team_adj_percent,
                                        'Original_Weight': base_weight,
                                        'Adjusted_Weight': adj_weight,
                                        'Weight_Change_Pct': weight_change_pct,
                                        'Original_Distance': base_distance,
                                        'Adjusted_Distance': adj_distance,
                                        'Distance_Change_Pct': distance_change_pct
                                    })
                                
                                # Convert to DataFrame and display
                                adjustment_results_df = pd.DataFrame(adjustment_results)
                                
                                # Format for display
                                display_df = adjustment_results_df.copy()
                                display_df['Adjustment_Factor'] = display_df['Adjustment_Factor'].map(lambda x: f"{x:.2f}x")
                                display_df['Adjustment_Percentage'] = display_df['Adjustment_Percentage'].map(lambda x: f"{x:+.1f}%")
                                display_df['Original_Weight'] = display_df['Original_Weight'].map(lambda x: f"{x:.1f} lbs")
                                display_df['Adjusted_Weight'] = display_df['Adjusted_Weight'].map(lambda x: f"{x:.1f} lbs")
                                display_df['Weight_Change_Pct'] = display_df['Weight_Change_Pct'].map(lambda x: f"{x:+.1f}%")
                                display_df['Original_Distance'] = display_df['Original_Distance'].map(lambda x: f"{x:.2f} km")
                                display_df['Adjusted_Distance'] = display_df['Adjusted_Distance'].map(lambda x: f"{x:.2f} km")
                                display_df['Distance_Change_Pct'] = display_df['Distance_Change_Pct'].map(lambda x: f"{x:+.1f}%")
                                
                                st.dataframe(display_df, use_container_width=True)
                                
                                # Visualize the adjustments
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    if adjustment_type in ["Weight Only", "Both Weight and Distance"]:
                                        fig_weight = px.bar(
                                            adjustment_results_df,
                                            x='Team',
                                            y='Adjusted_Weight',
                                            title=f'Adjusted Weight by Team for {event_str}',
                                            labels={'Adjusted_Weight': 'Weight (lbs)', 'Team': 'Team'},
                                            color='Adjustment_Percentage',
                                            color_continuous_scale='RdYlGn',
                                            range_color=[-20, 20]
                                        )
                                        
                                        # Add a line for the original weight
                                        fig_weight.add_hline(
                                            y=base_weight,
                                            line_dash="dash",
                                            line_color="red",
                                            annotation_text=f"Original: {base_weight:.1f} lbs",
                                            annotation_position="bottom right"
                                        )
                                        
                                        st.plotly_chart(fig_weight, use_container_width=True)
                                
                                with col2:
                                    if adjustment_type in ["Distance Only", "Both Weight and Distance"]:
                                        fig_distance = px.bar(
                                            adjustment_results_df,
                                            x='Team',
                                            y='Adjusted_Distance',
                                            title=f'Adjusted Distance by Team for {event_str}',
                                            labels={'Adjusted_Distance': 'Distance (km)', 'Team': 'Team'},
                                            color='Adjustment_Percentage',
                                            color_continuous_scale='RdYlGn',
                                            range_color=[-20, 20]
                                        )
                                        
                                        # Add a line for the original distance
                                        fig_distance.add_hline(
                                            y=base_distance,
                                            line_dash="dash",
                                            line_color="red",
                                            annotation_text=f"Original: {base_distance:.2f} km",
                                            annotation_position="bottom right"
                                        )
                                        
                                        st.plotly_chart(fig_distance, use_container_width=True)
                            else:
                                st.warning(f"Could not find details for {event_str}")
                    
                    # Save adjustments
                    if st.button("Save All Adjustments"):
                        if 'team_adjustments' not in st.session_state:
                            st.session_state.team_adjustments = []
                        
                        # Clear existing adjustments for these events
                        event_keys = [e.replace("Day ", "").replace(": ", "_") for e in selected_events]
                        st.session_state.team_adjustments = [
                            adj for adj in st.session_state.team_adjustments 
                            if adj['event_key'] not in event_keys
                        ]
                        
                        # Create new adjustments
                        for event_str in selected_events:
                            # Parse day and event name
                            day = int(event_str.split(":")[0].replace("Day ", ""))
                            event_name = event_str.split(": ")[1]
                            event_key = f"{day}_{event_name}"
                            
                            # Get event details
                            event_details = days_3_4_plan[
                                (days_3_4_plan['Day'] == day) & 
                                (days_3_4_plan['Event_Name'] == event_name)
                            ]
                            
                            if not event_details.empty:
                                event_detail = event_details.iloc[0]
                                
                                # Base values
                                base_weight = event_detail['Equipment_Weight'] * event_detail['Number_of_Equipment']
                                base_distance = event_detail['Distance']
                                
                                # Calculate adjustments for each team
                                for _, team_row in new_team_projected_difficulty.iterrows():
                                    team_name = team_row['New_Team']
                                    team_adj_factor = team_row['Adjustment_Factor']
                                    
                                    # Calculate adjusted values based on adjustment type
                                    if adjustment_type == "Weight Only":
                                        adj_weight = base_weight * team_adj_factor
                                        adj_distance = base_distance
                                    elif adjustment_type == "Distance Only":
                                        adj_weight = base_weight
                                        adj_distance = base_distance * team_adj_factor
                                    else:  # Both
                                        # Split adjustment between weight and distance
                                        split_factor = np.sqrt(team_adj_factor)
                                        adj_weight = base_weight * split_factor
                                        adj_distance = base_distance * split_factor
                                    
                                    # Add to adjustments
                                    st.session_state.team_adjustments.append({
                                        'event_key': event_key,
                                        'day': day,
                                        'event_name': event_name,
                                        'team': team_name,
                                        'original_weight': base_weight,
                                        'adjusted_weight': adj_weight,
                                        'original_distance': base_distance,
                                        'adjusted_distance': adj_distance,
                                        'adjustment_factor': team_adj_factor,
                                        'adjustment_type': adjustment_type
                                    })
                        
                        # Save session state
                        save_session_state()
                        st.success("All adjustments saved! These will be applied to the selected events for Days 3-4.")
                        
                        # Show download button for adjustments
                        if st.session_state.team_adjustments:
                            adj_df = pd.DataFrame(st.session_state.team_adjustments)
                            csv = adj_df.to_csv(index=False)
                            b64 = base64.b64encode(csv.encode()).decode()
                            href = f'<a href="data:file/csv;base64,{b64}" download="team_adjustments.csv">Download Team Adjustments CSV</a>'
                            st.markdown(href, unsafe_allow_html=True)
                else:
                    st.warning("Please select at least one event to adjust.")
            else:
                st.error("No events found for Days 3-4. Please set up the 4-day plan first.")
        else:
            st.warning("No team performance data available for Days 1-2. Please record events for Days 1-2 first.")
        
        # Display saved adjustments if they exist
        if 'team_adjustments' in st.session_state and st.session_state.team_adjustments:
            st.write("### Saved Adjustments")
            
            # Convert to DataFrame for display
            saved_adj_df = pd.DataFrame(st.session_state.team_adjustments)
            
            # Group by event
            event_keys = saved_adj_df['event_key'].unique()
            
            # Create tabs for each event
            event_tabs = st.tabs([key.replace("_", ": Day ") for key in event_keys])
            
            for i, event_key in enumerate(event_keys):
                with event_tabs[i]:
                    # Filter for this event
                    event_adj = saved_adj_df[saved_adj_df['event_key'] == event_key]
                    
                    # Get event details
                    day = event_adj['day'].iloc[0]
                    event_name = event_adj['event_name'].iloc[0]
                    
                    st.write(f"#### Day {day}: {event_name}")
                    
                    # Format for display
                    display_cols = ['team', 'original_weight', 'adjusted_weight', 'original_distance', 'adjusted_distance', 'adjustment_factor']
                    display_df = event_adj[display_cols].copy()
                    
                    # Rename columns
                    display_df.columns = ['Team', 'Original Weight (lbs)', 'Adjusted Weight (lbs)', 
                                          'Original Distance (km)', 'Adjusted Distance (km)', 'Adjustment Factor']
                    
                    # Format numbers
                    display_df['Original Weight (lbs)'] = display_df['Original Weight (lbs)'].map(lambda x: f"{x:.1f}")
                    display_df['Adjusted Weight (lbs)'] = display_df['Adjusted Weight (lbs)'].map(lambda x: f"{x:.1f}")
                    display_df['Original Distance (km)'] = display_df['Original Distance (km)'].map(lambda x: f"{x:.2f}")
                    display_df['Adjusted Distance (km)'] = display_df['Adjusted Distance (km)'].map(lambda x: f"{x:.2f}")
                    display_df['Adjustment Factor'] = display_df['Adjustment Factor'].map(lambda x: f"{x:.2f}x")
                    
                    st.dataframe(display_df, use_container_width=True)
            
            # Option to clear all adjustments
            if st.button("Clear All Saved Adjustments"):
                st.session_state.team_adjustments = []
                save_session_state()
                st.success("All adjustments cleared.")
                st.rerun()
    else:
        st.warning("Please reshuffle teams and record events for Days 1-2 before adjusting difficulty for Days 3-4.")

# Tab 6: Event Recording (Days 3-4)
with tabs[5]:
    st.header("Event Data Recording (Days 3-4)")
    
    # First, select the team for which we're recording data
    if st.session_state.reshuffled_teams is not None:
        # Get unique teams from reshuffled teams data
        team_options = st.session_state.reshuffled_teams['New_Team'].unique().tolist()
        selected_team = st.selectbox("Select Team", options=team_options, key="days_3_4_team_select")
        team_name = selected_team
        day_range = [3, 4]
        day_label = "Days 3-4"
        
        st.subheader(f"Recording Events for {team_name} - {day_label}")
        
        # Get team size for initial participants default
        team_roster = st.session_state.reshuffled_teams[
            st.session_state.reshuffled_teams['New_Team'] == team_name
        ]
        team_size = len(team_roster)
        
        # Check if we have a 4-day plan
        has_four_day_plan = ('structured_four_day_plan' in st.session_state and
                           st.session_state.structured_four_day_plan is not None and
                           isinstance(st.session_state.structured_four_day_plan, pd.DataFrame) and
                           not st.session_state.structured_four_day_plan.empty)
        
        # Prepare heat category options
        heat_categories = {
            1: "Heat Category 1 (no multiplier)",
            2: "Heat Category 2 (no multiplier)",
            3: "Heat Category 3 (no multiplier)",
            4: "Heat Category 4 (1.15x multiplier)",
            5: "Heat Category 5 (1.3x multiplier)"
        }
        
        # Create tabs for each day in the range
        day_tabs = st.tabs([f"Day {day}" for day in day_range])
        for i, day in enumerate(day_range):
            with day_tabs[i]:
                # Get events for this day from the 4-day plan
                day_events = []
                event_details_by_name = {}
                if has_four_day_plan:
                    day_plan = st.session_state.structured_four_day_plan[
                        st.session_state.structured_four_day_plan['Day'] == day
                    ]
                    if not day_plan.empty:
                        # Sort by event number
                        day_plan = day_plan.sort_values('Event_Number')
                        day_events = day_plan['Event_Name'].tolist()
                        # Create a mapping of event names to details
                        for _, event in day_plan.iterrows():
                            event_details_by_name[event['Event_Name']] = event
                
                if not day_events:
                    st.warning(f"No events defined for Day {day} in the 4-day plan. Please set up the 4-day plan first.")
                    continue
                
                st.write(f"### Events for Day {day}")
                
                # Create an expander for each event
                for event_idx, event_name in enumerate(day_events):
                    event_number = event_idx + 1
                    event_details = event_details_by_name.get(event_name, {})
                    
                    # Check for any difficulty adjustments for this team and event
                    adjusted_weight = None
                    adjusted_distance = None
                    if 'team_adjustments' in st.session_state and st.session_state.team_adjustments:
                        event_key = f"{day}_{event_name}"
                        for adj in st.session_state.team_adjustments:
                            if adj['event_key'] == event_key and adj['team'] == team_name:
                                adjusted_weight = adj['adjusted_weight']
                                adjusted_distance = adj['adjusted_distance']
                                break
                    
                    # Calculate adjusted initial participants based on previous events
                    adjusted_initial_participants = team_size  # Default to full team size
                    previous_drops = []
                    
                    # Get all drops for this team across all events up to this one
                    if not st.session_state.drop_data.empty:
                        all_team_drops = st.session_state.drop_data[
                            st.session_state.drop_data['Team'] == team_name
                        ]
                        # Get drops from previous events (earlier days or earlier events on same day)
                        prev_drops_query = (
                            # Earlier day
                            (all_team_drops['Day'] < day) |
                            # Same day but earlier event
                            ((all_team_drops['Day'] == day) & (all_team_drops['Event_Number'] < event_number))
                        )
                        previous_drops_df = all_team_drops[prev_drops_query]
                        previous_drops = previous_drops_df['Roster_Number'].unique().tolist()
                        # Calculate adjusted participants by removing those who dropped in previous events
                        if previous_drops:
                            # Get the participant list excluding previously dropped
                            current_participants = team_roster.copy()
                            current_participants = current_participants[
                                ~current_participants['Roster_Number'].isin(previous_drops)
                            ]
                            adjusted_initial_participants = len(current_participants)
                    
                    # Store this value in session state for use in the form
                    if 'adjusted_participants' not in st.session_state:
                        st.session_state.adjusted_participants = {}
                    participants_key = f"{team_name}_{day}_{event_number}"
                    st.session_state.adjusted_participants[participants_key] = adjusted_initial_participants
                    
                    # Check if we already have a record for this event
                    existing_record = pd.DataFrame()  # Default to empty DataFrame
                    if not st.session_state.event_records.empty and 'Team' in st.session_state.event_records.columns:
                        existing_record = st.session_state.event_records[
                            (st.session_state.event_records['Team'] == team_name) &
                            (st.session_state.event_records['Day'] == day) &
                            (st.session_state.event_records['Event_Number'] == event_number) &
                            (st.session_state.event_records['Event_Name'] == event_name)
                        ]
                    
                    # Set the expander title based on whether we have existing data
                    if not existing_record.empty:
                        expander_title = f"Event {event_number}: {event_name} ✓"
                        expander_open = False  # Default closed if already recorded
                    else:
                        expander_title = f"Event {event_number}: {event_name}"
                        expander_open = True  # Default open if not recorded
                        
                        # If there are difficulty adjustments, indicate in the title
                        if adjusted_weight is not None or adjusted_distance is not None:
                            expander_title += " (Adjusted)"
                    
                    with st.expander(expander_title, expanded=expander_open):
                        # If we have existing data, show a summary
                        if not existing_record.empty:
                            record = existing_record.iloc[0]
                            st.success("Event already recorded. You can update the data if needed.")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.write("**Time:**", f"{record['Start_Time']} - {record['End_Time']}")
                                st.write("**Duration:**", record['Time_Actual'])
                            with col2:
                                st.write("**Distance:**", f"{record['Distance_km']} km")
                                st.write("**Heat Category:**", record['Heat_Category'])
                            with col3:
                                st.write("**Participants:**", record['Initial_Participants'])
                                st.write("**Drops:**", record['Drops'])
                                st.write("**Difficulty:**", f"{record['Actual_Difficulty']:.2f}")
                        
                        # Create tabs for event data and drops management
                        event_data_tab, drops_tab = st.tabs(["Event Data", "Manage Drops"])
                        
                        # Event Data Tab
                        with event_data_tab:
                            # If there are difficulty adjustments, show a notice
                            if adjusted_weight is not None or adjusted_distance is not None:
                                st.info("This event has been adjusted for this team based on the difficulty balance calculations.")
                                
                                if adjusted_weight is not None:
                                    st.write(f"**Adjusted Weight:** {adjusted_weight:.1f} lbs (Original: {event_details.get('Equipment_Weight', 0) * event_details.get('Number_of_Equipment', 1):.1f} lbs)")
                                
                                if adjusted_distance is not None:
                                    st.write(f"**Adjusted Distance:** {adjusted_distance:.2f} km (Original: {event_details.get('Distance', 0):.2f} km)")
                            
                            # Create a form for each event
                            with st.form(f"event_form_days3-4_{team_name}_{day}_{event_number}"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    # Display event details
                                    st.write(f"**Event Name:** {event_name}")
                                    time_limit = event_details.get('Time_Limit', '00:00')
                                    st.write(f"**Time Limit:** {time_limit}")
                                    
                                    # Get equipment details
                                    equipment_key = f"equipment_days3-4_{day}_{event_name}_{event_number}"
                                    if equipment_key not in st.session_state:
                                        # Initialize equipment from event details or 4-day plan
                                        event_equipment = load_event_equip_data()
                                        if not event_equipment.empty and 'EventName' in event_equipment.columns:
                                            if event_name in event_equipment['EventName'].values:
                                                event_id = event_equipment[event_equipment['EventName'] == event_name]['EventID'].unique()[0]
                                                equipment_items = event_equipment[event_equipment['EventID'] == event_id]
                                                st.session_state[equipment_key] = equipment_items.copy()
                                            else:
                                                # Fallback to basic equipment
                                                basic_equipment = pd.DataFrame([{
                                                    'EquipmentName': event_details.get('Equipment_Name', 'Generic Equipment'),
                                                    'EquipWt': event_details.get('Equipment_Weight', 0),
                                                    'EquipNum': event_details.get('Number_of_Equipment', 1),
                                                    'AppRatio': 1,
                                                    'AppRatioWT': event_details.get('Equipment_Weight', 0) * event_details.get('Number_of_Equipment', 1)
                                                }])
                                                st.session_state[equipment_key] = basic_equipment
                                        else:
                                            # Fallback to basic equipment
                                            basic_equipment = pd.DataFrame([{
                                                'EquipmentName': event_details.get('Equipment_Name', 'Generic Equipment'),
                                                'EquipWt': event_details.get('Equipment_Weight', 0),
                                                'EquipNum': event_details.get('Number_of_Equipment', 1),
                                                'AppRatio': 1,
                                                'AppRatioWT': event_details.get('Equipment_Weight', 0) * event_details.get('Number_of_Equipment', 1)
                                            }])
                                            st.session_state[equipment_key] = basic_equipment
                                    
                                    # Display equipment list with adjustments applied
                                    st.write("**Equipment:**")
                                    equipment_list = st.session_state[equipment_key].copy()
                                    
                                    # Apply weight adjustment if available
                                    if adjusted_weight is not None:
                                        # Calculate adjustment factor
                                        original_total = equipment_list['AppRatioWT'].sum()
                                        if original_total > 0:
                                            adj_factor = adjusted_weight / original_total
                                            # Apply to each item
                                            for i, (_, equip) in enumerate(equipment_list.iterrows()):
                                                equipment_list.at[i, 'AppRatioWT'] = equip['AppRatioWT'] * adj_factor
                                    
                                    # Display equipment
                                    total_weight = 0
                                    for i, equip in enumerate(equipment_list.iterrows()):
                                        equip_idx = equip[0]
                                        equip = equip[1]
                                        col_name, col_weight, col_qty = st.columns([3, 1, 1])
                                        with col_name:
                                            st.text(equip['EquipmentName'])
                                        with col_weight:
                                            st.text(f"{equip['EquipWt']} lbs")
                                        with col_qty:
                                            # Set default qty from existing record if available
                                            default_qty = int(equip['EquipNum'])
                                            if not existing_record.empty:
                                                # Try to parse equipment details from existing record
                                                try:
                                                    equip_details = existing_record.iloc[0].get('Equipment_Details', '')
                                                    if equip_details:
                                                        import json
                                                        equip_details = json.loads(equip_details.replace("'", "\""))
                                                        for item in equip_details:
                                                            if item['Name'] == equip['EquipmentName']:
                                                                default_qty = int(item['Quantity'])
                                                                break
                                                except:
                                                    pass
                                            new_qty = st.number_input(
                                                f"Qty",
                                                value=default_qty,
                                                min_value=0,
                                                key=f"qty_days3-4_{team_name}_{day}_{event_name}_{event_number}_{i}"
                                            )
                                            if new_qty != equip['EquipNum']:
                                                equipment_list.at[equip_idx, 'EquipNum'] = new_qty
                                                app_ratio = equip['AppRatio'] if 'AppRatio' in equip and equip['AppRatio'] > 0 else 1
                                                equipment_list.at[equip_idx, 'AppRatioWT'] = equip['EquipWt'] * new_qty * (app_ratio / 100 if app_ratio > 10 else app_ratio)
                                        # Calculate total for this item
                                        item_total = equipment_list.at[equip_idx, 'AppRatioWT']
                                        total_weight += item_total
                                    
                                    st.markdown(f"**Total Adjusted Weight: {total_weight:.2f} lbs**")
                                    
                                    # Distance input with default from existing record or adjusted value
                                    default_distance = adjusted_distance if adjusted_distance is not None else event_details.get('Distance', 0)
                                    if not existing_record.empty:
                                        default_distance = existing_record.iloc[0]['Distance_km']
                                    
                                    distance_km = st.number_input(
                                        "Distance (km)",
                                        value=float(default_distance),
                                        min_value=0.0,
                                        key=f"distance_days3-4_{team_name}_{day}_{event_name}"
                                    )
                                
                                with col2:
                                    # Heat category with default from existing record
                                    default_heat = 1
                                    if not existing_record.empty:
                                        default_heat = existing_record.iloc[0]['Heat_Category']
                                    heat_category = st.selectbox(
                                        "Heat Category",
                                        options=list(heat_categories.keys()),
                                        format_func=lambda x: heat_categories[x],
                                        index=default_heat-1,
                                        key=f"heat_days3-4_{team_name}_{day}_{event_name}"
                                    )
                                    
                                    # Start and end times with defaults from existing record
                                    default_start = ""
                                    default_end = ""
                                    if not existing_record.empty:
                                        default_start = existing_record.iloc[0]['Start_Time']
                                        default_end = existing_record.iloc[0]['End_Time']
                                    start_time = st.text_input(
                                        "Start Time (HH:MM)",
                                        value=default_start,
                                        placeholder="e.g., 08:30",
                                        key=f"start_days3-4_{team_name}_{day}_{event_name}"
                                    )
                                    end_time = st.text_input(
                                        "End Time (HH:MM)",
                                        value=default_end,
                                        placeholder="e.g., 11:45",
                                        key=f"end_days3-4_{team_name}_{day}_{event_name}"
                                    )
                                    
                                    # Initial participants with default based on the freshly calculated value
                                    # Calculate initial participants based on the ending count from the previous event
                                    default_participants = team_size  # Default to full team size for the first event
                                    
                                    # Determine the previous event (regardless of whether we have a record for it)
                                    prev_day = day
                                    prev_event_num = event_number - 1
                                    # If this is the first event of the day, look at the last event of the previous day
                                    if prev_event_num < 1:
                                        prev_day = day - 1
                                        # Assume 3 events per day as default
                                        prev_event_num = 3
                                        # Try to find the actual last event number for the previous day
                                        if not st.session_state.event_records.empty:
                                            prev_day_events = st.session_state.event_records[
                                                (st.session_state.event_records['Team'] == team_name) &
                                                (st.session_state.event_records['Day'] == prev_day)
                                            ]
                                            if not prev_day_events.empty:
                                                prev_event_num = int(prev_day_events['Event_Number'].max())
                                    
                                    # Now try to find a record for this previous event
                                    previous_event_record = None
                                    if not st.session_state.event_records.empty:
                                        prev_event_records = st.session_state.event_records[
                                            (st.session_state.event_records['Team'] == team_name) &
                                            (st.session_state.event_records['Day'] == prev_day) &
                                            (st.session_state.event_records['Event_Number'] == prev_event_num)
                                        ]
                                        if not prev_event_records.empty:
                                            previous_event_record = prev_event_records.iloc[0]
                                    
                                    # Calculate default participants based on previous event
                                    if previous_event_record is not None:
                                        # Extract values as scalars (not Series)
                                        try:
                                            prev_initial = int(previous_event_record['Initial_Participants'])
                                            prev_drops = int(previous_event_record['Drops'])
                                            default_participants = prev_initial - prev_drops
                                            # Display info about calculation
                                            st.info(f"Initial participants calculated from previous event: {prev_initial} participants - {prev_drops} drops = {default_participants} participants")
                                        except Exception as e:
                                            st.error(f"Error calculating from previous event: {str(e)}")
                                            # Fall back to default
                                            default_participants = team_size
                                    else:
                                        # No previous event record, calculate from drops data
                                        previous_drops = []
                                        if not st.session_state.drop_data.empty:
                                            prev_drops_query = (
                                                (st.session_state.drop_data['Team'] == team_name) &
                                                (
                                                    # Earlier day
                                                    (st.session_state.drop_data['Day'] < day) |
                                                    # Same day but earlier event
                                                    ((st.session_state.drop_data['Day'] == day) &
                                                     (st.session_state.drop_data['Event_Number'] < event_number))
                                                )
                                            )
                                            if not st.session_state.drop_data[prev_drops_query].empty:
                                                previous_drops = st.session_state.drop_data[prev_drops_query]['Roster_Number'].unique().tolist()
                                            # Calculate initial participants excluding previous drops
                                            default_participants = team_size - len(previous_drops)
                                            if len(previous_drops) > 0:
                                                st.info(f"Initial participants set to {default_participants} based on {len(previous_drops)} drops from previous events")
                                    
                                    # If we have an existing record, use that value only if it was manually edited
                                    if not existing_record.empty:
                                        try:
                                            existing_participants = int(existing_record.iloc[0]['Initial_Participants'])
                                            if existing_participants != default_participants:
                                                # Only use existing value if it was manually edited
                                                if existing_participants != team_size and existing_participants != (team_size - len(previous_drops if 'previous_drops' in locals() else [])):
                                                    st.warning(f"Note: This event was previously recorded with {existing_participants} initial participants.")
                                                    default_participants = existing_participants
                                        except Exception as e:
                                            st.error(f"Error retrieving existing participants: {str(e)}")
                                    
                                    # Ensure default_participants is an integer
                                    try:
                                        default_participants = int(default_participants)
                                    except:
                                        default_participants = team_size
                                        st.error(f"Error converting participants to integer. Using team size: {team_size}")
                                    
                                    # Create a unique key for this field
                                    field_key = f"participants_days3-4_{team_name}_{day}_{event_number}_{event_name}"
                                    
                                    # Force update the session state for this input field to ensure it shows the correct value
                                    if field_key not in st.session_state or st.session_state[field_key] != default_participants:
                                        st.session_state[field_key] = default_participants
                                    
                                    # Display the initial participants field
                                    initial_participants = st.number_input(
                                        "Initial Participants",
                                        value=st.session_state[field_key],  # Use the value from session state
                                        min_value=0,
                                        key=field_key
                                    )
                                    
                                    # Get current drop count from drop data
                                    drops = 0
                                    if not st.session_state.drop_data.empty:
                                        drops_query = (
                                            (st.session_state.drop_data['Team'] == team_name) &
                                            (st.session_state.drop_data['Day'] == day) &
                                            (st.session_state.drop_data['Event_Number'] == event_number) &
                                            (st.session_state.drop_data['Event_Name'] == event_name)
                                        )
                                        drops = len(st.session_state.drop_data[drops_query])
                                    st.write(f"**Drops (automatically calculated):** {drops}")
                                    
                                    # Calculate button time duration for preview
                                    if start_time and end_time:
                                        try:
                                            time_actual_min = calculate_duration_minutes(start_time, end_time)
                                            time_actual = minutes_to_mmss(time_actual_min)
                                            st.write(f"**Calculated Duration:** {time_actual}")
                                        except:
                                            st.warning("Please enter valid times (HH:MM)")
                                
                                # Submit button for this event
                                submit_button = st.form_submit_button(f"Save Event Data")
                                if submit_button:
                                    if not start_time or not end_time:
                                        st.error("Please enter both start and end times.")
                                    else:
                                        try:
                                            # Calculate actual time duration
                                            time_actual_min = calculate_duration_minutes(start_time, end_time)
                                            time_actual = minutes_to_mmss(time_actual_min)
                                            
                                            # Convert time limit to minutes for calculations
                                            time_limit_min = time_str_to_minutes(time_limit)
                                            
                                            # Calculate temperature multiplier based on heat category
                                            temp_multiplier = 1.0
                                            if heat_category == 4:
                                                temp_multiplier = 1.15
                                            elif heat_category == 5:
                                                temp_multiplier = 1.3
                                            
                                            # Use the modified equipment data
                                            equipment_key = f"equipment_days3-4_{day}_{event_name}_{event_number}"
                                            if equipment_key in st.session_state:
                                                equipment_data = st.session_state[equipment_key]
                                                if 'AppRatioWT' in equipment_data.columns:
                                                    total_weight = equipment_data['AppRatioWT'].sum()
                                                else:
                                                    # Fallback calculation
                                                    total_weight = sum(equipment_data['EquipWt'] * equipment_data['EquipNum'])
                                                
                                                # Apply weight adjustment if available
                                                if adjusted_weight is not None:
                                                    total_weight = adjusted_weight
                                                
                                                # Store individual equipment details for reference
                                                equipment_details = []
                                                for _, equip in equipment_data.iterrows():
                                                    equipment_details.append({
                                                        'Name': equip['EquipmentName'],
                                                        'Weight': equip['EquipWt'],
                                                        'Quantity': equip['EquipNum'],
                                                        'AppRatio': equip['AppRatio'] if 'AppRatio' in equip else 1,
                                                        'TotalWeight': equip['AppRatioWT'] if 'AppRatioWT' in equip else (equip['EquipWt'] * equip['EquipNum'])
                                                    })
                                            else:
                                                # Fallback to simple calculation
                                                total_weight = event_details.get('Equipment_Weight', 0) * event_details.get('Number_of_Equipment', 1)
                                                if adjusted_weight is not None:
                                                    total_weight = adjusted_weight
                                                equipment_details = [{
                                                    'Name': event_details.get('Equipment_Name', 'Generic Equipment'),
                                                    'Weight': event_details.get('Equipment_Weight', 0),
                                                    'Quantity': event_details.get('Number_of_Equipment', 1),
                                                    'TotalWeight': total_weight
                                                }]
                                            
                                            # Calculate difficulty scores
                                            initial_difficulty = calculate_initial_difficulty(
                                                temp_multiplier, total_weight, initial_participants,
                                                distance_km, time_limit_min
                                            )
                                            
                                            # Get current drop count from drop data
                                            drops = 0
                                            team_drop_data = pd.DataFrame()
                                            if not st.session_state.drop_data.empty:
                                                drops_query = (
                                                    (st.session_state.drop_data['Team'] == team_name) &
                                                    (st.session_state.drop_data['Day'] == day) &
                                                    (st.session_state.drop_data['Event_Number'] == event_number) &
                                                    (st.session_state.drop_data['Event_Name'] == event_name)
                                                )
                                                team_drop_data = st.session_state.drop_data[drops_query]
                                                drops = len(team_drop_data)
                                            
                                            actual_difficulty = calculate_actual_difficulty(
                                                temp_multiplier, total_weight, initial_participants,
                                                distance_km, time_actual_min, drops,
                                                team_drop_data, day, event_number, event_name,
                                                start_time
                                            )
                                            
                                            # Create new record
                                            new_record = {
                                                'Team': team_name,
                                                'Day': day,
                                                'Event_Number': event_number,
                                                'Event_Name': event_name,
                                                'Equipment_Name': ', '.join([ed['Name'] for ed in equipment_details]),
                                                'Equipment_Weight': total_weight / sum([ed['Quantity'] for ed in equipment_details]) if sum([ed['Quantity'] for ed in equipment_details]) > 0 else 0,
                                                'Number_of_Equipment': sum([ed['Quantity'] for ed in equipment_details]),
                                                'Distance_km': distance_km,
                                                'Heat_Category': heat_category,
                                                'Time_Limit': time_limit,
                                                'Start_Time': start_time,
                                                'End_Time': end_time,
                                                'Time_Actual': time_actual,
                                                'Time_Actual_Minutes': time_actual_min,
                                                'Initial_Participants': initial_participants,
                                                'Drops': drops,
                                                'Initial_Difficulty': initial_difficulty,
                                                'Actual_Difficulty': actual_difficulty,
                                                'Temperature_Multiplier': temp_multiplier,
                                                'Equipment_Details': str(equipment_details)  # Store as string for DataFrame
                                            }
                                            
                                            # Check if we already have an entry for this team, day, event number, and event name
                                            if not existing_record.empty:
                                                # Update the existing record
                                                st.session_state.event_records.loc[existing_record.index[0]] = new_record
                                                st.success(f"Event data updated for {event_name}")
                                            else:
                                                # Add new record
                                                st.session_state.event_records = pd.concat([
                                                    st.session_state.event_records,
                                                    pd.DataFrame([new_record])
                                                ], ignore_index=True)
                                                st.success(f"Event data recorded for {event_name}")
                                            
                                            # Automatically save the session after recording data
                                            save_session_state()
                                            
                                            # Rerun to refresh the UI
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error saving event data: {str(e)}")
                        
                        # Drops Management Tab
                        with drops_tab:
                            st.write(f"### Manage Drops for {event_name}")
                            
                            # Display the current participants
                            st.write("#### Current Participants")
                            try:
                                # Get all drops for this team across all events
                                all_team_drops = pd.DataFrame()
                                if not st.session_state.drop_data.empty:
                                    all_team_drops = st.session_state.drop_data[
                                        st.session_state.drop_data['Team'] == team_name
                                    ]
                                
                                # Get drops from previous events (earlier days or earlier events on same day)
                                previous_drops_df = pd.DataFrame()
                                if not all_team_drops.empty:
                                    # Previous events drops query
                                    prev_drops_query = (
                                        # Earlier day
                                        (all_team_drops['Day'] < day) |
                                        # Same day but earlier event
                                        ((all_team_drops['Day'] == day) & (all_team_drops['Event_Number'] < event_number))
                                    )
                                    previous_drops_df = all_team_drops[prev_drops_query]
                                    previous_drops = previous_drops_df['Roster_Number'].unique().tolist()
                                
                                # Get drops specific to this event
                                current_drops = []
                                current_drops_df = pd.DataFrame()
                                if not all_team_drops.empty:
                                    current_drops_df = all_team_drops[
                                        (all_team_drops['Day'] == day) &
                                        (all_team_drops['Event_Number'] == event_number) &
                                        (all_team_drops['Event_Name'] == event_name)
                                    ]
                                    current_drops = current_drops_df['Roster_Number'].tolist()
                                
                                # Get the participant list from the team roster
                                current_participants = team_roster.copy()
                                
                                # Filter out previously dropped participants
                                if previous_drops_df is not None and not previous_drops_df.empty:
                                    previous_drops = previous_drops_df['Roster_Number'].unique().tolist()
                                    if previous_drops:
                                        current_participants = current_participants[
                                            ~current_participants['Roster_Number'].isin(previous_drops)
                                        ]
                                
                                # Further filter out those who dropped in this specific event
                                active_participants = current_participants.copy()
                                if current_drops:
                                    active_participants = active_participants[
                                        ~active_participants['Roster_Number'].isin(current_drops)
                                    ]
                                
                                # Show the adjusted initial participants count that will be used
                                st.write(f"**Initial participants for this event: {adjusted_initial_participants}**")
                                st.write(f"**Current drops for this event: {len(current_drops)}**")
                                st.write(f"**Remaining active participants: {adjusted_initial_participants - len(current_drops)}**")
                                
                                # Show the active participants with drop option
                                if not active_participants.empty:
                                    st.write(f"{len(active_participants)} active participants for this event:")
                                    
                                    # Create a selection for the participant to drop
                                    with st.form(f"drop_form_days3-4_{day}_{event_number}"):
                                        # Select a participant to drop
                                        participant_options = active_participants['Candidate_Name'].tolist()
                                        if participant_options:
                                            drop_participant = st.selectbox(
                                                "Select participant to mark as dropped:",
                                                options=participant_options,
                                                key=f"drop_participant_days3-4_{day}_{event_number}"
                                            )
                                            
                                            # Get the roster number for this participant
                                            drop_roster_number = active_participants[
                                                active_participants['Candidate_Name'] == drop_participant
                                            ]['Roster_Number'].values[0]
                                            
                                            # Create a unique session state key for this drop time
                                            drop_time_key = f"drop_time_days3-4_{team_name}_{day}_{event_number}"
                        
                                            # Initialize session state for this drop time if it doesn't exist
                                            if drop_time_key not in st.session_state:
                                                # Default to event start time if available, otherwise empty
                                                start_time_val = ""
                                                if not existing_record.empty:
                                                    start_time_val = existing_record.iloc[0]['Start_Time']
                                                
                                                st.session_state[drop_time_key] = start_time_val
                        
                                            # Create a callback to update the session state when the input changes
                                            def update_drop_time():
                                                # This will be called when the input changes
                                                pass  # The session state is automatically updated by Streamlit
                        
                                            # Enter drop time using session state to persist the value
                                            drop_time = st.text_input(
                                                "Drop Time (HH:MM)",
                                                key=drop_time_key,  # This key connects to the session state
                                                placeholder="e.g., 09:15",
                                                on_change=update_drop_time
                                            )
                                            
                                            # Submit button
                                            drop_submit = st.form_submit_button("Record Drop")
                                            if drop_submit:
                                                if drop_time:
                                                    try:
                                                        # Add to drop data
                                                        new_drop = {
                                                            'Team': team_name,
                                                            'Participant_Name': drop_participant,
                                                            'Roster_Number': drop_roster_number,
                                                            'Event_Name': event_name,
                                                            'Drop_Time': drop_time,
                                                            'Day': day,
                                                            'Event_Number': event_number
                                                        }
                                                        
                                                        # Create the drop_data DataFrame if it doesn't exist or is empty
                                                        if 'drop_data' not in st.session_state or st.session_state.drop_data.empty:
                                                            st.session_state.drop_data = pd.DataFrame([new_drop])
                                                        else:
                                                            # Check if this drop already exists
                                                            existing_drop = st.session_state.drop_data[
                                                                (st.session_state.drop_data['Team'] == team_name) &
                                                                (st.session_state.drop_data['Roster_Number'] == drop_roster_number) &
                                                                (st.session_state.drop_data['Day'] == day) &
                                                                (st.session_state.drop_data['Event_Number'] == event_number) &
                                                                (st.session_state.drop_data['Event_Name'] == event_name)
                                                            ]
                                                            
                                                            if existing_drop.empty:
                                                                # Add the new drop
                                                                st.session_state.drop_data = pd.concat([
                                                                    st.session_state.drop_data,
                                                                    pd.DataFrame([new_drop])
                                                                ], ignore_index=True)
                                                            else:
                                                                # Update the existing drop
                                                                st.session_state.drop_data.loc[existing_drop.index[0], 'Drop_Time'] = drop_time
                                                        
                                                        # Update the corresponding event record if it exists
                                                        if not st.session_state.event_records.empty:
                                                            event_record = st.session_state.event_records[
                                                                (st.session_state.event_records['Team'] == team_name) &
                                                                (st.session_state.event_records['Day'] == day) &
                                                                (st.session_state.event_records['Event_Number'] == event_number) &
                                                                (st.session_state.event_records['Event_Name'] == event_name)
                                                            ]
                                                            
                                                            if not event_record.empty:
                                                                # Get the current drops count
                                                                drops_query = (
                                                                    (st.session_state.drop_data['Team'] == team_name) &
                                                                    (st.session_state.drop_data['Day'] == day) &
                                                                    (st.session_state.drop_data['Event_Number'] == event_number) &
                                                                    (st.session_state.drop_data['Event_Name'] == event_name)
                                                                )
                                                                drops_count = len(st.session_state.drop_data[drops_query])
                                                                
                                                                # Update the drops count in the event record
                                                                st.session_state.event_records.loc[event_record.index[0], 'Drops'] = drops_count
                                                                
                                                                # Recalculate the actual difficulty with the new drops count
                                                                record = event_record.iloc[0]
                                                                temp_multiplier = record['Temperature_Multiplier']
                                                                total_weight = record['Equipment_Weight'] * record['Number_of_Equipment']
                                                                initial_participants = record['Initial_Participants']
                                                                distance_km = record['Distance_km']
                                                                time_actual_min = record['Time_Actual_Minutes']
                                                                
                                                                # Recalculate actual difficulty
                                                                actual_difficulty = calculate_actual_difficulty(
                                                                    temp_multiplier, total_weight, initial_participants,
                                                                    distance_km, time_actual_min, drops_count,
                                                                    st.session_state.drop_data[drops_query], day, event_number, event_name,
                                                                    record['Start_Time']
                                                                )
                                                                
                                                                # Update the actual difficulty
                                                                st.session_state.event_records.loc[event_record.index[0], 'Actual_Difficulty'] = actual_difficulty
                                                        
                                                        # Update ALL subsequent event records for this team to reflect the drop
                                                        if not st.session_state.event_records.empty:
                                                            # Get all events for this team that occur after the current event
                                                            subsequent_events = st.session_state.event_records[
                                                                (st.session_state.event_records['Team'] == team_name) &
                                                                (
                                                                    # Later day
                                                                    (st.session_state.event_records['Day'] > day) |
                                                                    # Same day but later event
                                                                    ((st.session_state.event_records['Day'] == day) &
                                                                     (st.session_state.event_records['Event_Number'] > event_number))
                                                                )
                                                            ]
                                                            
                                                            # For each subsequent event, update the initial participants count
                                                            for idx, event_record in subsequent_events.iterrows():
                                                                # Calculate the updated initial participants for this subsequent event
                                                                event_day = event_record['Day']
                                                                event_num = event_record['Event_Number']
                                                                
                                                                # Get drops from events before this one
                                                                prev_drops_to_event = st.session_state.drop_data[
                                                                    (st.session_state.drop_data['Team'] == team_name) &
                                                                    (
                                                                        # Earlier day
                                                                        (st.session_state.drop_data['Day'] < event_day) |
                                                                        # Same day but earlier event
                                                                        ((st.session_state.drop_data['Day'] == event_day) &
                                                                         (st.session_state.drop_data['Event_Number'] < event_num))
                                                                    )
                                                                ]['Roster_Number'].unique()
                                                                
                                                                # Calculate new initial participants count
                                                                updated_initial_participants = team_size - len(prev_drops_to_event)
                                                                
                                                                # Update the event record
                                                                st.session_state.event_records.loc[idx, 'Initial_Participants'] = updated_initial_participants
                                                                
                                                                # Recalculate difficulty scores with the updated initial participants
                                                                record = st.session_state.event_records.loc[idx]
                                                                
                                                                # Get current drop count for this event
                                                                event_drops = st.session_state.drop_data[
                                                                    (st.session_state.drop_data['Team'] == team_name) &
                                                                    (st.session_state.drop_data['Day'] == event_day) &
                                                                    (st.session_state.drop_data['Event_Number'] == event_num) &
                                                                    (st.session_state.drop_data['Event_Name'] == record['Event_Name'])
                                                                ]
                                                                drops_count = len(event_drops)
                                                                
                                                                # Recalculate initial difficulty
                                                                initial_difficulty = calculate_initial_difficulty(
                                                                    record['Temperature_Multiplier'],
                                                                    record['Equipment_Weight'] * record['Number_of_Equipment'],
                                                                    updated_initial_participants,
                                                                    record['Distance_km'],
                                                                    time_str_to_minutes(record['Time_Limit'])
                                                                )
                                                                
                                                                # Recalculate actual difficulty
                                                                actual_difficulty = calculate_actual_difficulty(
                                                                    record['Temperature_Multiplier'],
                                                                    record['Equipment_Weight'] * record['Number_of_Equipment'],
                                                                    updated_initial_participants,
                                                                    record['Distance_km'],
                                                                    record['Time_Actual_Minutes'],
                                                                    drops_count,
                                                                    event_drops,
                                                                    event_day,
                                                                    event_num,
                                                                    record['Event_Name'],
                                                                    record['Start_Time']
                                                                )
                                                                
                                                                # Update difficulty scores
                                                                st.session_state.event_records.loc[idx, 'Initial_Difficulty'] = initial_difficulty
                                                                st.session_state.event_records.loc[idx, 'Actual_Difficulty'] = actual_difficulty
                                                        
                                                        st.success(f"{drop_participant} marked as dropped at {drop_time}")
                                                        
                                                        # Save session
                                                        save_session_state()
                                                        
                                                        # Need to rerun to refresh the UI
                                                        st.rerun()
                                                    except Exception as e:
                                                        st.error(f"Error recording drop: {str(e)}")
                                                else:
                                                    st.error("Please enter a valid drop time.")
                                        else:
                                            st.write("No participants available to drop.")
                                    
                                    # Display current active participants in a table format
                                    st.write("#### Active Participants List")
                                    active_display = active_participants[['Candidate_Name', 'Candidate_Type', 'Roster_Number']]
                                    active_display.columns = ['Participant', 'Type', 'Roster #']
                                    st.dataframe(active_display)
                                else:
                                    if previous_drops_df is not None and not previous_drops_df.empty:
                                        st.warning(f"Initial participants for this event: {adjusted_initial_participants}")
                                        if len(current_drops) == adjusted_initial_participants:
                                            st.info("All participants have dropped from this event.")
                                        else:
                                            st.info("No active participants remaining for this event.")
                                    else:
                                        st.info("All participants have dropped from this event.")
                                
                                # If there are participants who dropped from previous events, show them
                                if previous_drops_df is not None and not previous_drops_df.empty:
                                    st.write("#### Participants Dropped from Previous Events")
                                    # Group by participant to show their last drop
                                    participant_last_drops = previous_drops_df.sort_values(['Day', 'Event_Number'], ascending=False)
                                    participant_last_drops = participant_last_drops.drop_duplicates('Roster_Number')
                                    
                                    # Create a nice display table
                                    prev_drop_display = participant_last_drops[['Participant_Name', 'Day', 'Event_Number', 'Event_Name']].copy()
                                    prev_drop_display.columns = ['Participant', 'Day', 'Event #', 'Dropped During']
                                    prev_drop_display = prev_drop_display.sort_values(['Day', 'Event #'])
                                    st.dataframe(prev_drop_display)
                                    st.info(f"These {len(prev_drop_display)} participants dropped from previous events and are not eligible for this event.")
                                
                                # Display the participants who have dropped in this specific event
                                st.write("#### Dropped Participants (This Event)")
                                if not current_drops_df.empty:
                                    # Create a table of dropped participants
                                    st.write(f"{len(current_drops_df)} participants have dropped from this event:")
                                    
                                    # Create a dataframe for display
                                    drop_display = current_drops_df[['Participant_Name', 'Drop_Time']].copy()
                                    drop_display.columns = ['Participant', 'Drop Time']
                                    
                                    # Display the dataframe with a "Remove" button column
                                    st.dataframe(drop_display)
                                    
                                    # Add a form to remove drops with a unique key
                                    with st.form(f"remove_drop_form_days3-4_{day}_{event_number}"):
                                        st.write("Remove a participant from the drop list:")
                                        
                                        # Select a participant to remove from drops
                                        remove_options = current_drops_df['Participant_Name'].tolist()
                                        if remove_options:
                                            participant_to_remove = st.selectbox(
                                                "Select participant:",
                                                options=remove_options,
                                                key=f"remove_participant_days3-4_{day}_{event_number}"
                                            )
                                            
                                            # Get the roster number
                                            remove_roster_number = current_drops_df[
                                                current_drops_df['Participant_Name'] == participant_to_remove
                                            ]['Roster_Number'].values[0]
                                            
                                            # Submit button
                                            remove_submit = st.form_submit_button("Remove Drop")
                                            if remove_submit:
                                                try:
                                                    # Remove this drop from the drop_data
                                                    st.session_state.drop_data = st.session_state.drop_data[
                                                        ~((st.session_state.drop_data['Team'] == team_name) &
                                                        (st.session_state.drop_data['Day'] == day) &
                                                        (st.session_state.drop_data['Event_Number'] == event_number) &
                                                        (st.session_state.drop_data['Event_Name'] == event_name) &
                                                        (st.session_state.drop_data['Roster_Number'] == remove_roster_number))
                                                    ]
                                                    
                                                    # Update the corresponding event record if it exists
                                                    if not st.session_state.event_records.empty:
                                                        event_record = st.session_state.event_records[
                                                            (st.session_state.event_records['Team'] == team_name) &
                                                            (st.session_state.event_records['Day'] == day) &
                                                            (st.session_state.event_records['Event_Number'] == event_number) &
                                                            (st.session_state.event_records['Event_Name'] == event_name)
                                                        ]
                                                        
                                                        if not event_record.empty:
                                                            # Recalculate the current drops count
                                                            drops_query = (
                                                                (st.session_state.drop_data['Team'] == team_name) &
                                                                (st.session_state.drop_data['Day'] == day) &
                                                                (st.session_state.drop_data['Event_Number'] == event_number) &
                                                                (st.session_state.drop_data['Event_Name'] == event_name)
                                                            )
                                                            drops_count = len(st.session_state.drop_data[drops_query])
                                                            
                                                            # Update the drops count in the event record
                                                            st.session_state.event_records.loc[event_record.index[0], 'Drops'] = drops_count
                                                            
                                                            # Recalculate the actual difficulty with the updated drops count
                                                            record = event_record.iloc[0]
                                                            temp_multiplier = record['Temperature_Multiplier']
                                                            total_weight = record['Equipment_Weight'] * record['Number_of_Equipment']
                                                            initial_participants = record['Initial_Participants']
                                                            distance_km = record['Distance_km']
                                                            time_actual_min = record['Time_Actual_Minutes']
                                                            
                                                            # Recalculate actual difficulty
                                                            actual_difficulty = calculate_actual_difficulty(
                                                                temp_multiplier, total_weight, initial_participants,
                                                                distance_km, time_actual_min, drops_count,
                                                                st.session_state.drop_data[drops_query], day, event_number, event_name,
                                                                record['Start_Time']
                                                            )
                                                            
                                                            # Update the actual difficulty
                                                            st.session_state.event_records.loc[event_record.index[0], 'Actual_Difficulty'] = actual_difficulty
                                                    
                                                    # Update ALL subsequent event records for this team to reflect the removed drop
                                                    if not st.session_state.event_records.empty:
                                                        # Get all events for this team that occur after the current event
                                                        subsequent_events = st.session_state.event_records[
                                                            (st.session_state.event_records['Team'] == team_name) &
                                                            (
                                                                # Later day
                                                                (st.session_state.event_records['Day'] > day) |
                                                                # Same day but later event
                                                                ((st.session_state.event_records['Day'] == day) &
                                                                 (st.session_state.event_records['Event_Number'] > event_number))
                                                            )
                                                        ]
                                                        
                                                        # For each subsequent event, update the initial participants count
                                                        for idx, event_record in subsequent_events.iterrows():
                                                            # Calculate the updated initial participants for this subsequent event
                                                            event_day = event_record['Day']
                                                            event_num = event_record['Event_Number']
                                                            
                                                            # Get drops from events before this one
                                                            prev_drops_to_event = st.session_state.drop_data[
                                                                (st.session_state.drop_data['Team'] == team_name) &
                                                                (
                                                                    # Earlier day
                                                                    (st.session_state.drop_data['Day'] < event_day) |
                                                                    # Same day but earlier event
                                                                    ((st.session_state.drop_data['Day'] == event_day) &
                                                                     (st.session_state.drop_data['Event_Number'] < event_num))
                                                                )
                                                            ]['Roster_Number'].unique()
                                                            
                                                            # Calculate new initial participants count
                                                            updated_initial_participants = team_size - len(prev_drops_to_event)
                                                            
                                                            # Update the event record
                                                            st.session_state.event_records.loc[idx, 'Initial_Participants'] = updated_initial_participants
                                                            
                                                            # Recalculate difficulty scores with the updated initial participants
                                                            record = st.session_state.event_records.loc[idx]
                                                            
                                                            # Get current drop count for this event
                                                            event_drops = st.session_state.drop_data[
                                                                (st.session_state.drop_data['Team'] == team_name) &
                                                                (st.session_state.drop_data['Day'] == event_day) &
                                                                (st.session_state.drop_data['Event_Number'] == event_num) &
                                                                (st.session_state.drop_data['Event_Name'] == record['Event_Name'])
                                                            ]
                                                            drops_count = len(event_drops)
                                                            
                                                            # Recalculate initial difficulty
                                                            initial_difficulty = calculate_initial_difficulty(
                                                                record['Temperature_Multiplier'],
                                                                record['Equipment_Weight'] * record['Number_of_Equipment'],
                                                                updated_initial_participants,
                                                                record['Distance_km'],
                                                                time_str_to_minutes(record['Time_Limit'])
                                                            )
                                                            
                                                            # Recalculate actual difficulty
                                                            actual_difficulty = calculate_actual_difficulty(
                                                                record['Temperature_Multiplier'],
                                                                record['Equipment_Weight'] * record['Number_of_Equipment'],
                                                                updated_initial_participants,
                                                                record['Distance_km'],
                                                                record['Time_Actual_Minutes'],
                                                                drops_count,
                                                                event_drops,
                                                                event_day,
                                                                event_num,
                                                                record['Event_Name'],
                                                                record['Start_Time']
                                                            )
                                                            
                                                            # Update difficulty scores
                                                            st.session_state.event_records.loc[idx, 'Initial_Difficulty'] = initial_difficulty
                                                            st.session_state.event_records.loc[idx, 'Actual_Difficulty'] = actual_difficulty
                                                    
                                                    st.success(f"Removed drop for {participant_to_remove}")
                                                    
                                                    # Save session and refresh
                                                    save_session_state()
                                                    st.rerun()
                                                except Exception as e:
                                                    st.error(f"Error removing drop: {str(e)}")
                                        else:
                                            st.write("No participants to remove.")
                                else:
                                    st.info("No participants have dropped from this specific event yet.")
                            except Exception as e:
                                st.error(f"Error in drop management: {str(e)}")
                                st.info("Please try refreshing the page if you encounter issues with drop management.")
                
                # After all event expanders, add a section to show completion status for this day
                st.write("---")
                st.write("### Day Completion Status")
                
                # Check how many events are recorded for this day and team
                recorded_events = []
                if not st.session_state.event_records.empty and 'Team' in st.session_state.event_records.columns:
                    day_records = st.session_state.event_records[
                        (st.session_state.event_records['Team'] == team_name) &
                        (st.session_state.event_records['Day'] == day)
                    ]
                    recorded_events = day_records['Event_Name'].tolist()
                
                # Display completion status for each event
                for event_idx, event_name in enumerate(day_events):
                    if event_name in recorded_events:
                        st.write(f"✅ Event {event_idx+1}: {event_name} - **Recorded**")
                    else:
                        st.write(f"❌ Event {event_idx+1}: {event_name} - **Not Recorded**")
                
                # Show completion percentage
                completion_pct = len(recorded_events) / len(day_events) * 100 if day_events else 0
                st.progress(completion_pct / 100)
                st.write(f"**Day {day} Completion: {completion_pct:.0f}%**")
        
        # After all day tabs, show a summary of all recorded events for this team
        st.write("---")
        st.subheader(f"Summary of All Recorded Events for {team_name}")
        if not st.session_state.event_records.empty and 'Team' in st.session_state.event_records.columns:
            team_records = st.session_state.event_records[
                st.session_state.event_records['Team'] == team_name
            ]
            if not team_records.empty:
                # Create a summary table
                summary_data = []
                for _, record in team_records.iterrows():
                    # Count drops for this event
                    drop_count = record['Drops']
                    summary_data.append({
                        'Day': record['Day'],
                        'Event': f"Event {record['Event_Number']}: {record['Event_Name']}",
                        'Time': f"{record['Start_Time']} - {record['End_Time']} ({record['Time_Actual']})",
                        'Distance': f"{record['Distance_km']} km",
                        'Heat': record['Heat_Category'],
                        'Participants': f"{record['Initial_Participants'] - drop_count} / {record['Initial_Participants']}",
                        'Drops': drop_count,
                        'Difficulty': f"{record['Actual_Difficulty']:.2f}"
                    })
                
                # Convert to DataFrame and display
                summary_df = pd.DataFrame(summary_data)
                st.dataframe(summary_df.sort_values(['Day', 'Event']), use_container_width=True)
                
                # Add download button for team records
                csv = team_records.to_csv(index=False)
                b64 = base64.b64encode(csv.encode()).decode()
                href = f'<a href="data:file/csv;base64,{b64}" download="{team_name}_event_records.csv">Download {team_name} Event Records</a>'
                st.markdown(href, unsafe_allow_html=True)
            else:
                st.info(f"No events recorded yet for {team_name}.")
        
        # Show a summary of all drops for this team
        if not st.session_state.drop_data.empty:
            team_drops = st.session_state.drop_data[
                st.session_state.drop_data['Team'] == team_name
            ]
            if not team_drops.empty:
                st.subheader(f"All Drops for {team_name}")
                
                # Group drops by day and event
                drop_summary = team_drops.groupby(['Day', 'Event_Number', 'Event_Name']).size().reset_index(name='Count')
                
                # Create a nicer display
                for _, drop_group in drop_summary.iterrows():
                    st.write(f"**Day {drop_group['Day']}, Event {drop_group['Event_Number']}: {drop_group['Event_Name']}** - {drop_group['Count']} drops")
                    
                    # Get the drops for this event
                    event_drops = team_drops[
                        (team_drops['Day'] == drop_group['Day']) &
                        (team_drops['Event_Number'] == drop_group['Event_Number']) &
                        (team_drops['Event_Name'] == drop_group['Event_Name'])
                    ]
                    
                    # Display in a table
                    drop_display = event_drops[['Participant_Name', 'Drop_Time']].sort_values('Drop_Time')
                    drop_display.columns = ['Participant', 'Drop Time']
                    st.table(drop_display)
            else:
                st.info(f"No drops recorded for {team_name}.")
    else:
        st.warning("Please complete team reshuffling first before recording events for Days 3-4.")
    
    # Display all recorded event data with team filter (outside the team selection)
    st.write("---")
    st.header("All Recorded Event Data for Days 3-4")
    if not st.session_state.event_records.empty:
        # Filter for Days 3-4 events
        days_3_4_records = st.session_state.event_records[
            st.session_state.event_records['Day'].isin([3, 4])
        ]
        
        if 'Team' in days_3_4_records.columns and not days_3_4_records.empty:
            # Get unique teams
            all_teams = days_3_4_records['Team'].unique().tolist()
            
            # Create a multiselect to filter by team
            selected_teams = st.multiselect(
                "Filter by Teams",
                options=all_teams,
                default=all_teams,
                key="days_3_4_team_filter"
            )
            
            # Filter event records by selected teams
            if selected_teams:
                filtered_records = days_3_4_records[
                    days_3_4_records['Team'].isin(selected_teams)
                ]
                
                # Add day and event type filters
                col1, col2 = st.columns(2)
                with col1:
                    days = st.multiselect(
                        "Filter by Days",
                        options=[3, 4],
                        default=[3, 4],
                        key="days_3_4_day_filter"
                    )
                with col2:
                    events = st.multiselect(
                        "Filter by Events",
                        options=sorted(filtered_records['Event_Name'].unique().tolist()),
                        default=sorted(filtered_records['Event_Name'].unique().tolist()),
                        key="days_3_4_event_filter"
                    )
                
                # Apply additional filters
                if days:
                    filtered_records = filtered_records[filtered_records['Day'].isin(days)]
                if events:
                    filtered_records = filtered_records[filtered_records['Event_Name'].isin(events)]
                
                # Display the filtered data
                if not filtered_records.empty:
                    # Select which columns to display
                    display_cols = ['Team', 'Day', 'Event_Number', 'Event_Name', 'Distance_km',
                                   'Time_Actual', 'Initial_Participants', 'Drops', 'Actual_Difficulty']
                    st.dataframe(filtered_records[display_cols], use_container_width=True)
                    
                    # Add a download button for the filtered data
                    csv = filtered_records.to_csv(index=False)
                    b64 = base64.b64encode(csv.encode()).decode()
                    href = f'<a href="data:file/csv;base64,{b64}" download="days_3_4_filtered_event_records.csv">Download Filtered Data as CSV</a>'
                    st.markdown(href, unsafe_allow_html=True)
                    
                    # Show drop data for the filtered teams
                    if not st.session_state.drop_data.empty:
                        filtered_drops = st.session_state.drop_data[
                            (st.session_state.drop_data['Team'].isin(selected_teams)) &
                            (st.session_state.drop_data['Day'].isin([3, 4]))
                        ]
                        if days:
                            filtered_drops = filtered_drops[filtered_drops['Day'].isin(days)]
                        if events:
                            filtered_drops = filtered_drops[filtered_drops['Event_Name'].isin(events)]
                        
                        if not filtered_drops.empty:
                            st.subheader("Drops for Selected Teams/Events")
                            
                            # Group by team, day, event
                            drop_summary = filtered_drops.groupby(['Team', 'Day', 'Event_Number', 'Event_Name']).size().reset_index(name='Drop_Count')
                            
                            # Display as a table
                            drop_summary = drop_summary.sort_values(['Team', 'Day', 'Event_Number'])
                            st.dataframe(drop_summary, use_container_width=True)
                            
                            # Option to view detailed drop data
                            if st.checkbox("View detailed drop data", key="view_detailed_drops_days3-4"):
                                st.dataframe(filtered_drops.sort_values(['Team', 'Day', 'Event_Number', 'Drop_Time']), use_container_width=True)
                                
                                # Add download button for drop data
                                csv = filtered_drops.to_csv(index=False)
                                b64 = base64.b64encode(csv.encode()).decode()
                                href = f'<a href="data:file/csv;base64,{b64}" download="days_3_4_filtered_drop_data.csv">Download Drop Data</a>'
                                st.markdown(href, unsafe_allow_html=True)
                else:
                    st.info("No records match the selected filters.")
            else:
                st.info("Please select at least one team to view records.")
        else:
            st.info("No event records available for Days 3-4 yet.")
    else:
        st.info("No event records available yet. Use the form above to record events.")

    # Display combined statistics comparing Days 1-2 vs Days 3-4
    st.write("---")
    st.header("Comparison: Days 1-2 vs Days 3-4")
    if not st.session_state.event_records.empty:
        # Split data by days
        days_1_2_data = st.session_state.event_records[st.session_state.event_records['Day'].isin([1, 2])]
        days_3_4_data = st.session_state.event_records[st.session_state.event_records['Day'].isin([3, 4])]
        
        if not days_1_2_data.empty and not days_3_4_data.empty:
            # Calculate summary statistics
            stats_days_1_2 = {
                'Average Difficulty': days_1_2_data['Actual_Difficulty'].mean(),
                'Max Difficulty': days_1_2_data['Actual_Difficulty'].max(),
                'Min Difficulty': days_1_2_data['Actual_Difficulty'].min(),
                'Total Events': len(days_1_2_data),
                'Total Drops': days_1_2_data['Drops'].sum()
            }
            
            stats_days_3_4 = {
                'Average Difficulty': days_3_4_data['Actual_Difficulty'].mean(),
                'Max Difficulty': days_3_4_data['Actual_Difficulty'].max(),
                'Min Difficulty': days_3_4_data['Actual_Difficulty'].min(),
                'Total Events': len(days_3_4_data),
                'Total Drops': days_3_4_data['Drops'].sum()
            }
            
            # Create a DataFrame for display
            comparison_df = pd.DataFrame({
                'Statistic': stats_days_1_2.keys(),
                'Days 1-2': stats_days_1_2.values(),
                'Days 3-4': stats_days_3_4.values(),
                'Change': [stats_days_3_4[k] - stats_days_1_2[k] for k in stats_days_1_2.keys()]
            })
            
            # Format the numeric columns
            for col in ['Days 1-2', 'Days 3-4', 'Change']:
                comparison_df[col] = comparison_df[col].apply(lambda x: f"{x:.2f}" if isinstance(x, float) else f"{x}")
            
            # Add a percent change column for applicable metrics
            comparison_df['Percent Change'] = ''
            for i, stat in enumerate(stats_days_1_2.keys()):
                if stat in ['Average Difficulty', 'Max Difficulty', 'Min Difficulty'] and stats_days_1_2[stat] != 0:
                    pct_change = (stats_days_3_4[stat] - stats_days_1_2[stat]) / stats_days_1_2[stat] * 100
                    comparison_df.loc[i, 'Percent Change'] = f"{pct_change:+.1f}%"
            
            # Display the comparison
            st.dataframe(comparison_df, use_container_width=True)
            
            # Create a visualization of the comparison
            import plotly.express as px
            
            # Prepare data for visualization
            viz_data = []
            for day in [1, 2, 3, 4]:
                day_data = st.session_state.event_records[st.session_state.event_records['Day'] == day]
                if not day_data.empty:
                    viz_data.append({
                        'Day': day,
                        'Average Difficulty': day_data['Actual_Difficulty'].mean(),
                        'Total Events': len(day_data),
                        'Total Drops': day_data['Drops'].sum()
                    })
            
            if viz_data:
                viz_df = pd.DataFrame(viz_data)
                
                # Create a bar chart for average difficulty by day
                fig = px.bar(
                    viz_df,
                    x='Day',
                    y='Average Difficulty',
                    title='Average Difficulty by Day',
                    labels={'Average Difficulty': 'Average Difficulty Score'},
                    color='Day',
                    color_continuous_scale='Viridis'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Create a line chart for drops by day
                fig2 = px.line(
                    viz_df,
                    x='Day',
                    y='Total Drops',
                    title='Total Drops by Day',
                    labels={'Total Drops': 'Number of Drops'},
                    markers=True
                )
                st.plotly_chart(fig2, use_container_width=True)
        else:
            if days_1_2_data.empty:
                st.warning("No data available for Days 1-2. Please record events for Days 1-2 first.")
            else:
                st.warning("No data available for Days 3-4 yet. Please record events for Days 3-4.")
    else:
        st.info("No event records available for comparison yet.")
        
                                        
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
                
                # Visualize final team scores
                if 'Team' in final_team_scores.columns:
                    fig = px.bar(
                        final_team_scores, 
                        x='Team', 
                        y='Average_Difficulty',
                        title='Final Team Difficulty Scores',
                        labels={'Average_Difficulty': 'Average Difficulty', 'Team': 'Team'},
                        color='Average_Difficulty',
                        color_continuous_scale='Viridis'
                    )
                    # Add a line for overall average
                    overall_avg = final_team_scores['Average_Difficulty'].mean()
                    fig.add_hline(
                        y=overall_avg,
                        line_dash="dash",
                        line_color="red",
                        annotation_text=f"Overall Avg: {overall_avg:.2f}",
                        annotation_position="top right"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
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
                
                # Add difficulty scores for each phase
                if 'Team' in team_difficulty_days_1_2.columns:
                    # Calculate average difficulty by team for days 1-2
                    team_avg_days_1_2 = team_difficulty_days_1_2.groupby('Team')['Actual_Difficulty'].mean().reset_index()
                    team_avg_days_1_2.columns = ['Team', 'Avg_Difficulty_Days_1_2']
                    
                    # Map to participants
                    team_map_days_1_2 = dict(zip(team_avg_days_1_2['Team'], team_avg_days_1_2['Avg_Difficulty_Days_1_2']))
                    all_participants_df['Difficulty_Days_1_2'] = all_participants_df['Team_Days_1_2'].map(team_map_days_1_2)
                
                if 'Team' in team_difficulty_days_3_4.columns:
                    # Calculate average difficulty by team for days 3-4
                    team_avg_days_3_4 = team_difficulty_days_3_4.groupby('Team')['Actual_Difficulty'].mean().reset_index()
                    team_avg_days_3_4.columns = ['Team', 'Avg_Difficulty_Days_3_4']
                    
                    # Map to participants
                    team_map_days_3_4 = dict(zip(team_avg_days_3_4['Team'], team_avg_days_3_4['Avg_Difficulty_Days_3_4']))
                    all_participants_df['Difficulty_Days_3_4'] = all_participants_df['Team_Days_3_4'].map(team_map_days_3_4)
                
                # Calculate overall average difficulty
                if 'Difficulty_Days_1_2' in all_participants_df.columns and 'Difficulty_Days_3_4' in all_participants_df.columns:
                    all_participants_df['Overall_Difficulty'] = (all_participants_df['Difficulty_Days_1_2'] + all_participants_df['Difficulty_Days_3_4']) / 2
                    
                    # Sort by overall difficulty
                    all_participants_df = all_participants_df.sort_values('Overall_Difficulty', ascending=False)
                
                # Display participant performance
                st.dataframe(all_participants_df, use_container_width=True)
                
                # Add download buttons
                csv_final_teams = final_team_scores.to_csv(index=False)
                b64_teams = base64.b64encode(csv_final_teams.encode()).decode()
                href_teams = f'<a href="data:file/csv;base64,{b64_teams}" download="final_team_scores.csv">Download Final Team Scores</a>'
                st.markdown(href_teams, unsafe_allow_html=True)
                
                csv_participants = all_participants_df.to_csv(index=False)
                b64_participants = base64.b64encode(csv_participants.encode()).decode()
                href_participants = f'<a href="data:file/csv;base64,{b64_participants}" download="participant_performance.csv">Download Participant Performance Data</a>'
                st.markdown(href_participants, unsafe_allow_html=True)
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
        # Create tabs within the visualization section to organize content
        viz_tabs = st.tabs(["Difficulty Trends", "Team Performance", "Drops Analysis", "Correlations"])
        
        # Tab 1: Difficulty Trends
        with viz_tabs[0]:
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
            
            # Day comparison bar chart
            day_avg_difficulty = st.session_state.event_records.groupby('Day')['Actual_Difficulty'].mean().reset_index()
            fig5 = px.bar(
                day_avg_difficulty,
                x='Day',
                y='Actual_Difficulty',
                title='Average Difficulty by Day',
                labels={'Actual_Difficulty': 'Average Difficulty Score'}
            )
            st.plotly_chart(fig5, use_container_width=True)
        
        # Tab 2: Team Performance
        with viz_tabs[1]:
            # Team difficulty comparison
            if 'Team' in st.session_state.event_records.columns:
                st.subheader("Team Performance")
                team_difficulty = st.session_state.event_records.groupby('Team')['Actual_Difficulty'].mean().reset_index()
                team_difficulty = team_difficulty.sort_values('Actual_Difficulty', ascending=False)
                fig_team = px.bar(
                    team_difficulty,
                    x='Team',
                    y='Actual_Difficulty',
                    title='Average Difficulty Score by Team',
                    labels={'Actual_Difficulty': 'Average Difficulty Score'},
                    color='Actual_Difficulty',
                    color_continuous_scale='Viridis'
                )
                st.plotly_chart(fig_team, use_container_width=True)
            
            # Team reshuffling visualization (if teams have been reshuffled)
            if st.session_state.reshuffled_teams is not None:
                # Heat map of difficulty by team and day (more space-efficient than multiple charts)
                if 'Team' in st.session_state.event_records.columns:
                    st.subheader("Difficulty Heat Map by Team and Day")
                    
                    # Calculate average difficulty by team and day
                    heatmap_data = st.session_state.event_records.groupby(['Team', 'Day'])['Actual_Difficulty'].mean().reset_index()
                    
                    # Pivot the data for the heat map
                    heatmap_pivot = heatmap_data.pivot(index='Team', columns='Day', values='Actual_Difficulty')
                    
                    # Create heat map
                    fig12 = px.imshow(
                        heatmap_pivot,
                        labels=dict(x="Day", y="Team", color="Difficulty"),
                        x=heatmap_pivot.columns,
                        y=heatmap_pivot.index,
                        color_continuous_scale='Viridis',
                        title='Difficulty Heat Map by Team and Day'
                    )
                    
                    # Add text annotations with values
                    for i in range(len(heatmap_pivot.index)):
                        for j in range(len(heatmap_pivot.columns)):
                            value = heatmap_pivot.iloc[i, j]
                            if not pd.isna(value):  # Only add annotation if value is not NaN
                                fig12.add_annotation(
                                    x=heatmap_pivot.columns[j],
                                    y=heatmap_pivot.index[i],
                                    text=f"{value:.2f}",
                                    showarrow=False,
                                    font=dict(color="white" if value > 3 else "black")
                                )
                    
                    st.plotly_chart(fig12, use_container_width=True)
        
        # Tab 3: Drops Analysis
        with viz_tabs[2]:
            if not st.session_state.drop_data.empty:
                st.subheader("Participant Drops Analysis")
                
                # Drops by day and event (combined chart)
                drops_by_day = st.session_state.drop_data.groupby('Day').size().reset_index(name='Number_of_Drops')
                
                # Create the main drops chart
                fig6 = px.bar(
                    drops_by_day,
                    x='Day',
                    y='Number_of_Drops',
                    title='Number of Drops by Day',
                    labels={'Number_of_Drops': 'Number of Drops'}
                )
                st.plotly_chart(fig6, use_container_width=True)
                
                # Team drops chart (if team data available)
                if 'Team' in st.session_state.drop_data.columns:
                    # Create a dropdown to select visualization type
                    drop_viz_type = st.selectbox(
                        "Select Drops Analysis View", 
                        ["Drops by Team", "Drops by Team and Day"]
                    )
                    
                    if drop_viz_type == "Drops by Team":
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
                        # Drops by team and day
                        drops_by_team_day = st.session_state.drop_data.groupby(['Team', 'Day']).size().reset_index(name='Number_of_Drops')
                        
                        fig8 = px.bar(
                            drops_by_team_day,
                            x='Team',
                            y='Number_of_Drops',
                            color='Day',
                            barmode='group',
                            title='Number of Drops by Team and Day',
                            labels={'Number_of_Drops': 'Number of Drops'}
                        )
                        st.plotly_chart(fig8, use_container_width=True)
            else:
                st.info("No drop data available for analysis.")
        
        # Tab 4: Correlations
        with viz_tabs[3]:
            st.subheader("Correlations with Difficulty")
            
            # Add a selector for correlation type
            correlation_type = st.radio(
                "Select Correlation Analysis",
                ["Equipment Weight vs Difficulty", "Distance vs Difficulty"],
                horizontal=True
            )
            
            if correlation_type == "Equipment Weight vs Difficulty":
                # Equipment weight vs difficulty correlation
                fig10 = px.scatter(
                    st.session_state.event_records,
                    x='Equipment_Weight',
                    y='Actual_Difficulty',
                    color='Day',
                    hover_data=['Event_Name', 'Team'],
                    title='Equipment Weight vs Difficulty',
                    labels={
                        'Equipment_Weight': 'Equipment Weight (lbs)',
                        'Actual_Difficulty': 'Actual Difficulty',
                        'Day': 'Day'
                    },
                    trendline="ols"  # Add regression line
                )
                
                st.plotly_chart(fig10, use_container_width=True)
            else:
                # Distance vs difficulty correlation
                fig11 = px.scatter(
                    st.session_state.event_records,
                    x='Distance_km',
                    y='Actual_Difficulty',
                    color='Day',
                    hover_data=['Event_Name', 'Team'],
                    title='Distance vs Difficulty',
                    labels={
                        'Distance_km': 'Distance (km)',
                        'Actual_Difficulty': 'Actual Difficulty',
                        'Day': 'Day'
                    },
                    trendline="ols"  # Add regression line
                )
                
                st.plotly_chart(fig11, use_container_width=True)
        
        # Download data button at the bottom of all tabs
        st.write("---")
        if st.button("Download All Visualization Data"):
            # Prepare data for download
            viz_data = {
                'difficulty_trends': difficulty_trends,
                'day_avg_difficulty': day_avg_difficulty
            }
            
            if 'Team' in st.session_state.event_records.columns:
                viz_data['team_difficulty'] = team_difficulty
            
            if not st.session_state.drop_data.empty:
                viz_data['drops_by_day'] = drops_by_day
                if 'Team' in st.session_state.drop_data.columns:
                    viz_data['drops_by_team'] = drops_by_team
                    viz_data['drops_by_team_day'] = drops_by_team_day
            
            # Create a zip file with all visualization data
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w') as zip_file:
                for name, df in viz_data.items():
                    zip_file.writestr(f"{name}.csv", df.to_csv(index=False))
            
            buffer.seek(0)
            b64 = base64.b64encode(buffer.read()).decode()
            href = f'<a href="data:application/zip;base64,{b64}" download="visualization_data.zip">Download All Visualization Data</a>'
            st.markdown(href, unsafe_allow_html=True)
    else:
        st.warning("No event data available for visualization. Please record events first.")

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