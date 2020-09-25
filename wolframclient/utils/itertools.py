def safe_len(obj):
    try:
        return len(obj)
    except TypeError:
        return

def enumerate_with_last(iterable, length = None):

    if length is None:
        length = safe_len(iterable)

    if length is None:
        i = 0
        iterable = iter(iterable)
        try:
            prev = next(iterable)
        except StopIteration:
            return
        while True:

            try:
                current = next(iterable)
            except StopIteration:
                break

            yield prev, i, False

            prev = current

            i += 1

        try:
            yield current, i , True
        except UnboundLocalError:
            yield prev, i , True

    else:

        for i, el in enumerate(iterable):
            yield el, i, i == (length-1)