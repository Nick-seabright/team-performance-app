import pandas as pd
import streamlit as st
import os
import numpy as np

def load_roster_data(file=None):
    """
    Load roster data from a CSV file or use default data
    """
    try:
        if file is None:
            # Use default data
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            default_path = os.path.join(script_dir, 'data', 'sample_roster.csv')
            if os.path.exists(default_path):
                df = pd.read_csv(default_path)
            else:
                # Create sample data if file doesn't exist
                df = create_default_roster()
                # Save it for future use
                df.to_csv(default_path, index=False)
        else:
            df = pd.read_csv(file)
        
        # Ensure required columns exist
        required_columns = ['Candidate_Name', 'Roster_Number', 'Candidate_Type', 'Initial_Team']
        
        # Check if all required columns exist
        for col in required_columns:
            if col not in df.columns:
                st.error(f"Required column '{col}' not found in the roster CSV file.")
                return None
        
        return df
    except Exception as e:
        st.error(f"Error loading roster data: {str(e)}")
        return None

def load_equipment_data(file=None):
    """
    Extract unique equipment data from the event equipment table
    """
    try:
        # Get the combined event equipment data
        event_equip_data = load_event_equip_data(file)
        
        if event_equip_data is None:
            return None
        
        # Extract unique equipment entries
        equipment_cols = ['EquipID', 'EquipmentName', 'EquipmentCategory', 'EquipWt']
        equipment_data = event_equip_data[equipment_cols].drop_duplicates('EquipID')
        
        # Add Equipment_Name and Equipment_Weight columns for compatibility with the app
        equipment_data['Equipment_Name'] = equipment_data['EquipmentName']
        equipment_data['Equipment_Weight'] = equipment_data['EquipWt']
        
        return equipment_data
    except Exception as e:
        st.error(f"Error loading equipment data: {str(e)}")
        return None

def load_event_equip_data(file=None):
    """
    Load event equipment data from a CSV file or use default data
    """
    try:
        if file is None:
            # Use default data
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            default_path = os.path.join(script_dir, 'data', 'event_equipment.csv')
            if os.path.exists(default_path):
                df = pd.read_csv(default_path)
            else:
                # Create sample data from the provided data
                df = create_default_event_equipment()
                # Save it for future use
                df.to_csv(default_path, index=False)
        else:
            df = pd.read_csv(file)
        
        return df
    except Exception as e:
        st.error(f"Error loading event equipment data: {str(e)}")
        return None

