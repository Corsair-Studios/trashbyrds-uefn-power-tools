# Install

## System requirements

For the default install — Power Tools' tools inside UEFN itself (step 1, then `import pt`):

- **UEFN** (Unreal Editor for Fortnite) installed, with your project open.
- The **Python Editor Script Plugin** enabled in UEFN (`Edit -> Plugins`, search "Python Editor Script Plugin", enable it, restart UEFN if prompted).

Additionally, ONLY if you also want to drive Power Tools from an external AI client (sections 2–4):

- **Node.js 18+** on the machine running the MCP server.
- An MCP-capable client (e.g. Claude Code) to talk to the server.

## Installing with an AI assistant

If you're running Claude Code, Codex CLI, Gemini CLI, Cursor, or a similar assistant with filesystem access, you can point it at this file and have it do the install with you rather than copy-pasting each step by hand. It reads your existing MCP config, merges the `powertools` entry in without disturbing anything already there, and fills in the real absolute path instead of leaving a placeholder in the file. It will ask before it changes any file.

Paste this into your assistant:

```
Read the INSTALL.md at https://github.com/Corsair-Studios/trashbyrds-uefn-power-tools/blob/main/INSTALL.md. If I haven't already downloaded and unpacked a release, do that first, verify the unpack landed correctly, and ask me where to put the folder permanently. Then figure out which MCP client I'm using and find its config file. Read that config file first. Propose a merged version that adds the powertools server entry while preserving every server already listed in it — including Epic's official unreal-mcp entry if it's there, which must be left exactly as it is — and use the real absolute path to my unpacked Power Tools folder, not a placeholder. Show me the exact change before writing anything, and wait for my approval. Also handle the separate step of copying python/ into my UEFN project's plugin Content folder — that is Plugins/<PluginName>/Content/Python inside the project, NOT a Content folder next to the .uefnproject file.
```

