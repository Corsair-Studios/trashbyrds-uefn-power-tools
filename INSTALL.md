# Install

## System requirements

- **UEFN** (Unreal Editor for Fortnite) installed, with your project open.
- The **Python Editor Script Plugin** enabled in UEFN (`Edit -> Plugins`, search "Python Editor Script Plugin", enable it, restart UEFN if prompted).
- **Node.js 18+** on the machine running the MCP server.
- An MCP-capable client (e.g. Claude Code) to talk to the server.

## 1. Install the Python bridge into your UEFN project

Copy the **contents** of this repo's `python/` folder into your UEFN project's `Content/Python/` directory.

`Content/Python` lives inside the folder that holds your project's `.uefnproject` file — that's your UEFN project root. If a `Python` folder doesn't already exist under `Content`, create it:

```
<your-uefn-project>/Content/Python/
```

After copying, `<your-uefn-project>/Content/Python/` should contain `init_unreal.py` alongside the rest of the files from this repo's `python/` folder.

- `init_unreal.py` auto-starts the Python bridge when UEFN loads the project — no manual step needed on subsequent launches.
- If UEFN prompts you to enable the Python Editor Script Plugin, accept it and restart UEFN.
- Once loaded, open UEFN's Python console and run `import pt` to open the Power Tools window.

## 2. Run the MCP server

From this repo:

```bash
npm install
npm start
```

`npm start` runs `tsx uefn-server.ts`. Point your MCP client's configuration at that command (or at `npx tsx <path-to-this-repo>/uefn-server.ts`) so it launches the server as an MCP tool provider.

## 3. How it connects

The MCP server and the in-UEFN Python bridge communicate through file-based IPC in the OS temp directory — no network port, no additional UEFN plugin. Keep UEFN open with your project loaded whenever you want live queries or edits to reach the editor; if UEFN isn't running (or the bridge hasn't started), the MCP server will report the bridge as unreachable.

## Updating

Pull the latest version of this repo and re-copy the contents of `python/` into `<your-uefn-project>/Content/Python/`, then restart UEFN (or reload the bridge module from the Python console) to pick up changes.
