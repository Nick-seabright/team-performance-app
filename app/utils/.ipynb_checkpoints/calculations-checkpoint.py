import numpy as np
import pandas as pd
from utils.data_processing import time_str_to_minutes, minutes_to_time_str

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
                              distance, time_actual, drops, drop_data, day, event_number, event_name):
    """
    Calculate the actual difficulty score, accounting for participants who dropped
    """
    try:
        if initial_participants <= 0 or time_actual <= 0:
            return 0
        
        # If no drops, the calculation is simple
        if drops == 0:
            difficulty = temp_multiplier * (total_weight / initial_participants) * (distance / time_actual)
            return difficulty
        
        # Filter drop data for this event
        event_drops = drop_data[
            (drop_data['Day'] == day) & 
            (drop_data['Event_Number'] == event_number) &
            (drop_data['Event_Name'] == event_name)
        ]
        
        # If no drop data available for this event, use the provided drops count
        if event_drops.empty:
            effective_participants = initial_participants - (drops / 2)  # Approximate
            difficulty = temp_multiplier * (total_weight / effective_participants) * (distance / time_actual)
            return difficulty
        
        # For each drop, calculate the effective participants
        # This is a simplification - in a real app, you'd calculate the exact time spent with each participant count
        drop_times = [time_str_to_minutes(t) for t in event_drops['Drop_Time']]
        
        # Sort drop times
        drop_times.sort()
        
        # Calculate weighted average of participants
        segments = [0] + drop_times + [time_actual]
        participant_counts = list(range(initial_participants, initial_participants - len(drop_times) - 1, -1))
        
        weighted_participants = 0
        for i in range(len(segments) - 1):
            segment_duration = segments[i+1] - segments[i]
            weighted_participants += participant_counts[i] * segment_duration
        
        effective_participants = weighted_participants / time_actual
        
        # Calculate difficulty with effective participants
        difficulty = temp_multiplier * (total_weight / effective_participants) * (distance / time_actual)
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
        if past_performance is not None:
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