from bs4 import BeautifulSoup
import requests as rq
import pandas as pd
import re

# Enter the URL of the event page you want to scrape.
event_url = "https://www.vlr.gg/event/matches/2097/valorant-champions-2024/?series_id=4035&group=completed"
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

# Retrieving individual match URLs from initial URL
match_blocks = bs.find_all('a', class_=lambda c: c and all(cls in c.split() for cls in ['wf-module-item', 'match-item']))
matchlinks_array = ["https://www.vlr.gg" + match_block.get("href") for match_block in match_blocks]

for match_link in matchlinks_array:
    match_html_text = rq.get(match_link).text
    match_bs = BeautifulSoup(match_html_text, "lxml")

    all_map_data = match_bs.find_all(has_map_data)

    for map_data in all_map_data:
        game_id = map_data.get('data-game-id')
        if game_id != "all":
            header = map_data.find('div', class_='vm-stats-game-header')
            if header:
                team_left = header.find('div', class_='team')
                team_right = header.find('div', class_='team mod-right')

                t_score_left = team_left.find(has_tside_stat).text if team_left and team_left.find(has_tside_stat) else None
                ct_score_left = team_left.find(has_ctside_stat).text if team_left and team_left.find(has_ctside_stat) else None
                t_score_right = team_right.find(has_tside_stat).text if team_right and team_right.find(has_tside_stat) else None
                ct_score_right = team_right.find(has_ctside_stat).text if team_right and team_right.find(has_ctside_stat) else None

                ot_score_left = int(team_left.find(has_otside_stat).text) if team_left and team_left.find(has_otside_stat) else None
                ot_score_right = int(team_right.find(has_otside_stat).text) if team_right and team_right.find(has_otside_stat) else None

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
                    ovr_numbers = [re.sub(r'\D', '', stat.get_text()) for stat in ovr_stats]
                    ovr_numbers = [float(num) if re.match(r'^\d+\.?\d*$', num) else num for num in ovr_numbers]
                    ovr_data = dict(zip(titles_ovr, ovr_numbers))

                    t_stats = row.find_all(has_tside_stat)
                    t_numbers = [re.sub(r'\D', '', stat.get_text()) for stat in t_stats]
                    t_numbers = [float(num) if re.match(r'^\d+\.?\d*$', num) else num for num in t_numbers]
                    t_data = dict(zip(titles_t, t_numbers))

                    ct_stats = row.find_all(has_ctside_stat)
                    ct_numbers = [re.sub(r'\D', '', stat.get_text()) for stat in ct_stats]
                    ct_numbers = [float(num) if re.match(r'^\d+\.?\d*$', num) else num for num in ct_numbers]
                    ct_data = dict(zip(titles_ct, ct_numbers))

                    combined_data = {**ovr_data, **t_data, **ct_data}
                    combined_data.update({
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

# Combine T-side and CT-side scores into final columns
def assign_scores(group):
    group['t_score'] = group['t_score_left'].iloc[0]
    group['ct_score'] = group['ct_score_left'].iloc[0]
    group['ot_score'] = group['ot_score_left'].iloc[0]
    group.loc[group.index[-5:], 't_score'] = group['t_score_right'].iloc[0]
    group.loc[group.index[-5:], 'ct_score'] = group['ct_score_right'].iloc[0]
    group.loc[group.index[-5:], 'ot_score'] = group['ot_score_right'].iloc[0]
    return group

finaldf = df.groupby('game_id', group_keys=False).apply(assign_scores)

# Calculate total scores for each team and determine the win
def calculate_win(group):
    # Replace None with 0 for overtime scores
    group['ot_score_left'] = group['ot_score_left'].fillna(0)
    group['ot_score_right'] = group['ot_score_right'].fillna(0)

    total_score_left = group['t_score_left'].astype(float).iloc[0] + group['ct_score_left'].astype(float).iloc[0] + group['ot_score_left'].astype(float).iloc[0]
    total_score_right = group['t_score_right'].astype(float).iloc[0] + group['ct_score_right'].astype(float).iloc[0] + group['ot_score_right'].astype(float).iloc[0]

    win_left = 1 if total_score_left > total_score_right else 0
    win_right = 1 if total_score_left < total_score_right else 0

    group['win'] = group['team'].apply(lambda t: win_left if t == group['team'].iloc[0] else win_right)
    return group

finaldf = finaldf.groupby('game_id', group_keys=False).apply(calculate_win)

# Drop intermediate score columns
finaldf = finaldf.drop(['t_score_left', 'ct_score_left', 't_score_right', 'ct_score_right', 'ot_score_right', 'ot_score_left'], axis=1)

# Reorder columns as needed
column_order = ['game_id', 'map', 'win', 'team', 'player', 'agent', 't_score', 'ct_score', 'ot_score'] + [col for col in finaldf.columns if col not in ['player', 'team', 'agent', 'map', 'game_id', 't_score', 'ct_score', 'win', 'ot_score']]
finaldf = finaldf[column_order]


# Enter desired file location inbetween "" and then remove the ""
output_path = r'C:\Users""{event}.csv'.format(event=event)
finaldf.to_csv(output_path, index=False)
