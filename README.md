# SIB-200 functional test — TofuPilot workshop

Example test procedure for the Swiss Hardware Testing Day 2026 workshop: the
end-of-line functional test of the SIB-200 board, written as a [TofuPilot]
procedure. No real board or instrument is needed — the whole bench is simulated.

## Quick start: test a board in the browser

You only need the [TofuPilot] CLI. Open a terminal in this folder and run:

```bash
tofupilot run . --upload --ui browser
```

The browser opens the operator screen. Enter a serial number and your name
(any serial works — the boards are simulated), confirm the board is in the
fixture, and watch the five steps run. At the end you see every measurement
against its limit: green PASS or red FAIL.

`--upload` records the run in your TofuPilot dashboard (needs `tofupilot login`
once). Without it, the run stays on this machine.

Expect a FAIL about one time in ten: the simulation gives some boards a weak
3.3 V regulator. That is on purpose. Just run again with a new serial number.

## The test

The SIB-200 is powered with 24 V and has three parts we check: the voltage
regulator (24 V → 3.3 V), the microcontroller (firmware must be version 2.1.0)
and the temperature sensor the MCU reads. After the operator places the board
and confirms, five steps run:

| # | Step | What is checked | Limit |
|---|------|-----------------|-------|
| 1 | Power on | Idle current at 24 V | ≤ 80 mA |
| 2 | 3.3 V rail | Regulator output, measured with the DMM | 3.2 – 3.32 V |
| 3 | Flash firmware | Firmware version read back from the MCU | == 2.1.0 |
| 4 | Read sensor | Temperature reading makes sense for a room | 15 – 35 °C |
| 5 | Temperature log | 2 s recording is stable (min/max aggregation) | 15 – 35 °C |

Steps 5 and 6 (temperature log, LED check) are commented out in
`procedure.yaml` — they are the workshop exercises, see below.

## How it is built

```
procedure.yaml     the test: board, instruments, steps, limits, operator UI
phases/sib200.py   one Python function per step — measures only, never judges
plugs/bench.py     the instruments as plain classes (simulated power supply,
                   multimeter, programmer, I2C sensor)
images/            pictures shown to the operator (pcb, LED colours)
tofupilot.json     links this folder to its dashboard procedure
```

The split is deliberate: the Python only measures, the validators in
`procedure.yaml` decide PASS or FAIL. Change a limit without touching code.
If you come from TestStand: a phase is a Step, `measurements.x = ...` fills a
Numeric Limit Test, and the limits sit in the YAML next to the step.

## Other ways to run

```bash
tofupilot run .                         # run on this machine only
tofupilot run . --ui kiosk              # full-screen kiosk (station setups)
tofupilot run . --ui headless           # print the UI URL only (CI, SSH)
tofupilot run . --no-ui                 # no operator UI at all
```

The operator UI is served locally on `127.0.0.1:7321` (a free port if that one
is taken; override with `TOFUPILOT_LOCAL_UI_PORT`). Without a flag, a plain
terminal run is headless: the URL is printed, nothing opens. Use `--tui` for
the terminal UI instead. `tofupilot validate` checks the YAML and Python
without running.

## Reports

There is no separate report format — the recorded run *is* the report:

- `tofupilot run . --json > run.jsonl` writes the NDJSON event stream
  (phase lifecycle, measurements, run outcome) to a file.
- With `--upload`, the full run (phases, measurements vs. limits, logs,
  attachments) appears under **Runs** in the dashboard. A failed upload goes
  to the local queue (`tofupilot queue`) and retries.
- Fetched back with `tofupilot runs get --id <run_id> --json`.

## Workshop exercises

Two phases ship switched off. To switch one on, remove the leading `# ` from
every line of its block in `procedure.yaml` (in VS Code: select the lines,
then Ctrl+/ — macOS Cmd+/). Keep the indentation.

1. **Temperature log** (`temperature_log`): records 100 readings over 2 s into
   a curve with min/max aggregations. The Python is already written in
   `phases/sib200.py`; only the YAML block needs uncommenting.
2. **LED check** (`led_check`): the operator picks the LED colour from two
   pictures; the answer is bound to a measurement and judged by its limit —
   green PASS, red FAIL. Needs the temperature log switched on first
   (`depends_on`).

[TofuPilot]: https://www.tofupilot.com