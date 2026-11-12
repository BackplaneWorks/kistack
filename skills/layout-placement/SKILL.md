---
name: layout-placement
description: Place components on a KiCad board so each part sits where its circuit needs it, placement DRC passes, and every pad stays reachable, with IPC scripts that move parts and measure distances and routability. Covers reading the circuit, fixed parts, IC orientation, and decoupling, regulator, clock, RF and filter parts. Use for component placement; not for routing or schematic design.
---

Run KiCad's CLI as plain `kicad-cli` (in Backplane, the KiCad Backplane has selected, first on your PATH; `$BACKPLANE_KICAD_CLI` is the same program), never by another install's path.

# PCB component placement

Placement decides most of what routing can achieve. A part in the wrong
place makes a track long, a current loop large, or a pad unreachable, and
no routing fixes that later. Good placement gives every connection that
carries fast-changing current a short, direct path, keeps a channel open
for every other connection, and passes placement DRC (courtyards, clearance,
board edge) with zero errors.

This skill is experimental. It was developed against a few small Nordic
QFN benchmark boards and has not been qualified for electrical, RF or
manufacturing sign-off. Its scripts check placement geometry under simple
rules. Where their results and the datasheet or the vendor's reference
layout disagree, follow the datasheet and the reference.

## Save progress to the configured board

Resolve the canonical path from the project root's `.backplane.json` (`project`, or explicit `pcb`). After each meaningful group, save even unfinished placement to that exact file with `SaveDocument` or `--save`; do not leave progress only in the server or a final copy. Read back the saved path and show it with `viewer_show`, then verify the viewer and history refer to that saved file; report any mismatch. Preserve its `<native-filename>.backplane.json` companion. Keep backups/intermediates separate; validate any staging output and promote it back with a backup. The person may be editing the same board or schematic in KiCad while you work, and other agents too: edit through IPC, which reaches the open editor live. Never ask the person to close KiCad, save, revert, stop editing or wait for you, and never rewrite the .kicad_pcb, .kicad_sch, .kicad_pro or .kicad_dru file directly while KiCad has the project open; change design rules by name over IPC (EditCustomRules) and net classes and board setup over IPC, so nobody's rules are overwritten. An update answered ISC_DEFERRED (or a delete IDS_DEFERRED) touches what the person is editing right now: it lands when they finish, merged with their edit; check GetNotices. Alternate files require an explicit experiment request.

## Why parts go where they go

Work from these reasons. The rules in the later sections follow from them.
When a rule and a reason disagree on a particular board, follow the reason.

- **Current flows in loops.** A signal or supply current goes out on one
  conductor and comes back on another, usually ground. The area of that loop
  sets how much it radiates and how much noise it picks up, and its length
  sets its inductance. A decoupling capacitor helps only if the loop from its
  pads to the IC's supply and ground pins is small. In a switching regulator
  one loop carries current that switches in nanoseconds. In a buck it is the
  input capacitor, the switches and their ground return; in a boost it is the
  switch, the rectifier and the output capacitor. The datasheet's layout
  section names it. Short loops matter most where current changes fastest.
- **Some connections tolerate distance and some do not.** A slow GPIO can run
  across the board. A decoupler, a switch node, a crystal pin, an RF node or
  a filter capacitor on a sensitive input cannot. Rank every connection by how
  much length it tolerates before placing anything, and give the space next
  to the pins to the ones that tolerate least.
- **Noisy and sensitive circuits need distance or a barrier.** Switch nodes,
  clocks and digital buses are noisy. Crystals, analog inputs, references and
  RF are sensitive. Keep a noisy node's copper away from a sensitive node's,
  and do not route a sensitive pair past a noisy part.
- **Some things are fixed before you start.** Connectors, buttons, LEDs,
  mounting holes, the antenna and its keep-out, the board outline and parts
  the enclosure dictates. Place these first, from the mechanical
  requirements, and lock them.
