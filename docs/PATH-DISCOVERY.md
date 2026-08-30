# Path discovery

How Power Tools finds a user's UEFN project on an arbitrary machine, and why it
does it the way it does. Referenced from `device_audit.py`, `init_unreal.py`,
`asset_usage.py`, `dependency_viewer.py`, and `health_scanner.py`.

This exists because path discovery is the single largest source of field
failures in this project. Every rule below was written after something broke.

## 1. There are two layouts, and the obvious one is wrong

UEFN does **not** put `Content` next to the `.uefnproject` file. It nests it
inside the project's plugin:

```
<project>/
  MyProject.uefnproject
  Plugins/
    MyProject/
      Content/          <- the real content root
        Python/         <- where the bridge is installed
```

The flat `<project>/Content/` layout appears in older projects and in some
templates, so both must be handled — but the plugin layout is the normal case
and must be tried first.

**Never derive the project root by fixed-depth `dirname()` chaining.** The
project file is 4 levels above `Content/Python` in the real layout and 2 in the
flat one, so any fixed depth makes the other layout invisible. Walk upward
looking for `*.uefnproject`, with a bounded number of steps (6 is the value used
throughout) so a miss terminates instead of climbing to the drive root.

**The project folder name is not the island name.** A folder called
`ChaosValley_` can hold plugin `ChaosValley`, whose island prefix is
`/ChaosValley/`. Renames, suffixes, and "MyGame v2" folders are all normal.
Probing `<root>/<island_name>` alone therefore misses real projects; also check
whether a candidate folder *contains* `Plugins/<island_name>`, which is a much
stronger signal than the folder's own name.

## 2. Multiple independent signals, de-duplicated

No single signal finds every machine's projects. Gather several, de-duplicate,
and let the validation gate (section 3) pick the winner. Any one of them
succeeding is enough, and a signal that fails must never raise — every probe is
wrapped so a wrong platform, a missing registry key, or a permission error
yields nothing rather than an exception.

Signal order, most authoritative first:

1. `UEFN_PROJECTS_ROOT` (section 5)
2. `%USERPROFILE%\Documents\Fortnite Projects`
3. `%USERPROFILE%\OneDrive\Documents\Fortnite Projects`
4. `%USERPROFILE%\OneDrive*\Documents\Fortnite Projects` — tenant-branded
   OneDrive folder names ("OneDrive - Contoso")
5. `%OneDrive%`, `%OneDriveConsumer%`, `%OneDriveCommercial%` + `\Documents\Fortnite Projects`
6. The registry "Personal" known folder (section 4)
7. `C:\UEFN`, `D:\UEFN` — a bare drive-root projects folder is a common
   convention and costs one stat call to check
8. The directory holding the project the running copy is inside (`init_unreal.py`
   only — see section 6)

OneDrive Known Folder Move is the reason 3–6 exist. A real user sat on a stale
engine copy for a long time because their projects lived under
`C:\Users\<name>\OneDrive\Documents\Fortnite Projects\` and only the plain
`~\Documents` path was checked.

## 3. Never trust a guess — validate

Everything in section 2 produces *candidates*. A candidate is only accepted
once it is validated against something real:

- **Best:** resolve a known island asset through the asset registry
  (`unreal.PackageName.long_package_name_to_filename`, or `load_asset` +
  `SystemLibrary.get_system_path`) and confirm the resulting `.uasset`/`.umap`
  actually exists under the candidate's `Content`. A wrong tree matches zero of
  them.
- **Weaker fallback**, when no registry samples are available: the candidate
  directory contains a `*.uefnproject`.

Offering several candidates costs only stat calls, so prefer a broad candidate
list with a strict gate over a narrow list with a loose one.

## 4. The Windows "Personal" known folder

Read `Personal` from
`HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders`
and expand environment variables in the result. This is the value Explorer and
file dialogs themselves use, so it is authoritative regardless of the
redirection scheme in play — OneDrive or otherwise. `winreg` is Windows-only
stdlib; guard the whole block so it is a no-op elsewhere.

## 5. `UEFN_PROJECTS_ROOT` — the escape hatch

Everything above is inference, and inference cannot cover every machine. A user
may keep projects on a work drive, a network share, or a path no convention
predicts. `UEFN_PROJECTS_ROOT` lets them state it outright, and it is checked
**first** so a user who sets it is never second-guessed.

Set it to the folder that *contains* project folders, not to a project itself:

```
setx UEFN_PROJECTS_ROOT "D:\Work\UEFN"
```

This is the answer to give any user whose tools cannot find their project. It
is documented for users in INSTALL.md.

## 6. What `unreal.Paths` does and does not tell you

**`unreal.Paths.project_dir()` does not return the user's island project.** In
UEFN it resolves to the embedded **FortniteGame** project inside the game
install; the user's island is only a mounted plugin. Trusting it unconditionally
once caused this codebase to scan the game install and report every real user
asset as a ghost.

If it is used at all, the result must be validated (section 3) — FortniteGame
ships a `.uproject` and never a `.uefnproject`, so a `.uefnproject` check
rejects it cleanly.

The reliable engine-side signal is the **asset anchor** in section 3: ask where
a real island asset lives on disk and derive the content root from that actual
path. It is layout-agnostic and location-agnostic by construction.

For `init_unreal.py` specifically, the strongest signal is simpler: UEFN runs
the project copy's `init_unreal.py` as a startup script, so `__file__` is
already inside the user's project. Walk up from it.

Note the asymmetry this creates: a copy running from the **engine** side has
nothing in its own path pointing at the user's projects. For a project outside
the Documents roots, `UEFN_PROJECTS_ROOT` is the only thing that will find it.

## 7. Where this lives in the code

| File | Function | Returns |
| --- | --- | --- |
| `init_unreal.py` | `_find_uefnproject_dir` | project dir for a `Content/Python` |
| `init_unreal.py` | roots 1–7 in the self-sync block | search roots |
| `asset_usage.py` | `_uefn_project_search_roots`, `_candidate_project_dirs`, `_default_location_project_roots` | dirs to which `Content` is appended (so: **plugin** dirs) |
| `dependency_viewer.py` | same three | same |
| `health_scanner.py` | `_uefn_project_search_roots`, `_candidate_project_dirs`, `_default_location_content_dirs` | `Content` dirs directly |
| `device_audit.py` | `_registry_fortnite_projects_roots`, `_registry_fortnite_project_candidates` | `Content` dirs, project dir as last resort |

The three tool modules deliberately hold their own copies rather than importing
a shared helper: a version-skewed sibling set is a real field failure mode here
(an engine-side copy can be older than the project copy), and a missing shared
import would break them all at once. See `bridge_paths.py`'s module docstring
for the same reasoning applied to the IPC path contract.
