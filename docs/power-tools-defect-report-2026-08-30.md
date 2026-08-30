# Power Tools — defect report

**Date:** 2026-08-30
**Verified against:** this repo's working tree (`D:\ACode\Trashbyrds Power Tools`), not just the shipped build
**Release cross-checked:** v0.1.4 (`trashbyrds-power-tools-0.1.4.zip`, 574,951 bytes)
**Environment:** Windows 11 Home 10.0.26200 · UEFN · Python 3.11.8 · Claude Code (VS Code extension)
**Test project:** `C:\UEFN\ChaosValley_` — standard UEFN plugin layout

All line numbers below refer to **this repo's files**. Where the shipped v0.1.4 build
differs, it is noted inline.

Install was performed on a deliberately cleaned machine: no prior Power Tools, no
TycoonAgents extension, no stale IPC directory, no duplicate projects. The unpacked
release was SHA256-verified file-by-file against the zip (31/31 identical, zero extras)
before testing, so nothing here is an artifact of a bad unpack.

### Repo vs. shipped v0.1.4

| File | Status |
| --- | --- |
| `python/init_unreal.py` | **Byte-identical** — D2 is live in main |
| `python/bridge_version.py` | **Byte-identical** — D4 is live in main |
| `INSTALL.md` | Differs (repo 34,573 b / release 34,692 b) — every doc defect below re-verified against the repo copy |
| `python/uefn_launcher.py` | Differs (repo 101,124 b / release 98,885 b) — tick-pump architecture unchanged, so OPEN still applies |
| `package.json` | Differs; both report version `0.1.4` |

---

## D1 — CRITICAL — INSTALL.md points `Content/Python` at a folder that does not exist in UEFN projects

**INSTALL.md:40**

> `Content/Python` lives inside the folder that holds your project's `.uefnproject` file — that's your UEFN project root.

UEFN does not put `Content` there. It nests it under the plugin:

```
C:\UEFN\ChaosValley_\ChaosValley.uefnproject          <- .uefnproject root
C:\UEFN\ChaosValley_\Content\                         <- DOES NOT EXIST (what the doc implies)
C:\UEFN\ChaosValley_\Plugins\ChaosValley\Content\     <- the actual Content folder
```

Verified on disk: `C:\UEFN\ChaosValley_\Content` does not exist. UEFN loaded the bridge
from the plugin path:

```
[2026.08.30-07.05.01:967] LogPython: Running start-up script
  C:/UEFN/ChaosValley_/Plugins/ChaosValley/Content/Python/init_unreal.py... started...
```

**Impact.** A user following the doc literally creates `<root>/Content/Python`, which
UEFN never reads. They then hit exactly the symptom INSTALL.md:48 describes — *"no
error, no console output — UEFN silently finds nothing and the tools never appear"* —
but the troubleshooting offered for that symptom blames a nested `python/` folder, a
different cause. There is no path from the symptom to the real problem.

**Suggested fix.** Document `<project-root>/Plugins/<PluginName>/Content/Python`, or
instruct users to find the existing `Content` folder (the one holding `.umap`/`.uasset`
files) rather than deriving it from where the `.uefnproject` sits.

**Related UX note.** `Content/Python` holds no `.uasset` files, so it is invisible in
UEFN's Content Browser — it appears only in Explorer. Worth stating outright; combined
with the wrong parent path above, it cost real time during this install.

---

## D2 — HIGH — bridge self-sync cannot discover any UEFN project (same root cause as D1)

**python/init_unreal.py:286**

```python
_pattern = _sync_os.path.join(_root, "*", "Content", "Python")
```

**python/init_unreal.py:299-303** then derives the project directory as
`dirname(dirname(py_dir))` and requires a `*.uefnproject` there.

Against the real layout:

```
py_dir       = C:\UEFN\ChaosValley_\Plugins\ChaosValley\Content\Python
_project_dir = C:\UEFN\ChaosValley_\Plugins\ChaosValley     <- holds .uplugin, not .uefnproject
actual       = C:\UEFN\ChaosValley_\ChaosValley.uefnproject
```

The candidate is discarded at the `*.uefnproject` check. Confirmed in the log — the
bridge reports finding no project copy while *running from one*:

```
[2026.08.30-07.05.02:049] LogPython: Trashbyrd: bridge self-sync — no project copy found, staying on v0.1.1
```

**Impact.** Self-sync is inert on every standard UEFN project. INSTALL.md:83 documents
behavior that cannot occur, and the whole *"A tool seems to be running an old version"*
section (INSTALL.md:79-89) rests on a mechanism that never fires.

