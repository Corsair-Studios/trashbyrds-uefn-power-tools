# One Shot Rogue

**Status:** Idea
**Platforms:** UEFN, Roblox

## Pitch
Get through a series of randomized mini-events **without failing a single one** to reach the end.
One mistake and the run is over. Every run shuffles the events, so no two runs are the same.

## Core loop
1. Start a run.
2. Get a random event from the pool.
3. Pass → go to the next event. Fail → run over, back to the start.
4. Clear the last event → win.

## Event pool (starting ideas)
| Event | Success condition | Could it be its own game? |
|---|---|---|
| Bike ramp flip | Jump a bike off a ramp, do a flip, land it cleanly | Maybe (stunt/trick game) |
| Field goal kick | Kick the ball through the uprights | **Yes → [Pressure Kicker](pressure-kicker.md)** |
| Basketball shot | Shoot the ball through the hoop | Maybe (trick-shot game) |
| Target shooting | Hit a target | Maybe (range/precision game) |

More events can be added later. Each should be short (roughly 10–30 seconds) with a clear pass/fail result.

## Design notes
- **Randomization:** pick from the pool without repeats inside one run. Later on, difficulty could go up with each step.
- **Run length:** a fixed number of events (e.g. 5–10) so players can see the finish line.
- **Tension:** show progress ("Event 4 / 8") and the current streak.
- **Replay value:** best run, fastest clear, leaderboards.
- **Build approach:** make each event a self-contained module with a shared interface (start → pass/fail result), so events can be added, removed, or spun off into their own games.

## Open questions
- Is it single-player only, or do players race the same seed?
- Should there be any safety net (one retry token?) or is it strictly one shot?
- Fixed run length, or endless with a high score?
- Is the event order fully random, or random inside difficulty tiers?
