#!/bin/python3
import subprocess
import requests
from collections import defaultdict

def run_command(command):
    try:
        result = subprocess.run(command, shell=True, check=True, 
stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.stdout.decode('utf-8').strip(), None
    except subprocess.CalledProcessError as e:
        return None, e.stderr.decode('utf-8').strip()

def get_and_remove_duplicate_branches(owner, repo, oauth_token):
    base_url = f"https://api.github.com/repos/{owner}/{repo}/forks"
    headers = {'Authorization': f'token {oauth_token}'}
    params = {'per_page': 100}
    session = requests.Session()
    session.headers.update(headers)

    # Dictionary to keep track of branches and their latest commit hash
    branch_hashes = defaultdict(list)

    response = session.get(base_url, params=params)
    while True:
        if response.status_code == 200:
            forks = response.json()
            for fork in forks:
                fork_owner = fork['owner']['login']
                remote_name = fork_owner.replace('.', '_')

                # Add remote for the fork
                _, error = run_command(f"git remote add {remote_name} 
{fork['clone_url']}")
                if error:
                    print(f"Error adding remote {remote_name}: {error}")
                    continue

                # Fetch all branches from the remote
                _, error = run_command(f"git fetch {remote_name}")
                if error:
                    print(f"Error fetching branches from {remote_name}: 
{error}")
                    continue

                # Get all branch names from the remote
                stdout, error = run_command(f"git branch -r | grep 
{remote_name}")
                if error:
                    print(f"Error listing branches for {remote_name}: 
{error}")
                    continue

                # Check out each branch and get the latest commit hash
                for remote_branch in stdout.split('\n'):
                    local_branch = 
remote_branch.replace(f"{remote_name}/", "")
                    _, error = run_command(f"git checkout -b 
{local_branch} {remote_branch}")
                    if error:
                        print(f"Error checking out {local_branch}: 
{error}")
                        continue

                    # Get the latest commit hash of the branch
                    commit_hash, error = run_command(f"git rev-parse 
{local_branch}")
                    if error:
                        print(f"Error getting latest commit hash for 
{local_branch}: {error}")
                        continue

                    # Add the branch to the list of branches that have the 
same commit hash
                    branch_hashes[commit_hash].append((local_branch, 
remote_name))

            # Pagination check
            if 'next' in response.links:
                base_url = response.links['next']['url']
                response = session.get(base_url)
            else:
                break
        else:
            print(f"Failed to retrieve forks: {response.status_code}")
            break

    # Remove duplicate branches, keeping one copy of each
    for branches in branch_hashes.values():
        if len(branches) > 1:
            # Keep the first branch, remove the rest
            for local_branch, remote_name in branches[1:]:
                _, error = run_command(f"git branch -D {local_branch}")
                if error:
                    print(f"Error deleting duplicate branch 
{local_branch}: {error}")
                    continue
                
                _, error = run_command(f"git remote remove {remote_name}")
                if error:
                    print(f"Error removing remote {remote_name}: {error}")

# Example usage:
# get_and_remove_duplicate_branches('owner', 'repo', 'your_oauth_token')

