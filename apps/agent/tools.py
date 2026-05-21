import requests


def list_github_files(repo_url: str, path: str = "") -> str:
    """Tool to list files in a GitHub repository."""
    parts = repo_url.rstrip('/').split('/')
    if len(parts) < 2: return "Invalid URL"
    owner_repo = f"{parts[-2]}/{parts[-1]}"
    
    api_url = f"https://api.github.com/repos/{owner_repo}/git/trees/main?recursive=1"
    response = requests.get(api_url)
    if response.status_code == 200:
        paths = [item['path'] for item in response.json().get('tree', []) if item['type'] == 'blob']
        return "\n".join(paths[:100]) # Return first 100 to save tokens
    return "Failed to fetch files."


def read_github_file(repo_url: str, file_path: str) -> str:
    """Tool to read the exact text/code content of a specific file in the repository."""
    parts = repo_url.rstrip('/').split('/')
    owner_repo = f"{parts[-2]}/{parts[-1]}"
    
    # Use raw.githubusercontent to get the actual text
    raw_url = f"https://raw.githubusercontent.com/{owner_repo}/main/{file_path}"
    response = requests.get(raw_url)
    if response.status_code == 200:
        return response.text[:5000] # Limit file size to prevent token overflow
    return f"Failed to read file: {file_path}. Ensure the path is correct."


def get_previous_findings(repo_url: str) -> str:
    """Tool to search the database for previous research sessions on this repository."""
    from .models import ResearchSession # Local import to prevent circular dependency
    
    sessions = ResearchSession.objects.filter(repository__url=repo_url).exclude(final_answer__isnull=True)[:3]
    if not sessions.exists():
        return "No previous research found for this repository."
    
    memory = []
    for s in sessions:
        memory.append(f"Previous Question: {s.question}\nPrevious Answer: {s.final_answer}")
    return "\n\n".join(memory)


# The dictionary of tools to pass to the agent
AGENT_TOOLS = {
    "list_github_files": list_github_files,
    "read_github_file": read_github_file,
    "get_previous_findings": get_previous_findings
}
