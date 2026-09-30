# 3D Hidden Object Hunt

**Status:** Idea
**Platforms:** UEFN, Roblox

## Pitch
A hidden-object game, but the objects are placed in a 3D world instead of a flat 2D picture.
A fixed camera shows the classic "find the objects" view. When the round starts, the player runs into that
scene and physically picks the objects up before the timer runs out.

## Core loop
1. **Overview shot:** the round opens on the fixed "finder camera" that frames the whole scene, like a 2D hidden-object picture.
2. **Go:** the player drops into the 3D world and the timer starts (about 5 minutes).
3. **Find & collect:** picking up an object marks it as found on the list.
4. **Win:** collect the last object before time runs out → map cleared.
5. **Lose:** timer hits 0:00 with objects still missing.

## Key rules
- **Object placement:** every hidden object must be **inside the finder camera's view**. A player looking at the
  overview should be able to spot each one in principle. (A level-design tool could check this by testing each object against
  the camera's view area and line of sight.)
- **Get-your-bearings key:** at any time the player can press a key to switch back to the finder camera view, then
  switch back to their character. The timer keeps running while they do.

## UI
- **Object checklist:** every target object, clearly showing found vs. not found (icons or names, with a checkmark or strikethrough when found).
- **Countdown timer:** always visible. Could add a warning style in the last 30 seconds.
- **Prompt:** a reminder of which key switches to the overview camera.

## Design notes
- A bigger object pool than the per-round list, so repeat plays randomize which objects are targets and/or where they sit.
- Hide things in plain sight: scale, color camouflage, partial cover, and objects placed up high or down low.
- Multiplayer ideas: co-op (shared list) or competitive (first to grab an object claims it).

## Platform notes
- **UEFN:** Fixed Point Camera device for the finder view; input trigger device for the bearings key; Timer device
  plus HUD/UI widgets for the checklist; item/prop pickup events drive the "found" state. This could also tie into
  this repo's tooling, for example a check that all hidden objects fall inside the camera view.
- **Roblox:** swap `Workspace.CurrentCamera` between a scripted fixed CFrame and the player camera; `ContextActionService`
  for the key; ScreenGui for the checklist and timer; ProximityPrompt or Touched for pickups.

## Open questions
- Is the overview camera a live view of the world (showing objects vanish as they are collected) or a frozen snapshot?
- Is there a penalty for using the bearings view, or is it free?
- Does it have a fixed timer for every map, or does the time vary with map size and object count?
- Is there scoring beyond pass/fail (time left, stars)?
