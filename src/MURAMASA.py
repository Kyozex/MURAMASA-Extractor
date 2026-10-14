import struct
import os
from typing import BinaryIO
import zlib

FILE_PATH_ENCODING = "gbk"
DIR_TYPE = 1
FILE_TYPE = 2
UINT8_MASK = 0xFF
UINT32_MASK = 0xFFFFFFFF

# use in un obfuscate
REORDER_TABLE = [
    0x48, 0xE8, 0xD3, 0x11, 0x1D, 0x58, 0xEA, 0xE5, 0x23, 0xBD, 0x41, 0xC0, 0x86, 0x6A, 0x0A, 0xB3,
    0xE9, 0x26, 0xAE, 0x90, 0xBF, 0x92, 0x02, 0x55, 0x06, 0x61, 0xAF, 0xF1, 0x76, 0xF0, 0x96, 0x91,
    0x34, 0x40, 0x30, 0xA6, 0x15, 0x1E, 0x89, 0x09, 0x7E, 0x2E, 0x63, 0x8B, 0xA1, 0x43, 0x9E, 0x51,
    0xB5, 0xFA, 0xB2, 0x93, 0xE7, 0xD1, 0xBA, 0x33, 0xE2, 0x9F, 0xF6, 0x56, 0xCC, 0x67, 0x71, 0xBC,
    0xED, 0x08, 0xDC, 0xE0, 0xC6, 0xD6, 0xFC, 0x21, 0x99, 0x0E, 0x5F, 0xF2, 0xB4, 0xDB, 0x84, 0xD7,
    0xA7, 0x2A, 0x82, 0x3F, 0xEC, 0x6D, 0xA8, 0x62, 0x5E, 0x8A, 0x28, 0x00, 0xE4, 0x36, 0xFD, 0x8C,
    0x65, 0xA9, 0x39, 0xB7, 0x25, 0x7B, 0x7F, 0xA5, 0x10, 0x2C, 0x54, 0x3B, 0x74, 0xC9, 0x4A, 0x53,
    0xCE, 0xFE, 0xE1, 0x2B, 0xD9, 0x3D, 0xDF, 0x22, 0x3E, 0xD2, 0xB6, 0x8D, 0x8E, 0x72, 0xC4, 0x0D,
    0x52, 0x88, 0x85, 0xB0, 0x7C, 0xD0, 0x6C, 0x31, 0xB8, 0x13, 0x46, 0xAB, 0xF3, 0x81, 0x5C, 0x01,
    0xCB, 0xC2, 0xF5, 0xFB, 0x20, 0xA4, 0x47, 0xD5, 0xB9, 0x4C, 0x3A, 0x77, 0x3C, 0x44, 0x2D, 0x19,
    0x14, 0x5A, 0x45, 0x0B, 0xD8, 0xDD, 0xF7, 0x07, 0xCF, 0xDA, 0x0F, 0x32, 0x38, 0x37, 0x9C, 0x75,
    0x24, 0x57, 0x05, 0xCD, 0xBB, 0xF4, 0xCA, 0x69, 0x03, 0xA3, 0xBE, 0x49, 0xEE, 0x17, 0x1F, 0x59,
    0x7A, 0x78, 0x1C, 0xC8, 0xC7, 0x7D, 0x66, 0x5B, 0x35, 0x04, 0x9A, 0x64, 0xAA, 0x9D, 0x4D, 0x83,
    0x42, 0xC3, 0xDE, 0x1A, 0x50, 0x6F, 0xFF, 0x6E, 0x0C, 0x2F, 0xAD, 0x94, 0xA2, 0x97, 0x9B, 0xC5,
    0x70, 0x79, 0xC1, 0xEF, 0x98, 0xA0, 0xF9, 0xEB, 0x80, 0xF8, 0x73, 0x27, 0x18, 0x6B, 0x29, 0xAC,
    0x4B, 0x16, 0x68, 0x12, 0xE3, 0x95, 0x4E, 0xD4, 0x8F, 0x87, 0xE6, 0x5D, 0x1B, 0xB1, 0x4F, 0x60,
]

