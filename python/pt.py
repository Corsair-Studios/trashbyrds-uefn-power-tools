"""
pt — Trashbyrd's Power Tools Quick Launcher
============================================
In UEFN's Python console, type:  import pt

Every import first makes sure Power Tools is actually initialized
(bridge + native toolsets, via ``init_unreal``), then reloads
``uefn_launcher`` so freshly synced tool updates are picked up
immediately, and opens the launcher UI.

WHY THE BOOTSTRAP: UEFN only auto-runs a project's ``init_unreal.py``
if the project is already mounted when Python initializes. With Epic's
MCP server set to auto-start, Python now initializes at editor boot —
before any project is open — so the auto-run never fires and a user's
first contact with Power Tools is often this module. Running our
``init_unreal.py`` here (only when it hasn't already run, and loaded BY
FILE PATH — the bare module name now belongs to Epic, see the bootstrap
comment below) means ``import pt`` alone brings up the bridge, the
toolsets, and the launcher, instead of a launcher whose footer says the
bridge is disconnected.

WHY THE DEFERRED SELF-REMOVAL: this module removes itself from
``sys.modules`` so that ``import pt`` works again next time (a plain
re-import of a cached module is a silent no-op). It used to do that
pop at module scope, i.e. *during* its own import — and Python 3.11's
import machinery then fails to finalize the import and surfaces
``KeyError: 'pt'`` as an error traceback in the console, right after
the launcher opens. The pop now happens on a one-shot Slate tick,
after the import has completed, so the console stays clean.
"""

import sys

try:
    try:
        import unreal
        _warn = unreal.log_warning
        _HAS_UNREAL = True
    except ImportError:
        _warn = print
        _HAS_UNREAL = False

    # ── Bootstrap: make sure OUR init_unreal.py has run this session ──
    # Auto-run only happens when Python initializes AFTER the project is
    # mounted (see module docstring), so this is the normal path now, not
    # an edge case.
    #
    # LOADED BY FILE PATH, NEVER BY `import init_unreal`. Epic's
    # experimental Toolsets plugins (EditorToolset, ToolsetRegistry, ...)
    # ship their own init_unreal.py, and their directories sit ahead of
    # the project's on sys.path — so the bare module name resolves to
    # EPIC'S file, silently re-running their toolset registration (a wall
    # of "Toolset already registered" warnings) while ours never runs.
    # Confirmed in the field on the first 0.1.5 test session. This file
    # sits beside our init_unreal.py, so its own directory is the one
    # unambiguous way to name the right file.
    #
    # "Has it run?" is checked via uefn_bridge in sys.modules — our
    # init_unreal.py registers that itself — because it is true no matter
    # HOW our file ran: UEFN's startup-script auto-run (when that fires),
    # or this bootstrap. A module-name sentinel would miss the auto-run
    # case and double-start the bridge.
    if 'uefn_bridge' not in sys.modules:
        try:
            if _HAS_UNREAL:
                unreal.log("[pt] Power Tools has not initialized this session — running init_unreal.py")
            import importlib.util
            import os
            _init_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 'init_unreal.py')
            _spec = importlib.util.spec_from_file_location(
                'trashbyrd_init_unreal', _init_path)
            _mod = importlib.util.module_from_spec(_spec)
            sys.modules['trashbyrd_init_unreal'] = _mod
            try:
                _spec.loader.exec_module(_mod)
            except Exception:
                sys.modules.pop('trashbyrd_init_unreal', None)
                raise
        except Exception as e:
            _warn(f"[pt] init_unreal bootstrap failed (launcher will still open): {e}")

    try:
        if 'uefn_launcher' in sys.modules:
            import importlib
            uefn_launcher = importlib.reload(sys.modules['uefn_launcher'])
        else:
            import uefn_launcher  # type: ignore

        uefn_launcher.show_launcher()
    except Exception as e:
        _warn(f"[pt] Failed to launch Trashbyrd's Power Tools: {e}")

except Exception as e:
    print(f"[pt] Unexpected error: {e}")

finally:
    # Deferred self-removal — see module docstring. Falls back to the old
    # inline pop (and its cosmetic KeyError) only if the tick API is
    # unavailable, so re-importability is never lost.
    def _pt_deferred_forget():
        sys.modules.pop('pt', None)

    _deferred = False
    try:
        import unreal as _u

        _pt_tick = [None]

        def _pt_forget_tick(_dt):
            try:
                _pt_deferred_forget()
            finally:
                if _pt_tick[0] is not None:
                    _u.unregister_slate_post_tick_callback(_pt_tick[0])
                    _pt_tick[0] = None

        _pt_tick[0] = _u.register_slate_post_tick_callback(_pt_forget_tick)
        _deferred = True
    except Exception:
        pass

    if not _deferred:
        _pt_deferred_forget()
