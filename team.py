"""AFC Fable — the first team, in one file.

Two hand-written deterministic players (RFL_RULES.md: "how you produce
decisions is your business ... hand-written code"). No model API is called
at match time: every decision is geometry computed from the SDK detections,
inside a microsecond, never late against the 3 s bridge deadline.

The shape of the football, learned the hard way in founding-night practice:

  CONTESTED ball (an opponent is on it): both players join as a WEDGE —
      two push vectors at split angles beat one fair duel. 2v2 football is
      won and lost in the shoving.
  FREE ball: the nearer player takes it; the other plays OUTLET ahead of
      the play in their half (a swarm has no defenders — breakthroughs are
      collected in front of an empty net) or BACKSTOP behind the play in
      ours (second balls, clearances).
  OUR BOX: the last defender's job is the SHOT LINE, not the duel — plant
      the body where the ball's path crosses the mouth, then poke clear.

Role assignment is time-to-ball with hysteresis; #2 Hare wins dead heats
(attack-biased), #1 Tortoise anchors. The radio is honest natural language,
spoken only on real transitions, in each player's fable voice.

Everything here sits ON the engine's public skill contract: go_to_ball /
kick_toward approach the correct side of the ball, orbit rather than barge,
and repair stances at walls. This layer decides WHO goes, WHERE to aim,
and WHERE the off-ball player stands.

Engine notes (rfl-0.3, verified in practice logs):
  - obs["you"]["defend_goal_xy"] reports the WRONG end for the home team
    (obs_for passes a team index where a robot index is expected), so our
    own goal is derived as the mirror of attack_goal_xy. Public obs, same
    for every club.
  - A ball pinned >8 s teleports to the centre spot (referee drop): when
    the count runs high, the off-ball player camps the drop.
"""

import math

# Pitch facts (docs/RFL_RULES.md; obs["field"] agrees at runtime).
PITCH_X = 7.0            # goal lines at x = +-7
PITCH_Y = 4.5            # side walls at y = +-4.5
GOAL_HALF_W = 1.6        # goal mouth |y| < 1.6
WALK_MPS = 0.7           # planning estimate of cruise speed
FALL_OUT_S = 8.0         # a fallen robot is out this long

SAY_GAP_S = 12.0         # self-imposed radio discipline (engine floor is 10)