# use in obfuscate
ORDER_TABLE = [
    0x5b, 0x8f, 0x16, 0xb8, 0xc9, 0xb2, 0x18, 0xa7, 0x41, 0x27, 0x0e, 0xa3, 0xd8, 0x7f, 0x49, 0xaa,
    0x68, 0x03, 0xf3, 0x89, 0xa0, 0x24, 0xf1, 0xbd, 0xec, 0x9f, 0xd3, 0xfc, 0xc2, 0x04, 0x25, 0xbe,
    0x94, 0x47, 0x77, 0x08, 0xb0, 0x64, 0x11, 0xeb, 0x5a, 0xee, 0x51, 0x73, 0x69, 0x9e, 0x29, 0xd9,
    0x22, 0x87, 0xab, 0x37, 0x20, 0xc8, 0x5d, 0xad, 0xac, 0x62, 0x9a, 0x6b, 0x9c, 0x75, 0x78, 0x53,
    0x21, 0x0a, 0xd0, 0x2d, 0x9d, 0xa2, 0x8a, 0x96, 0x00, 0xbb, 0x6e, 0xf0, 0x99, 0xce, 0xf6, 0xfe,
    0xd4, 0x2f, 0x80, 0x6f, 0x6a, 0x17, 0x3b, 0xb1, 0x05, 0xbf, 0xa1, 0xc7, 0x8e, 0xfb, 0x58, 0x4a,
    0xff, 0x19, 0x57, 0x2a, 0xcb, 0x60, 0xc6, 0x3d, 0xf2, 0xb7, 0x0d, 0xed, 0x86, 0x55, 0xd7, 0xd5,
    0xe0, 0x3e, 0x7d, 0xea, 0x6c, 0xaf, 0x1c, 0x9b, 0xc1, 0xe1, 0xc0, 0x65, 0x84, 0xc5, 0x28, 0x66,
    0xe8, 0x8d, 0x52, 0xcf, 0x4e, 0x82, 0x0c, 0xf9, 0x81, 0x26, 0x59, 0x2b, 0x5f, 0x7b, 0x7c, 0xf8,
    0x13, 0x1f, 0x15, 0x33, 0xdb, 0xf5, 0x1e, 0xdd, 0xe4, 0x48, 0xca, 0xde, 0xae, 0xcd, 0x2e, 0x39,
    0xe5, 0x2c, 0xdc, 0xb9, 0x95, 0x67, 0x23, 0x50, 0x56, 0x61, 0xcc, 0x8b, 0xef, 0xda, 0x12, 0x1a,
    0x83, 0xfd, 0x32, 0x0f, 0x4c, 0x30, 0x7a, 0x63, 0x88, 0x98, 0x36, 0xb4, 0x3f, 0x09, 0xba, 0x14,
    0x0b, 0xe2, 0x91, 0xd1, 0x7e, 0xdf, 0x44, 0xc4, 0xc3, 0x6d, 0xb6, 0x90, 0x3c, 0xb3, 0x70, 0xa8,
    0x85, 0x35, 0x79, 0x02, 0xf7, 0x97, 0x45, 0x4f, 0xa4, 0x74, 0xa9, 0x4d, 0x42, 0xa5, 0xd2, 0x76,
    0x43, 0x72, 0x38, 0xf4, 0x5c, 0x07, 0xfa, 0x34, 0x01, 0x10, 0x06, 0xe7, 0x54, 0x40, 0xbc, 0xe3,
    0x1d, 0x1b, 0x4b, 0x8c, 0xb5, 0x92, 0x3a, 0xa6, 0xe9, 0xe6, 0x31, 0x93, 0x46, 0x5e, 0x71, 0xd6,
]


# Data-byte substitution used by the Muramasa Shokuzai Hen archive. The path
# obfuscation is unchanged; this table and key seed apply only to file payloads.
SHOKUZAI_REORDER_TABLE = [
    0xCA, 0xBA, 0xF3, 0x7B, 0x7E, 0x0A, 0xB7, 0xB0, 0x43, 0x1E, 0xCB, 0x8C, 0x21, 0x97, 0xD7, 0x13,
    0xB5, 0x41, 0x69, 0xEC, 0x12, 0xE8, 0xD8, 0x00, 0xD1, 0x9B, 0x62, 0x3B, 0xA1, 0x3C, 0xE1, 0xEB,
    0x5F, 0xCC, 0x5C, 0x61, 0x70, 0x79, 0x25, 0xD5, 0xA9, 0x49, 0x93, 0x2D, 0x6B, 0xC3, 0xE9, 0x0B,
    0x10, 0x37, 0x18, 0xE3, 0xB4, 0xFB, 0x17, 0x53, 0xB8, 0xE2, 0x31, 0x01, 0x86, 0x94, 0xAB, 0x16,
    0xBE, 0xDA, 0xF6, 0xBC, 0x81, 0xF1, 0x36, 0x4B, 0xE5, 0xD9, 0x02, 0x38, 0x1F, 0xFD, 0x2F, 0xF4,
    0x64, 0x47, 0x28, 0x52, 0xB6, 0x9E, 0x6A, 0x98, 0x09, 0x27, 0x4A, 0xDC, 0xBF, 0x51, 0x3E, 0x26,
    0x90, 0x65, 0x55, 0x14, 0x40, 0xAD, 0xA2, 0x60, 0x7C, 0x46, 0x0F, 0x5D, 0xAF, 0x85, 0xC7, 0x03,
    0x89, 0x39, 0xBB, 0x4D, 0xF5, 0x5E, 0xF2, 0x48, 0x59, 0xF8, 0x11, 0x2E, 0x29, 0xA8, 0x8F, 0xDE,
    0x08, 0x2A, 0x20, 0x1C, 0xA6, 0xFC, 0x96, 0x5B, 0x1A, 0x73, 0xC1, 0x6D, 0x33, 0x2B, 0x06, 0xDB,
    0x8D, 0x88, 0x30, 0x3D, 0x4C, 0x6F, 0xC4, 0xF0, 0x15, 0xC6, 0x57, 0xA4, 0x56, 0xCF, 0x4E, 0x75,
    0x7F, 0x07, 0xC0, 0xDD, 0xFA, 0xFE, 0x34, 0xD4, 0x82, 0xF7, 0xD2, 0x58, 0x5A, 0x54, 0xE6, 0xA0,
    0x4F, 0x04, 0xD0, 0x8E, 0x1D, 0x3F, 0x87, 0x95, 0xD3, 0x63, 0x19, 0xC5, 0xB9, 0x74, 0x72, 0x05,
    0xA7, 0xAA, 0x76, 0x8A, 0x84, 0xAE, 0x91, 0x0D, 0x50, 0xDF, 0xE7, 0x9F, 0x67, 0xEE, 0xCE, 0x23,
    0xC8, 0x83, 0xF9, 0x77, 0x0C, 0x92, 0x32, 0x99, 0xD6, 0x42, 0x6E, 0xEF, 0x68, 0xE4, 0xED, 0x80,
    0xAC, 0xA5, 0x8B, 0xB2, 0xEA, 0x6C, 0x35, 0xBD, 0x2C, 0x3A, 0xA3, 0x44, 0x7A, 0x9D, 0x45, 0x66,
    0xCD, 0x71, 0x9A, 0x78, 0xB3, 0xE0, 0xC9, 0xFF, 0x22, 0x24, 0xB1, 0x0E, 0x7D, 0x1B, 0xC2, 0x9C,
]

