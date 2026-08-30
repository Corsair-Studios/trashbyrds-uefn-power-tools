/**
 * verse_lsp_check.py ships in TWO places, and they must be byte-identical.
 *
 * - skills/uefn/verse_lsp_check.py — the canonical copy; what the MCP
 *   server spawns (via VERSE_LSP_CHECK_SCRIPT or its own discovery).
 * - python/verse_lsp_check.py — the copy that lands in a UEFN project's
 *   Content/Python, so the NATIVE toolset path (copy python/, import pt)
 *   is self-contained: a native-only user never unpacks skills/, and the
 *   in-editor verse_check tool must find the script beside itself.
 *
 * A duplicated file drifts the moment nothing checks it — this repo has
 * been burned by exactly that before (bridge_version.py sat three patch
 * versions stale because its generator didn't exist and nothing verified
 * it; see the release workflow's version gate). This test is the same
 * idea applied here: edit one copy, and the release fails until the other
 * is updated to match. `npm test` gates every release, so a drifted pair
 * cannot ship.
 */
import { test } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), '..');

test('python/verse_lsp_check.py is byte-identical to skills/uefn/verse_lsp_check.py', () => {
  const canonical = readFileSync(join(repoRoot, 'skills', 'uefn', 'verse_lsp_check.py'));
  const shipped = readFileSync(join(repoRoot, 'python', 'verse_lsp_check.py'));
  assert.ok(
    canonical.equals(shipped),
    'python/verse_lsp_check.py has drifted from skills/uefn/verse_lsp_check.py — ' +
    'copy the edited one over the other (skills/uefn/ is canonical) so both ' +
    'install paths ship the same code.'
  );
});
