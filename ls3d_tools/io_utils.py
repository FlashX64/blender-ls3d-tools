# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  version 2 as published by the Free Software Foundation.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import struct
from collections.abc import Iterable
from dataclasses import dataclass

class IStream:
    def __init__(self, filepath):
        self.stream = open(filepath, "rb")

    def close(self):
        self.stream.close()

    def read(self, fmt):
        unpacked = struct.unpack(fmt, self.stream.read(struct.calcsize(fmt)))
        
        return unpacked[0] if len(unpacked) == 1 else unpacked

    def read_string(self, length, fallback: 'str' = ""):
        string = self.read(f"<{str(length)}s")

        try:
            return str(string, encoding='ascii', errors='ignore').strip(chr(0))
        except:
            return fallback

    def read_presized_string(self):
        return self.read_string(self.read("<B"))

    def read_vector3(self):
        vec = self.read("<3f")
        return (vec[0], vec[2], vec[1])

    def read_quaternion(self):
        quat = self.read("<4f")
        return (quat[3], quat[0], quat[2], quat[1])

    def read_face(self):
        face = self.read("<3H")
        return (face[2], face[1], face[0])

class OStream:
    def __init__(self, filepath):
        self.stream = open(filepath, "wb")

    def close(self):
        self.stream.close()

    def write(self, fmt, *data):
        packed = struct.pack(fmt, *data)
        
        self.stream.write(packed)

    def write_string(self, string):
        self.stream.write(bytearray(string, 'ascii'))

    def write_presized_string(self, string):
        self.write("<B", len(string))
        self.stream.write(bytearray(string, 'ascii'))

    def write_vector3(self, vec):
        packed = struct.pack("<3f", vec[0], vec[2], vec[1])

        self.stream.write(packed)

    def write_vector4(self, vec):
        packed = struct.pack("<4f", vec[0], vec[2], vec[1], 0)

        self.stream.write(packed)

    def write_quaternion(self, quat):
        packed = struct.pack("<4f", quat[1], quat[3], quat[2], quat[0])

        self.stream.write(packed)

    def write_face(self, face):
        packed = struct.pack("<3H", face[2], face[1], face[0])

        self.stream.write(packed)