# Data-byte substitution used by the Muramasa Janen Hen archive.
JANEN_REORDER_TABLE = [
    0xA1, 0xF1, 0x70, 0x5F, 0x5D, 0x01, 0xFA, 0xF6, 0x80, 0xCD, 0xAF, 0xEE, 0x37, 0x1A, 0x6A, 0xC0,
    0xF9, 0x87, 0xD4, 0xBE, 0xC5, 0xB3, 0x63, 0x06, 0x67, 0x1F, 0xD5, 0x4F, 0x27, 0x4E, 0xB7, 0xBF,
    0x92, 0xAE, 0x9E, 0xD7, 0x56, 0x54, 0x39, 0x69, 0x24, 0x84, 0x10, 0x3B, 0xDF, 0xA0, 0xB4, 0x0F,
    0xC6, 0x4A, 0xC3, 0xB0, 0xF8, 0x7F, 0xCA, 0x90, 0xF3, 0xB5, 0x47, 0x07, 0xEC, 0x18, 0x2F, 0xCC,
    0xFD, 0x61, 0x7C, 0xFE, 0xE7, 0x77, 0x4C, 0x8F, 0xB9, 0x64, 0x05, 0x43, 0xC2, 0x7B, 0x32, 0x78,
    0xD8, 0x8A, 0x33, 0x95, 0xFC, 0x1D, 0xD1, 0x13, 0x04, 0x3A, 0x81, 0x6E, 0xF2, 0x97, 0x4D, 0x3C,
    0x16, 0xD9, 0x99, 0xC8, 0x86, 0x2B, 0x25, 0xD6, 0x5E, 0x8C, 0x02, 0x9B, 0x22, 0xE9, 0xAA, 0x00,
    0xE4, 0x44, 0xFF, 0x8B, 0x79, 0x9D, 0x75, 0x83, 0x94, 0x73, 0xC7, 0x3D, 0x34, 0x23, 0xE2, 0x6D,
    0x03, 0x31, 0x36, 0xCE, 0x2C, 0x7E, 0x1C, 0x9F, 0xC1, 0x50, 0xA7, 0xDB, 0x40, 0x3F, 0x0C, 0x6F,
    0xEB, 0xE3, 0x46, 0x4B, 0x8E, 0xD2, 0xA8, 0x76, 0xC9, 0xAC, 0x9A, 0x28, 0x9C, 0xA2, 0x8D, 0x59,
    0x52, 0x0A, 0xA6, 0x6B, 0x71, 0x7D, 0x48, 0x68, 0xE5, 0x7A, 0x65, 0x93, 0x91, 0x98, 0xBC, 0x26,
    0x82, 0x08, 0x66, 0xED, 0xCB, 0x42, 0xEA, 0x19, 0x60, 0xD0, 0xC4, 0xA9, 0xF4, 0x58, 0x55, 0x09,
    0x2A, 0x21, 0x5C, 0xE1, 0xE8, 0x2D, 0x17, 0x0B, 0x96, 0x62, 0xBA, 0x12, 0xDA, 0xBD, 0xAD, 0x30,
    0xA3, 0xE0, 0x74, 0x5A, 0x0E, 0x15, 0x45, 0x14, 0x6C, 0x85, 0xDD, 0xB2, 0xD3, 0xB8, 0xBB, 0xE6,
    0x2E, 0x29, 0xEF, 0xF5, 0xB1, 0xDE, 0x49, 0xFB, 0x3E, 0x41, 0x20, 0x88, 0x51, 0x1B, 0x89, 0xDC,
    0xAB, 0x57, 0x11, 0x53, 0xF0, 0xB6, 0xA4, 0x72, 0x35, 0x38, 0xF7, 0x0D, 0x5B, 0xCF, 0xA5, 0x1E,
]

DATA_CRYPTO_PROFILES = {
    "muramasa": {"name": "MURAMASA", "table": REORDER_TABLE,
                  "key_constant": 0x87654321, "path_encoding": None},
    "janen": {"name": "Janen Hen", "table": JANEN_REORDER_TABLE,
              "key_constant": 0x87654321, "path_encoding": "cp932"},
    "shokuzai": {"name": "Shokuzai Hen", "table": SHOKUZAI_REORDER_TABLE,
                 "key_constant": 0x20101118, "path_encoding": "cp932"},
}


# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# ==================================================================
# ========================== Common Utils ==========================
# ==================================================================
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

