from github import Github
from datetime import datetime
import os
import argparse
import shelve
import logging
from dotenv import load_dotenv
import openai
import nltk
import tiktoken

load_dotenv()

logger = logging.getLogger(__name__)

class GitHubItem:
    def __init__(self, title, url, description, submitter, tags, assignees, reviewers, created_at, comments, review_comments, state):
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
        self.state = state

def count_tokens(text, encoding_name='gpt2'):
    """
    Counts the number of tokens in a text string using the specified encoding.
    """
    logger.info(f"Counting tokens for text: {text[:50]}...")
    encoding = tiktoken.get_encoding(encoding_name)
    tokens = encoding.encode(text)
    logger.info(f"Token count: {len(tokens)}")
    return len(tokens)

def split_text_into_chunks(text, max_tokens, overlap_tokens):
    """
    Splits text into chunks of approximately max_tokens tokens, with overlap.
    """
    logger.info("Splitting text into chunks...")
    nltk.download('punkt', quiet=True)
    sentences = nltk.sent_tokenize(text)
    chunks = []
    current_chunk = ''
    current_tokens = 0
    overlap = []
    overlap_token_count = 0

    for sentence in sentences:
        token_count = count_tokens(sentence)
        if current_tokens + token_count <= max_tokens:
            current_chunk += ' ' + sentence
            current_tokens += token_count
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
                logger.info(f"Created chunk of length {current_tokens} tokens.")
            current_chunk = ' '.join(overlap) + ' ' + sentence
            current_tokens = overlap_token_count + token_count
            overlap = []

        # Maintain overlap
        overlap.append(sentence)
        overlap_token_count = count_tokens(' '.join(overlap))
        while overlap_token_count > overlap_tokens:
            overlap.pop(0)
            overlap_token_count = count_tokens(' '.join(overlap))

    if current_chunk:
        chunks.append(current_chunk.strip())
        logger.info(f"Created final chunk of length {current_tokens} tokens.")

    logger.info(f"Total number of chunks: {len(chunks)}")
    return chunks

def summarize_chunk(client, chunk, prompt_instructions="", max_summary_tokens=None):
    """
    Summarizes a text chunk using OpenAI's GPT-3.5 Turbo model.
    """
    logger.info(f"Summarizing chunk: {chunk[:50]}...")
    prompt = f"{prompt_instructions}\n\nText:\n{chunk}\n\n"
    try:
        response = client.ChatCompletion.create(
            model='gpt-3.5-turbo',
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=max_summary_tokens,
            temperature=0.7,
        )
        summary = response['choices'][0]['message']['content'].strip()
        logger.info(f"Summary generated: {summary[:50]}...")
        return summary
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return ""

def summarize_text(text, max_chunk_tokens=2000, overlap_tokens=200, max_summary_tokens=200, prompt_instructions="Please provide a concise summary of the following text."):
    """
    Summarizes the given text using chunk-based summarization with overlap.
    """
    client = openai
    client.api_key = os.getenv('OPENAI_API_KEY')

    chunks = split_text_into_chunks(text, max_chunk_tokens, overlap_tokens)
    summaries = []
    for i, chunk in enumerate(chunks):
        logger.info(f"Summarizing chunk {i + 1}/{len(chunks)}...")
        summary = summarize_chunk(client, chunk, prompt_instructions, max_summary_tokens)
        summaries.append(summary)

    combined_summary = ' '.join(summaries)
    logger.info("Combined all chunk summaries.")
    return combined_summary

def refresh_items(repo, start_date, end_date, db):
    start_date_dt = datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%SZ")
    end_date_dt = datetime.strptime(end_date, "%Y-%m-%dT%H:%M:%SZ")
    all_issues = repo.get_issues(state='all', since=start_date_dt)
    for item in all_issues:
        if item.created_at.replace(tzinfo=None) > end_date_dt:
            logger.info("Reached items outside of date range. Stopping early.")
            break
        if str(item.number) in db:
            logger.info(f"Item with ID {item.id} found in database, updating fields except comments.")
            github_item = db[str(item.number)]
            github_item.title = item.title
            github_item.description = item.body if item.body else "No description available"
            github_item.tags = [label.name for label in item.labels]
            github_item.assignees = [assignee.login for assignee in item.assignees]
            github_item.reviewers = []
            github_item.state = item.state
            # commented out for efficiency
            # if '/pull/' in item.html_url:  # To distinguish pull requests by URL pattern
            #     pr = repo.get_pull(item.number)
            #     github_item.reviewers = list(set([review.user.login for review in pr.get_reviews() if review.user]))
            db[str(item.number)] = github_item
            continue
        process_item(repo, item, db)

