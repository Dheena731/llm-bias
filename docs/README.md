# TIST Review Pages

This directory contains the static GitHub Pages documentation for the TIST
external-review package. It is a coordination surface, not the canonical
anonymous archive.

Canonical package state:

- Archive SHA-256: `4d843384ca2057f5ef1ca4eadb49c4cb1892148f5535aae645fef82ec429bf22`
- Package source commit: `494d4e3 Mark TIST bibliography source check complete`
- Tracking issue: <https://github.com/Dheena731/llm-bias/issues/1>
- Pages enablement issue: <https://github.com/Dheena731/llm-bias/issues/4>

The Pages workflow publishes this directory as static HTML through GitHub
Actions. The generated archive remains ignored by git and should not be
force-added.

## Publication Status

The static docs and workflow are committed, but the repository Pages setting is
not yet enabled. The latest workflow run reached `actions/configure-pages@v5`
with `enablement: true`, then failed because the GitHub Actions integration
could not create the Pages site for this private repository.

A repository admin should enable Pages with GitHub Actions as the source, then
rerun:

```bash
gh workflow run pages.yml --repo Dheena731/llm-bias --ref main
```

After deployment, confirm:

```bash
gh api repos/Dheena731/llm-bias/pages
```
