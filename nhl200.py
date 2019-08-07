import requests
import urllib
import time
from bs4 import BeautifulSoup
import re, sys, time, os

NAME = 0
POSITION = 1
PRICE = 2
GAMES = 3
POINTS = 4
PS = 5

DEFENSEMAN = 'D'
GOALIE = 'G'

player_stats = {}

def getScore(p):
	if p[GAMES] >= 0:
		return p[POINTS]
	else:
		return 0

def getRosterScore(roster):
	return sum(getScore(player) for player in roster)


def filterPlayers(players, num):
	filtered = []
	for i in range(0, len(players)):
		better = 0
		p1 = players[i]
		for j in range(0, len(players)):
			if i == j:
				continue

			p2 = players[j]

			if p1[PRICE] >= p2[PRICE] and getScore(p1) <= getScore(p2):
				better += 1
				# print "{}\t{}".format(p1[NAME], p2[NAME])

			if better >= num:
				break

		if better < num:
			filtered.append(p1)

	return filtered


def selectTeam(forwards, defense, goalies):
	best_score = -1
	best_team = None

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

							total_cost = sum(p[PRICE] for p in players)

							if total_cost > 200:
								continue

							score = sum(getScore(p) for p in players)

							if score > best_score:
								best_score = score
								best_team = players

	return best_team

def printTeam(team, roster):
	team_score = 0
	team_price = 0
	team_points = 0
	team_wins = 0

	print team.upper()
	print "{}\t{}\t{}\t{}".format("Position", "Name", "Cost", "Points/Wins")

	for p in roster:
		s = getScore(p)
		price = p[PRICE]

		team_score += s
		team_price += price

		if p[POSITION] == GOALIE:
			team_wins += s
		else:
			team_points += s
		
		pos = p[POSITION]
		if pos not in [GOALIE, DEFENSEMAN]:
			pos = "F"
		
		print "{}\t{}\t${}\t{}".format(pos, p[NAME], price, s)


	print "Cost\t${}".format(team_price)
	print "Points\t{:,}".format(team_points)
	print "Wins\t{:,}".format(team_wins)
	print "Score\t{:,}".format(team_score)


def createTeam(team):

	forwards = []
	defense = []
	goalies = []
	# team already scraped
	file = "data/{}.csv".format(team.upper())
	if os.path.isfile(file):
		f = open(file)
		for line in f:
			data = line.split(',')
			name = data[0].strip()
			position = data[2].strip()
			price = int(data[3])
			games = int(data[4])
			points = int(data[7])
			ps = float(data[8])

			player = [name, position, price, games, points, ps]

			if position == DEFENSEMAN:
				defense.append(player)
			elif position == GOALIE:
				goalies.append(player)
			else:
				forwards.append(player)

		forwards = filterPlayers(forwards, 3)
		defense = filterPlayers(defense, 2)
		goalies = filterPlayers(goalies, 1)

		roster = selectTeam(forwards, defense, goalies)
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
		print "COULDN'T GET STAT"
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


def getCareerStats(player_name, player_id, url):
	global player_stats
	if player_id in player_stats:
		print "cache hit\t{}".format(player_name)
		return player_stats[player_id]
	else:
		print "cache miss\t{}".format(player_name)
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
		goals = 0
		assists = 0
		points = int(getStat(tips[1]))
	else:
		goals = int(getStat(tips[1]))
		assists = int(getStat(tips[2]))
		points = int(getStat(tips[3]))

	stats = [position,games,goals,assists,points,points_share]
	player_stats[player_id] = stats
	time.sleep(0.5)
	return stats


def getRows(url):
	response = requests.get(url)
	soup = BeautifulSoup(response.text, "html.parser")
	table = soup.findAll("tbody")[0]
	return table.find_all('tr')

def initializeCache(teams):
	global player_stats
	for team in teams:
		file = "data/{}.csv".format(team.lower())
		if not os.path.isfile(file):
			continue

		f = open(file)

		for line in f:
			data = line.split(",")
			name = data[0].strip()
			name_id = data[1].strip()
			position = data[2].strip()
			price = int(data[3])
			games = int(data[4])
			goals = int(data[5])
			assists = int(data[6])
			points = int(data[7])
			points_share = float(data[8])

			stats = [position,games,goals,assists,points,points_share]
			player_stats[name_id] = stats
		f.close()

def scrapeTeam(team):
	goalie_rows = getRows("https://www.hockey-reference.com/teams/{}/goalies.html".format(team.upper()))
	skater_rows = getRows("https://www.hockey-reference.com/teams/{}/skaters.html".format(team.upper()))

	with open("data/{}.csv".format(team.lower()), 'w') as f:
		for row in (goalie_rows + skater_rows):
			if len(row) > 30:
				continue
			cells = row.find_all("td")
			name = cells[0].get_text().encode('utf-8')
			name_id = cells[0]['data-append-csv']
			price = int(cells[4].get_text())

			if price > 195:
				continue

			url = "https://www.hockey-reference.com{}".format(cells[0].next_element['href'])
			career_stats = getCareerStats(name, name_id, url)

			if career_stats is None:
				continue

			s = "{},{},{},{},{},{},{},{},{}".format(name, name_id, career_stats[0], price, career_stats[1], career_stats[2], career_stats[3], career_stats[4], career_stats[5])
			f.write("{}\n".format(s))

        
teams = ["ana", "ari", "bos", "buf", "cgy", "car", "chi", "col", "cbj",
"dal", "det", "edm", "fla", "lak", "min", "mtl", "nsh", "njd", "nyi", "nyr",
"ott", "phi", "pit", "sjs", "stl", "tbl", "tor", "van", "veg", "wsh", "wpg"]

initializeCache(teams)

for team in teams:

	file = "data/{}.csv".format(team.upper())
	if not os.path.isfile(file):
		scrapeTeam(team)

	roster = createTeam(team)
	printTeam(team, roster)
	print ""


''' 
todo
	goalie points
	adding wins as separate stat
	incomplete caching (temp file?)
	better nested for loops
	player class
	team class
	general cleanup
'''