class BinaryReader:
    def __init__(self, fp: BinaryIO):
        self._fp = fp

    def read(self, n: int):
        buf = self._fp.read(n)
        assert len(buf) == n, "Reading Data Fail"
        return buf

    def seek(self, offset, whence):
        self._fp.seek(offset, whence)


# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# ==================================================================
# ======================== NPA Structure Def =======================
# ==================================================================
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


class NpaHeader:
    FMT = "<3sIII2sIIIIII"
    SIZE = 3 + 4 + 4 + 4 + 2 + 4 + 4 + 4 + 4 + 4 + 4
    SIG = b'NPA'

    def __init__(self, signature_3s: bytes, unknown1_I: int, seed1_I: int, seed2_I: int, unknown2_2s: bytes,
                 entryCount_I: int, dirCount_I: int, fileCount_I: int,  # excluding directories
                 unknown4_I: int, unknown5_I: int, tocLength_I: int):
        assert signature_3s == NpaHeader.SIG, "invalid Signature"
        assert entryCount_I == dirCount_I + fileCount_I

        self.signature_3s = signature_3s
        self.unknown1_I = unknown1_I
        self.seed1_I = seed1_I
        self.seed2_I = seed2_I
        self.unknown2_2s = unknown2_2s
        self.entryCount_I = entryCount_I
        self.dirCount_I = dirCount_I
        self.fileCount_I = fileCount_I
        self.unknown4_I = unknown4_I
        self.unknown5_I = unknown5_I
        self.tocLength_I = tocLength_I

    @staticmethod
    def unpack(data: bytes):
        assert len(data) == NpaHeader.SIZE
        return NpaHeader(*struct.unpack(NpaHeader.FMT, data))

    def pack(self):
        return struct.pack(NpaHeader.FMT, self.signature_3s, self.unknown1_I, self.seed1_I, self.seed2_I,
                           self.unknown2_2s, self.entryCount_I, self.dirCount_I, self.fileCount_I, self.unknown4_I,
                           self.unknown5_I, self.tocLength_I)


class NpaEntry1:
    FMT = "<I"
    SIZE = 4

    def __init__(self, filePathLength_I: int):
        self.filePathLength_I = filePathLength_I

    @staticmethod
    def unpack(data: bytes):
        assert len(data) == NpaEntry1.SIZE
        return NpaEntry1(*struct.unpack(NpaEntry1.FMT, data))

    def pack(self):
        return struct.pack(NpaEntry1.FMT, self.filePathLength_I)


class NpaEntry2:
    FMT = "<BIIII"
    SIZE = 1 + 4 + 4 + 4 + 4

    def __init__(self, type_B: int, fileBatch_I: int, offset_I: int, length_I: int, originalLength_I: int):
        assert type_B in (DIR_TYPE, FILE_TYPE)

        self.type_B = type_B
        self.fileBatch_I = fileBatch_I
        self.offset_I = offset_I
        self.length_I = length_I
        self.originalLength_I = originalLength_I

    @staticmethod
    def unpack(data: bytes):
        assert len(data) == NpaEntry2.SIZE
        return NpaEntry2(*struct.unpack(NpaEntry2.FMT, data))

    def pack(self):
        return struct.pack(NpaEntry2.FMT, self.type_B, self.fileBatch_I, self.offset_I,
                           self.length_I, self.originalLength_I)


class NpsiHeader:
    FMT = "<4sIHIIII"
    SIZE = 4 + 4 + 2 + 4 + 4 + 4 + 4
    SIG = b'NPSI'

    def __init__(self, signature_4s: bytes, unknown1_I: int, unknown2_H: int,
                 width_I: int, width2_I: int, height_I: int, height2_I: int):
        assert signature_4s == NpsiHeader.SIG, "invalid sig"

        self.signature_4s = signature_4s
        self.unknown1_I = unknown1_I
        self.unknown2_H = unknown2_H
        self.width_I = width_I
        self.width2_I = width2_I
        self.height_I = height_I
        self.height2_I = height2_I

    @staticmethod
    def unpack(data: bytes):
        assert len(data) == NpsiHeader.SIZE
        return NpsiHeader(*struct.unpack(NpsiHeader.FMT, data))

    def pack(self):
        return struct.pack(NpsiHeader.FMT, self.signature_4s, self.unknown1_I, self.unknown2_H,
                           self.width_I, self.width2_I, self.height_I, self.height2_I)


# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# ==================================================================
# ======================== NPA Unpacking  ==========================
# ==================================================================
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

def un_obfuscate(buf: bytes, len_I: int, key_I: int, reorder_table=REORDER_TABLE) -> bytes:
    # buf'[i] = reorder_table[buf[i]] - key_I - i
    return bytes([(reorder_table[buf[i]] - key_I - i) & UINT8_MASK for i in range(len_I)])


def obfuscate(buf: bytes, len_I: int, key_I: int) -> bytes:
    # buf'[i] = ORDER_TABLE[ buf[i] + key_I + i ]
    return bytes([ORDER_TABLE[(buf[i] + key_I + i) & UINT8_MASK] for i in range(len_I)])


