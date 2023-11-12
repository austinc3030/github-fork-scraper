#!python3

import subprocess
import requests
import sys
import os
from collections import defaultdict


def run_command(command):
    try:
        result = subprocess.run(
            command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.stdout.decode('utf-8').strip(), None
    except subprocess.CalledProcessError as e:
        return None, e.stderr.decode('utf-8').strip()


def get_oauth_token():
    home_dir = os.path.expanduser('~')
    token_file_path = os.path.join(home_dir, '.github_oauth_token')
    try:
        with open(token_file_path, 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        print(f"OAuth token file not found in {token_file_path}")
        sys.exit(1)


def get_github_username(oauth_token):
    headers = {'Authorization': f'token {oauth_token}'}
    response = requests.get("https://api.github.com/user", headers=headers)
    if response.status_code == 200:
        return response.json().get('login')
    else:
        print(f"Failed to retrieve GitHub username: {response.status_code}")
        sys.exit(1)


def create_or_update_origin_branch(local_branch):
    _, error = run_command(f"git push -u origin {local_branch}")
    if error:
        print(
            f"Error creating or updating origin branch {local_branch}: {error}")


def process_forks(base_url, session, my_username, branch_hashes, owner, repo):
    response = session.get(base_url)
    while response.status_code == 200:
        forks = response.json()
        for fork in forks:
            fork_owner = fork['owner']['login']
            if fork_owner == my_username:
                continue

            remote_name = fork_owner.replace('.', '_')

            _, error = run_command(
                f"git remote add {remote_name} {fork['clone_url']}")
            if error:
                print(f"Error adding remote {remote_name}: {error}")
                continue

            _, error = run_command(f"git fetch {remote_name}")
            if error:
                print(f"Error fetching branches from {remote_name}: {error}")
                continue

            stdout, error = run_command(f"git branch -r | grep {remote_name}")
            if error:
                print(f"Error listing branches for {remote_name}: {error}")
                continue

            for remote_branch in stdout.split('\n'):
                # local_branch = remote_branch.replace(f"{remote_name}/", "")
                local_branch = remote_branch
                _, error = run_command(
                    f"git checkout -b {local_branch} {remote_branch}")
                if error:
                    print(f"Error checking out {local_branch}: {error}")
                    continue

                commit_hash, error = run_command(
                    f"git rev-parse {local_branch}")
                if error:
                    print(
                        f"Error getting latest commit hash for {local_branch}: {error}")
                    continue

                branch_hashes[commit_hash].append((local_branch, remote_name))

                # Set the upstream branch to your repository's origin
                create_or_update_origin_branch(local_branch)

            # Recursively process forks of this fork
            next_forks_url = fork['forks_url']
            process_forks(next_forks_url, session, my_username,
                          branch_hashes, owner, repo)

        if 'next' in response.links:
            response = session.get(response.links['next']['url'])
        else:
            break


def get_and_remove_duplicate_branches(github_url):
    oauth_token = get_oauth_token()
    my_username = get_github_username(oauth_token)

    owner_repo = github_url[len("https://github.com/"):]
    owner, repo = owner_repo.split('/')

    base_url = f"https://api.github.com/repos/{owner}/{repo}/forks"
    headers = {'Authorization': f'token {oauth_token}'}
    session = requests.Session()
    session.headers.update(headers)

    branch_hashes = defaultdict(list)

    process_forks(base_url, session, my_username, branch_hashes, owner, repo)

    for branches in branch_hashes.values():
        if len(branches) > 1:
            for local_branch, remote_name in branches[1:]:
                _, error = run_command(f"git branch -D {local_branch}")
                if error:
                    print(
                        f"Error deleting duplicate branch {local_branch}: {error}")
                    continue

                _, error = run_command(f"git remote remove {remote_name}")
                if error:
                    print(f"Error removing remote {remote_name}: {error}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script_name.py <GitHub URL>")
        sys.exit(1)
    else:
        github_url = sys.argv[1]
        get_and_remove_duplicate_branches(github_url)
