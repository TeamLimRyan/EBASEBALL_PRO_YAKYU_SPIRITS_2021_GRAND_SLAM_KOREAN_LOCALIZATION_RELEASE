"""Native acceleration of the public filename-derived RDB transform."""
import ctypes
from pathlib import Path
try:
    from rdb_primitives import initial_state,crypt as reference
except ImportError:
    from rdblib import initial_state,crypt as reference
_fn=None

def crypt(data,seed):
    global _fn
    if len(data)%4:raise ValueError('RDB word alignment')
    dll=next((Path(__file__).with_name(n) for n in ['native_bits_v3.dll','native_bits.dll'] if Path(__file__).with_name(n).exists()),None)
    if dll is None:return reference(data,seed)
    if _fn is None:
        lib=ctypes.CDLL(str(dll))
        if not hasattr(lib,'rdb_transform'):return reference(data,seed)
        _fn=lib.rdb_transform;_fn.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p];_fn.restype=ctypes.c_int
    buf=bytearray(data);out=(ctypes.c_ubyte*len(buf)).from_buffer(buf);state=(ctypes.c_uint32*64)(*initial_state(seed));_fn(out,len(buf)//4,state);return bytes(buf)