def refresh_item_comments(repo, start_date, db):
    start_date_dt = datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%SZ")
    # Fetch issue comments
    for comment in repo.get_issues_comments(since=start_date_dt):
        item_id = comment.issue_url.split('/')[-1]
        if item_id in db:
            update_with_new_comment(db, item_id, comment, is_review=False)
        else:
            item = repo.get_issue(int(item_id))
            process_item(repo, item, db)

    # Fetch pull request comments
    for comment in repo.get_pulls_comments(since=start_date_dt):
        item_id = comment.pull_request_url.split('/')[-1]
        if item_id in db:
            update_with_new_comment(db, item_id, comment, is_review=False)
        else:
            item = repo.get_pull(int(item_id))
            process_item(repo, item, db)

    # Fetch pull request review comments
    for comment in repo.get_pulls_review_comments(since=start_date_dt):
        item_id = comment.pull_request_url.split('/')[-1]
        if item_id in db:
            update_with_new_comment(db, item_id, comment, is_review=True)
        else:
            item = repo.get_pull(int(item_id))
            process_item(repo, item, db)

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
        logger.info(f"Comment by {new_comment['author']} on {new_comment['created_at']} already exists, skipping.")
        return

    if is_review:
        github_item.review_comments.append(new_comment)
    else:
        github_item.comments.append(new_comment)
    db[item_id] = github_item

def process_item(repo, item, db):
    logger.info(f"Starting to process item '{item.title}' with ID {item.number}")
    created_at = item.created_at.isoformat()
    comments = []
    review_comments = []

    # Fetch normal comments
    for comment in item.get_comments():
        logger.info(f"Fetching comment by {comment.user.login} created at {comment.created_at.isoformat()}")
        comments.append({
            "author": comment.user.login,
            "body": comment.body,
            "created_at": comment.created_at.isoformat()
        })

    # Fetch review comments for pull requests
    if '/pull/' in item.html_url:  # To distinguish pull requests by URL pattern
        pr = repo.get_pull(item.number)
        for review_comment in pr.get_review_comments():
            logger.info(f"Fetching review comment by {review_comment.user.login} created at {review_comment.created_at.isoformat()}")
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
    state = item.state

    if '/pull/' in item.html_url:  # To distinguish pull requests by URL pattern
        reviewers = list(set([review.user.login for review in pr.get_reviews() if review.user]))
        logger.info(f"Fetching reviewers for PR #{item.number}: {', '.join(reviewers)}")

    logger.info(f"Adding or updating item '{item.title}' created by {submitter} on {created_at}")
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
        review_comments,
        state
    )
    db[str(item.number)] = github_item

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
        logger.info(f"Filtering out '{item.title}' because neither its creation time nor any comment time is within the date range.")
        return False

    # Rule 2: Comments containing tags of the specified user
    specified_user = rules.get('specified_user', '')
    if specified_user and not any(specified_user in comment['body'] for comment in item.comments + item.review_comments):
        logger.info(f"Filtering out '{item.title}' because it does not contain a comment tagging the user '{specified_user}'.")
        return False

    # Rule 3: Ignore titles starting with "DISABLED"
    if item.title.startswith("DISABLED"):
        logger.info(f"Filtering out '{item.title}' because the title starts with 'DISABLED'.")
        return False

    # Rule 4: Ignore comments tagging or created by specific bots
    ignored_authors = {"pytorchmergebot", "pytorch-bot[bot]", "facebook-github-bot"}
    item.comments = [comment for comment in item.comments if comment['author'] not in ignored_authors]
    item.review_comments = [review_comment for review_comment in item.review_comments if review_comment['author'] not in ignored_authors]

    # Rule 5: Filter out items if all comments within the specified date range are created by ignored authors
    filtered_comments = [comment for comment in item.comments + item.review_comments if rules['start_date'] <= datetime.fromisoformat(comment['created_at'].replace('Z', '+00:00')).replace(tzinfo=None) <= rules['end_date']]
    if filtered_comments and all(comment['author'] in ignored_authors for comment in filtered_comments):
        logger.info(f"Filtering out '{item.title}' because all comments within the specified date range are created by ignored authors.")
        return False

    return True

