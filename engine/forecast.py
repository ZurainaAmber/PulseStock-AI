"""
PulseStock AI - Decision Engine: Hourly Demand Forecasting Module
Cypher 2026 Challenge 6 - Store 7 Stock-out Prevention & Decision Engine

Pure Python module implementing deterministic hourly demand forecasting,
event uplift modeling (Cricket, Rain, Festival), historical baseline extraction,
and configurable multi-hour projection.

Independent of database and FastAPI web framework.
Uses only Python standard library.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Union


class HourlyForecastPoint(dict):
    """
    Representation of a single hourly demand forecast interval.
    Inherits from dict to allow dictionary indexing, JSON serialization,
    and attribute-style access.
    """

    def __init__(
        self,
        timestamp: str,
        hour_label: str,
        baseline_demand_units: Union[int, float],
        cricket_uplift_units: Union[int, float],
        rain_uplift_units: Union[int, float],
        festival_uplift_units: Union[int, float],
        final_projected_demand_units: Union[int, float],
        confidence_lower_bound: int,
        confidence_upper_bound: int,
        applied_multiplier: float = 1.0,
        **kwargs: Any,
    ):
        super().__init__(
            timestamp=timestamp,
            hour_label=hour_label,
            baseline_demand_units=baseline_demand_units,
            cricket_uplift_units=cricket_uplift_units,
            rain_uplift_units=rain_uplift_units,
            festival_uplift_units=festival_uplift_units,
            final_projected_demand_units=final_projected_demand_units,
            confidence_lower_bound=confidence_lower_bound,
            confidence_upper_bound=confidence_upper_bound,
            applied_multiplier=applied_multiplier,
            **kwargs,
        )

    def __getattr__(self, item: str) -> Any:
        try:
            return self[item]
        except KeyError:
            raise AttributeError(f"'HourlyForecastPoint' object has no attribute '{item}'")

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value


def _parse_timestamp(ts: Union[str, datetime]) -> datetime:
    """
    Parse a timestamp string or datetime object into a UTC timezone-aware datetime.

    Convention:
    - String timestamps should be ISO 8601 (e.g. '2026-10-09T18:00:00Z' or '2026-10-09 18:00:00').
    - Naive datetimes are assumed to be UTC.
    - Aware datetimes are normalized to UTC.
    """
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)

    if isinstance(ts, str):
        clean_str = ts.strip()
        if clean_str.endswith("Z"):
            clean_str = clean_str[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(clean_str)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            for fmt in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d",
                "%d-%m-%Y %H:%M:%S",
            ):
                try:
                    parsed = datetime.strptime(clean_str, fmt)
                    return parsed.replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
            raise ValueError(f"Unable to parse timestamp '{ts}'. Expected valid ISO 8601 string or standard format.")

    raise TypeError(f"Timestamp must be str or datetime, got {type(ts).__name__}")


def _format_number(val: Union[int, float]) -> Union[int, float]:
    """Format numeric values as int if whole, or float rounded to 4 decimals."""
    if isinstance(val, (int, float)):
        fval = float(val)
        if fval.is_integer():
            return int(fval)
        return round(fval, 4)
    return val


def validate_forecast_inputs(
    baseline_demand: Optional[Union[Sequence[Union[int, float]], Union[int, float]]] = None,
    uplift: Optional[Union[Sequence[Union[int, float]], Union[int, float]]] = None,
    timestamps: Optional[Sequence[Union[str, datetime]]] = None,
    horizon: Optional[int] = None,
    start_time: Optional[Union[str, datetime]] = None,
) -> bool:
    """
    Validate demand, uplift, timestamps, forecast horizon, and list lengths.

    Validation Rules:
    - Baseline demand must be non-negative (>= 0). Rejects negative demand.
    - Uplift factor must be non-negative (>= 0). Rejects negative uplift.
    - Numeric values cannot be NaN or Infinite.
    - If both baseline demand and uplift are sequences, their lengths must match.
    - If timestamps are provided alongside baseline demand sequence, lengths must match.
    - Forecast horizon must be a strictly positive integer (> 0).
    - Start time, if provided, must be a valid parsable timestamp.

    Raises:
        ValueError: For invalid values, negative inputs, or mismatched sequence lengths.
        TypeError: For unsupported data types.

    Returns:
        bool: True if all provided inputs pass validation.
    """
    # 1. Validate baseline_demand
    if baseline_demand is not None:
        if isinstance(baseline_demand, bool):
            raise TypeError("Baseline demand cannot be a boolean.")

        if isinstance(baseline_demand, (int, float)):
            if math.isnan(baseline_demand) or math.isinf(baseline_demand):
                raise ValueError(f"Baseline demand cannot be NaN or infinite, got: {baseline_demand}")
            if baseline_demand < 0:
                raise ValueError(f"Baseline demand cannot be negative, got: {baseline_demand}")
        elif isinstance(baseline_demand, Sequence) and not isinstance(baseline_demand, (str, bytes)):
            if len(baseline_demand) == 0:
                raise ValueError("Baseline demand sequence cannot be empty.")
            for idx, val in enumerate(baseline_demand):
                if isinstance(val, bool) or not isinstance(val, (int, float)):
                    raise TypeError(f"Baseline demand value at index {idx} must be numeric, got: {type(val).__name__}")
                if math.isnan(val) or math.isinf(val):
                    raise ValueError(f"Baseline demand value at index {idx} cannot be NaN or infinite, got: {val}")
                if val < 0:
                    raise ValueError(f"Baseline demand cannot contain negative values, found {val} at index {idx}")
        else:
            raise TypeError(f"Baseline demand must be a number or sequence of numbers, got: {type(baseline_demand).__name__}")

    # 2. Validate uplift
    if uplift is not None:
        if isinstance(uplift, bool):
            raise TypeError("Uplift cannot be a boolean.")

        if isinstance(uplift, (int, float)):
            if math.isnan(uplift) or math.isinf(uplift):
                raise ValueError(f"Uplift factor cannot be NaN or infinite, got: {uplift}")
            if uplift < 0:
                raise ValueError(f"Uplift factor cannot be negative, got: {uplift}")
        elif isinstance(uplift, Sequence) and not isinstance(uplift, (str, bytes)):
            if len(uplift) == 0:
                raise ValueError("Uplift sequence cannot be empty.")
            for idx, val in enumerate(uplift):
                if isinstance(val, bool) or not isinstance(val, (int, float)):
                    raise TypeError(f"Uplift value at index {idx} must be numeric, got: {type(val).__name__}")
                if math.isnan(val) or math.isinf(val):
                    raise ValueError(f"Uplift value at index {idx} cannot be NaN or infinite, got: {val}")
                if val < 0:
                    raise ValueError(f"Uplift factor cannot be negative, found {val} at index {idx}")
        else:
            raise TypeError(f"Uplift must be a number or sequence of numbers, got: {type(uplift).__name__}")

    # 3. Check sequence length parity between baseline_demand and uplift
    if (
        baseline_demand is not None
        and uplift is not None
        and isinstance(baseline_demand, Sequence)
        and not isinstance(baseline_demand, (str, bytes))
        and isinstance(uplift, Sequence)
        and not isinstance(uplift, (str, bytes))
    ):
        if len(baseline_demand) != len(uplift):
            raise ValueError(
                f"List length mismatch: baseline_demand has length {len(baseline_demand)} "
                f"but uplift has length {len(uplift)}."
            )

    # 4. Validate timestamps
    if timestamps is not None:
        if not isinstance(timestamps, Sequence) or isinstance(timestamps, (str, bytes)):
            raise TypeError(f"Timestamps must be a sequence of timestamps, got: {type(timestamps).__name__}")
        if (
            baseline_demand is not None
            and isinstance(baseline_demand, Sequence)
            and not isinstance(baseline_demand, (str, bytes))
        ):
            if len(timestamps) != len(baseline_demand):
                raise ValueError(
                    f"List length mismatch: timestamps has length {len(timestamps)} "
                    f"but baseline_demand has length {len(baseline_demand)}."
                )
        for idx, ts in enumerate(timestamps):
            try:
                _parse_timestamp(ts)
            except Exception as e:
                raise ValueError(f"Invalid timestamp at index {idx}: {ts} ({e})") from e

    # 5. Validate horizon
    if horizon is not None:
        if isinstance(horizon, bool) or not isinstance(horizon, int):
            raise TypeError(f"Forecast horizon must be an integer, got: {type(horizon).__name__}")
        if horizon <= 0:
            raise ValueError(f"Forecast horizon must be a positive integer (> 0), got: {horizon}")

    # 6. Validate start_time
    if start_time is not None:
        _parse_timestamp(start_time)

    return True


def forecast_hourly_demand(
    baseline_demand: Union[Sequence[Union[int, float]], Union[int, float]],
    uplift: Union[Sequence[Union[int, float]], Union[int, float]] = 1.0,
    cap_multiplier: Optional[float] = None,
) -> Union[List[Union[int, float]], Union[int, float]]:
    """
    Calculate hourly demand using baseline demand multiplied by the applicable event uplift.

    Expected Behavior & Examples:
    - Baseline [3, 3, 3, 3], uplift [1, 1, 1, 1] -> [3, 3, 3, 3]
    - Baseline [3, 3, 3, 3], uplift [1, 1, 3, 3] -> [3, 3, 9, 9]
    - Baseline [2, 4, 3, 5], uplift [1, 1.5, 2, 1] -> [2, 6, 6, 5]

    Rejects negative demand and negative uplift with meaningful ValueError.
    Supports single scalar numbers or matched sequences of hourly values.
    Optional cap_multiplier caps the maximum multiplier applied (e.g. 4.5x).
    """
    validate_forecast_inputs(baseline_demand=baseline_demand, uplift=uplift)

    if cap_multiplier is not None:
        if isinstance(cap_multiplier, bool) or not isinstance(cap_multiplier, (int, float)):
            raise TypeError("cap_multiplier must be a positive numeric value.")
        if cap_multiplier <= 0:
            raise ValueError(f"cap_multiplier must be positive, got: {cap_multiplier}")

    # Case A: Scalar baseline demand
    if isinstance(baseline_demand, (int, float)):
        if isinstance(uplift, (int, float)):
            eff_uplift = min(uplift, cap_multiplier) if cap_multiplier is not None else uplift
            return _format_number(baseline_demand * eff_uplift)
        else:
            results = []
            for u in uplift:
                eff_u = min(u, cap_multiplier) if cap_multiplier is not None else u
                results.append(_format_number(baseline_demand * eff_u))
            return results

    # Case B: Sequence baseline demand
    baseline_list = list(baseline_demand)
    if isinstance(uplift, (int, float)):
        uplift_list = [uplift] * len(baseline_list)
    else:
        uplift_list = list(uplift)

    projected: List[Union[int, float]] = []
    for b, u in zip(baseline_list, uplift_list):
        eff_u = min(u, cap_multiplier) if cap_multiplier is not None else u
        val = b * eff_u
        projected.append(_format_number(val))

    return projected


def calculate_baseline_demand(
    sales_data: Sequence[Any],
    target_hour: Optional[int] = None,
    missing_strategy: str = "ignore",
    default: Optional[Union[int, float]] = None,
) -> Union[int, float]:
    """
    Calculate average hourly demand from historical timestamped sales data,
    handling missing observations correctly.

    Supported Input Formats:
    1. Sequence of numeric values (e.g., [10, 15, 20]).
    2. Sequence of dictionaries with timestamp and sales quantity
       (e.g., [{'timestamp': '2026-10-08T18:00:00Z', 'quantity': 14}, ...]).
       Recognized quantity keys: 'quantity', 'demand', 'units', 'sales', 'qty', 'count'.
    3. Sequence of tuples/lists: (timestamp, quantity).
    4. Objects with .timestamp and .quantity attributes (e.g. SQLAlchemy Order).

    Missing Observation Strategies:
    - 'ignore' (default): Omits None / NaN entries and averages observed values.
    - 'zero': Imputes None / NaN missing hourly observations as 0.0 units.

    Target Hour Filter:
    - If target_hour is provided (0-23), only observations matching that hour of the day
      are averaged.

    Error Handling:
    - Rejects negative quantities.
    - Raises ValueError on insufficient historical data (empty list or all missing).
    """
    if not isinstance(sales_data, Sequence) or isinstance(sales_data, (str, bytes)):
        raise TypeError(f"sales_data must be a sequence of observations, got: {type(sales_data).__name__}")

    if missing_strategy not in ("ignore", "zero"):
        raise ValueError(f"Invalid missing_strategy: '{missing_strategy}'. Must be 'ignore' or 'zero'.")

    if target_hour is not None:
        if isinstance(target_hour, bool) or not isinstance(target_hour, int):
            raise TypeError(f"target_hour must be an integer, got: {type(target_hour).__name__}")
        if not (0 <= target_hour <= 23):
            raise ValueError(f"target_hour must be between 0 and 23, got: {target_hour}")

    if len(sales_data) == 0:
        if default is not None:
            return _format_number(default)
        raise ValueError("Insufficient historical data: sales_data sequence is empty.")

    extracted_values: List[float] = []

    for idx, item in enumerate(sales_data):
        # Case 1: None / Null item
        if item is None:
            if missing_strategy == "zero":
                extracted_values.append(0.0)
            continue

        # Case 2: Pure numeric observation
        if isinstance(item, (int, float)) and not isinstance(item, bool):
            if math.isnan(item):
                if missing_strategy == "zero":
                    extracted_values.append(0.0)
                continue
            if item < 0:
                raise ValueError(f"Historical sales observations cannot contain negative quantities, found: {item}")
            if target_hour is not None:
                # When target_hour is specified, untimestamped numeric data cannot be matched to an hour
                continue
            extracted_values.append(float(item))
            continue

        # Case 3: Dictionary record
        if isinstance(item, dict):
            # Extract quantity
            qty_val = None
            for q_key in ("quantity", "demand", "units", "sales", "qty", "count", "value"):
                if q_key in item:
                    qty_val = item[q_key]
                    break

            if qty_val is None:
                if missing_strategy == "zero":
                    extracted_values.append(0.0)
                continue

            if isinstance(qty_val, bool) or not isinstance(qty_val, (int, float)):
                raise TypeError(f"Record at index {idx} quantity must be numeric, got: {type(qty_val).__name__}")

            if math.isnan(qty_val):
                if missing_strategy == "zero":
                    extracted_values.append(0.0)
                continue

            if qty_val < 0:
                raise ValueError(f"Historical sales observations cannot contain negative quantities, found: {qty_val}")

            # Extract timestamp / hour
            item_hour: Optional[int] = None
            if "hour" in item and isinstance(item["hour"], int):
                item_hour = item["hour"]
            else:
                for t_key in ("timestamp", "time", "date", "created_at", "datetime"):
                    if t_key in item and item[t_key] is not None:
                        try:
                            parsed_dt = _parse_timestamp(item[t_key])
                            item_hour = parsed_dt.hour
                            break
                        except Exception:
                            pass

            if target_hour is not None:
                if item_hour is None or item_hour != target_hour:
                    continue

            extracted_values.append(float(qty_val))
            continue

        # Case 4: Tuple or List (timestamp, quantity)
        if isinstance(item, (tuple, list)) and len(item) >= 2:
            ts_raw, qty_val = item[0], item[1]
            if qty_val is None:
                if missing_strategy == "zero":
                    extracted_values.append(0.0)
                continue

            if isinstance(qty_val, bool) or not isinstance(qty_val, (int, float)):
                raise TypeError(f"Record at index {idx} quantity must be numeric, got: {type(qty_val).__name__}")

            if math.isnan(qty_val):
                if missing_strategy == "zero":
                    extracted_values.append(0.0)
                continue

            if qty_val < 0:
                raise ValueError(f"Historical sales observations cannot contain negative quantities, found: {qty_val}")

            item_hour = None
            if ts_raw is not None:
                try:
                    item_hour = _parse_timestamp(ts_raw).hour
                except Exception:
                    pass

            if target_hour is not None:
                if item_hour is None or item_hour != target_hour:
                    continue

            extracted_values.append(float(qty_val))
            continue

        # Case 5: Object with attributes (e.g. SQLAlchemy model)
        if hasattr(item, "quantity"):
            qty_val = getattr(item, "quantity")
            if qty_val is None:
                if missing_strategy == "zero":
                    extracted_values.append(0.0)
                continue
            if qty_val < 0:
                raise ValueError(f"Historical sales observations cannot contain negative quantities, found: {qty_val}")

            item_hour = None
            if hasattr(item, "timestamp") and getattr(item, "timestamp") is not None:
                try:
                    item_hour = _parse_timestamp(getattr(item, "timestamp")).hour
                except Exception:
                    pass

            if target_hour is not None:
                if item_hour is None or item_hour != target_hour:
                    continue

            extracted_values.append(float(qty_val))
            continue

        raise TypeError(f"Unsupported observation format at index {idx}: {type(item).__name__}")

    if len(extracted_values) == 0:
        if default is not None:
            return _format_number(default)
        if target_hour is not None:
            raise ValueError(f"Insufficient historical data: no valid observations found for target hour {target_hour}.")
        raise ValueError("Insufficient historical data: no valid non-null observations found.")

    avg = sum(extracted_values) / len(extracted_values)
    return _format_number(avg)


def build_hourly_forecast(
    start_time: Union[str, datetime],
    horizon_hours: int = 12,
    baseline_demand: Union[Sequence[Union[int, float]], Union[int, float]] = 10,
    events: Optional[Sequence[Dict[str, Any]]] = None,
    cap_multiplier: Optional[float] = 4.5,
    confidence_interval_pct: float = 0.10,
) -> List[HourlyForecastPoint]:
    """
    Produce a timestamped hourly demand forecast for a configurable number of future hours.

    Event Handling Convention:
    - Time Boundaries: Half-open interval [start_time, end_time).
      An event is active for a forecast hour [hour_start, hour_end) if the event window
      overlaps the forecast hour: max(hour_start, event_start) < min(hour_end, event_end).
    - Time Zones: Normalized to UTC. ISO 8601 strings output with 'Z' suffix.
    - Multiplicative Combination:
      Total Multiplier = Product of active event multipliers (capped at cap_multiplier, default 4.5x).
    - Uplift Attribution:
      Uplift units are decomposed into cricket, rain, festival, and other categories based
      on each active event's relative contribution.
    - Confidence Intervals:
      lower_bound = max(0, round(final_projected * (1.0 - confidence_interval_pct)))
      upper_bound = round(final_projected * (1.0 + confidence_interval_pct))

    Returns:
        List[HourlyForecastPoint]: Sequence of structured forecast intervals.
    """
    validate_forecast_inputs(horizon=horizon_hours, start_time=start_time)

    if isinstance(baseline_demand, Sequence) and not isinstance(baseline_demand, (str, bytes)):
        validate_forecast_inputs(baseline_demand=baseline_demand)
        if len(baseline_demand) != horizon_hours:
            raise ValueError(
                f"Baseline demand list length ({len(baseline_demand)}) does not match horizon_hours ({horizon_hours})."
            )
        baseline_sequence = list(baseline_demand)
    else:
        validate_forecast_inputs(baseline_demand=baseline_demand)
        baseline_sequence = [baseline_demand] * horizon_hours

    if cap_multiplier is not None:
        if isinstance(cap_multiplier, bool) or not isinstance(cap_multiplier, (int, float)):
            raise TypeError("cap_multiplier must be a positive number.")
        if cap_multiplier <= 0:
            raise ValueError(f"cap_multiplier must be positive, got: {cap_multiplier}")

    if not isinstance(confidence_interval_pct, (int, float)) or isinstance(confidence_interval_pct, bool):
        raise TypeError("confidence_interval_pct must be a float between 0.0 and 1.0.")
    if not (0.0 <= confidence_interval_pct <= 1.0):
        raise ValueError(f"confidence_interval_pct must be between 0.0 and 1.0, got: {confidence_interval_pct}")

    # Standardize start_dt to UTC top of the hour
    start_dt = _parse_timestamp(start_time)
    start_dt = start_dt.replace(minute=0, second=0, microsecond=0)

    # Parse and validate events
    parsed_events: List[Dict[str, Any]] = []
    if events is not None:
        if not isinstance(events, Sequence) or isinstance(events, (str, bytes)):
            raise TypeError(f"events must be a sequence of event dictionaries, got: {type(events).__name__}")
        for idx, ev in enumerate(events):
            if not isinstance(ev, dict):
                raise TypeError(f"Event at index {idx} must be a dictionary, got: {type(ev).__name__}")

            ev_start_raw = ev.get("start_time")
            ev_end_raw = ev.get("end_time")

            if ev_start_raw is None or ev_end_raw is None:
                raise ValueError(f"Event at index {idx} must provide both 'start_time' and 'end_time'.")

            ev_start = _parse_timestamp(ev_start_raw)
            ev_end = _parse_timestamp(ev_end_raw)

            if ev_end <= ev_start:
                raise ValueError(
                    f"Event at index {idx} end_time ({ev_end.isoformat()}) "
                    f"must be strictly after start_time ({ev_start.isoformat()})."
                )

            ev_multiplier = ev.get("multiplier", 1.0)
            if isinstance(ev_multiplier, bool) or not isinstance(ev_multiplier, (int, float)):
                raise TypeError(f"Event multiplier at index {idx} must be numeric, got: {type(ev_multiplier).__name__}")
            if ev_multiplier < 0:
                raise ValueError(f"Event multiplier cannot be negative, got: {ev_multiplier}")

            ev_type = str(ev.get("event_type", "GENERIC")).upper()
            ev_name = str(ev.get("name", ev_type))

            parsed_events.append({
                "name": ev_name,
                "event_type": ev_type,
                "multiplier": float(ev_multiplier),
                "start": ev_start,
                "end": ev_end,
            })

    forecast_intervals: List[HourlyForecastPoint] = []

    for h in range(horizon_hours):
        hour_start = start_dt + timedelta(hours=h)
        hour_end = hour_start + timedelta(hours=1)
        hour_label = f"{hour_start.strftime('%H:00')} - {hour_end.strftime('%H:00')}"
        b_demand = baseline_sequence[h]

        # Determine events active during this hour window [hour_start, hour_end)
        cricket_mult = 1.0
        rain_mult = 1.0
        festival_mult = 1.0
        other_mult = 1.0

        for ev in parsed_events:
            # Overlap check: max(hour_start, ev["start"]) < min(hour_end, ev["end"])
            if hour_start < ev["end"] and hour_end > ev["start"]:
                etype = ev["event_type"]
                if "CRICKET" in etype:
                    cricket_mult *= ev["multiplier"]
                elif "RAIN" in etype or "WEATHER" in etype:
                    rain_mult *= ev["multiplier"]
                elif "FESTIVAL" in etype:
                    festival_mult *= ev["multiplier"]
                else:
                    other_mult *= ev["multiplier"]

        combined_multiplier = cricket_mult * rain_mult * festival_mult * other_mult

        if cap_multiplier is not None:
            effective_multiplier = min(combined_multiplier, cap_multiplier)
        else:
            effective_multiplier = combined_multiplier

        final_projected = b_demand * effective_multiplier
        total_uplift = max(0.0, final_projected - b_demand)

        # Decompose total uplift into categories proportionally
        cricket_inc = max(0.0, cricket_mult - 1.0)
        rain_inc = max(0.0, rain_mult - 1.0)
        fest_inc = max(0.0, festival_mult - 1.0)
        other_inc = max(0.0, other_mult - 1.0)
        sum_inc = cricket_inc + rain_inc + fest_inc + other_inc

        if sum_inc > 0 and total_uplift > 0:
            cricket_uplift = total_uplift * (cricket_inc / sum_inc)
            rain_uplift = total_uplift * (rain_inc / sum_inc)
            fest_uplift = total_uplift * (fest_inc / sum_inc)
        else:
            cricket_uplift = 0.0
            rain_uplift = 0.0
            fest_uplift = 0.0

        # Confidence bounds (rounded integers, floor at 0)
        lower_bound = max(0, round(final_projected * (1.0 - confidence_interval_pct)))
        upper_bound = round(final_projected * (1.0 + confidence_interval_pct))

        point = HourlyForecastPoint(
            timestamp=hour_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            hour_label=hour_label,
            baseline_demand_units=_format_number(b_demand),
            cricket_uplift_units=_format_number(cricket_uplift),
            rain_uplift_units=_format_number(rain_uplift),
            festival_uplift_units=_format_number(fest_uplift),
            final_projected_demand_units=_format_number(final_projected),
            confidence_lower_bound=int(lower_bound),
            confidence_upper_bound=int(upper_bound),
            applied_multiplier=round(effective_multiplier, 3),
        )
        forecast_intervals.append(point)

    return forecast_intervals
