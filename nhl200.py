import requests
import urllib
import time
from bs4 import BeautifulSoup
import re, sys, time, os

INDEX_NAME = 0
INDEX_PLAYER_URL = 1
INDEX_POSITION = 2
INDEX_PRICE = 3
INDEX_GAMES = 4
INDEX_GOALS = 5
INDEX_ASSISTS = 6
INDEX_POINTS = 7
INDEX_POINTS_SHARE = 8
INDEX_WINS = 9
INDEX_TEAM_GOALS = 10
INDEX_TEAM_ASSISTS = 11
INDEX_TEAM_POINTS = 12
INDEX_TEAM_WINS = 13


POSITION_FORWARD = 'F'
POSITIONS_FORWARD = ['C', 'LW', 'RW', 'F']
POSITION_DEFENSEMAN = 'D'
POSITION_GOALIE = 'G'

TEAMS_LIST = ["ana", "ari", "bos", "buf", "cgy", "car", "chi", "col", "cbj",
"dal", "det", "edm", "fla", "lak", "min", "mtl", "nsh", "njd", "nyi", "nyr",
"ott", "phi", "pit", "sjs", "stl", "tbl", "tor", "van", "veg", "wsh", "wpg"]

player_stats_cache = {}

def get_player_score(p):
	return p[INDEX_POINTS] + p[INDEX_WINS]

def get_player_score_label():
	return "Points + Wins"

def get_roster_score(roster):
	return sum(get_player_score(player) for player in roster)

def get_roster_cost(roster):
	return sum(player[INDEX_PRICE] for player in roster)

def filter_players(players, num):
	filtered = []
	
	for i in range(0, len(players)):
		num_better = 0
		p1 = players[i]
		p1_score = get_player_score(p1)

		for j in range(0, len(players)):
			if i == j:
				continue

			p2 = players[j]
			p2_score = get_player_score(p2)

			if p1_score == 0 and p2_score > 0:
				num_better += 1
			elif p1_score == 0 and p2_score == 0 and p1[INDEX_PRICE] > p2[INDEX_PRICE]:
				num_better += 1
			elif p1[INDEX_PRICE] >= p2[INDEX_PRICE] and p1_score < p2_score:
				num_better += 1
				p1[INDEX_PRICE] >= p2[INDEX_PRICE]
			if num_better >= num:
				break

		if num_better < num:
			filtered.append(p1)

	return filtered

def select_team(forwards, defense, goalies):
	best_score = -1
	best_team = None

	# this is ugly as fuck
	for f1 in range(0, len(forwards[:-2])):
		forward1 = forwards[f1]
		for f2 in range(f1 + 1, len(forwards[:-1])):
			forward2 = forwards[f2]
			for f3 in range(f2 + 1, len(forwards)):
				forward3 =  forwards[f3]
				for d1, defense1 in enumerate(defense[:-1]):
					for d2, defense2 in enumerate(defense[(d1 + 1):]):
						for goalie in goalies:
							players = [forward1, forward2, forward3, defense1, defense2, goalie]
							total_cost = get_roster_cost(players)

							if total_cost > 200:
								continue

							score = sum(get_player_score(player) for player in players)

							if score > best_score:
								best_score = score
								best_team = players

	return best_team

def print_team(team_name, roster):	
	team_score = 0
	team_price = 0

	print team_name.upper()
	print "{}\t{}\t{}\t{}".format("Position", "Name", "Cost", get_player_score_label())

	for player in roster:
		score = get_player_score(player)
		price = player[INDEX_PRICE]

		team_score += score
		team_price += price

		position = player[INDEX_POSITION]
		if position not in [POSITION_GOALIE, POSITION_DEFENSEMAN]:
			position = POSITION_FORWARD
		
		print "{}\t{}\t${}\t{:,}".format(position, player[INDEX_NAME], price, score)


	print "Cost\t${}".format(team_price)
	print "Score\t{:,}".format(team_score)

def create_team(team_name):

	forwards = []
	defense = []
	goalies = []

	# team already scraped
	file = "data/{}.csv".format(team_name.lower())
	if os.path.isfile(file):
		f = open(file)

		for line in f:
			data = line.split(',')
			name = data[INDEX_NAME].strip().replace("*", "")
			player_url = data[INDEX_PLAYER_URL].strip()
			position = data[INDEX_POSITION].strip()
			price = int(data[INDEX_PRICE])
			games = int(data[INDEX_GAMES])
			goals = int(data[INDEX_GOALS])
			assists = int(data[INDEX_ASSISTS])
			points = int(data[INDEX_POINTS])
			points_share = float(data[INDEX_POINTS_SHARE])
			wins = int(data[INDEX_WINS])
			team_goals = int(data[INDEX_TEAM_GOALS])
			team_assists = int(data[INDEX_TEAM_ASSISTS])
			team_points = int(data[INDEX_TEAM_POINTS])
			team_wins = int(data[INDEX_TEAM_WINS])

			player = [name, player_url, position, price, games, goals, 
			assists, points, points_share, wins, team_goals, team_assists, 
			team_points, team_wins]

			if position == POSITION_DEFENSEMAN:
				defense.append(player)
			elif position == POSITION_GOALIE:
				goalies.append(player)
			else:
				forwards.append(player)

		forwards = filter_players(forwards, 3)
		defense = filter_players(defense, 2)
		goalies = filter_players(goalies, 1)

		roster = select_team(forwards, defense, goalies)
		return roster
	else:
		return None

def strip_non_ascii(string):
    ''' Returns the string without non ASCII characters'''
    stripped = (c for c in string if 0 < ord(c) < 127)
    return ''.join(stripped)

