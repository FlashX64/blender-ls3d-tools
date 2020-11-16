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
    IntProperty
)

class LS3DTargetProperty(bpy.types.PropertyGroup):
    unknown: IntProperty(
        name="Unknown"
    )

class LS3D_UL_ls3d_targets(bpy.types.UIList):
    def draw_item(self, _context, layout, _data, item, icon, _active_data, _active_propname, _index):
        target = item
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if target:
                row = layout.row()
                row.prop(target, "unknown", text="", emboss=False, icon_value=icon)
            else:
                layout.label(text="", icon_value=icon)
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)

class LS3DAddTarget(bpy.types.Operator):
    bl_idname = "object.ls3d_target_add"
    bl_label = "Add target slot"
    bl_description = "Add a new target slot"

    @classmethod
    def poll(self, context):
        return context.active_object != None

    def execute(self, context):
        obj = context.active_object

        ls3d_props = obj.ls3d_props

        ls3d_props.targets.add()
        ls3d_props.active_target_index = len(ls3d_props.targets) - 1

        return {'FINISHED'}

class LS3DRemoveTarget(bpy.types.Operator):
    bl_idname = "object.ls3d_target_remove"
    bl_label = "Remove target slot"
    bl_description = "Remove the selected target slot"

    @classmethod
    def poll(self, context):
        return context.active_object != None

    def execute(self, context):
        obj = context.active_object

        ls3d_props = obj.ls3d_props

        ls3d_props.targets.remove(ls3d_props.active_target_index)

        if ls3d_props.active_target_index >= len(ls3d_props.targets):
            ls3d_props.active_target_index = len(ls3d_props.targets) - 1

        if ls3d_props.active_target_index < 0:
            ls3d_props.active_target_index = 0

        return {'FINISHED'}