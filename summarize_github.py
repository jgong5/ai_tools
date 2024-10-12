from github import Github
from datetime import datetime
import os
import argparse
import shelve
from dotenv import load_dotenv

load_dotenv()

class GitHubItem:
    def __init__(self, title, url, description, submitter, tags, assignees, reviewers, created_at, comments, review_comments):
        self.title = title
        self.url = url
        self.description = description
        self.submitter = submitter
        self.tags = tags
        self.assignees = assignees
        self.reviewers = reviewers
        self.created_at = created_at
        self.comments = comments
        self.review_comments = review_comments

def get_all_items(repo, start_date, end_date, db):
    items = []
    start_date_dt = datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%SZ")
    end_date_dt = datetime.strptime(end_date, "%Y-%m-%dT%H:%M:%SZ")
    all_issues = repo.get_issues(state='all', since=start_date_dt)
    for item in all_issues:
        if item.created_at.replace(tzinfo=None) > end_date_dt:
            print("Reached items outside of date range. Stopping early.")
            break
        if str(item.number) in db:
            print(f"Item with ID {item.id} found in database, skipping fetch.")
            continue
        process_item(repo, item, db, items)
    return items

def get_updated_items(repo, start_date, db):
    items = []
    start_date_dt = datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%SZ")
    # Fetch issue comments
    for comment in repo.get_issues_comments(since=start_date_dt):
        item_id = comment.issue_url.split('/')[-1]
        if item_id in db:
            update_with_new_comment(db, item_id, comment, is_review=False)
            items.append(db[str(item_id)])
        else:
            item = repo.get_issue(int(item_id))
            process_item(repo, item, db, items)

    # Fetch pull request comments
    for comment in repo.get_pulls_comments(since=start_date_dt):
        item_id = comment.pull_request_url.split('/')[-1]
        if item_id in db:
            update_with_new_comment(db, item_id, comment, is_review=False)
            items.append(db[item_id])
        else:
            item = repo.get_pull(int(item_id))
            process_item(repo, item, db, items)

    # Fetch pull request review comments
    for comment in repo.get_pulls_review_comments(since=start_date_dt):
        item_id = comment.pull_request_url.split('/')[-1]
        if item_id in db:
            update_with_new_comment(db, item_id, comment, is_review=True)
            items.append(db[item_id])
        else:
            item = repo.get_pull(int(item_id))
            process_item(repo, item, db, items)

    return items

def update_with_new_comment(db, item_id, comment, is_review):
    github_item = db[item_id]
    new_comment = {
        "author": comment.user.login,
        "body": comment.body,
        "created_at": comment.created_at.isoformat()
    }
    # Check if the comment already exists
    existing_comments = github_item.review_comments if is_review else github_item.comments
    if any(c["created_at"] == new_comment["created_at"] and c["author"] == new_comment["author"] for c in existing_comments):
        print(f"Comment by {new_comment['author']} on {new_comment['created_at']} already exists, skipping.")
        return
    
    if is_review:
        github_item.review_comments.append(new_comment)
    else:
        github_item.comments.append(new_comment)
    db[item_id] = github_item

def process_item(repo, item, db, items):
    print(f"Starting to process item '{item.title}' with ID {item.number}")
    created_at = item.created_at.isoformat()
    comments = []
    review_comments = []

    # Fetch normal comments
    for comment in item.get_comments():
        print(f"Fetching comment by {comment.user.login} created at {comment.created_at.isoformat()}")
        comments.append({
            "author": comment.user.login,
            "body": comment.body,
            "created_at": comment.created_at.isoformat()
        })

    # Fetch review comments for pull requests
    if '/pull/' in item.html_url:  # To distinguish pull requests by URL pattern
        pr = repo.get_pull(item.number)
        for review_comment in pr.get_review_comments():
            print(f"Fetching review comment by {review_comment.user.login} created at {review_comment.created_at.isoformat()}")
            review_comments.append({
                "author": review_comment.user.login,
                "body": review_comment.body,
                "created_at": review_comment.created_at.isoformat()
            })

    description = item.body if item.body else "No description available"
    submitter = item.user.login if item.user else "Unknown"
    tags = [label.name for label in item.labels]
    assignees = [assignee.login for assignee in item.assignees]
    reviewers = []

    if '/pull/' in item.html_url:  # To distinguish pull requests by URL pattern
        reviewers = list(set([review.user.login for review in pr.get_reviews() if review.user]))
        print(f"Fetching reviewers for PR #{item.number}: {', '.join(reviewers)}")

    print(f"Adding or updating item '{item.title}' created by {submitter} on {created_at}")
    github_item = GitHubItem(
        item.title,
        item.html_url,
        description,
        submitter,
        tags,
        assignees,
        reviewers,
        created_at,
        comments,
        review_comments
    )
    items.append(github_item)
    db[str(item.number)] = github_item

# Example usage
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch GitHub issues and pull requests for a specified repository.")
    parser.add_argument("--owner", type=str, default="pytorch", help="Owner of the GitHub repository")
    parser.add_argument("--repo", type=str, default="pytorch", help="Name of the GitHub repository")
    parser.add_argument("--start_date", type=str, default=datetime.utcnow().strftime("%Y-%m-%d"), help="Start date for fetching issues and PRs (YYYYMMDD format)")
    parser.add_argument("--end_date", type=str, default=datetime.utcnow().strftime("%Y-%m-%d"), help="End date for fetching issues and PRs (YYYYMMDD format)")
    parser.add_argument("--db_path", type=str, default=None, help="Path to the database folder")
    args = parser.parse_args()

    if not args.db_path:
        db_path = f"{args.owner}_{args.repo}_db"
    else:
        db_path = args.db_path

    token = os.getenv("GITHUB_TOKEN")
    start_date = args.start_date + "T00:00:00Z"
    end_date = args.end_date + "T23:59:59Z"

    if not token:
        print("Error: GitHub token not found in environment variables.")
    else:
        g = Github(token)
        repo = g.get_repo(f"{args.owner}/{args.repo}")

        with shelve.open(db_path) as db:
            print("Starting to fetch issues and pull requests...")
            new_items = get_all_items(repo, start_date, end_date, db)
            updated_items = get_updated_items(repo, start_date, db)

            items = new_items + updated_items

            print("Filtered GitHub Items:")
            for item in items:
                print(f"Title: {item.title}\nURL: {item.url}\nDescription: {item.description[:100]}...\nSubmitter: {item.submitter}\nTags: {', '.join(item.tags)}\nAssignees: {', '.join(item.assignees)}\nReviewers: {', '.join(item.reviewers)}\nCreated At: {item.created_at}\nComments: {len(item.comments)}\nReview Comments: {len(item.review_comments)}")
                for comment in item.comments:
                    print(f"- Comment by {comment['author']} (Created at {comment['created_at']}): {comment['body'][:100]}...")
                for review_comment in item.review_comments:
                    print(f"- Review Comment by {review_comment['author']} (Created at {review_comment['created_at']}): {review_comment['body'][:100]}...")
                print()