from __future__ import absolute_import, print_function, unicode_literals

from wolframclient.utils.api import pyarrow
from wolframclient.utils.dispatch import Dispatch

encoder = Dispatch()


@encoder.dispatch(pyarrow.Table)
def encoder_pyarrow_table(serializer, o):
    sink = pyarrow.BufferOutputStream()
    batch = o.to_batches()[0]
    strm = pyarrow.ipc.new_stream(sink, o.schema)
    strm.write_batch(batch)
    buf = sink.getvalue()
    return serializer.serialize_function(
        serializer.serialize_symbol(b"ImportByteArray"),
        (serializer.serialize_bytes(buf), serializer.serialize_string("ArrowIPC")),
    )
