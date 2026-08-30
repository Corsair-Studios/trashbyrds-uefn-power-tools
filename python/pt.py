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
first contact with Power Tools is often this module. Importing
``init_unreal`` here (only when it hasn't already run) means
``import pt`` alone brings up the bridge, the toolsets, and the
launcher, instead of a launcher whose footer says the bridge is
disconnected.

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

    # ── Bootstrap: make sure init_unreal has run this session ──────
    # Auto-run only happens when Python initializes AFTER the project is
    # mounted (see module docstring), so this is the normal path now, not
    # an edge case. A repeat `import init_unreal` when it HAS run is a
    # silent no-op by Python semantics, but skipping it via sys.modules
    # keeps the intent explicit and the log honest.
    if 'init_unreal' not in sys.modules:
        try:
            if _HAS_UNREAL:
                unreal.log("[pt] init_unreal has not run this session — starting Power Tools first")
            import init_unreal  # noqa: F401 — bridge, toolsets, menus
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
