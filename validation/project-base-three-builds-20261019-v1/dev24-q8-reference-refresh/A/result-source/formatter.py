from outcomes import summarize

def render_summary(records):
    summary = summarize(records)
    return f"{summary['total']} runs: {summary['passed']} passed, {summary['failed']} failed"
