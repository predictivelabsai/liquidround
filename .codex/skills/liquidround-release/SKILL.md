---
name: liquidround-release
description: Prepare and publish LiquidRound changes by auditing the working tree, bumping the application version, documenting the release in docs/change_log.md, validating the changed functionality, committing all intended files, and pushing the active branch. Use whenever the user asks to commit, push, publish, hand off work to another computer, or make a major LiquidRound checkpoint.
---

# LiquidRound Release

Treat every major commit or push as a versioned, documented release checkpoint.

## Release workflow

1. Work from the LiquidRound repository root.
2. Read repository guidance and inspect the full working tree, branch, remotes, and
   recent commits. Preserve secrets and ignored local state.
3. Review every tracked and untracked file before staging. Include all files only when
   the user explicitly requests everything; otherwise stage only the intended changes.
4. Read the current version from `utils/config.py`.
5. Bump the version once for the checkpoint:
   - Patch for fixes, documentation, and backward-compatible features.
   - Minor for a substantial backward-compatible capability set.
   - Major for breaking changes.
6. Update version references in current user-facing documentation when they identify the
   running release. Regenerate timestamped demo documents when the user guide changes.
7. Add a newest-first entry to `docs/change_log.md` containing:
   - Version and date
   - Concise summary
   - Added, changed, fixed, documentation, and verification details as applicable
   - Migration, compatibility, or operational notes
8. Run checks proportionate to the changed surface. For UI work, follow `SKILLS.md` and
   use Playwright at desktop and mobile sizes.
9. Run `git diff --check`, inspect the staged diff and staged file list, and confirm no
   credential or secret file is staged.
10. Commit with a concise release-oriented message.
11. Push the current branch to its configured upstream. If it has none, push with
    `--set-upstream origin <branch>`.
12. Verify the local commit matches the remote branch and report the version, commit
    hash, branch, push destination, tests, and any intentionally excluded files.

## Guardrails

- Never push `.env`, `.secrets`, credentials, tokens, or private keys.
- Never rewrite published history unless the user explicitly requests it.
- Never use destructive cleanup to make the tree look clean.
- Do not create a second version bump for retries of the same release.
- If the remote advanced, fetch and reconcile safely before pushing.
