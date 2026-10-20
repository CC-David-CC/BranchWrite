from outcomes import summarize

def render_summary(records, *, include_cancelled=False):
    summary = summarize(records, include_cancelled=include_cancelled)

    if include_cancelled:
        return (
            f"{summary['total']} runs: "
            f"{summary['passed']} passed, "
            f"{summary['failed']} failed, "
            f"{summary['cancelled']} cancelled"
        )

    return f"{summary['total']} runs: {summary['passed']} passed, {summary['failed']} failed"