def getStat(stat):
	try:
		if not hasattr(stat.next_sibling.next_sibling, 'contents'):
			return stat.next_sibling.next_sibling.next_sibling.contents[0]
		else:
			return stat.next_sibling.next_sibling.contents[0]
	except:
		# hockey reference has an empty cell for this, move along
		return 0

def get_goalie_offense(url):
	response = requests.get(url)

	soup = BeautifulSoup(response.text, "html.parser")
	table_data = soup.findAll("table", {"id": "stats_basic_nhl"})

	if len(table_data) == 0:
		table_data = soup.findAll("table", {"id": "stats_basic_plus_nhl"})

	table = table_data[0]
	footer = table.find_all('tfoot')[0]
	rows = footer.find_all('tr')

	for row in rows:
		row_header = row.find_all("th")[0]
		if row_header.get_text() == "Career":
			cells = row_header = row.find_all("td")
			if cells[2].get_text() == "NHL":
				goals = int(cells[22].get_text())
				assists = int(cells[23].get_text())
				points = int(cells[24].get_text())

				return {"goals": goals, "assists": assists, "points": points}


def get_career_stats(player_url):
	global player_stats_cache

	if player_url in player_stats_cache:
		return player_stats_cache[player_url]
	
	url = "https://www.hockey-reference.com{}".format(player_url)
	response = requests.get(url)

	soup = BeautifulSoup(response.text, "html.parser")
	position_html = soup.findAll(text=re.compile("Position"))
	position = strip_non_ascii(position_html[0].next_element[1:].strip())

	tips = soup.findAll("h4", {"class": "poptip"})

	if len(tips) == 0:
		return None

	games = int(getStat(tips[0]))
	points_share = float(getStat(tips[5]))

	if position == 'G':
		goalie_offense = get_goalie_offense(url)
		goals = goalie_offense["goals"]
		assists = goalie_offense["assists"]
		points = goalie_offense["points"]
		wins = int(getStat(tips[1]))
	else:
		goals = int(getStat(tips[1]))
		assists = int(getStat(tips[2]))
		points = int(getStat(tips[3]))
		wins = 0

	stats = {"position": position, "games": games, "goals": goals, 
	"assists": assists, "points": points, "points_share": points_share, "wins": wins}

	player_stats_cache[player_url] = stats
	
	# don't hit hockey reference too fast
	time.sleep(0.5)
	return stats


def initialize_cache(teams):
	global player_stats_cache
	
	for team in teams:
		file = "data/{}.csv".format(team.lower())
		if not os.path.isfile(file):
			continue

		f = open(file)

		for line in f:
			data = line.split(",")
			name = data[0].strip()
			player_url = data[1].strip()
			position = data[2].strip()
			price = int(data[3])
			games = int(data[4])
			goals = int(data[5])
			assists = int(data[6])
			points = int(data[7])
			points_share = float(data[8])
			wins = int(data[9])

			stats = {"position": position, "games": games, "goals": goals, 
			"assists": assists, "points": points, "points_share": points_share, "wins": wins}
			player_stats_cache[player_url] = stats

		f.close()

def get_rows(url):
	response = requests.get(url)
	soup = BeautifulSoup(response.text, "html.parser")
	table = soup.findAll("tbody")[0]
	return table.find_all('tr')

def scrape_team(team):
	skater_rows = get_rows("https://www.hockey-reference.com/teams/{}/skaters.html".format(team.upper()))
	goalie_rows = get_rows("https://www.hockey-reference.com/teams/{}/goalies.html".format(team.upper()))

	players_seen = set()

	with open("data/{}.csv".format(team.lower()), 'w') as f:
		
		for index, row in enumerate(skater_rows + goalie_rows):
			# these are divider rows, we don't care
			if len(row) > 30:
				continue

			cells = row.find_all("td")
			name = cells[0].get_text().encode('utf-8')
			player_url = cells[0].next_element['href']
			price = int(cells[4].get_text())

			if player_url in players_seen:
				print "SEEN\t{}\t{}\t{}".format(team, name, player_url)
				continue

			players_seen.add(player_url)

			# maximum price for a player is $195
			if price > 195:
				continue

			if index >= len(skater_rows):
				team_wins = int(cells[6].get_text()) if cells[6].get_text() != '' else 0
				team_goals = int(cells[21].get_text()) if cells[21].get_text() != '' else 0
				team_assists = int(cells[22].get_text()) if cells[22].get_text() != '' else 0
				team_points = int(cells[23].get_text()) if cells[23].get_text() != '' else 0
			else:
				team_wins = 0
				team_goals = int(cells[5].get_text()) if cells[5].get_text() != '' else 0
				team_assists = int(cells[6].get_text()) if cells[6].get_text() != '' else 0
				team_points = int(cells[7].get_text()) if cells[7].get_text() != '' else 0

			career_stats = get_career_stats(player_url)

			if career_stats is None:
				# somethng went wrong
				continue

			s = "{},{},{},{},{},{},{},{},{},{},{},{},{},{}".format(name, player_url, 
				career_stats["position"], price, career_stats["games"], career_stats["goals"], 
				career_stats["assists"], career_stats["points"], career_stats["points_share"], 
				career_stats["wins"], team_goals, team_assists, team_points, team_wins)

			f.write("{}\n".format(s))


initialize_cache(TEAMS_LIST)

rosters = []
for team in TEAMS_LIST:
	file = "data/{}.csv".format(team.lower())
	if not os.path.isfile(file):
		scrape_team(team)

	roster = create_team(team)

	if roster is not None:
		rosters.append([team, roster])


for team, roster in sorted(rosters, key=lambda x: get_roster_score(x[1]), reverse=True):
	print_team(team, roster)
	print ""
