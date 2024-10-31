import requests
import csv
import time
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import urllib.request
import re
import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Increase CSV field size limit to avoid field limit error
csv.field_size_limit(sys.maxsize)

# Base URLs for API and scraping
API_BASE_URL = "https://codeforces.com/api/"
CONTEST_URL_PREFIX = 'https://codeforces.com/contest/'
CONTEST_URL_SUFFIX = '?locale=en'
PROFILE_URL_PREFIX = 'https://codeforces.com/profile/'

# Function to make API request to Codeforces
def get_codeforces_data(method_name, params):
    url = f"{API_BASE_URL}{method_name}"
    params['time'] = int(time.time())
    response = requests.get(url, params=params)
    data = response.json()
    if data['status'] == 'OK':
        return data['result']
    else:
        raise Exception(f"API request failed: {data.get('comment', 'No comment provided')}")

# Function to save user data to CSV
def save_user_data_to_csv(users, filename="user_data.csv"):
    with open(filename, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if not os.path.exists(filename) or os.path.getsize(filename) == 0:
            writer.writerow(["handle", "email", "contribution", "firstName", "lastName", "country", "city", "organization", "contribution", "rating", "registrationPeriodDays", "friendOfCount", "streak", "problemSolved"])
        for user in users:
            handle = user.get('handle')
            email = user.get('email')
            contribution = user.get('contribution')
            first_name = user.get('firstName')
            last_name = user.get('lastName')
            country = user.get('country')
            city = user.get('city')
            organization = user.get('organization')
            rating = user.get('rating')
            registration_time_seconds = user.get('registrationTimeSeconds')
            registration_period_days = (int(time.time()) - registration_time_seconds) // (60 * 60 * 24) if registration_time_seconds else None
            friend_of_count = user.get('friendOfCount')
            streak = fetch_user_streak(handle)
            problems_solved = fetch_user_problems_solved(handle)
            writer.writerow([handle, email, contribution, first_name, last_name, country, city, organization, contribution, rating, registration_period_days, friend_of_count, streak, problems_solved])

# Function to extract user streak and problems solved from profile page
def fetch_user_streak(handle):
    profile_url = f"{PROFILE_URL_PREFIX}{handle}"
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    req = urllib.request.Request(profile_url, headers=headers)
    try:
        response = urllib.request.urlopen(req)
        webpage = response.read()
        logging.info(f"Successfully fetched the profile page for user {handle}.")
    except urllib.error.HTTPError as e:
        logging.error(f"HTTP Error for user {handle}: {e.code}")
        return 0
    except urllib.error.URLError as e:
        logging.error(f"URL Error for user {handle}: {e.reason}")
        return 0

    soup = BeautifulSoup(webpage, 'html.parser')
    # Extract max streak from profile page
    streak_div = soup.find('div', class_='_UserActivityFrame_countersRow')
    if streak_div:
        max_streak_div = streak_div.find_all('div', class_='_UserActivityFrame_counter')[0]
        max_streak_value = max_streak_div.find('div', class_='_UserActivityFrame_counterValue').get_text(strip=True)
        streak_days = int(re.search(r'\d+', max_streak_value).group()) if re.search(r'\d+', max_streak_value) else 0
    else:
        logging.info(f"Streak information not found for user {handle}.")
        streak_days = 0

    return streak_days

# Function to extract number of problems solved from profile page
def fetch_user_problems_solved(handle):
    profile_url = f"{PROFILE_URL_PREFIX}{handle}"
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    req = urllib.request.Request(profile_url, headers=headers)
    try:
        response = urllib.request.urlopen(req)
        webpage = response.read()
        logging.info(f"Successfully fetched the profile page for user {handle}.")
    except urllib.error.HTTPError as e:
        logging.error(f"HTTP Error for user {handle}: {e.code}")
        return 0
    except urllib.error.URLError as e:
        logging.error(f"URL Error for user {handle}: {e.reason}")
        return 0

    soup = BeautifulSoup(webpage, 'html.parser')
    problems_solved_div = soup.find('div', class_='_UserActivityFrame_counterValue')
    if problems_solved_div:
        problems_solved_value = problems_solved_div.get_text(strip=True)
        problems_solved_count = int(re.search(r'\d+', problems_solved_value).group()) if re.search(r'\d+', problems_solved_value) else 0
    else:
        logging.info(f"Problems solved information not found for user {handle}.")
        problems_solved_count = 0

    return problems_solved_count

# Function to save contest data to CSV
def save_contest_data_to_csv(contests, filename="contest_data.csv"):
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["id", "name", "startDate", "division", "registeredParticipants", "finalStandings", "problemsUsed", "preparedBy", "description"])
        for contest in contests:
            contest_id = contest.get('id')
            name = contest.get('name')
            start_time_seconds = contest.get('startTimeSeconds')
            start_date = datetime.fromtimestamp(start_time_seconds, tz=timezone.utc).date() if start_time_seconds else None
            division = "Div. 1" if "Div. 1" in name else "Div. 2" if "Div. 2" in name else "Unknown"
            registered_participants, final_standings = fetch_contest_standings(contest_id)
            problems_used = fetch_contest_problems(contest_id)
            prepared_by = contest.get('preparedBy', 'N/A')
            description = contest.get('description', 'N/A')
            writer.writerow([contest_id, name, start_date, division, registered_participants, final_standings, problems_used, prepared_by, description])

