"""Range calibration: turn a phone GPS track + station detections into
distance/RSSI samples, a fitted propagation model, and a coverage raster.

The field workflow this serves: a person carries a test tag away from a
station while their phone posts timestamped GPS points. The station hears
(or misses) the tag and reports detections through the normal event path.
Nothing here talks to hardware — it is pure geometry and statistics over
two timestamped series, so it is all unit-testable.

Correlation is by timestamp: a detection's position is interpolated from
the bracketing track points. Both clocks are NTP-backed (phone and Pi),
and MAX_GAP_S absorbs the residual skew plus the Pi's batching delay
(event_timestamp is stamped on the Pi at detection time, not at delivery,
so late batches still correlate correctly).
"""
import math
from typing import Dict, List, Optional, Tuple
MAX_GAP_S = 20
MAX_DWELL_STEP_S = 15
EARTH_RADIUS_M = 6371000.0

def _wrap_dlon(dlon: float) -> float:
    """Shortest signed longitude difference, antimeridian-safe.

    Identity for any |dlon| < 180 — i.e. for every real walk — but keeps a
    station sited within metres of ±180° from producing 20,000 km cells.
    """
    ...

def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres."""
    ...

def initial_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Bearing from point 1 to point 2, degrees clockwise from true north."""
    ...

def interpolate_position(track: List[Dict], ts: float, max_gap_s: float=MAX_GAP_S) -> Optional[Tuple[float, float]]:
    """Phone position at time ts, from a track sorted ascending by 't'.

    Linear interpolation between the bracketing points when both are within
    max_gap_s; nearest endpoint when ts falls just off either end. None when
    the track has no point close enough in time.
    """
    ...

def correlate_detections(track: List[Dict], detections: List[Dict], station_lat: float, station_lon: float, max_gap_s: float=MAX_GAP_S) -> List[Dict]:
    """Place each detection on the ground and measure its distance.

    track: [{'t', 'lat', 'lon'}, ...] sorted ascending by 't'
    detections: [{'timestamp', 'signal_db', 'confidence', 'frequency_khz'}, ...]

    Returns samples: detections that could be positioned, each with
    lat/lon/distance_m/bearing_deg added. Unplaceable detections are dropped —
    a sample with an invented position would poison the fit and the raster.
    """
    ...

def fit_path_loss(samples: List[Dict], min_distance_m: float=1.0) -> Optional[Dict]:
    """Least-squares fit of the log-distance path-loss model.

    RSSI(d) = A - 10 * n * log10(d)   with d in metres, A = RSSI at 1 m.

    Needs enough samples spread over enough distance to mean anything: at
    least 5 usable points spanning a factor of 2 in distance. Below that the
    slope is noise and we return None rather than a confident-looking lie.
    """
    ...

def predicted_range_m(fit: Dict, threshold_db: float) -> Optional[float]:
    """Distance at which the fitted RSSI falls to threshold_db.

    Only meaningful when signal actually decays with distance (n > 0); a
    flat or inverted fit — all samples at similar range, or multipath noise
    dominating — yields no usable prediction.
    """
    ...

def build_raster(track: List[Dict], samples: List[Dict], station_lat: float, station_lon: float, cell_m: float=25.0, pulse_rate_ppm: Optional[float]=None) -> Dict:
    """Grid the walked area into cells and score each one.

    Every cell the walker spent time in gets dwell seconds; every positioned
    detection lands in a cell. A cell with dwell but no detections is the
    valuable negative result — you stood there and the station heard nothing.

    detection_rate is detections / expected pulses (needs the tag's pulse
    rate); without it, det_per_min still orders cells by how well they hear.
    """
    ...

def summarize(track: List[Dict], samples: List[Dict], fit: Optional[Dict]) -> Dict:
    """Headline numbers for the results view."""
    ...

def distance_bands(cells: List[Dict], band_m: float=50.0) -> List[Dict]:
    """Aggregate raster cells into concentric distance bands from the station.

    Bands pool the dwell and detections of every cell whose centre falls in
    [k*band_m, (k+1)*band_m); rate math mirrors the per-cell version —
    absolute heard/expected when expected_pulses is present, detections/min
    always.
    """
    ...

def reliable_range_m(cells: List[Dict], band_m: float=50.0, min_dwell_s: float=15.0) -> Optional[float]:
    """How far out detection still WORKS, as one number.

    predicted_range_m says where the fitted signal crosses the weakest level
    ever detected — an extrapolation. This is the empirical counterpart: walk
    outward band by band, and the reliable range is the edge of the last band
    that still heard the tag properly before the first band that didn't.

    "Properly" is judged against the walk's own best band, not against the
    tag's pulse rate: a station does not report every pulse (validation,
    event batching, and lock rate-limiting all thin the stream), so absolute
    heard/expected math fails walks that plainly worked. A band qualifies
    while its detections-per-minute holds at least half the best rate seen
    anywhere on this walk (and at least one a minute). Bands with under
    min_dwell_s of dwell are skipped rather than failed — passing through in
    two seconds proves nothing either way — and the first well-sampled band
    that fails ends the scan, so a lucky pulse beyond a dead zone can't
    stretch the answer.
    """
    ...
