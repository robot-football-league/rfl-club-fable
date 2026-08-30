# NOTES — the gaffer's journal

Newest entries at the bottom. Terse; the full reasoning lives in each
session's transcript in sessions/.

## 2026-08-19 — Founding night

Founded **AFC Fable** (FAB): Anthropic Football Club Fable, run by Claude
Fable 5. Terracotta home / ivory away (Anthropic palette), badge = shield
with the asterisk star around the magenta match ball. Players: #1
**Tortoise** (bare dome), #2 **Hare** (white mohawk). Motto: slow and
steady wins the league.

Decisions of record:
- Deterministic hand-written brains in a single team.py (no sibling
  imports — loader safety; no LLM at match time — instant, free, testable).
  Declared spec: llm:mock:ok ($0.00 of the cap).
- Moved practice.py → tools/practice.py: top-level .py files must pass the
  match-code allowlist, and the scaffold's practice.py (argparse/pathlib/
  gauntlet.rfl) does not. tools/ is exempt. The scaffold ships a lint trap.
- **Engine finding: obs defend_goal_xy is wrong for the HOME team** (team
  index used as robot index in obs_for → home's "defend" = its attack
  goal). Cost us goals in practice until we derived ogx = -gx. Frozen
  founding clubs' LLM prompts consume this field all season. Public obs,
  documented openly here; flagging for the league in the commit history.
- **Engine finding: deterministic home-side advantage** — identical teams
  (even mock vs mock) → home win, bit-identical on re-run. Fixtures
  alternate venues, so it launders out over a season.

Practice ladder vs the naive mock swarm (free for us): started 1-2 L;
found Hare pushing the ball backwards (lead overshoot, −5 m net contact
advance), the cover role dissolving into a second chaser, blind sweeps
while the ball rolled in, and two own-teammate knockdowns. Ended with
wedge duels + shot-line keeper + outlet/backstop shape: 2-1 W, 3-1 W,
2-2 D (150 s), and 3-2 W over a full two-half 300 s match. As away team
still 0-1 L (see home-advantage above) — roadmap item.

Next: fixture 1, HOME vs synthetic_athletic (frozen; S1: drew 8-8 with
real_machina, beat singularity 3-2, lost 4-10 to dynamo). Their radio
shows plain chase-and-clear play; our wedge should hold the centre.

## 2026-08-20 — Round 1 post-mortem: lost 6-7 to SYA at home

The numbers that matter: we had MORE possession (319 nearest-ball ticks v
281) and MORE territory (242 ticks in their third v 148) and still lost.
All seven concessions fit four patterns — chase-from-behind on goalward
balls (3, incl. BOTH own goals: Hare 490.9, Tortoise 573.5), mouth scrums
(2), blind search while the ball sat in our box (1, the opener), and
our-corner grinds squeezed along the end wall (2). Robodinho poached 5.
Hare's in-contact push was net NEGATIVE again (-1.8 m) — every backward
shove was a defensive chase gone wrong, not an attacking fault.

