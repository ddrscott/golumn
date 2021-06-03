
def detect_columns(rows):
    if rows is None or len(rows) == 0:
        return []
    result = list()
    for i, h in enumerate(rows[0]):
        cells = [r[i] for r in rows if len(r) > i]
        if are_ints(cells):
            result.append('integer')
        elif are_floats(cells):
            result.append('numeric')
        else:
            result.append('text')
    return result


def are_floats(items):
    """
    detect if all items are floats
    """
    for i in items:
        try:
            float(i) if i is not None and len(i) > 0 else None
        except ValueError:
            return False
    return True


def are_ints(items):
    """
    detect if all items are ints
    """
    for i in items:
        try:
            int(i) if i is not None and len(i) > 0 else None
        except ValueError:
            return False
    return True