def load_events_data(file=None):
    """
    Transform event equipment data into the format needed for the app
    """
    try:
        # Get the combined event equipment data
        event_equip_data = load_event_equip_data(file)
        
        if event_equip_data is None:
            return None
        
        # Group by EventID and EventName to get unique events
        events = event_equip_data.groupby(['EventID', 'EventName']).first().reset_index()
        
        # Create a combined events DataFrame
        combined_events = []
        
        # Process each unique event
        for _, event in events.iterrows():
            event_id = event['EventID']
            
            # Get all equipment for this event
            event_equipment = event_equip_data[event_equip_data['EventID'] == event_id]
            
            # Calculate total weight and count
            total_weight = event_equipment['AppRatioWT'].sum()
            total_count = event_equipment['EquipNum'].sum()
            
            # Get distance and time
            distance_km = event_equipment['Distance_KM'].iloc[0]
            time_std = event_equipment['Time_STD'].iloc[0]  # Time limit in minutes
            
            # Convert time limit from minutes to mm:ss format
            total_minutes = int(time_std)
            seconds = int((time_std - total_minutes) * 60)
            time_limit = f"{total_minutes:02d}:{seconds:02d}"
            
            # Distribute events across days (1-4) and event numbers (1-3)
            # Simple distribution: events 1-6 on day 1, 7-12 on day 2, etc.
            day = min(4, ((event_id - 1) // 6) + 1)
            event_number = ((event_id - 1) % 3) + 1
            
            # Create combined event record
            combined_event = {
                'Day': day,
                'Event_Number': event_number,
                'Event_Name': event['EventName'],
                'Equipment_Name': 'MIXED EQUIPMENT' if len(event_equipment) > 1 else event_equipment.iloc[0]['EquipmentName'],
                'Equipment_Weight': total_weight,
                'Number_of_Equipment': total_count,
                'Time_Limit': time_limit,  # Format: mm:ss
                'Initial_Participants': 18,  # Default team size
                'Distance': distance_km
            }
            
            combined_events.append(combined_event)
        
        # Create DataFrame from the combined events
        combined_df = pd.DataFrame(combined_events)
        
        # Save the combined data for future use
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        combined_path = os.path.join(script_dir, 'data', 'events_combined.csv')
        combined_df.to_csv(combined_path, index=False)
        
        return combined_df
    except Exception as e:
        st.error(f"Error creating events data: {str(e)}")
        return None

def create_default_event_equipment():
    """Create the default event equipment data based on the provided structure"""
    # The data you provided with some minor formatting fixes
    data = [
        {'EventEquipID': 1, 'EventID': 1, 'EventName': 'AMMO CAN LOW CARRY', 'EquipID': 1, 'EquipmentName': 'AMMO CAN', 'EquipmentCategory': 'AMMO CAN', 'EquipNum': 4, 'EquipWt': 120, 'AppRatio': 1, 'AppRatioWT': 480, 'Distance_KM': 7, 'Time_STD': 185},
        {'EventEquipID': 2, 'EventID': 1, 'EventName': 'AMMO CAN LOW CARRY', 'EquipID': 21, 'EquipmentName': 'TIRE', 'EquipmentCategory': 'TIRE', 'EquipNum': 4, 'EquipWt': 50, 'AppRatio': 5, 'AppRatioWT': 40, 'Distance_KM': 7, 'Time_STD': 185},
        {'EventEquipID': 3, 'EventID': 1, 'EventName': 'AMMO CAN LOW CARRY', 'EquipID': 16, 'EquipmentName': '2"x10\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 6, 'EquipWt': 45, 'AppRatio': 1, 'AppRatioWT': 270, 'Distance_KM': 7, 'Time_STD': 185},
        {'EventEquipID': 4, 'EventID': 1, 'EventName': 'AMMO CAN LOW CARRY', 'EquipID': 17, 'EquipmentName': '3"x10\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 1, 'EquipWt': 60, 'AppRatio': 1, 'AppRatioWT': 60, 'Distance_KM': 7, 'Time_STD': 185},
        {'EventEquipID': 5, 'EventID': 2, 'EventName': 'AMMO CAN APP', 'EquipID': 1, 'EquipmentName': 'AMMO CAN', 'EquipmentCategory': 'AMMO CAN', 'EquipNum': 7, 'EquipWt': 120, 'AppRatio': 5, 'AppRatioWT': 168, 'Distance_KM': 3.7, 'Time_STD': 195},
        {'EventEquipID': 6, 'EventID': 2, 'EventName': 'AMMO CAN APP', 'EquipID': 21, 'EquipmentName': 'TIRE', 'EquipmentCategory': 'TIRE', 'EquipNum': 4, 'EquipWt': 50, 'AppRatio': 5, 'AppRatioWT': 40, 'Distance_KM': 3.7, 'Time_STD': 195},
        {'EventEquipID': 7, 'EventID': 2, 'EventName': 'AMMO CAN APP', 'EquipID': 16, 'EquipmentName': '2"x10\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 6, 'EquipWt': 45, 'AppRatio': 5, 'AppRatioWT': 54, 'Distance_KM': 3.7, 'Time_STD': 195},
        {'EventEquipID': 8, 'EventID': 2, 'EventName': 'AMMO CAN APP', 'EquipID': 17, 'EquipmentName': '3"x10\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 1, 'EquipWt': 60, 'AppRatio': 5, 'AppRatioWT': 12, 'Distance_KM': 3.7, 'Time_STD': 195},
        {'EventEquipID': 9, 'EventID': 3, 'EventName': 'AMMO CAN HIGH CARRY', 'EquipID': 1, 'EquipmentName': 'AMMO CAN', 'EquipmentCategory': 'AMMO CAN', 'EquipNum': 4, 'EquipWt': 120, 'AppRatio': 1, 'AppRatioWT': 480, 'Distance_KM': 7, 'Time_STD': 210},
        {'EventEquipID': 10, 'EventID': 3, 'EventName': 'AMMO CAN HIGH CARRY', 'EquipID': 21, 'EquipmentName': 'TIRE', 'EquipmentCategory': 'TIRE', 'EquipNum': 4, 'EquipWt': 50, 'AppRatio': 5, 'AppRatioWT': 40, 'Distance_KM': 7, 'Time_STD': 210},
        {'EventEquipID': 11, 'EventID': 3, 'EventName': 'AMMO CAN HIGH CARRY', 'EquipID': 16, 'EquipmentName': '2"x10\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 6, 'EquipWt': 45, 'AppRatio': 1, 'AppRatioWT': 270, 'Distance_KM': 7, 'Time_STD': 210},
        {'EventEquipID': 12, 'EventID': 3, 'EventName': 'AMMO CAN HIGH CARRY', 'EquipID': 17, 'EquipmentName': '3"x10\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 1, 'EquipWt': 60, 'AppRatio': 1, 'AppRatioWT': 60, 'Distance_KM': 7, 'Time_STD': 210},
        {'EventEquipID': 14, 'EventID': 4, 'EventName': 'AMMO CRATE APP', 'EquipID': 21, 'EquipmentName': 'TIRE', 'EquipmentCategory': 'TIRE', 'EquipNum': 4, 'EquipWt': 50, 'AppRatio': 5, 'AppRatioWT': 40, 'Distance_KM': 4.1, 'Time_STD': 285},
        {'EventEquipID': 13, 'EventID': 4, 'EventName': 'AMMO CRATE APP', 'EquipID': 2, 'EquipmentName': 'AMMO CRATE', 'EquipmentCategory': 'AMMO CRATE', 'EquipNum': 8, 'EquipWt': 100, 'AppRatio': 5, 'AppRatioWT': 160, 'Distance_KM': 4.1, 'Time_STD': 285},
        {'EventEquipID': 15, 'EventID': 4, 'EventName': 'AMMO CRATE APP', 'EquipID': 16, 'EquipmentName': '2"x10\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 3, 'EquipWt': 45, 'AppRatio': 5, 'AppRatioWT': 27, 'Distance_KM': 4.1, 'Time_STD': 285},
        {'EventEquipID': 16, 'EventID': 4, 'EventName': 'AMMO CRATE APP', 'EquipID': 17, 'EquipmentName': '3"x10\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 1, 'EquipWt': 60, 'AppRatio': 5, 'AppRatioWT': 12, 'Distance_KM': 4.1, 'Time_STD': 285},
        {'EventEquipID': 17, 'EventID': 5, 'EventName': 'AMMO CRATE LOW CARRY', 'EquipID': 2, 'EquipmentName': 'AMMO CRATE', 'EquipmentCategory': 'AMMO CRATE', 'EquipNum': 7, 'EquipWt': 100, 'AppRatio': 1, 'AppRatioWT': 700, 'Distance_KM': 8.16, 'Time_STD': 240},
        {'EventEquipID': 19, 'EventID': 6, 'EventName': 'DOWN PILOT HIGH CARRY', 'EquipID': 16, 'EquipmentName': '2"x10\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 12, 'EquipWt': 45, 'AppRatio': 1, 'AppRatioWT': 540, 'Distance_KM': 6.7, 'Time_STD': 330},
        {'EventEquipID': 22, 'EventID': 7, 'EventName': 'DOWN PILOT APP', 'EquipID': 21, 'EquipmentName': 'TIRE', 'EquipmentCategory': 'TIRE', 'EquipNum': 4, 'EquipWt': 50, 'AppRatio': 5, 'AppRatioWT': 40, 'Distance_KM': 4.2, 'Time_STD': 210},
        {'EventEquipID': 21, 'EventID': 7, 'EventName': 'DOWN PILOT APP', 'EquipID': 16, 'EquipmentName': '2"x10\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 12, 'EquipWt': 45, 'AppRatio': 5, 'AppRatioWT': 108, 'Distance_KM': 4.2, 'Time_STD': 210},
        {'EventEquipID': 23, 'EventID': 7, 'EventName': 'DOWN PILOT APP', 'EquipID': 17, 'EquipmentName': '3"x10\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 1, 'EquipWt': 60, 'AppRatio': 5, 'AppRatioWT': 12, 'Distance_KM': 4.2, 'Time_STD': 210},
        {'EventEquipID': 26, 'EventID': 8, 'EventName': 'DOWN PILOT APP W/JEEP & TRAILER', 'EquipID': 16, 'EquipmentName': '2"x10\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 7, 'EquipWt': 45, 'AppRatio': 10, 'AppRatioWT': 31.5, 'Distance_KM': 3.95, 'Time_STD': 240},
        {'EventEquipID': 24, 'EventID': 8, 'EventName': 'DOWN PILOT APP W/JEEP & TRAILER', 'EquipID': 3, 'EquipmentName': 'JEEP', 'EquipmentCategory': 'JEEP', 'EquipNum': 1, 'EquipWt': 2440, 'AppRatio': 10, 'AppRatioWT': 244, 'Distance_KM': 3.95, 'Time_STD': 240},
        {'EventEquipID': 18, 'EventID': 6, 'EventName': 'DOWN PILOT HIGH CARRY', 'EquipID': 20, 'EquipmentName': 'SANDMEN', 'EquipmentCategory': 'SANDMEN', 'EquipNum': 3, 'EquipWt': 250, 'AppRatio': 1, 'AppRatioWT': 750, 'Distance_KM': 6.7, 'Time_STD': 330},
        {'EventEquipID': 20, 'EventID': 7, 'EventName': 'DOWN PILOT APP', 'EquipID': 20, 'EquipmentName': 'SANDMEN', 'EquipmentCategory': 'SANDMEN', 'EquipNum': 3, 'EquipWt': 250, 'AppRatio': 5, 'AppRatioWT': 150, 'Distance_KM': 4.2, 'Time_STD': 210},
        {'EventEquipID': 25, 'EventID': 8, 'EventName': 'DOWN PILOT APP W/JEEP & TRAILER', 'EquipID': 20, 'EquipmentName': 'SANDMEN', 'EquipmentCategory': 'SANDMEN', 'EquipNum': 2, 'EquipWt': 250, 'AppRatio': 10, 'AppRatioWT': 50, 'Distance_KM': 3.95, 'Time_STD': 240},
        {'EventEquipID': 27, 'EventID': 8, 'EventName': 'DOWN PILOT APP W/JEEP & TRAILER', 'EquipID': 22, 'EquipmentName': 'TRAILER', 'EquipmentCategory': 'TRAILER', 'EquipNum': 1, 'EquipWt': 575, 'AppRatio': 10, 'AppRatioWT': 57.5, 'Distance_KM': 3.95, 'Time_STD': 240},
        {'EventEquipID': 28, 'EventID': 8, 'EventName': 'DOWN PILOT APP W/JEEP & TRAILER', 'EquipID': 1, 'EquipmentName': 'AMMO CAN', 'EquipmentCategory': 'AMMO CAN', 'EquipNum': 1, 'EquipWt': 120, 'AppRatio': 10, 'AppRatioWT': 12, 'Distance_KM': 3.95, 'Time_STD': 240},
        {'EventEquipID': 29, 'EventID': 9, 'EventName': 'DOWN PILOT HIGH CARRY W/JEEP', 'EquipID': 3, 'EquipmentName': 'JEEP', 'EquipmentCategory': 'JEEP', 'EquipNum': 1, 'EquipWt': 2440, 'AppRatio': 5, 'AppRatioWT': 488, 'Distance_KM': 7.22, 'Time_STD': 360},
        {'EventEquipID': 30, 'EventID': 9, 'EventName': 'DOWN PILOT HIGH CARRY W/JEEP', 'EquipID': 20, 'EquipmentName': 'SANDMEN', 'EquipmentCategory': 'SANDMEN', 'EquipNum': 2, 'EquipWt': 250, 'AppRatio': 1, 'AppRatioWT': 500, 'Distance_KM': 7.22, 'Time_STD': 360},
        {'EventEquipID': 31, 'EventID': 9, 'EventName': 'DOWN PILOT HIGH CARRY W/JEEP', 'EquipID': 16, 'EquipmentName': '2"x10\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 10, 'EquipWt': 45, 'AppRatio': 1, 'AppRatioWT': 450, 'Distance_KM': 7.22, 'Time_STD': 360},
        {'EventEquipID': 32, 'EventID': 9, 'EventName': 'DOWN PILOT HIGH CARRY W/JEEP', 'EquipID': 2, 'EquipmentName': 'AMMO CRATE', 'EquipmentCategory': 'AMMO CRATE', 'EquipNum': 4, 'EquipWt': 100, 'AppRatio': 1, 'AppRatioWT': 400, 'Distance_KM': 7.22, 'Time_STD': 360},
        {'EventEquipID': 33, 'EventID': 10, 'EventName': 'PAILS OF PAIN', 'EquipID': 16, 'EquipmentName': '2"x10\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 10, 'EquipWt': 45, 'AppRatio': 1, 'AppRatioWT': 450, 'Distance_KM': 7.22, 'Time_STD': 270},
        {'EventEquipID': 34, 'EventID': 10, 'EventName': 'PAILS OF PAIN', 'EquipID': 13, 'EquipmentName': '2"x6\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 1, 'EquipWt': 27, 'AppRatio': 1, 'AppRatioWT': 27, 'Distance_KM': 7.22, 'Time_STD': 270},
        {'EventEquipID': 35, 'EventID': 10, 'EventName': 'PAILS OF PAIN', 'EquipID': 17, 'EquipmentName': '3"x10\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 1, 'EquipWt': 60, 'AppRatio': 1, 'AppRatioWT': 60, 'Distance_KM': 7.22, 'Time_STD': 270},
        {'EventEquipID': 36, 'EventID': 10, 'EventName': 'PAILS OF PAIN', 'EquipID': 10, 'EquipmentName': 'PAIL', 'EquipmentCategory': 'PAIL', 'EquipNum': 27, 'EquipWt': 35, 'AppRatio': 1, 'AppRatioWT': 945, 'Distance_KM': 7.22, 'Time_STD': 270},
        {'EventEquipID': 37, 'EventID': 11, 'EventName': 'RED DOT AMMO CAN APP', 'EquipID': 9, 'EquipmentName': 'RED DOT LOG', 'EquipmentCategory': 'LOG', 'EquipNum': 1, 'EquipWt': 750, 'AppRatio': 5, 'AppRatioWT': 150, 'Distance_KM': 3.95, 'Time_STD': 210},
        {'EventEquipID': 38, 'EventID': 11, 'EventName': 'RED DOT AMMO CAN APP', 'EquipID': 17, 'EquipmentName': '3"x10\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 1, 'EquipWt': 60, 'AppRatio': 5, 'AppRatioWT': 12, 'Distance_KM': 3.95, 'Time_STD': 210},
        {'EventEquipID': 39, 'EventID': 11, 'EventName': 'RED DOT AMMO CAN APP', 'EquipID': 21, 'EquipmentName': 'TIRE', 'EquipmentCategory': 'TIRE', 'EquipNum': 4, 'EquipWt': 50, 'AppRatio': 5, 'AppRatioWT': 40, 'Distance_KM': 3.95, 'Time_STD': 210},
        {'EventEquipID': 40, 'EventID': 11, 'EventName': 'RED DOT AMMO CAN APP', 'EquipID': 1, 'EquipmentName': 'AMMO CAN', 'EquipmentCategory': 'AMMO CAN', 'EquipNum': 5, 'EquipWt': 120, 'AppRatio': 5, 'AppRatioWT': 120, 'Distance_KM': 3.95, 'Time_STD': 210},
        {'EventEquipID': 41, 'EventID': 11, 'EventName': 'RED DOT AMMO CAN APP', 'EquipID': 16, 'EquipmentName': '2"x10\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 4, 'EquipWt': 45, 'AppRatio': 5, 'AppRatioWT': 36, 'Distance_KM': 3.95, 'Time_STD': 210},
        {'EventEquipID': 42, 'EventID': 12, 'EventName': 'RED DOT AMMO CRATE APP', 'EquipID': 9, 'EquipmentName': 'RED DOT LOG', 'EquipmentCategory': 'LOG', 'EquipNum': 1, 'EquipWt': 750, 'AppRatio': 5, 'AppRatioWT': 150, 'Distance_KM': 3.8, 'Time_STD': 200},
        {'EventEquipID': 43, 'EventID': 12, 'EventName': 'RED DOT AMMO CRATE APP', 'EquipID': 16, 'EquipmentName': '2"x10\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 4, 'EquipWt': 45, 'AppRatio': 5, 'AppRatioWT': 36, 'Distance_KM': 3.8, 'Time_STD': 200},
        {'EventEquipID': 44, 'EventID': 12, 'EventName': 'RED DOT AMMO CRATE APP', 'EquipID': 17, 'EquipmentName': '3"x10\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 1, 'EquipWt': 60, 'AppRatio': 5, 'AppRatioWT': 12, 'Distance_KM': 3.8, 'Time_STD': 200},
        {'EventEquipID': 45, 'EventID': 12, 'EventName': 'RED DOT AMMO CRATE APP', 'EquipID': 1, 'EquipmentName': 'AMMO CAN', 'EquipmentCategory': 'AMMO CAN', 'EquipNum': 5, 'EquipWt': 120, 'AppRatio': 5, 'AppRatioWT': 120, 'Distance_KM': 3.8, 'Time_STD': 200},
        {'EventEquipID': 46, 'EventID': 12, 'EventName': 'RED DOT AMMO CRATE APP', 'EquipID': 21, 'EquipmentName': 'TIRE', 'EquipmentCategory': 'TIRE', 'EquipNum': 4, 'EquipWt': 50, 'AppRatio': 5, 'AppRatioWT': 40, 'Distance_KM': 3.8, 'Time_STD': 200},
        {'EventEquipID': 47, 'EventID': 13, 'EventName': 'RED DOT APP', 'EquipID': 9, 'EquipmentName': 'RED DOT LOG', 'EquipmentCategory': 'LOG', 'EquipNum': 1, 'EquipWt': 750, 'AppRatio': 5, 'AppRatioWT': 150, 'Distance_KM': 3.8, 'Time_STD': 200},
        {'EventEquipID': 48, 'EventID': 13, 'EventName': 'RED DOT APP', 'EquipID': 16, 'EquipmentName': '2"x10\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 4, 'EquipWt': 45, 'AppRatio': 5, 'AppRatioWT': 36, 'Distance_KM': 3.8, 'Time_STD': 200},
        {'EventEquipID': 49, 'EventID': 13, 'EventName': 'RED DOT APP', 'EquipID': 17, 'EquipmentName': '3"x10\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 1, 'EquipWt': 60, 'AppRatio': 5, 'AppRatioWT': 12, 'Distance_KM': 3.8, 'Time_STD': 200},
        {'EventEquipID': 50, 'EventID': 13, 'EventName': 'RED DOT APP', 'EquipID': 1, 'EquipmentName': 'AMMO CAN', 'EquipmentCategory': 'AMMO CAN', 'EquipNum': 5, 'EquipWt': 120, 'AppRatio': 5, 'AppRatioWT': 120, 'Distance_KM': 3.8, 'Time_STD': 200},
        {'EventEquipID': 51, 'EventID': 13, 'EventName': 'RED DOT APP', 'EquipID': 21, 'EquipmentName': 'TIRE', 'EquipmentCategory': 'TIRE', 'EquipNum': 4, 'EquipWt': 50, 'AppRatio': 5, 'AppRatioWT': 40, 'Distance_KM': 3.8, 'Time_STD': 200},
        {'EventEquipID': 52, 'EventID': 14, 'EventName': 'RED DOT LOW CARRY', 'EquipID': 9, 'EquipmentName': 'RED DOT LOG', 'EquipmentCategory': 'LOG', 'EquipNum': 1, 'EquipWt': 750, 'AppRatio': 1, 'AppRatioWT': 750, 'Distance_KM': 6.7, 'Time_STD': 260},
        {'EventEquipID': 53, 'EventID': 15, 'EventName': 'RELEASE RUCK', 'EquipID': 18, 'EquipmentName': 'RUCK', 'EquipmentCategory': 'RUCK', 'EquipNum': 1, 'EquipWt': 65, 'AppRatio': 1, 'AppRatioWT': 65, 'Distance_KM': 3.8, 'Time_STD': 330},
        {'EventEquipID': 54, 'EventID': 16, 'EventName': 'SAND BABIES', 'EquipID': 19, 'EquipmentName': 'SAND BAG', 'EquipmentCategory': 'SAND BAG', 'EquipNum': 25, 'EquipWt': 50, 'AppRatio': 1, 'AppRatioWT': 1250, 'Distance_KM': 4, 'Time_STD': 120},
        {'EventEquipID': 55, 'EventID': 17, 'EventName': 'WATER CAN LOW CARRY', 'EquipID': 23, 'EquipmentName': 'WATER CAN', 'EquipmentCategory': 'WATER CAN', 'EquipNum': 18, 'EquipWt': 45, 'AppRatio': 1, 'AppRatioWT': 810, 'Distance_KM': 7, 'Time_STD': 165},
        {'EventEquipID': 56, 'EventID': 18, 'EventName': 'WATER DRUM APP', 'EquipID': 24, 'EquipmentName': 'WATER DRUM', 'EquipmentCategory': 'WATER DRUM', 'EquipNum': 2, 'EquipWt': 265, 'AppRatio': 5, 'AppRatioWT': 106, 'Distance_KM': 4.7, 'Time_STD': 225},
        {'EventEquipID': 57, 'EventID': 18, 'EventName': 'WATER DRUM APP', 'EquipID': 23, 'EquipmentName': 'WATER CAN', 'EquipmentCategory': 'WATER CAN', 'EquipNum': 2, 'EquipWt': 45, 'AppRatio': 5, 'AppRatioWT': 18, 'Distance_KM': 4.7, 'Time_STD': 225},
        {'EventEquipID': 58, 'EventID': 18, 'EventName': 'WATER DRUM APP', 'EquipID': 16, 'EquipmentName': '2"x10\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 5, 'EquipWt': 45, 'AppRatio': 5, 'AppRatioWT': 45, 'Distance_KM': 4.7, 'Time_STD': 225},
        {'EventEquipID': 59, 'EventID': 18, 'EventName': 'WATER DRUM APP', 'EquipID': 17, 'EquipmentName': '3"x10\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 1, 'EquipWt': 60, 'AppRatio': 5, 'AppRatioWT': 12, 'Distance_KM': 4.7, 'Time_STD': 225},
        {'EventEquipID': 60, 'EventID': 18, 'EventName': 'WATER DRUM APP', 'EquipID': 21, 'EquipmentName': 'TIRE', 'EquipmentCategory': 'TIRE', 'EquipNum': 4, 'EquipWt': 50, 'AppRatio': 5, 'AppRatioWT': 40, 'Distance_KM': 4.7, 'Time_STD': 225},
        {'EventEquipID': 61, 'EventID': 19, 'EventName': 'WATER DRUM HIGH CARRY', 'EquipID': 24, 'EquipmentName': 'WATER DRUM', 'EquipmentCategory': 'WATER DRUM', 'EquipNum': 2, 'EquipWt': 265, 'AppRatio': 1, 'AppRatioWT': 530, 'Distance_KM': 7.25, 'Time_STD': 315},
        {'EventEquipID': 62, 'EventID': 19, 'EventName': 'WATER DRUM HIGH CARRY', 'EquipID': 23, 'EquipmentName': 'WATER CAN', 'EquipmentCategory': 'WATER CAN', 'EquipNum': 6, 'EquipWt': 45, 'AppRatio': 1, 'AppRatioWT': 270, 'Distance_KM': 7.25, 'Time_STD': 315},
        {'EventEquipID': 63, 'EventID': 19, 'EventName': 'WATER DRUM HIGH CARRY', 'EquipID': 16, 'EquipmentName': '2"x10\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 10, 'EquipWt': 45, 'AppRatio': 1, 'AppRatioWT': 450, 'Distance_KM': 7.25, 'Time_STD': 315},
        {'EventEquipID': 64, 'EventID': 20, 'EventName': 'WATER DRUM LOW CARRY', 'EquipID': 24, 'EquipmentName': 'WATER DRUM', 'EquipmentCategory': 'WATER DRUM', 'EquipNum': 2, 'EquipWt': 265, 'AppRatio': 1, 'AppRatioWT': 530, 'Distance_KM': 6, 'Time_STD': 330},
        {'EventEquipID': 65, 'EventID': 20, 'EventName': 'WATER DRUM LOW CARRY', 'EquipID': 23, 'EquipmentName': 'WATER CAN', 'EquipmentCategory': 'WATER CAN', 'EquipNum': 6, 'EquipWt': 45, 'AppRatio': 1, 'AppRatioWT': 270, 'Distance_KM': 6, 'Time_STD': 330},
        {'EventEquipID': 66, 'EventID': 21, 'EventName': 'BUY BACK', 'EquipID': 16, 'EquipmentName': '2"x10\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 2, 'EquipWt': 45, 'AppRatio': 1, 'AppRatioWT': 90, 'Distance_KM': 4.4, 'Time_STD': 200},
        {'EventEquipID': 67, 'EventID': 21, 'EventName': 'BUY BACK', 'EquipID': 17, 'EquipmentName': '3"x10\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 1, 'EquipWt': 60, 'AppRatio': 1, 'AppRatioWT': 60, 'Distance_KM': 4.4, 'Time_STD': 200},
        {'EventEquipID': 68, 'EventID': 21, 'EventName': 'BUY BACK', 'EquipID': 13, 'EquipmentName': '2"x6\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 1, 'EquipWt': 27, 'AppRatio': 1, 'AppRatioWT': 27, 'Distance_KM': 4.4, 'Time_STD': 200},
        {'EventEquipID': 69, 'EventID': 21, 'EventName': 'BUY BACK', 'EquipID': 11, 'EquipmentName': '2"x4\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 2, 'EquipWt': 18, 'AppRatio': 1, 'AppRatioWT': 36, 'Distance_KM': 4.4, 'Time_STD': 200},
        {'EventEquipID': 70, 'EventID': 21, 'EventName': 'BUY BACK', 'EquipID': 15, 'EquipmentName': '3"x6\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 1, 'EquipWt': 36, 'AppRatio': 1, 'AppRatioWT': 36, 'Distance_KM': 4.4, 'Time_STD': 200},
        {'EventEquipID': 71, 'EventID': 21, 'EventName': 'BUY BACK', 'EquipID': 12, 'EquipmentName': '3"x4\' POLE', 'EquipmentCategory': 'POLE', 'EquipNum': 2, 'EquipWt': 24, 'AppRatio': 1, 'AppRatioWT': 48, 'Distance_KM': 4.4, 'Time_STD': 200},
        {'EventEquipID': 72, 'EventID': 21, 'EventName': 'BUY BACK', 'EquipID': 21, 'EquipmentName': 'TIRE', 'EquipmentCategory': 'TIRE', 'EquipNum': 4, 'EquipWt': 50, 'AppRatio': 5, 'AppRatioWT': 40, 'Distance_KM': 4.4, 'Time_STD': 200},
        {'EventEquipID': 73, 'EventID': 21, 'EventName': 'BUY BACK', 'EquipID': 2, 'EquipmentName': 'AMMO CRATE', 'EquipmentCategory': 'AMMO CRATE', 'EquipNum': 7, 'EquipWt': 100, 'AppRatio': 1, 'AppRatioWT': 700, 'Distance_KM': 4.4, 'Time_STD': 200},
        {'EventEquipID': 74, 'EventID': 22, 'EventName': 'JUNK YARD', 'EquipID': 9, 'EquipmentName': 'RED DOT LOG', 'EquipmentCategory': 'LOG', 'EquipNum': 7, 'EquipWt': 750, 'AppRatio': 1, 'AppRatioWT': 5250, 'Distance_KM': 13.9, 'Time_STD': 600},
        {'EventEquipID': 75, 'EventID': 22, 'EventName': 'JUNK YARD', 'EquipID': 8, 'EquipmentName': 'YELLOW DOT LOG', 'EquipmentCategory': 'LOG', 'EquipNum': 5, 'EquipWt': 550, 'AppRatio': 1, 'AppRatioWT': 2750, 'Distance_KM': 13.9, 'Time_STD': 600},
        {'EventEquipID': 76, 'EventID': 22, 'EventName': 'JUNK YARD', 'EquipID': 7, 'EquipmentName': 'WHITE DOT LOG', 'EquipmentCategory': 'LOG', 'EquipNum': 3, 'EquipWt': 375, 'AppRatio': 1, 'AppRatioWT': 1125, 'Distance_KM': 13.9, 'Time_STD': 600},
        {'EventEquipID': 77, 'EventID': 22, 'EventName': 'JUNK YARD', 'EquipID': 6, 'EquipmentName': '3 DOT LOG', 'EquipmentCategory': 'LOG', 'EquipNum': 4, 'EquipWt': 250, 'AppRatio': 1, 'AppRatioWT': 1000, 'Distance_KM': 13.9, 'Time_STD': 600},
        {'EventEquipID': 78, 'EventID': 22, 'EventName': 'JUNK YARD', 'EquipID': 5, 'EquipmentName': '2 DOT LOG', 'EquipmentCategory': 'LOG', 'EquipNum': 3, 'EquipWt': 220, 'AppRatio': 1, 'AppRatioWT': 660, 'Distance_KM': 13.9, 'Time_STD': 600},
        {'EventEquipID': 79, 'EventID': 22, 'EventName': 'JUNK YARD', 'EquipID': 4, 'EquipmentName': '1 DOT LOG', 'EquipmentCategory': 'LOG', 'EquipNum': 2, 'EquipWt': 140, 'AppRatio': 1, 'AppRatioWT': 280, 'Distance_KM': 13.9, 'Time_STD': 600},
        {'EventEquipID': 80, 'EventID': 22, 'EventName': 'JUNK YARD', 'EquipID': 24, 'EquipmentName': 'WATER DRUM', 'EquipmentCategory': 'WATER DRUM', 'EquipNum': 5, 'EquipWt': 265, 'AppRatio': 1, 'AppRatioWT': 1325, 'Distance_KM': 13.9, 'Time_STD': 600},
        {'EventEquipID': 81, 'EventID': 22, 'EventName': 'JUNK YARD', 'EquipID': 2, 'EquipmentName': 'AMMO CRATE', 'EquipmentCategory': 'AMMO CRATE', 'EquipNum': 1, 'EquipWt': 100, 'AppRatio': 1, 'AppRatioWT': 100, 'Distance_KM': 13.9, 'Time_STD': 600},
        {'EventEquipID': 82, 'EventID': 22, 'EventName': 'JUNK YARD', 'EquipID': 1, 'EquipmentName': 'AMMO CAN', 'EquipmentCategory': 'WATER CAN', 'EquipNum': 1, 'EquipWt': 120, 'AppRatio': 1, 'AppRatioWT': 120, 'Distance_KM': 13.9, 'Time_STD': 600},
        {'EventEquipID': 83, 'EventID': 22, 'EventName': 'JUNK YARD', 'EquipID': 23, 'EquipmentName': 'WATER CAN', 'EquipmentCategory': 'WATER CAN', 'EquipNum': 1, 'EquipWt': 45, 'AppRatio': 1, 'AppRatioWT': 45, 'Distance_KM': 13.9, 'Time_STD': 600}
    ]
    
    return pd.DataFrame(data)

def create_default_roster():
    """Create default roster data with 10 teams of 18 participants"""
    roster_data = []
    candidate_types = ['OF', 'ADE']
    
    for team_num in range(1, 11):
        for member_num in range(1, 19):
            roster_number = 1000 + (team_num - 1) * 18 + member_num
            
            # Alternate OF and ADE types
            candidate_type = candidate_types[member_num % 2]
            
            # Create a unique name
            if candidate_type == 'OF':
                prefix = "Officer"
            else:
                prefix = "Candidate"
            
            name = f"{prefix} {team_num}-{member_num}"
            
            roster_data.append({
                'Candidate_Name': name,
                'Roster_Number': roster_number,
                'Candidate_Type': candidate_type,
                'Initial_Team': f'Team {team_num}'
            })
    
    return pd.DataFrame(roster_data)

def time_str_to_minutes(time_str):
    """
    Convert time string in format 'mm:ss' to minutes (float)
    Minutes can exceed 60
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
    Minutes can exceed 60
    """
    try:
        total_minutes = int(minutes)
        seconds = int((minutes - total_minutes) * 60)
        
        return f"{total_minutes:02d}:{seconds:02d}"
    except Exception as e:
        st.error(f"Error converting minutes to time string: {str(e)}")
        return "00:00"

def military_time_to_minutes(time_str):
    """
    Convert military time (HH:MM) to minutes since midnight
    
    Parameters:
    -----------
    time_str : str
        Time in military format (HH:MM)
        
    Returns:
    --------
    float
        Minutes since midnight
    """
    try:
        parts = time_str.split(':')
        if len(parts) != 2:
            raise ValueError("Time must be in format 'HH:MM'")
        
        hours = int(parts[0])
        minutes = int(parts[1])
        
import pandas as pd
import numpy as np

def reshuffle_teams(active_participants, team_difficulty_df, target_team_size=17):
    """
    Reshuffle participants into new teams for Days 3 and 4 with improved balancing
    
    Parameters:
    -----------
    active_participants : DataFrame
        Dataframe of participants who haven't dropped
    team_difficulty_df : DataFrame
        Difficulty scores for each team from Days 1 and 2
    target_team_size : int
        Target number of participants per team
    
    Returns:
    --------
    DataFrame
        New team assignments
    """
    try:
        # Calculate the number of teams needed
        num_participants = len(active_participants)
        num_teams = max(1, round(num_participants / target_team_size))
        
        # Assign performance scores based on team difficulty data
        if team_difficulty_df is not None and 'Team' in team_difficulty_df.columns:
            # Create a mapping of team to difficulty score
            team_difficulty_map = dict(zip(
                team_difficulty_df['Team'], 
                team_difficulty_df['Difficulty_Score']
            ))
            
            # Assign performance score to each participant based on their original team
            active_participants['Performance_Score'] = active_participants['Initial_Team'].map(
                team_difficulty_map
            ).fillna(team_difficulty_df['Difficulty_Score'].mean())
        else:
            # If no team-specific data, assign random performance scores
            active_participants['Performance_Score'] = np.random.uniform(0.8, 1.2, size=len(active_participants))
        
        # Separate participants by type
        of_participants = active_participants[active_participants['Candidate_Type'] == 'OF'].copy()
        ade_participants = active_participants[active_participants['Candidate_Type'] == 'ADE'].copy()
        
        # Sort participants by performance score (alternating high/low to create balance)
        of_participants = of_participants.sort_values('Performance_Score', ascending=False)
        ade_participants = ade_participants.sort_values('Performance_Score', ascending=False)
        
        # Create zigzag pattern for distribution (to balance teams)
        of_zigzag = []
        for i in range(0, len(of_participants), 2*num_teams):
            chunk = of_participants.iloc[i:i+2*num_teams]
            if len(chunk) <= num_teams:
                of_zigzag.extend(chunk.to_dict('records'))
            else:
                first_half = chunk.iloc[:num_teams]
                second_half = chunk.iloc[num_teams:2*num_teams].iloc[::-1]  # Reverse second half
                of_zigzag.extend(first_half.to_dict('records'))
                of_zigzag.extend(second_half.to_dict('records'))
        
        ade_zigzag = []
        for i in range(0, len(ade_participants), 2*num_teams):
            chunk = ade_participants.iloc[i:i+2*num_teams]
            if len(chunk) <= num_teams:
                ade_zigzag.extend(chunk.to_dict('records'))
            else:
                first_half = chunk.iloc[:num_teams]
                second_half = chunk.iloc[num_teams:2*num_teams].iloc[::-1]  # Reverse second half
                ade_zigzag.extend(first_half.to_dict('records'))
                ade_zigzag.extend(second_half.to_dict('records'))
        
        # Assign new team numbers with a distribution that balances performance
        new_team_assignments = []
        
        # Distribute participants to teams
        for i, participant in enumerate(of_zigzag):
            team_num = i % num_teams + 1
            participant['New_Team'] = f'Team {team_num}'
            new_team_assignments.append(participant)
        
        for i, participant in enumerate(ade_zigzag):
            team_num = i % num_teams + 1
            participant['New_Team'] = f'Team {team_num}'
            new_team_assignments.append(participant)
        
        # Create DataFrame from assignments
        reshuffled_teams = pd.DataFrame(new_team_assignments)
        
        # Calculate and add team performance metrics
        team_stats = reshuffled_teams.groupby('New_Team')['Performance_Score'].agg(['mean', 'std']).reset_index()
        team_stats.columns = ['New_Team', 'Avg_Performance', 'Std_Performance']
        
        print(f"Team balance check - Std Dev of Avg Performances: {team_stats['Avg_Performance'].std():.4f}")
        
        return reshuffled_teams
    except Exception as e:
        print(f"Error reshuffling teams: {str(e)}")
        return pd.DataFrame()