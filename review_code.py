import requests
from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
# Set your OpenAI API key
client = OpenAI()

def get_pr_details(pr_url):
    headers = {
        'Authorization': f'token {os.getenv("GITHUB_TOKEN")}',
        'Accept': 'application/vnd.github.dif'
    }
    response = requests.get(pr_url, headers=headers)
    
    if response.status_code == 200:
        return response.json()  # Parse and return the JSON content as a dictionary
    else:
        raise Exception(f"Failed to fetch PR details: {response.status_code} {response.text}")

def get_code_changes(base_url, base_sha, head_sha):
    headers = {
        'Authorization': f'token {os.getenv("GITHUB_TOKEN")}',
        'Accept': 'application/vnd.github.v3.diff'
    }
    response = requests.get(f"{base_url}/compare/{base_sha}...{head_sha}", headers=headers)
    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"Failed to fetch code changes: {response.status_code} {response.text}")

def analyze_code_with_chatgpt(code_diff):
    # Read system prompt from review_prompt.txt file
    with open('review_prompt.txt', 'r') as file:
        system_prompt = file.read()
        
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # The appropriate model you are subscribed to
        messages=[
            {
                "role": "system", 
                "content": system_prompt
            },
            {
                "role": "user", 
                "content": f"{code_diff}"
            },
        ],
        max_tokens=2048
    )
    return response.choices[0].message.content.strip()

def post_feedback_to_github(pr_url, feedback):
    # Extract the repo and pull number from the PR URL
    parts = pr_url.split('/')
    repo = parts[4] + '/' + parts[5]
    pull_number = parts[7]

    pr_comments_url = f"https://api.github.com/repos/{repo}/issues/{pull_number}/comments"
    response = requests.post(pr_comments_url, json={
        "body": feedback
    }, headers={
        'Authorization': f'token {os.getenv("GITHUB_TOKEN")}',
        'Content-Type': 'application/json'
    })

    try:
        response.raise_for_status()
        print("Successfully posted feedback to GitHub.")
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except requests.exceptions.RequestException as err:
        print(f"Other error occurred: {err}")

def main(pr_url):
    pr_details = get_pr_details(pr_url)
    base_sha = pr_details['base']['sha']
    head_sha = pr_details['head']['sha']
    repo_url = pr_details['base']['repo']['url']

    # Get the code changes between the base and head commit
    code_diff = get_code_changes(repo_url, base_sha, head_sha)
    feedback = analyze_code_with_chatgpt(code_diff)
    post_feedback_to_github(pr_url, feedback)

if __name__ == "__main__":
    import sys
    main(sys.argv[1])