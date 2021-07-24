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


class LS3DPortalProperties(bpy.types.PropertyGroup):
    flag_a: BoolProperty(
        name="Unknown",
        description="It seems that this option should always be checked for proper portal functionality",
        default=True
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

    unknown_a: FloatProperty()
    unknown_b: FloatProperty()
    color: FloatVectorProperty(
        subtype='COLOR',
        size=4
    )

class LS3D_PT_PortalPanel(bpy.types.Panel):
    bl_label = "Portal"
    bl_idname = "SCENE_PT_ls3d_portal"
    bl_parent_id = "SCENE_PT_ls3d_object"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        obj = context.active_object
        props = obj.ls3d_props
        return props.is_portal and obj.parent is not None and obj.parent.type == 'MESH' and props.mesh_type == obj.parent.ls3d_props.mesh_type and props.mesh_type == 'SECTOR'

    def draw(self, context: bpy.types.Context) -> None:
        obj = context.active_object
        props = obj.ls3d_props
        portal_props = props.portal_props

        layout = self.layout

        row = layout.row()
        row.label(text="Flags")
        row.prop(portal_props, "flag_a", text="")
        row.prop(portal_props, "flag_b", text="")
        row.prop(portal_props, "flag_c", text="")
        row.prop(portal_props, "flag_d", text="")
        layout.prop(portal_props, "unknown_a")
        layout.prop(portal_props, "unknown_b")
        layout.prop(portal_props, "unknown_c")
        layout.prop(portal_props, "color")
