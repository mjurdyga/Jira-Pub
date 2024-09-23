import requests
from datetime import datetime
import json

# Jira instance details
JIRA_URL = "https://your-domain.atlassian.net"
PROJECT_KEY = "YOUR_PROJECT_KEY"
EMAIL = "your-email@example.com"
API_TOKEN = "your-api-token"

def get_today_comments():
    # JQL query to filter issues with comments created today
    jql_query = f'project = "{PROJECT_KEY}" AND created >= startOfDay()'
    
    # API endpoint for searching issues
    url = f"{JIRA_URL}/rest/api/3/search"
    
    # Request parameters
    params = {
        "jql": jql_query,
        "fields": "comment",
        "expand": "renderedFields"
    }
    
    # Make the API request
    response = requests.get(
        url,
        params=params,
        auth=(EMAIL, API_TOKEN)
    )
    
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return []
    
    data = response.json()
    
    comments = []
    for issue in data['issues']:
        for comment in issue['fields']['comment']['comments']:
            comment_date = datetime.strptime(comment['created'][:19], "%Y-%m-%dT%H:%M:%S")
            if comment_date.date() == datetime.now().date():
                comments.append({
                    'commenter': comment['author']['displayName'],
                    'date': comment_date.strftime("%Y-%m-%d"),
                    'time': comment_date.strftime("%H:%M:%S"),
                    'content': comment['body']
                })
    
    return comments

def save_comments(comments):
    with open('today_comments.json', 'w') as f:
        json.dump(comments, f, indent=2)

if __name__ == "__main__":
    today_comments = get_today_comments()
    save_comments(today_comments)
    print(f"Retrieved and saved {len(today_comments)} comments from today.")