- **A placed part must stay reachable.** Every pad needs a way for a track to
  reach it, and every ground pad a place for a via. Pins whose signals leave
  the area need a path out, but an escaping track can bend, change layer or
  take another edge, and a decoupler or crystal pad cannot. So a pad that no
  track can reach is a defect, while a longer escape is a cost to accept.
- **The board must be built and tested.** Courtyards must not overlap. Parts
  on one side cost less to assemble. Polarised parts in the same orientation,
  test points that a probe can reach, and heat-producing parts with copper
  and air around them make the board easier to build, inspect and keep cool.

## 1. Read the circuit before moving anything

From the schematic and netlist, write down each part's job and the pin or
part it serves. Typical jobs:

| Job | What it needs from placement |
|---|---|
| Decoupling cap | at its supply pin, supply pad toward the pin, ground returned the way the vendor shows; usually the smallest value closest, unless the vendor's layout orders them otherwise |
| Bulk cap | near the pins it feeds, in line behind the small cap it backs, supply pad toward that cap so both share one supply track |
| Switching regulator | the fast-switching loop the datasheet names as small as possible (for a buck, the input cap at the VIN and ground pins); switch node short; output cap at the regulated pin or where the datasheet puts it, with the inductor's output pad near it |
| Crystal or resonator | both pads close to their two pins, at nearly equal distance; nothing routed between |
| RF chain (pi or T network) | series parts in schematic order on one axis from the RF pin to the port; leave a gap between series parts where a shunt joins, and put the shunt's node pad on the axis in that gap, the shunt turned across the axis with its ground pad away; the last shunt at the port node; ground as the vendor says |
| Filter or RC on an input | the cap at the pin it filters; a series resistor beside the cap's signal pad, away from the IC |
| Ferrite or link between supplies | only one the schematic has; between the pins or caps of the two domains |
| Connector, button, LED | where the enclosure or user needs it |
| Pull-up, series termination | termination at the driving pin; a pull-up on a slow or static net anywhere on it, unless the datasheet says where |

Use the parts the schematic gives and add none. Do not add a ferrite, a
cap or a via pattern that neither the schematic nor the vendor's reference
has, and keep the ground and layer arrangement the vendor shows. When one
supply net reaches several IC pins and there are enough caps, put one at
each pin, including pins on other sides of the package. When there are fewer caps than pins,
neighbouring pins of the same supply share, and the vendor's grouping says
which. Read the datasheet and any layout notes for constraints such as a
ground pad tied to one IC pin, a via to one layer only, or a length limit, and
treat them as requirements. When the documents leave a choice open, make it,
say that it is your inference, and keep going.

Then find where the pins are on the package. `scripts/run.sh pin_sides.py
<board> <IC>` prints each pin's side and position. The layout of the
schematic sheet says nothing about the board.

## 2. Fix the immovable, then orient the ICs

Place and lock the mechanically fixed parts first. Then choose each large
IC's rotation and position by where its pins must go:

- pins that go to fixed parts (connectors, the RF port, the antenna) face
  them
- pins that leave the area face the edges or connectors they go to
- pins with local parts (supplies, regulator, clock) face room for those parts

Score all four rotations against these and pick the best. Set the distance
to a fixed destination by what goes between. An RF pin sits the length of its
matching chain from the port, a connector's pins the length of their
protection parts from it. When the chain does not fit that distance, move the
IC. Stretching the links between matching parts adds inductance the
matching values did not allow for, and it pulls each shunt and its tied
ground away from the IC pin. If the IC cannot move, keep the matching parts
together and let the length go into the 50 ohm track at the port, then say
so. Leave room on every side for that side's parts and for the tracks
leaving the other pins.

## 3. Place in order of how little distance each connection tolerates

The parts that depend most on a short connection go first, while the space
at the pins is free:

1. Parts whose position the vendor fixes or whose node is a high-frequency
   path: an RF chain, a regulator's power loop, a vendor-tied ground.
2. Decoupling caps and filter caps, each at its own pin, even when that
   means a neighbouring escape needs a bend or a via.