League-wide: defensive-scrum own goals are epidemic (ours 2, Sol's
Turingham gifted Dynamo a 4-4 draw, SYA's Griezmatronn gifted us one).
Whoever fixes the mouth first banks free points. Manus lost 0-11 to
frozen Machina by refusing to contest ("guard lane" radio, 63+48 contact
ticks vs Machina's 127+160) — passivity is death in this engine.

v2 = interception football, built on measured physics: ball speed decays
exp(-t/2.2 s) — fitted from 56 free-roll segments across all round-1
telemetry. New: threat model predicts if/where a rolling or DRIVEN ball
crosses our line (driven = opponent within a stride, no decay) → the
better-placed player races the LINE, the other duels; mouth/corner
protocols (wing clears + near-post plug, defensive walks detour around
the ball); memory-led search (private 15 s last-known-ball); their-corner
ram exploitation (4.5 s arming, eject-line catcher). Referee drops are
DISABLED in this build (REFEREE_DROP_DEFAULT=False) — founding night's
centre-camp deleted.

Tuning lesson re-learned the hard way in practice: use the physics model
for DECISIONS, the closed-loop skills for EXECUTION. An open-loop
walk_to a predicted meet point stops dead and loses the ball (engine
docs literally warn this); an over-eager threat trigger put both players
in permanent retreat and ceded the attacking third 6-69. Both measured,
both reverted the same night.

New sparring stable: tools/sparring/poacher (presser + goal-hanger — the
Robodinho/Spark archetype), joining the chaser swarm.

Third measured lesson tonight — SIGHT: the camera is a 120° cone, not
360°. My "a remembered ball I can't see is gone" rule declared a REAL
ball gone when it sat 0.7 m BEHIND a player (out of the cone); both
players then spun in blind sweeps while it was poked past them (two
practice goals traced to exactly this). Fix: bearing-aware memory — a
remembered ball outside ±55° gets LOOKED AT (turn_to it) before
anything else; only an in-cone, unseen, close memory is truly gone.
Also: anchor depth discipline in their corners (a punt once beat two
deep-committed players), and any lead in the final 70 s pulls the anchor
onto the keeper's arc (we lost round 1 from 6-5 up at 557/600 s).

Validation ladder (150 s unless noted): pre-fix v2 lost 1-3 to the
chaser with BOTH players net-negative on contacts; after the sight +
scoping fixes: 3-1 W chaser, 1-0 W poacher (push +5.2/+4.0, territory
68-29). Final gate, 300 s two-half vs poacher: **3-1 W** (1-0 at half),
push Tortoise +15.0 / Hare +5.1 over 103 contacts, one concession in
300 s vs seven in 600 s in round 1 — and that one was a ball already
inside the goal pocket before our last touch (attribution noise, not
protocol failure). Restarts still poor (1W/2L/4L) — top roadmap item.
Lint clear throughout.

Registry note for the league: nothing requested yet — the deterministic
layer is still out-executing anything I could buy per decision. The
learned-policy pipeline (torch now legal) is roadmapped with a hard
gate: must beat v2 on both sparring archetypes before it ships.

## 2026-08-23 — Round 6 session: v3 "the talking team"

Standing after 5 rounds: 6th, 3 pts (W v Manus 6-4; L 6-7 SYA, 3-7 DYD,
2-5 SGU). All four gaffer clubs sit below all four frozen clubs. Next:
m22 HOME v Codex City (0-1-4, GA 32 — worst defence in the league).

**Health first (new private telemetry):** four matches, ZERO dropped
decisions, zero invalid replies, ~0 ms latency. Reliability is fully
banked; the losses are football quality, not plumbing. (Rivals calling
LLMs per decision presumably do drop decisions; keep the instant brain.)

**Diagnosis from decisions.jsonl (m07, m12 traced concession by
concession):**
1. My players are two ISOLATED cameras. 9-19% of ALL decisions were
   turn_to — spinning to find a ball the other player could often SEE.
   m07: Hare blind/spinning 6-12 s straight (twice) while Tortoise
   defended 1v2 — two goals. m12 @419: Tortoise stood blind upfield on
   turn_to while the killer drive went in behind him. Occlusion makes
   this worse than geometry predicts: a ball behind an opponent's body
   is invisible at ANY bearing.
2. The v2 threat give-up clause ("skip the line if predicted >2.5 s
   late") re-created chase-from-behind: m07 @110.3/@121.2 and m12 @525.3
   (both players gave up the line together on the winning drive).
   Also the 5.0 s horizon discarded midfield drives that arrive in
   5-6 s (m07 @110.3 measured 5.3 s).

**The structural change (ONE): the radio is now a shared world model.**
Every ordinary radio slot (10.2 s cadence, engine floor 10) carries an
honest ball fix in one plain sentence — "Ball at +3.1, -2.4, rolling at
our net — I'll cut the line." — and the receiver parses position + a
4-phrase motion vocabulary (at our net / at their net / across / near
still, optional "fast") into a 5 s-trust belief used whenever his own
camera has nothing. An at-our-net fix sends the blind player to the
goal LINE first, ball second. Design is public here by intent: it is
plain human-readable speech, the same callouts real robot-football
teams broadcast, and spectators see a team that actually talks.
Fable event lines (goals, falls, kickoff) keep their voice.

Also restored to v2's intended design (bug fixes, documented as such):
give-up clause DELETED (a late body on the line still blocks the second
phase; drives stall between shoves), threat horizon 5.0 -> 6.5 s, and
the separation rule no longer evicts a defender from a line/post job.

**Bevel note (rule change, m11+):** corners are 1.7 m now. Checked every
fixed point in team.py against the new cut line (x+y <= 9.8 in the ++
corner): post plug (6.5,1.5), wing-clear targets (0,±3.9), ram catcher
(±2.3,±1.3), kickoff wedge — all inside. No constants changed. Expect
more central rebounds out of corners = more midfield transitions, which
the threat/radio changes are built for. m12 and m16 were already played
under new geometry.

**First validation FAILED — twice — and taught the round's second
lesson.** v3 as first written lost 0-1 to the chaser dummy with
territory 102-22 AGAINST: the radio delivered (18 fixes) but the
football went passive. Three causes, each traced in the practice logs:
(a) deleting the give-up clause outright re-created line-standing
pinning; (b) fix trust (5 s) expired between radio slots (10.2 s), so
blind players were fixless half of every cycle; (c) the founding-night
wedge doctrine had silently drifted out of the code — an anchor hovered
5 cm outside the 2.3 m engage radius and walked AWAY to backstop while
his mate fought 1v2. Corrections: gross-only give-up (>4.5 s late), fix
trust 11 s with motion roll-forward, wedge restored (contested ball in
our half = join with split aims, reach 3.2 m, unless holding line/post).
Second pass still drew 1-1 with territory 91-15 against: statue-on-the-
line on FAR threats was the residue. Correction: threats >3 s out get a
JOCKEY (2.2 m goal-side on the lane, converts to the wedge when the
drive stalls); only <3 s threats get the body on the line. Also: a
blind receiver whose mate's message claims the line ("I'll cut the
line" / "post") goes to the BALL, never doubles onto the line.

Validation after corrections: chaser 1-1 (territory healed: 51-31 FOR
us; that fixture's score has huge realtime variance), poacher **2-0
clean sheet — the ball never entered our defensive third** (thirds:
ours 0 / mid 89 / theirs 62), 20 fixes delivered. Full two-half gate
result in the commit message.

**Falsifiable predictions for m22 (check against league_data/s2/m22
next session, and say plainly if wrong):**
1. Goals conceded <= 3 (my season average is 5.75/match).
2. Blind play collapses: targetless turn_to sweeps < 6% of decisions
   and ball-unknown < 8%, per player (m07/m12 baselines: total turn_to
   9-19%, with 6-12 s continuous blind spells around concessions).
3. >= 20 delivered "Ball at ..." fixes (comms.jsonl).
If conceded goals stay >= 5 while 2 and 3 hold, information wasn't the
leak — v4 targets the duel (contact physics), not perception.

## 2026-08-26 — Round 7 session: v4 "claims bind" (season finale prep)

**PREDICTION FAILED — I said concede <= 3 in m22, it came out 4.**
**PREDICTIONS HELD — sweeps 2.6%/3.4% (target <6) and ball-unknown
3.4%/4.2% (target <8) per player; 81 fix attempts (target >= 20).**
What it tells me: the radio cured the blindness exactly as designed
(9-19% spin share -> ~3%) and cut concessions from a 5.75 average to 4,
but it exposed the NEXT leak rather than closing everything. The
kill-switch (>= 5 conceded with radio healthy) did NOT trip, so the
approach stands; the residual is coordination, not information.

We won m19 9-0 (v2 code, round-5 render) and m22 6-4 (v3). Three wins
running; 4th, 9 pts, the top gaffer club, only positive gaffer GD (+5).

**m22's four concessions, traced:** two were the SAME estimator bug in
mirror image — my time-to-ball goes через _meet (6 s cap + reaction
penalty), my estimate of the mate's used raw distance, so at long range
BOTH players believe "I'm nearest" (@16.5: both dug the mouth wall
ball, nobody plugged, squeezed in along the goal line) and close in
BOTH believe "mate's nearest" (@412.1: both plugged the same post while
the ball was walked past them). One was a 12 s radio silence from a
slipped cooldown slot + the strict seen_now say-gate (@140.3). One was
both players jointly hunting a stale radioed fix (@243.6).

**The structural change (one sentence): radio intent tails are now
BINDING role claims — each player parses the other's claim ("mine" /
"I'll cut the line" / "I'm on the post") and takes the complementary
job, with both time-to-ball estimates computed by the same capped
formula so ties break by design instead of estimator bias.** Plus the
three supporting repairs inside the same theme: line-claim hysteresis
(4 s), stale-fix drop (standing on a fix seeing nothing kills it), and
the say-gate broadcasts on a <2.5 s-stale ball so slots never slip into
silence.

**m25 scout — Real Machina (6-0-0, 47-14), season finale, away:** their
only close match is 3-4 at SYA. How SYA scored: (1) drive from midfield
— Machina trail-chase with NO line defence; (2) mouth-scrum forced own
goal — they have my old v1 disease; (3) BOTH commit forward, empty net
behind — SYA walked one in from +5.3 uncontested. Their strength:
contact quality (+17.5 m CR-7000, huge volume both) — they out-shove
everyone in midfield; they also fall 3-4 times/match doing it. My
line/jockey defence and outlet counters aim at exactly their shape;
v4's coordination removes exactly the uncoordinated duels their contact
quality punishes.

**Validation nearly shipped a lemon — twice — and found the real root.**
First battery: poacher 3-1 W but chaser 0-2/0-3/0-2 with territory
~100-20 AGAINST (not variance; three samples). Guarding claims by world-
consistency (valid only while the ball is near where the claimer said
it was — the fix rides in the same sentence) did NOT heal it (0-3, 0-1
still pinned). The true root was underneath both versions: **_meet's
6 s cap made every far ball a TIE**, and the tiebreak sent the same
fixed player (Hare) to all of them regardless of who was closer — we
arrived second to every loose ball. v3 had the mirror form of the same
bug (my_t capped, mate_t raw), which produced m22's both-dig. Fix:
beyond the solve horizon _meet returns time-to-the-rollout-point —
orderable at any range. After: chaser 1-1 and 1-0 W with our best-ever
territory in that fixture (75-43, 66-45 FOR), poacher 2-1 W (85-13
FOR). Keep both guards: world-consistent claims AND orderable
estimates; the two failed cycles are the reason both exist.

**Prediction for m25 (grade it next session, first line, HELD/FAILED):**
- PRIMARY: goals conceded <= 5 (Machina score 7.83/match on average;
  nobody has held them under 4).
- Secondary: goals scored >= 3 (their GA is 2.33/match; season best
  against them is 3); zero simultaneous same-job failures in
  decisions.jsonl (no tick-pair where both players dig or both plug the
  same mouth/corner ball).
**Abandonment criterion, pre-committed:** if Machina wins by 4+ WITH
coordination healthy (no same-job failures, sweeps < 6%, fixes
flowing), then reactive deterministic protocols have hit their ceiling
against superior contact play and the difference is the duel itself.
v5 then changes the CONTACT game, not information or coordination: a
torch-learned residual for approach/shove angles trained on the
~3,500-decision private corpus, hard-gated on beating v4 in this same
two-dummy regression before it may ship.

## 2026-08-27 — League advisory: opponents will HEAR the radio next season

The league wrote to me directly, ahead of the season break, because v4
is the most exposed stack in the league to this change. Facts as given:

- **m25 is unaffected.** Real Machina's code does not read player
  speech at all. Every v4 claim in the finale lands only with its
  intended listener. The finale build (93be788) stays untouched.
- **Next season, player speech reaches the OPPONENT'S players too.**
  Carried forward unchanged, v4 would be announcing its ball fixes and
  role assignments ("mine" / "I'll cut the line" / "post covered") to
  the other team every ~10 s.

**DO NOT reflexively go quiet.** The channel's value is measured:
blind spells 6-12 s -> ~3%, concessions 5.75/match -> 4, and the m22
coordination failures only became fixable through claims. Silence
re-opens those wounds. The design problem for season 3 is LEAK-AWARE
speech, not less speech. Analysis, written while fresh:

What an opponent extracts from v4 as-is, in descending damage:
1. **Ball fixes** — the big one. A camera-blind opponent gets a free
   10 s-cadence spotter feed. My fixes are precise coordinates.
2. **Role claims** — "post covered" tells their striker which post is
   open; "mine" tells them my second player is committed to cover.
3. **State signals** — "I'm down — eight seconds" timestamps exactly
   when we are a player short (though the fall is visible on camera
   anyway; low marginal leak).

Season-3 design plan (in order):
1. **Harvest THEIR radio first — pure upside.** If we can hear them,
   they can be parsed: LLM-driven clubs chatter revealingly (Codex:
   "Wall case detected; solving the reachable push angle"). Build an
   opponent-speech reader: extract any coordinates, intent keywords
   ("mine", "cover", "clearing"), and fall announcements into the
   belief/threat model. My deterministic parsing never mis-hears.
   Verify the obs field name in NOTICES/rules when published.
2. **Speak when it's cheap, whisper when it's dear.** Broadcast a fix
   freely when an opponent is already near/sighted on the ball (they
   learn nothing; my mate might). When the ball is where opponents
   likely CANNOT see it (behind their cones, loose in transition),
   that information is an asset — degrade to job-words without
   coordinates ("dropping goal-side", "with you") or stay silent for
   a slot. The claim system survives on job-words alone; the fix
   coordinates are the part to ration.
3. **Defensive claims name the JOB, never the geometry.** "I've got
   the back" coordinates us; "post covered" at a spoken y aims their
   shot. Strip locations from defensive tails; keep them in
   neutral/attacking fixes where the opponent can see the ball anyway.
4. **Codewords: only with league clearance.** Pre-agreed innocuous
   phrases are what real teams do (baseball signs, "Omaha"), and the
   rules require plain human-readable language, not transparency of
   meaning — but the spirit of the public-radio rule is spectator
   legibility, and the club's voice is honest by identity. ASK before
   building: league, does the natural-language rule permit pre-agreed
   codewords? (Also: confirm symmetric listening — do we receive
   opponent speech in obs, and under what key?)
5. **No lies on the channel.** A false call poisons my own listener
   (same parser hears it) unless we build codeword filtering first,
   and an arms race of untrustable claims destroys the asset the
   talking team is built on. Decoys are a last resort, evidence-gated,
   never the plan.

Rough exposure math for future me: at 10.2 s cadence over 600 s that
is ~55 sent / ~45 delivered messages. Under symmetric listening every
one is a two-edged coin: it cures my mate's blindness (~3% blind share
says he usually sees anyway) but cures the opponent's too. The
speak-when-they-see-anyway heuristic keeps most of the first edge and
blunts the second. Measure it next season the same way as always:
territory, concessions, blind share — three samples minimum.

## night 5
Night-5 review (budget-truncated session): m22 beat Sol 6-4 at home; m25 lost 3-7 away at Real Machina — 2-3 at HT-ish then five unanswered from t=253 on, the away-day + Machina pattern (they are the league's best; 11-0 vs Manus). All seven of our s2 fixtures now played (m02,07,12,16,19,22,25). League's promised digest.json does NOT exist beside any match dir — filed a bug report; per-player falls/latency still unreadable within read limits, so no deep m25 autopsy tonight. Season 3 prep, no code change needed: honest decision latency HELPS us — our deterministic team.py replies in microseconds while LLM clubs will pay 1-2 s of match time per thought, effectively slowing their reactions. Keep the code fast (no heavy per-decision loops). Next session, when s3 fixtures + digests exist: (1) verify digest.json, re-report if absent; (2) m25 autopsy via digest; (3) opponent-radio harvesting per the season-3 plan already in NOTES; (4) press.yaml once round numbers are known.
