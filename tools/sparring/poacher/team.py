"""Sparring dummy #2: presser + poacher, the shape that beat us in round 1.

Press-1 chases and shoots like the mock. Lurk-2 loiters at the edge of
OUR defensive box, pokes in anything loose, and retreats no further than
midfield — a caricature of Robodinho/Spark. Hand-written so practice
stays free and deterministic.
"""

import math


class Press:
    def __init__(self, number):
        self.name = f"Press-{number}"
        self.episode_usage = {}

    def begin_episode(self, log_dir=None):
        pass

    def decide(self, obs):
        det = obs.get("detections") or {}
        ball = det.get("ball")
        gx = float(obs["you"]["attack_goal_xy"][0])
        if obs["self"].get("fallen"):
            return {"skill": "hold"}
        if ball is None:
            return {"skill": "turn_to"}
        if ball.get("distance_m", 99.0) < 1.0:
            return {"skill": "kick_toward", "target": [gx, 0.0]}
        return {"skill": "go_to_ball"}


class Lurk:
    """Hangs around the opponent goal, pokes in loose balls."""

    def __init__(self, number):
        self.name = f"Lurk-{number}"
        self.episode_usage = {}

    def begin_episode(self, log_dir=None):
        pass

    def decide(self, obs):
        det = obs.get("detections") or {}
        ball = det.get("ball")
        gx = float(obs["you"]["attack_goal_xy"][0])
        asign = 1.0 if gx > 0 else -1.0
        me = obs["self"]["field_xy"]
        if obs["self"].get("fallen"):
            return {"skill": "hold"}
        if ball is None:
            post = (gx - asign * 2.2, 0.0)
            if math.hypot(me[0] - post[0], me[1] - post[1]) > 1.0:
                return {"skill": "walk_to", "target": [post[0], post[1]]}
            return {"skill": "turn_to"}
        bx, by = ball["field_xy"]
        # poach anything within reach or anything in the attacking third
        if ball.get("distance_m", 99.0) < 2.8 or asign * bx > 2.3:
            if ball.get("distance_m", 99.0) < 1.0:
                return {"skill": "kick_toward", "target": [gx, by * 0.3]}
            return {"skill": "go_to_ball"}
        # otherwise loiter at the edge of the box, level with the ball
        return {"skill": "walk_to",
                "target": [gx - asign * 2.2,
                           max(-2.0, min(2.0, by * 0.5))]}


def build_team(ctx):
    return {"players": [Press(1), Lurk(2)], "manager": None}