**Suggested fix.** Also glob `<root>/*/Plugins/*/Content/Python`, or walk upward from
`py_dir` until a `*.uefnproject` is found, instead of assuming a fixed directory depth.

---

## D3 — HIGH — the `UEFN_BRIDGE_DIR` example desynchronizes the two halves of the bridge

Present in all three officially-supported client walkthroughs —
**INSTALL.md:152** (Claude Code), **:199** (Codex CLI), **:243** (Gemini CLI):

```json
"env": { "UEFN_BRIDGE_DIR": "<POWER_TOOLS_DIR>/bridge-dir" }
```

`python/bridge_paths.py:63-91` states the requirement plainly:

> To use a custom dir, set `UEFN_BRIDGE_DIR` for **BOTH** the UEFN process and the MCP wrapper.

A client `env` block sets the variable for the **MCP server only**. UEFN's Python side
never sees it and falls back to `<temp>/uefn_bridge`. The two halves then use different
directories and never pair. Confirmed in the log:

```
[2026.08.30-07.05.02:736] LogPython: uefn_bridge: Bridge started.  IPC dir: C:\Users\majes\AppData\Local\Temp\uefn_bridge
```

Secondary: the release ships no `bridge-dir` directory, so the example path does not
exist in a fresh unpack.

**Impact.** A user copying the example verbatim gets a server the client reports as
"Connected" while every bridge tool fails — the precise failure mode INSTALL.md:131
warns about at length, manufactured by the doc's own default example.

**Suggested fix.** Drop the `env` block from the default examples; the temp default is
machine-agnostic and needs no configuration, as `bridge_paths.py` itself says. If it
stays, state that the variable must also be set in UEFN's own process environment, and
show how.

---

## D4 — MEDIUM — the version-stamp generator is not in the repo

`python/bridge_version.py` — byte-identical in repo and release — contains:

```python
BRIDGE_VERSION = "0.1.1"
```

while `package.json` reads `"version": "0.1.4"`.

The file's own header says it is *"GENERATED by scripts/release.mjs at version bump"*,
and its body references `scripts/sync-powertools.mjs`. **Neither script exists:**

```
scripts\release.mjs            False
scripts\sync-powertools.mjs    False
scripts\sync-to-project.mjs    True     <- the only script present
```

`package.json` has no release script either — only `start`, `build`, `sync:project`,
`test`. So the stamp cannot be regenerated by anything in this repo, which is why it is
stuck three patch versions behind.

