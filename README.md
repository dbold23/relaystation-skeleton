# RelayStation

Unattended VHF wildlife tag detection on a Raspberry Pi and a software-defined radio,
with a central server for the fleet.

> **Skeleton of an ongoing project.** This is the real module layout, signatures and
> docstrings of the station and its server, with every function body replaced by `...`
> and all keys, station configs and field data left out. It does not run, but the
> docstrings and the outline below are enough to build your own station. You are welcome
> to; please credit Daniel Sambold if you do.

## Collaborate

I am looking for collaborators. What needs work:

- **Outdoor range walk.** The roughly 30 dB gain is on a synthetic-noise bench; it has not been turned into distance in the field yet.
- **Real noise captures** from other sites, to test the self-calibrating gates against heavier-tailed noise.
- **Field partners** running VHF tags who want an unattended receiver, and help with antennas and enclosures.

<p>
  <a href="https://github.com/dbold23/relaystation-skeleton/issues/new?template=1-collaborate.yml"><img alt="Propose a collaboration" src="https://img.shields.io/badge/Propose%20a%20collaboration-0b1f33?style=for-the-badge&labelColor=2bb3a9&color=2bb3a9"></a>
  <a href="https://github.com/dbold23/relaystation-skeleton/issues/new?template=2-beta-tester.yml"><img alt="Become a beta tester" src="https://img.shields.io/badge/Become%20a%20beta%20tester-0b1f33?style=for-the-badge&labelColor=f2a93b&color=f2a93b"></a>
  <a href="https://github.com/dbold23/relaystation-skeleton/issues/new?template=3-share-data.yml"><img alt="Share data or a site" src="https://img.shields.io/badge/Share%20data%20or%20a%20site-0b1f33?style=for-the-badge&labelColor=2bb3a9&color=2bb3a9"></a>
</p>

<sub>Each button opens a short form. Anything you would rather not post in public: <a href="https://www.linkedin.com/in/daniel-sambold-620b37221">LinkedIn</a>.</sub>

![Detection chain](docs/detection-chain.svg)

Radio tags on animals beep for about 19 ms every 1.7 s near 151 MHz. A station reads
128 ms of IQ at a time, surveys every channel, runs a per-tag matched filter, folds the
statistic at the beacon period to find tags too weak for a single pulse, and validates
the pulse train before it reports. Stations report over WiFi or NB-IoT cellular, queue
offline, and update themselves over the air with staging, verification and rollback.

![Sensitivity on the bench](docs/sensitivity.svg)

On a synthetic-noise bench the rebuilt chain first validates a tag about 30 dB fainter
than the old Welch detector. Real sites have heavier-tailed noise than the bench, which
is why the gates calibrate themselves from each station's own data, and the outdoor
range walk that turns this into distance has not been redone.

## Built to fail loudly

Every channel-frame lands in exactly one pipeline stage and the counts ride the
heartbeat, so a station that is running but deaf shows up on the dashboard instead of
looking healthy. The clock steps from the server when there is no NTP, the modem has a
recovery ladder, and the watchdog keeps a persistent blackout clock.

## Build your own

1. **Hardware.** A Raspberry Pi, an RTL-SDR tuned near your tag band, an antenna,
   and optionally an NB-IoT HAT for sites with no WiFi.
2. **Survey.** Read short IQ blocks, take a spectrogram, slide a pulse-length mean
   along time in every bin, and normalise each bin by its own learnt level so spurs
   divide out (`station/core/survey_dsp.py`).
3. **Gate from your own noise.** Fit the detection threshold from the station's pooled
   noise maxima at a chosen false-alarm rate, not from a fixed dB number.
4. **Matched filter and fold.** For each known tag, decimate around its carrier, run a
   pulse-length matched filter, and fold the statistic at the beacon period to pull out
   tags too weak for one pulse (`station/core/mf_frontend.py`).
5. **Validate the train.** Accept a tag only after a run of pulses at the right interval
   (`station/core/pattern_validator.py`).
6. **Report so deafness shows.** Count every channel-frame into one pipeline stage and
   send the counts with the heartbeat (`central/server/`).

## Layout

| Part | What it holds |
|---|---|
| `station/core/` | Survey DSP, CFAR gate, matched filter, period fold, pattern validator |
| `station/comms/` | Central client, offline queue, SIM7028 NB-IoT HTTP transport, clock sync |
| `station/health/`, `station/monitoring/` | Watchdog, modem recovery, telemetry |
| `central/server/` | FastAPI API, SQLite schema, alerts, diagnostics, range calibration |

```
station/
    comms/
    core/
    health/
    monitoring/
central/
    server/
```