3. Clock parts: crystals and their load caps.
4. Bulk caps, series resistors, ferrites, pull-ups: near what they serve,
   out of the paths above.
5. Everything that tolerates distance.

When a large part and a small cap compete for a spot at a pin, move the
large part. More generally, when a part that needs to be close (decoupler,
filter cap, RF part, output cap) cannot reach its pin, find what holds the
space with `scripts/local_search.py --conflicts` and move the part that
tolerates distance (crystal, bulk cap, series resistor). Do not push the
close part out to make room for one that could sit further away.

When several parts compete for the pins of one region (caps, inductor and
ferrite around a regulator, or two caps at neighbouring pins), place them
together as a group. `scripts/group_search.py` tries the orders and
positions. Give each connection a weight for the distance it tolerates.
`L1:46@1,45@3` means the pad to pin 46 must be short and the pad to pin 45
may be three times longer. Lift parts that sit between two nodes rather
than at a pin, and place them afterwards. The search ranks by distance and blocked
escapes only, so it can put one group member across another's track. Run
`route_check.py` on its result before keeping it.

Cases that go wrong often:

- **Parts at neighbouring pins.** Two parts placed side by side, each in line
  with its pin, fit only if their courtyard widths add up to no more than
  twice the pin pitch. Two 0201s (0.46 mm courtyards) at 0.4 mm pitch do not.
  Plan the pair together. Offset them sideways, move one outward by its
  courtyard length, or swap which pin gets the nearer spot.
- **A regulator whose switch pin and regulated pin are neighbours.** This
  is common in ICs with an integrated DC/DC converter. The inductor joins
  both pins, and the output cap belongs at the regulated pin. An inductor
  laid parallel to the pin row keeps both of its pads near their pins. One
  turned across the row leaves its output pad, and the output cap behind it,
  far from the regulated pin. Compare both with `group_search.py` and keep
  the one whose output cap reaches its pin.
- **An RF matching network (pi or T).** Put the series parts on one
  straight line from the RF pin to the port, and give each shunt its own
  place on that line. Leave a gap between the two series parts where the
  shunt joins, and put its node pad in that gap, turned across the line with
  its ground pad away. The track then runs straight through the node pad. A
  shunt placed beside a series pad needs a short branch track to reach the
  line. At RF (2.4 GHz, for example) that branch adds inductance and
  capacitance the part values did not allow for, and how much depends on its
  length and width. A ground or return path that the vendor documents for
  one shunt (a ground that must go only to one IC pin, or only to one layer)
  takes precedence over an inline node pad. Place that shunt's ground pad at
  its documented return first, then bring its node pad as close to the line
  as the courtyards allow, and report the branch. Do not move the ground
  away from its documented return to make the shunt inline. Nordic's
  nRF54L15 schematic, for example, says one shunt's ground connects only to
  pin 32 on the top layer; its reference keeps that ground next to pin 32
  and accepts a 0.2 mm branch. Pass each documented tie to the audit with
  `--tie`. The gaps make the chain longer than its parts laid end to end,
  so count them before you set the IC's distance from the port. Check every shunt with
  `placement_audit.py --chain ... --rf-track <width>`, giving the width of
  the track that will run through the chain. This checks geometry only; the
  match itself still needs the vendor's tuning or a measurement.
- **A two-pin part across two IC pins** (crystal, flying capacitor). Its two
  gaps should be nearly equal. Rotating it 180 degrees, mirroring which pad
  faces which pin, or sliding it along the IC side usually evens them. On a
  four-pad crystal the two signal pads sit on opposite corners, so each of
  the four rotations puts a different pair of pads toward the IC and gives
  different gaps. Measure both gaps with `placement_audit.py` at all four
  rotations before keeping one. Each pin's track adds stray capacitance to
  its load capacitor, so two equal tracks keep the loads matched and a short
  track with a long one does not. When the balanced choice costs only a
  little length, prefer it. Do not trade much length for balance, because
  every extra millimetre on both pins adds capacitance and pickup. Follow
  the IC vendor's crystal layout where it gives one.

