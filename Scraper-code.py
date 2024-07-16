from bs4 import BeautifulSoup
import requests as rq
import pandas as pd
import re

# Enter the URL of the event page you want to scrape. For example, the Champions Tour 2024 EMEA Stage 2 event page.
event_url = "https://www.vlr.gg/event/matches/2094/champions-tour-2024-emea-stage-2/?series_id=all"

# retrieving and parsing whole page HTML data from the URL
html_text = rq.get(event_url).text
bs = BeautifulSoup(html_text, "lxml")
#Creating data titles and functions to extract t/ct data
def has_map_data(tag):
    return tag.has_attr('class') and 'vm-stats-game' in tag['class']
def has_tside_stat(tag):
    return tag.has_attr('class') and 'mod-t' in tag['class']
def has_ctside_stat(tag):
    return tag.has_attr('class') and 'mod-ct' in tag['class']
titles_t = [
    "rating-tside",
    "acs-tside",
    "kills-tside",
    "deaths-tside",
    "assists-tside",
    "kd_diff-tside",
    "kast-tside",
    "adr-tside",
    "hs_perc-tside",
    "fb-tside",
    "fd-tside",
    "fk_diff-tside"
]
titles_ct = [
    "rating-ctside",
    "acs-ctside",
    "kills-ctside",
    "deaths-ctside",
    "assists-ctside",
    "kd_diff-ctside",
    "kast-ctside",
    "adr-ctside",
    "hs_perc-ctside",
    "fb-ctside",
    "fd-ctside",
    "fk_diff-ctside"
]
all_players_t_data = []
all_players_ct_data = []

# retrieving individual match URLs from initial URL
match_blocks = bs.find_all('a', class_=lambda c: c and all(cls in c.split() for cls in ['wf-module-item', 'match-item']))
matchlinks_array = []
for match_block in match_blocks:
    match_redirects = "https://www.vlr.gg" + match_block.get("href")
    matchlinks_array.append(match_redirects)

for match_link in matchlinks_array:
    match_html_text = rq.get(match_link).text
    match_bs = BeautifulSoup(match_html_text, "lxml")

    all_map_data = match_bs.find_all(has_map_data)

    for map_tdata in all_map_data:
        game_id = map_tdata.get('data-game-id')
        if game_id != "all":
            map_name_elem = map_tdata.find('div', class_='map')
            if map_name_elem:
                map_name = map_name_elem.text.strip()
                map = re.split(r'\s{2,}', map_name)[0].strip()
            stats_rows = map_tdata.find_all('tr')
            for row in stats_rows[1:]:  # Skip the header row
                player_data = row.find('td', class_='mod-player')
                if player_data:
                    player_team_text = player_data.text.strip()
                    player = re.split(r'\s{2,}', player_team_text)[0].strip()
                    team = player_team_text.split()[-1].strip()
                    
                    # Extract agent data
                    agent_td = row.find('td', class_='mod-agents')
                    if agent_td:
                        agent_img = agent_td.find('img')
                        if agent_img:
                            agent = agent_img.get('alt', 'Unknown').strip()
                        else:
                            agent = 'Unknown'
                    else:
                        agent = 'Unknown'
                    
                    t_stats = row.find_all(has_tside_stat)
                    numbers = [re.sub(r'\D', '', stat.get_text()) for stat in t_stats]
                    numbers = [float(num) if re.match(r'^\d+\.?\d*$', num) else num for num in numbers]  # Convert to float if valid
                    data = dict(zip(titles_t, numbers))
                    data['player'] = player
                    data['team'] = team
                    data['map'] = map
                    data['game_id'] = game_id
                    data['agent'] = agent
                    all_players_t_data.append(data)
    tdf = pd.DataFrame(all_players_t_data)

    # Reorder columns to put player, team, agent, map, and game_id first
    column_order = ['player', 'team', 'agent', 'map', 'game_id'] + titles_t 
    tdf = tdf[column_order]

    for map_ctdata in all_map_data:
        game_id = map_ctdata.get('data-game-id')
        stats_rows = map_ctdata.find_all('tr')

        if game_id != "all":    
            for row in stats_rows[1:]:  # Skip the header row
                player_data = row.find('td', class_='mod-player')
                if player_data:
                    ct_stats = row.find_all(has_ctside_stat)
                    numbers = [re.sub(r'\D', '', stat.get_text()) for stat in ct_stats]
                    numbers = [float(num) if re.match(r'^\d+\.?\d*$', num) else num for num in numbers]  # Convert to float if valid
                    data = dict(zip(titles_ct, numbers))
                    all_players_ct_data.append(data)

    ctdf = pd.DataFrame(all_players_ct_data)
#Combine the two dataframes so each player has a row with both t and ct data for every map played
finaldf = pd.concat([tdf, ctdf], axis=1).reindex(tdf.index)

output_path = r'#imput a file path here to save the data to a csv file'
finaldf.to_csv(output_path, index=False)

    
#Method to extract map links from match pages that isnt nescassary for this project
'''matchmap_links_array = []
def has_map_switch_class(tag):
    return tag.has_attr('class') and 'vm-stats-gamesnav-item' in tag['class'] and 'js-map-switch' in tag['class']
for match_link in matchlinks_array:
    match_html_text = rq.get(match_link).text
    match_bs = BeautifulSoup(match_html_text, "lxml")
    
    # Extract relevant elements with the specified classes
    elements = match_bs.find_all(has_map_switch_class)
    
    for element in elements:
        matchmap_redirects_array = []
        data_disabled = element.get('data-disabled')
        if data_disabled == "0":
            matchmap_redirects_array = "https://www.vlr.gg" + element.get('data-href') + "/?game=" + element.get('data-game-id') +"&tab=overview"
            matchmap_links_array.append(matchmap_redirects_array)

            for i in range(len(matchmap_links_array)):
                if "/?map=all" in matchmap_links_array[i]:
                    matchmap_links_array[i] = matchmap_links_array[i].replace("/?map=all", "")
                for j in range(1, 6): # 5 maps in grand finals games
                    if f"/?map={j}" in matchmap_links_array[i]:
                        matchmap_links_array[i] = matchmap_links_array[i].replace(f"/?map={j}", "")'''



