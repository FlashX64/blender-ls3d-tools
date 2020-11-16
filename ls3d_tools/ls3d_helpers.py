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

def show_hide_by_type(mesh_type, state):
    objects = bpy.context.scene.objects

    for obj in objects:
        if obj.type == 'MESH':
            props = obj.ls3d_props

            if props.mesh_type == mesh_type:
                obj.hide_viewport = state

def show_hide_sectors(state, portals):
    objects = bpy.context.scene.objects

    for obj in objects:
        if obj.type == 'MESH':
            props = obj.ls3d_props

            if props.mesh_type == 'SECTOR' and props.is_portal == portals:
                obj.hide_viewport = state

def show_hide_lods(state):
    objects = bpy.context.scene.objects

    for obj in objects:
        if obj.type == 'MESH':
            props = obj.ls3d_props

            if props.is_lod and (props.mesh_type == 'STANDARD' or props.mesh_type == 'BILLBOARD' or props.mesh_type == 'SINGLE' or props.mesh_type == 'MORPH' or props.mesh_type == 'SINGLE_MORPH'):
                obj.hide_viewport = state

class LS3DHidePortals(bpy.types.Operator):
    bl_idname = "object.ls3d_hide_portals"
    bl_label = "Hide portals"
    bl_description = "Hide all portal meshes in the scene"

    def execute(self, context):
        show_hide_sectors(True, True)

        return {'FINISHED'}

class LS3DShowPortals(bpy.types.Operator):
    bl_idname = "object.ls3d_show_portals"
    bl_label = "Show portals"
    bl_description = "Show all portal meshes in the scene"

    def execute(self, context):
        show_hide_sectors(False, True)

        return {'FINISHED'}

class LS3DHideSectors(bpy.types.Operator):
    bl_idname = "object.ls3d_hide_sectors"
    bl_label = "Hide sectors"
    bl_description = "Hide all sector meshes in the scene"

    def execute(self, context):
        show_hide_sectors(True, False)

        return {'FINISHED'}

class LS3DShowSectors(bpy.types.Operator):
    bl_idname = "object.ls3d_show_sectors"
    bl_label = "Show sectors"
    bl_description = "Show all sector meshes in the scene"

    def execute(self, context):
        show_hide_sectors(False, False)

        return {'FINISHED'}

class LS3DHideOccluders(bpy.types.Operator):
    bl_idname = "object.ls3d_hide_occluders"
    bl_label = "Hide occluders"
    bl_description = "Hide all occluder meshes in the scene"

    def execute(self, context):
        show_hide_by_type('OCCLUDER', True)

        return {'FINISHED'}

class LS3DShowOccluders(bpy.types.Operator):
    bl_idname = "object.ls3d_show_occluders"
    bl_label = "Show occluders"
    bl_description = "Show all occluder meshes in the scene"

    def execute(self, context):
        show_hide_by_type('OCCLUDER', False)

        return {'FINISHED'}

class LS3DHideLods(bpy.types.Operator):
    bl_idname = "object.ls3d_hide_lods"
    bl_label = "Hide LODs"
    bl_description = "Hide all LOD meshes in the scene"

    def execute(self, context):
        show_hide_lods(True)

        return {'FINISHED'}

class LS3DShowLods(bpy.types.Operator):
    bl_idname = "object.ls3d_show_lods"
    bl_label = "Show LODs"
    bl_description = "Show all LOD meshes in the scene"

    def execute(self, context):
        show_hide_lods(False)

        return {'FINISHED'}

class LS3D_PT_HelperPanel(bpy.types.Panel):
    bl_label = "LS3D Helpers"
    bl_idname = "SCENE_PT_ls3d_helpers"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "world"

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.operator("object.ls3d_hide_sectors", icon='HIDE_ON')
        row.operator("object.ls3d_show_sectors", icon='HIDE_OFF')

        row = layout.row(align=True)
        row.operator("object.ls3d_hide_portals", icon='HIDE_ON')
        row.operator("object.ls3d_show_portals", icon='HIDE_OFF')

        row = layout.row(align=True)
        row.operator("object.ls3d_hide_occluders", icon='HIDE_ON')
        row.operator("object.ls3d_show_occluders", icon='HIDE_OFF')

        row = layout.row(align=True)
        row.operator("object.ls3d_hide_lods", icon='HIDE_ON')
        row.operator("object.ls3d_show_lods", icon='HIDE_OFF')