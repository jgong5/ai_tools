import requests
from datetime import datetime
import json
import os
from dotenv import load_dotenv

load_dotenv()

class GitHubItem:
    def __init__(self, title, url, description, comments):
        self.title = title
        self.url = url
        self.description = description
        self.comments = comments

def make_request(url, token):
    print(f"Making request to URL: {url}")
    headers = {
        "Authorization": f"token {token}"
    }
    response = requests.get(url, headers=headers)
    print(f"Response status code: {response.status_code}")
    if response.status_code != 200:
        print(f"Request failed: {response.status_code}")
        return None
    print(f"Request successful: {response.status_code}")
    return response.text

def get_all_items(base_url, token, start_date, end_date):
    items = []
    page = 1
    while True:
        url = f"{base_url}?state=all&per_page=100&page={page}"
        response_text = make_request(url, token)
        if not response_text:
            break
        data = json.loads(response_text)
        if not data:
            break

        for item in data:
            created_at = item.get("created_at")
            if created_at and created_at > end_date:
                continue
            if created_at and created_at < start_date:
                print("Reached items outside of date range. Stopping early.")
                return items

            comments_url = item.get("comments_url")
            comments = []
            if comments_url:
                print(f"Fetching comments from URL: {comments_url}")
                comments_response = make_request(comments_url, token)
                if comments_response:
                    comments_data = json.loads(comments_response)
                    for comment in comments_data:
                        comments.append(comment["body"])

            description = item.get("body") if item.get("body") else "No description available"
            items.append(GitHubItem(item["title"], item["html_url"], description, comments))
        
        page += 1
    return items

# Example usage
if __name__ == "__main__":
    issues_url = "https://api.github.com/repos/pytorch/pytorch/issues"
    pulls_url = "https://api.github.com/repos/pytorch/pytorch/pulls"
    token = os.getenv("GITHUB_TOKEN")
    start_date = "2024-10-09T00:00:00Z"
    end_date = "2024-10-10T23:59:59Z"

    if not token:
        print("Error: GitHub token not found in environment variables.")
    else:
        print("Starting to fetch issues and pull requests...")
        issues = get_all_items(issues_url, token, start_date, end_date)
        pulls = get_all_items(pulls_url, token, start_date, end_date)

        data = issues + pulls

        print("Filtered GitHub Items:")
        for item in data:
            print(f"Title: {item.title}\nURL: {item.url}\nDescription: {item.description[:100]}...\nComments: {len(item.comments)}\n")