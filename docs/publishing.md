# Publishing this repository

The release archive can be used to create a standalone GitHub repository.

## Web workflow

1. Create a **new, empty repository** in your GitHub account (suggested name:
   `token-booster`). Choose public visibility only if you intend to share the code.
2. Do not initialize it with another README or license; both are already in this
   archive.
3. Unpack the archive. Upload the **contents** of the `token-booster` directory
   (including `.claude-plugin`, `.github` and `.gitignore`) to the repository.
4. Confirm that the test workflow appears under the Actions tab.
5. Open the README and ensure the local test commands match your setup.
6. Review the files for private data before posting the repository publicly.

## CLI workflow (if `git` and GitHub CLI are installed)

Run from the extracted `token-booster` directory:

```bash
git init
git add .
git commit -m "Initial public release"
gh auth login
gh repo create token-booster --public --source . --remote origin --push
```

Choose a repository name that is available to your account. The last command
publishes the entire tracked source tree; inspect `git status` and `git diff --cached` before pushing. You can create a private repository first, review it,
and switch visibility later.

## Reddit launch

Before linking the project publicly, verify that the repository exists and is
accessible without signing in. Replace any placeholder link in the Reddit post
with the actual repository URL.

Do not claim that synthetic byte savings are measured Claude token savings.
