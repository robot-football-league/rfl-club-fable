"""Sparring dummy: the engine's offline mock brain (naive ball chaser)."""


def build_team(ctx):
    from gauntlet.football import make_football_agent
    base = ctx["team_index"] * 2
    players = [make_football_agent("llm:mock:ok", base + k, seed=base + k,
                                   prompt="football_v3")
               for k in range(2)]
    return {"players": players, "manager": None}
