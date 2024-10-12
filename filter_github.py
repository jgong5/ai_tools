import argparse
import shelve
from datetime import datetime

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

def load_db(db_path):
    """
    Load the GitHub items from the database.
    """
    with shelve.open(db_path) as db:
        items = list(db.values())
    return items

def filter_items(items, rules):
    """
    Apply filtering rules to the list of GitHub items.
    """
    filtered_items = []
    for item in items:
        if apply_rules(item, rules):
            filtered_items.append(item)
    return filtered_items

def apply_rules(item, rules):
    """
    Check if a GitHub item satisfies the given filtering rules.
    """
    # Rule 1: Filter by start and end dates
    created_at = datetime.fromisoformat(item.created_at.replace('Z', '+00:00')).replace(tzinfo=None)
    comment_dates = [datetime.fromisoformat(comment['created_at'].replace('Z', '+00:00')).replace(tzinfo=None) for comment in item.comments + item.review_comments]
    all_dates = [created_at] + comment_dates
    if not any(rules['start_date'] <= date <= rules['end_date'] for date in all_dates):
        print(f"Filtering out '{item.title}' because neither its creation time nor any comment time is within the date range. Start date: {rules['start_date']}, End date: {rules['end_date']}, Created at: {created_at}")
        return False

    # Rule 2: Comments containing tags of the specified user
    specified_user = rules.get('specified_user', '')
    if specified_user and not any(specified_user in comment['body'] for comment in item.comments + item.review_comments):
        print(f"Filtering out '{item.title}' because it does not contain a comment tagging the user '{specified_user}'.")
        return False

    # Rule 3: Ignore titles starting with "DISABLED"
    if item.title.startswith("DISABLED"):
        print(f"Filtering out '{item.title}' because the title starts with 'DISABLED'.")
        return False

    # Rule 4: Ignore comments tagging or created by specific bots
    ignored_authors = {"pytorchmergebot", "pytorch-bot", "facebook-github-bot"}
    item.comments = [comment for comment in item.comments if comment['author'] not in ignored_authors]
    item.review_comments = [review_comment for review_comment in item.review_comments if review_comment['author'] not in ignored_authors]

    # Rule 5: Filter out items if all comments within the specified date range are created by ignored authors
    filtered_comments = [comment for comment, date in zip(item.comments + item.review_comments, comment_dates) if rules['start_date'] <= date <= rules['end_date']]
    if any(comment['author'] in ignored_authors for comment in filtered_comments):
        print(f"Filtering out '{item.title}' because all comments within the specified date range are created by ignored authors.")
        return False

    return True

def print_items(items):
    """
    Print the filtered GitHub items to stdout.
    """
    for item in items:
        print(f"Title: {item.title}\nURL: {item.url}\nDescription: {item.description[:100]}...\nSubmitter: {item.submitter}\nTags: {', '.join(item.tags)}\nAssignees: {', '.join(item.assignees)}\nReviewers: {', '.join(item.reviewers)}\nCreated At: {item.created_at}\nComments: {len(item.comments)}\nReview Comments: {len(item.review_comments)}")
        for comment in item.comments:
            print(f"- Comment by {comment['author']} (Created at {comment['created_at']}): {comment['body'][:100]}...")
        for review_comment in item.review_comments:
            print(f"- Review Comment by {review_comment['author']} (Created at {review_comment['created_at']}): {review_comment['body'][:100]}...")
        print()

def main():
    parser = argparse.ArgumentParser(description="Filter and display GitHub items from a database.")
    parser.add_argument("--owner", type=str, default="pytorch", help="Owner of the GitHub repository")
    parser.add_argument("--repo", type=str, default="pytorch", help="Name of the GitHub repository")
    parser.add_argument("--db_path", type=str, default=None, help="Path to the database folder")
    parser.add_argument("--start_date", type=str, default=datetime.utcnow().strftime("%Y-%m-%d"), help="Start date for filtering (YYYYMMDD format)")
    parser.add_argument("--end_date", type=str, default=datetime.utcnow().strftime("%Y-%m-%d"), help="End date for filtering (YYYYMMDD format)")
    parser.add_argument("--specified_user", type=str, default="", help="User to look for in comments (default: no filtering)")
    args = parser.parse_args()

    if not args.db_path:
        db_path = f"{args.owner}_{args.repo}_db"
    else:
        db_path = args.db_path

    # Parse start and end dates
    start_date = datetime.strptime(args.start_date + "T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=None)
    end_date = datetime.strptime(args.end_date + "T23:59:59Z", "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=None)

    # Load items from the database
    items = load_db(db_path)

    # Define filtering rules
    rules = {
        'start_date': start_date,
        'end_date': end_date,
        'specified_user': args.specified_user
    }

    # Filter items according to the rules
    filtered_items = filter_items(items, rules)

    # Print filtered items
    print_items(filtered_items)

if __name__ == "__main__":
    main()