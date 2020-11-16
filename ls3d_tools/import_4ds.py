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

import os

from .io_utils import IStream
from ._4ds_utils import *

def read_materials(file):
    Libraries.Materials = []
    mat_count = file.read("<H")

    # Read all materials and load them to the material library
    for i in range(mat_count):
        mat = LS3DMaterial(
            file.read("<I"),
            file.read("<4f"),
            file.read("<4f"),
            file.read("<4f"),
            file.read("<4f"),
            *file.read("<2f")
            )

        no_map = True

        if mat.has_flag(MaterialFlag.ENVIRONMENT_MAPPING):
            mat.env_overlay_ratio = file.read("<f")
            mat.env_map = file.read_presized_string()
            no_map = False

        if mat.has_flag(MaterialFlag.DIFFUSE_MAPPING):
            mat.diff_map = file.read_presized_string()
            no_map = False

        if mat.has_flag(MaterialFlag.ALPHA_MAPPING) and not mat.has_flag(MaterialFlag.DIFFUSE_ALPHA):
            mat.alpha_map = file.read_presized_string()
            no_map = False

        if mat.has_flag(MaterialFlag.DIFFUSE_ANIMATED):
            mat.animation = AnimatedMap(*file.read("<IH3I"))

        if no_map:
            file.read_presized_string()

        Libraries.Materials.append(mat)

def read_objects(file):
    Libraries.Objects = []
    Libraries.Joints = []
    obj_count = file.read("<H")
    
    for i in range(obj_count):
        try:
            obj_type = ObjectType(file.read("<B"))
        except ValueError:
            raise IOError(f"Unsupported object type {obj_type}")

        visual_type = visual_flags = 0

        if obj_type == ObjectType.VISUAL:
            try:
                visual_type = VisualType(file.read("<B"))
            except ValueError:
                raise IOError(f"Unsupported visual type {visual_type}")

            visual_flags = file.read("<H")

        # Reading standard object data
        obj = LS3DObject(
            obj_type,
            visual_type,
            visual_flags,
            file.read("<H"),
            file.read("<3f"),
            file.read("<4f"),
            file.read("<3f"),
            *file.read("<IB"),
            file.read_presized_string(),
            file.read_presized_string()
            )

        obj.mesh = read_mesh(file, obj_type, visual_type)
        Libraries.Objects.append(obj)

        if obj.object_type == ObjectType.JOINT:
            Libraries.Joints.append(obj)
            print(f"Appending: {obj.mesh.joint_index}")

def read_mesh(file, obj_type, visual_type):
    if obj_type == ObjectType.VISUAL:
        if visual_type == VisualType.STANDARD_MESH:
            mesh = StandardMesh()
        elif visual_type == VisualType.SINGLE_MESH:
            mesh = SingleMesh()
        elif visual_type == VisualType.SINGLE_MORPH:
            mesh = SingleMorph()
        elif visual_type == VisualType.BILLBOARD:
            mesh = Billboard()
        elif visual_type == VisualType.MORPH:
            mesh = MorphMesh()
        elif visual_type == VisualType.LENS:
            mesh = Lens()
        elif visual_type == VisualType.MIRROR:
            mesh = Mirror()
        else:
            raise Exception(f"Konec: Visual {{{VisualType(visual_type)}}}")
        
    elif obj_type == ObjectType.SECTOR:
        mesh = Sector()
    elif obj_type == ObjectType.DUMMY:
        mesh = Dummy()
    elif obj_type == ObjectType.TARGET:
        mesh = Target()
    elif obj_type == ObjectType.JOINT:
        mesh = Joint()
    elif obj_type == ObjectType.OCCLUDER:
        mesh = Occluder()
    else:
        raise Exception(f"Konec: Object {{{ObjectType(obj_type)}}}")

    mesh.read(file)

    return mesh

def import_4ds(import_ctx, filepath):
    Settings.load_settings()

    file = IStream(filepath)

    signature = file.read("<4s")

    if signature != LS3D_4DS_SIGNATURE:
        raise IOError("Invalid 4DS signature")

    version = file.read("<H")

    if version != LS3D_4DS_VERSION:
        raise IOError("Unsupported 4DS version")

    # Skip the filetime timestamp
    file.stream.seek(8, 1)

    read_materials(file)
    read_objects(file)

    for mat in Libraries.Materials:
        mat.create_bl_mat()

    for joint in Libraries.Joints:
        joint.mesh.prepare_bone(joint)

    for obj in Libraries.Objects:
        #if obj.object_type != ObjectType.JOINT:
        obj.create_bl_obj()

    for joint in Libraries.Joints:
        joint.mesh.set_pose_transformation(joint)

    animation_5ds = file.read("<B")

    del Libraries.Materials
    del Libraries.Objects
    del Libraries.Joints
    Libraries.WorldArmature = None

    file.close()

def load_4ds(import_ctx, filepath):
    import_4ds(import_ctx, filepath)

    return {'FINISHED'}