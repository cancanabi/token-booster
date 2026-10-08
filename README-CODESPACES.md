# Offline testing in GitHub Codespaces

A small Codespace can run the project without installing Claude Code. Usage is
subject to your GitHub account's current included hours and billing settings.

Upload the release archive to a blank Codespace, then run:

```bash
unzip -q token-booster-github-ready.zip
cd token-booster
bash scripts/test_v5.sh
```

Alternatively, clone a published repository and run the test script from its
root directory. These checks exercise the local Python implementation, not an
authenticated Claude Code installation.
