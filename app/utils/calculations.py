import numpy as np
import pandas as pd
from utils.data_processing import time_str_to_minutes, minutes_to_time_str, military_time_to_minutes

def calculate_initial_difficulty(temp_multiplier, total_weight, participants, distance, time_limit):
    """
    Calculate the initial difficulty score
    
    Difficulty Initial = Temperature Multiplier × (Total Weight / Initial Participants) × (Distance / Time Limit)
    """
    try:
        if participants <= 0 or time_limit <= 0:
            return 0
        
        difficulty = temp_multiplier * (total_weight / participants) * (distance / time_limit)
        return difficulty
    except Exception as e:
        print(f"Error calculating initial difficulty: {str(e)}")
        return 0

def calculate_actual_difficulty(temp_multiplier, total_weight, initial_participants, 
                              distance, time_actual_min, drops, 
                              drop_data, day, event_number, event_name,
                              start_time=None):
    """
    Calculate the actual difficulty score, accounting for participants who dropped
    
    Parameters:
    -----------
    temp_multiplier : float
        Temperature multiplier based on heat category
    total_weight : float
        Total weight of equipment (lbs)
    initial_participants : int
        Initial number of participants
    distance : float
        Distance in kilometers
    time_actual_min : float
        Actual time in minutes
    drops : int
        Number of drops (if not using detailed drop data)
    drop_data : DataFrame
        Detailed drop data including drop times
    day : int
        Day of the event
    event_number : int
        Event number
    event_name : str
        Name of the event
    start_time : str, optional
        Start time of the event in military format (HH:MM)
        
    Returns:
    --------
    float
        Actual difficulty score
    """
    try:
        if initial_participants <= 0 or time_actual_min <= 0:
            return 0
        
        # If no drops, the calculation is simple
        if drops == 0:
            difficulty = temp_multiplier * (total_weight / initial_participants) * (distance / time_actual_min)
            return difficulty
        
        # Filter drop data for this event
        if 'Team' in drop_data.columns:
            # Filter by team and event
            event_drops = drop_data[
                (drop_data['Day'] == day) & 
                (drop_data['Event_Number'] == event_number) &
                (drop_data['Event_Name'] == event_name)
            ]
        else:
            # Filter by event only
            event_drops = drop_data[
                (drop_data['Day'] == day) & 
                (drop_data['Event_Number'] == event_number) &
                (drop_data['Event_Name'] == event_name)
            ]
        
        # If no drop data available for this event, use the provided drops count
        if event_drops.empty:
            effective_participants = initial_participants - (drops / 2)  # Approximate
            difficulty = temp_multiplier * (total_weight / effective_participants) * (distance / time_actual_min)
            return difficulty
        
        # For each drop, calculate the effective participants
        if start_time is None:
            # If no start time provided, approximate using drop times relative to duration
            drop_times_relative = [0.5 * time_actual_min] * len(event_drops)  # Assume drops at midpoint
            
            # Calculate weighted average of participants
            segments = [0] + drop_times_relative + [time_actual_min]
            participant_counts = list(range(initial_participants, initial_participants - len(drop_times_relative) - 1, -1))
            
        else:
            # If start time provided, calculate minutes from start for each drop
            start_minutes = military_time_to_minutes(start_time)
            
            drop_times_relative = []
            for drop_time in event_drops['Drop_Time']:
                drop_minutes = military_time_to_minutes(drop_time)
                # Handle case where drop time is next day
                if drop_minutes < start_minutes:
                    drop_minutes += 24 * 60  # Add a day in minutes
                
                minutes_from_start = drop_minutes - start_minutes
                drop_times_relative.append(minutes_from_start)
            
            # Sort drop times
            drop_times_relative.sort()
            
            # Calculate weighted average of participants
            segments = [0] + drop_times_relative + [time_actual_min]
            participant_counts = list(range(initial_participants, initial_participants - len(drop_times_relative) - 1, -1))
        
        weighted_participants = 0
        for i in range(len(segments) - 1):
            segment_duration = segments[i+1] - segments[i]
            weighted_participants += participant_counts[i] * segment_duration
        
        effective_participants = weighted_participants / time_actual_min
        
        # Calculate difficulty with effective participants
        difficulty = temp_multiplier * (total_weight / effective_participants) * (distance / time_actual_min)
        return difficulty
    except Exception as e:
        print(f"Error calculating actual difficulty: {str(e)}")
        return 0

def calculate_target_difficulty(avg_difficulty, target_multiplier):
    """
    Calculate target difficulty score for Days 3 and 4
    """
    return avg_difficulty * target_multiplier

def adjust_equipment_weight(target_score, temp_multiplier, distance, time_limit, participants):
    """
    Calculate new equipment weight to reach target difficulty score
    
    New Weight = (Target Score / (Temp Multiplier × (Current Distance / Time Limit) × (1 / Participants))) × Participants
    """
    try:
        if temp_multiplier <= 0 or distance <= 0 or time_limit <= 0 or participants <= 0:
            return 0
        
        new_weight = (target_score / (temp_multiplier * (distance / time_limit) * (1 / participants))) * participants
        return max(0, new_weight)  # Ensure non-negative weight
    except Exception as e:
        print(f"Error adjusting equipment weight: {str(e)}")
        return 0

def adjust_distance(target_score, temp_multiplier, weight, time_limit, participants):
    """
    Calculate new distance to reach target difficulty score
    
    New Distance = (Target Score / (Temp Multiplier × (Current Weight / Participants) × (1 / Time Limit))) × Time Limit
    """
    try:
        if temp_multiplier <= 0 or weight <= 0 or time_limit <= 0 or participants <= 0:
            return 0
        
        new_distance = (target_score / (temp_multiplier * (weight / participants) * (1 / time_limit))) * time_limit
        return max(0, new_distance)  # Ensure non-negative distance
    except Exception as e:
        print(f"Error adjusting distance: {str(e)}")
        return 0

def predict_team_success(team_composition, event_difficulty, past_performance=None):
    """
    Predict team success rate for an event based on team composition and event difficulty
    
    Parameters:
    -----------
    team_composition : DataFrame
        DataFrame containing team member details
    event_difficulty : float
        Difficulty score of the event
    past_performance : DataFrame, optional
        Past performance data for team members
    
    Returns:
    --------
    float
        Predicted success rate (0-1)
    """
    try:
        # Basic model: success rate decreases as difficulty increases
        # and increases with more experienced team members
        
        # Count team members by type
        of_count = sum(team_composition['Candidate_Type'] == 'OF')
        ade_count = sum(team_composition['Candidate_Type'] == 'ADE')
        
        # Calculate a team strength score
        # This is a simplistic model - in a real app, you'd use more sophisticated ML
        of_strength = of_count * 1.0  # OF members contribute base strength
        ade_strength = ade_count * 0.8  # ADE members contribute slightly less
        
        total_strength = of_strength + ade_strength
        
        # If past performance data is available, use it to adjust strength
        if past_performance is not None and not past_performance.empty:
            performance_boost = past_performance['Actual_Difficulty'].mean() / 10
            total_strength *= (1 + performance_boost)
        
        # Calculate success rate: strength / (strength + difficulty)
        success_rate = total_strength / (total_strength + event_difficulty)
        
        # Clamp between 0.3 and 0.95
        success_rate = max(0.3, min(0.95, success_rate))
        
        return success_rate
    except Exception as e:
        print(f"Error predicting team success: {str(e)}")
        return 0.5