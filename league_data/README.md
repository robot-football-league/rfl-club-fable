# league_data/

Written by the league after each of your matches — **do not edit by hand**;
it is overwritten. This is YOUR private telemetry: no other club sees it.

Per match you get:

- `decisions.jsonl` — every decision your two players made, including the
  ones the engine THREW AWAY. Check the `status` field:
  - `ok` — applied
  - `missed_deadline` — your reply arrived after the 3 s shot clock and was
    discarded. The robot kept doing whatever it was already doing.
  - `abandoned_hung_call` — your brain never answered; the engine gave up
    after 10 s and freed the robot to ask again.
  - `ignored_invalid` — the reply did not parse as a legal skill.
- `health.json` — the summary: how many decisions landed, how many were
  dropped, and your latency spread against the deadline.

If `dropped_pct` is high, your players are effectively playing with fewer
decisions than the opposition. That is a competitive problem you can fix:
a faster model, a lower reasoning effort, a smaller prompt, fewer history
turns, or local logic that acts while a slow call is in flight.
