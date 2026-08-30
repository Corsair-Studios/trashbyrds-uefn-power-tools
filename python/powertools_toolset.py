"""
Power Tools — native UEFN toolset registration
==============================================
Registers Power Tools' commands with UEFN's own Toolset Registry, so the
tools appear inside UEFN alongside Epic's built-in toolsets (Verse, PCG,
Niagara, UMG, ...) rather than only through an external MCP client.

WHY THIS EXISTS: the external path (Node MCP server + file IPC bridge +
a per-client config file) is a lot of moving parts for a user to get
right, and most of the install guide exists to explain it. Registering
here means a user who has copied python/ into their project gets the
tools with no Node, no config file, and no bridge — UEFN's own assistant
can call them directly.

This is ADDITIVE. It does not replace or disable the MCP server or the
file-IPC bridge; both continue to work exactly as before, and a user can
run all of them at once.

--------------------------------------------------------------------------
HOW THE REGISTRY WORKS (Engine/Plugins/Experimental/ToolsetRegistry)
--------------------------------------------------------------------------
A toolset is a ``unreal.ToolsetDefinition`` subclass decorated with
``@unreal.uclass()``. Tools are ``@toolset_registry.tool_call`` +
``@staticmethod`` methods. Registration happens through
``toolset_registry.registration.Registration([...]).register()``.

Two constraints from that API drive the shape of everything below:

1. **Static methods only.** Toolsets are Blueprint Function Libraries, so
   a tool cannot be an instance method. Epic's own toolsets are written
   the same way.

2. **Every parameter and the return type must be annotated, and the
   annotation must map to a UE type.** ``_types.python_to_unreal_type``
   accepts scalars, ``list[T]`` / ``set[T]`` / ``dict[str, T]`` (mapped to
   unreal.Array/Set/Map), ``Optional[T]``, and unreal.Object subclasses.

Constraint 2 is why **every tool here returns ``str`` holding JSON.**
Power Tools' handlers return deeply nested, heterogeneous structures —
``{"status": ..., "counts": {...}, "items": [{...}, ...]}`` — and a
``unreal.Map`` is homogeneous, so there is no faithful UE type for them.
Returning JSON text is lossless and is what the agent consuming these
tools wants anyway. The docstrings say so per tool, since the docstring
is what the agent sees.

--------------------------------------------------------------------------
IMPORTANT: the lazy uefn_bridge import
--------------------------------------------------------------------------
``import uefn_bridge`` calls ``start_bridge()`` at module scope (see that
file's "Auto-start on import" section). Importing it here at module load
would therefore spin up the file-IPC bridge — a tick callback, a polling
loop, and a heartbeat file — merely as a side effect of registering
toolsets, even for a user who only ever wanted the native path. So the
import is deferred into ``_call`` and only happens when a tool is
actually invoked.
"""

import json
import traceback

try:
    import unreal
    _HAS_UNREAL = True
except ImportError:
    _HAS_UNREAL = False

try:
    import toolset_registry
    from toolset_registry.registration import Registration
    _HAS_REGISTRY = True
except ImportError:
    # UEFN build without the ToolsetRegistry plugin, or a non-UEFN Python.
    # Everything below degrades to a clean no-op; the MCP/bridge path is
    # unaffected.
    _HAS_REGISTRY = False


_registration = [None]


def _call(method, params):
    """Dispatch one Power Tools command and return its result as JSON text.

    Errors are returned as ``{"error": ...}`` JSON rather than raised. A
    raised exception would reach the agent as an opaque UE script error,
    which loses the message that actually tells a user what went wrong;
    an error object keeps it readable and keeps every tool's return type
    honest (always JSON text, never sometimes-an-exception).
    """
    try:
        # Deferred deliberately — see the module docstring. Importing
        # uefn_bridge starts the file-IPC bridge.
        import uefn_bridge
    except Exception as exc:
        return json.dumps({
            "error": "could not import uefn_bridge: {}".format(exc),
            "hint": "uefn_bridge.py must sit beside this file in the "
                    "project's Content/Python folder.",
        })

    handler = uefn_bridge._METHODS.get(method)
    if handler is None:
        return json.dumps({
            "error": "unknown command: {}".format(method),
            "available": sorted(uefn_bridge._METHODS.keys()),
        })

    try:
        return json.dumps(handler(params or {}), default=str)
    except Exception as exc:
        try:
            unreal.log_warning(
                "powertools_toolset: {} failed: {}\n{}".format(
                    method, exc, traceback.format_exc()))
        except Exception:
            pass
        return json.dumps({
            "error": "{}: {}".format(type(exc).__name__, exc),
            "command": method,
        })


