import pandas as pd
import numpy as np

def reshuffle_teams(active_participants, team_difficulty_scores, target_team_size=17):
    """
    Reshuffle participants into new teams for Days 3 and 4 with improved balancing
    
    This algorithm:
    1. Calculates performance scores for each participant based on their original team
    2. Sorts participants by candidate type and performance
    3. Distributes participants to create balanced teams
    """
    try:
        # Calculate the number of teams needed
        num_participants = len(active_participants)
        num_teams = max(1, round(num_participants / target_team_size))
        
        # Get average difficulty scores by team
        if 'Initial_Team' in active_participants.columns:
            # Join difficulty data with participants
            # This is a simplified approach - in a real app, you'd track individual performance
            team_avg_difficulty = team_difficulty_scores.groupby('Day')['Actual_Difficulty'].mean().reset_index()
            
            # Create a performance score for each participant based on their original team
            # Higher scores mean more difficult events completed
            active_participants['Performance_Score'] = active_participants['Initial_Team'].apply(
                lambda x: team_avg_difficulty['Actual_Difficulty'].mean()  # Placeholder logic
            )
        else:
            # If no team data available, use random performance scores
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