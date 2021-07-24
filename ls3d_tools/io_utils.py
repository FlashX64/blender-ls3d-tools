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
from typing import Tuple
from bmesh import new
from mathutils import Vector, Quaternion, Matrix
from bpy_extras.io_utils import axis_conversion

class IStream:
    def __init__(self, filepath):
        self.stream = open(filepath, "rb")

    def close(self) -> None:
        self.stream.close()

    def read(self, fmt):
        unpacked = struct.unpack(fmt, self.stream.read(struct.calcsize(fmt)))

        return unpacked[0] if len(unpacked) == 1 else unpacked

    def read_string(self, length: int, fallback: str = "") -> str:
        string = self.read(f"<{str(length)}s")

        try:
            return str(string, encoding='ascii', errors='ignore').strip(chr(0))
        except:
            return fallback

    def read_presized_string(self) -> str:
        return self.read_string(self.read("<B"))

    def read_vector3(self) -> Vector:
        vec = self.read("<3f")
        return Vector((vec[0], vec[2], vec[1]))

    def read_quaternion(self) -> Quaternion:
        quat = self.read("<4f")
        return Quaternion((quat[3], quat[0], quat[2], quat[1]))

    def read_matrix4x4(self) -> Matrix:
        mat = Matrix((self.read("4f"), self.read("4f"),
                      self.read("4f"), self.read("4f")))
        mat.transpose()

        return mat

    def read_face(self) -> Tuple[int, int, int]:
        face = self.read("<3H")
        return (face[2], face[1], face[0])


class OStream:
    def __init__(self, filepath):
        self.stream = open(filepath, "wb")

    def close(self) -> None:
        self.stream.close()

    def write(self, fmt: str, *data) -> None:
        packed = struct.pack(fmt, *data)

        self.stream.write(packed)

    def write_string(self, string: str) -> None:
        self.stream.write(bytearray(string, 'ascii'))

    def write_presized_string(self, string: str) -> None:
        self.write("<B", len(string))
        self.stream.write(bytearray(string, 'ascii'))

    def write_vector3(self, vec: Vector) -> None:
        packed = struct.pack("<3f", vec[0], vec[2], vec[1])

        self.stream.write(packed)

    def write_vector4(self, vec: Vector) -> None:
        packed = struct.pack("<4f", vec[0], vec[2], vec[1], 0)

        self.stream.write(packed)

    def write_quaternion(self, quat: Quaternion) -> None:
        packed = struct.pack("<4f", quat[1], quat[3], quat[2], quat[0])

        self.stream.write(packed)

    def write_matrix4x4(self, mat: Matrix) -> None:
        new_mat = mat.copy()
        new_mat.transpose()

        packed = struct.pack(
            "<16f", *new_mat[0], *new_mat[1], *new_mat[2], *new_mat[3])
        self.stream.write(packed)

    def write_face(self, face: Tuple[int, int, int]):
        packed = struct.pack("<3H", face[2], face[1], face[0])

        self.stream.write(packed)