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
 *   3. DEFAULT_DEST             (documented default, below)
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

// Documented default destination. Override with --dest or
// UEFN_PROJECT_PYTHON_DIR — this is only the fallback, not the only option.
const DEFAULT_DEST = path.join(
  'C:\\', 'Users', 'majes', 'OneDrive', 'Documents', 'Fortnite Projects',
  'StarWars', 'Content', 'Python',
);

const SKIP_NAMES = new Set(['__pycache__']);
const SKIP_EXTS = new Set(['.pyc', '.pyo']);

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
  3. Documented default: ${DEFAULT_DEST}
`);
}

function resolveDest(cliDest) {
  if (cliDest) {
    return { dest: cliDest, source: '--dest flag' };
  }
  if (process.env.UEFN_PROJECT_PYTHON_DIR) {
    return { dest: process.env.UEFN_PROJECT_PYTHON_DIR, source: 'UEFN_PROJECT_PYTHON_DIR env var' };
  }
  return { dest: DEFAULT_DEST, source: 'documented default' };
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
