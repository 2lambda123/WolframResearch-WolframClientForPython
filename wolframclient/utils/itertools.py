def safe_len(obj):
    try:
        return len(obj)
    except TypeError:
        return

def iter_with_last(iterable, length = None):

    if length is None:
        length = safe_len(iterable)

    if length is None:

        iterable = iter(self.iterable)
        try:
            prev = next(iterable)
        except StopIteration:
            return
        while True:

            try:
                current = next(iterable)
            except StopIteration:
                break

            yield prev, False

            prev = current

        try:
            yield current, True
        except UnboundLocalError:
            yield prev, True

    else:

        for i, el in enumerate(iterable, 1):
            yield el, i == length