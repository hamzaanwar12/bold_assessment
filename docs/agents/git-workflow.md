# Git workflow: one ticket → one worktree → one PR

How changes land in this repo. Agents and humans follow the same loop.

## Branch names

`<type>/<NN>-<slug>`, where `NN` is the ticket number in
`.scratch/<feature>/issues/` when there is one.

| Type | Use |
|---|---|
| `feat/` | new behaviour |
| `fix/` | defect or review follow-up |
| `test/` | test-only changes |
| `docs/` | documentation-only changes |
| `chore/` | tooling or dependencies |

Examples: `feat/06-import-endpoint`, `test/09-test-matrix`, `feat/ui-motion`.

## The loop

```bash
# 1. Isolated checkout per ticket: parallel tickets never share a working tree
git worktree add ../bold_assessment.wt/06-import-endpoint -b feat/06-import-endpoint main
cd ../bold_assessment.wt/06-import-endpoint

# 2. Work in small commits. Tests and docs land in the SAME branch as the code.

# 3. Gate before pushing
(cd backend && uv run pytest)                                  # backend changes
(cd frontend && npm run lint && npm test && npm run build)    # frontend changes

# 4. Open the PR
git push -u origin feat/06-import-endpoint
gh pr create --base main --title "..." --body-file pr.md

# 5. Merge with a merge commit (keeps per-ticket history visible), then clean up
gh pr merge --merge --delete-branch
cd - && git worktree remove ../bold_assessment.wt/06-import-endpoint
git switch main && git pull
```

Each worktree needs its own `npm install` / `uv sync`, because `node_modules` and
`.venv` are per checkout.

## Running tickets in parallel

Tickets whose `Blocked by:` lines are all resolved can run at the same time, each
in its own worktree, for example 02 ∥ 04 and 03 ∥ 05 in this feature. If a later
ticket needs an unmerged sibling, merge `main` into it after the sibling lands.
Don't merge sibling branches into each other.

## PR body checklist

- **What / why**: link the ticket file.
- **Test evidence**: the command run and its pass count.
- **Docs touched**: README, NOTES, ADR, GLOSSARY, or "none" plus the reason.
- **Behaviour change**: yes or no. For UI PRs, include screenshots at 375 / 1440 px.
