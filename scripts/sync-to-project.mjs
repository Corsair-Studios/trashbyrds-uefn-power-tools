#!/usr/bin/env node
/**
 * sync-to-project.mjs
 *
 * Power Tools is source of truth for its Python tools. This script copies
 * them ONE WAY from this repo's python/ directory into a live UEFN
 * project's Content/Python directory, so a developer can pick up the
 * latest tools while building.
 *
 * It NEVER writes back into this repo, and NEVER deletes anything in the
 * destination — it only adds new files and overwrites files it manages
 * when their content actually changed (additive-overwrite only).
 *
 * Destination resolution ladder:
 *   1. --dest=<path>            (CLI flag, always wins)
 *   2. UEFN_PROJECT_PYTHON_DIR  (environment variable override)
 *   3. Auto-discovery           (scan candidate roots, below)
 *
 * There is deliberately no hardcoded default path. This used to end in a
 * literal C:\Users\majes\OneDrive\Documents\Fortnite Projects\StarWars\
 * Content\Python, which broke the moment the machine was reimaged and the
 * projects moved to C:\UEFN — and which encoded the wrong layout anyway
 * (UEFN nests Content under Plugins/<PluginName>/, not beside the
 * .uefnproject). Auto-discovery finds the real thing on any machine, and
 * refuses to guess when the answer is ambiguous.
 *
 * Usage:
 *   node scripts/sync-to-project.mjs [--dry-run] [--dest=<path>]
 */

import { fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';
import crypto from 'node:crypto';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Source is always relative to this script, never a hardcoded absolute
// path, so this works on any machine that clones the repo.
const REPO_ROOT = path.resolve(__dirname, '..');
const SOURCE_DIR = path.join(REPO_ROOT, 'python');

const SKIP_NAMES = new Set(['__pycache__']);
const SKIP_EXTS = new Set(['.pyc', '.pyo']);

// Levels to walk up from a .../Content/Python looking for the owning
// *.uefnproject. 4 for the real UEFN layout (Python -> Content -> <plugin>
// -> Plugins -> project), 2 for the older flat one; 6 leaves headroom
// without walking far enough to hit a drive root.
const UEFNPROJECT_SEARCH_DEPTH = 6;

function isDir(p) {
  try {
    return fs.statSync(p).isDirectory();
  } catch {
    return false;
  }
}

function safeReaddir(p) {
  try {
    return fs.readdirSync(p);
  } catch {
    return [];
  }
}

function hasUefnProject(dir) {
  return safeReaddir(dir).some((name) => name.toLowerCase().endsWith('.uefnproject'));
}

/**
 * Walk upward from a .../Content/Python directory to the directory holding
 * the owning *.uefnproject. Returns null if there isn't one.
 *
 * Deliberately not a fixed-depth dirname() chain: the project file sits 4
 * levels up in a real UEFN project and 2 in the legacy flat layout, so any
 * fixed depth makes the other layout invisible.
 */
function findUefnProjectDir(startDir) {
  let dir = path.resolve(startDir);
  for (let i = 0; i <= UEFNPROJECT_SEARCH_DEPTH; i++) {
    if (hasUefnProject(dir)) return dir;
    const parent = path.dirname(dir);
    if (!parent || parent === dir) return null;
    dir = parent;
  }
  return null;
}

/**
 * Roots that plausibly hold UEFN projects on this machine, most specific
 * first. UEFN_PROJECTS_ROOT lets anyone point this at somewhere else
 * entirely without touching the script.
 */
function candidateRoots() {
  const roots = [];
  const add = (r) => {
    if (r && !roots.includes(r)) roots.push(r);
  };

  if (process.env.UEFN_PROJECTS_ROOT) add(path.resolve(process.env.UEFN_PROJECTS_ROOT));

  const home = process.env.USERPROFILE || process.env.HOME || '';
  if (home) {
    add(path.join(home, 'Documents', 'Fortnite Projects'));
    add(path.join(home, 'OneDrive', 'Documents', 'Fortnite Projects'));
    // OneDrive can redirect Documents under a tenant-branded folder name.
    for (const entry of safeReaddir(home)) {
      if (entry.toLowerCase().startsWith('onedrive')) {
        add(path.join(home, entry, 'Documents', 'Fortnite Projects'));
      }
    }
  }

  // A plain drive-root projects folder, which is what this repo's own
  // author uses and a common convention generally -- on any drive letter,
  // not just C:/D:. A:/B: skipped (legacy removable-media letters).
  for (const letter of 'CDEFGHIJKLMNOPQRSTUVWXYZ') {
    const conv = letter + ':\\UEFN';
    if (isDir(conv)) add(conv);
  }

  return roots.filter(isDir);
}

/**
 * Find every existing <project>/.../Content/Python under the candidate
 * roots, in both the real UEFN layout and the legacy flat one. Only
 * directories that already exist and are owned by a *.uefnproject count —
 * this script never creates a destination tree, so a path that isn't there
 * yet is not a candidate.
 */
function discoverDestinations() {
  const hits = [];
  const seen = new Set();
  const record = (p) => {
    const key = path.resolve(p).toLowerCase();
    if (seen.has(key) || !isDir(p)) return;
    if (findUefnProjectDir(p) === null) return;
    seen.add(key);
    hits.push(path.resolve(p));
  };

  for (const root of candidateRoots()) {
    for (const projectName of safeReaddir(root)) {
      const projectDir = path.join(root, projectName);
      if (!isDir(projectDir)) continue;

      // Real UEFN layout: <project>/Plugins/<PluginName>/Content/Python
      const pluginsDir = path.join(projectDir, 'Plugins');
      for (const pluginName of safeReaddir(pluginsDir)) {
        record(path.join(pluginsDir, pluginName, 'Content', 'Python'));
      }

      // Legacy flat layout: <project>/Content/Python
      record(path.join(projectDir, 'Content', 'Python'));
    }
  }

  return hits;
}

function parseArgs(argv) {
  let dest = null;
  let dryRun = false;
  for (const arg of argv) {
    if (arg === '--dry-run') {
      dryRun = true;
    } else if (arg.startsWith('--dest=')) {
      dest = arg.slice('--dest='.length);
    } else if (arg === '--dest') {
      throw new Error('--dest requires a value, e.g. --dest="C:\path\to\Python"');
    } else if (arg === '--help' || arg === '-h') {
      printHelp();
      process.exit(0);
    } else {
      throw new Error(`Unrecognized argument: ${arg}`);
    }
  }
  return { dest, dryRun };
}

function printHelp() {
  console.log(`sync-to-project.mjs

Copies this repo's python/ tools into a live UEFN project's Content/Python
directory. Additive-overwrite only: never deletes files, never touches
files outside the destination it is given.

Options:
  --dry-run          Report what would change without writing anything.
  --dest=<path>       Destination Content/Python directory.

Destination resolution order:
  1. --dest=<path>
  2. UEFN_PROJECT_PYTHON_DIR environment variable
  3. Auto-discovery: scans for <project>/Plugins/<PluginName>/Content/Python
     (and the legacy <project>/Content/Python) under, in order:
       - UEFN_PROJECTS_ROOT, if set
       - %USERPROFILE%\\Documents\\Fortnite Projects (incl. OneDrive variants)
       - C:\\UEFN and D:\\UEFN
     Exactly one match is used automatically. Zero or several is an error
     that lists what was found — this script never guesses between projects.
`);
}

function resolveDest(cliDest) {
  if (cliDest) {
    return { dest: cliDest, source: '--dest flag' };
  }
  if (process.env.UEFN_PROJECT_PYTHON_DIR) {
    return { dest: process.env.UEFN_PROJECT_PYTHON_DIR, source: 'UEFN_PROJECT_PYTHON_DIR env var' };
  }

  const found = discoverDestinations();

  if (found.length === 1) {
    return { dest: found[0], source: 'auto-discovered' };
  }

  if (found.length === 0) {
    console.error('Error: could not find a UEFN project Content/Python directory to sync into.');
    console.error('');
    console.error('Searched these roots:');
    const roots = candidateRoots();
    if (roots.length === 0) {
      console.error('  (none of the candidate roots exist on this machine)');
    } else {
      for (const r of roots) console.error(`  ${r}`);
    }
    console.error('');
    console.error('...for <project>/Plugins/<PluginName>/Content/Python (the real UEFN layout)');
    console.error('or <project>/Content/Python (legacy), owned by a *.uefnproject.');
    console.error('');
    console.error('Note this script never creates the destination tree, so the Content/Python');
    console.error('folder has to exist already. Point it somewhere explicitly with:');
    console.error('  1. --dest="<path>"');
    console.error('  2. UEFN_PROJECT_PYTHON_DIR=<path>');
    console.error('  3. UEFN_PROJECTS_ROOT=<folder holding your projects>');
    process.exit(1);
  }

  console.error(`Error: found ${found.length} UEFN project Content/Python directories; refusing to guess.`);
  console.error('');
  for (const p of found) console.error(`  ${p}`);
  console.error('');
  console.error('Pick one explicitly:');
  console.error(`  node scripts/sync-to-project.mjs --dest="${found[0]}"`);
  console.error('or set UEFN_PROJECT_PYTHON_DIR to the one you want.');
  process.exit(1);
}

function hashFile(filePath) {
  const buf = fs.readFileSync(filePath);
  return crypto.createHash('sha256').update(buf).digest('hex');
}

function listSourceFiles(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    if (entry.isDirectory()) {
      if (SKIP_NAMES.has(entry.name)) continue;
      // python/ is flat today, but recurse defensively in case that changes.
      files.push(...listSourceFiles(path.join(dir, entry.name)).map((f) => f));
      continue;
    }
    const ext = path.extname(entry.name).toLowerCase();
    if (SKIP_EXTS.has(ext)) continue;
    files.push(path.join(dir, entry.name));
  }
  return files;
}

