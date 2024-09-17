from bs4 import BeautifulSoup
import requests as rq
import pandas as pd
import re
from datetime import datetime

# Enter the URL of the event page you want to scrape.
event_url = "https://www.vlr.gg/event/matches/2097/valorant-champions-2024/?series_id=all"
match_type = event_url.split("=")[1]
event = event_url.split("/")[-2] + "-" + match_type

# Retrieving and parsing whole page HTML data from the URL
html_text = rq.get(event_url).text
bs = BeautifulSoup(html_text, "lxml")

# Creating data titles and functions to extract t/ct data
def has_map_data(tag):
    return tag.has_attr('class') and 'vm-stats-game' in tag['class']

def has_tside_stat(tag):
    return tag.has_attr('class') and 'mod-t' in tag['class']

def has_ovrside_stat(tag):
    return tag.has_attr('class') and 'mod-both' in tag['class']

def has_ctside_stat(tag):
    return tag.has_attr('class') and 'mod-ct' in tag['class']

def has_otside_stat(tag):
    return tag.has_attr('class') and 'mod-ot' in tag['class']

def has_header_info(tag):
    return tag.has_attr('class') and 'match-header' in tag['class']

def has_odds_info(tag):
    return tag.has_attr('class') and 'match-bet-item' in tag['class']

def has_date(tag):
    return tag.has_attr('class') and 'moment-tz-convert' in tag['class']

titles_t = [
    "rating_tside", "acs_tside", "kills_tside", "deaths_tside", "assists_tside",
    "kd_diff_tside", "kast_tside", "adr_tside", "hs_perc_tside", "fb_tside",
    "fd_tside", "fk_diff_tside"
]

titles_ct = [
    "rating_ctside", "acs_ctside", "kills_ctside", "deaths_ctside", "assists_ctside",
    "kd_diff_ctside", "kast_ctside", "adr_ctside", "hs_perc_ctside", "fb_ctside",
    "fd_ctside", "fk_diff_ctside"
]

titles_ovr = [
    "rating_ovr", "acs_ovr", "kills_ovr", "deaths_ovr", "assists_ovr",
    "kd_diff_ovr", "kast_ovr", "adr_ovr", "hs_perc_ovr", "fb_ovr",
    "fd_ovr", "fk_diff_ovr"
]

all_players_data = []
match_odds = {}  # Dictionary to store odds for each match

# Retrieving individual match URLs from initial URL
match_blocks = bs.find_all('a', class_=lambda c: c and all(cls in c.split() for cls in ['wf-module-item', 'match-item']))
matchlinks_array = ["https://www.vlr.gg" + match_block.get("href") for match_block in match_blocks]

