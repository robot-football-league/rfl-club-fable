"""AFC Fable — the first team, in one file. v4: claims bind.

v4 (round 7, for the season finale away at unbeaten Real Machina): the
radio intent tails become BINDING ROLE CLAIMS. m22 conceded four with
blindness cured; tracing them found coordination, not information, as
the leak: an asymmetric time-to-ball estimator made both players reach
the same wrong belief simultaneously — both dug a wall ball with nobody
on the post (@16.5), both plugged the same post while the ball was
walked past them (@412.1). Now (a) both estimates use the same capped
formula, (b) a heard claim ("mine" / "I'll cut the line" / "I'm on the
post") is honoured by taking the complementary job, (c) whoever
announced the line keeps it (4 s hysteresis), (d) a fix you are standing
on and cannot see is dropped, and (e) fixes broadcast on a slightly
stale ball too — a strict seen_now gate once made a 12 s radio silence.

Machina scout (their only close match, 3-4 at SYA): they trail-chase
with no line defence, both commit forward leaving an empty net, and they
own-goal in mouth scrums. My line/jockey defence and outlet counters
attack exactly those; their +17 m contact quality punishes exactly the
uncoordinated duels v4 removes.

--- v3 below ---
The talking team.

Two hand-written deterministic players (RFL_RULES.md: "how you produce
decisions is your business ... hand-written code"). Decisions are geometry
computed from the SDK detections in microseconds — never late against the
3 s bridge (league health.json: 0 dropped decisions in four matches).

v3's structural change, from the round-2..5 private telemetry: my players
were two ISOLATED cameras. 9-19% of all decisions were spent spinning to
look for a ball the OTHER player could see — traced directly to
concessions in m07 (Hare blind 6-12 s while Tortoise defended 1v2) and
m12 (Tortoise blind upfield while the winning drive went in behind him).
The fix is the fully legal, fully public player radio: every ordinary
call now carries an honest ball fix in plain language —

    "Ball at +3.1, -2.4, rolling at our net — I'll cut the line."

— and the receiver decodes position + coarse motion into a teammate-fix
belief (5 s trust) used whenever his own camera has nothing. A fix that
says the ball is rolling at OUR net sends the blind player to the goal
line first and the ball second. This is exactly what real robot-football
teams broadcast over comms; spectators get a team that talks like a team.

Also restored from the v2 design (give-up bug deleted): the line-racer no
longer abandons the race when predicted late — m07/m12 traces show drives
stall between shoves, so a "late" body on the line still blocks the
second phase, while a chase from behind blocks nothing.

v2 is the round-1 post-mortem made executable. We lost 6-7 at home with
BETTER territory and possession; all seven concessions fell into four
repeatable failures, each now a named protocol:

  CHASE-FROM-BEHIND (3 goals, incl. both own goals): a ball rolling at our
      net was chased, never cut off. Now: a fitted ball-physics model —
      exponential speed decay, tau = 2.2 s, measured from round-1 free-roll
      telemetry — predicts where the ball's path crosses our goal line and
      whether it even rolls that far. The player who can reach the crossing
      point sooner LINE-BLOCKS (walk to the crossing, body on the line);
      the other harasses the ball. Nobody chases a lost race from behind.
  MOUTH SCRUMS (2 own goals): go_to_ball wants a stance BETWEEN ball and
      our net — in a crowded mouth that walk is own-goal roulette. Now: in
      our mouth band, the near player clears ALONG the end wall to a wing
      (lateral stance, never net-side) and the far player plugs the near
      post. Defensive walks detour around the ball (never barge through).
  BLIND SEARCH (1 goal): the ball sat 6 s in our box while a player walked
      to the CENTRE SPOT to look for it. Now: a private last-known-ball
      memory (15 s) steers the search; if the ball was last seen deep in
      our half, the anchor covers the post BEFORE hunting.
  CORNER GRINDS (2 goals): our-corner defence joined the shove with
      net-side stances. Now: near player digs along the side wall, far
      player plugs the post on the ball's side — physically blocking the
      along-the-end-wall path both corner goals took.

Also new: CORNER-RAM awareness. The rams fire after 4.5 s of slow ball in
a 1.5 x 1.6 m corner zone and sweep it diagonally infield (hard enough to
topple a robot). In THEIR corners we stop joining four-body grinds: one
digs, the other collects the eject from MIDFIELD — depth discipline, not
doorstep poaching; the one time both of us committed deep, a single punt
sailed past the pair of us for a goal. In ours, the post-plug stands
clear of the panel stroke.

(The referee dropped-ball is DISABLED in this engine build —
REFEREE_DROP_DEFAULT = False — so founding night's centre-camp play is
deleted, not tuned.)

Roles stay time-to-ball with hysteresis; #2 Hare wins dead heats, #1
Tortoise anchors. Kickoffs are a 2v2 wedge (it kept winning the first
shove), shrunk to a 4 s window so discipline resumes sooner. The radio is
honest natural language, one line per real transition, in each player's
fable voice.

Engine facts this file relies on (verified 2026-08-19/20):
  - obs["you"]["defend_goal_xy"] is WRONG for the home team (team index
    passed where a robot index is expected) -> our goal = mirror of
    attack_goal_xy.
  - Ball speed decays ~exp(-t / 2.2 s): a ball at v m/s rolls ~2.2*v m.
  - Corner rams: 4.5 s arming, zone 1.5 m (end) x 1.6 m (side), fires
    only while ball speed < 0.5; panel stroke 0.65 m, diagonal infield.
  - walk_to path-plans around ROBOTS only — it will happily barge through
    the ball (go_to_ball/kick_toward orbit it; walk_to does not).
"""

