---
id: B-1
type: Bug
title: "Browser test flaky: Chrome does not write its DevTools port in time"
status: erledigt
milestone: M-1
tags: [tests, browser, ci, flaky]
created: 2026-09-23
---

# Chrome does not write its DevTools port in time

## Repro

Seen on GitHub runners four times: 2026-09-23 (PR #17, `tests (3.14)`), 2026-11-13 (PR #129, `tests (3.13)`),
2026-11-21 (PR #144, `tests (3.15)`, run 44894366057), plus the same pattern in two other repos with the same driver.
A rerun of the same commit was green each time, so not the code.

Deterministic repro (2026-11-21): the CI image in a container, Chrome's files dropped from the page cache
(`posix_fadvise(POSIX_FADV_DONTNEED)` on the install directory and the libraries `ldd` lists), the disk throttled to
30 read IOPS (`docker run --device-read-iops <disk>:30`), then `python3 tests/test_browser.py`.

## Expected vs. actual

**Expected:** Chrome writes `DevToolsActivePort` within 0.2 s (1.3 s under full CPU load), far inside the 30 s.

**Actual:** Chrome is still running after 30 s and has written no port. stderr holds only
`ERROR:dbus/bus.cc … Failed to connect to the bus: Could not parse server address: Unknown address type`,
spread over 11 s, no `DevTools listening`.

## Cause

A cold disk, not D-Bus and not CPU:

- The test ran the runner image's **preinstalled** `google-chrome`, not the Chrome that `setup-chrome` had just
  unpacked: `find_chrome()` looks up `google-chrome` before `chrome`. Nothing on a fresh runner had read those ~400 MB
  yet, and the first reads from the image disk are slow. Chrome faults its 300 MB binary in page by page.
- In another repo with the same driver the new state dump showed it directly: Chrome's main process in **state D,
  `wchan=folio_wait_bit_common`** (waiting for a page to come in from disk), load 1.25, 15 GB free.
- The D-Bus lines are noise. Chrome writes the same eight lines from two threads in **every** start when no session bus
  is set (`DBUS_SESSION_BUS_ADDRESS` unset, as on a runner); locally they all come within 20 ms, right before
  `DevTools listening`. `dbus/bus.cc` (`Bus::Connect`) fails at once on an unparsable address, it does not wait. In
  the CI run the same eight lines took 11 s: the whole process was slow, not stuck in one call.
- Repro above: without the fix no port within 30 s, process `läuft noch`, stderr empty.

## Fix (2026-11-21)

- CI passes `CHROME=<setup-chrome's chrome-path>` (`ci.yml`, `release.yml`); `find_chrome()` honours `CHROME` first and
  fails loudly on a wrong path.
- `prewarm_chrome()` reads Chrome's files (binary, its siblings, linked libraries) once before the timed start, and
  the test prints how long that took. The 30 s stay the measure for a hung Chrome; the disk's time is shown, not
  hidden in it.
- The abort message now adds load, free memory, and state plus `wchan` of every Chrome process and of the main
  process's threads, so a different cause would show itself.
- Self-checks: the read covers the executed binary (not only the wrapper script), and the abort names process state.
- Mutation: without `prewarm_chrome()` the repro is red again.

## Done when

- A failed Chrome start names its cause in the test output. ☑
- The repro is green with the fix and red without. ☑
- Two consecutive full runs of `scripts/check.sh` are green. ☑
