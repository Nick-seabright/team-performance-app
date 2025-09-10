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