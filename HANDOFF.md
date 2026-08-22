# Handoff: Trashbyrd's UEFN Power Tools

## What this repo is

An MCP server plus Python tools for live, chat-driven inspection and editing
of a UEFN (Unreal Editor for Fortnite) project, Verse, and assets. Public,
MIT licensed: `github.com/Corsair-Studios/trashbyrds-uefn-power-tools`.

## THIS REPO IS THE SOURCE OF TRUTH

Read this before touching anything else. This repo was previously
**developed inside a different project (TycoonAgents)** and mirrored out by
a sync script. That mirror was retired on 2026-08-21.

Git history still contains commits titled `Sync 0.1.0` / `Sync 0.1.1` from
that era, and some docs may still claim the repo is "generated ... and must
not be edited directly." **That is no longer true and is now exactly
backwards.** Edit here. Nothing upstream regenerates this repo. If you find
leftover language claiming otherwise, it's stale — don't follow it.

## Relationship to TycoonAgents

TycoonAgents is a separate VS Code extension that is one *consumer* of this
repo — it installs Power Tools on demand from this repo's GitHub Releases.
It no longer bundles a copy. This repo does not depend on it.

## Build

```
npm ci
npm run build
```

Exact build command (esbuild):

```
esbuild uefn-server.ts --bundle --platform=node --format=esm --target=node18 --outfile=uefn-server.mjs
```

**Gotcha:** `uefn-server.mjs` is gitignored. It's a build artifact published
to GitHub Releases, not committed. A fresh clone will not have it — you must
run the build.

Dev run without building: `npm start` (runs `tsx uefn-server.ts`).

Requires Node >=18 (see `engines` in `package.json`).
Deps: `@modelcontextprotocol/sdk`, `zod`.
Dev deps: `esbuild`, `tsx`, `typescript`, `@types/node`.

## Release process

Trigger: push a tag matching `v*` (also supports `workflow_dispatch`).
Workflow: `.github/workflows/release.yml`.

**Hard guard:** the tag must match `package.json`'s `"version"` field
exactly (tag `v0.1.2` <-> version `0.1.2`) or the workflow fails on
purpose. Bump `package.json` first, then tag.

Publishes two assets:
- `trashbyrds-power-tools-<version>.zip` — contains `uefn-server.mjs`,
  `python/`, `skills/`, `LICENSE`, `README.md`, `INSTALL.md`, and
  `package.json`, all at the archive root.
- the bare `uefn-server.mjs`.

Current release: v0.1.2.

## Architecture: file-based IPC

The MCP server (`uefn-server.ts`, Node) and the in-UEFN Python bridge
(`python/uefn_bridge.py`) do **not** talk over a socket. They exchange JSON
files in a bridge directory.

- Bridge dir: `$UEFN_BRIDGE_DIR`, else `<temp>/uefn_bridge`.
- Commands land as `command.json` / `command_<id>.json`; responses as
  `response_<id>.json`.
- Python polls every 0.5s (`_POLL_INTERVAL`, `uefn_bridge.py:207`) and
  writes a heartbeat every ~5s (`_HEARTBEAT_INTERVAL`, `uefn_bridge.py:208`).

30 MCP tools are registered via `server.registerTool()` in
`uefn-server.ts` (roughly lines 626-1510). Representative examples:
`uefn_status`, `uefn_list_devices`, `uefn_get_property`,
`uefn_set_property`, `uefn_run_audit`, `uefn_verse_check`.

## Python entry points

- `python/init_unreal.py` — auto-runs when UEFN opens the project.
  Self-syncs the bridge from the newest copy on disk, starts the bridge,
  registers Tools-menu entries.
- `python/pt.py` — in UEFN's Python console, `import pt` reloads
  `uefn_launcher` and opens the Power Tools UI.
- `python/uefn_launcher.py` — the Tkinter launcher UI.

## Verse check

`skills/uefn/verse_lsp_check.py` drives Epic's `verse-lsp` binary headless
over LSP/stdio for real compiler diagnostics. Pure Python stdlib.

Needs the `verse-lsp` binary from Epic's Verse IDE extension (VS Code /
Cursor / Windsurf / Antigravity).

Three distinct overrides — don't conflate them:
- `VERSE_LSP_PATH` — the analyzer *binary*.
- `UEFN_VERSE_PROJECT_DIR` — the VerseProject *data root*.
- `VERSE_LSP_CHECK_SCRIPT` — read by `uefn-server.ts`; points at where
  `verse_lsp_check.py` itself lives.

## Path discovery doctrine

This repo installs on machines you will never see. Never assume one
machine's username, drive, or folder layout. Discover at runtime.

`init_unreal.py`'s project-root discovery (roughly lines 79-132, ladder
~238-278) tries, in order:
1. `~\Documents\Fortnite Projects`
2. `~\OneDrive\Documents\Fortnite Projects`
3. wildcarded `~\OneDrive*\...`
4. the `OneDrive` / `OneDriveConsumer` / `OneDriveCommercial` env vars
5. the Windows registry "Personal" known folder

Registry probes must fail open (missing key or wrong platform → skip, never
raise).

On failure: error explicitly, listing every location tried and naming the
override var — never return a clean/empty success shape.

**Known gap, stated honestly:** project-root discovery has **no env-var
override today**. `UEFN_BRIDGE_DIR` controls the IPC directory, which is a
different thing entirely — it does not help here. This is a real gap worth
closing, not a rumor.

## Syncing tools into a live project

```
npm run sync:project
```

Runs `scripts/sync-to-project.mjs`, which copies `python/` into a UEFN
project's `Content\Python`.

Destination resolution ladder: `--dest=<path>`, then
`UEFN_PROJECT_PYTHON_DIR`, then a documented default.

Additive-overwrite only: it never deletes anything it did not install, so
generated files (e.g. `tag_inspect_report.json`) and `__pycache__` survive.
Byte-identical files are skipped so mtimes stay stable (the usual
destination is OneDrive-synced).

`--dry-run` reports what would change without writing.

## Tests — there are none

There is **no test suite** in this repo. No pytest, no `node --test`, no CI
test job. The release workflow builds and publishes **without running
tests**. This is a real risk, not a to-do list item — anyone changing
`uefn-server.ts` or the Python tools must verify manually before releasing.

## Docs

- `README.md` — overview, tool groupings, architecture.
- `INSTALL.md` — per-client MCP setup for Claude Code / Codex CLI / Gemini
  CLI and others. Uses `<POWER_TOOLS_DIR>` and `<POWER_TOOLS_REPO>`
  placeholders — this is a public repo, never paste real machine paths into
  it.
- `docs/verse-tag-inspector-spec.md`.