**What the assistant needs to get right:**
- The server key is `powertools`, chosen so it doesn't collide with Epic's official UEFN MCP server, which registers itself as `unreal-mcp`. Running both at once is supported and expected — adding Power Tools must never rename, replace, or remove an existing `unreal-mcp` entry. See **[5. Epic's official UEFN MCP server](#5-epics-official-uefn-mcp-server)** for how the two coexist.
- The config shape differs per client — JSON with an `mcpServers` object, TOML `[mcp_servers.X]` tables, or VS Code's `servers` key. The per-client sections under **Connecting an AI client** below are authoritative for the exact shape and location.
- `<POWER_TOOLS_DIR>` in every example in this file means the absolute path to the folder holding `uefn-server.mjs`. It must be replaced with a real path, and that folder needs to be a permanent location, not one that will move or get deleted.
- Config files must be merged, never replaced — an existing config can already list other MCP servers, and overwriting the file instead of merging into it silently deletes them.
- Copying the Python bridge and configuring the MCP client are two separate steps. Both are required; doing only one leaves the install incomplete. The bridge goes into the project's **plugin** `Content/Python` folder — see step 1, because it is *not* the folder next to the `.uefnproject` file.

**If it's also fetching the release, these facts matter:**
- The canonical source is `https://github.com/Corsair-Studios/trashbyrds-uefn-power-tools`, and releases live on that repo's Releases page. Anything else is not this project — a fork or mirror may not contain the same code.
- The release asset to use is the zip named `trashbyrds-power-tools-<version>.zip` (for example `trashbyrds-power-tools-0.1.3.zip`). A bare `uefn-server.mjs` asset is also published for anyone who only wants the server file. GitHub's auto-generated "Source code (zip)" is not the release artifact and does not contain a built `uefn-server.mjs`.
- A correct unpack puts `uefn-server.mjs`, `package.json`, `python/`, `skills/`, and the LICENSE/README/INSTALL files at the top level of the chosen folder. If those sit one directory deeper, the archive was unpacked into a nested folder and every configured path will be wrong.
- Verification after unpacking: `uefn-server.mjs` exists at the top level, and the `version` field in `package.json` matches the release tag that was downloaded (tag `v0.1.3` corresponds to version `0.1.3`). A mismatch means the wrong artifact was used.
- The destination folder needs to be permanent — not Downloads, not a temp folder, not a location a cleanup or reinstall would remove — because the client config hard-codes the absolute path to `uefn-server.mjs`. Moving the folder later breaks the config until the path is updated.

**What it cannot do for you.** An assistant editing config files cannot verify the bridge is actually running inside UEFN. That check requires UEFN open with your project loaded, running `import pt` in UEFN's Python console (UEFN auto-runs a project's `init_unreal.py` only if the project is already mounted when Python initializes — and with Epic's MCP server set to auto-start, Python now initializes at editor boot, before any project is open, so in practice the auto-run rarely fires and `import pt` is the normal path; do not use `import init_unreal`, which now resolves to a file Epic ships — see **Starting the bridge**), and confirming a fresh `heartbeat.json` appears in the bridge's IPC directory. See **[3. How it connects](#3-how-it-connects)** below for what a working versus non-working bridge looks like and why a client's own "Connected" status isn't proof either way.

## 1. Install the Python bridge into your UEFN project

Copy the **contents** of this repo's `python/` folder into your UEFN project's `Content/Python/` directory.

**Finding `Content` — this is the step people get wrong.** UEFN does **not** put `Content` next to your `.uefnproject` file. It nests it inside the project's plugin, so the folder you want is `Plugins/<PluginName>/Content/`. Create `Python` inside it if it isn't there already:

```
<your-uefn-project>/
  MyProject.uefnproject                <- the .uefnproject file
  Plugins/
    MyProject/
      Content/                         <- THE Content folder — the one you want
        Python/                        <- create this if it doesn't exist
```

So the destination is `<your-uefn-project>/Plugins/<PluginName>/Content/Python/`. There is normally **no** `Content` folder next to the `.uefnproject` file, and if you create one yourself UEFN will never read it. If you're unsure which `Content` folder is the right one, it's the one that already holds your `.umap` and `.uasset` files. `<PluginName>` is usually your project's name but does not have to be — use whatever folder is actually there under `Plugins/`.

**`Content/Python` is invisible inside UEFN.** It holds no `.uasset` files, so it never appears in UEFN's Content Browser. Create it and copy into it from File Explorer, not from inside UEFN.

After copying, `Plugins/<PluginName>/Content/Python/` should contain `init_unreal.py` directly — **not** a nested `Content/Python/python/init_unreal.py`. Copy the folder's contents, not the folder itself.

**Symptom of getting the location wrong — either the wrong `Content` folder, or files one level too deep:** no error, no console output — UEFN silently finds nothing and the tools never appear. **Check both:**
- `Plugins/<PluginName>/Content/Python/init_unreal.py` exists at exactly that path. If what you have instead is `<your-uefn-project>/Content/Python/`, that is the wrong folder — move it under the plugin.
- `Content/Python/python/` does **not** exist. If it does, your files are one level too deep; move everything up into `Content/Python/` directly.

**Once the files are in place:**

- Start Power Tools by opening UEFN's Python console once your project is open and running `import pt` — see **Starting the bridge** below.
- If UEFN prompts you to enable the Python Editor Script Plugin, accept it and restart UEFN.

### Starting the bridge

Open UEFN's Python console (Output Log panel → console dropdown → **Python**) and run:

```python
import pt
```

That one command initializes everything — the bridge, the native toolsets, the Tools-menu entries — and opens the Power Tools window. Run it once per UEFN session, after each restart of UEFN.

**Symptom if you skip this step:** no Power Tools window, no native toolsets, and the MCP server reports the bridge unreachable.

**Do not use `import init_unreal` to start Power Tools.** It used to be the documented command, and it no longer works: Epic's experimental Toolsets plugins now ship their own `init_unreal.py` files, and their directories sit ahead of your project's on Python's search path — so `import init_unreal` silently loads and runs **Epic's** file instead of this project's. The telltale is a wall of `LogToolsetRegistry: Warning: Toolset '...' already registered` lines and no `Trashbyrd:` lines at all. `import pt` is immune: it locates this project's `init_unreal.py` by its file path, next to `pt.py` itself.

**If the bridge needs a restart mid-session** (a client can't reach it and the launcher footer agrees), reload the bridge module directly:

```python
import importlib, uefn_bridge
importlib.reload(uefn_bridge)
```

### "Rejected command.json with missing/mismatched session token"

**Known issue, not yet fixed.** If the Output Log shows `uefn_bridge: Bridge started.` twice in a row, followed by a rejection message like this, two bridge instances registered with two different session tokens and are now fighting over the same IPC files. **Fix:** restart UEFN to clear the duplicate registration — a full restart, not just re-running `import pt` or reloading the module.

### A tool seems to be running an old version

UEFN can load Python from two places: your project's plugin `Content/Python/` (where you just copied files) and an engine-side copy inside your Fortnite installation, at `FortniteGame/Content/Python/` under wherever your Epic Games Launcher installed Fortnite. That parent location varies by machine and by Launcher settings, so no single real path is given here. On a clean install `FortniteGame/Content/` exists but has **no** `Python` subfolder — that folder appears only once something puts files there.

`init_unreal.py` syncs the newest project copy over the engine copy automatically when the bridge starts, comparing the `BRIDGE_VERSION` stamp in `bridge_version.py`. If that stamp already matches on both sides, the sync can skip copying even when the file contents underneath differ — so the engine copy can end up running stale code behind a version number that looks current.

**Symptom:** a bug you know was fixed is still happening, or a feature you just added isn't there, even though the project copy on disk is correct.

**Check which version is loaded:** the Power Tools launcher window footer (`import pt`) shows the bridge version currently running.

**Manual fix:** copy this repo's `python/` files into the engine-side `FortniteGame/Content/Python/` directory as well as the project copy — **create that `Python` folder first, since it does not exist by default** — then delete any `__pycache__` folder in both locations and restart UEFN.

### A tool can't find your project

Several tools locate your project on disk rather than through the editor — the version sync above, the Verse cross-reference check, the health scan, and the device audit. They try a list of known locations, then validate each guess against real assets before trusting it.

**If your projects live somewhere conventional** — `Documents\Fortnite Projects`, including any OneDrive-redirected version of it, or a plain `C:\UEFN` / `D:\UEFN` folder — this is automatic and you can ignore this section.

**If they live anywhere else** — a work drive, a network share, a folder named something else entirely — no amount of guessing will find them. Tell Power Tools directly by setting one environment variable to the folder that **contains** your project folders:

```
setx UEFN_PROJECTS_ROOT "D:\Work\UEFN"
```

Point it at the parent folder, not at a single project. If your project is `D:\Work\UEFN\MyGame\MyGame.uefnproject`, the value is `D:\Work\UEFN`.

**This must be a real environment variable, not a client config entry** — the same trap as `UEFN_BRIDGE_DIR` above. The tools that need it run inside UEFN, so the variable has to exist in UEFN's own process: set it with `setx` (or System Properties → Environment Variables) and **restart UEFN** so it inherits the new value. Putting it in `.mcp.json` or `config.toml` will not work.

**Symptoms that point here:** a Verse cross-reference check that reports nothing, a health scan that finds no files, a device audit that comes up empty, or the version-sync line in the Output Log saying it found no project copy — all while the project is plainly open in UEFN.

**Worth knowing:** your project's *folder* name doesn't have to match the island name inside it. A folder called `MyGame_` holding an island called `MyGame` is fine and is handled — you don't need to rename anything.

## 1b. Native UEFN toolsets (no Node, no config file)

**This is the default install — for most people, step 1 plus `import pt` is the whole setup.**

Once `python/` is in place (step 1), Power Tools registers itself with UEFN's own Toolset Registry. Its tools then appear inside UEFN alongside Epic's built-in toolsets — same registry, same discovery, same assistant — and are also discoverable through Epic's official MCP server's tool search (`list_toolsets`).

**Nothing else is required.** No Node, no `uefn-server.mjs`, no `.mcp.json`, no bridge directory, and no external client. Sections 2 and 4 exist for the second, fully supported path: driving Power Tools from Claude Code, Codex CLI, or Gemini CLI. You can use either path or both at once.

**Requirements:** **Python Editor Scripting** enabled for the project (the same setting Epic's own MCP server needs), and a UEFN build that ships the Toolset Registry.

**When it runs.** Registration happens when `init_unreal.py` runs — and UEFN only auto-runs that if the project is already mounted when Python initializes, which in practice it usually is not (with Epic's MCP server set to auto-start, Python initializes at editor boot, before any project is open). This interaction is a known UEFN issue with bugs already filed against it, so it may change in a future UEFN release — `import pt` works correctly either way, skipping its bootstrap whenever the auto-run did fire. So after opening your project, run `import pt` in the Python console once per session — it bootstraps everything and opens the launcher in one step. (Not `import init_unreal`: that name now resolves to a file Epic ships — see **Starting the bridge**.)

**How to tell it worked.** The Output Log shows one of:

```
Trashbyrd: native UEFN toolsets registered
Trashbyrd: native UEFN toolsets unavailable this session (Toolset Registry not present) — MCP bridge unaffected
```

The second line is not an error — it means this UEFN build has no Toolset Registry, and everything else about Power Tools works as before. If **neither** line appears, `init_unreal.py` has not run this session at all — run `import pt` in the Python console.

**Where the tools appear — and where they don't.** These toolsets register with UEFN's **Toolset Registry** and surface through UEFN's own AI assistant. They do **not** appear on the **Editor Preferences → Plugins → MCP Toolset Servers** page — that page only lists outbound server connections you add there yourself (see the optional section under **[5. Epic's official UEFN MCP server](#5-epics-official-uefn-mcp-server)**), and it starts with one blank placeholder entry that belongs to no one.

**What gets registered.** Three toolsets, 29 tools, each returning JSON:

| Toolset | Covers |
| --- | --- |
| `PowerToolsInspect` | Status, level info, devices, actor properties, bulk queries, asset listing and inspection, device audit |
| `PowerToolsScan` | Health, dependency and asset sweeps; texture, material and Niagara usage; Verse tags; moderation/IP pre-flight |
| `PowerToolsEdit` | Select actors, set properties (single and bulk), spawn, duplicate, set transforms |

`batch_set` defaults to a dry run, so a bulk edit reports what it would change before changing anything.

**Caveat, stated plainly.** This is verified working (registration, discovery through Epic's MCP tool search, and a live bridge were all confirmed against a real project on 2026-08-30), but it rides on an Epic API that is marked Experimental and is not covered by Epic's public documentation, so a future UEFN build could change or remove it. The registration is fully isolated: if the API goes away, it logs the "unavailable" line above and the MCP server, the file-IPC bridge, and the launcher all keep working exactly as they do today. Please report anything that behaves differently on your build.

## 2. Run the MCP server

**Only needed for external AI clients.** If the native toolsets from section 1b are all you want, you are already done — skip sections 2 through 4 entirely. Continue here to drive Power Tools from Claude Code, Codex CLI, Gemini CLI, or another MCP client, which works alongside the native path.

If you downloaded a release, you already have everything you need: the zip includes `uefn-server.mjs` at its root, a self-contained bundle with no dependencies to install. Run it directly:

```bash
node uefn-server.mjs
```

Point your MCP client's configuration at that same `node uefn-server.mjs` command — see **Connecting an AI client** below.

**If you cloned the source repo instead** (to fork or modify Power Tools), run the TypeScript source directly instead of the bundled `.mjs`:

```bash
npm install
npm start
```

`npm start` runs `tsx uefn-server.ts`. Point your MCP client's configuration at that command (or at `npx tsx <path-to-your-clone>/uefn-server.ts`) instead of the `node uefn-server.mjs` form.

## 3. How it connects

The MCP server and the in-UEFN Python bridge communicate through file-based IPC in the OS temp directory — no network port, no additional UEFN plugin. Keep UEFN open with your project loaded whenever you want live queries or edits to reach the editor; if UEFN isn't running (or the bridge hasn't started), the MCP server will report the bridge as unreachable.

**"Connected" in your MCP client is not proof the bridge is running.** A client-side "Connected" status only means the client successfully launched `node uefn-server.mjs` — it says nothing about whether the Python bridge inside UEFN has started. You can see a client report the server as connected while the Power Tools panel shows "Bridge disconnected" and no heartbeat file exists at all. The only trustworthy check is calling the `uefn_status` tool from your client, or reading the bridge state directly in the Power Tools launcher window (`import pt`) — trust those over the client's own connection indicator.

## 4. Connecting an AI client

The MCP server (`uefn-server.mjs`) speaks plain stdio MCP, so any MCP-capable client can launch it the same way: a `command` plus `args` that run the server, with an optional `env` block for the [environment overrides](#environment-overrides) below. Each client stores that config in its own file, using its own key name, and each client resolves that file from a different location — the subsections below give a complete, standalone, step-by-step walkthrough for each one. Pick the section for the client you're using and follow it top to bottom; you should not need to read any other client's section.

**Before you start any of these, know your server path.** Wherever you unzipped the Power Tools release is where `uefn-server.mjs` lives. That location must be **permanent** — not your Downloads folder, not a temp folder, not a location you plan to delete or move later — because every config below hard-codes a path to that file. If you move the unzipped folder after configuring a client, that client's config breaks until you update the path. In every example below, replace the placeholder `<POWER_TOOLS_DIR>` (shown in config blocks as e.g. `<POWER_TOOLS_DIR>/uefn-server.mjs`, similar to a prose example like `C:/path/to/power-tools/uefn-server.mjs`) with the real, full path to your own `uefn-server.mjs`, using forward slashes (`/`) even on Windows — Node accepts forward slashes in paths, and using them avoids backslash-escaping mistakes in JSON and TOML files (double backslashes, `\\`, are easy to get wrong and are a real source of broken configs).

**If you cloned the source repo instead** of downloading a release, and are running the TypeScript source directly (`npm start`), swap the `"command"`/`"args"` pair in every example below for:

```json
"command": "npx",
"args": ["tsx", "<POWER_TOOLS_REPO>/uefn-server.ts"]
```

Replace `<POWER_TOOLS_REPO>` with the real, full path to your own clone's location.

If you're using the in-UEFN launcher window (`import pt` → MCP Bridge info), its **Copy config for selected client** button fills in the real, discovered path and command for your install automatically — you don't need to hand-edit the placeholder paths below if you use that button. The walkthroughs below assume you're editing the config file by hand.

**Officially supported clients: Claude Code, Codex CLI, and Gemini CLI.** Each gets a full standalone walkthrough below. If you work inside VS Code or Antigravity IDE, note that those are editors, not MCP clients themselves — see **Other MCP clients (community, not tested)** below for what that means for you. Every other client (Cursor, Windsurf, and anything else not listed) is community and untested, covered together in that same section.

**A client reporting the server "Connected" is not proof anything is working.** This is repeated in every section below because it is the single most common point of confusion: a "Connected" status in your AI client only means the client successfully launched `node uefn-server.mjs` as a child process. It says nothing about whether the Python bridge inside UEFN has started. You can have a fully "Connected" client, call a tool, and have it fail — because UEFN was never told to start the bridge. The only real proof that everything is working end to end is calling the `uefn_status` tool from inside your client and getting back a real level name and actor count, as described in each section's verification step.

### Claude Code

**1. Which file, and where.** Claude Code reads its MCP configuration from a file named `.mcp.json`. This file is **project-local**, not global — Claude Code looks for it in **the directory you launch Claude Code from**, and nowhere else: not your home folder, and not any parent folder. That launch directory is the only thing that decides where this file goes.

So: pick the folder you'll actually run Claude Code in while working on this project, and put `.mcp.json` there. Your UEFN project root (next to the `.uefnproject` file) and the plugin `Content` folder you edit Verse in are both fine choices — they are different folders, and only the one you launch from matters. This is unrelated to where the Python bridge goes in step 1.

**2. Create the directory first?** No new directory is needed — `.mcp.json` is a single file that goes directly in the folder you chose above.

**3. Full file content.** Create a file named exactly `.mcp.json` (note the leading dot, and no other file extension) in that folder with this content if the file doesn't exist yet, or merge the `powertools` entry into the existing `mcpServers` object if `.mcp.json` already exists, preserving any servers already there:

```json
{
  "mcpServers": {
    "powertools": {
      "command": "node",
      "args": ["<POWER_TOOLS_DIR>/uefn-server.mjs"]
    }
  }
}
```

Replace `<POWER_TOOLS_DIR>` with the real, full path to your own unzipped Power Tools folder. That is the whole entry — **no `env` block is needed**, and you should not add one here without reading [Environment overrides](#environment-overrides) first. In particular, do not set `UEFN_BRIDGE_DIR` in this file on its own: a client `env` block reaches the MCP server only, never UEFN's own Python, and setting it on one side alone puts the two halves of the bridge in different directories where they can never pair.

If your `.mcp.json` already lists other servers — Epic's official `unreal-mcp` entry, or anything else — add `powertools` alongside them inside the existing `mcpServers` object. Do not replace the file.

**4. Where to launch Claude Code from.** This is the step people get wrong. Claude Code only reads `.mcp.json` from the directory you **launch it in** — not from any other folder, and not recursively from parent folders. Open your terminal (or your editor's integrated terminal) in the exact folder where you created `.mcp.json` in step 1, and start Claude Code from there. If you launch Claude Code from your home directory, your Desktop, or any other folder, it will not find this `.mcp.json` and the `powertools` server will not appear at all.

**5. In UEFN's Python console, in order.** With your UEFN project open, open the Python console (Output Log panel → console dropdown → **Python**) and run these two lines, in this order:

```python
import importlib, uefn_bridge
importlib.reload(uefn_bridge)
```

If Power Tools hasn't been started at all this session, `import pt` also works and additionally opens the launcher window. Do not use `import init_unreal` — that module name now resolves to a file Epic ships, not this project's (see **Starting the bridge**). The `importlib.reload(uefn_bridge)` form above forces the bridge to actually (re)start regardless of what's already loaded this session, so it's the reliable command to run before connecting a client.

**6. Verify it worked.** In Claude Code, ask it to call the `uefn_status` tool (or just ask "check the UEFN bridge status"). A real, working connection returns a specific level name and an actor count greater than zero. If you get an error, a generic "unreachable" message, or no level name, the bridge is not actually running even if Claude Code's own connection indicator looks fine — go back to step 5.

**Claude Code showing the `powertools` server as "Connected" is not proof anything is working.** A "Connected" status in Claude Code only means Claude Code successfully launched `node uefn-server.mjs` as a child process — it says nothing about whether the Python bridge inside UEFN has started. You can have a fully "Connected" server in Claude Code, call a tool, and have it fail, or you can have Claude Code report "Connected" while the Power Tools launcher window shows "Bridge disconnected" and no heartbeat file exists at all. The only trustworthy check is calling the `uefn_status` tool from Claude Code and getting back a real level name and an actor count greater than zero, as described above — trust that result over Claude Code's own connection indicator.

**7. If it doesn't work:**
- Double-check you launched Claude Code from the exact folder containing `.mcp.json` — this is the most common mistake.
- Confirm `.mcp.json` is valid JSON — a trailing comma or missing brace will make Claude Code silently ignore the whole file. Paste it into any JSON validator if unsure.
- Confirm the path in `"args"` points at a `uefn-server.mjs` file that actually exists at that exact location, using forward slashes.
- Re-run the two-line reload command from step 5 — UEFN must be open with your project loaded, and the bridge must be re-started after every UEFN restart.
- Check the Power Tools launcher window (`import pt`) — its footer shows whether the bridge is actually running and which version.

### Codex CLI

This client has a sharp edge (the sandbox gotcha in step 7) that has caused real confusion, so read this whole section including step 7 before you try it.

**1. Which file, and where.** Codex CLI reads MCP server configuration from exactly one file: `~/.codex/config.toml`. This is a **global** file — it lives in your user home directory, not in your UEFN project. There is no such thing as a project-local Codex config: a `.codex` folder placed anywhere inside your project (including inside `Content/`) is never read by Codex CLI. `~/` means your home directory — on Windows that's `C:/Users/<your-username>` (Codex CLI itself resolves the `~`; you don't need to expand it yourself when editing the file, but if your editor doesn't expand `~` either, use the full path).

**2. Create the directory first?** The `.codex` folder may not exist yet if you've never run Codex CLI before. Create it if needed: on Windows, in File Explorer, go to your user folder (`C:/Users/<your-username>`) and create a folder named `.codex` (you may need to type the name including the leading dot in the "New Folder" rename box). From a terminal, `mkdir "$env:USERPROFILE\.codex"` in PowerShell, or `mkdir ~/.codex` in a bash-like shell, does the same thing.

**3. Full file content.** Inside `~/.codex/config.toml`, add this complete table (if the file already has other content in it from other MCP servers or settings, add this table without disturbing what's already there):

```toml
[mcp_servers.powertools]
command = "node"
args = ["<POWER_TOOLS_DIR>/uefn-server.mjs"]
```

Replace `<POWER_TOOLS_DIR>` with the real, full path to your own unzipped Power Tools folder, using forward slashes. That is the whole table — **no `env` table is needed**, and you should not add one without reading [Environment overrides](#environment-overrides) first. In particular, do not set `UEFN_BRIDGE_DIR` here on its own: a client `env` table reaches the MCP server only, never UEFN's own Python, and setting it on one side alone puts the two halves of the bridge in different directories where they can never pair. If the file already contains other `[mcp_servers.*]` tables (Epic's official `unreal-mcp`, or anything else), leave them exactly as they are.

**4. Where to launch Codex CLI from.** It does not matter. Because Codex CLI's config is global (step 1), you can launch `codex` from any directory on your machine and it will find the same `~/.codex/config.toml` and the same `powertools` server entry every time.

**5. In UEFN's Python console, in order.** With your UEFN project open, open the Python console (Output Log panel → console dropdown → **Python**) and run these two lines, in this order:

```python
import importlib, uefn_bridge
importlib.reload(uefn_bridge)
```

This reload form reliably (re)starts the bridge regardless of what's already loaded this session. (`import pt` also works if Power Tools hasn't started yet, and opens the launcher too; `import init_unreal` does not — that name now resolves to a file Epic ships, see **Starting the bridge**.) Run this once per UEFN session, and again after every UEFN restart.

**6. Verify it worked.** From a Codex CLI session, ask it to call the `uefn_status` tool. A working connection returns a real level name and an actor count greater than zero — that's the only proof that matters. A "Connected" server status in Codex CLI on its own only means Node launched successfully, not that UEFN's bridge is reachable.

**7. If it doesn't work:**
- **The sandbox gotcha (read this first):** Codex CLI's default `sandbox_mode = "read-only"` auto-denies the very first MCP tool call in `codex exec` — instantly, before it ever reaches the server — with a message like `"user cancelled MCP tool call"`. That message reads exactly as if a human rejected the call, but no human did anything; the sandbox blocked it automatically. If your first `uefn_status` call fails with that message, this is almost certainly the cause, not a broken server or bridge. Fix it by either running Codex CLI interactively so you can approve the tool call when prompted, or by starting Codex with the sandbox opened (not read-only), so `uefn_*` calls are allowed through.
- Confirm you edited `~/.codex/config.toml` and not some other file — there is no project-local alternative, so a project-local `.codex` folder anywhere will silently do nothing.
- Confirm the TOML syntax is valid — table headers (`[mcp_servers.powertools]`) must appear before the keys that belong to them, and string values need double quotes.
- Confirm the path in `args` points at a real, existing `uefn-server.mjs`, with forward slashes.
- Re-run the two-line reload command from step 5 in UEFN's Python console — UEFN must be open with your project loaded.

### Gemini CLI

**1. Which file, and where.** Gemini CLI supports two locations, and either one works — pick one, don't use both:
- **Global:** `~/.gemini/settings.json` (in your home directory — on Windows, `C:/Users/<your-username>/.gemini/settings.json`). Use this if you want the `powertools` server available no matter which project you're in.
- **Project-local:** `.gemini/settings.json` inside the folder you launch Gemini CLI from for this project. Use this if you only want the `powertools` server available for this specific project.

**2. Create the directory first?** Whichever location you pick, the `.gemini` folder likely doesn't exist yet. Create it before creating the file inside it:
- For the global option, create a folder named `.gemini` directly inside your user home directory.
- For the project-local option, create a folder named `.gemini` directly inside the folder you launch Gemini CLI from for this project.

**3. Full file content.** Inside whichever `settings.json` you chose, put this complete content (if the file already exists with other settings, merge this `mcpServers` key into the existing JSON object rather than replacing the whole file):

```json
{
  "mcpServers": {
    "powertools": {
      "command": "node",
      "args": ["<POWER_TOOLS_DIR>/uefn-server.mjs"]
    }
  }
}
```

Replace `<POWER_TOOLS_DIR>` with the real, full path to your own unzipped Power Tools folder, using forward slashes. That is the whole entry — **no `env` block is needed**, and you should not add one without reading [Environment overrides](#environment-overrides) first. In particular, do not set `UEFN_BRIDGE_DIR` here on its own: a client `env` block reaches the MCP server only, never UEFN's own Python, and setting it on one side alone puts the two halves of the bridge in different directories where they can never pair. Merge `powertools` into any `mcpServers` object the file already has — including Epic's official `unreal-mcp` entry, which must be left as it is — rather than replacing the file.

**4. Where to launch Gemini CLI from.** If you used the **global** file, it doesn't matter — launch `gemini` from anywhere. If you used the **project-local** file, you must launch `gemini` from the folder containing the `.gemini` folder you just created, the same way Claude Code requires.

**5. In UEFN's Python console, in order.** With your UEFN project open, open the Python console (Output Log panel → console dropdown → **Python**) and run these two lines, in this order:

```python
import importlib, uefn_bridge
importlib.reload(uefn_bridge)
```

This reliably (re)starts the bridge regardless of what's already loaded this session. (`import pt` also works if Power Tools hasn't started yet; `import init_unreal` does not — that name now resolves to a file Epic ships, see **Starting the bridge**.) Run this once per UEFN session, and again after every UEFN restart.

**6. Verify it worked.** From a Gemini CLI session, ask it to call the `uefn_status` tool. A working connection returns a real level name and an actor count greater than zero. A "Connected" status for the server on its own only confirms Node started — it does not confirm the bridge is reachable.

**7. If it doesn't work:**
- Confirm you edited the file at the location you intended — if you used the project-local file but launched Gemini CLI from a different folder, it won't be found.
- Confirm the JSON is valid — a trailing comma or missing brace makes Gemini CLI silently ignore the file.
- Confirm the path in `"args"` points at a real, existing `uefn-server.mjs`, with forward slashes.
- Re-run the two-line reload command from step 5 in UEFN's Python console.
- Check the Power Tools launcher window (`import pt`) footer for the bridge's actual running status and version.

### Other MCP clients (community, not tested)

**These are not officially supported, and none of them have been tested end to end with Power Tools.** Claude Code, Codex CLI, and Gemini CLI (above) have been tested to differing degrees; the clients below have not. They are documented on a best-effort basis, from each client's own published MCP config format, with no verification that a `uefn_status` call actually comes back with a real level name and actor count. If you get one of these working (or can't), please report it.

**Using VS Code or Antigravity IDE? You probably don't need this section.** VS Code and Antigravity IDE are editors — they are hosts you run a terminal inside, not MCP clients in their own right. If you're using either one, the normal path is to open its integrated terminal and run Claude Code, Codex CLI, or Gemini CLI there, then follow that CLI's section above exactly as written. The editor itself needs no separate MCP setup; only the CLI running inside it does. The VS Code Copilot agent-mode and Antigravity-native config entries below exist only for people who specifically want the editor's own built-in agent (not a CLI in its terminal) to talk to the bridge, which is the untested path.

Every client below uses the same config **shape** as the Claude Code section above: a `command` of `node` and an `args` array pointing at your `uefn-server.mjs` (see the Claude Code section's `.mcp.json` example for the full JSON to copy and adapt — name the server entry `powertools`, same as that example, and merge it into whatever servers the file already lists). No `env` block is needed; read [Environment overrides](#environment-overrides) before adding one. What differs per client is only the file location and, in one case, the top-level key name:

| Client | Config file | Key |
| --- | --- | --- |
| Cursor | `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project-local) | `mcpServers` |
| Windsurf | `%USERPROFILE%\.codeium\windsurf\mcp_config.json` (Windows; global only) | `mcpServers` |
| Antigravity IDE (native) | `~/.gemini/config/mcp_config.json` (global) or `.agents/mcp_config.json` (workspace) — also reachable via agent side panel → menu → **MCP Servers** → **Manage MCP Servers** → **View raw config** | `mcpServers` |
| VS Code Copilot (agent mode) | `.vscode/mcp.json` (project-local) | `servers` — **not** `mcpServers`, and each entry needs an added `"type": "stdio"` field |

**Windows-specific gotcha for Windsurf:** a leading `~` in any path inside `mcp_config.json` is **not** automatically expanded by Windsurf on Windows the way it is in a Unix shell. Use `%USERPROFILE%` or a full drive-letter path instead of `~/...`.

For all four: after saving the config, launch the client from your UEFN project root if the file you used is project-local (Cursor project-local, Antigravity workspace, VS Code); global files (Cursor global, Windsurf, Antigravity global) work from anywhere. Then start the bridge in UEFN's Python console the same way as every other client:

```python
import importlib, uefn_bridge
importlib.reload(uefn_bridge)
```

**A "Connected" status here is not proof of anything**, exactly as with the three supported clients above: it only means the client launched `node uefn-server.mjs`, not that the Python bridge inside UEFN has started. The only trustworthy check is calling the `uefn_status` tool from the client and getting back a real level name and an actor count greater than zero.

If it doesn't work: double-check the file is valid JSON at the exact path for your client, confirm the path in `"args"` points at a real `uefn-server.mjs` with forward slashes, re-run the reload command above, check the Power Tools launcher window (`import pt`) footer for the bridge's actual status, and consult that client's own current MCP documentation in case its format has changed since this was written — then let us know what you find either way.

### Environment overrides

These are the client-neutral way to point the bridge and its tools at a non-default location — set them in the shell/process that launches the MCP server (or, where a client's `env` block is supported, there).

> **`UEFN_BRIDGE_DIR` is the one that bites.** The bridge has two halves — the MCP server, and the Python running inside UEFN — and they find each other only by both resolving the same directory. A client `env` block sets the variable for **the MCP server only**; UEFN's own process never sees it and falls back to `<temp>/uefn_bridge`. Set it on one side alone and the two halves sit in different directories forever: your client will report the server "Connected" while every bridge tool fails.
>
> **You almost certainly do not need this variable.** Left unset, both sides independently resolve the same per-machine temp path, which is exactly why the default needs no configuration. Set it only if you genuinely need a custom directory, and then set it for **both** processes — for UEFN that means a machine- or user-level environment variable in place *before* UEFN starts, not anything in a client config file.

| Variable | What it points to |
| --- | --- |
| `UEFN_BRIDGE_DIR` | The bridge IPC directory the MCP server and the in-UEFN Python bridge use to hand off work. Defaults to a per-machine temp directory if unset. Must be set for **both** processes or neither — see the warning above. |
| `UEFN_VERSE_PROJECT_DIR` | UEFN's `VerseProject` data root — where digests and `.vproject` files live. |
| `VERSE_LSP_PATH` | The Verse language server binary, used by tools that run compiler diagnostics. |
| `VERSE_LSP_CHECK_SCRIPT` | Where `verse_lsp_check.py` itself lives (see below) — a different thing from `VERSE_LSP_PATH`, which is the analyzer binary the script locates internally. |

### The `uefn_verse_check` tool needs `verse_lsp_check.py`

`uefn_verse_check` doesn't talk to the in-UEFN Python bridge like the other tools — it runs `verse_lsp_check.py` directly as a local subprocess, which drives Epic's bundled Verse language server headless. That means it needs the script to be present on disk, separately from everything else this repo installs.

This repo ships that script at `skills/uefn/verse_lsp_check.py`. Point the server at it with the `VERSE_LSP_CHECK_SCRIPT` environment variable:

```json
"env": {
  "VERSE_LSP_CHECK_SCRIPT": "<POWER_TOOLS_DIR>/skills/uefn/verse_lsp_check.py"
}
```

Replace `<POWER_TOOLS_DIR>` with the real, full path to your own Power Tools folder (source clone or unzipped release), using forward slashes on Windows as everywhere else in this document. (Windows-style backslashes work too, but in JSON they must be doubled — `\\` — since a single backslash is not valid JSON escaping. Forward slashes avoid the problem entirely and Node accepts them.) Add that to whichever client config you're already using from **Connecting an AI client** above. Unlike `UEFN_BRIDGE_DIR`, this one **is** safe to set in a client `env` block alone: `verse_lsp_check.py` runs as a subprocess of the MCP server, so the server's environment is the only one that needs it. Without it, `uefn_verse_check` fails with an honest error listing every location it tried — set the variable to the path above and it resolves.

## 5. Epic's official UEFN MCP server

Epic ships its own official UEFN MCP server. Enable it in UEFN via **Project Settings → Python Editor Scripting** and **Project Settings → UEFN MCP Toolsets**; once enabled it binds `http://127.0.0.1:8000/mcp` by default (both the port and the URL path are configurable in its settings, and it can be started by hand with the console command `ModelContextProtocol.StartServer`). See Epic's own documentation for what its server covers: https://dev.epicgames.com/documentation/fortnite/uefn-mcp

**Running both at once is supported and expected.** They do not compete for anything:

| | Epic's server | Power Tools |
| --- | --- | --- |
| Config key | `unreal-mcp` | `powertools` |
| Transport | HTTP on `127.0.0.1:8000` | stdio (`node uefn-server.mjs`) |
| Reaches UEFN via | its own in-process HTTP server | files in the bridge IPC directory |

Different keys, different transports, no shared port, no shared files. **The one way these two actually conflict is a config-editing mistake:** when you add Power Tools to a config that already has an `unreal-mcp` entry, merge into the existing server object — never replace the file, and never rename or remove that entry. If you configured Power Tools under a different key in an older setup, rename it to `powertools` and confirm it doesn't collide with `unreal-mcp` in that same file.

**One useful interaction.** Both require **Python Editor Scripting** enabled for the project. Turning it on for Epic's server therefore also lets UEFN auto-run Power Tools' `init_unreal.py` at the next editor startup — so if you enabled Python for Epic's server and have already copied `python/` into place, the Power Tools bridge may already be starting on its own.

**One thing to expect.** Epic documents that its tool calls can cause the editor to hitch. Power Tools' bridge writes its heartbeat from an editor tick, so a long enough hitch can stall that heartbeat and make the Power Tools launcher footer show a stale or disconnected status while an Epic tool call is running. This is cosmetic and self-correcting: the bridge is not restarted, no state is lost, and the footer returns to connected once the editor resumes ticking. If it stays disconnected after the editor is responsive again, that's a real problem — see [3. How it connects](#3-how-it-connects).

Power Tools (this server) focuses on bulk queries over a project's actors, plus moderation, dependency, texture, material, and Niagara-usage scanning.

### Fallback: the MCP Toolset Servers page (only if native registration reported unavailable)

**You almost certainly do not need this.** On a UEFN build that ships the Toolset Registry, the native registration from **[section 1b](#1b-native-uefn-toolsets-no-node-no-config-file)** already puts Power Tools inside UEFN's assistant, and an entry on this page would only add a second, slower copy of the same tools through more moving parts. The one audience for this section: a UEFN build **without** the Toolset Registry — the Output Log said `Trashbyrd: native UEFN toolsets unavailable this session`. For that build, the page below is the only remaining way into UEFN's assistant.

**Not yet verified end to end — treat this like the community clients above.** The steps below are derived from UEFN's own settings definitions and are believed correct, but no one has yet confirmed a full round trip. If you try it, please report how it went either way.

UEFN's MCP support runs in both directions. Besides serving its own tools (above), it can act as an MCP **client** and connect outward to other MCP servers, exposing their tools to the assistant built into UEFN. Power Tools speaks stdio MCP, so it can be registered there — and because it needs no network endpoint, no ports or API keys are involved.

**Where.** UEFN → **Edit → Editor Preferences → Plugins → MCP Toolset Servers**. (This is a different page from **Model Context Protocol**, which configures UEFN's own server — the one in the section above.)

**What to enter.** Add an entry to the MCP Servers list:

| Field | Value |
| --- | --- |
| Name | `powertools` |
| Description | anything, e.g. `Trashbyrd's UEFN Power Tools` |
| Transport | **Local stdio (launch a process)** |
| Exe Path | the full path to `node` — e.g. `C:/Program Files/nodejs/node.exe` |
| Args | the full path to your `uefn-server.mjs` |
| Enabled | checked |

Leave `Server Url`, `Api Key`, and the OAuth fields empty — those apply only to the HTTP transports (`Streamable HTTP` and `Legacy SSE (HTTP+SSE)`), not to stdio.

**Things that will bite you:**
- **The `Name` must be unique and non-empty.** Registration is refused outright if another configured server already uses that name, and an entry with an empty `Name` — or with no endpoint for its transport (no `Exe Path` for stdio) — is silently skipped at startup with no error in the UI.
- **Disabled entries are skipped on startup**, so unchecking `Enabled` fully removes it rather than merely hiding it.
- **This does not start the Python bridge for you.** Exactly as with every external client, you still need `import pt` (or the reload form) in UEFN's Python console, or the tools will be listed but every call will fail. See **[Starting the bridge](#starting-the-bridge)**.
- **Settings live in `EditorPerProjectUserSettings.ini`** under `[/Script/MCPClientToolset.MCPToolsetSettings]` if you would rather edit it directly than use the UI.

## Updating

Download the latest release and re-copy the contents of `python/` into `<your-uefn-project>/Plugins/<PluginName>/Content/Python/` (see [step 1](#1-install-the-python-bridge-into-your-uefn-project) if you're unsure which folder that is), then restart UEFN (or reload the bridge module from the Python console) to pick up changes. If you cloned the source repo, `git pull` instead. If a tool still behaves like the old version afterward, see [A tool seems to be running an old version](#a-tool-seems-to-be-running-an-old-version) — the engine-side copy may need updating too.