Tracks from a part further out than the row of caps need a corridor through
that row. Leave the gap when you place the caps.

## 4. Keep every pad reachable

For every part you place:

- leave a channel one track wide plus two clearances, from the board's
  rules (0.35 mm for 0.15 mm tracks with 0.1 mm clearance), wherever a
  signal must pass between parts
- keep the area in front of a fine-pitch row free for its escaping tracks
  until they can bend, about 2 mm at 0.4 mm pitch. Do not park a part in front
  of a pin it does not connect to unless that pin's track can leave at 45
  degrees.
- where a ground pad of a decoupler, crystal or shunt returns through a via
  to a ground plane, give it a via site next to it (via diameter plus
  clearance to other-net copper). Where the vendor ties that pad to a
  particular pin, layer or copper instead, follow the vendor and add no via
  the reference does not have
- keep courtyards from overlapping. Touching passes DRC; leave a small gap
  where a track or via must go between.
- place a part in line with its pin (radial) rather than across the row,
  because a radial part leaves both neighbours' straight exits open

Compute positions from pad coordinates, not from a picture. An estimate by
eye is often off by 0.3 mm, which is half the length of an 0201.

## 5. Check, look, fix

After each group of parts, check before going on:

- **Placement DRC.** Save, then run `kicad-cli pcb drc`. Fix every courtyard,
  clearance and edge error. Unconnected items are expected before routing.
- **Distances.** `scripts/placement_audit.py <board> --ic <IC>` measures from
  each IC pin to its parts, so a cap that is near another cap but far from its
  pin shows up. `--chain` checks an ordered chain (RF, filter) link by link,
  `--tie` a vendor-mandated pad-to-pin connection, and for each shunt on the
  chain whether its node pad is inline or how long a branch it needs. Fix,
  worst first: a pin whose part is more than about two body lengths away, a
  part with its ground pad facing the pin, a bulk cap far behind its small
  cap, a ground pad without a via site, a two-pin part with uneven gaps, a
  long chain link, an RF shunt off the path, a blocked pin front.
- **Routability.** `scripts/route_check.py <board> --ic <IC>` routes every
  local connection on the top layer in two orders, then every net that leaves
  the area to the board edge. The local connections must all exist on the
  finished board at once, so at least one order must route every one of
  them; the check prints "all local links together". When it says NO, the
  placement is not finished. Find the link that fails and open its corridor.
  Usually a cap at a neighbouring pin sits in front of the failing pin, and
  shifting it toward its own pin or turning it frees the lane. Escapes are
  different. An escape that fails in one order only can still bend, change
  layer or leave by another edge, so say which order works and go on.
  An escape that fails in both orders is unresolved, not impossible. The
  check is a simple grid router. Try a physical alternative (another edge,
  an earlier via, another rotation, moving the part in its way), confirm the
  rules it printed are the board's, and report the escape as unresolved if
  none of that works.
- **Look.** Render the board and check for chains out of order and parts
  that block pins.

When a short critical connection and an escaping track compete for the same
space, keep the critical part. An escaping track can bend at 45 degrees, take
a via to another layer or leave by another edge; a decoupler, crystal pad, RF
part or switch node has no such alternative. Say which alternative the
escape needs.

Before moving a critical part away from its pin to solve a conflict, try at
least two alternatives (another rotation, the other side of a neighbour,
swapping two parts at adjacent pins, moving the part that holds the space;
`scripts/local_search.py --conflicts` shows which parts hold it), and check
each. Keep the one with the shortest worst gap that still routes. If a side
cannot hold its parts, move or rotate the IC. Report what you could not
satisfy and why.

## What the checks assume

