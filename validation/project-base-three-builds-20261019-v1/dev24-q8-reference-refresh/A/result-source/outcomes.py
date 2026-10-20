def summarize(records):
    if not isinstance(records, list):
        raise ValueError("records must be a list")

    passed = 0
    failed = 0
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("record must be a dict")
        if "exit_code" not in record:
            raise ValueError("record must contain exit_code")

        exit_code = record["exit_code"]
        if isinstance(exit_code, bool) or not isinstance(exit_code, int):
            raise ValueError("exit_code must be an int")

        if exit_code == 0:
            passed += 1
        else:
            failed += 1

    return {"total": len(records), "passed": passed, "failed": failed}
