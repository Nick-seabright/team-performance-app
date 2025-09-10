import pandas as pd
import streamlit as st

def load_roster_data(file):
    """
    Load roster data from a CSV file
    """
    try:
        df = pd.read_csv(file)
        
        # Ensure required columns exist
        required_columns = ['Candidate_Name', 'Roster_Number', 'Candidate_Type', 'Initial_Team']
        for col in required_columns:
            if col not in df.columns:
                st.error(f"Required column '{col}' not found in the roster CSV file.")
                return None
        
        return df
    except Exception as e:
        st.error(f"Error loading roster data: {str(e)}")
        return None

def load_equipment_data(file):
    """
    Load equipment data from a CSV file
    """
    try:
        df = pd.read_csv(file)
        
        # Ensure required columns exist
        required_columns = ['Equipment_Name', 'Equipment_Weight']
        for col in required_columns:
            if col not in df.columns:
                st.error(f"Required column '{col}' not found in the equipment CSV file.")
                return None
        
        return df
    except Exception as e:
        st.error(f"Error loading equipment data: {str(e)}")
        return None

def load_events_data(file):
    """
    Load events data from a CSV file
    """
    try:
        df = pd.read_csv(file)
        
        # Ensure required columns exist
        required_columns = ['Event_Name', 'Day', 'Event_Number', 'Equipment_Name', 
                          'Equipment_Weight', 'Number_of_Equipment', 'Time_Limit', 
                          'Initial_Participants', 'Distance']
        for col in required_columns:
            if col not in df.columns:
                st.error(f"Required column '{col}' not found in the events CSV file.")
                return None
        
        return df
    except Exception as e:
        st.error(f"Error loading events data: {str(e)}")
        return None

def time_str_to_minutes(time_str):
    """
    Convert time string in format 'mm:ss' to minutes (float)
    """
    try:
        parts = time_str.split(':')
        if len(parts) != 2:
            raise ValueError("Time must be in format 'mm:ss'")
        
        minutes = int(parts[0])
        seconds = int(parts[1])
        
        return minutes + seconds / 60
    except Exception as e:
        st.error(f"Error converting time: {str(e)}")
        return 0

def minutes_to_time_str(minutes):
    """
    Convert minutes (float) to time string in format 'mm:ss'
    """
    try:
        total_seconds = int(minutes * 60)
        mins = total_seconds // 60
        secs = total_seconds % 60
        
        return f"{mins:02d}:{secs:02d}"
    except Exception as e:
        st.error(f"Error converting minutes to time string: {str(e)}")
        return "00:00"