- **Rules.** The checks route and measure with one value each for track
  width, clearance, via diameter and copper-to-edge clearance. Each is the
  strictest the board applies anywhere: every net's class as KiCad resolves
  it, the board minimums in the `.kicad_pro`, and pad and footprint
  clearance overrides. Each script prints the values and what set each one.
  A strict class elsewhere on the board makes the check stricter than a
  given connection needs, so a failure can come from that. Differential
  pairs are routed as single tracks at least the pair width wide; their
  coupling and gap are not checked.
- **What makes a script stop.** A board without a `.kicad_pro`, or with
  custom DRC rules in a `.kicad_dru`, which the checks cannot evaluate,
  needs `--track --clear --via --edge`. A flag stricter than the board is
  fine. A flag looser than the board is refused unless `--rules-override`
  is given, and then the output says the check was looser than the board.
  Use it only when the user asks for that.
- **Scope.** One IC per run: run a check again for each IC. Parts with four
  pads or fewer count as the IC's local parts. Local links are routed on
  F.Cu only, and two copper layers are modelled.
- A result from these checks is a heuristic's answer under these
  assumptions. A pass is not a finished route, and a failure is not proof
  that the board cannot be routed.

## Working with the board

Read and change the board through KiCad's IPC API, never by editing the
`.kicad_pcb` text. In Backplane, open the board once with the `kicad_ipc`
tool (`kiapi.common.commands.OpenDocument`); the scripts then talk to that
KiCad server with kicad-python.

Run every script through `scripts/run.sh`, for example
`scripts/run.sh pin_sides.py <board> U1`. The first run makes the scripts'
own Python environment from `requirements.txt` (exact versions, Python 3.12
or newer) under `~/.cache/kistack/layout-placement`, with uv when it is
installed, else with python3 and pip. It installs nothing elsewhere.

- Always pass the project's configured `.kicad_pcb`, the one Backplane's
  viewer shows. A script refuses a board that the nearest `.backplane.json`
  does not name. Set `LAYOUT_PLACEMENT_ALTERNATE=1` only when the user asked
  for an alternate board.
- A script uses the one KiCad server that has the board open. It stops when
  none has it, when several have it, or when `KICAD_API_SOCKET` names a
  server with another board. It never picks a board by itself.
- `scripts/move.py <board> REF=x,y,rot[,F|B] ... [--save]` moves parts as one
  commit. Without `--save` the change lives in the server only, and the
  checks read the server, so you can try a move, check it and move again.
- `move.py` checks every argument before it asks KiCad anything, takes
  each part once per call, and refuses a reference that two footprints
  share, or a part with custom properties (this KiCad's footprint update
  drops them; move such a part in KiCad itself). `,B` or `,F` flips the part with KiCad's own flip, so its pads and
  courtyard go to that side. If KiCad does not place a part as asked, it
  drops the commit. If the footprint count, the net of any fixed copper, or a
  moved part's position reads back wrong after the commit, it puts the parts
  back and does not save. It exits non-zero whenever the board was not
  changed as asked.
- `--save` writes the board KiCad has open, which the script has checked is
  the configured one, and keeps its `.backplane.json` companion file.
  Before any change it refuses a companion that a save would lose part of
  (an unknown version, other top-level keys, properties for an item the
  board does not have). It also refuses to save when the board or the
  companion changed on disk meanwhile. After the save it checks that every
  extension record and custom property survived, and puts back a record
  the save dropped. A copy of the companion is kept under
  `~/.cache/kistack/layout-placement/backups`.
- `scripts/ipc_board.py` loads pads, courtyards, outline and fixed copper for
  your own checks.
- kicad-cli DRC reads the file, so save first.
- Backplane stops an idle server, and unsaved moves go with it. Save after
  each group of parts. If a script says no server has the board open, open
  it again with `OpenDocument`. Only if that keeps happening, run your own
  server, `kicad-cli api-server --socket <dir>/api.sock <board>`, and set
  `KICAD_API_SOCKET=ipc://<dir>/api.sock`. Never let two servers save the
  same board, and let one agent at a time move parts on it.

Run each script in the foreground and wait for its result.
