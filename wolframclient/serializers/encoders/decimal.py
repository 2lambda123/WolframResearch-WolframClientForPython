from __future__ import absolute_import, print_function, unicode_literals

import decimal

from wolframclient.utils.dispatch import Dispatch

encoder = Dispatch()


@encoder.dispatch(decimal.Decimal)
def encode_decimal(serializer, o):
    return serializer.serialize_decimal(o)
