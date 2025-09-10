# Team Performance Management and Analysis App

This Streamlit application helps manage and analyze team performance during a 4-day event. It provides tools for data management, event recording, team reshuffling, difficulty adjustment, and visualization.

## Features

- **Data Management**: Upload and manage roster, equipment, and events data
- **Event Recording**: Record event data and calculate difficulty scores
- **Drop Management**: Track participant drops during events
- **Team Reshuffling**: Automatically reassign participants to new teams after Day 2
- **Difficulty Adjustment**: Calculate and adjust event parameters for Days 3 and 4
- **Performance Analysis**: Calculate and visualize final difficulty scores
- **Predictive Analytics**: Predict team success rates for upcoming events

## Installation and Setup

### Local Development

1. Clone this repository:
   ```
   git clone https://github.com/Nick-seabright/team-performance-app.git
   cd team-performance-app
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Run the Streamlit app:
   ```
   streamlit run app/main.py
   ```

### Deploying to Streamlit Cloud

1. Fork this repository to your GitHub account
2. Sign up for [Streamlit Cloud](https://streamlit.io/cloud)
3. Create a new app and connect it to your forked repository
4. Set the main file path to `app/main.py`
5. Deploy the app

## Usage Guide

### 1. Data Upload

Start by uploading your roster, equipment, and events data. You can use the provided sample CSV files or connect to a SQL database.

### 2. Event Recording

Record event data for each day and event number. The app will automatically calculate:
- Initial Difficulty Score = Temperature Multiplier × (Total Weight / Initial Participants) × (Distance / Time Limit)
- Actual Difficulty Score (adjusts for participant drops)

### 3. Drop Management

Record participant drops as they occur, including:
- Participant Name
- Roster Number
- Event Name
- Drop Time
- Day and Event Number

### 4. Team Reshuffling

After Day 2, use the team reshuffling feature to:
- Create new balanced teams for Days 3 and 4
- Maintain the same OF:ADE ratios
- Balance team performance based on Days 1-2 difficulty scores

### 5. Difficulty Adjustment

Adjust event parameters for Days 3-4:
- Calculate target difficulty scores
- Adjust equipment weight, distance, or both
- Balance challenge levels based on team performance

### 6. Final Scores

View and analyze final difficulty scores:
- Team scores for all 4 days
- Comparison of team performance
- Overall event difficulty analysis

### 7. Visualizations

Visualize team performance data:
- Difficulty score trends over 4 days
- Team reshuffling and difficulty distributions
- Final difficulty scores by team
- Drop analysis

### 8. Predictive Analytics

Predict team success rates for upcoming events:
- Select a team and event to analyze
- View predicted success rate
- Get recommendations for adjustments

## Data Formats

### Roster Data
- Candidate_Name: Name of the participant
- Roster_Number: Unique identifier
- Candidate_Type: OF or ADE
- Initial_Team: Initial team assignment (Team 1, Team 2, etc.)

### Equipment Data
- Equipment_Name: Name of the equipment
- Equipment_Weight: Weight in pounds

### Events Data
- Event_Name: Name of the event
- Day: 1, 2, 3, or 4
- Event_Number: 1, 2, or 3
- Equipment_Name: Name of the equipment used
- Equipment_Weight: Weight in pounds
- Number_of_Equipment: Quantity of equipment
- Time_Limit: Time limit in mm:ss format
- Initial_Participants: Number of initial participants
- Distance: Distance in kilometers

## Calculations

### Difficulty Score Formulas

- **Initial Difficulty**: Temperature Multiplier × (Total Weight / Initial Participants) × (Distance / Time Limit)
- **Actual Difficulty**: Temperature Multiplier × (Total Weight / Effective Participants) × (Distance / Time Actual)
  - Effective Participants adjusts for drops during the event
  
- **Temperature Multiplier**:
  - Heat Categories 1-3: Multiplier = 1.0
  - Heat Category 4: Multiplier = 1.15
  - Heat Category 5: Multiplier = 1.3

### Adjustments for Days 3-4

- **Weight Adjustment**: New Weight = (Target Score / (Temp Multiplier × (Current Distance / Time Limit) × (1 / Participants))) × Participants
- **Distance Adjustment**: New Distance = (Target Score / (Temp Multiplier × (Current Weight / Participants) × (1 / Time Limit))) × Time Limit

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.