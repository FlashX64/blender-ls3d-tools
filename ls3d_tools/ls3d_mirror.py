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
    IntProperty,
    FloatProperty,
    FloatVectorProperty,
    PointerProperty
)


class LS3DMirrorProperties(bpy.types.PropertyGroup):
    area: PointerProperty(
        name="Reflected area",
        type=bpy.types.Object
    )

    back_color: FloatVectorProperty(
        name="Back Color",
        description="",
        subtype='COLOR',
        size=3
    )

    far_plane: FloatProperty(
        name="Far plane"
    )

    unknown: IntProperty(
        name="Unknown"
    )

class LS3D_PT_MirrorPanel(bpy.types.Panel):
    bl_label = "Mirror"
    bl_idname = "SCENE_PT_ls3d_mirror"
    bl_parent_id = "SCENE_PT_ls3d_object"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        obj = context.active_object
        props = obj.ls3d_props
        return props.mesh_type == 'MIRROR'

    def draw(self, context: bpy.types.Context) -> None:
        obj = context.active_object
        props = obj.ls3d_props
        mirror_props = props.mirror_props

        layout = self.layout
        row = layout.row()
        row.label(text="Reflected area")
        row.prop(mirror_props, "area", icon='CUBE', text="")

        layout.prop(mirror_props, "back_color")
        layout.prop(mirror_props, "far_plane")
        layout.prop(mirror_props, "unknown")