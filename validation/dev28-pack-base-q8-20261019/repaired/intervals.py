def merge_intervals(intervals):
    normalized = []
    for interval in intervals:
        start, end = interval
        if start > end:
            raise ValueError("interval bounds are reversed")
        normalized.append((start, end))

    if not normalized:
        return []

    normalized.sort()
    merged = [normalized[0]]
    for start, end in normalized[1:]:
        current_start, current_end = merged[-1]
        if start <= current_end:
            if end > current_end:
                merged[-1] = (current_start, end)
        else:
            merged.append((start, end))
    return merged