# Function to fetch contest standings and participants
def fetch_contest_standings(contest_id):
    try:
        standings_data = get_codeforces_data("contest.standings", {"contestId": contest_id})
        participants = [
            row['party'].get('teamName', row['party']['members'][0]['handle'])
            for row in standings_data['rows']
        ]
        standings = [
            (row['party'].get('teamName', row['party']['members'][0]['handle']), row['rank'])
            for row in standings_data['rows']
        ]
        return participants, standings
    except Exception as e:
        logging.error(f"Error fetching standings for contest {contest_id}: {e}")
        return [], []

# Function to fetch contest problems
def fetch_contest_problems(contest_id):
    try:
        standings_data = get_codeforces_data("contest.standings", {"contestId": contest_id})
        problem_ids = [
            f"{contest_id}_{problem['index']}" for problem in standings_data['problems']
        ]
        return problem_ids
    except Exception as e:
        logging.error(f"Error fetching problems for contest {contest_id}: {e}")
        return []

# Function to fetch all problems and save to CSV
def fetch_all_problems():
    try:
        problems_data = get_codeforces_data("problemset.problems", {})
        problems, statistics = problems_data['problems'], problems_data['problemStatistics']
        save_problem_data_to_csv(problems, statistics)
    except Exception as e:
        logging.error(f"Error fetching problems: {e}")

# Function to save problem data to CSV
def save_problem_data_to_csv(problems, statistics, filename="problem_data.csv"):
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["contestId", "problemsetName", "index", "name", "rating", "tags", "solvedCount", "timeLimit", "memoryLimit", "description"])
        stat_dict = {f"{stat['contestId']}_{stat['index']}": stat['solvedCount'] for stat in statistics}
        for problem in problems:
            contest_id = problem.get('contestId')
            problemset_name = problem.get('problemsetName')
            index = problem.get('index')
            name = problem.get('name')
            rating = problem.get('rating')
            tags = ', '.join(problem.get('tags', []))
            solved_count = stat_dict.get(f"{contest_id}_{index}", 0)
            time_limit, memory_limit, description = fetch_problem_details(contest_id, index)
            writer.writerow([contest_id, problemset_name, index, name, rating, tags, solved_count, time_limit, memory_limit, description])

# Function to extract problem details using urllib
def fetch_problem_details(contest_id, problem_index):
    problem_url = f"{CONTEST_URL_PREFIX}{contest_id}/problem/{problem_index}{CONTEST_URL_SUFFIX}"
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    req = urllib.request.Request(problem_url, headers=headers)
    try:
        response = urllib.request.urlopen(req)
        webpage = response.read()
        logging.info("Successfully fetched the webpage.")
    except urllib.error.HTTPError as e:
        logging.error(f"HTTP Error: {e.code}")
        return None, None, None
    except urllib.error.URLError as e:
        logging.error(f"URL Error: {e.reason}")
        return None, None, None

    soup = BeautifulSoup(webpage, 'html.parser')
    
    # Extract time limit
    time_limit_div = soup.find('div', class_='time-limit')
    time_limit = time_limit_div.get_text(strip=True).replace('time limit per test', '').strip() if time_limit_div else 'N/A'

    # Extract memory limit
    memory_limit_div = soup.find('div', class_='memory-limit')
    memory_limit = memory_limit_div.get_text(strip=True).replace('memory limit per test', '').strip() if memory_limit_div else 'N/A'

    # Extract full problem description
    problem_statement_div = soup.find('div', class_='problem-statement')
    if not problem_statement_div:
        logging.info("Problem statement not found.")
        return time_limit, memory
