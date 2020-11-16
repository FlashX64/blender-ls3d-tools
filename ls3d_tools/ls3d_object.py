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
        StringProperty,
        IntProperty,
        BoolProperty,
        FloatProperty,
        EnumProperty,
        CollectionProperty,
        PointerProperty
        )

from mathutils import Matrix, Vector

from .ls3d_sector import LS3DSectorProperties
from .ls3d_portal import LS3DPortalProperties
from .ls3d_mirror import LS3DMirrorProperties
from .ls3d_lens import LS3DLensProperty
from .ls3d_target import LS3DTargetProperty

class LS3DObjectProperty(bpy.types.PropertyGroup):
    content: StringProperty(maxlen=255)

class LS3D_UL_ls3d_props(bpy.types.UIList):
    def draw_item(self, _context, layout, _data, item, icon, _active_data, _active_propname, _index):
        prop = item
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if prop:
                layout.prop(prop, "content", text="", emboss=False, icon_value=icon)
            else:
                layout.label(text="", icon_value=icon)
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)

class LS3DObjectProperties(bpy.types.PropertyGroup):
    mesh_type: EnumProperty(
        name="Mesh Type",
        description="LS3D mesh type",
        default='STANDARD',
        items=[
            ('MIRROR', "Mirror", "The mesh represents a reflective surface"),
            ('OCCLUDER', "Occluder", "The mesh represents a occluder primitive"),
            ('SECTOR', "Sector", "The mesh represents a sector primitive or a portal primitive linked to a sector"),
            ('BILLBOARD', "Billboard", "The mesh always faces the camera"),
            ('SINGLE_MORPH', "Single morph", "The mesh represents a skin of an armature, to which is linked and its vertices are animated"),
            ('MORPH', "Morph", "The mesh vertices are animated"),
            ('SINGLE', "Single", "The mesh represents a skin of an armature, to which is linked"),
            ('STANDARD', "Standard", "Standard mesh")
        ]
    )

    visual_flag_a: BoolProperty(
        name="Depth Bias",
        description="Depth bias helps coplanar polygons to appear as if they are not coplanar. This mesh will be rendered on top of the second mesh with which it has coplanar polygons.",
        default=False
    )

    visual_flag_b: BoolProperty(
        name="Dynamic Shadows",
        description="Dynamic shadows are projected onto the mesh surface",
        default=True
    )
    
    visual_flag_c: BoolProperty(
        name="Unknown",
        default=False
    )

    visual_flag_d: BoolProperty(
        name="Unknown",
        description="It seems that this option should always be checked",
        default=True
    )

    visual_flag_e: BoolProperty(
        name="Unknown",
        default=False
    )

    visual_flag_f: BoolProperty(
        name="Decals Projection",
        description="Decal textures (bullet holes, blood splatters, footprints) can be projected onto the mesh surface",
        default=True
    )

    visual_flag_g: BoolProperty(
        name="No Fog",
        description="No fog is applied to the mesh",
        default=False
    )

    culling_flag_a: BoolProperty(
        name="Enabled",
        description="Enable mesh rendering",
        default=True
    )

    culling_flag_b: BoolProperty(
        name="Unknown",
        description=""
    )

    culling_flag_c: BoolProperty(
        name="Unknown",
        description="",
        default=True
    )

    culling_flag_d: BoolProperty(
        name="Unknown",
        description=""
    )

    culling_flag_e: BoolProperty(
        name="Unknown",
        description=""
    )

    helper_type: EnumProperty(
        name="Helper Type",
        description="LS3D helper object type",
        default='DUMMY',
        items=[
            ('TARGET', "Target", "Object represents a target object"),
            ('DUMMY', "Dummy", "Object represents a dummy object")
        ]
    )

    draw_distance: FloatProperty(
        name="Draw Distance",
        description="Distance in which this geometry is swapped for a lower LOD. For last LODs this value should be zero, otherwise it disappears",
        subtype='DISTANCE',
        min=0.0
    )

    is_lod: BoolProperty(
        name="LOD",
        description="Marks this child object as a level of detail",
        default=False
    )

    is_portal: BoolProperty(
        name="Portal",
        description="Marks this child object as a portal",
        default=False
    )

    sector_props: PointerProperty(type=LS3DSectorProperties)
    portal_props: PointerProperty(type=LS3DPortalProperties)
    mirror_props: PointerProperty(type=LS3DMirrorProperties)

    user_defined_properties: CollectionProperty(type=LS3DObjectProperty)
    active_property_index: IntProperty()

    lenses: CollectionProperty(type=LS3DLensProperty)
    active_lens_index: IntProperty()

    target_unknown: IntProperty(
        name="Unknown",
        default=1
    )
    
    targets: CollectionProperty(type=LS3DTargetProperty)
    active_target_index: IntProperty()

    billboarding_axis: EnumProperty(
        name="Billboarding axis",
        default='Y',
        items=[
            ('X', "X", "The mesh faces the camera on X axis"),
            ('Y', "Y", "The mesh faces the camera on Y axis"),
            ('Z', "Z", "The mesh faces the camera on Z axis"),
            ('XYZ', "XYZ", "The mesh faces the camera on XYZ axis")
        ]
    )

    #dummy_display_size_y: FloatProperty(
    #    name="Empty Display Size",
    #    description="Size of display for empties (not shown in the viewport)",
    #    subtype='DISTANCE',
    #    min=0.01,
    #    max=1000.0,
    #    step=0.01
    #)
    
    #dummy_display_size_z: FloatProperty(
    #    name="Empty Display Size",
    #    description="Size of display for empties (not shown in the viewport)",
    #    subtype='DISTANCE',
    #    min=0.01,
    #    max=1000.0,
    #    step=0.01
    #)

