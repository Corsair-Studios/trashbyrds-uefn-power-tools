/*
 * Trashbyrd's UEFN Power Tools — standalone version helpers.
 * Replaces TycoonAgents' src/shared/bridgeVersion (not present in this repo).
 * Same exported symbol names/shapes as that module's isNumericVersion /
 * isBridgeVersionNewer, so uefn-server.ts needed no logic changes — only the
 * import path changed.
 */
/**
 * True iff `v` is a well-formed numeric version string, ignoring any
 * trailing `-suffix`: one or more dot-separated components, every
 * component a non-empty run of digits (e.g. "0.0.441", "1", "2026.8.21-b").
 */
export function isNumericVersion(v: string): boolean {
  if (typeof v !== "string" || v.length === 0) return false;
  const base = stripVersionSuffix(v);
  if (base.length === 0) return false;
  return base.split(".").every((part) => part.length > 0 && /^\d+$/.test(part));
}
/**
 * True iff `candidate` is strictly newer than `baseline`, comparing
 * dot-separated components NUMERICALLY (not lexicographically) left to
 * right. Never throws.
 */
export function isBridgeVersionNewer(candidate: string, baseline: string): boolean {
  try {
    const toParts = (v: string): number[] =>
      stripVersionSuffix(v)
        .split(".")
        .map((p) => {
          const n = Number.parseInt(p, 10);
          return Number.isFinite(n) ? n : NaN;
        });
    const a = toParts(candidate);
    const b = toParts(baseline);
    const len = Math.max(a.length, b.length);
    for (let i = 0; i < len; i++) {
      const av = a[i] ?? 0;
      const bv = b[i] ?? 0;
      if (Number.isNaN(av) || Number.isNaN(bv)) return false;
      if (av > bv) return true;
      if (av < bv) return false;
    }
    return false; // equal
  } catch {
    return false;
  }
}
function stripVersionSuffix(v: string): string {
  const dashIndex = v.indexOf("-");
  return dashIndex === -1 ? v : v.slice(0, dashIndex);
}
