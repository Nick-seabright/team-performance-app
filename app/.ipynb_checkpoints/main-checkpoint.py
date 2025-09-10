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
    load_roster_data, load_equipment_data, load_events_data, 
    time_str_to_minutes, minutes_to_time_str
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
        'Day', 'Event_Number', 'Event_Name', 'Equipment_Name', 'Equipment_Weight',
        'Number_of_Equipment', 'Distance_km', 'Heat_Category', 'Time_Limit',
        'Time_Actual', 'Initial_Participants', 'Drops', 'Initial_Difficulty',
        'Actual_Difficulty'
    ])
if 'drop_data' not in st.session_state:
    st.session_state.drop_data = pd.DataFrame(columns=[
        'Participant_Name', 'Roster_Number', 'Event_Name', 'Drop_Time', 'Day', 'Event_Number'
    ])
if 'reshuffled_teams' not in st.session_state:
    st.session_state.reshuffled_teams = None

# Functions for session state persistence
def save_session_state():
    """Save session state to disk"""
    state_dict = {}
    
    # Convert DataFrames to dictionaries
    if st.session_state.roster_data is not None:
        state_dict['roster_data'] = st.session_state.roster_data.to_dict()
    
    if st.session_state.equipment_data is not None:
        state_dict['equipment_data'] = st.session_state.equipment_data.to_dict()
    
    if st.session_state.events_data is not None:
        state_dict['events_data'] = st.session_state.events_data.to_dict()
    
    if not st.session_state.event_records.empty:
        state_dict['event_records'] = st.session_state.event_records.to_dict()
    
    if not st.session_state.drop_data.empty:
        state_dict['drop_data'] = st.session_state.drop_data.to_dict()
    
    if st.session_state.reshuffled_teams is not None:
        state_dict['reshuffled_teams'] = st.session_state.reshuffled_teams.to_dict()
    
    # Save to file
    with open('session_state.json', 'w') as f:
        json.dump(state_dict, f)
    
    return True

def load_session_state():
    """Load session state from disk"""
    if not os.path.exists('session_state.json'):
        return False
    
    try:
        with open('session_state.json', 'r') as f:
            state_dict = json.load(f)
        
        # Convert dictionaries back to DataFrames
        if 'roster_data' in state_dict:
            st.session_state.roster_data = pd.DataFrame.from_dict(state_dict['roster_data'])
        
        if 'equipment_data' in state_dict:
            st.session_state.equipment_data = pd.DataFrame.from_dict(state_dict['equipment_data'])
        
        if 'events_data' in state_dict:
            st.session_state.events_data = pd.DataFrame.from_dict(state_dict['events_data'])
        
        if 'event_records' in state_dict:
            st.session_state.event_records = pd.DataFrame.from_dict(state_dict['event_records'])
        
        if 'drop_data' in state_dict:
            st.session_state.drop_data = pd.DataFrame.from_dict(state_dict['drop_data'])
        
        if 'reshuffled_teams' in state_dict:
            st.session_state.reshuffled_teams = pd.DataFrame.from_dict(state_dict['reshuffled_teams'])
        
        return True
    except Exception as e:
        st.error(f"Error loading session state: {str(e)}")
        return False

# Title and description
st.title("Team Performance Management and Analysis")
st.markdown("Manage roster, equipment, events, and analyze team performance for a 4-day event.")

# Create tabs for different sections
tabs = st.tabs(["Data Upload", "Event Recording", "Drop Management", "Team Reshuffling", 
                "Adjust Difficulty", "Final Scores", "Visualizations", "Predictive Analytics"])