def generate_file_key(buf: bytes, len_I: int, dataLength_I: int, seed1_I: int, seed2_I: int,
                      key_constant_I: int = 0x87654321) -> int:
    """

    :param buf:             buffer, use to gen key
    :param len_I:           length of buf           (uint32_t, 4 bytes length)
    :param dataLength_I:    file original length    (uint32_t, 4 bytes length)
    :param seed1_I:         seed1                   (uint32_t, 4 bytes length)
    :param seed2_I:         seed2                   (uint32_t, 4 bytes length)
    :param key_constant_I:  payload cipher variant constant
    :return:                key                     (uint32_t, 4 bytes length)
    """
    # key: uint32_t = ((key_constant - sum(buf)) * len + seed1 * seed2) * dataLength
    return (((key_constant_I - sum(buf)) * len_I + seed1_I * seed2_I) * dataLength_I) & UINT32_MASK


def un_obfuscate_file_path(buf: bytes, len_I: int, index_I: int, seed1_I: int, seed2_I: int) -> bytes:
    ret = []
    for i in range(len_I):
        key = i * 0xFC
        mutator = seed1_I * seed2_I

        key -= (mutator >> 24) & UINT8_MASK
        key -= (mutator >> 16) & UINT8_MASK
        key -= (mutator >> 8) & UINT8_MASK

        key -= seed1_I * seed2_I

        key -= (index_I >> 24) & UINT8_MASK
        key -= (index_I >> 16) & UINT8_MASK
        key -= (index_I >> 8) & UINT8_MASK
        key -= index_I & UINT8_MASK

        ret.append((buf[i] + key) & UINT8_MASK)
    return bytes(ret)


def obfuscate_file_path(raw_path: bytes, len_I: int, index_I: int, seed1_I: int, seed2_I: int) -> bytes:
    ret = []
    for i in range(len_I):
        key = i * 0xFC
        mutator = seed1_I * seed2_I

        key -= (mutator >> 24) & UINT8_MASK
        key -= (mutator >> 16) & UINT8_MASK
        key -= (mutator >> 8) & UINT8_MASK

        key -= seed1_I * seed2_I

        key -= (index_I >> 24) & UINT8_MASK
        key -= (index_I >> 16) & UINT8_MASK
        key -= (index_I >> 8) & UINT8_MASK
        key -= index_I & UINT8_MASK

        ret.append((raw_path[i] - key) & UINT8_MASK)
    return bytes(ret)


def _read_npa_entries(toc_buf: bytes, hdr: NpaHeader, archive_size: int):
    data_base = NpaHeader.SIZE + hdr.tocLength_I
    entries = []
    pos = 0
    for index in range(hdr.entryCount_I):
        if pos + NpaEntry1.SIZE > len(toc_buf):
            raise ValueError("Truncated NPA directory table")
        entry1 = NpaEntry1.unpack(toc_buf[pos:pos + NpaEntry1.SIZE])
        pos += NpaEntry1.SIZE
        path_end = pos + entry1.filePathLength_I
        if path_end + NpaEntry2.SIZE > len(toc_buf):
            raise ValueError("Truncated NPA path or entry")
        raw_path = toc_buf[pos:path_end]
        pos = path_end
        entry2 = NpaEntry2.unpack(toc_buf[pos:pos + NpaEntry2.SIZE])
        pos += NpaEntry2.SIZE
        if data_base + entry2.offset_I + entry2.length_I > archive_size:
            raise ValueError("NPA entry points outside the archive: index {}".format(index))
        entries.append((raw_path, entry2))
    if pos != len(toc_buf):
        raise ValueError("NPA directory table length does not match its header")
    return entries


_FILE_SIGNATURES = (
    b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"NPSI", b"BM", b"GIF87a", b"GIF89a",
    b"RIFF", b"OggS", b"ID3", b"PK\x03\x04",
)
_EXTENSION_SIGNATURES = {
    ".png": (b"\x89PNG\r\n\x1a\n", b"NPSI"),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".bmp": (b"BM",),
    ".gif": (b"GIF87a", b"GIF89a"),
    ".wav": (b"RIFF",),
    ".ogg": (b"OggS",),
    ".zip": (b"PK\x03\x04",),
}


def _decode_entry_prefix(fp_in: BinaryReader, data_base: int, raw_path: bytes, entry2: NpaEntry2,
                         hdr: NpaHeader, profile: dict) -> bytes:
    if not entry2.length_I:
        return b""
    # Encryption only covers the first 0x1000 + path length bytes. Read enough
    # to recognize the file header, including when the payload is zlib-compressed.
    read_len = min(entry2.length_I, 0x1000 + len(raw_path))
    fp_in.seek(data_base + entry2.offset_I, 0)
    buf = fp_in.read(read_len)
    key = generate_file_key(raw_path, len(raw_path), entry2.originalLength_I,
                            hdr.seed1_I, hdr.seed2_I, profile["key_constant"])
    decoded = un_obfuscate(buf, len(buf), key, profile["table"])
    if entry2.length_I != entry2.originalLength_I:
        try:
            decoded = zlib.decompressobj().decompress(decoded, 64)
        except zlib.error:
            pass
    return decoded


def _signature_score(file_name: str, prefix: bytes) -> int:
    extension = os.path.splitext(file_name)[1].lower()
    expected = _EXTENSION_SIGNATURES.get(extension, ())
    if any(prefix.startswith(signature) for signature in expected):
        return 2
    if any(prefix.startswith(signature) for signature in _FILE_SIGNATURES):
        return 1
    return 0


