import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

def plot_difficulty_trends(event_records):
    """
    Plot difficulty score trends over the 4-day event
    
    Parameters:
    -----------
    event_records : DataFrame
        DataFrame containing event records with difficulty scores
    
    Returns:
    --------
    plotly.graph_objects.Figure
        Plotly figure showing difficulty trends
    """
    try:
        if event_records.empty:
            return go.Figure()
        
        # Calculate average difficulty by day
        daily_difficulty = event_records.groupby('Day')[
            ['Initial_Difficulty', 'Actual_Difficulty']
        ].mean().reset_index()
        
        # Create figure
        fig = px.line(
            daily_difficulty,
            x='Day',
            y=['Initial_Difficulty', 'Actual_Difficulty'],
            markers=True,
            title='Difficulty Score Trends Over 4 Days',
            labels={
                'value': 'Difficulty Score',
                'variable': 'Difficulty Type',
                'Day': 'Day'
            }
        )
        
        return fig
    except Exception as e:
        print(f"Error plotting difficulty trends: {str(e)}")
        return go.Figure()

def plot_team_difficulty_distribution(event_records, team_data, phase='Before Reshuffling'):
    """
    Plot distribution of difficulty scores by team
    
    Parameters:
    -----------
    event_records : DataFrame
        DataFrame containing event records with difficulty scores
    team_data : DataFrame
        DataFrame with team assignments
    phase : str
        'Before Reshuffling' or 'After Reshuffling'
    
    Returns:
    --------
    plotly.graph_objects.Figure
        Plotly figure showing team difficulty distributions
    """
    try:
        if event_records.empty or team_data.empty:
            return go.Figure()
        
        # This is a simplified approach - in a real app, you'd track which teams participated in each event
        # For this demo, we'll create a synthetic joined dataset
        
        if phase == 'Before Reshuffling':
            days = [1, 2]
            team_column = 'Initial_Team'
        else:
            days = [3, 4]
            team_column = 'New_Team'
        
        # Filter event records for the relevant days
        filtered_events = event_records[event_records['Day'].isin(days)]
        
        # Create dummy team assignments for visualization
        teams = team_data[team_column].unique()
        
        # Create figure
        fig = px.box(
            filtered_events,
            x='Day',
            y='Actual_Difficulty',
            color='Event_Number',
            title=f'Difficulty Score Distribution ({phase})',
            labels={
                'Actual_Difficulty': 'Difficulty Score',
                'Day': 'Day',
                'Event_Number': 'Event Number'
            }
        )
        
        return fig
    except Exception as e:
        print(f"Error plotting team difficulty distribution: {str(e)}")
        return go.Figure()

def plot_final_difficulty_scores(event_records, team_data):
    """
    Plot final difficulty scores grouped by team
    
    Parameters:
    -----------
    event_records : DataFrame
        DataFrame containing event records with difficulty scores
    team_data : DataFrame
        DataFrame with team assignments (both original and reshuffled)
    
    Returns:
    --------
    plotly.graph_objects.Figure
        Plotly figure showing final difficulty scores
    """
    try:
        if event_records.empty or team_data.empty:
            return go.Figure()
        
        # Calculate average difficulty by day
        daily_difficulty = event_records.groupby('Day')['Actual_Difficulty'].mean().reset_index()
        
        # Create figure
        fig = px.bar(
            daily_difficulty,
            x='Day',
            y='Actual_Difficulty',
            title='Final Average Difficulty Scores by Day',
            labels={
                'Actual_Difficulty': 'Average Difficulty Score',
                'Day': 'Day'
            }
        )
        
        # Add a line for the overall average
        overall_avg = daily_difficulty['Actual_Difficulty'].mean()
        fig.add_hline(
            y=overall_avg,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Overall Avg: {overall_avg:.2f}",
            annotation_position="top right"
        )
        
        return fig
    except Exception as e:
        print(f"Error plotting final difficulty scores: {str(e)}")
        return go.Figure()