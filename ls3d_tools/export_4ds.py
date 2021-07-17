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
import bmesh
from mathutils import Vector, Matrix
from mathutils.geometry import normal
from datetime import datetime

from .io_utils import OStream
from .ls3d_object import is_ls3d_mesh
from ._4ds_utils import *

def get_root_objects():
    root_objects = []
    root_armatures = []

    for obj in bpy.context.scene.collection.all_objects:
        if not obj.parent:
            if obj.type == 'MESH' or obj.type == 'EMPTY' or (obj.type == 'LIGHT' and len(obj.ls3d_props.lenses) > 0):
                root_objects.append(obj)
            elif obj.type == 'ARMATURE':
                root_armatures.append(obj)

    return root_objects, root_armatures

def create_ls3d_sector(ls3d_obj):
    children = []
    portals = []

    bl_obj = ls3d_obj.bl_obj

    # Gather and sort all child objects and portals
    for child in bl_obj.children:
        props = child.ls3d_props

        if not (props.mesh_type == 'SECTOR' and props.is_portal): # Child object is not portal
            children.append(child)
            continue

        p_props = props.portal_props

        p_flags = 0
        if p_props.flag_a:
            p_flags |= PortalFlags.UNKNOWN0
        if p_props.flag_b:
            p_flags |= PortalFlags.UNKNOWN1
        if p_props.flag_c:
            p_flags |= PortalFlags.UNKNOWN2
        if p_props.flag_d:
            p_flags |= PortalFlags.UNKNOWN3

        unk0 = p_props.unknown_a
        unk1 = p_props.unknown_b

        # Continue if mesh has not polygons
        if len(child.data.polygons) == 0:
            continue

        polygon = child.data.polygons[0]
        vertices = child.data.vertices

        local = child.matrix_local

        positions = []
        for vert_index in polygon.vertices:
            pos = (local @ Matrix.Translation(vertices[vert_index].co)).to_translation()

            positions.append(Vector((pos.x, pos.z, pos.y)))

        p_normal = normal(positions)
        p_dist = -p_normal.dot(positions[0])

        portal = Portal(
            p_flags,
            unk0,
            unk1,
            0,0,0,0,
            positions,
            p_normal,
            p_dist
        )

        portals.append(portal)

    # Gather info about sector
    props = bl_obj.ls3d_props

    ls3d_mesh = Sector()
    ls3d_mesh.portals = portals

    ls3d_obj.mesh = ls3d_mesh
    ls3d_obj.children = children

def create_ls3d_standard_mesh(ls3d_obj, visual_type):
    bl_mesh = ls3d_obj.bl_obj.data

    children = []

    instanced = False

    if visual_type == VisualType.STANDARD_MESH:
        ls3d_mesh = StandardMesh()
    elif visual_type == VisualType.BILLBOARD:
        ls3d_mesh = Billboard()
    elif visual_type == VisualType.SINGLE_MESH:
        ls3d_mesh = SingleMesh()
    elif visual_type == VisualType.MORPH:
        ls3d_mesh = Morph()
    elif visual_type == VisualType.SINGLE_MORPH:
        ls3d_mesh = SingleMorph()


    def get_all_used_mats(bl_mesh_data):
        if len(bl_mesh_data.materials) > 0:
            mats = bl_mesh_data.materials
            for polygon in bl_mesh_data.polygons:
                mat = mats[polygon.material_index]
                if mat not in Libraries.Materials:
                    Libraries.Materials.append(mat)

    get_all_used_mats(bl_mesh)

    ls3d_mesh.lods = None

    # Look up in already exported mesh instances
    # If found, the mesh is an instance of already exported mesh
    if bl_mesh in Libraries.MeshInstances:
        instanced = True

        mesh_index = Libraries.MeshInstances.index(bl_mesh)
        base_obj = Libraries.MeshInstancesParents[mesh_index]
        ls3d_mesh.instance_index = Libraries.Objects.index(base_obj) + 1
    else:
        ls3d_mesh.instance_index = 0
        base_obj = ls3d_obj
        Libraries.MeshInstances.append(bl_mesh)
        Libraries.MeshInstancesParents.append(ls3d_obj)

    ls3d_obj.mesh = ls3d_mesh

    lods = []

    def get_lods(bl_obj, level):
        """Get all lods recursively"""
        for child in bl_obj.children:
            if child.ls3d_props.is_lod:
                if len(lods) == level: # We cannot assign more than one LOD to each level
                    lods.append(child)
                    get_lods(child, level + 1)

                    get_all_used_mats(child.data)
            elif level == 0: # Children must be only on the top level
                children.append(child)

    get_lods(ls3d_obj.bl_obj, 0)
    ls3d_obj.children = children

    if len(lods) > 0:
        if instanced:
            # Create a new LOD hierarchy, if it doesn't have any yet (for instanced meshes)
            if base_obj.mesh.lods is None:
                base_obj.mesh.lods = lods
        else:
            ls3d_mesh.lods = lods