def _detect_data_crypto(fp_in: BinaryReader, entries, hdr: NpaHeader) -> str:
    data_base = NpaHeader.SIZE + hdr.tocLength_I
    scores = {name: 0 for name in DATA_CRYPTO_PROFILES}
    sampled = 0
    for index, (encoded_path, entry2) in enumerate(entries):
        if entry2.type_B != FILE_TYPE or not entry2.length_I:
            continue
        raw_path = un_obfuscate_file_path(encoded_path, len(encoded_path), index,
                                          hdr.seed1_I, hdr.seed2_I)
        # File extensions are ASCII; avoid assuming the archive's name encoding
        # before the payload profile has been detected.
        file_name = raw_path.decode("ascii", errors="replace")
        for profile_name, profile in DATA_CRYPTO_PROFILES.items():
            prefix = _decode_entry_prefix(fp_in, data_base, raw_path, entry2, hdr, profile)
            scores[profile_name] += _signature_score(file_name, prefix)
        sampled += 1
        if sampled >= 64:
            break
    # Keep the original algorithm as the fallback for archives without common
    # image/audio signatures; known signatures distinguish the two variants.
    return max(scores, key=scores.get) if max(scores.values(), default=0) else "muramasa"


def inspect_archive(in_filePath: str, crypto_profile: str = "auto") -> dict:
    """Read archive metadata and identify its payload cipher without extracting it."""
    if crypto_profile != "auto" and crypto_profile not in DATA_CRYPTO_PROFILES:
        raise ValueError("crypto_profile must be 'auto', 'muramasa', 'janen', or 'shokuzai'")

    with open(in_filePath, "rb") as fp:
        reader = BinaryReader(fp)
        hdr = NpaHeader.unpack(reader.read(NpaHeader.SIZE))
        toc_buf = reader.read(hdr.tocLength_I)
        entries = _read_npa_entries(toc_buf, hdr, os.path.getsize(in_filePath))
        selected_profile = crypto_profile
        if selected_profile == "auto":
            selected_profile = _detect_data_crypto(reader, entries, hdr)

    return {
        "profile": selected_profile,
        "profile_name": DATA_CRYPTO_PROFILES[selected_profile]["name"],
        "entry_count": hdr.entryCount_I,
        "directory_count": hdr.dirCount_I,
        "file_count": hdr.fileCount_I,
        "toc_length": hdr.tocLength_I,
        "archive_size": os.path.getsize(in_filePath),
    }


def list_archive_entries(in_filePath: str, crypto_profile: str = "auto",
                        file_path_encoding: str | None = None) -> dict:
    """List archive paths and sizes for browsing or selective extraction."""
    if crypto_profile != "auto" and crypto_profile not in DATA_CRYPTO_PROFILES:
        raise ValueError("crypto_profile must be 'auto', 'muramasa', 'janen', or 'shokuzai'")

    archive_size = os.path.getsize(in_filePath)
    with open(in_filePath, "rb") as fp:
        reader = BinaryReader(fp)
        hdr = NpaHeader.unpack(reader.read(NpaHeader.SIZE))
        toc_buf = reader.read(hdr.tocLength_I)
        entries = _read_npa_entries(toc_buf, hdr, archive_size)
        selected_profile = crypto_profile
        if selected_profile == "auto":
            selected_profile = _detect_data_crypto(reader, entries, hdr)
        profile = DATA_CRYPTO_PROFILES[selected_profile]
        path_encoding = file_path_encoding or profile["path_encoding"] or FILE_PATH_ENCODING

        listed_entries = []
        for index, (encoded_path, entry) in enumerate(entries):
            raw_path = un_obfuscate_file_path(encoded_path, len(encoded_path), index,
                                              hdr.seed1_I, hdr.seed2_I)
            path = raw_path.decode(path_encoding)
            listed_entries.append({
                "index": index,
                "path": path,
                "is_dir": entry.type_B == DIR_TYPE,
                "size": entry.originalLength_I,
                "packed_size": entry.length_I,
                "extension": os.path.splitext(path)[1].lower(),
            })

    return {
        "profile": selected_profile,
        "profile_name": profile["name"],
        "entry_count": hdr.entryCount_I,
        "directory_count": hdr.dirCount_I,
        "file_count": hdr.fileCount_I,
        "archive_size": archive_size,
        "entries": listed_entries,
    }


def read_archive_entry(in_filePath: str, entry_index: int, crypto_profile: str = "auto",
                       file_path_encoding: str | None = None) -> bytes:
    """Decrypt and decompress one file entry, returning its original bytes."""
    if crypto_profile != "auto" and crypto_profile not in DATA_CRYPTO_PROFILES:
        raise ValueError("crypto_profile must be 'auto', 'muramasa', 'janen', or 'shokuzai'")

    with open(in_filePath, "rb") as fp:
        reader = BinaryReader(fp)
        hdr = NpaHeader.unpack(reader.read(NpaHeader.SIZE))
        toc_buf = reader.read(hdr.tocLength_I)
        data_base = NpaHeader.SIZE + hdr.tocLength_I
        entries = _read_npa_entries(toc_buf, hdr, os.path.getsize(in_filePath))
        if not isinstance(entry_index, int) or not 0 <= entry_index < len(entries):
            raise IndexError("archive entry index is out of range")
        if crypto_profile == "auto":
            crypto_profile = _detect_data_crypto(reader, entries, hdr)
        profile = DATA_CRYPTO_PROFILES[crypto_profile]
        encoded_path, entry = entries[entry_index]
        if entry.type_B != FILE_TYPE:
            raise ValueError("archive entry is a directory")
        raw_path = un_obfuscate_file_path(encoded_path, len(encoded_path), entry_index,
                                          hdr.seed1_I, hdr.seed2_I)
        relative_path = raw_path.decode(file_path_encoding or profile["path_encoding"] or FILE_PATH_ENCODING)
        if not entry.length_I:
            return b""

        reader.seek(data_base + entry.offset_I, 0)
        buf = reader.read(entry.length_I)
        key = generate_file_key(raw_path, len(raw_path), entry.originalLength_I,
                                hdr.seed1_I, hdr.seed2_I, profile["key_constant"])
        un_obfuscate_len = min(len(buf), 0x1000 + len(raw_path))
        buf = un_obfuscate(buf[:un_obfuscate_len], un_obfuscate_len, key, profile["table"]) + buf[un_obfuscate_len:]
        if entry.length_I != entry.originalLength_I:
            obj = zlib.decompressobj()
            buf = obj.decompress(buf) + obj.flush()
            if len(buf) != entry.originalLength_I:
                raise ValueError("Decompress failed for '{}'".format(relative_path))
        return buf