# Tab 1: Data Upload
with tabs[0]:
    st.header("Upload Data")
    
    # Roster Upload
    st.subheader("Roster Upload")
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
    
    # Equipment Table Upload
    st.subheader("Equipment Table Upload")
    equip_upload_method = st.radio("Choose upload method for equipment:", ["CSV File", "SQL Server"])
    
    if equip_upload_method == "CSV File":
        equip_file = st.file_uploader("Upload Equipment CSV", type="csv")
        if equip_file:
            st.session_state.equipment_data = load_equipment_data(equip_file)
            st.success(f"Equipment data uploaded successfully with {len(st.session_state.equipment_data)} items.")
    else:
        st.text_input("SQL Server Connection String for Equipment")
        sql_query_equip = st.text_area("SQL Query for Equipment")
        if st.button("Connect and Load Equipment"):
            st.error("SQL connection not implemented in this demo. Please use CSV upload.")
    
    # Events Table Upload
    st.subheader("Events Table Upload")
    events_upload_method = st.radio("Choose upload method for events:", ["CSV File", "SQL Server"])
    
    if events_upload_method == "CSV File":
        events_file = st.file_uploader("Upload Events CSV", type="csv")
        if events_file:
            st.session_state.events_data = load_events_data(events_file)
            st.success(f"Events data uploaded successfully with {len(st.session_state.events_data)} events.")
    else:
        st.text_input("SQL Server Connection String for Events")
        sql_query_events = st.text_area("SQL Query for Events")
        if st.button("Connect and Load Events"):
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

