### **Overall Requirements for the GitHub Summary Script**:

1. **Objective**:
   - The script should **summarize daily activity** from a specified GitHub repository.
   - It should collect data for **both Issues and Pull Requests** (PRs) based on a given **time range** (`start_date` and `end_date`).

2. **GitHub Token Handling**:
   - Use a **GitHub personal access token** to authenticate with the GitHub API.
   - The token should be **loaded from an `.env` file** using the `dotenv` library for better security and convenience.

3. **Data Retrieval from GitHub**:
   - The script should be able to **fetch both Issues and PRs** from a specified GitHub repository.
   - It should utilize the **GitHub REST API**.
   - **Pagination Handling**:
     - The script should support pagination, iterating through **all pages** to retrieve **all items** (`per_page=100`).
     - It should **stop early** if it encounters items **outside the specified date range**, reducing unnecessary API requests.

4. **GitHub Item Creation**:
   - A class named `GitHubItem` should be used to **store the information** about each issue or PR.
   - Each `GitHubItem` should include:
     - **Title**: The title of the issue or PR.
     - **URL**: The URL link to the issue or PR.
     - **Description**: The body content of the issue or PR. If it is not available, set it as "No description available".
     - **Comments**: All comments associated with the issue or PR.

5. **Populating Comments**:
   - The script should **fetch all comments** for each issue or PR.
   - Use the `comments_url` field to get comments and **store each comment's body** in the corresponding `GitHubItem`.

6. **Filtering and Processing Data**:
   - The filtering for issues and PRs by their **creation date** should be handled **while populating the items** (`get_all_items` function).
   - This ensures that only relevant items within the specified date range are processed further.

7. **Debugging and Logging**:
   - Add print/logging statements throughout the script to aid in debugging:
     - Log the **URL requests** and **status codes**.
     - Log the **creation date** of each item, the **addition of items**, and the **retrieval of comments**.
     - Log messages when the script **stops fetching** due to reaching items outside of the specified date range.

8. **Output**:
   - The script should **print a summary** of the filtered GitHub items, including:
     - **Title**.
     - **URL**.
     - **Description** (first 100 characters).
     - **Number of comments**.

### **Workflow**:

1. **Load Configuration**: Load GitHub token from an `.env` file.
2. **Fetch Issues and PRs**:
   - Retrieve issues and PRs using pagination.
   - Stop fetching if items are outside of the given date range.
3. **Filter and Create Items**:
   - Create `GitHubItem` instances for each valid issue/PR.
   - Populate the attributes, including fetching and storing comments.
4. **Print Results**:
   - Display the summary of each GitHub item, including the number of comments.

This script ensures efficient GitHub data retrieval, comprehensive data storage in custom objects, and easy debugging and output for summarizing the activity within the specified repository.