def create_ls3d_mirror(ls3d_obj):
    ls3d_obj.mesh = Mirror()

    bl_obj = ls3d_obj.bl_obj
    refl_axis = bl_obj.ls3d_props.mirror_props.reflection_axis

    if refl_axis:
        children = []

        for child in bl_obj.children:
            if child != refl_axis:
                children.append(child)

        ls3d_obj.children = children
    else:
        ls3d_obj.children = bl_obj.children

def create_ls3d_lens(ls3d_obj):
    ls3d_obj.mesh = Lens()

    bl_obj = ls3d_obj.bl_obj
    ls3d_obj.children = bl_obj.children

    lenses = bl_obj.ls3d_props.lenses
    for lens in lenses:
        mat = lens.material
        if mat:
            if mat not in Libraries.Materials:
                Libraries.Materials.append(mat)

def create_ls3d_object(bl_obj, ls3d_parent):
    props = bl_obj.ls3d_props

    print(f"Exporting {bl_obj.name}")

    def get_obj_and_visual_type():
        if bl_obj.type == 'MESH':
            mesh_type = props.mesh_type

            if mesh_type == 'STANDARD':
                return ObjectType.VISUAL, VisualType.STANDARD_MESH
            elif mesh_type == 'SECTOR':
                return ObjectType.SECTOR, None
            elif mesh_type == 'OCCLUDER':
                return ObjectType.OCCLUDER, None
            elif mesh_type == 'BILLBOARD':
                return ObjectType.VISUAL, VisualType.BILLBOARD
            elif mesh_type == 'SINGLE':
                return ObjectType.VISUAL, VisualType.SINGLE_MESH
            elif mesh_type == 'SINGLE_MORPH':
                return ObjectType.VISUAL, VisualType.SINGLE_MORPH
            elif mesh_type == 'MORPH':
                return ObjectType.VISUAL, VisualType.MORPH
            elif mesh_type == 'MIRROR':
                return ObjectType.VISUAL, VisualType.MIRROR

        elif bl_obj.type == 'LIGHT':
            return ObjectType.VISUAL, VisualType.LENS
        elif bl_obj.type == 'EMPTY' and props.helper_type == 'TARGET':
            return ObjectType.TARGET, None
        else:
            return ObjectType.DUMMY, None

    obj_type, visual_type = get_obj_and_visual_type()

    parent_index = 0

    if ls3d_parent:
        parent_index = Libraries.Objects.index(ls3d_parent) + 1

    visual_flags = 0

    # Extracting visual flags
    if props.visual_flag_a:
        visual_flags |= VisualFlags.DEPTH_BIAS
    if props.visual_flag_b:
        visual_flags |= VisualFlags.DYNAMIC_SHADOWS
    if props.visual_flag_c:
        visual_flags |= VisualFlags.UNKNOWN0
    if props.visual_flag_d:
        visual_flags |= VisualFlags.UNKNOWN1
    if props.visual_flag_e:
        visual_flags |= VisualFlags.UNKNOWN2
    if props.visual_flag_f:
        visual_flags |= VisualFlags.DECALS
    if props.visual_flag_g:
        visual_flags |= VisualFlags.NO_FOG

    culling_flags = 0

    # Extracting culling flags
    if props.culling_flag_a:
        culling_flags |= CullingFlags.ENABLED
    if props.culling_flag_b:
        culling_flags |= CullingFlags.UNKNOWN1
    if props.culling_flag_c:
        culling_flags |= CullingFlags.UNKNOWN2
    if props.culling_flag_d:
        culling_flags |= CullingFlags.UNKNOWN3
    if props.culling_flag_e:
        culling_flags |= CullingFlags.UNKNOWN4

    properties = ""

    for prop in props.user_defined_properties:
        if properties != "":
            properties += '\r\n'

        properties += prop.content

    rotation_mode = bl_obj.rotation_mode
    bl_obj.rotation_mode = 'QUATERNION'

    ls3d_obj = LS3DObject(
        obj_type,
        visual_type,
        visual_flags,
        parent_index,
        bl_obj.matrix_local.to_translation(),
        bl_obj.matrix_local.to_quaternion(),
        bl_obj.matrix_local.to_scale(),
        0,
        culling_flags,
        bl_obj.name.replace(".", "_"),
        properties
        )

    bl_obj.rotation_mode = rotation_mode
    ls3d_obj.bl_obj = bl_obj

    # Create ls3d meshes depending on the object type and visual type
    if obj_type == ObjectType.VISUAL:
        if (visual_type == VisualType.STANDARD_MESH or
            visual_type == VisualType.BILLBOARD or
            visual_type == VisualType.SINGLE_MESH or
            visual_type == VisualType.MORPH or
            visual_type == VisualType.SINGLE_MORPH):
            create_ls3d_standard_mesh(ls3d_obj, visual_type)
        elif visual_type == VisualType.LENS:
            create_ls3d_lens(ls3d_obj)
        elif visual_type == VisualType.MIRROR:
            create_ls3d_mirror(ls3d_obj)
    elif obj_type == ObjectType.DUMMY:
        ls3d_obj.mesh = Dummy()
        ls3d_obj.children = bl_obj.children

    elif obj_type == ObjectType.SECTOR:
        create_ls3d_sector(ls3d_obj)
    elif obj_type == ObjectType.OCCLUDER:
        ls3d_obj.mesh = Occluder()
        ls3d_obj.children = bl_obj.children
    elif obj_type == ObjectType.TARGET:
        ls3d_obj.mesh = Target()
        ls3d_obj.children = bl_obj.children

    return ls3d_obj