def print_items(items, dump_comments=False):
    """
    Print the filtered GitHub items to stdout.
    """
    for item in items:
        print(f"Title: {item.title}\nURL: {item.url}\nDescription: {item.description}\nSubmitter: {item.submitter}\nTags: {', '.join(item.tags)}\nAssignees: {', '.join(item.assignees)}\nReviewers: {', '.join(item.reviewers)}\nCreated At: {item.created_at}\nState: {item.state}\nComments: {len(item.comments)}\nReview Comments: {len(item.review_comments)}")
        if dump_comments:
            for comment in item.comments:
                print(f"- Comment by {comment['author']} (Created at {comment['created_at']}): {comment['body']}")
            for review_comment in item.review_comments:
                print(f"- Review Comment by {review_comment['author']} (Created at {review_comment['created_at']}): {review_comment['body']}")
        print()

def main():
    parser = argparse.ArgumentParser(description="Fetch, filter, and display GitHub issues and pull requests for a specified repository.")
    parser.add_argument("--owner", type=str, default="pytorch", help="Owner of the GitHub repository")
    parser.add_argument("--repo", type=str, default="pytorch", help="Name of the GitHub repository")
    parser.add_argument("--start-date", type=str, default=datetime.utcnow().strftime("%Y-%m-%d"), help="Start date for fetching and filtering issues and PRs (YYYY-MM-DD format)")
    parser.add_argument("--end-date", type=str, default=datetime.utcnow().strftime("%Y-%m-%d"), help="End date for fetching and filtering issues and PRs (YYYY-MM-DD format)")
    parser.add_argument("--db-path", type=str, default=None, help="Path to the database folder")
    parser.add_argument("--specified-user", type=str, default="", help="User to look for in comments (default: no filtering)")
    parser.add_argument("--log-level", type=str, default="WARNING", help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    parser.add_argument("--retrieve-only", action="store_true", help="Retrieve data only without filtering or dumping information")
    parser.add_argument("--dump-comments", action="store_true", help="Dump detailed comments and review comments for each item")
    parser.add_argument("--only-issues", action="store_true", help="Dump only issues (default: dump both issues and PRs)")
    parser.add_argument("--only-prs", action="store_true", help="Dump only pull requests (default: dump both issues and PRs)")
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.WARNING), format='%(asctime)s - %(levelname)s - %(message)s')

    if not args.db_path:
        db_path = f"{args.owner}_{args.repo}_db"
    else:
        db_path = args.db_path

    token = os.getenv("GITHUB_TOKEN")
    start_date = args.start_date + "T00:00:00Z"
    end_date = args.end_date + "T23:59:59Z"

    # Parse start and end dates for filtering
    filter_start_date = datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=None)
    filter_end_date = datetime.strptime(end_date, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=None)

    if not token:
        logger.error("Error: GitHub token not found in environment variables.")
    else:
        g = Github(token)
        repo = g.get_repo(f"{args.owner}/{args.repo}")

        with shelve.open(db_path) as db:
            logger.info("Starting to fetch issues and pull requests...")
            refresh_items(repo, start_date, end_date, db)
            refresh_item_comments(repo, start_date, db)

            # Load items from the database
            items = list(db.values())

        if not args.retrieve_only:
            # Define filtering rules
            rules = {
                'start_date': filter_start_date,
                'end_date': filter_end_date,
                'specified_user': args.specified_user
            }

            # Apply PR or issue only filters
            if args.only_issues:
                items = [item for item in items if '/pull/' not in item.url]
            elif args.only_prs:
                items = [item for item in items if '/pull/' in item.url]

            # Filter items according to the rules
            filtered_items = filter_items(items, rules)

            # Print filtered items
            logger.info("Filtered GitHub Items:")
            print_items(filtered_items, dump_comments=args.dump_comments)

if __name__ == "__main__":
    main()