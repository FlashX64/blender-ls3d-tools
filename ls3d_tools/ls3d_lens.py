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

from typing import Set
import bpy
from bpy.props import (
    FloatProperty,
    PointerProperty
)
from bpy.types import AnyType

class LS3DLensProperty(bpy.types.PropertyGroup):
    unknown_a: FloatProperty(
        name="Unknown"
    )
    
    unknown_b: FloatProperty(
        name="Unknown"
    )

    material: PointerProperty(
        name="Material",
        type=bpy.types.Material,
        )

class LS3D_UL_ls3d_lenses(bpy.types.UIList):
    def draw_item(self, _context: bpy.types.Context, layout: bpy.types.UILayout, _data: AnyType, item: LS3DLensProperty, icon: int, _active_data: AnyType, _active_propname: str, _index: int) -> None:
        lens = item
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if lens:
                split = layout.split()

                col = split.column()
                col.prop(lens, "material", text="", emboss=True, icon_only=True)
                col = split.column()
                row = col.row()
                row.prop(lens, "unknown_a", text="", emboss=False, icon_value=icon)
                row.prop(lens, "unknown_b", text="", emboss=False, icon_value=icon)
            else:
                layout.label(text="", icon_value=icon)
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)

class LS3DAddLens(bpy.types.Operator):
    bl_idname = "object.ls3d_lens_add"
    bl_label = "Add lens slot"
    bl_description = "Add a new lens slot"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return context.active_object != None

    def execute(self, context: bpy.types.Context) -> Set[str]:
        obj = context.active_object

        ls3d_props = obj.ls3d_props

        ls3d_props.lenses.add()
        ls3d_props.active_lens_index = len(ls3d_props.lenses) - 1

        return {'FINISHED'}

class LS3DRemoveLens(bpy.types.Operator):
    bl_idname = "object.ls3d_lens_remove"
    bl_label = "Remove lens slot"
    bl_description = "Remove the selected lens slot"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return context.active_object != None

    def execute(self, context: bpy.types.Context) -> Set[str]:
        obj = context.active_object

        ls3d_props = obj.ls3d_props

        ls3d_props.lenses.remove(ls3d_props.active_lens_index)

        if ls3d_props.active_lens_index >= len(ls3d_props.lenses):
            ls3d_props.active_lens_index = len(ls3d_props.lenses) - 1

        if ls3d_props.active_lens_index < 0:
            ls3d_props.active_lens_index = 0

        return {'FINISHED'}