def create_ls3d_objects(root_objects, root_armatures):
    for obj in root_objects:
        ls3d_obj = create_ls3d_object(obj, None)
        Libraries.Objects.append(ls3d_obj)

        def create_recursively(parent, children):
            for child in children:
                ls3d_child = create_ls3d_object(child, parent)
                Libraries.Objects.append(ls3d_child)

                create_recursively(ls3d_child, ls3d_child.children)

        create_recursively(ls3d_obj, ls3d_obj.children)

def export_4ds(filepath):
    file = OStream(filepath)

    file.stream.write(LS3D_4DS_SIGNATURE)
    file.write("<H", LS3D_4DS_VERSION)

    filetime = int(datetime.timestamp(datetime.now())) * 10000000 + 116444736000000000 # Datetime * hundreds of nanoseconds + epoch as filetime
    file.write("<Q", filetime)

    Libraries.Materials = []
    Libraries.Objects = []
    Libraries.MeshInstances = []
    Libraries.MeshInstancesParents = []

    root_objects, root_armatures = get_root_objects()

    create_ls3d_objects(root_objects, root_armatures)

    mat_count_offs = file.stream.tell()
    file.write("<H", len(Libraries.Materials))

    for mat in Libraries.Materials:
        LS3DMaterial.write_ls3d_material(mat, file)

    obj_count_offs = file.stream.tell()
    file.write("<H", len(Libraries.Objects))

    for obj in Libraries.Objects:
        obj.export(file)

    file.write("<B", 0)

    file.close()

    del Libraries.Materials
    del Libraries.Objects
    del Libraries.MeshInstances
    del Libraries.MeshInstancesParents

def save_4ds(context, filepath):
    export_4ds(filepath)

    return {'FINISHED'}