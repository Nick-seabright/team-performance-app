import pandas as pd
import numpy as np

def reshuffle_teams(active_participants, team_difficulty_df=None, target_team_size=17):
    """
    Reshuffle participants into new teams for Days 3 and 4 with balanced team composition
    Parameters:
    -----------
    active_participants : DataFrame
        Dataframe of participants who haven't dropped
    team_difficulty_df : DataFrame, optional
        Difficulty scores for each team from Days 1 and 2 (not used in this version)
    target_team_size : int
        Target number of participants per team
    Returns:
    --------
    DataFrame
        New team assignments with balanced OF:ADE ratio across teams
    """
    try:
        # Calculate the number of teams needed
        num_participants = len(active_participants)
        num_teams = max(1, round(num_participants / target_team_size))
        
        # Separate participants by type
        of_participants = active_participants[active_participants['Candidate_Type'] == 'OF'].copy()
        ade_participants = active_participants[active_participants['Candidate_Type'] == 'ADE'].copy()
        
        # Shuffle both groups to randomize
        of_participants = of_participants.sample(frac=1).reset_index(drop=True)
        ade_participants = ade_participants.sample(frac=1).reset_index(drop=True)
        
        # Calculate target ratio to maintain
        total_of = len(of_participants)
        total_ade = len(ade_participants)
        
        # Distribute participants evenly across teams
        team_assignments = []
        
        # Distribute OF participants
        for i, participant in enumerate(of_participants.iterrows()):
            team_num = i % num_teams + 1
            participant_dict = participant[1].to_dict()
            participant_dict['New_Team'] = f'Team {team_num}'
            team_assignments.append(participant_dict)
        
        # Distribute ADE participants
        for i, participant in enumerate(ade_participants.iterrows()):
            team_num = i % num_teams + 1
            participant_dict = participant[1].to_dict()
            participant_dict['New_Team'] = f'Team {team_num}'
            team_assignments.append(participant_dict)
        
        # Create DataFrame from assignments
        reshuffled_teams = pd.DataFrame(team_assignments)
        
        # Calculate and display team composition stats for verification
        team_stats = reshuffled_teams.groupby(['New_Team', 'Candidate_Type']).size().unstack().reset_index()
        if 'OF' not in team_stats.columns:
            team_stats['OF'] = 0
        if 'ADE' not in team_stats.columns:
            team_stats['ADE'] = 0
        
        team_stats['Total'] = team_stats['OF'] + team_stats['ADE']
        team_stats['OF_Ratio'] = team_stats['OF'] / team_stats['Total']
        
        print("Team Composition Stats:")
        print(team_stats)
        
        # Calculate overall stats
        overall_of_ratio = total_of / (total_of + total_ade)
        of_ratio_std_dev = team_stats['OF_Ratio'].std()
        
        print(f"Overall OF Ratio: {overall_of_ratio:.2f}")
        print(f"Team OF Ratio Standard Deviation: {of_ratio_std_dev:.4f}")
        
        return reshuffled_teams
    except Exception as e:
        print(f"Error reshuffling teams: {str(e)}")
        return pd.DataFrame()