if _HAS_UNREAL and _HAS_REGISTRY:

    @unreal.uclass()
    class PowerToolsInspect(unreal.ToolsetDefinition):
        """Read-only inspection of a UEFN project: level contents, actor
        properties, devices, and assets.

        Every tool returns a JSON string.
        """

        @toolset_registry.tool_call
        @staticmethod
        def status() -> str:
            """Reports whether the Power Tools bridge is live, plus the current
            level name and actor count.

            Use this first to confirm the tools can see the editor at all.

            Returns:
                JSON: {"status", "level_name", "actor_count"}.
            """
            return _call("status", {})

        @toolset_registry.tool_call
        @staticmethod
        def list_commands() -> str:
            """Lists every Power Tools command available, with its parameters.

            Returns:
                JSON: {"count", "commands": [...]}.
            """
            return _call("list_commands", {})

        @toolset_registry.tool_call
        @staticmethod
        def get_level_info() -> str:
            """Summarizes the open level: name, actor count, and class breakdown.

            Returns:
                JSON object describing the level.
            """
            return _call("get_level_info", {})

        @toolset_registry.tool_call
        @staticmethod
        def list_devices() -> str:
            """Lists every Creative device in the open level.

            Returns:
                JSON: the devices found, with labels and classes.
            """
            return _call("list_devices", {})

        @toolset_registry.tool_call
        @staticmethod
        def get_property(actor_label: str, property_name: str) -> str:
            """Reads one property from one actor, found by its label.

            Args:
                actor_label: The actor's label as shown in the Outliner.
                property_name: The property to read.

            Returns:
                JSON with the property's value, or an error if not found.
            """
            return _call("get_property", {
                "actor_label": actor_label,
                "property_name": property_name,
            })

        @toolset_registry.tool_call
        @staticmethod
        def batch_get(
                property_name: str,
                filter_type: str = "",
                filter_value: str = "",
                fields: list[str] | None = None,
                max_results: int = 100,
                offset: int = 0) -> str:
            """Reads one property across many actors at once — the main bulk
            query. Prefer this over repeated get_property calls.

            Args:
                property_name: The property to read from each actor.
                filter_type: How to select actors, e.g. by class or label.
                    Empty means all actors.
                filter_value: The value the filter matches, glob allowed.
                fields: Extra per-actor fields to include.
                max_results: Page size.
                offset: Page offset, for paging through large levels.

            Returns:
                JSON: matched actors with the requested property, plus paging
                info.
            """
            return _call("batch_get", {
                "property_name": property_name,
                "filter_type": filter_type or None,
                "filter_value": filter_value or None,
                "fields": list(fields) if fields else None,
                "max_results": max_results,
                "offset": offset,
            })

        @toolset_registry.tool_call
        @staticmethod
        def batch_location(
                filter_type: str = "",
                filter_value: str = "",
                fields: list[str] | None = None,
                max_results: int = 100,
                offset: int = 0) -> str:
            """Reads world locations for many actors at once.

            Args:
                filter_type: How to select actors. Empty means all actors.
                filter_value: The value the filter matches, glob allowed.
                fields: Extra per-actor fields to include.
                max_results: Page size.
                offset: Page offset.

            Returns:
                JSON: matched actors with their locations.
            """
            return _call("batch_location", {
                "filter_type": filter_type or None,
                "filter_value": filter_value or None,
                "fields": list(fields) if fields else None,
                "max_results": max_results,
                "offset": offset,
            })

        @toolset_registry.tool_call
        @staticmethod
        def list_assets(
                path: str = "",
                class_filter: str = "",
                recursive: bool = True,
                limit: int = 200) -> str:
            """Lists assets in the project's content tree.

            Args:
                path: Content-browser path to list, e.g. /MyProject/Meshes.
                    Empty lists from the project root.
                class_filter: Restrict to one asset class.
                recursive: Whether to descend into subfolders.
                limit: Maximum assets returned.

            Returns:
                JSON: the assets found.
            """
            return _call("list_assets", {
                "path": path or None,
                "class_filter": class_filter or None,
                "recursive": recursive,
                "limit": limit,
            })

        @toolset_registry.tool_call
        @staticmethod
        def inspect_asset(asset_path: str, max_depth: int = 1) -> str:
            """Inspects one asset: its class, properties, and references.

            Args:
                asset_path: Full content path to the asset.
                max_depth: How deep to follow references.

            Returns:
                JSON describing the asset.
            """
            return _call("inspect_asset", {
                "asset_path": asset_path,
                "max_depth": max_depth,
            })

        @toolset_registry.tool_call
        @staticmethod
        def run_audit() -> str:
            """Runs the device audit over the open level.

            Returns:
                JSON: the audit findings.
            """
            return _call("run_audit", {})

    @unreal.uclass()
    class PowerToolsScan(unreal.ToolsetDefinition):
        """Project-wide sweeps: assets, dependencies, textures, materials,
        Niagara, file health, Verse tags, and moderation/IP pre-flight.

        These walk the whole project and can take a while on a large one.
        Every tool returns a JSON string.
        """

        @toolset_registry.tool_call
        @staticmethod
        def health_scan() -> str:
            """Scans the project's content on disk for file-health problems:
            zero-byte assets, oversized files, invalid or duplicate names, and
            over-deep paths.

            Returns:
                JSON: the issues found, grouped by kind.
            """
            return _call("health_scan", {})

        @toolset_registry.tool_call
        @staticmethod
        def dependency_scan(project_only: bool = True) -> str:
            """Traces the project's asset dependency graph.

            Args:
                project_only: Exclude engine and Fortnite content.

            Returns:
                JSON: the dependency graph and any orphans.
            """
            return _call("dependency_scan", {"project_only": project_only})

        @toolset_registry.tool_call
        @staticmethod
        def asset_sweep(project_only: bool = True) -> str:
            """Sweeps the project for unused assets, confirmed against the
            reverse-reference graph and Verse source text.

            Args:
                project_only: Exclude engine and Fortnite content.

            Returns:
                JSON: assets with no remaining references.
            """
            return _call("asset_sweep", {"project_only": project_only})

        @toolset_registry.tool_call
        @staticmethod
        def texture_find(
                texture_name: str,
                match_mode: str = "contains",
                project_only: bool = True) -> str:
            """Finds textures by name and reports where each is used.

            Args:
                texture_name: Name or fragment to search for.
                match_mode: How to match, e.g. contains or exact.
                project_only: Exclude engine and Fortnite content.

            Returns:
                JSON: matching textures and their usage.
            """
            return _call("texture_find", {
                "texture_name": texture_name,
                "match_mode": match_mode,
                "project_only": project_only,
            })

        @toolset_registry.tool_call
        @staticmethod
        def texture_summary(
                texture_name: str = "",
                match_mode: str = "contains",
                project_only: bool = True) -> str:
            """Summarizes texture usage across the project, grouped.

            Args:
                texture_name: Optional name filter.
                match_mode: How to match the name filter.
                project_only: Exclude engine and Fortnite content.

            Returns:
                JSON: the grouped usage summary.
            """
            return _call("texture_summary", {
                "texture_name": texture_name or None,
                "match_mode": match_mode,
                "project_only": project_only,
            })

        @toolset_registry.tool_call
        @staticmethod
        def texture_on_actor(actor_label: str) -> str:
            """Lists every texture used by one actor.

            Args:
                actor_label: The actor's label as shown in the Outliner.

            Returns:
                JSON: the textures that actor references.
            """
            return _call("texture_on_actor", {"actor_label": actor_label})

        @toolset_registry.tool_call
        @staticmethod
        def material_browse(project_only: bool = True) -> str:
            """Lists the project's materials and where they are used.

            Args:
                project_only: Exclude engine and Fortnite content.

            Returns:
                JSON: materials with usage counts.
            """
            return _call("material_browse", {"project_only": project_only})

        @toolset_registry.tool_call
        @staticmethod
        def material_unused(project_only: bool = True) -> str:
            """Finds materials nothing in the project references.

            Args:
                project_only: Exclude engine and Fortnite content.

            Returns:
                JSON: the unreferenced materials.
            """
            return _call("material_unused", {"project_only": project_only})

        @toolset_registry.tool_call
        @staticmethod
        def niagara_browse(project_only: bool = True) -> str:
            """Lists the project's Niagara systems.

            Args:
                project_only: Exclude engine and Fortnite content.

            Returns:
                JSON: the Niagara systems found.
            """
            return _call("niagara_browse", {"project_only": project_only})

        @toolset_registry.tool_call
        @staticmethod
        def niagara_usage() -> str:
            """Reports which actors in the level use which Niagara systems.

            Returns:
                JSON: Niagara usage per actor.
            """
            return _call("niagara_usage", {})

        @toolset_registry.tool_call
        @staticmethod
        def tag_inspect(
                label_pattern: str = "",
                fields: list[str] | None = None,
                include_location: bool = False,
                max_results: int = 200,
                offset: int = 0,
                project_dir: str = "") -> str:
            """Inspects Verse tags across the project and the open level.

            Args:
                label_pattern: Restrict to actors whose label matches this
                    glob. Empty means all.
                fields: Extra per-actor fields to include.
                include_location: Include each actor's world location.
                max_results: Page size.
                offset: Page offset.
                project_dir: Override the project directory to scan. Leave
                    empty to auto-detect.

            Returns:
                JSON: tag usage findings.
            """
            return _call("tag_inspect", {
                "label_pattern": label_pattern or None,
                "fields": list(fields) if fields else None,
                "include_location": include_location,
                "max_results": max_results,
                "offset": offset,
                "project_dir": project_dir or None,
            })

        @toolset_registry.tool_call
        @staticmethod
        def moderation_scan(
                max_items: int = 500,
                include_hashes: bool = False,
                project_dir: str = "") -> str:
            """Scans the project for content that risks a moderation or IP
            rejection. Run this before submitting an island.

            Args:
                max_items: Maximum findings to return.
                include_hashes: Include content hashes for each finding.
                project_dir: Override the project directory to scan. Leave
                    empty to auto-detect.

            Returns:
                JSON: findings with severity counts.
            """
            return _call("moderation_scan", {
                "max_items": max_items,
                "include_hashes": include_hashes,
                "project_dir": project_dir or None,
            })

        @toolset_registry.tool_call
        @staticmethod
        def moderation_report_read() -> str:
            """Reads back the most recently saved moderation report.

            Returns:
                JSON: the saved report, or an error if none exists.
            """
            return _call("moderation_report_read", {})

    @unreal.uclass()
    class PowerToolsEdit(unreal.ToolsetDefinition):
        """Tools that MODIFY the open level: setting properties, spawning,
        duplicating, and moving actors.

        These change the user's project. Prefer the inspect tools when only
        reading. Every tool returns a JSON string.
        """

        @toolset_registry.tool_call
        @staticmethod
        def select_actor(actor_label: str) -> str:
            """Selects one actor in the editor, by label.

            Args:
                actor_label: The actor's label as shown in the Outliner.

            Returns:
                JSON confirming the selection.
            """
            return _call("select_actor", {"actor_label": actor_label})

        @toolset_registry.tool_call
        @staticmethod
        def set_property(actor_label: str, property_name: str, value: str) -> str:
            """Sets one property on one actor.

            Args:
                actor_label: The actor's label as shown in the Outliner.
                property_name: The property to set.
                value: The new value, as text. It is coerced to the
                    property's real type.

            Returns:
                JSON confirming the change, or an error.
            """
            return _call("set_property", {
                "actor_label": actor_label,
                "property_name": property_name,
                "value": value,
            })

        @toolset_registry.tool_call
        @staticmethod
        def batch_set(
                property_name: str,
                value: str,
                filter_type: str = "",
                filter_value: str = "",
                dry_run: bool = True) -> str:
            """Sets one property across many actors at once.

            Defaults to a dry run. Call it once with dry_run true, show the
            user what would change, and only then call again with dry_run
            false.

            Args:
                property_name: The property to set on each matched actor.
                value: The new value, as text.
                filter_type: How to select actors. Empty means all actors.
                filter_value: The value the filter matches, glob allowed.
                dry_run: When true, report what would change without
                    changing anything.

            Returns:
                JSON: what changed, or what would change.
            """
            return _call("batch_set", {
                "property_name": property_name,
                "value": value,
                "filter_type": filter_type or None,
                "filter_value": filter_value or None,
                "dry_run": dry_run,
            })

        @toolset_registry.tool_call
        @staticmethod
        def spawn_actor(
                asset_path: str,
                label: str = "",
                location: list[float] | None = None,
                rotation: list[float] | None = None,
                scale: list[float] | None = None) -> str:
            """Spawns an actor from an asset into the open level.

            Args:
                asset_path: Full content path to the asset to spawn.
                label: Label for the new actor. Empty uses a default.
                location: World location as [x, y, z].
                rotation: Rotation as [pitch, yaw, roll].
                scale: Scale as [x, y, z].

            Returns:
                JSON describing the spawned actor.
            """
            return _call("spawn_actor", {
                "asset_path": asset_path,
                "label": label or None,
                "location": list(location) if location else None,
                "rotation": list(rotation) if rotation else None,
                "scale": list(scale) if scale else None,
            })

        @toolset_registry.tool_call
        @staticmethod
        def duplicate_actor(
                actor_label: str,
                new_label: str = "",
                offset: list[float] | None = None) -> str:
            """Duplicates an existing actor.

            Args:
                actor_label: Label of the actor to duplicate.
                new_label: Label for the copy. Empty uses a default.
                offset: Offset the copy by [x, y, z] from the original.

            Returns:
                JSON describing the new actor.
            """
            return _call("duplicate_actor", {
                "actor_label": actor_label,
                "new_label": new_label or None,
                "offset": list(offset) if offset else None,
            })

        @toolset_registry.tool_call
        @staticmethod
        def set_transform(
                actor_label: str,
                location: list[float] | None = None,
                rotation: list[float] | None = None,
                scale: list[float] | None = None,
                name: str = "") -> str:
            """Sets an actor's transform.

            Only the components you pass are changed; omit the rest to leave
            them alone.

            Args:
                actor_label: Label of the actor to move.
                location: New world location as [x, y, z].
                rotation: New rotation as [pitch, yaw, roll].
                scale: New scale as [x, y, z].
                name: Optional new name for the actor.

            Returns:
                JSON confirming the new transform.
            """
            return _call("set_transform", {
                "actor_label": actor_label,
                "location": list(location) if location else None,
                "rotation": list(rotation) if rotation else None,
                "scale": list(scale) if scale else None,
                "name": name or None,
            })

    _TOOLSETS = [PowerToolsInspect, PowerToolsScan, PowerToolsEdit]

else:
    _TOOLSETS = []


def register():
    """Register the Power Tools toolsets with UEFN's Toolset Registry.

    Returns True if registration happened, False otherwise — a False is a
    normal outcome, not a failure: it means this UEFN build has no Toolset
    Registry, or the registry is not available yet. Never raises, because
    this is called from init_unreal.py during editor startup and must not
    be able to take the rest of Power Tools down with it.
    """
    if not _TOOLSETS:
        return False
    if _registration[0] is not None:
        return True
    try:
        reg = Registration(_TOOLSETS)
        if not reg.register():
            return False
        _registration[0] = reg
        return True
    except Exception as exc:
        try:
            unreal.log_warning(
                "powertools_toolset: registration failed: {}\n{}".format(
                    exc, traceback.format_exc()))
        except Exception:
            pass
        return False


def unregister():
    """Unregister the toolsets. Safe to call when not registered."""
    reg = _registration[0]
    if reg is None:
        return
    try:
        reg.unregister()
    except Exception:
        pass
    _registration[0] = None
