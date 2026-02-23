import requests
import math

# ==============================
# CONFIG
# ==============================



headers = {
    "X-Auth-Token": API_KEY
}

BASE_URL = "https://api.football-data.org/v4"

HOME_ADVANTAGE = 0.25   # home team boost


# ==============================
# GET LAST 5 MATCH STATS
# ==============================

def get_team_stats(team_id):

    url = f"{BASE_URL}/teams/{team_id}/matches?status=FINISHED&limit=5"
    response = requests.get(url, headers=headers)
    data = response.json()

    goals_scored = 0
    goals_conceded = 0
    matches = 0

    for match in data.get("matches", []):

        home_id = match["homeTeam"]["id"]
        away_id = match["awayTeam"]["id"]

        home_goals = match["score"]["fullTime"]["home"]
        away_goals = match["score"]["fullTime"]["away"]

        if home_goals is None or away_goals is None:
            continue

        matches += 1

        if team_id == home_id:
            goals_scored += home_goals
            goals_conceded += away_goals
        else:
            goals_scored += away_goals
            goals_conceded += home_goals

    if matches == 0:
        return 1.0, 1.0

    return goals_scored / matches, goals_conceded / matches


# ==============================
# POISSON FUNCTIONS
# ==============================

def poisson(lmbda, k):
    return (lmbda ** k) * math.exp(-lmbda) / math.factorial(k)


def calculate_probabilities(xG_home, xG_away):

    max_goals = 6

    home_win = 0
    draw = 0
    away_win = 0
    btts_yes = 0

    score_matrix = []

    for h in range(max_goals):
        for a in range(max_goals):

            prob = poisson(xG_home, h) * poisson(xG_away, a)

            score_matrix.append(((h, a), prob))

            if h > a:
                home_win += prob
            elif h == a:
                draw += prob
            else:
                away_win += prob

            if h > 0 and a > 0:
                btts_yes += prob

    score_matrix.sort(key=lambda x: x[1], reverse=True)

    top_scores = score_matrix[:3]

    return (
        round(home_win * 100, 1),
        round(draw * 100, 1),
        round(away_win * 100, 1),
        round(btts_yes * 100, 1),
        top_scores
    )


# ==============================
# MAIN PREDICTION FUNCTION
# ==============================

def predict_match(home_id, away_id, home_name, away_name):

    home_scored, home_conceded = get_team_stats(home_id)
    away_scored, away_conceded = get_team_stats(away_id)

    # Expected Goals with home advantage
    xG_home = (home_scored + away_conceded) / 2 + HOME_ADVANTAGE
    xG_away = (away_scored + home_conceded) / 2

    P_home, P_draw, P_away, BTTS_prob, top_scores = calculate_probabilities(xG_home, xG_away)

    # Half-time ≈ 45%
    HT_home = round(xG_home * 0.45, 2)
    HT_away = round(xG_away * 0.45, 2)

    # Confidence
    diff = abs(P_home - P_away)
    if diff > 25:
        confidence = "HIGH"
    elif diff > 15:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    print("\n=================================")
    print(f"{home_name} vs {away_name}")
    print("---------- 1X2 ----------")
    print(f"Home: {P_home}%")
    print(f"Draw: {P_draw}%")
    print(f"Away: {P_away}%")

    print("---------- VIP ----------")
    print(f"BTTS YES: {BTTS_prob}%")
    print(f"Mi-temps Expected: {HT_home} - {HT_away}")
    print("Top 3 Exact Scores:")
    for score, prob in top_scores:
        print(f"{score[0]} - {score[1]}  ({round(prob*100,1)}%)")

    print(f"Confidence: {confidence}")
    print("=================================")


# ==============================
# GET TOOMORO 7  MATCHES cofiance
# ==============================

response = requests.get(f"{BASE_URL}/matches", headers=headers)
data = response.json()

for match in data["matches"]:

    if match["status"] == "TIMED":

        home_id = match["homeTeam"]["id"]
        away_id = match["awayTeam"]["id"]

        home_name = match["homeTeam"]["name"]
        away_name = match["awayTeam"]["name"]

        predict_match(home_id, away_id, home_name, away_name)
