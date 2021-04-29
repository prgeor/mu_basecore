# @file
#
# Formats a collection of intermediate OEM data binary files
# in a given directory into a single OEM binary file
#
# Copyright (C) Microsoft Corporation. All rights reserved.
#
##

import glob
import io
import os
import sys
import struct
from collections import namedtuple


class OemDataFormatter:
    STRUCT_SIGNATURE = b"__SDSH__"
    ITEM_SIGNATURE = b"_SDDATA_"
    OEM_ID = b"__MSFT__"

    def __init__(self, directory_path):
        if not os.path.isdir(directory_path):
            raise NotADirectoryError(
                f"{directory_path} is an invalid directory!")

        self._directory_path = directory_path

    def _get_bins(self):
        return glob.glob(os.path.join(self._directory_path, '*.oemdatabin.i'))

    def _get_signed_item(self, file_path):
        with open(file_path, 'rb') as bin_file:
            bin_data = bytearray(bin_file.read())

        signed_item_pos = 0
        while True:
            signed_item_pos = bin_data.find(
                self.ITEM_SIGNATURE, signed_item_pos)

            if signed_item_pos == -1:
                return

            ItemHeader = namedtuple('ItemHeader', 'sig header_len id len')

            item_header = ItemHeader._make(struct.unpack_from(
                '<QHHI', bin_data, signed_item_pos))

            print(f"Signed data item found")
            print(f"  Item ID: {item_header.id}")
            print(f"  Item Length: {item_header.len} bytes")

            signed_item = bin_data[signed_item_pos:signed_item_pos +
                                   item_header.header_len + item_header.len]

            yield signed_item
            signed_item_pos += (item_header.header_len + item_header.len)

    def _get_signed_structure(self):
        signed_items = [i for b in self._get_bins() for i in
                        self._get_signed_item(b)]

        StructureHeader = namedtuple('StructureHeader',
                                     'sig rev header_len oem_id desc_count')

        struct_header = StructureHeader(
                        self.STRUCT_SIGNATURE,
                        1,
                        26,
                        self.OEM_ID,
                        len(signed_items))

        struct_header_data = struct.pack('<8sHI8sI', *struct_header)

        with io.BytesIO() as out_buffer:
            out_buffer.write(struct_header_data)
            for item in signed_items:
                # Note: Just keep things packed tight for now
                # aligned_boundary = (((~out_buffer.tell()) + 1) &
                #                     self.ITEM_ALIGNMENT - 1)
                # out_buffer.seek(out_buffer.tell() + aligned_boundary)
                out_buffer.write(item)
            return out_buffer.getvalue()

    def get_file_data(self):
        return {f: list(self._get_signed_item(f)) for f in self._get_bins()}

    def write_data(self, out_file_path):
        with open(out_file_path, 'wb') as out_bin_file:
            out_bin_file.write(self._get_signed_structure())


# Todo: Clean up arg parsing, documentation, logger, etc.
if __name__ == '__main__':
    oem_data = OemDataFormatter(sys.argv[1])
    oem_data.write_data(os.path.join(sys.argv[1], 'data.oemdatabin'))
