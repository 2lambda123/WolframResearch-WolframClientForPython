from __future__ import absolute_import, print_function, unicode_literals

import struct

from wolframclient.utils import six
from wolframclient.utils.datastructures import Settings
from functools import partial
if six.JYTHON:
    pass

if six.PY2:

    def _bytes(value):
        return chr(value)


else:

    def _bytes(value):
        return bytes((value,))


WXF_VERSION = b"8"
WXF_HEADER_SEPARATOR = b":"
WXF_HEADER_COMPRESS = b"C"

# The list of all the WXF tokens.
WXF_CONSTANTS = Settings(
    Function=b"f",
    Symbol=b"s",
    String=b"S",
    BinaryString=b"B",
    Integer8=b"C",
    Integer16=b"j",
    Integer32=b"i",
    Integer64=b"L",
    Real64=b"r",
    BigInteger=b"I",
    BigReal=b"R",
    PackedArray=_bytes(0xC1),
    NumericArray=_bytes(0xC2),
    Association=b"A",
    Rule=b"-",
    RuleDelayed=b":",
)

# The list of all array value type tokens.
ARRAY_TYPES = Settings(
    Integer8=_bytes(0x00),
    Integer16=_bytes(0x01),
    Integer32=_bytes(0x02),
    Integer64=_bytes(0x03),
    UnsignedInteger8=_bytes(0x10),
    UnsignedInteger16=_bytes(0x11),
    UnsignedInteger32=_bytes(0x12),
    UnsignedInteger64=_bytes(0x13),
    Real32=_bytes(0x22),
    Real64=_bytes(0x23),
    ComplexReal32=_bytes(0x33),
    ComplexReal64=_bytes(0x34),
)
ARRAY_TYPES_FROM_WXF_TYPES = {v: k for k, v in ARRAY_TYPES.items()}


ARRAY_TYPES_ELEM_SIZE = {
    ARRAY_TYPES.Integer8: 1,
    ARRAY_TYPES.Integer16: 2,
    ARRAY_TYPES.Integer32: 4,
    ARRAY_TYPES.Integer64: 8,
    ARRAY_TYPES.UnsignedInteger8: 1,
    ARRAY_TYPES.UnsignedInteger16: 2,
    ARRAY_TYPES.UnsignedInteger32: 4,
    ARRAY_TYPES.UnsignedInteger64: 8,
    ARRAY_TYPES.Real32: 4,
    ARRAY_TYPES.Real64: 8,
    ARRAY_TYPES.ComplexReal32: 8,
    ARRAY_TYPES.ComplexReal64: 16,
}
""" A set of all valid value type tokens for PackedArray.
There is no restriction for NumericArray value types. """
VALID_PACKED_ARRAY_TYPES = frozenset(
    (
        ARRAY_TYPES.Integer8,
        ARRAY_TYPES.Integer16,
        ARRAY_TYPES.Integer32,
        ARRAY_TYPES.Integer64,
        ARRAY_TYPES.Real32,
        ARRAY_TYPES.Real64,
        ARRAY_TYPES.ComplexReal32,
        ARRAY_TYPES.ComplexReal64,
    )
)

VALID_PACKED_ARRAY_LABEL_TYPES = frozenset(
    (
        "Integer8",
        "Integer16",
        "Integer32",
        "Integer64",
        "Real32",
        "Real64",
        "ComplexReal32",
        "ComplexReal64",
    )
)

def make_struct(format, size = 1):
    s = struct.Struct(b"<%s%s" % (size > 1 and size or b"", format))
    return Settings(
        format = s.format,
        as_size = partial(make_struct, format),
        pack = s.pack,
        pack_into = s.pack_into,
        unpack = s.unpack,
    )

STRUCT_MAPPING = Settings(
    Integer8=make_struct(b"b"),
    UnsignedInteger8=make_struct(b"B"),
    Integer16=make_struct(b"h"),
    UnsignedInteger16=make_struct(b"H"),
    Integer32=make_struct(b"i"),
    UnsignedInteger32=make_struct(b"I"),
    Integer64=make_struct(b"q"),
    UnsignedInteger64=make_struct(b"Q"),
    Real32=make_struct(b"f"),
    Real64=make_struct(b"d"),
    ComplexReal32=make_struct(b"f"),
    ComplexReal64=make_struct(b"d"),
)