for match_link in matchlinks_array:
    match_html_text = rq.get(match_link).text
    match_bs = BeautifulSoup(match_html_text, "lxml")

    # Date parsing
    all_header_info = match_bs.find_all(has_header_info)
    for date_info in all_header_info:
        dates = date_info.find_all(has_date)
    if len(dates) >= 2:
        raw_date = " ".join(" ".join(date_tag.stripped_strings) for date_tag in dates)
        date_time_match = re.search(r"(\w+), (\w+) (\d+)(?:st|nd|rd|th) (\d+:\d+) (AM|PM) CDT", raw_date)

        if date_time_match:
            month_str = date_time_match.group(2)
            day = date_time_match.group(3)
            time = date_time_match.group(4)
            period = date_time_match.group(5)
            month = datetime.strptime(month_str, "%B").month
            formatted_date = f"{month}_{day}_{time} {period}"
            time_obj = datetime.strptime(formatted_date, "%m_%d_%I:%M %p")
            final_date = time_obj.strftime("%m_%d_%H_%M")

    # Odds calculation
    all_odds_info = match_bs.find_all(has_odds_info)
    int_return = None
    for odds_info in all_odds_info:
        odds = odds_info.find_all('span', class_='match-bet-item-odds')
        if len(odds) > 1:
            raw_return = odds[1].text
            int_return = int(raw_return.replace("$", ""))/100
            break

    if int_return is not None:
        return_vig = int_return
        if return_vig > 2:
            winning_odds = 100 * (return_vig - 1)
        else:
            winning_odds = -100 / (return_vig - 1)
        if winning_odds > 0:
            perc_win = 100 / (100 + winning_odds)
        else:
            perc_win = -winning_odds / (100 - winning_odds)
        perc_lose = 1.08 - perc_win
        if (perc_lose * 100) / (100 * (1 - perc_lose)) > 1:
            losing_odds = -(100 * perc_lose) / (1 - perc_lose)
        else:
            losing_odds = (100 - perc_lose) / perc_lose
        match_odds[final_date] = {'winning_odds': winning_odds, 'losing_odds': losing_odds}
    else:
        print(f"No valid odds found for match on {final_date}")

    # Map data scraping
    all_map_data = match_bs.find_all(has_map_data)
    for map_data in all_map_data:
        game_id = map_data.get('data-game-id')
        if game_id != "all":
            stats_header = map_data.find('div', class_='vm-stats-game-header')
            if stats_header:
                team_left = stats_header.find('div', class_='team')
                team_right = stats_header.find('div', class_='team mod-right')

                t_score_left = team_left.find(has_tside_stat).text if team_left and team_left.find(has_tside_stat) else None
                ct_score_left = team_left.find(has_ctside_stat).text if team_left and team_left.find(has_ctside_stat) else None
                t_score_right = team_right.find(has_tside_stat).text if team_right and team_right.find(has_tside_stat) else None
                ct_score_right = team_right.find(has_ctside_stat).text if team_right and team_right.find(has_ctside_stat) else None

                ot_score_left = int(team_left.find(has_otside_stat).text) if team_left and team_left.find(has_otside_stat) else 0
                ot_score_right = int(team_right.find(has_otside_stat).text) if team_right and team_right.find(has_otside_stat) else 0

                map_name_elem = map_data.find('div', class_='map')
                if map_name_elem:
                    map_name = map_name_elem.text.strip()
                    map = re.split(r'\s{2,}', map_name)[0].strip()

            stats_rows = map_data.find_all('tr')
            for row in stats_rows[1:]:  # Skip the header row
                player_data = row.find('td', class_='mod-player')
                if player_data:
                    player_team_text = player_data.text.strip()
                    player = re.split(r'\s{2,}', player_team_text)[0].strip()
                    team = player_team_text.split()[-1].strip()

                    agent_td = row.find('td', class_='mod-agents')
                    agent = agent_td.find('img').get('alt', 'Unknown').strip() if agent_td and agent_td.find('img') else 'Unknown'

                    ovr_stats = row.find_all(has_ovrside_stat)
                    ovr_numbers = [re.sub(r'[^\d\.]', '', stat.get_text()) for stat in ovr_stats]
                    ovr_numbers = [float(num) if re.match(r'^\d+\.?\d*$', num) else 0 for num in ovr_numbers]
                    ovr_data = dict(zip(titles_ovr, ovr_numbers))

                    t_stats = row.find_all(has_tside_stat)
                    t_numbers = [re.sub(r'[^\d\.]', '', stat.get_text()) for stat in t_stats]
                    t_numbers = [float(num) if re.match(r'^\d+\.?\d*$', num) else 0 for num in t_numbers]
                    t_data = dict(zip(titles_t, t_numbers))

                    ct_stats = row.find_all(has_ctside_stat)
                    ct_numbers = [re.sub(r'[^\d\.]', '', stat.get_text()) for stat in ct_stats]
                    ct_numbers = [float(num) if re.match(r'^\d+\.?\d*$', num) else 0 for num in ct_numbers]
                    ct_data = dict(zip(titles_ct, ct_numbers))

                    combined_data = {**ovr_data, **t_data, **ct_data}
                    combined_data.update({
                        'date': final_date,
                        'player': player,
                        'team': team,
                        'map': map,
                        'game_id': game_id,
                        'agent': agent,
                        't_score_left': t_score_left,
                        'ct_score_left': ct_score_left,
                        't_score_right': t_score_right,
                        'ct_score_right': ct_score_right,
                        'ot_score_left': ot_score_left,
                        'ot_score_right': ot_score_right
                    })

                    all_players_data.append(combined_data)

df = pd.DataFrame(all_players_data)

def assign_scores(group):
    group['t_score'] = group['t_score_left'].iloc[0]
    group['ct_score'] = group['ct_score_left'].iloc[0]
    group['ot_score'] = group['ot_score_left'].iloc[0]
    group.loc[group.index[-5:], 't_score'] = group['t_score_right'].iloc[0]
    group.loc[group.index[-5:], 'ct_score'] = group['ct_score_right'].iloc[0]
    group.loc[group.index[-5:], 'ot_score'] = group['ot_score_right'].iloc[0]
    return group