def _emit_log(message: str, log_callback=None) -> None:
    print(message, flush=True)
    if log_callback is not None:
        log_callback(message)


def unpack(in_filePath: str, out_dirPath: str, crypto_profile: str = "auto",
           file_path_encoding: str | None = None, progress_callback=None,
           cancel_callback=None, log_callback=None, selected_paths=None) -> None:
    """Unpack an NPA archive, detecting its data cipher and path encoding."""
    if not os.path.isdir(out_dirPath):
        raise FileNotFoundError("output directory '{}' doesn't exist".format(out_dirPath))
    if crypto_profile != "auto" and crypto_profile not in DATA_CRYPTO_PROFILES:
        raise ValueError("crypto_profile must be 'auto', 'muramasa', 'janen', or 'shokuzai'")

    with open(in_filePath, "rb") as _fp_in:
        fp_in = BinaryReader(_fp_in)
        hdr = NpaHeader.unpack(fp_in.read(NpaHeader.SIZE))
        toc_buf = fp_in.read(hdr.tocLength_I)
        data_base = NpaHeader.SIZE + hdr.tocLength_I
        entries = _read_npa_entries(toc_buf, hdr, os.path.getsize(in_filePath))
        if crypto_profile == "auto":
            crypto_profile = _detect_data_crypto(fp_in, entries, hdr)
        profile = DATA_CRYPTO_PROFILES[crypto_profile]
        path_encoding = file_path_encoding or profile["path_encoding"] or FILE_PATH_ENCODING
        _emit_log("[log] data cipher: {}".format(profile["name"]), log_callback)

        selected = None
        if selected_paths is not None:
            selected = {str(path).replace("\\", "/").strip("/") for path in selected_paths}
            if not selected:
                raise ValueError("No files selected")
            available = set()
            for index, (encoded_path, entry) in enumerate(entries):
                if entry.type_B == FILE_TYPE:
                    raw_path = un_obfuscate_file_path(encoded_path, len(encoded_path), index,
                                                      hdr.seed1_I, hdr.seed2_I)
                    available.add(raw_path.decode(path_encoding).replace("\\", "/").strip("/"))
            missing = selected - available
            if missing:
                raise ValueError("Selected archive path not found: {}".format(next(iter(missing))))
            total_progress = sum(1 for path in available if path in selected)
        else:
            total_progress = len(entries)

        extracted_count = 0
        processed_count = 0
        for index, (raw_path, entry2) in enumerate(entries):
            if cancel_callback is not None and cancel_callback():
                raise InterruptedError("Unpacking cancelled")
            file_path = un_obfuscate_file_path(raw_path, len(raw_path), index, hdr.seed1_I, hdr.seed2_I)
            relative_path = file_path.decode(path_encoding)
            out_path = os.path.join(out_dirPath, relative_path)
            if entry2.type_B == DIR_TYPE:
                if selected is None:
                    os.makedirs(out_path, exist_ok=True)
                    _emit_log("[write] {}".format(out_path), log_callback)
                    processed_count += 1
                    if progress_callback is not None:
                        progress_callback(processed_count, total_progress, relative_path, extracted_count)
                continue

            normalized_path = relative_path.replace("\\", "/").strip("/")
            if selected is not None and normalized_path not in selected:
                continue

            if entry2.length_I:
                fp_in.seek(data_base + entry2.offset_I, 0)
                buf = fp_in.read(entry2.length_I)
                key = generate_file_key(file_path, len(file_path), entry2.originalLength_I,
                                        hdr.seed1_I, hdr.seed2_I, profile["key_constant"])
                un_obfuscate_len = min(len(buf), 0x1000 + len(file_path))
                buf = un_obfuscate(buf[:un_obfuscate_len], un_obfuscate_len, key, profile["table"]) + buf[un_obfuscate_len:]
            else:
                buf = b""
            if entry2.length_I != entry2.originalLength_I:
                obj = zlib.decompressobj()
                buf = obj.decompress(buf) + obj.flush()
                if len(buf) != entry2.originalLength_I:
                    raise ValueError("Decompress failed for '{}'".format(relative_path))

            if len(buf) >= 4 and buf[:4] == b"NPSI":
                raise RuntimeError("NPSI image conversion is not implemented: '{}'".format(relative_path))
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "wb") as fp_out:
                fp_out.write(buf)
            extracted_count += 1
            processed_count += 1
            _emit_log("[write] {}".format(out_path), log_callback)
            if progress_callback is not None:
                progress_callback(processed_count, total_progress, relative_path, extracted_count)
    _emit_log("[log] unpack '{}' finish!".format(in_filePath), log_callback)


