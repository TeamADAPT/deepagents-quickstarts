from langchain.tools import tool
import git
import os


@tool
def git_clone(repo_url: str, target_dir: str = None) -> str:
    """Clones a git repository."""
    try:
        if target_dir is None:
            target_dir = repo_url.split("/")[-1].replace(".git", "")

        git.Repo.clone_from(repo_url, target_dir)
        return f"Successfully cloned {repo_url} to {target_dir}"
    except Exception as e:
        return f"Error cloning repo: {str(e)}"


@tool
def git_status(repo_path: str = ".") -> str:
    """Checks git status of a repository."""
    try:
        repo = git.Repo(repo_path)
        return repo.git.status()
    except Exception as e:
        return f"Error checking status: {str(e)}"


def get_git_tools():
    """Returns a list of git tools."""
    return [git_clone, git_status]
