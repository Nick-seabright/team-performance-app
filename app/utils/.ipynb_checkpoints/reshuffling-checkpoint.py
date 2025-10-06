import pandas as pd
import numpy as np

def reshuffle_teams(active_participants, team_difficulty_df=None, target_team_size=17):
    """
    Reshuffle participants into new teams for Days 3 and 4 with balanced officer:enlisted ratio
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
        New team assignments with balanced officer:enlisted ratio across teams
    """
    try:
        # Calculate the number of teams needed
        num_participants = len(active_participants)
        num_teams = max(1, round(num_participants / target_team_size))
        
        # Categorize participants as officers or enlisted
        active_participants['Is_Officer'] = active_participants['Candidate_Type'].apply(
            lambda x: x in ['ADO', 'NGO']
        )
        
        # Separate participants by officer/enlisted category
        officers = active_participants[active_participants['Is_Officer']].copy()
        enlisted = active_participants[~active_participants['Is_Officer']].copy()
        
        # Further categorize by specific type for even distribution
        type_groups = {}
        for candidate_type in active_participants['Candidate_Type'].unique():
            type_groups[candidate_type] = active_participants[
                active_participants['Candidate_Type'] == candidate_type
            ].copy().sample(frac=1).reset_index(drop=True)  # Shuffle each type
        
        # Calculate overall officer:enlisted ratio
        total_officers = len(officers)
        total_enlisted = len(enlisted)
        overall_ratio = total_enlisted / total_officers if total_officers > 0 else float('inf')
        
        print(f"Overall Officer:Enlisted Ratio: 1:{overall_ratio:.2f}")
        print(f"Total Officers: {total_officers}, Total Enlisted: {total_enlisted}")
        
        # Initialize team assignments
        team_assignments = []
        
        # First, distribute officers evenly across teams
        for i, (_, officer) in enumerate(officers.iterrows()):
            team_num = i % num_teams + 1
            officer_dict = officer.to_dict()
            officer_dict['New_Team'] = f'Team {team_num}'
            team_assignments.append(officer_dict)
        
        # Next, distribute each type of enlisted to maintain overall balance
        for candidate_type, participants in type_groups.items():
            if candidate_type not in ['ADO', 'NGO']:  # Only process enlisted types
                for i, (_, participant) in enumerate(participants.iterrows()):
                    # Calculate current distribution to ensure balance
                    current_assignments = pd.DataFrame(team_assignments)
                    
                    if not current_assignments.empty and 'New_Team' in current_assignments.columns:
                        # Count officers and enlisted per team
                        team_counts = current_assignments.groupby('New_Team').apply(
                            lambda x: pd.Series({
                                'Officers': sum(x['Is_Officer']),
                                'Enlisted': sum(~x['Is_Officer'])
                            })
                        ).reset_index()
                        
                        # Find team with lowest enlisted-to-officer ratio
                        team_counts['Ratio'] = team_counts['Enlisted'] / team_counts['Officers'].replace(0, 0.1)
                        team_counts = team_counts.sort_values('Ratio')
                        
                        # Assign to team with lowest ratio to balance
                        best_team = team_counts.iloc[0]['New_Team']
                        participant_dict = participant.to_dict()
                        participant_dict['New_Team'] = best_team
                    else:
                        # If no assignments yet, distribute evenly
                        team_num = i % num_teams + 1
                        participant_dict = participant.to_dict()
                        participant_dict['New_Team'] = f'Team {team_num}'
                    
                    team_assignments.append(participant_dict)
        
        # Create DataFrame from assignments
        reshuffled_teams = pd.DataFrame(team_assignments)
        
        # Calculate and display team composition stats for verification
        if not reshuffled_teams.empty:
            team_stats = reshuffled_teams.groupby('New_Team').apply(
                lambda x: pd.Series({
                    'Officers': sum(x['Is_Officer']),
                    'Enlisted': sum(~x['Is_Officer']),
                    'Total': len(x)
                })
            ).reset_index()
            
            team_stats['Officer:Enlisted Ratio'] = team_stats['Enlisted'] / team_stats['Officers']
            
            print("\nTeam Composition Stats:")
            print(team_stats)
            
            # Calculate detailed type distribution
            type_distribution = reshuffled_teams.groupby(['New_Team', 'Candidate_Type']).size().unstack(fill_value=0).reset_index()
            print("\nDetailed Type Distribution:")
            print(type_distribution)
            
            # Calculate ratio standard deviation to measure balance
            ratio_std_dev = team_stats['Officer:Enlisted Ratio'].std()
            print(f"\nTeam Ratio Standard Deviation: {ratio_std_dev:.4f}")
        
        return reshuffled_teams
    except Exception as e:
        print(f"Error reshuffling teams: {str(e)}")
        return pd.DataFrame()