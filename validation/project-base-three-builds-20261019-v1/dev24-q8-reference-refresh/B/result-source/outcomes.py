def summarize(records, *, include_cancelled=False):
    if not isinstance(records, list):
        raise ValueError("records must be a list")

    passed = 0
    failed = 0
    cancelled = 0

    for record in records:
        if not isinstance(record, dict):
            raise ValueError("record must be a dict")

        if include_cancelled:
            if "cancelled" in record:
                cancelled_flag = record["cancelled"]
                if not isinstance(cancelled_flag, bool):
                    raise ValueError("cancelled must be a bool")
            else:
                cancelled_flag = False
        else:
            cancelled_flag = False

        if "exit_code" not in record:
            raise ValueError("record must contain exit_code")

        exit_code = record["exit_code"]

        if include_cancelled and cancelled_flag:
            if exit_code is not None:
                raise ValueError("cancelled record must have exit_code None")
            cancelled += 1
            continue

        if isinstance(exit_code, bool) or not isinstance(exit_code, int):
            raise ValueError("exit_code must be an int")

        if exit_code == 0:
            passed += 1
        else:
            failed += 1

    if include_cancelled:
        return {"total": len(records), "passed": passed, "failed": failed, "cancelled": cancelled}

    return {"total": len(records), "passed": passed, "failed": failed}