# Tab 2: Event Recording
with tabs[1]:
    st.header("Event Data Recording")
    
    # Create a form for event data input
    with st.form("event_data_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            day = st.selectbox("Day", options=[1, 2, 3, 4])
            event_number = st.selectbox("Event Number", options=[1, 2, 3])
            
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
                initial_parts = selected_event.get('Initial_Participants', 0)
            else:
                time_limit_str = '00:00'
                initial_parts = 0
            
            time_limit = st.text_input("Time Limit (mm:ss)", value=time_limit_str)
            time_actual = st.text_input("Time Actual (mm:ss)")
            initial_participants = st.number_input(
                "Initial Participants", 
                value=initial_parts,
                min_value=0
            )
            drops = st.number_input("Drops", min_value=0)
        
        submit_button = st.form_submit_button("Record Event Data")
        
        if submit_button:
            # Convert time strings to minutes for calculations
            time_limit_min = time_str_to_minutes(time_limit)
            time_actual_min = time_str_to_minutes(time_actual)
            
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
            
            actual_difficulty = calculate_actual_difficulty(
                temp_multiplier, total_weight, initial_participants, 
                distance_km, time_actual_min, drops, 
                st.session_state.drop_data, day, event_number, event_name
            )
            
            # Create new record
            new_record = {
                'Day': day,
                'Event_Number': event_number,
                'Event_Name': event_name,
                'Equipment_Name': equipment_name,
                'Equipment_Weight': equipment_weight,
                'Number_of_Equipment': num_equipment,
                'Distance_km': distance_km,
                'Heat_Category': heat_category,
                'Time_Limit': time_limit,
                'Time_Actual': time_actual,
                'Initial_Participants': initial_participants,
                'Drops': drops,
                'Initial_Difficulty': initial_difficulty,
                'Actual_Difficulty': actual_difficulty,
                'Temperature_Multiplier': temp_multiplier
            }
            
            # Add to event records
            st.session_state.event_records = pd.concat([
                st.session_state.event_records, 
                pd.DataFrame([new_record])
            ], ignore_index=True)
            
            st.success(f"Event data recorded successfully for Day {day}, Event {event_number}: {event_name}")
    
    # Display recorded event data
    if not st.session_state.event_records.empty:
        st.subheader("Recorded Event Data")
        st.dataframe(st.session_state.event_records)

# Tab 3: Drop Management
with tabs[2]:
    st.header("Drop Management")
    
    # Create a form for recording participant drops
    with st.form("drop_data_form"):
        if st.session_state.roster_data is not None:
            participant = st.selectbox(
                "Participant", 
                options=st.session_state.roster_data['Candidate_Name'].tolist()
            )
            roster_number = st.session_state.roster_data[
                st.session_state.roster_data['Candidate_Name'] == participant
            ]['Roster_Number'].values[0]
        else:
            participant = st.text_input("Participant Name")
            roster_number = st.text_input("Roster Number")
        
        if st.session_state.events_data is not None:
            event_name = st.selectbox(
                "Event Name", 
                options=st.session_state.events_data['Event_Name'].unique()
            )
            # Get the day and event number for the selected event
            event_info = st.session_state.events_data[
                st.session_state.events_data['Event_Name'] == event_name
            ].iloc[0]
            day = event_info['Day']
            event_number = event_info['Event_Number']
        else:
            event_name = st.text_input("Event Name")
            day = st.selectbox("Day", options=[1, 2, 3, 4])
            event_number = st.selectbox("Event Number", options=[1, 2, 3])
        
        drop_time = st.text_input("Drop Time (mm:ss)")
        
        submit_drop = st.form_submit_button("Record Drop")
        
        if submit_drop:
            # Add to drop data
            new_drop = {
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
            
            st.success(f"Drop recorded successfully for {participant} during {event_name}")
    
    # Display drop data
    if not st.session_state.drop_data.empty:
        st.subheader("Recorded Drop Data")
        st.dataframe(st.session_state.drop_data)

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
                all_drops = st.session_state.drop_data['Participant_Name'].unique()
                active_participants = st.session_state.roster_data[
                    ~st.session_state.roster_data['Candidate_Name'].isin(all_drops)
                ]
                
                # Calculate difficulty scores for each participant
                team_difficulty_scores = days_1_2_data.groupby(['Day', 'Event_Number'])['Actual_Difficulty'].mean().reset_index()
                
                # Reshuffle teams based on difficulty scores
                st.session_state.reshuffled_teams = reshuffle_teams(
                    active_participants, 
                    team_difficulty_scores
                )
                
                st.success("Teams reshuffled successfully for Days 3 and 4!")
            
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

# Tab 6: Final Scores
with tabs[5]:
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
                # Join event data with team data to get team for each event
                # This is a simplified approach - in a real app, you'd track which teams participated in each event
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
                
                # Calculate difficulty scores by team for days 3-4
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
                final_team_scores = all_team_difficulties.groupby('Day')['Actual_Difficulty'].mean().reset_index()
                
                st.subheader("Final Team Difficulty Scores (All Days)")
                st.dataframe(final_team_scores)
                
                # Calculate individual participant scores
                # This would require tracking individual participation in events
                st.write("Note: Individual participant scores would require tracking individual participation in each event.")
            else:
                st.warning("Data for Days 3-4 not available yet or teams haven't been reshuffled.")
        else:
            st.warning("Please upload roster data and record event data to calculate final scores.")
    else:
        st.warning("No event data available. Please record events first.")

# Tab 7: Visualizations
with tabs[6]:
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
        
        # 2. Team reshuffling visualization (if teams have been reshuffled)
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
            
            # 3. Difficulty score distributions by team
            st.subheader("Difficulty Score Distribution by Team")
            
            # For this visualization, we need to combine team information with event scores
            # This is a simplified approach - in a real app, you'd track which teams participated in each event
            
            # For Days 1-2, use original teams
            if not st.session_state.event_records[st.session_state.event_records['Day'].isin([1, 2])].empty:
                days_1_2_events = st.session_state.event_records[st.session_state.event_records['Day'].isin([1, 2])]
                
                # Create a distribution plot for Days 1-2
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
                fig4 = px.box(
                    days_3_4_events,
                    x='Day',
                    y='Actual_Difficulty',
                    title='Difficulty Score Distribution for Days 3-4',
                    labels={'Actual_Difficulty': 'Difficulty Score'}
                )
                st.plotly_chart(fig4, use_container_width=True)
        
        # 4. Final difficulty scores grouped by team
        st.subheader("Final Difficulty Scores by Team")
        
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
            
        # 5. Drops analysis
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
    else:
        st.warning("No event data available for visualization. Please record events first.")

# Tab 8: Predictive Analytics
with tabs[7]:
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
                st.write(f"- Extend time limit to approximately {minutes_to_time_str(extended_time)}")
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
    
    # Provide download link
    buffer.seek(0)
    b64 = base64.b64encode(buffer.read()).decode()
    href = f'<a href="data:application/zip;base64,{b64}" download="team_performance_data.zip">Download All Data</a>'
    st.sidebar.markdown(href, unsafe_allow_html=True)

# Session state persistence
if st.sidebar.button("Save Current Session"):
    if save_session_state():
        st.sidebar.success("Session saved successfully!")

if st.sidebar.button("Load Previous Session"):
    if load_session_state():
        st.sidebar.success("Session loaded successfully!")
    else:
        st.sidebar.warning("No previous session found.")

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