finaldf = df.groupby('game_id', group_keys=False).apply(assign_scores)

def calculate_win(group):
    group['ot_score_left'] = group['ot_score_left'].fillna(0)
    group['ot_score_right'] = group['ot_score_right'].fillna(0)

    total_score_left = float(group['t_score_left'].iloc[0]) + float(group['ct_score_left'].iloc[0]) + float(group['ot_score_left'].iloc[0])
    total_score_right = float(group['t_score_right'].iloc[0]) + float(group['ct_score_right'].iloc[0]) + float(group['ot_score_right'].iloc[0])

    win_left = 1 if total_score_left > total_score_right else 0
    win_right = 1 if total_score_left < total_score_right else 0

    left_team = group['team'].iloc[0]
    right_team = group['team'].iloc[-1]

    group['win'] = group['team'].apply(lambda t: win_left if t == left_team else win_right)
    return group

finaldf = finaldf.groupby('game_id', group_keys=False).apply(calculate_win)

finaldf = finaldf.drop(['t_score_left', 'ct_score_left', 't_score_right', 'ct_score_right', 'ot_score_right', 'ot_score_left'], axis=1)

# Get match results
match_results = finaldf.groupby(['date', 'team'])['win'].sum().unstack()
match_results['team_win'] = match_results.sum(axis=1)

# Get the list of team names (excluding 'team_win' column)
teams = [col for col in match_results.columns if col != 'team_win']

# Assign odds to each team
for date in match_results.index:
    odds = match_odds.get(date, {'winning_odds': 0, 'losing_odds': 0})
    max_team_win = match_results.loc[date, teams].max()
    for team in teams:
        if match_results.loc[date, team] == max_team_win:
            match_results.loc[date, f"{team}_odds"] = odds['winning_odds']
        else:
            match_results.loc[date, f"{team}_odds"] = odds['losing_odds']

# Reset index to turn 'date' back into a column
match_results = match_results.reset_index()

# Melt the DataFrame to long format
teams = [col for col in match_results.columns if col not in ['date', 'team_win'] and not col.endswith('_odds')]
match_results_melted = match_results.melt(
    id_vars=['date', 'team_win'],
    value_vars=teams,
    var_name='team',
    value_name='team_win_score'
)

# Collect odds columns
odds_columns = [col for col in match_results.columns if col.endswith('_odds')]

# Melt odds columns
odds_data = match_results[['date'] + odds_columns]
odds_melted = odds_data.melt(
    id_vars=['date'],
    value_vars=odds_columns,
    var_name='team_odds',
    value_name='match_odds'
)

# Extract team name from odds columns
odds_melted['team'] = odds_melted['team_odds'].str.replace('_odds', '', regex=False)
odds_melted = odds_melted.drop('team_odds', axis=1)

# Merge odds with match results
match_results_melted = match_results_melted.merge(odds_melted, on=['date', 'team'], how='left')

# Create 'match_win' column
# For each date, assign 'match_win' = 1 to team with higher 'team_win_score', 0 to the other team
max_team_win_score = match_results_melted.groupby('date')['team_win_score'].transform('max')
match_results_melted['match_win'] = (match_results_melted['team_win_score'] == max_team_win_score).astype(int)

# Merge the odds and 'match_win' into the final DataFrame
finaldf = finaldf.merge(
    match_results_melted[['date', 'team', 'match_win', 'match_odds']],
    on=['date', 'team'],
    how='left'
)

# Drop 'team_win' and 'team_win_score' if they exist
finaldf = finaldf.drop(columns=['team_win_score'], errors='ignore')

# Reorder columns, replacing 'team_win' with 'match_win'
column_order = ['date', 'game_id', 'map', 'win', 'match_win', 'team', 'player', 'agent', 't_score', 'ct_score', 'ot_score', 'match_odds'] + \
               [col for col in finaldf.columns if col not in ['date', 'player', 'team', 'agent', 'map', 'game_id', 't_score', 'ct_score', 'win', 'match_win', 'ot_score', 'match_odds']]
finaldf = finaldf[column_order]

print(finaldf.head())  # Display the first few rows of the final DataFrame

# Enter desired file location inbetween "" and then remove the ""
output_path = r'C:\Users""{event}.csv'.format(event=event)
finaldf.to_csv(output_path, index=False)
