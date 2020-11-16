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

import bpy
from bpy.props import (
    BoolProperty,
    IntProperty,
    FloatProperty,
    FloatVectorProperty
)


class LS3DSectorProperties(bpy.types.PropertyGroup):
    flag_a: BoolProperty(
        name="Unknown",
        default=False
    )

    flag_b: BoolProperty(
        name="Unknown",
        default=False
    )

    flag_c: BoolProperty(
        name="Unknown",
        default=False
    )

    flag_d: BoolProperty(
        name="Unknown",
        default=False
    )

    flag_e: BoolProperty(
        name="Unknown",
        default=False
    )

    unknown: IntProperty(
        name="Unknown"
    )