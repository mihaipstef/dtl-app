#!/usr/bin/env python3

import functools
import struct
import sys


fname = sys.argv[1]
frame_len = int(sys.argv[2])

chunk_size = 64
typ = "fcomplex"
pilots = (-21+32, -7+32, 7+32, 21+32)
with open(fname, "rb") as f:
    match typ:
        case "fcomplex":
            chunker = functools.partial(f.read, chunk_size * 8)
            for i_sym, bin_ofdm in enumerate(iter(chunker, b'')):
                i = i_sym % frame_len
                j = i_sym // frame_len
                ofdm = struct.unpack('f'*chunk_size*2, bin_ofdm)
                ofdm_sym = list(zip(ofdm[::2], ofdm[1::2]))
                f_pilots = [x for i,x in enumerate(ofdm_sym) if i in pilots]
                print(f"[{j}] [{i}] {ofdm_sym}")
                print("***")
        case _:
            print("nothing")