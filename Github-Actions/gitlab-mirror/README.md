# Mirror to GitLab

GitHub Actions workflow that mirrors a GitHub repository to a self-hosted GitLab instance on every push.

Works around GitLab Community Edition's lack of paid pull mirroring by pushing from GitHub instead.

## How It Works

- Triggers on every branch push and branch deletion
- Checks out the full commit history (`fetch-depth: 0`)
- Adds your GitLab repo as a remote and force-pushes all branches and tags
- `--prune` ensures deleted branches are removed from GitLab too

## Setup

1. Copy `mirror-to-gitlab.yml` into your repo at `.github/workflows/mirror-to-gitlab.yml`
2. Add the following secrets to your GitHub repository:

| Secret | Value |
|---|---|
| `GITLAB_TOKEN` | GitLab Personal Access Token with `write_repository` scope |
| `GITLAB_REPO_URL` | GitLab repo URL **without** `https://` — e.g. `gitlab.example.com/group/repo.git` |

## Notes

- GitHub is the source of truth — GitLab is the follower
- Never commit directly to the GitLab mirror or those changes will be overwritten
- The GitLab CI/CD pipeline triggers automatically once the mirror push lands