def pack(in_dirPath: str, out_filePath: str, seed1_I: int = 0, seed2_I: int = 0, compress: bool = True):
    class NpaEntry:
        def __init__(self, _raw_file_path: str, _entry1: NpaEntry1, _file_path: bytes, _entry2: NpaEntry2):
            self.raw_file_path = _raw_file_path
            self.entry1 = _entry1
            self.file_path = _file_path
            self.entry2 = _entry2

    out_tmp_file_path = out_filePath + '.tmp'
    assert not os.path.exists(out_tmp_file_path), \
        "File exists: need to create '{0}' as a tmp file".format(out_tmp_file_path)
    # glob all files and dirs
    entry_lst = []
    file_count = 0
    offset = 0
    index = 0
    batch = 1
    # check first file batch num
    for root, dirs, files in os.walk(in_dirPath):
        if len(dirs) == 0:
            batch = 0
    with open(out_tmp_file_path, "wb") as out_fileTmpFp:
        for root, dirs, files in os.walk(in_dirPath):
            # add dir into Entry
            for _dir in dirs:
                # absolute raw path
                raw_dir_path = os.path.relpath(os.path.join(root, _dir), in_dirPath)
                # obfuscate path data
                dir_path = raw_dir_path.encode(FILE_PATH_ENCODING)
                dir_path = obfuscate_file_path(dir_path, len(dir_path), index, seed1_I, seed2_I)
                dir_path_length = len(dir_path)
                # add to entry
                entry_lst.append(NpaEntry(
                    _raw_file_path=raw_dir_path,
                    _entry1=NpaEntry1(dir_path_length),
                    _file_path=dir_path,
                    _entry2=NpaEntry2(type_B=DIR_TYPE, fileBatch_I=0, offset_I=0, length_I=0, originalLength_I=0)
                ))
                index += 1
                print("[pack]", raw_dir_path)
            # add file into Entry
            new_batch = batch
            for file in files:
                new_batch = batch + 1
                # absolute raw path
                raw_file_path = os.path.relpath(os.path.join(root, file), in_dirPath)
                # obfuscate path data
                file_original_length = os.path.getsize(os.path.join(root, file))
                file_path = raw_file_path.encode(FILE_PATH_ENCODING)
                file_path = obfuscate_file_path(file_path, len(file_path), index, seed1_I, seed2_I)
                file_path_length = len(file_path)
                # write to tmp file
                with open(os.path.join(in_dirPath, raw_file_path), "rb") as in_fileFp:
                    # read file
                    buf = in_fileFp.read()
                    # compress file
                    if compress:
                        obj = zlib.compressobj()
                        buf = obj.compress(buf) + obj.flush()
                    # obfuscate file
                    obfuscate_len = 0x1000 + file_path_length
                    if obfuscate_len > len(buf):
                        obfuscate_len = len(buf)
                    key = generate_file_key(raw_file_path.encode(FILE_PATH_ENCODING),
                                            file_path_length, file_original_length, seed1_I, seed2_I)
                    buf = obfuscate(buf[:obfuscate_len], obfuscate_len, key) + buf[obfuscate_len:]
                    file_length = len(buf)
                    # write file
                    out_fileTmpFp.write(buf)
                # add to entry
                entry_lst.append(NpaEntry(
                    _raw_file_path=raw_file_path,
                    _entry1=NpaEntry1(len(file_path)),
                    _file_path=file_path,
                    _entry2=NpaEntry2(type_B=FILE_TYPE, fileBatch_I=batch, offset_I=offset,
                                      length_I=file_length, originalLength_I=file_original_length)
                ))
                offset += file_length
                file_count += 1
                index += 1
                print("[pack]", raw_file_path)
            batch = new_batch
    entry_count = len(entry_lst)
    hdr = NpaHeader(NpaHeader.SIG, unknown1_I=1, seed1_I=seed1_I, seed2_I=seed2_I, unknown2_2s=b'\x01\x01',
                    entryCount_I=entry_count, dirCount_I=entry_count - file_count, fileCount_I=file_count,
                    unknown4_I=0, unknown5_I=0,
                    tocLength_I=sum([NpaEntry1.SIZE + len(item.file_path) + NpaEntry2.SIZE for item in entry_lst]))
    # pack
    with open(out_filePath, "wb") as out_fileFp:
        # write NpaHeader
        out_fileFp.write(hdr.pack())
        # write Entry
        for i in range(len(entry_lst)):
            out_fileFp.write(entry_lst[i].entry1.pack())
            out_fileFp.write(entry_lst[i].file_path)
            out_fileFp.write(entry_lst[i].entry2.pack())
        # write files(copy from tmp)
        with open(out_tmp_file_path, "rb") as in_fileTmpFp:
            buf = in_fileTmpFp.read(1024 * 1024)
            while len(buf) > 0:
                out_fileFp.write(buf)
                buf = in_fileTmpFp.read(1024 * 1024)
    os.remove(out_tmp_file_path)
    print("[log] pack '{}' finish!".format(in_dirPath))
