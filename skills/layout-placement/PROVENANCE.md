# layout-placement provenance

## Source

The Nordic PCB placement skill lab's frozen v18, handed off as
`layout-placement-v18.tar.gz`
(sha256 `39c00c45e66b1ba6938fa3b84cfcab13268776b7f2345d86c4b581936d796a54`).
Its files match the lab's `skills/snapshots/v18.sha256`:

```
edbb639cf71645eec2e7188679f5476d6f90219b273754fe1d7e7a27d3a60c1a  SKILL.md
f37c85f7aae992774acc4c6dd47212e35002aef2928c9368b6dfa0eda5acf330  scripts/grid_router.py
e112d192b135bb57d58b8126f0ed22a718e4c198107535ffe0f65b7c130a1b18  scripts/group_search.py
ad83535e93d463b38a46cae2af295cf24d9d5af7e471090f313149cfa363d532  scripts/ipc_board.py
3bb282dcd7cf3190304669b847e9ebda48e53480dfe6ef83c73493f8d06d51a7  scripts/local_search.py
f3ae39bc67909101f2acc005247dab3d59959b6240845d2e940a9322e7658a2a  scripts/move.py
69615a716533804d28a2f524016c222eda873ae9ceaf8fe1d6f33ddae7be9f24  scripts/pin_sides.py
7bec7b9dedde6aa80fb6fef38babbf6e6f3855d90c8ac9297c535981ad5e108a  scripts/placement_audit.py
75dd0f805adb01706bda27552698c5e2e53f9b3812aef8b37188400f03702ec5  scripts/route_check.py
```

In KiStack's history the commit "import layout-placement v18 ... unchanged"
holds exactly these files, and the commit after it holds every change below.

## What the lab measured

The lab's handoff reports these results for v18 (copied from the handoff
brief, not checked again here). They come from a few small Nordic QFN
benchmark boards, with the lab's own evaluators, and are not a fresh-model
comparison or an untouched holdout:

- with the v1.5 evaluator (links and DRC checked together), two of two runs
  on the nRF54L15 board (gpt-6.1-sol) passed;
- the older v1.1 to v1.3 evaluators fail one link on that board;
- the nRF54LS05B validation board misses one escape.

Nothing in this copy was measured again. The changes below are packaging,
safety and wording. They do not requalify the skill's placement results.

## v19 (RF matching network)

The lab's v19 (`layout-placement-v19.tar.gz`, sha256
`4c976fab5739344e76392c19c965506528c76dfaa29193b754efbef03c003dd2`, files
matching `skills/snapshots/v19.sha256`; v18 unchanged) changes three files:

- SKILL.md: the case "An RF matching network (pi or T)": series parts on one
  line, each shunt's node pad in a gap on that line, a vendor-forced branch
  kept short and stated, the gaps counted before the IC's distance to the
  port is set, and the check is geometry only. The RF chain row of the table,
  the Distances check and the fix list follow it.
- `placement_audit.py --chain`: each shunt reads `inline`, `no branch, but
  ... off the path`, or `OFF THE PATH: a X mm branch`, from pad polygons,
  against a `--rf-track` wide path through its node.
- `ipc_board.py`: pads with no copper layer (paste-only apertures) are
  skipped.

Ported here on top of the changes below, with one difference: `--rf-track`
has no default (the lab's is 0.3 mm), and `--chain` without it is refused,
because a width wider than the board's real track would read a shunt beside
the path as inline. With `--rf-track 0.3` the port prints what v19 prints
(tested on a synthetic chain). The lab's regression of the new check (the
Nordic reference, a hand-corrected showcase that is not agent output, and
three agent boards) is theirs, in the lab's `extra/handoff/v19_rf_regression/`,
and was not run again here.

## v20 (vendor ground tie over an inline shunt)

The lab's fresh v19 runs (their `layout-placement-v19.README.md`) found a
gap: an Opus 5.5 run put all three shunts inline but moved C6's ground
1.332 mm from pin 32, against Nordic's note that it connects only to pin 32
on the top layer, and failed the RF group; a GPT-6.1 Sol run kept a 0.18 mm
branch and its ground 0.352 mm from pin 32.

The lab's v20 (`layout-placement-v20.tar.gz`, sha256
`8ea5080231642120d53912c713c3bde592ead2f087ceee333cc608cf999c55bb`, files
matching `skills/snapshots/v20.sha256`; v18 and v19 unchanged) changes:

- SKILL.md: a ground or return the vendor documents for a shunt takes
  precedence over an inline node pad. The ground goes at its documented
  return first, the node pad as close to the line as the courtyards allow,
  the branch is reported, and the ground is never moved off its return to
  make the shunt inline; each documented tie is passed with `--tie`.
- `placement_audit.py`: a shunt on the chain with a `--tie` shows the tie's
  gap, and a tie longer than the part's own courtyard reads `TIE STRETCHED`
  there and in the ties section. Without `--tie` nothing about ties is
  reported.

Ported here unchanged in substance on top of v19's port (so `--rf-track`
stays required). On a synthetic chain the port prints what v20 prints with
the same ties. The lab's tie regression (`v20_rf_tie_regression/`) and its
fresh Opus run of v20 are theirs and not repeated here.

`TIE STRETCHED` is a heuristic: a tie gap longer than the part's own
courtyard. It does not validate the vendor's electrical requirement.

The lab's one fresh Opus 5.5 run of v20 (r21_v20_opus_a, reported in its
`layout-placement-v20.README.md`, sha256
`046d39b688baf1104c462ea0f4bfd4109bd1e557898a64c2b63148abc1b24bba`):