def _d(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _clip(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


# Radio voice: honest tactical calls in each player's fable voice.
LINES = {
    "Tortoise": {
        "kickoff":  "Steady from the whistle — I've got our half.",
        "take":     "Mine — slow and steady.",
        "leave":    "Yours, Hare — I'll hold the line.",
        "wedge":    "Shoulder to shoulder — push with me.",
        "goal_for": "The moral so far: patience scores.",
        "goal_against": "A lesson, not a defeat. Reset and go again.",
        "down":     "I'm down — eight seconds. Hold the fort, Hare.",
        "camp":     "Referee's counting — I'll take the drop at centre.",
        "solo":     "You rest — I'll carry us till you're up.",
    },
    "Hare": {
        "kickoff":  "Off at the whistle — first touch is mine!",
        "take":     "Mine! No naps today.",
        "leave":    "All yours, Tortoise — dropping back.",
        "wedge":    "Two of us now — heave!",
        "goal_for": "Fast AND finished this time!",
        "goal_against": "They won't outrun us twice. Again.",
        "down":     "Legs gone — eight seconds. Yours, Tortoise!",
        "camp":     "Drop ball coming — I'm on the centre spot.",
        "solo":     "I've got both ends till you're back up.",
    },
}


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
        self.t0_rem = None          # first-seen time_remaining_s
        self.t = 0.0                # elapsed match seconds (from remaining)
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

    # ---------------------------------------------------------------- radio
    def _say(self, reply, key):
        line = LINES[self.name].get(key, "")
        if not line or line == self.last_line or self.t < self.say_ok_t:
            return reply
        reply["say"] = line
        self.say_ok_t = self.t + SAY_GAP_S
        self.last_line = line
        return reply

    # ----------------------------------------------------------------- main
    def decide(self, obs):
        det = obs.get("detections") or {}
        ball = det.get("ball")
        me = obs["self"]["field_xy"]
        you = obs["you"]
        gx = float(you["attack_goal_xy"][0])
        # NOT obs defend_goal_xy — see module docstring: wrong for the home
        # team in rfl-0.3. The pitch is symmetric; our goal is the mirror.
        ogx = -gx
        asign = 1.0 if gx > 0 else -1.0
        score = obs.get("score") or {}
        rem = float(obs.get("time_remaining_s", 0.0))
        ref = obs.get("referee") or {}
        stuck_s = float(ref.get("ball_stuck_s", 0.0))

        # -- clock: derive an increasing elapsed time from the countdown
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

        mate_msg = (obs.get("teammate_says") or "").lower()
        if "down" in mate_msg or "legs gone" in mate_msg:
            self.mate_down_until = self.t + FALL_OUT_S

        mates = det.get("teammates") or []
        if mates:
            self.mate_xy = tuple(mates[0]["field_xy"])
            self.mate_seen_t = self.t

        # -- fallen: nothing to do but say so once and wait -----------------
        if obs["self"].get("fallen"):
            reply = {"skill": "hold"}
            if not self.self_down_said:
                self.self_down_said = True
                self.say_ok_t = -1e9        # a fall is worth interrupting for
                self._say(reply, "down")
            return reply
        self.self_down_said = False

        # -- restart detection: ball at centre, still, me at a kickoff spot -
        bxy = tuple(ball["field_xy"]) if ball else None
        bspeed = float(ball.get("speed_mps", 0.0)) if ball else 0.0
        if (bxy is not None and _d(bxy, (0.0, 0.0)) < 0.4 and bspeed < 0.2
                and 2.0 < abs(me[0]) < 3.0 and 0.7 < abs(me[1]) < 1.7):
            if self.t > self.kickoff_until:      # a fresh restart
                self.kickoff_said = False
            self.kickoff_until = self.t + 6.0
        kickoff_play = (self.t < self.kickoff_until and bxy is not None
                        and _d(bxy, (0.0, 0.0)) < 1.2)

        # -- kickoff: both press as a wedge with split aims — the centre
        #    duel is 2v2 and we don't concede the first shove.
        if kickoff_play:
            split = 0.5 if self.number == 1 else -0.5
            reply = {"skill": "kick_toward", "target": [gx, split]}
            if goal_line:
                return self._say(reply, goal_line)
            if not self.kickoff_said:
                self.kickoff_said = True
                return self._say(reply, "kickoff")
            return reply

        # -- a remembered ball at my feet that I plainly can't see is GONE --
        if (ball is not None and not ball.get("seen_now")
                and float(ball.get("age_s", 0.0)) > 1.5
                and _d(me, bxy) < 1.2):
            ball, bxy = None, None

        # -- ball unknown: search without leaving my job. The anchor faces
        #    midfield from home (that is where balls come from); the runner
        #    goes to the centre spot and sweeps.
        if ball is None:
            if self.attack_biased:
                spot = (0.0, 0.0)
            else:
                spot = (ogx + asign * 1.35, 0.0)
            if _d(me, spot) > 1.0:
                reply = {"skill": "walk_to",
                         "target": [round(spot[0], 2), round(spot[1], 2)]}
            elif self.attack_biased:
                reply = {"skill": "turn_to"}     # sweep for the magenta ball
            else:
                reply = {"skill": "turn_to", "target": [0.0, 0.0]}
            return self._say(reply, goal_line) if goal_line else reply

        age = float(ball.get("age_s", 0.0))
        if age > 3.0:
            bspeed = 0.0                          # don't lead a ghost
        vel = ball.get("velocity_mps") or [0.0, 0.0]
        bx, by = bxy

        # -- a remembered ball I should plainly see isn't there: reacquire --
        if not ball.get("seen_now") and age > 2.0 and _d(me, bxy) < 2.2:
            reply = {"skill": "turn_to", "target": [round(bx, 2), round(by, 2)]}
            return self._say(reply, goal_line) if goal_line else reply

        # -- game state -----------------------------------------------------
        opps = det.get("opponents") or []
        contested = any(_d(o["field_xy"], bxy) < 1.1 for o in opps)
        mate_down = self.t < self.mate_down_until
        mate_known = (self.t - self.mate_seen_t) < 6.0 and self.mate_xy
        my_t = _d(me, bxy) / WALK_MPS
        if mate_down:
            mate_t = 1e9
        elif mate_known:
            mate_t = _d(self.mate_xy, bxy) / WALK_MPS
        else:
            mate_t = my_t + (0.001 if not self.attack_biased else -0.001)
        bias = -0.45 if self.role == "attack" else 0.45
        if abs(my_t - mate_t) < 0.25:
            attack = self.attack_biased           # dead heat: fable order
        else:
            attack = (my_t + bias) < mate_t
        role_was = self.role
        self.role = "attack" if attack else "cover"

        # danger = anywhere the next touch can put it in: a 3 m radius of our
        # goal centre (covers the wall channels that feed the mouth), plus
        # the mouth band itself a little further out
        in_our_box = (_d(bxy, (ogx, 0.0)) < 3.0
                      or (asign * bx < -(PITCH_X - 2.4)
                          and abs(by) < GOAL_HALF_W + 0.9))
        rolling_in = bspeed > 0.35 and vel[0] * (-asign) > 0.2

        # -- pick the job ---------------------------------------------------
        if attack:
            reply = self._on_ball(me, bxy, bspeed, vel, ball, opps, gx, asign)
        elif in_our_box or (rolling_in and asign * bx < 0.0):
            reply = self._shot_line(me, bxy, bspeed, vel, ogx, asign)
        elif contested and not mate_down:
            reply = self._wedge(me, bxy, gx, asign)
        else:
            reply = self._off_ball(me, bxy, bspeed, opps, ogx, gx, asign,
                                   score, rem, stuck_s, mate_down, my_t,
                                   mate_t)

        # -- separation: never shoulder my own teammate ---------------------
        if (not attack and mates and _d(me, self.mate_xy) < 1.1
                and _d(me, bxy) > 1.5):
            ax_, ay_ = me[0] - self.mate_xy[0], me[1] - self.mate_xy[1]
            n = math.hypot(ax_, ay_) or 1.0
            reply = {"skill": "walk_to",
                     "target": [round(_clip(me[0] + ax_ / n * 1.2,
                                            -PITCH_X + 0.5, PITCH_X - 0.5), 2),
                                round(_clip(me[1] + ay_ / n * 1.2,
                                            -PITCH_Y + 0.5, PITCH_Y - 0.5), 2)]}

        # -- blocked far from the ball: sidestep out of the shove -----------
        if obs["self"].get("blocked") and _d(me, bxy) > 1.15:
            ux, uy = bx - me[0], by - me[1]
            n = math.hypot(ux, uy) or 1.0
            side = 1.0 if me[1] > 0 else -1.0     # step toward mid-pitch
            reply = {"skill": "walk_to",
                     "target": [round(_clip(me[0] - uy / n * 0.9 * side,
                                            -PITCH_X + 0.5, PITCH_X - 0.5), 2),
                                round(_clip(me[1] + ux / n * 0.9 * side,
                                            -PITCH_Y + 0.5, PITCH_Y - 0.5), 2)]}

        tgt = reply.get("target")
        if isinstance(tgt, list):
            reply["target"] = [round(float(tgt[0]), 2), round(float(tgt[1]), 2)]

        # -- one voice line, by priority ------------------------------------
        if goal_line:
            return self._say(reply, goal_line)
        if mate_down and "down" not in self.last_line:
            return self._say(reply, "solo")
        if reply.get("_wedge"):
            reply.pop("_wedge", None)
            return self._say(reply, "wedge")
        reply.pop("_wedge", None)
        if self.role != role_was:
            return self._say(reply, "take" if attack else "leave")
        return reply

    # -------------------------------------------------- on the ball (duel)
    def _on_ball(self, me, bxy, bspeed, vel, ball, opps, gx, asign):
        bx, by = bxy
        goal = (gx, 0.0)
        d_goal = _d(bxy, goal)
        on_wall = bool(ball.get("against_wall"))

        # our own corner pocket: don't push at our goal — clear down the wing
        if on_wall and asign * bx < -(PITCH_X - 1.4) and abs(by) > GOAL_HALF_W:
            wing = 1.0 if by > 0 else -1.0
            return {"skill": "kick_toward",
                    "target": [0.0, wing * (PITCH_Y - 0.5)]}

        # shooting range: place the shot at the corner the keeper isn't in
        if d_goal < 3.4:
            aim_y = _clip(by * 0.3, -0.9, 0.9)
            keeper, best = None, 2.6
            for o in opps:
                dk = _d(o["field_xy"], goal)
                if dk < best:
                    best, keeper = dk, o
            if keeper is not None:
                aim_y = (GOAL_HALF_W - 0.5) * (-1.0 if keeper["field_xy"][1] >= 0
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

        # open field: a modest lead to intercept a crossing ball — but never
        # overrun it. Founding-night practice measured aggressive leads
        # putting the striker goal-side, pushing the ball BACKWARD (-5 m of
        # net advance). Close in, or with the ball already rolling the right
        # way, play it where it is and let the stance geometry do the work.
        lead = 0.0
        d_me = _d(me, bxy)
        if bspeed > 0.35 and d_me > 2.0:
            lead = _clip(0.45 * d_me / WALK_MPS, 0.3, 1.2)
        ux, uy = me[0] - bx, me[1] - by
        n = math.hypot(ux, uy) or 1.0
        if (vel[0] * ux + vel[1] * uy) / n > 0.15:   # rolling at me
            lead = min(lead, 0.4)
        if vel[0] * asign > 0.2:                     # already goalward
            lead = 0.0
        if lead > 0.0:
            return {"skill": "go_to_ball", "lead_s": round(lead, 2)}
        return {"skill": "go_to_ball"}

    # ------------------------------------------------- the wedge (2v2 duel)
    def _wedge(self, me, bxy, gx, asign):
        """Join a contested duel as the second pusher, at a split angle so
        we arrive shoulder-to-shoulder, never in each other's stance."""
        split = 0.8 if self.number == 1 else -0.8
        return {"skill": "kick_toward", "target": [gx, split], "_wedge": True}

    # ------------------------------------------- last defender: shot line
    def _shot_line(self, me, bxy, bspeed, vel, ogx, asign):
        bx, by = bxy
        line_x = ogx + asign * 0.55
        if _d(me, bxy) < 1.35 or (bspeed < 0.15 and _d(me, bxy) < 2.1):
            return {"skill": "go_to_ball"}       # close enough: poke it clear
        y_block = by
        if abs(vel[0]) > 0.05:
            t_hit = (line_x - bx) / vel[0]
            if 0.0 < t_hit < 6.0:
                y_block = by + vel[1] * t_hit
        return {"skill": "walk_to",
                "target": [line_x, _clip(y_block, -(GOAL_HALF_W - 0.1),
                                         GOAL_HALF_W - 0.1)]}

    # ----------------------------------------------- off the ball (free)
    def _off_ball(self, me, bxy, bspeed, opps, ogx, gx, asign, score, rem,
                  stuck_s, mate_down, my_t, mate_t):
        bx, by = bxy

        # dropped ball incoming: be the one standing at the centre spot
        near_our_goal = asign * bx < -(PITCH_X - 2.6)
        if stuck_s > 5.0 and _d(bxy, (0.0, 0.0)) > 0.7 and not near_our_goal:
            reply = {"skill": "walk_to", "target": [-asign * 1.1, 0.0]}
            return self._say(reply, "camp")

        # clear and present danger: engage and clear (skills aim goalward)
        if _d(me, bxy) < 2.3 or (near_our_goal and (mate_down
                                                    or mate_t > my_t + 1.2)):
            return {"skill": "go_to_ball"}

        two_up = score and score.get("you", 0) - score.get("them", 0) >= 2
        cautious = two_up and rem < 120.0

        # free ball in their half: OUTLET ahead of the play to collect
        # breakthroughs — but with anchor discipline: never so deep that one
        # long punt strands me (walking home costs ~1.4 s per metre)
        if asign * bx > 0.5 and not cautious:
            out_x = _clip(bx + asign * 2.3, -PITCH_X + 0.8, PITCH_X - 0.8)
            if asign * out_x > 2.0:
                out_x = asign * 2.0
            return {"skill": "walk_to",
                    "target": [out_x, _clip(by * 0.4, -2.2, 2.2)]}

        # free ball in our half: BACKSTOP on the ball-to-goal line, shifted
        # a stride sideways — covering the clearance lane without standing
        # in the attacker's push-through
        if not cautious:
            og = (ogx, 0.0)
            lx, ly = og[0] - bx, og[1] - by
            n = math.hypot(lx, ly) or 1.0
            px_, py_ = -ly / n, lx / n            # perpendicular unit
            if abs(by + py_ * 0.9) > abs(by - py_ * 0.9):
                px_, py_ = -px_, -py_             # offset toward mid-pitch
            return {"skill": "walk_to",
                    "target": [_clip(bx + lx / n * 2.3 + px_ * 0.9,
                                     -PITCH_X + 0.7, PITCH_X - 0.7),
                               _clip(by + ly / n * 2.3 + py_ * 0.9,
                                     -PITCH_Y + 0.7, PITCH_Y - 0.7)]}

        # protecting a lead late: keeper's arc between ball and our net
        og = (ogx, 0.0)
        ux, uy = bx - og[0], by - og[1]
        n = math.hypot(ux, uy) or 1.0
        hx = _clip(og[0] + ux / n * 1.35, -PITCH_X + 0.6, PITCH_X - 0.6)
        hy = _clip(og[1] + uy / n * 1.35, -(GOAL_HALF_W - 0.15),
                   GOAL_HALF_W - 0.15)
        if _d(me, (hx, hy)) < 0.35:
            return {"skill": "turn_to", "target": [bx, by]}
        return {"skill": "walk_to", "target": [hx, hy]}


def build_team(ctx):
    """The engine's only entry point. ctx brings team.yaml as ctx["config"];
    this club's players are code, so nothing in it is needed here."""
    return {"players": [FablePlayer(1), FablePlayer(2)], "manager": None}
