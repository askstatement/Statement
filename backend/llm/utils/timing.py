import time


def startTiming() -> float:
    """Return a monotonic start timestamp."""
    return time.perf_counter()


def endTiming(t0: float, unit: str = "s", decimals: int = 3) -> float:
    """
    Return elapsed time since t0.
    unit: "s" (seconds), "ms" (milliseconds), "us" (microseconds), "ns" (nanoseconds), "min" (minutes)
    """
    dt = time.perf_counter() - t0
    if unit == "s":
        val = dt
    elif unit == "ms":
        val = dt * 1_000
    elif unit == "us":
        val = dt * 1_000_000
    elif unit == "ns":
        val = dt * 1_000_000_000
    elif unit == "min":
        val = dt / 60.0
    else:
        raise ValueError("unit must be one of: s, ms, us, ns, min")
    return round(val, decimals)