class LS3DAddProperty(bpy.types.Operator):
    bl_idname = "object.ls3d_property_add"
    bl_label = "Add property slot"
    bl_description = "Add a new property slot"

    @classmethod
    def poll(self, context):
        return context.active_object != None

    def execute(self, context):
        obj = context.active_object

        ls3d_props = obj.ls3d_props

        ls3d_props.user_defined_properties.add()
        ls3d_props.active_property_index = len(ls3d_props.user_defined_properties) - 1

        return {'FINISHED'}

class LS3DRemoveProperty(bpy.types.Operator):
    bl_idname = "object.ls3d_property_remove"
    bl_label = "Remove property slot"
    bl_description = "Remove the selected property slot"

    @classmethod
    def poll(self, context):
        return context.active_object != None

    def execute(self, context):
        obj = context.active_object

        ls3d_props = obj.ls3d_props

        ls3d_props.user_defined_properties.remove(ls3d_props.active_property_index)

        if ls3d_props.active_property_index >= len(ls3d_props.user_defined_properties):
            ls3d_props.active_property_index = len(ls3d_props.user_defined_properties) - 1

        if ls3d_props.active_property_index < 0:
            ls3d_props.active_property_index = 0

        return {'FINISHED'}

class LS3DDistanceFromCamera(bpy.types.Operator):
    bl_idname = "object.ls3d_distance_from_camera"
    bl_label = "Distance from camera"
    bl_description = "Set the draw distance to the current distance from the camera"

    @classmethod
    def poll(self, context):
        return context.active_object != None

    def execute(self, context):
        obj = context.active_object

        props = obj.ls3d_props

        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                region = area.spaces[0].region_3d
                if region:
                    cam_pos = region.view_matrix.inverted().to_translation()

                    dist = (obj.location - cam_pos).length
                    props.draw_distance = dist

        return {'FINISHED'}

def is_ls3d_mesh(obj):
    props = obj.ls3d_props
    return props.mesh_type == 'STANDARD' or props.mesh_type == 'BILLBOARD' or props.mesh_type == 'SINGLE' or props.mesh_type == 'MORPH' or props.mesh_type == 'SINGLE_MORPH'

def is_ls3d_visual(obj):
    props = obj.ls3d_props
    return obj.type == 'MESH' and (props.mesh_type != 'SECTOR' or props.mesh_type == 'OCCLUDER')

