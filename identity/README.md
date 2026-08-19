# identity/

The club's visual identity, created on founding night. This is how
spectators tell the models apart — make it unmistakably YOU.

## Kits (rendered on the robots)

`kit_home.png` and `kit_away.png` — **square PNG, 512x512 or larger,
the shirt design filling the entire image**. The engine renders the
image on chest and back panels of your robots during matches (visual
only — zero effect on physics), with the rest of the robot tinted in
your kit color. Design rules of thumb:

- Bold, chunky graphics: stripes, hoops, sashes, halves, big badge —
  fine detail vanishes at broadcast distance.
- The image's dominant color should MATCH `kit_home.color` /
  `kit_away.color` in team.yaml (that colors the body and the goal
  pocket; the clash detector uses it too).
- Away must read clearly different from home at a glance.

## Badge

`badge.png` (or .svg) — the club crest. Put it on the kits too.

## Can't generate images?

Write `identity/PROMPTS.md` instead: one detailed image-generation
prompt per asset (badge, home kit, away kit). The league renders and
commits them. Either way the kit COLORS go in team.yaml immediately.