- the targeted defect did not recur: C9 and C11 inline, C6 on a 0.170 mm
  branch with its ground 0.332 mm from pin 32 (the v19 Opus run had 1.332 mm,
  Nordic's reference 0.400 mm);
- the run fails the lab's frozen evaluator overall: the RF group at 1.753,
  only on the last link (L4 ends 1.32 mm short of the port, the spare length
  put into the 50 ohm track), decoupling at 9.99 (C2 and C3 supply pads
  turned away from their pins, the caps at pins 33, 36, 43, 45 and 47 far
  from them; the lab calls this a separate regression in that run, not
  explained by v20), and a soft pass fraction of 0.758 against its 0.85 gate;
- it passes the hard gate, placement DRC with no errors and the v1.5
  routability check (28 of 28 links, 35 of 35 escapes).

It is one run. It shows the tie rule can work, not how often, and not that
v20 places better overall than v19. No RF performance is claimed.

## Changes in this copy

- `SKILL.md`, "Routability": one sentence saying that `route_check.py` and
  `grid_router.py` check a placement and do not route the board, and that in
  Backplane tracks come from `kicad_edit`'s `route` (an agent asked to route
  a board found `grid_router.py` here and routed with it).

Scripts:

- `rules.py` (new): track width, clearance, via diameter and edge clearance
  are the strictest the board applies: every net's effective class from
  KiCad (`GetNetClassForNets`, so assignments, patterns and directives
  count), its differential pair width for nets KiCad pairs, the board
  minimums in the `.kicad_pro`, and pad and footprint clearance overrides.
  Custom DRC rules (`.kicad_dru`) and a missing `.kicad_pro` need all four
  values as flags. A flag looser than the board needs `--rules-override`,
  and the output then says so. v18 had 0.15 / 0.1 / 0.5 / 0.2 mm built in.
  On a board with those rules, `route_check.py` and `placement_audit.py`
  print exactly what v18 printed (tested).
- `sidecar.py` (new) and `move.py --save`: the board's companion metadata
  is kept. bp.4 KiCad reads companion versions 1 and 2 and writes 2: native
  v1 fields go into the board file, other per-item fields become v2
  extension records, and other top-level keys or native fields for no item
  are dropped. `--save` refuses before any change when a save would drop
  part of the companion, refuses to save when the board or the companion
  changed on disk meanwhile, keeps a copy, and after the save checks every
  extension record and property, putting back a dropped record.
- `move.py` refuses to move a footprint with custom properties: bp.4's
  partial footprint update drops them (found by the tests).
- `grid_router.py`: the rules are the `Witness`'s, from `rules.py`. The
  unused `via_site_gap`, which had the built-in rules, is gone.
- `route_check.py`, `placement_audit.py`, `local_search.py`,
  `group_search.py`: the rules flags and `rules.py`; a clear error for a
  part that is not on the board; `route_check.py` states its scope and what
  an escape failing in both orders means.
- `ipc_board.py`: the board must be the one the nearest `.backplane.json`
  names, checked from the path as given and from the file it resolves to
  (`LAYOUT_PLACEMENT_ALTERNATE=1` allows another when the user asked for
  one); exactly one server may have it open, and the connection the script
  then uses is checked again; a `KICAD_API_SOCKET`
  server with another board is refused; Backplane's sockets are looked for
  under `$XDG_RUNTIME_DIR/backplane/kicad` and `<Backplane home>/run/kicad`
  (macOS) as well as `/run/user/<uid>/backplane/kicad`.
- `move.py`: arguments checked before any request, and a reference that
  more than one footprint has is refused; `,B`/`,F` is KiCad's own flip
  (FlipItems, pads and courtyard mirrored to the other side) in its own
  commit, where v18 only changed the footprint's layer field and left its
  pads and courtyard on the old side; KiCad's answer for each part compared
  with the request, and the commit dropped when they differ (in the tests
  KiCad clamped an out-of-range position, which v18 would have committed);
  after the commit, a failed integrity check (footprint count, fixed copper
  nets, poses and pad sides read back) flips and moves the parts back and
  reads the board again, instead of leaving them moved; non-zero exit
  whenever the board was not changed as asked; says whether it saved. v18
  pushed the commit and then only told the agent to undo it, and its count
  check failed on any board with a repeated reference.
- `run.sh` (new), `requirements.in`, `requirements.txt` (new): a private
  Python environment with exact versions and hashes, the versions the lab
  tested (kicad-python 0.8.0, shapely 2.2.0, numpy 2.5.4, protobuf 5.29.6;
  Python 3.12 or newer).

SKILL.md:

- a status paragraph with these limits; a section on the rules and scope
  the checks assume; how to run the scripts and what they refuse;
- "Two cases" had three; it now says three, and long paragraphs are split;
- wording scoped where v18 stated a rule more widely than it holds: the
  switching loop by topology (buck, boost) as the datasheet names it rather
  than "input cap, switch and inductor"; the smallest decoupler closest
  "usually, unless the vendor orders them otherwise"; a via site for ground
  pads that return through a via, and the vendor's ground and layer
  arrangement otherwise; crystal balance preferred when it costs little
  length rather than always; pull-ups anywhere only on slow or static nets;
  no ferrite or other part the schematic does not have;
- what to do when an escape fails in both orders: unresolved, try a
  physical alternative, confirm the rules, and report it, rather than
  calling the board unroutable.

Tests (not part of the skill): `tests/layout-placement/` in KiStack makes
synthetic boards and checks reading, board binding, moves, saving, rollback
and rules against `kicad-cli api-server` processes of its own.