class LS3D_PT_ObjectPanel(bpy.types.Panel):
    bl_label = "LS3D Object"
    bl_idname = "SCENE_PT_ls3d_object"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"

    @classmethod
    def poll(self, context):
        return context.active_object is not None

    def draw(self, context):
        obj = context.active_object
        props = obj.ls3d_props

        layout = self.layout

        if obj:
            if obj.type == 'MESH':
                is_mesh = is_ls3d_mesh(obj)

                if not is_mesh or not props.is_lod:
                    layout.prop(props, "mesh_type", icon='MESH_DATA')

                is_loddable = False
                is_portalable = False

                if is_mesh:
                    row = layout.row()
                    row.prop(props, "draw_distance")
                    row.operator("object.ls3d_distance_from_camera", icon='CAMERA_DATA', text="")

                if obj.parent is not None and obj.parent.type == 'MESH':
                    parent_props = obj.parent.ls3d_props

                    if is_mesh:
                        is_loddable = True
                    else:
                        if parent_props.mesh_type == props.mesh_type:
                            if props.mesh_type == 'SECTOR':
                                is_portalable = True

                # Visual flags
                if is_ls3d_visual(obj) and not props.is_lod:
                    row = layout.row(align=True)
                    row.label(text="Visual Flags")
                    row.prop(props, "visual_flag_a", text="")
                    row.prop(props, "visual_flag_b", text="")
                    row.prop(props, "visual_flag_c", text="")
                    row.prop(props, "visual_flag_d", text="")
                    row.prop(props, "visual_flag_e", text="")
                    row.prop(props, "visual_flag_f", text="")
                    row.prop(props, "visual_flag_g", text="")

                # Culling flags
                if (not is_loddable or not props.is_lod) and (not is_portalable or not props.is_portal):
                    row = layout.row(align=True)
                    row.label(text="Culling Flags")
                    row.prop(props, "culling_flag_a", text="")
                    row.prop(props, "culling_flag_b", text="")
                    row.prop(props, "culling_flag_c", text="")
                    row.prop(props, "culling_flag_d", text="")
                    row.prop(props, "culling_flag_e", text="")

                if is_loddable:
                    layout.prop(props, "is_lod")

                if is_portalable:
                    layout.prop(props, "is_portal")
                elif props.mesh_type == 'SECTOR':
                    row = layout.row(align=True)

                    sector_props = props.sector_props

                    row.label(text="Sector Flags")
                    row.prop(sector_props, "flag_a", text="")
                    row.prop(sector_props, "flag_b", text="")
                    row.prop(sector_props, "flag_c", text="")
                    row.prop(sector_props, "flag_d", text="")
                    row.prop(sector_props, "flag_e", text="")

                    row = layout.row()
                    row.label(text="Sector Unknown")
                    row.prop(sector_props, "unknown", text="")

                if props.mesh_type == 'BILLBOARD':
                    row = layout.row()
                    row.label(text="Billboarding axis")
                    row.prop(props, "billboarding_axis", icon='EMPTY_AXIS', text="")

            # Lenses
            elif obj.type == 'LIGHT':
                is_sortable = len(props.lenses) > 1
                rows = 3
                if is_sortable:
                    rows = 5

                layout.label(text="Lenses")
                row = layout.row()
                row.template_list("LS3D_UL_ls3d_lenses", "", props, "lenses", props, "active_lens_index", rows=rows)

                col = row.column(align=True)
                col.operator("object.ls3d_lens_add", icon='ADD', text="")
                col.operator("object.ls3d_lens_remove", icon='REMOVE', text="")
            elif obj.type == 'EMPTY':
                layout.prop(props, "helper_type")

                if props.helper_type == 'DUMMY':
                    row = layout.row(align=True)
                    row.label(text="Display size")
                    row.prop(obj, "empty_display_size", text="")
                elif props.helper_type == 'TARGET':
                    is_sortable = len(props.targets) > 1
                    rows = 3
                    if is_sortable:
                        rows = 5

                    layout.label(text="Targets")
                    layout.prop(props, "target_unknown")
                    row = layout.row()
                    row.template_list("LS3D_UL_ls3d_targets", "", props, "targets", props, "active_target_index", rows=rows)

                    col = row.column(align=True)
                    col.operator("object.ls3d_target_add", icon='ADD', text="")
                    col.operator("object.ls3d_target_remove", icon='REMOVE', text="")


            # Portals
            if not props.is_lod and not props.is_portal:
                is_sortable = len(props.user_defined_properties) > 1
                rows = 3
                if is_sortable:
                    rows = 5

                layout.label(text="User defined properties")
                row = layout.row()
                row.template_list("LS3D_UL_ls3d_props", "", props, "user_defined_properties", props, "active_property_index", rows=rows)

                col = row.column(align=True)
                col.operator("object.ls3d_property_add", icon='ADD', text="")
                col.operator("object.ls3d_property_remove", icon='REMOVE', text="")