**Impact.** Compounds D2 — the stamp the sync compares is wrong even where the sync can
run. Also makes INSTALL.md:87 ("the launcher footer shows the bridge version currently
running") report a version that was never released. The header comment's own warning
applies: *"if the two ever diverged, that comparison would be meaningless."* They have
diverged.

---

## D5 — MEDIUM — INSTALL.md:34 states UEFN does not auto-run `init_unreal.py`; it does

> UEFN does not auto-run third-party `init_unreal.py` on its own

With `"bEnablePythonForProject": true` in the `.uefnproject`, UEFN auto-ran it as a
startup script — see the D1 log excerpt. No manual import was issued.

**Impact.** Misleads users about whether the manual step is needed. More significantly,
auto-run *plus* the documented manual `import init_unreal` is a plausible route into
the known issue at INSTALL.md:75-77 (*"Bridge started twice … missing/mismatched
session token"*). In this session the guard held —

```
[2026.08.30-07.05.02:737] LogPython: uefn_bridge: Bridge already running.
```

— but that pairing is worth investigating as a root cause of that open issue.

---

## D6 — MEDIUM — `.mcp.json` location guidance is self-contradictory for UEFN projects

**INSTALL.md:139** places `.mcp.json` in

> the same folder that directly contains your project's `.uefnproject` file (the same folder where you created `Content/Python/` in step 1 above)

Per D1 those are **two different folders** in any real UEFN project. **INSTALL.md:161**
adds a third constraint — Claude Code reads `.mcp.json` only from the directory it is
launched in, never from parent folders. INSTALL.md:141 and :143 repeat the same
equivalence.

**Impact.** The constraints cannot all be satisfied as written. In this install Claude
Code launches from `...\Plugins\ChaosValley\Content`, so `.mcp.json` had to go there —
not next to the `.uefnproject` as documented.

**Suggested fix.** State the rule purely as "the directory you launch Claude Code from"
and drop the `.uefnproject` / `Content` equivalence claim. The same wording appears for
Gemini CLI project-local config at INSTALL.md:228.

---

## D7 — LOW — internal contradiction on path separators

**INSTALL.md:118** mandates forward slashes everywhere, explicitly to avoid
backslash-escaping mistakes. **INSTALL.md:319** then gives an example using doubled
backslashes, and INSTALL.md:323 instructs the reader to keep them:

```json
"VERSE_LSP_CHECK_SCRIPT": "<POWER_TOOLS_DIR>\\skills\\uefn\\verse_lsp_check.py"
```

Pick one. Forward slashes work here and match the rest of the document.

---

## D8 — LOW — engine-side path in the manual fix does not exist by default

**INSTALL.md:81 / :89** direct users to `FortniteGame/Content/Python`. On this machine
`C:\Program Files\Epic Games\Fortnite\FortniteGame\Content` exists but has no `Python`
subfolder, so the "copy the files there too" fix requires creating it first — unstated.

---

## OPEN — launcher renders blank, then aborts UEFN with no crash handler

**Not yet root-caused.** Recorded so it isn't lost; a clean-room retest is pending.

**Observed.** After `import pt`, the Power Tools window opened as a solid white
rectangle — no text, controls, or layout. Dragging it by the title bar terminated UEFN
instantly: no UE crash reporter, no crash dialog, and **no crash dump written**
(`Saved\Crashes` holds nothing for that timestamp).

**Log.** Ends mid-session with no shutdown sequence and no Python traceback:

```
[2026.08.30-07.05.10:710] LogPython: uefn_launcher: Launcher window opened.
[2026.08.30-07.05.10:710] LogPython: Trashbyrd: Launcher opened by user request
                                     <- end of file
```

**Suspected mechanism.** The codebase documents this failure class itself. Every window
is a Tk window pumped by `unreal.register_slate_post_tick_callback` calling `update()`
rather than running `mainloop()` — `python/uefn_launcher.py:626-632` (registration at
:567):

> …there is no owning event loop able to service a selection request. That leaves
> Tcl/Tk unable to hand off the clipboard and it aborts the whole host process — real
> crash stack: `ucrtbase -> python311 -> _tkinter -> tcl86t (x5) -> tk86t -> user32 …
> Abort signal received`, i.e. it used to crash UEFN itself, not just the window.

A C-runtime `abort()` bypasses UE's crash reporter, matching the missing dump exactly.
The blank render is consistent with the tick pump never painting the window; the abort
on drag is consistent with a Win32 modal move/size loop starving or re-entering that
pump. The documented case is the **clipboard** path, which was **not** exercised here —
so if confirmed, this is a second route into the same abort.

**Confound to rule out first.** Python was force-enabled mid-session, not at startup:

```
[2026.08.30-07.04.53:422] LogPython: Warning: Python enabled via IPythonScriptPlugin::ForceEnablePythonAtRuntime
[2026.08.30-07.04.53:423] LogSlate: Prevented a slow task dialog from being summoned while a context menu was open
```

The tick pump registered into an already-running editor with a context menu open.
Retest with Python enabled **before** launch, and confirm `ForceEnablePythonAtRuntime`
is absent from the log. If the launcher then paints correctly, this is a
runtime-enable-only fragility rather than a general defect — still worth hardening,
since users hit it whenever they enable the plugin mid-session exactly as the docs
invite (INSTALL.md:6, INSTALL.md:51).

---

## Not a defect — confirmed correct

- **Node.js 18+ is documented** (INSTALL.md:7), including `npm install` / `npm start`
  for source clones (INSTALL.md:102-104). Minor gap: nothing states plainly that the
  in-UEFN Python tools work with no Node installed at all, so a user without Node may
  assume the whole product is unusable.
- **Unpack layout guidance is accurate** (INSTALL.md:30) — `uefn-server.mjs`,
  `package.json`, `python/`, `skills/` land at top level exactly as described.
- **Server key `powertools`** avoids collision with Epic's `uefn` key as intended.
- **`skills/uefn/verse_lsp_check.py`** ships and is present (97,876 bytes).
- **The `import init_unreal` no-op warning** (INSTALL.md:68) and the
  `importlib.reload(uefn_bridge)` workaround are correct Python semantics.

---

## Suggested priority

`D1`, `D2`, and `D6` share one root cause: the assumption that a UEFN project is
`<root>/Content/...` when it is really `<root>/Plugins/<plugin>/Content/...`. One
conceptual fix likely closes all three.

`D3` is the most urgent user-facing item independent of that: it is the default example
in every supported client walkthrough, and it produces precisely the "Connected but
nothing works" confusion the document spends three separate passages warning against.
