import requests
from datetime import datetime
import json
import os
import argparse
import shelve
from dotenv import load_dotenv

load_dotenv()

class GitHubItem:
    def __init__(self, title, url, description, submitter, tags, assignees, reviewers, comments):
        self.title = title
        self.url = url
        self.description = description
        self.submitter = submitter
        self.tags = tags
        self.assignees = assignees
        self.reviewers = reviewers
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

def get_all_items(base_url, token, start_date, end_date, db):
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
            item_id = item.get("id")
            created_at = item.get("created_at")
            if created_at and created_at > end_date:
                continue
            if created_at and created_at < start_date:
                print("Reached items outside of date range. Stopping early.")
                return items

            # Check if item is already in the database
            if str(item_id) in db:
                print(f"Item with ID {item_id} found in database, skipping fetch.")
                items.append(db[str(item_id)])
            else:
                comments_url = item.get("comments_url")
                comments = []
                if comments_url:
                    print(f"Fetching comments from URL: {comments_url}")
                    comments_response = make_request(comments_url, token)
                    if comments_response:
                        comments_data = json.loads(comments_response)
                        for comment in comments_data:
                            comment_body = comment["body"]
                            comment_author = comment["user"]["login"] if comment.get("user") else "Unknown"
                            comments.append({"author": comment_author, "body": comment_body})

                description = item.get("body") if item.get("body") else "No description available"
                submitter = item["user"]["login"] if item.get("user") else "Unknown"
                tags = [label["name"] for label in item.get("labels", [])]
                assignees = [assignee["login"] for assignee in item.get("assignees", [])]
                reviewers = []

                if "pulls" in base_url:
                    reviews_url = item.get("url") + "/reviews"
                    reviews_response = make_request(reviews_url, token)
                    if reviews_response:
                        reviews_data = json.loads(reviews_response)
                        reviewers = list(set([review["user"]["login"] for review in reviews_data if review.get("user")]))

                github_item = GitHubItem(
                    item["title"],
                    item["html_url"],
                    description,
                    submitter,
                    tags,
                    assignees,
                    reviewers,
                    comments
                )
                items.append(github_item)
                db[str(item_id)] = github_item
        
        page += 1
    return items

# Example usage
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch GitHub issues and pull requests for a specified repository.")
    parser.add_argument("--owner", type=str, default="pytorch", help="Owner of the GitHub repository")
    parser.add_argument("--repo", type=str, default="pytorch", help="Name of the GitHub repository")
    parser.add_argument("--start_date", type=str, default=datetime.utcnow().strftime("%Y-%m-%dT00:00:00Z"), help="Start date for fetching issues and PRs (ISO format)")
    parser.add_argument("--end_date", type=str, default=datetime.utcnow().strftime("%Y-%m-%dT23:59:59Z"), help="End date for fetching issues and PRs (ISO format)")
    parser.add_argument("--db_path", type=str, default=None, help="Path to the database folder")
    args = parser.parse_args()

    if not args.db_path:
        db_path = f"{args.owner}_{args.repo}_db"
    else:
        db_path = args.db_path

    issues_url = f"https://api.github.com/repos/{args.owner}/{args.repo}/issues"
    pulls_url = f"https://api.github.com/repos/{args.owner}/{args.repo}/pulls"
    token = os.getenv("GITHUB_TOKEN")
    start_date = args.start_date
    end_date = args.end_date

    if not token:
        print("Error: GitHub token not found in environment variables.")
    else:
        with shelve.open(db_path) as db:
            print("Starting to fetch issues and pull requests...")
            issues = get_all_items(issues_url, token, start_date, end_date, db)
            pulls = get_all_items(pulls_url, token, start_date, end_date, db)

            data = issues + pulls

            print("Filtered GitHub Items:")
            for item in data:
                print(f"Title: {item.title}\nURL: {item.url}\nDescription: {item.description[:100]}...\nSubmitter: {item.submitter}\nTags: {', '.join(item.tags)}\nAssignees: {', '.join(item.assignees)}\nReviewers: {', '.join(item.reviewers)}\nComments: {len(item.comments)}")
                for comment in item.comments:
                    print(f"- Comment by {comment['author']}: {comment['body'][:100]}...")
                print()