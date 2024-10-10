### **Overall Requirements for the GitHub Summary Script**:

1. **Objective**:
   - The script should **summarize daily activity** from a specified GitHub repository.
   - It should collect data for **both Issues and Pull Requests (PRs)** within a given **time range** (`start_date` and `end_date`).

2. **GitHub Token Handling**:
   - Use a **GitHub personal access token** to authenticate with the GitHub API.
   - The token should be **loaded from an `.env` file** using the `dotenv` library for better security and convenience.

3. **Data Retrieval from GitHub**:
   - The script should **fetch issues and pull requests** from a specified GitHub repository using the GitHub API.
   - Handle **pagination** to retrieve **all items**, with up to 100 items per page.
   - **Stop early** if items are found outside the specified date range, reducing unnecessary API requests.

4. **Use of Database**:
   - A **file-based database** (`shelve`) should be used to store previously fetched items to avoid redundant API calls.
   - The database path can be specified via command line, and it defaults to `{args.owner}_{args.repo}_db`.
   - The script should **reuse previously fetched data** (e.g., comments) if they are already available in the database.

5. **GitHub Item Details**:
   - Each `GitHubItem` object should store:
     - **Title**: The title of the issue or PR.
     - **URL**: The link to the GitHub item.
     - **Description**: Use the `body` field if available, otherwise set it as "No description available".
     - **Submitter**: The author of the issue or PR.
     - **Tags**: The labels associated with the issue or PR.
     - **Assignees**: The users assigned to the issue or PR.
     - **Reviewers**: (For PRs only) The list of reviewers.
     - **Comments**: Include each comment's **body** and the **author**.

6. **Fetching Additional Information**:
   - **Comments**: Use the `comments_url` to fetch all comments for each issue or PR. Each comment should include:
     - **Author**: The username of the person who made the comment.
     - **Body**: The content of the comment.
   - **Reviewers** (For PRs only):
     - Use the `reviews` endpoint to fetch the list of reviewers for each PR.

7. **Debugging and Logging**:
   - Add print/logging statements to track:
     - URLs being requested.
     - Status codes of responses.
     - Important events, such as adding items, skipping items found in the database, and retrieving comments or reviewers.

8. **Command Line Arguments**:
   - **`--owner`**: GitHub repository owner (default: `"pytorch"`).
   - **`--repo`**: GitHub repository name (default: `"pytorch"`).
   - **`--start_date`**: Start date for fetching issues and PRs in ISO format (default: `"today"`).
   - **`--end_date`**: End date for fetching issues and PRs in ISO format (default: `"today"`).
   - **`--db_path`**: Path to the database folder (defaults to `{args.owner}_{args.repo}_db`).

9. **Output**:
   - Print a summary of the retrieved GitHub items, including:
     - **Title**, **URL**, **description (truncated)**, **submitter**, **tags**, **assignees**, **reviewers**, and **comments**.
     - Each comment should display its **author** and the first 100 characters of its **body**.

### **Workflow**:

1. **Load Configuration**: Load GitHub token from an `.env` file and parse command line arguments.
2. **Fetch Issues and PRs**:
   - Retrieve issues and PRs using pagination, avoiding redundant API requests by using a database.
   - Store and reuse previously fetched data from a local database.
3. **Populate GitHub Items**:
   - Create `GitHubItem` instances for each valid issue/PR and populate all attributes, including comments and reviewers.
4. **Print Results**:
   - Display the summary of each GitHub item, including all required details.