import math
import re

# Pitch facts (docs/RFL_RULES.md; obs["field"] agrees at runtime).
PITCH_X = 7.0            # goal lines at x = +-7
PITCH_Y = 4.5            # side walls at y = +-4.5
GOAL_HALF_W = 1.6        # goal mouth |y| < 1.6
WALK_MPS = 0.7           # planning estimate of cruise speed
REACT_S = 0.35           # decision-to-motion latency allowance
FALL_OUT_S = 8.0         # a fallen robot is out this long
BALL_TAU_S = 2.2         # fitted speed-decay constant (round-1 telemetry)

CORNER_X = PITCH_X - 1.5     # ram zone reach from the end wall
CORNER_Y = PITCH_Y - 1.6     # ... and from the side wall

SAY_GAP_S = 10.2         # just over the engine's 10 s cooldown: every slot
                         # the rules allow now carries a ball fix


def _d(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _clip(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def _roll(bxy, vel, t):
    """Ball position after t seconds under exponential speed decay."""
    k = BALL_TAU_S * (1.0 - math.exp(-t / BALL_TAU_S))
    return (bxy[0] + vel[0] * k, bxy[1] + vel[1] * k)


def _meet(me, bxy, vel):
    """Earliest (t, point) where I can be where the ball will be. Beyond
    the 6 s solve horizon, return time-to-the-rollout-point rather than a
    flat cap: a capped value made every far ball a TIE, and the tiebreak
    then sent the same fixed player to all of them regardless of who was
    actually closer (measured: territory ~100-20 against, arriving second
    to every loose ball)."""
    t = 0.0
    while t <= 6.0:
        p = _roll(bxy, vel, t)
        if _d(me, p) <= WALK_MPS * max(0.0, t - REACT_S):
            return t, p
        t += 0.25
    end = _roll(bxy, vel, 6.0)
    return REACT_S + _d(me, end) / WALK_MPS, end


def _cross_our_line(bxy, vel, ogx, asign, driven=False):
    """(t, y) where the ball's path crosses our goal line — or None if the
    roll dies first or it isn't heading in. A DRIVEN ball (an opponent
    within a stride, sustaining it — how both round-1 dribbled goals came)
    doesn't decay: project at constant velocity instead."""
    line_x = ogx + asign * 0.45
    if vel[0] * (-asign) < 0.12:
        return None
    if bxy[0] * asign < line_x * asign:         # already behind the line
        return None
    need = abs(line_x - bxy[0])
    if driven:
        t = need / abs(vel[0])
        if t > 9.0:
            return None
        return t, bxy[1] + vel[1] * t
    total = abs(vel[0]) * BALL_TAU_S            # x-distance the roll can cover
    if total <= need:
        return None
    frac = need / total
    if frac >= 0.999:
        return None
    t = -BALL_TAU_S * math.log(1.0 - frac)
    y = bxy[1] + vel[1] * BALL_TAU_S * frac
    return t, y


# Radio voice. v3: the radio is a WORLD MODEL CHANNEL first and a
# personality second. Ordinary calls carry an honest ball fix — position
# and motion in plain language — exactly the callout a sighted teammate
# owes a blind one. Event lines (goals, falls) keep their fable voice.
LINES = {
    "Tortoise": {
        "kickoff":  "Steady from the whistle — I've got our half.",
        "goal_for": "The moral so far: patience scores.",
        "goal_against": "A lesson, not a defeat. Reset and go again.",
        "down":     "I'm down — eight seconds. Hold the fort, Hare.",
        "solo":     "You rest — I'll carry us till you're up.",
    },
    "Hare": {
        "kickoff":  "Off at the whistle — first touch is mine!",
        "goal_for": "Fast AND finished this time!",
        "goal_against": "They won't outrun us twice. Again.",
        "down":     "Legs gone — eight seconds. Yours, Tortoise!",
        "solo":     "I've got both ends till you're back up.",
    },
}

# short intent tails for the fix calls, per player, per situation
INTENTS = {
    "Tortoise": {"take": "mine, slow and steady", "cover": "dropping goal-side",
                 "line": "I'll cut the line", "post": "I'm on the post",
                 "wedge": "push with me", "ram": "I'll take the bounce",
                 "outlet": "ahead for the break"},
    "Hare": {"take": "mine — no naps", "cover": "dropping back",
             "line": "racing it to the line", "post": "post covered",
             "wedge": "heave with me", "ram": "on the bounce",
             "outlet": "ahead for the break"},
}

# motion vocabulary: spoken by the sender, decoded by the receiver
MOTION_AT_OURS = "rolling at our net"
MOTION_AT_THEIRS = "rolling at their net"
MOTION_ACROSS = "rolling across"
MOTION_STILL = "near still"
_FIX_RE = re.compile(r"[Bb]all at ([+-]?\d+\.?\d*), ([+-]?\d+\.?\d*)")


def _motion_phrase(vel, asign):
    speed = math.hypot(vel[0], vel[1])
    if speed < 0.25:
        return MOTION_STILL
    fast = ", fast" if speed > 1.0 else ""
    if vel[0] * (-asign) > 0.25:
        return MOTION_AT_OURS + fast
    if vel[0] * asign > 0.25:
        return MOTION_AT_THEIRS + fast
    return MOTION_ACROSS + fast


def _parse_fix(msg, asign):
    """Decode a teammate's ball call -> (xy, vel_estimate) or None."""
    m = _FIX_RE.search(msg or "")
    if not m:
        return None
    try:
        xy = (float(m.group(1)), float(m.group(2)))
    except ValueError:
        return None
    low = msg.lower()
    mag = 1.3 if "fast" in low else 0.9
    vel = (0.0, 0.0)
    if MOTION_AT_OURS in low:
        vel = (-asign * mag, 0.0)
    elif MOTION_AT_THEIRS in low:
        vel = (asign * mag, 0.0)
    return xy, vel


def _parse_claim(msg):
    """The intent tail of a call is a role CLAIM. Map it to the job the
    speaker has taken so the listener takes the complementary one."""
    low = (msg or "").lower()
    if "mine" in low or "racing it" in low or "no naps" in low:
        return "ball"
    if "cut the line" in low:
        return "line"
    if "post" in low:
        return "post"
    if "push with me" in low or "heave" in low:
        return "wedge"
    if "dropping" in low or "goal-side" in low or "ahead for the break" in low:
        return "cover"
    return None


class FablePlayer:
    """One robot's behaviour layer. number is the shirt (1 or 2)."""

    def __init__(self, number):
        self.number = number
        self.name = "Tortoise" if number == 1 else "Hare"
        self.attack_biased = (number == 2)      # Hare wins the tie-breaks
        self.episode_usage = {}                 # zero tokens, zero dollars
        self.begin_episode()

    # ------------------------------------------------------------ lifecycle
    def begin_episode(self, log_dir=None):
        self.t0_rem = None
        self.t = 0.0
        self.role = "attack" if self.attack_biased else "cover"
        self.mate_xy = None
        self.mate_seen_t = -1e9
        self.mate_down_until = -1e9
        self.self_down_said = False
        self.kickoff_until = -1e9
        self.kickoff_said = False
        self.say_ok_t = -1e9
        self.last_line = ""
        self.score_prev = None
        self.ball_mem = None        # (xy, t) our OWN long memory, ~15 s
        self.ball_mem_t = -1e9
        self.fix_xy = None          # teammate's radioed ball fix
        self.fix_vel = (0.0, 0.0)
        self.fix_t = -1e9
        self.last_mate_msg = ""
        self.mate_claim = None      # the job the mate's last call claimed
        self.mate_claim_t = -1e9
        self.my_claim = None        # the job my own last call claimed
        self.my_claim_t = -1e9

    # ---------------------------------------------------------------- radio
    def _say(self, reply, key):
        line = LINES[self.name].get(key, "")
        if not line or line == self.last_line or self.t < self.say_ok_t:
            return reply
        reply["say"] = line
        self.say_ok_t = self.t + SAY_GAP_S
        self.last_line = line
        return reply

    CLAIM_OF_INTENT = {"take": "ball", "line": "line", "post": "post",
                       "wedge": "wedge", "cover": "cover", "ram": "cover",
                       "outlet": "cover"}

    def _say_fix(self, reply, intent, bxy, vel, asign):
        """The v3 workhorse: an honest ball fix in plain language, with my
        intent as the tail — the callout a sighted player owes a blind
        teammate. In v4 the tail is also a binding role claim, so record
        what I just committed to."""
        if self.t < self.say_ok_t:
            return reply
        tail = INTENTS[self.name].get(intent) or INTENTS[self.name]["cover"]
        line = (f"Ball at {bxy[0]:+.1f}, {bxy[1]:+.1f}, "
                f"{_motion_phrase(vel, asign)} — {tail}.")[:120]
        if line == self.last_line:
            return reply
        reply["say"] = line
        self.say_ok_t = self.t + SAY_GAP_S
        self.last_line = line
        self.my_claim = self.CLAIM_OF_INTENT.get(intent)
        self.my_claim_t = self.t
        return reply

    # ------------------------------------------------------------- helpers
    def _safe_target(self, me, target, bxy):
        """A walk_to waypoint that will not barge through the ball: walk_to
        A*-avoids robots but NOT the ball, and shoving the ball while
        crossing our box is exactly how own goals happen. If the straight
        leg passes within 0.65 m of the ball, detour perpendicular."""
        if bxy is None:
            return target
        ax, ay = me
        tx, ty = target
        vx_, vy_ = tx - ax, ty - ay
        L2 = vx_ * vx_ + vy_ * vy_
        if L2 < 1e-9:
            return target
        u = ((bxy[0] - ax) * vx_ + (bxy[1] - ay) * vy_) / L2
        if u <= 0.0 or u >= 1.0:
            return target
        px_, py_ = ax + u * vx_, ay + u * vy_
        if _d((px_, py_), bxy) >= 0.65:
            return target
        L = math.sqrt(L2)
        nx, ny = -vy_ / L, vx_ / L               # unit normal
        side = 1.0 if (bxy[0] - px_) * nx + (bxy[1] - py_) * ny < 0 else -1.0
        wx = _clip(px_ + nx * side * 1.0, -PITCH_X + 0.4, PITCH_X - 0.4)
        wy = _clip(py_ + ny * side * 1.0, -PITCH_Y + 0.4, PITCH_Y - 0.4)
        return (wx, wy)

    def _walk(self, me, target, bxy=None):
        tx, ty = self._safe_target(me, target, bxy) if bxy else target
        return {"skill": "walk_to", "target": [round(float(tx), 2),
                                               round(float(ty), 2)]}

    # ----------------------------------------------------------------- main
    def decide(self, obs):
        det = obs.get("detections") or {}
        ball = det.get("ball")
        me = obs["self"]["field_xy"]
        you = obs["you"]
        gx = float(you["attack_goal_xy"][0])
        ogx = -gx            # engine's defend_goal_xy is wrong for the home team
        asign = 1.0 if gx > 0 else -1.0
        score = obs.get("score") or {}
        rem = float(obs.get("time_remaining_s", 0.0))

        if self.t0_rem is None:
            self.t0_rem = rem
        self.t = self.t0_rem - rem

        # -- events ---------------------------------------------------------
        goal_line = None
        if self.score_prev is not None and score:
            if score.get("you", 0) > self.score_prev.get("you", 0):
                goal_line = "goal_for"
            elif score.get("them", 0) > self.score_prev.get("them", 0):
                goal_line = "goal_against"
        if score:
            self.score_prev = dict(score)

        mate_msg = obs.get("teammate_says") or ""
        low_msg = mate_msg.lower()
        if "down" in low_msg or "legs gone" in low_msg:
            self.mate_down_until = self.t + FALL_OUT_S
        if mate_msg and mate_msg != self.last_mate_msg:
            self.last_mate_msg = mate_msg
            fx = _parse_fix(mate_msg, asign)
            if fx is not None:
                self.fix_xy, self.fix_vel = fx
                self.fix_t = self.t
            # the intent tail is a binding role CLAIM (v4): honour it
            self.mate_claim = _parse_claim(mate_msg)
            self.mate_claim_t = self.t

        mates = det.get("teammates") or []
        if mates:
            self.mate_xy = tuple(mates[0]["field_xy"])
            self.mate_seen_t = self.t

        # -- fallen ---------------------------------------------------------
        if obs["self"].get("fallen"):
            reply = {"skill": "hold"}
            if not self.self_down_said:
                self.self_down_said = True
                self.say_ok_t = -1e9
                self._say(reply, "down")
            return reply
        self.self_down_said = False

        # -- ball memory (ours, longer than the SDK's 6 s) -------------------
        bxy = tuple(ball["field_xy"]) if ball else None
        bspeed = float(ball.get("speed_mps", 0.0)) if ball else 0.0
        if ball is not None and float(ball.get("age_s", 9.0)) < 2.0:
            self.ball_mem, self.ball_mem_t = bxy, self.t

        # -- sight discipline. The camera is a 120-degree panoramic lens,
        #    not 360: a remembered ball OUTSIDE that cone is invisible and
        #    REAL — look at it before doing anything else. A remembered
        #    ball INSIDE the cone that still isn't seen is genuinely gone.
        #    (Both players once spun in blind sweeps with the ball 0.7 m
        #    behind them; a goal followed. Bearing is in the detection.)
        if ball is not None and not ball.get("seen_now"):
            brg = abs(float(ball.get("bearing_deg", 0.0)))
            age_ = float(ball.get("age_s", 0.0))
            if brg > 55.0 and age_ > 1.0:
                reply = {"skill": "turn_to",
                         "target": [round(bxy[0], 2), round(bxy[1], 2)]}
                return self._say(reply, goal_line) if goal_line else reply
            if brg <= 55.0 and age_ > 1.5 and _d(me, bxy) < 2.5:
                ball, bxy = None, None

        # -- restart detection ----------------------------------------------
        if (bxy is not None and _d(bxy, (0.0, 0.0)) < 0.4 and bspeed < 0.2
                and 2.0 < abs(me[0]) < 3.0 and 0.7 < abs(me[1]) < 1.7):
            if self.t > self.kickoff_until:
                self.kickoff_said = False
            self.kickoff_until = self.t + 4.0
        kickoff_play = (self.t < self.kickoff_until and bxy is not None
                        and _d(bxy, (0.0, 0.0)) < 1.2)

        if kickoff_play:
            split = 0.5 if self.number == 1 else -0.5
            reply = {"skill": "kick_toward", "target": [gx, split]}
            if goal_line:
                return self._say(reply, goal_line)
            if not self.kickoff_said:
                self.kickoff_said = True
                return self._say(reply, "kickoff")
            return reply

        # -- ball unknown: use the TEAM's knowledge, not just mine. The
        #    teammate's radioed fix is often fresher than my own memory —
        #    round-1-to-5 telemetry showed players spinning blind for 6-12 s
        #    while the other player was WATCHING the ball roll in.
        if ball is None:
            # trust a fix for a full radio cycle (cadence is 10.2 s — a 5 s
            # window left the blind player fixless half of every cycle),
            # and roll it forward with its spoken motion
            fix_age = self.t - self.fix_t
            fix_ok = fix_age < 11.0 and self.fix_xy
            # I am standing where the fix says and see nothing: the fix is
            # stale — drop it rather than orbit a ghost (m22 @243: both
            # players hunted the same dead coordinates while the real ball
            # was scored at the other end)
            if fix_ok and _d(me, self.fix_xy) < 1.2:
                self.fix_t = -1e9
                fix_ok = False
            mem_ok = (self.t - self.ball_mem_t) < 15.0 and self.ball_mem
            if fix_ok and (not mem_ok or self.fix_t >= self.ball_mem_t):
                fx_, fy_ = _roll(self.fix_xy, self.fix_vel,
                                 min(fix_age, 4.0))
                fx_ = _clip(fx_, -PITCH_X + 0.4, PITCH_X - 0.4)
                fy_ = _clip(fy_, -PITCH_Y + 0.4, PITCH_Y - 0.4)
                # if the sender's intent tail says HE has the line/post,
                # don't double onto it — go to the ball he is calling
                low_fix = self.last_mate_msg.lower()
                line_covered = ("cut the line" in low_fix
                                or "post" in low_fix)
                if (self.fix_vel[0] * (-asign) > 0.25
                        and not line_covered):
                    # mate says it's rolling at OUR net: line first, look later
                    line_pt = (ogx + asign * 0.5,
                               _clip(fy_, -(GOAL_HALF_W - 0.1),
                                     GOAL_HALF_W - 0.1))
                    if _d(me, line_pt) < 0.4:
                        reply = {"skill": "turn_to",
                                 "target": [round(fx_, 2), round(fy_, 2)]}
                    else:
                        reply = self._walk(me, line_pt)
                elif _d(me, (fx_, fy_)) > 1.4:
                    reply = self._walk(me, (fx_, fy_))
                else:
                    reply = {"skill": "turn_to",
                             "target": [round(fx_, 2), round(fy_, 2)]}
                return self._say(reply, goal_line) if goal_line else reply
            if mem_ok:
                mx, my_ = self.ball_mem
                deep = asign * mx < -(PITCH_X - 3.0)
                if deep and not self.attack_biased:
                    post = (ogx + asign * 0.55,
                            _clip(my_, -(GOAL_HALF_W - 0.15),
                                  GOAL_HALF_W - 0.15))
                    if _d(me, post) > 0.5:
                        reply = self._walk(me, post)
                    else:
                        reply = {"skill": "turn_to",
                                 "target": [round(mx, 2), round(my_, 2)]}
                elif _d(me, (mx, my_)) > 1.4:
                    reply = self._walk(me, (mx, my_))
                else:
                    reply = {"skill": "turn_to"}
            else:
                spot = ((0.0, 0.0) if self.attack_biased
                        else (ogx + asign * 1.35, 0.0))
                reply = (self._walk(me, spot) if _d(me, spot) > 1.0
                         else {"skill": "turn_to"})
            return self._say(reply, goal_line) if goal_line else reply

        age = float(ball.get("age_s", 0.0))
        if age > 3.0:
            bspeed = 0.0
        vel = ball.get("velocity_mps") or [0.0, 0.0]
        if age > 3.0:
            vel = [0.0, 0.0]
        bx, by = bxy

        # -- shared state ---------------------------------------------------
        opps = det.get("opponents") or []
        mate_down = self.t < self.mate_down_until
        mate_known = (self.t - self.mate_seen_t) < 6.0 and self.mate_xy
        # v4: BOTH time-to-ball estimates go through the SAME capped formula.
        # The old asymmetry (mine via _meet with its 6 s cap and reaction
        # penalty, the mate's via raw distance) made both players reach the
        # same wrong belief at once — both "nearest" at long range (m22
        # @16.5: both dug the wall ball, nobody on the post) and both
        # "second" close in (m22 @412.1: both plugged the same post while
        # the ball was walked past them).
        my_t = _meet(me, bxy, vel)[0]
        if mate_down:
            mate_t = 1e9
        elif mate_known:
            mate_t = _meet(self.mate_xy, bxy, vel)[0]
        else:
            mate_t = my_t + (0.001 if not self.attack_biased else -0.001)
        # a radio claim is BINDING — but only while the WORLD still matches
        # it: the claim rode in with a ball fix, so it is valid only while
        # the ball remains near where the claimer said it was. Wall-time
        # freshness alone froze us against swarms (three straight practice
        # losses, territory ~100-20 against): the ball's situation turns
        # over every 2-3 s there, and honouring a 6 s-old "mine" meant
        # backing off loose balls nobody owned any more.
        claim_fresh = ((self.t - self.mate_claim_t) < 5.0
                       and self.fix_xy is not None
                       and _d(bxy, self.fix_xy) < 2.5)
        bias = -0.45 if self.role == "attack" else 0.45
        if claim_fresh and self.mate_claim == "ball" and _d(me, bxy) > 1.2:
            attack = False
        elif claim_fresh and self.mate_claim in ("cover", "line", "post"):
            attack = True
        elif abs(my_t - mate_t) < 0.25:
            attack = self.attack_biased
        else:
            attack = (my_t + bias) < mate_t
        role_was = self.role
        self.role = "attack" if attack else "cover"
        i_am_near = my_t <= mate_t
        if claim_fresh and self.mate_claim == "ball" and _d(me, bxy) > 1.2:
            i_am_near = False               # he took the ball: I take the post
        elif claim_fresh and self.mate_claim == "post":
            i_am_near = True                # he took the post: I dig

        our_mouth = (asign * bx < -(PITCH_X - 1.6)
                     and abs(by) <= GOAL_HALF_W + 0.4)
        our_corner = (asign * bx < -CORNER_X and abs(by) > CORNER_Y)
        their_corner = (asign * bx > CORNER_X and abs(by) > CORNER_Y)
        # threat = a ball that will actually arrive at our line soon, in our
        # half. Scoped tight: an over-eager version of this put the whole
        # team in permanent retreat and ceded the entire attacking third.
        driven = any(_d(o["field_xy"], bxy) < 1.0 for o in opps)
        threat = None
        if bspeed > 0.45 and asign * bx < 0.0:
            threat = _cross_our_line(bxy, vel, ogx, asign, driven=driven)
            # horizon 6.5 s: a drive from midfield takes ~5-6 s to arrive,
            # and the old 5.0 s gate threw away exactly that case (traced to
            # concessions in m07 and m12)
            if threat is not None and threat[0] > 6.5:
                threat = None

        say_key = None

        # ==== OUR MOUTH: clear along the end wall / plug the near post =====
        if our_mouth:
            if i_am_near and not (mate_down and _d(me, bxy) > 1.6):
                wing = 1.0 if by >= 0 else -1.0
                reply = {"skill": "kick_toward",
                         "target": [0.0, wing * (PITCH_Y - 0.6)]}
            else:
                post_y = (GOAL_HALF_W - 0.12) * (1.0 if by >= 0 else -1.0)
                post = (ogx + asign * 0.5, post_y)
                if _d(me, post) < 0.45:
                    reply = {"skill": "turn_to",
                             "target": [round(bx, 2), round(by, 2)]}
                else:
                    reply = self._walk(me, post, bxy)
                say_key = "post"

        # ==== OUR CORNER: dig along the side wall / plug the post ==========
        elif our_corner:
            if i_am_near and not (mate_down and _d(me, bxy) > 1.6):
                wing = 1.0 if by >= 0 else -1.0
                reply = {"skill": "kick_toward",
                         "target": [0.0, wing * (PITCH_Y - 0.6)]}
            else:
                post_y = (GOAL_HALF_W - 0.10) * (1.0 if by >= 0 else -1.0)
                post = (ogx + asign * 0.5, post_y)
                if _d(me, post) < 0.45:
                    reply = {"skill": "turn_to",
                             "target": [round(bx, 2), round(by, 2)]}
                else:
                    reply = self._walk(me, post, bxy)
                say_key = "post"

        # ==== THREAT: the ball's roll crosses our line — cut it off ========
        elif threat is not None:
            t_cross, y_cross = threat
            y_cross = _clip(y_cross, -(GOAL_HALF_W - 0.10), GOAL_HALF_W - 0.10)
            line_pt = (ogx + asign * 0.5, y_cross)
            # full stride on the line race (walk_to bursts ~0.85-1.0 aligned).
            # Give up the line only when GROSSLY hopeless (>4.5 s late —
            # drives stall between shoves, so moderately late still blocks
            # the second phase). The old 2.5 s clause produced
            # chase-from-behind concessions (m07 110.3/121.2, m12 525.3);
            # NO clause at all produced passive pinning (round-6 practice,
            # territory 102-22 against). 4.5 s is the measured middle.
            my_line = _d(me, line_pt) / 0.85
            mate_line = (_d(self.mate_xy, line_pt) / 0.85
                         if mate_known and not mate_down else 1e9)
            t_meet, meet_pt = _meet(me, bxy, vel)
            # claim hysteresis: whoever ANNOUNCED the line keeps it for a
            # few seconds — two players flip-flopping the line job between
            # slots is how nobody ends up on it
            i_claimed_line = (self.my_claim == "line"
                              and (self.t - self.my_claim_t) < 4.0)
            mate_claimed_line = (claim_fresh and self.mate_claim == "line")
            if ((my_line <= mate_line or i_claimed_line)
                    and not mate_claimed_line and my_line < t_cross + 4.5):
                if t_cross < 3.0:
                    # imminent: body ON the crossing point
                    if _d(me, line_pt) < 0.4:
                        reply = {"skill": "turn_to",
                                 "target": [round(bx, 2), round(by, 2)]}
                    else:
                        reply = self._walk(me, line_pt, bxy)
                else:
                    # far threat: JOCKEY goal-side on the lane, not a statue
                    # on the line — close enough (2.2 m) to convert into the
                    # wedge the moment the drive stalls. Statue-mode on far
                    # threats pinned us 91-15 on territory in practice.
                    og = (ogx, 0.0)
                    lx, ly = og[0] - bx, og[1] - by
                    n = math.hypot(lx, ly) or 1.0
                    jx = _clip(bx + lx / n * 2.2, -PITCH_X + 0.6,
                               PITCH_X - 0.6)
                    jy = _clip(by + ly / n * 2.2, -PITCH_Y + 0.6,
                               PITCH_Y - 0.6)
                    if _d(me, (jx, jy)) < 0.4:
                        reply = {"skill": "turn_to",
                                 "target": [round(bx, 2), round(by, 2)]}
                    else:
                        reply = self._walk(me, (jx, jy), bxy)
                say_key = "line"
            elif t_meet < t_cross:
                reply = {"skill": "go_to_ball",
                         "lead_s": round(_clip(t_meet, 0.0, 2.0), 2)}
            else:
                reply = {"skill": "go_to_ball"}

        elif attack:
            reply = self._on_ball(me, bxy, bspeed, vel, ball, opps, gx, asign)
        else:
            reply, say_key = self._off_ball(me, bxy, bspeed, vel, opps, ogx,
                                            gx, asign, score, rem, mate_down,
                                            my_t, mate_t, their_corner)

        # -- separation: never shoulder my own teammate — but NEVER evict a
        #    defender from a line/post job (plug and line-racer stand close
        #    by design; shoving one aside opens the exact gap they plug)
        if (not attack and say_key not in ("line", "post")
                and mates and _d(me, self.mate_xy) < 1.1
                and _d(me, bxy) > 1.5):
            ax_, ay_ = me[0] - self.mate_xy[0], me[1] - self.mate_xy[1]
            n = math.hypot(ax_, ay_) or 1.0
            reply = self._walk(me, (_clip(me[0] + ax_ / n * 1.2,
                                          -PITCH_X + 0.5, PITCH_X - 0.5),
                                    _clip(me[1] + ay_ / n * 1.2,
                                          -PITCH_Y + 0.5, PITCH_Y - 0.5)))

        # -- blocked far from the ball: sidestep out of the shove -----------
        if obs["self"].get("blocked") and _d(me, bxy) > 1.15:
            ux, uy = bx - me[0], by - me[1]
            n = math.hypot(ux, uy) or 1.0
            side = 1.0 if me[1] > 0 else -1.0
            reply = self._walk(me, (_clip(me[0] - uy / n * 0.9 * side,
                                          -PITCH_X + 0.5, PITCH_X - 0.5),
                                    _clip(me[1] + ux / n * 0.9 * side,
                                          -PITCH_Y + 0.5, PITCH_Y - 0.5)))

        tgt = reply.get("target")
        if isinstance(tgt, list):
            reply["target"] = [round(float(tgt[0]), 2), round(float(tgt[1]), 2)]

        # -- radio: event lines keep their fable voice; EVERY other slot the
        #    cooldown allows carries an honest ball fix + my intent. The
        #    receiver decodes it — the radio is the team's shared eyes.
        if goal_line:
            return self._say(reply, goal_line)
        if mate_down and "down" not in self.last_line:
            return self._say(reply, "solo")
        # broadcast on a slightly stale ball too (age < 2.5): a strict
        # seen_now gate once turned a slipped cooldown slot into a 12 s
        # radio silence while the ball crossed the pitch (m22 @140)
        if ball is not None and float(ball.get("age_s", 9.0)) < 2.5:
            intent = say_key or ("take" if attack else "cover")
            return self._say_fix(reply, intent, bxy, vel, asign)
        return reply

    # -------------------------------------------------- on the ball (duel)
    def _on_ball(self, me, bxy, bspeed, vel, ball, opps, gx, asign):
        bx, by = bxy
        goal = (gx, 0.0)
        d_goal = _d(bxy, goal)

        # their mouth band: ram it straight through
        if asign * bx > PITCH_X - 1.6 and abs(by) <= GOAL_HALF_W + 0.3:
            return {"skill": "kick_toward",
                    "target": [gx, _clip(by, -1.1, 1.1)]}

        # their corner: dig it toward the mouth along the end wall
        if asign * bx > CORNER_X and abs(by) > CORNER_Y:
            return {"skill": "kick_toward",
                    "target": [gx, (1.0 if by >= 0 else -1.0)]}

        # shooting range: place the shot at the corner the keeper isn't in
        if d_goal < 3.4:
            aim_y = _clip(by * 0.3, -0.9, 0.9)
            keeper, best = None, 2.6
            for o in opps:
                dk = _d(o["field_xy"], goal)
                if dk < best:
                    best, keeper = dk, o
            if keeper is not None:
                # 0.6 margin: the ball is 0.35 m — tighter aims clip the post
                aim_y = (GOAL_HALF_W - 0.6) * (-1.0 if keeper["field_xy"][1] >= 0
                                               else 1.0)
            return {"skill": "kick_toward", "target": [gx, aim_y]}

        # blocked lane in the middle third: knock it into the open channel
        if -2.3 < asign * bx < 3.6 and bspeed < 0.6:
            blockers, traffic = 0, {1.0: 0, -1.0: 0}
            for o in opps:
                ox, oy = o["field_xy"]
                if asign * (ox - bx) > 0.3 and asign * ox < asign * gx:
                    if abs(oy - by) < 1.2:
                        blockers += 1
                    traffic[1.0 if oy >= 0 else -1.0] += 1
            if blockers >= 1:
                side = 1.0 if traffic[1.0] <= traffic[-1.0] else -1.0
                return {"skill": "kick_toward",
                        "target": [_clip(bx + asign * 3.5, -5.9, 5.9),
                                   side * 2.7]}

        # open field: intercept at the measured meet time, executed through
        # the CLOSED-LOOP skill (go_to_ball re-solves its lead every control
        # step; an open-loop walk_to a predicted point stops dead and loses
        # the ball — measured: it ceded the whole attacking third). Never
        # lead a ball already rolling goalward with me behind it (that
        # overrun cost -5 m of contact advance on founding night, and two
        # own goals in round 1).
        t_meet, meet_pt = _meet(me, bxy, vel)
        lead = 0.0
        if bspeed > 0.35 and _d(me, bxy) > 2.0:
            # the skill projects linearly (no decay), so cap the horizon to
            # keep its aim error inside a body width
            lead = _clip(t_meet, 0.3, 1.6)
        ux, uy = me[0] - bx, me[1] - by
        n = math.hypot(ux, uy) or 1.0
        if (vel[0] * ux + vel[1] * uy) / n > 0.15:
            lead = min(lead, 0.4)
        if vel[0] * asign > 0.2:
            lead = 0.0
        if lead > 0.0:
            return {"skill": "go_to_ball", "lead_s": round(lead, 2)}
        return {"skill": "go_to_ball"}

    # ----------------------------------------------- off the ball (free)
    def _off_ball(self, me, bxy, bspeed, vel, opps, ogx, gx, asign, score,
                  rem, mate_down, my_t, mate_t, their_corner):
        bx, by = bxy

        # their corner with the ball slow: the ram is arming. Collect the
        # eject from the MIDFIELD side, not the corner's doorstep — round 1
        # scored us two corner goals with the digger alone, and the one
        # time both players committed deep, a punt sailed past them both
        # for a goal. Depth discipline pays better than doorstep poaching.
        if their_corner and bspeed < 0.5:
            spot = (asign * 2.3, (1.0 if by >= 0 else -1.0) * 1.3)
            if _d(me, spot) < 0.5:
                return ({"skill": "turn_to",
                         "target": [round(bx, 2), round(by, 2)]}, "ram")
            return (self._walk(me, spot, bxy), "ram")

        # clear and present danger: engage and clear (skills aim goalward).
        # In OUR half a contested ball is a WEDGE call — founding-night
        # doctrine that drifted out of the code: one dueler + one backstop
        # loses the shove war to any two-body press (re-measured round 6:
        # the anchor once hovered 5 cm outside the old 2.3 m radius and
        # walked away while his mate fought 1v2).
        near_our_goal = asign * bx < -(PITCH_X - 2.6)
        contested = any(_d(o["field_xy"], bxy) < 1.0 for o in opps)
        reach = 3.2 if (contested and asign * bx < 0.5) else 2.3
        if _d(me, bxy) < reach or (near_our_goal and (mate_down
                                                      or mate_t > my_t + 1.2)):
            split = 0.8 if self.number == 1 else -0.8
            if contested:
                return ({"skill": "kick_toward", "target": [gx, split]},
                        "wedge")
            return ({"skill": "go_to_ball"}, None)

        # we lost round 1 from 6-5 up with 43 s left: any lead in the final
        # stretch pulls the anchor onto the keeper's arc
        lead_n = (score.get("you", 0) - score.get("them", 0)) if score else 0
        cautious = (lead_n >= 2 and rem < 120.0) or (lead_n >= 1 and rem < 70.0)

        # free ball in their half: OUTLET ahead of the play, depth-capped
        if asign * bx > 0.5 and not cautious:
            out_x = _clip(bx + asign * 2.3, -PITCH_X + 0.8, PITCH_X - 0.8)
            if asign * out_x > 2.0:
                out_x = asign * 2.0
            return (self._walk(me, (out_x, _clip(by * 0.4, -2.2, 2.2)), bxy),
                    None)

        # free ball in our half: BACKSTOP on the ball-to-goal line, shifted
        # a stride toward mid-pitch, out of the attacker's lane
        if not cautious:
            og = (ogx, 0.0)
            lx, ly = og[0] - bx, og[1] - by
            n = math.hypot(lx, ly) or 1.0
            px_, py_ = -ly / n, lx / n
            if abs(by + py_ * 0.9) > abs(by - py_ * 0.9):
                px_, py_ = -px_, -py_
            tgt = (_clip(bx + lx / n * 2.3 + px_ * 0.9,
                         -PITCH_X + 0.7, PITCH_X - 0.7),
                   _clip(by + ly / n * 2.3 + py_ * 0.9,
                         -PITCH_Y + 0.7, PITCH_Y - 0.7))
            return (self._walk(me, tgt, bxy), None)

        # protecting a lead late: keeper's arc between ball and our net
        og = (ogx, 0.0)
        ux, uy = bx - og[0], by - og[1]
        n = math.hypot(ux, uy) or 1.0
        hx = _clip(og[0] + ux / n * 1.35, -PITCH_X + 0.6, PITCH_X - 0.6)
        hy = _clip(og[1] + uy / n * 1.35, -(GOAL_HALF_W - 0.15),
                   GOAL_HALF_W - 0.15)
        if _d(me, (hx, hy)) < 0.35:
            return ({"skill": "turn_to", "target": [round(bx, 2),
                                                    round(by, 2)]}, None)
        return (self._walk(me, (hx, hy), bxy), None)


def build_team(ctx):
    """The engine's only entry point. ctx brings team.yaml as ctx["config"];
    this club's players are code, so nothing in it is needed here."""
    return {"players": [FablePlayer(1), FablePlayer(2)], "manager": None}