function main() {
  const argv = process.argv.slice(2);
  let dest, dryRun, cliDest;
  try {
    ({ dest: cliDest, dryRun } = parseArgs(argv));
  } catch (err) {
    console.error(`Error: ${err.message}`);
    process.exit(1);
  }

  const { dest: destDir, source: destSource } = resolveDest(cliDest);

  if (!fs.existsSync(SOURCE_DIR) || !fs.statSync(SOURCE_DIR).isDirectory()) {
    console.error(`Error: source directory not found: ${SOURCE_DIR}`);
    console.error('This script resolves its source relative to itself and expects a python/ dir at the repo root.');
    process.exit(1);
  }

  if (!fs.existsSync(destDir) || !fs.statSync(destDir).isDirectory()) {
    console.error(`Error: destination directory does not exist: ${destDir}`);
    console.error(`Resolved via: ${destSource}`);
    console.error('');
    console.error('This script will never create the destination tree silently. Point it at an');
    console.error('existing UEFN project Content/Python directory using one of:');
    console.error('  1. --dest="<path>"');
    console.error('  2. UEFN_PROJECT_PYTHON_DIR=<path> environment variable');
    process.exit(1);
  }

  const sourceFiles = listSourceFiles(SOURCE_DIR);

  let copied = 0;
  let updated = 0;
  let unchanged = 0;
  const actions = [];

  for (const srcPath of sourceFiles) {
    const rel = path.relative(SOURCE_DIR, srcPath);
    const destPath = path.join(destDir, rel);

    if (!fs.existsSync(destPath)) {
      copied++;
      actions.push(`  [copy]      ${rel}`);
      if (!dryRun) {
        fs.mkdirSync(path.dirname(destPath), { recursive: true });
        fs.copyFileSync(srcPath, destPath);
      }
      continue;
    }

    const srcHash = hashFile(srcPath);
    const destHash = hashFile(destPath);
    if (srcHash === destHash) {
      unchanged++;
      continue;
    }

    updated++;
    actions.push(`  [update]    ${rel}`);
    if (!dryRun) {
      fs.copyFileSync(srcPath, destPath);
    }
  }

  console.log(`Power Tools -> project sync${dryRun ? ' (dry run)' : ''}`);
  console.log(`  source:      ${SOURCE_DIR}`);
  console.log(`  destination: ${destDir}  (via ${destSource})`);
  console.log('');
  if (actions.length > 0) {
    console.log(actions.join('\n'));
    console.log('');
  }
  console.log(`  copied:    ${copied}`);
  console.log(`  updated:   ${updated}`);
  console.log(`  unchanged: ${unchanged}`);
  if (dryRun) {
    console.log('');
    console.log('Dry run — nothing was written.');
  }
  console.log('');
  console.log('This script only adds/overwrites files present in python/. It never deletes');
  console.log('anything in the destination, so generated files (e.g. tag_inspect_report.json)');
  console.log('and __pycache__ are left untouched.');
}

main();
