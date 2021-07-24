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

from __future__ import annotations
from typing import List, Optional, Tuple, overload
import bpy
import bmesh
import os

from enum import IntEnum, IntFlag
from dataclasses import dataclass
from abc import ABC, abstractmethod
from mathutils import Vector, Euler, Quaternion, Matrix
from math import radians, degrees, sqrt
from bpy_extras.image_utils import load_image

from .ls3d_material import (
    LS3DMaterialProperties,
    create_ls3d_material,
    NODE_DIFFUSE,
    NODE_ALPHA,
    NODE_ENVIRONMENT,
    NODE_OUTPUT,
    NODE_SHADER
)

from .io_utils import IStream, OStream
from .ls3d_object import LS3DObjectProperties
from .ls3d_mirror import LS3DMirrorProperties
from .ls3d_sector import LS3DSectorProperties
from .ls3d_portal import LS3DPortalProperties
from .ls3d_lens import LS3DLensProperty


def create_transformation(translation: Vector, rotation: Quaternion, scale: Vector) -> Matrix:
    mat_loc = Matrix.Translation(translation)
    mat_rot = rotation.to_matrix().to_4x4()
    mat_sca = Matrix()
    mat_sca[0][0] = scale[0]
    mat_sca[1][1] = scale[1]
    mat_sca[2][2] = scale[2]

    return mat_loc @ mat_rot @ mat_sca


def component_min(vec_a: Vector, vec_b: Vector) -> Vector:
    vec = Vector((0.0, 0.0, 0.0))

    for i in range(3):
        vec[i] = vec_a[i] if vec_a[i] < vec_b[i] else vec_b[i]

    return vec


def component_max(vec_a: Vector, vec_b: Vector) -> Vector:
    vec = Vector((0.0, 0.0, 0.0))

    for i in range(3):
        vec[i] = vec_a[i] if vec_a[i] > vec_b[i] else vec_b[i]

    return vec


def create_armature(bl_obj: bpy.types.Object = None) -> bpy.types.Object:
    """Creates a new armature, which is required to create bone children."""

    if bl_obj:
        arm_data = bpy.data.armatures.new(f"Armature {bl_obj.name}")
    else:
        arm_data = bpy.data.armatures.new(f"Armature World")

    bl_armature = bpy.data.objects.new(arm_data.name, arm_data)

    bpy.context.collection.objects.link(bl_armature)

    bl_armature.select_set(True)
    bpy.context.view_layer.objects.active = bl_armature

    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)

    if bl_obj:
        bl_obj.parent = bl_armature

    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    return bl_armature


def get_bmesh(bl_obj: bpy.types.Object) -> bmesh.types.BMesh:
    bl_mesh = bl_obj.data

    bm = bmesh.new()
    bm.from_mesh(bl_mesh)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()

    return bm


LS3D_4DS_SIGNATURE = b'4DS\x00'
LS3D_4DS_VERSION = 41


class Settings:
    Maps: List[str]
    SectorColor: Tuple[float, float, float, float]
    PortalColor: Tuple[float, float, float, float]
    OccluderColor: Tuple[float, float, float, float]
    MirrorColor: Tuple[float, float, float, float]

    @classmethod
    def load_settings(cls) -> None:
        try:
            from . import settings
            cls.Maps = settings.MapsDirectories
            cls.SectorColor = settings.SectorColor
            cls.PortalColor = settings.PortalColor
            cls.OccluderColor = settings.OccluderColor
            cls.MirrorColor = settings.MirrorColor

        except(ImportError):
            cls.Maps = []
            cls.SectorColor = (1.0, 0.0, 0.0, 0.6)
            cls.PortalColor = (0.0, 1.0, 0.0, 0.4)
            cls.OccluderColor = (0.0, 0.0, 1.0, 0.6)
            cls.MirrorColor = (1.0, 1.0, 0.0, 1.0)


class Libraries:
    Materials: List[LS3DMaterial]
    Objects: List[LS3DObject]
    Joints: List[LS3DObject]
    WorldArmature: bpy.types.Armature = None
    MeshInstances: list
    MeshInstancesParents: list

    @staticmethod
    def get_object_by_name(name: str) -> Optional[LS3DObject]:
        for obj in Libraries.Objects:
            if obj.name == name:
                return obj

        return None


class MaterialFlag(IntFlag):
    DIFFUSE_MAPPING = 0x00040000
    ENVIRONMENT_MAPPING = 0x00080000
    ENVIRONMENT_BASE = 0x00000100
    ENVIRONMENT_MULTIPLY = 0x00000200
    ENVIRONMENT_ADD = 0x00000400
    ENVIRONMENT_REFL_COMP_Z = 0x00001000
    ENVIRONMENT_REFL_PROJ_Z = 0x00002000
    ENVIRONMENT_REFL_PROJ_Y = 0x00004000
    ADDITIONAL_EFFECT = 0x00008000
    ALPHA_MAPPING = 0x40000000
    COLOR_KEYING = 0x20000000
    # ALPHA_ANIMATED = 0x02000000
    DIFFUSE_ANIMATED = 0x04000000
    DIFFUSE_ALPHA = 0x01000000
    NO_BACKFACE_CULLING = 0x10000000
    GENERATE_MIPMAPS = 0x00800000
    ADDITIVE_BLENDING = 0x80000000
    COLORING = 0x08000000


@dataclass
class AnimatedMap:
    frame_count: int = 0
    unk0: int = 0
    frame_time: int = 0
    unk1: int = 0
    unk2: int = 0


@dataclass
class LS3DMaterial:
    flags: MaterialFlag
    ambient_color: Tuple[float, float, float, float]
    diffuse_color: Tuple[float, float, float, float]
    specular_color: Tuple[float, float, float, float]
    emission_color: Tuple[float, float, float, float]
    glossiness: float
    opacity: float

    diff_map: str = None
    env_map: str = None
    alpha_map: str = None

    env_overlay_ratio: float = 0.0
    animation: AnimatedMap = None
    bl_mat: bpy.types.Material = None

    def has_flag(self, flag) -> bool: return self.flags & flag == flag

    def create_bl_mat(self) -> None:
        mat = bpy.data.materials.new("Material")

        mat.diffuse_color = (*self.diffuse_color[0:3], 1.0)
        mat.use_backface_culling = not self.has_flag(
            MaterialFlag.NO_BACKFACE_CULLING)

        props: LS3DMaterialProperties
        props = mat.ls3d_props

        props.mipmapping = self.has_flag(MaterialFlag.GENERATE_MIPMAPS)
        props.coloring = self.has_flag(MaterialFlag.COLORING)
        props.additive_blending = self.has_flag(MaterialFlag.ADDITIVE_BLENDING)
        props.color_keying = self.has_flag(MaterialFlag.COLOR_KEYING)
        props.diffuse_alpha = self.has_flag(MaterialFlag.DIFFUSE_ALPHA)
        props.diffuse_texture = self.has_flag(MaterialFlag.DIFFUSE_MAPPING)
        props.alpha_texture = self.has_flag(MaterialFlag.ALPHA_MAPPING)
        props.env_texture = self.has_flag(MaterialFlag.ENVIRONMENT_MAPPING)

        props.ambient_color = (*self.ambient_color[0:3], 1.0)
        props.specular_color = (*self.specular_color[0:3], 1.0)

        create_ls3d_material(mat)

        ntree = mat.node_tree

        # Node properties
        if NODE_SHADER in ntree.nodes:
            shader_node = ntree.nodes[NODE_SHADER]
            shader_node.inputs["Base Color"].default_value = mat.diffuse_color
            shader_node.inputs["Emission"].default_value = (
                *self.emission_color[0:3], 1.0)
            shader_node.inputs["Alpha"].default_value = self.opacity
            shader_node.inputs["Metallic"].default_value = self.glossiness / 100.0

            if self.has_flag(MaterialFlag.DIFFUSE_MAPPING):
                ntree.nodes[NODE_DIFFUSE].image = self.load_texture(
                    self.diff_map)

            if self.has_flag(MaterialFlag.ALPHA_MAPPING) and not self.has_flag(MaterialFlag.DIFFUSE_ALPHA):
                ntree.nodes[NODE_ALPHA].image = self.load_texture(
                    self.alpha_map)

            if self.has_flag(MaterialFlag.ENVIRONMENT_MAPPING):
                ntree.nodes[NODE_ENVIRONMENT].image = self.load_texture(
                    self.env_map)
                props.env_ratio = self.env_overlay_ratio

                if not self.has_flag(MaterialFlag.ENVIRONMENT_BASE):
                    pass  # raise Exception("Environment mapping error base")

                if not self.has_flag(MaterialFlag.ENVIRONMENT_REFL_COMP_Z):
                    pass  # raise Exception("Environment mapping error Z")

                props.env_base_mixing = self.has_flag(
                    MaterialFlag.ENVIRONMENT_BASE)
                props.env_mix_type = 'ADD' if self.has_flag(MaterialFlag.ENVIRONMENT_ADD) else 'MULTIPLY' if self.has_flag(
                    MaterialFlag.ENVIRONMENT_MULTIPLY) else 'NONE'
                props.env_projection_axis = 'YZ' if (self.has_flag(MaterialFlag.ENVIRONMENT_REFL_PROJ_Y) and self.has_flag(MaterialFlag.ENVIRONMENT_REFL_PROJ_Z)) else 'Y' if self.has_flag(
                    MaterialFlag.ENVIRONMENT_REFL_PROJ_Y) else 'Z' if self.has_flag(MaterialFlag.ENVIRONMENT_REFL_PROJ_Z) else 'NONE'

        anm = self.has_flag(MaterialFlag.DIFFUSE_ANIMATED)

        # Animation properties
        anm_props: ls3d_material.LS3DAnimatedMapProperties
        anm_props = props.anm_props

        props.texture_animation = anm

        if anm:
            anm_props.frame_count = self.animation.frame_count
            anm_props.frame_time = self.animation.frame_time
            anm_props.unknown_a = self.animation.unk0
            anm_props.unknown_b = self.animation.unk1
            anm_props.unknown_c = self.animation.unk2

        self.bl_mat = mat

    @staticmethod
    def write_ls3d_material(bl_mat: bpy.types.Material, file: OStream) -> None:
        flags = 1  # Material flags always have this set

        props: LS3DMaterialProperties
        props = bl_mat.ls3d_props

        if not bl_mat.use_backface_culling:
            flags |= MaterialFlag.NO_BACKFACE_CULLING
        if props.mipmapping:
            flags |= MaterialFlag.GENERATE_MIPMAPS
        if props.coloring:
            flags |= MaterialFlag.COLORING
        if props.additive_blending:
            flags |= MaterialFlag.ADDITIVE_BLENDING
        if props.color_keying:
            flags |= MaterialFlag.COLOR_KEYING

        ntree = bl_mat.node_tree

        # Node properties
        if NODE_SHADER in ntree.nodes:
            shader_node = ntree.nodes[NODE_SHADER]

            if props.diffuse_texture:
                flags |= MaterialFlag.DIFFUSE_MAPPING

                if props.texture_animation:
                    flags |= MaterialFlag.DIFFUSE_ANIMATED

            if props.alpha_texture:
                flags |= MaterialFlag.ALPHA_MAPPING

            if props.env_texture:
                flags |= MaterialFlag.ENVIRONMENT_MAPPING

            if props.diffuse_alpha:
                flags |= MaterialFlag.ALPHA_MAPPING
                flags |= MaterialFlag.DIFFUSE_ALPHA

            if props.env_base_mixing:
                flags |= MaterialFlag.ENVIRONMENT_BASE

            flags |= MaterialFlag.ENVIRONMENT_ADD if props.env_mix_type == 'ADD' else MaterialFlag.ENVIRONMENT_MULTIPLY if props.env_mix_type == 'MULTIPLY' else 0

            file.write("<I", flags)
            file.write("<16f", *props.ambient_color, *
                       shader_node.inputs["Base Color"].default_value, *props.specular_color, *shader_node.inputs["Emission"].default_value)
            file.write("<2f", shader_node.inputs["Metallic"].default_value *
                       100.0, shader_node.inputs["Alpha"].default_value)

            def export_texname(node_name: str) -> None:
                image = ntree.nodes[node_name].image

                if image:
                    file.write_presized_string(
                        os.path.basename(image.filepath).upper())
                else:
                    file.write_presized_string("")

            no_tex = True

            if props.env_texture:
                file.write("<f", props.env_ratio)
                export_texname(NODE_ENVIRONMENT)
                no_tex = False

            if props.diffuse_texture:
                export_texname(NODE_DIFFUSE)
                no_tex = False

            if props.alpha_texture and not props.diffuse_alpha:
                export_texname(NODE_ALPHA)
                no_tex = False

            # Animation properties
            anm_props: ls3d_material.LS3DAnimatedMapProperties
            anm_props = props.anm_props

            if props.texture_animation and props.diffuse_texture:
                file.write("<IH3I", anm_props.frame_count, anm_props.unknown_a,
                           anm_props.frame_time, anm_props.unknown_b, anm_props.unknown_c)

            if no_tex:
                file.write("<B", 0)
        else:
            file.write("<I", flags)
            file.write("<16f", *props.ambient_color, *
                       bl_mat.diffuse_color, *props.specular_color, 0, 0, 0, 0)
            file.write("<2f", 25.0, 1)
            file.write("<B", 0)

    @staticmethod
    def load_texture(filename: str) -> bpy.types.Image:
        image = None

        for dirname in Settings.Maps:
            path = os.path.join(dirname, filename)

            if os.path.isfile(path):
                image = load_image(filename, dirname)

        if not image:
            image = load_image(filename, "", True)

        return image


class ObjectType(IntEnum):
    VISUAL = 1
    SECTOR = 5
    DUMMY = 6
    TARGET = 7
    JOINT = 10
    OCCLUDER = 12


class VisualType(IntEnum):
    STANDARD_MESH = 0
    SINGLE_MESH = 2
    SINGLE_MORPH = 3
    BILLBOARD = 4
    MORPH = 5
    LENS = 6
    MIRROR = 8


class VisualFlags(IntFlag):
    DEPTH_BIAS = 0x0100
    DYNAMIC_SHADOWS = 0x0200
    UNKNOWN0 = 0x0400  # Transparency sorting priority ?? m_palmop01.4ds, la_N_flag01.4ds, b_art16.4ds, m_AF3_kob03.4ds
    UNKNOWN1 = 0x0800
    UNKNOWN2 = 0x1000  # Used for equipment (bagpacks, hats, weapons)
    DECALS = 0x2000
    NO_FOG = 0x8000


class CullingFlags(IntFlag):
    ENABLED = 0x01
    UNKNOWN1 = 0x04
    UNKNOWN2 = 0x08
    UNKNOWN3 = 0x10
    UNKNOWN4 = 0x20


@dataclass
class LS3DMesh(ABC):
    @abstractmethod
    def build_bl_obj(self, obj: LS3DObject) -> bpy.types.Object:
        return

    @abstractmethod
    def read(self, file: IStream) -> None:
        return

    def post_create(self, obj: LS3DObject) -> None:
        return

    # @abstractmethod
    def write(self, obj: LS3DObject, file: OStream) -> None:
        return


@dataclass
class LS3DObject:
    object_type: ObjectType
    visual_type: VisualType
    visual_flags: VisualFlags
    parent_index: int
    location: Vector
    rotation: Quaternion
    scale: Vector
    unk0: int
    culling_flags: CullingFlags
    name: str
    properties: str
    mesh: LS3DMesh = None
    bl_obj: bpy.types.Object = None
    armature: bpy.types.Armature = None
    children: List[LS3DObject] = None

    def create_bl_obj(self) -> None:
        self.bl_obj = self.mesh.build_bl_obj(self)

        if self.object_type != ObjectType.JOINT:
            self.__set_common_properties()

            # Link the object to the scene
            bpy.context.scene.collection.objects.link(self.bl_obj)

        self.mesh.post_create(self)

    def __set_common_properties(self) -> None:
        # Parse the user defined properties
        lines = self.properties.splitlines()
        for line in lines:
            prop: ls3d_object.LS3DObjectProperty
            prop = self.bl_obj.ls3d_props.user_defined_properties.add()
            prop.content = line

        if self.armature:
            bl_obj = self.armature
        else:
            bl_obj = self.bl_obj

        bl_obj.matrix_local = create_transformation(
            self.location, self.rotation, self.scale)
        self.set_parent()

        # Set LS3D properties
        props: LS3DObjectProperties
        props = bl_obj.ls3d_props
        mesh_type = self.get_mesh_type()

        if mesh_type:
            props.mesh_type = mesh_type

        if self.object_type == ObjectType.VISUAL:
            visual_flags = self.visual_flags
            props.visual_flag_a = visual_flags & VisualFlags.DEPTH_BIAS == VisualFlags.DEPTH_BIAS
            props.visual_flag_b = visual_flags & VisualFlags.DYNAMIC_SHADOWS == VisualFlags.DYNAMIC_SHADOWS
            props.visual_flag_c = visual_flags & VisualFlags.UNKNOWN0 == VisualFlags.UNKNOWN0
            props.visual_flag_d = visual_flags & VisualFlags.UNKNOWN1 == VisualFlags.UNKNOWN1
            props.visual_flag_e = visual_flags & VisualFlags.UNKNOWN2 == VisualFlags.UNKNOWN2
            props.visual_flag_f = visual_flags & VisualFlags.DECALS == VisualFlags.DECALS
            props.visual_flag_g = visual_flags & VisualFlags.NO_FOG == VisualFlags.NO_FOG

            if visual_flags & VisualFlags.UNKNOWN2 == VisualFlags.UNKNOWN2:
                print(self.name)

            if visual_flags & VisualFlags.UNKNOWN0 == VisualFlags.UNKNOWN0:
                print(self.name)

        culling_flags = self.culling_flags
        props.culling_flag_a = culling_flags & CullingFlags.ENABLED == CullingFlags.ENABLED
        props.culling_flag_b = culling_flags & CullingFlags.UNKNOWN1 == CullingFlags.UNKNOWN1
        props.culling_flag_c = culling_flags & CullingFlags.UNKNOWN2 == CullingFlags.UNKNOWN2
        props.culling_flag_d = culling_flags & CullingFlags.UNKNOWN3 == CullingFlags.UNKNOWN3
        props.culling_flag_e = culling_flags & CullingFlags.UNKNOWN4 == CullingFlags.UNKNOWN4

    def set_parent(self) -> None:
        if self.parent_index > 0:
            parent = Libraries.Objects[self.parent_index - 1]

            if parent.object_type != ObjectType.JOINT:
                self.bl_obj.parent = parent.bl_obj
            else:
                self.bl_obj.parent = parent.mesh.armature
                self.bl_obj.parent_bone = parent.name
                self.bl_obj.parent_type = 'BONE'
                self.bl_obj.matrix_world = parent.mesh.armature.matrix_world @ parent.mesh.transformation @ create_transformation(
                    self.location, self.rotation, self.scale)

    def create_armature(self, bl_obj: bpy.types.Object) -> None:
        self.armature = create_armature(bl_obj)

    def get_mesh_type(self) -> Optional[str]:
        if self.object_type == ObjectType.VISUAL:
            if self.visual_type == VisualType.STANDARD_MESH:
                return 'STANDARD'
            elif self.visual_type == VisualType.BILLBOARD:
                return 'BILLBOARD'
            elif self.visual_type == VisualType.SINGLE_MESH:
                return 'SINGLE'
            elif self.visual_type == VisualType.MORPH:
                return 'MORPH'
            elif self.visual_type == VisualType.SINGLE_MORPH:
                return 'SINGLE_MORPH'
            elif self.visual_type == VisualType.MIRROR:
                return 'MIRROR'
        elif self.object_type == ObjectType.SECTOR:
            return 'SECTOR'
        elif self.object_type == ObjectType.OCCLUDER:
            return 'OCCLUDER'

        return None

    def export(self, file: OStream) -> None:
        file.write("<B", self.object_type)

        if self.object_type == ObjectType.VISUAL:
            file.write("<BH", self.visual_type, self.visual_flags)

        file.write("<H", self.parent_index)

        file.write_vector3(self.location)
        file.write_quaternion(self.rotation)
        file.write_vector3(self.scale)

        file.write("<IB", self.unk0, self.culling_flags)
        file.write_presized_string(self.name)
        file.write_presized_string(self.properties)

        self.mesh.write(self, file)

    def get_bbox(self) -> Tuple[Vector, Vector]:
        bbox = self.bl_obj.bound_box

        corner_min = bbox[0]
        corner_max = bbox[0]

        for i in range(1, 8):
            corner_min = component_min(corner_min, bbox[i])
            corner_max = component_max(corner_max, bbox[i])

        return corner_min, corner_max


class Mirror(LS3DMesh):
    unk0: Tuple[float, float, float, float]
    reflection_matrix: Matrix
    back_color: Tuple[float, float, float]
    unk1: int
    far_plane: float
    positions: List[Vector]
    faces: List[Tuple[int, int, int]]

    def read(self, file: IStream) -> None:
        file.stream.seek(32, 1)  # Bounding box
        self.unk0 = file.read("4f")
        self.reflection_matrix = file.read_matrix4x4()
        self.back_color = file.read("3f")
        self.unk1 = file.read("<I")
        self.far_plane = file.read("<f")

        vertices_count = file.read("<I")
        faces_count = file.read("<I")

        self.positions = []
        self.faces = []

        for i in range(vertices_count):
            self.positions.append(file.read_vector3())
            file.stream.seek(4, 1)

        for i in range(faces_count):
            self.faces.append(file.read_face())

    def build_bl_obj(self, obj: LS3DObject) -> bpy.types.Object:
        bl_mesh = bpy.data.meshes.new(obj.name)
        bl_mesh.from_pydata(self.positions, [], self.faces)

        bl_obj = bpy.data.objects.new(obj.name, bl_mesh)
        bl_obj.color = Settings.MirrorColor

        props: LS3DObjectProperties
        props = bl_obj.ls3d_props
        props.mesh_type = 'MIRROR'

        return bl_obj

    def post_create(self, obj: LS3DObject) -> None:
        bl_obj = obj.bl_obj

        # Create the reflection axis
        refl_name = bl_obj.name + f".Reflection"

        refl_obj = bpy.data.objects.new(refl_name, None)
        refl_obj.empty_display_type = 'ARROWS'
        refl_obj.parent = bl_obj

        mirror_props: LS3DMirrorProperties
        mirror_props = bl_obj.ls3d_props.mirror_props
        mirror_props.reflection_axis = refl_obj
        mirror_props.unknown_a = self.unk0
        mirror_props.back_color = self.back_color
        mirror_props.unknown_b = self.unk1
        mirror_props.far_plane = self.far_plane

        # Link the reflection axis to the scene
        bpy.context.scene.collection.objects.link(refl_obj)

    def write(self, obj: LS3DObject, file: OStream) -> None:
        mirror_props: LS3DMirrorProperties
        mirror_props = obj.bl_obj.ls3d_props.mirror_props
        bmin, bmax = obj.get_bbox()

        file.write_vector4(bmin)
        file.write_vector4(bmax)
        file.write("<4f", *mirror_props.unknown_a)

        if mirror_props.reflection_axis:
            refl_axis = mirror_props.reflection_axis
            refl_local = refl_axis.matrix_local
            refl_loc = refl_local.to_translation()
            refl_rot = refl_local.to_quaternion()
            refl_sca = refl_local.to_scale()

            mat = create_transformation(refl_loc, refl_rot, refl_sca)
        else:
            mat = Matrix().identity()

        file.write_matrix4x4(mat)
        file.write("<3f", *mirror_props.back_color)
        file.write("<I", mirror_props.unknown_b)
        file.write("<f", mirror_props.far_plane)

        bm = get_bmesh(obj.bl_obj)

        vert_count = len(bm.verts)
        face_count = len(bm.faces)

        file.write("<II", vert_count, face_count)

        for vert in bm.verts:
            file.write_vector4(vert.co)

        for face in bm.faces:
            file.write_face(
                (face.loops[0].vert.index, face.loops[1].vert.index, face.loops[2].vert.index))

        bm.free()


class PortalFlags(IntFlag):
    UNKNOWN0 = 0x04
    UNKNOWN1 = 0x10
    UNKNOWN2 = 0x20
    UNKNOWN3 = 0x40


@dataclass
class Portal:
    flags: PortalFlags
    unk0: float
    unk1: float
    color_r: int
    color_g: int
    color_b: int
    color_a: int
    positions: List[Vector] = None
    normal: Vector = None
    distance: Vector = None


class SectorFlags(IntFlag):
    UNKNOWN0 = 0x0001
    UNKNOWN4 = 0x0020
    UNKNOWN3 = 0x0040
    UNKNOWN1 = 0x0100
    UNKNOWN2 = 0x0800


class Sector(LS3DMesh):
    flags: SectorFlags
    unknown: int
    positions: List[Vector]
    faces: List[Tuple[int, int, int]]
    portals: List[Portal]

    def read(self, file: IStream) -> None:
        self.flags, self.unknown = file.read("<2I")
        vertices_count: int = file.read("<I")
        faces_count: int = file.read("<I")
        file.stream.seek(32, 1)  # Bounding box

        self.positions = []
        self.faces = []

        for i in range(vertices_count):
            self.positions.append(file.read_vector3())
            file.stream.seek(4, 1)

        for i in range(faces_count):
            self.faces.append(file.read_face())

        portals_count: int = file.read("<B")
        self.portals = []

        for i in range(portals_count):
            vertices_count: int = file.read("<B")
            file.stream.seek(16, 1)  # Normal and distance
            portal = Portal(*file.read("<IffBBBB"))

            portal.positions = []
            for j in range(vertices_count):
                portal.positions.append(file.read_vector3())
                file.stream.seek(4, 1)

            self.portals.append(portal)

    def build_bl_obj(self, obj: LS3DObject) -> bpy.types.Object:
        bl_mesh = bpy.data.meshes.new(obj.name)
        bl_mesh.from_pydata(self.positions, [], self.faces)

        bl_obj = bpy.data.objects.new(obj.name, bl_mesh)
        bl_obj.color = Settings.SectorColor

        props: LS3DSectorProperties
        props = bl_obj.ls3d_props.sector_props
        props.flag_a = self.flags & SectorFlags.UNKNOWN0 == SectorFlags.UNKNOWN0
        props.flag_b = self.flags & SectorFlags.UNKNOWN1 == SectorFlags.UNKNOWN1
        props.flag_c = self.flags & SectorFlags.UNKNOWN2 == SectorFlags.UNKNOWN2
        props.flag_d = self.flags & SectorFlags.UNKNOWN3 == SectorFlags.UNKNOWN3
        props.flag_e = self.flags & SectorFlags.UNKNOWN4 == SectorFlags.UNKNOWN4
        props.unknown = self.unknown

        def create_portal(portal: Portal, index: int) -> None:
            portal_name = bl_obj.name + f".Portal_{index}"
            portal_faces = [(range(0, len(portal.positions)))]
            portal_mesh = bpy.data.meshes.new(portal_name)
            portal_mesh.from_pydata(portal.positions, [], portal_faces)

            portal_obj = bpy.data.objects.new(portal_name, portal_mesh)
            portal_obj.color = Settings.PortalColor
            portal_obj.parent = bl_obj

            props: LS3DObjectProperties
            props = portal_obj.ls3d_props
            props.mesh_type = 'SECTOR'
            props.is_portal = True

            flags = PortalFlags(portal.flags)

            portal_props: LS3DPortalProperties
            portal_props = props.portal_props
            portal_props.flag_a = flags & PortalFlags.UNKNOWN0 == PortalFlags.UNKNOWN0
            portal_props.flag_b = flags & PortalFlags.UNKNOWN1 == PortalFlags.UNKNOWN1
            portal_props.flag_c = flags & PortalFlags.UNKNOWN2 == PortalFlags.UNKNOWN2
            portal_props.flag_d = flags & PortalFlags.UNKNOWN3 == PortalFlags.UNKNOWN3
            portal_props.unknown_a = portal.unk0
            portal_props.unknown_b = portal.unk1
            portal_props.color = (portal.color_r / 255, portal.color_g /
                                  255, portal.color_b / 255, portal.color_a / 255)

            # Link the portal to the scene
            bpy.context.scene.collection.objects.link(portal_obj)

        for i, portal in enumerate(self.portals):
            create_portal(portal, i)

        return bl_obj

    def write(self, obj: LS3DObject, file: OStream) -> None:
        props: LS3DSectorProperties
        props = obj.bl_obj.ls3d_props.sector_props

        bm = get_bmesh(obj.bl_obj)

        vert_count = len(bm.verts)
        face_count = len(bm.faces)

        flags = 0

        if props.flag_a:
            flags |= SectorFlags.UNKNOWN0

        if props.flag_b:
            flags |= SectorFlags.UNKNOWN1

        if props.flag_c:
            flags |= SectorFlags.UNKNOWN2

        if props.flag_d:
            flags |= SectorFlags.UNKNOWN3

        if props.flag_e:
            flags |= SectorFlags.UNKNOWN4

        file.write("<IIII", flags, props.unknown, vert_count, face_count)

        bmin, bmax = obj.get_bbox()

        file.write_vector4(bmin)
        file.write_vector4(bmax)

        for vert in bm.verts:
            file.write_vector4(vert.co)

        for face in bm.faces:
            file.write_face(
                (face.loops[0].vert.index, face.loops[1].vert.index, face.loops[2].vert.index))

        bm.free()

        file.write("<B", len(self.portals))

        for portal in self.portals:
            file.write("<B", len(portal.positions))
            file.write("<3f", *portal.normal)
            file.write("<fIffI", portal.distance, portal.flags,
                       portal.unk0, portal.unk1, 0)

            for position in portal.positions:
                file.write("<4f", *position, 0)


class Dummy(LS3DMesh):
    bounds_min: Vector
    bounds_max: Vector

    def read(self, file: IStream) -> None:
        self.bounds_min = file.read_vector3()
        file.stream.seek(4, 1)  # Useless 4th float
        self.bounds_max = file.read_vector3()
        file.stream.seek(4, 1)  # Useless 4th float

    def build_bl_obj(self, obj: LS3DObject) -> bpy.types.Object:
        bl_obj = bpy.data.objects.new(obj.name, None)
        bl_obj.empty_display_type = 'CUBE'

        # Since Blender doesn't support setting the display size as XYZ Vector, we must use only the X axis
        display_size = Vector((abs(self.bounds_max.x), abs(
            self.bounds_max.y), abs(self.bounds_max.z)))
        bl_obj.empty_display_size = display_size.x

        props: LS3DObjectProperties
        props = bl_obj.ls3d_props
        props.helper_type = 'DUMMY'

        return bl_obj

    def write(self, obj: LS3DObject, file: OStream) -> None:
        display_size = obj.bl_obj.empty_display_size

        file.write("<8f", -display_size, -display_size, -display_size,
                   0, display_size, display_size, display_size, 0)


class Joint(LS3DMesh):
    joint_index: int
    transformation: Matrix
    pose_transformation: Matrix
    parent: LS3DObject
    children: Optional[List[LS3DObject]]
    direction: Vector
    roll: float
    armature: bpy.types.Armature
    bl_bone_name: str

    def read(self, file: IStream) -> None:
        self.joint_index = file.read("<I")

    def prepare_bone(self, obj: LS3DObject) -> None:
        # Initialize the list of children bones
        self.children = None
        self.pose_transformation = None

        # Since Blender doesn't support the edit bones transformation (translation, rotation, scale), we have to calculate
        # the bone's world transformation ourselves and convert it to the "heads and tails space"
        local = create_transformation(obj.location, obj.rotation, obj.scale)
        # self.roll = local.to_euler().z

        if obj.parent_index:
            parent = Libraries.Objects[obj.parent_index - 1]

            if parent.object_type == ObjectType.JOINT:
                self.parent = parent

                if not parent.mesh.children:
                    parent.mesh.children = []

                parent.mesh.children.append(obj)
                parent_matrix = parent.mesh.transformation
                self.transformation = parent_matrix @ local
                self.roll = self.transformation.to_euler().z
                return

        self.parent = None
        self.transformation = local
        self.roll = self.transformation.to_euler().z

    def build_bl_obj(self, obj: LS3DObject) -> None:
        # Extracting the locations from the bone's world matrix
        head_location = Vector(self.transformation.to_translation())

        if obj.parent_index:
            parent = Libraries.Objects[obj.parent_index - 1]

            if parent.object_type == ObjectType.JOINT:
                self.armature = parent.mesh.armature
            else:
                if not parent.armature:
                    parent.create_armature(parent.bl_obj)

                self.armature = parent.armature
        else:
            # If the bone has no parent, world armature creation comes into place
            if not Libraries.WorldArmature:
                Libraries.WorldArmature = create_armature()

            self.armature = Libraries.WorldArmature

        if self.children:
            tail_location = self.children[0].mesh.transformation.to_translation(
            )
            self.direction = (tail_location - head_location).normalized()
        else:
            # We don't really know the end site bone's size
            tail_location = head_location + self.parent.mesh.direction * 0.05

        # Since Blender doesn't support zero-size bones, we have to extend the bone a little if it's too short
        if (tail_location - head_location).magnitude < 1e-2:
            bone_vec = (tail_location - head_location).normalized()
            tail_location = head_location + bone_vec * 0.01

        # Edit bones can be accesed only in the edit mode
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)

        # Creating a new Blender bone
        arm_data = self.armature.data
        bl_bone = arm_data.edit_bones.new(obj.name)

        # Since we will need the bone name for future tasks, we have to save it (the bone name could have changed)
        self.bl_bone_name = bl_bone.name

        bl_bone.head = head_location
        bl_bone.tail = tail_location
        bl_bone.roll = self.roll

        # Link the bone to the parent bone
        if self.parent:
            if self.parent.mesh.bl_bone_name in arm_data.edit_bones:
                bl_bone.parent = arm_data.edit_bones[self.parent.mesh.bl_bone_name]

        direction = (tail_location - head_location).normalized()
        orig_rot = self.transformation.to_quaternion().to_euler()
        new_rot = direction.to_track_quat('Z', 'Y').to_euler()

        print(obj.name)
        print(f"Orig rot: {orig_rot}")
        print(f"New rot: {new_rot}")
        print(
            f"Orig rot deg: {(degrees(orig_rot.x), degrees(orig_rot.y), degrees(orig_rot.z))}")
        print(
            f"New rot deg: {(degrees(new_rot.x), degrees(new_rot.y), degrees(new_rot.z))}")

        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

    def set_pose_transformation(self, obj: LS3DObject) -> None:
        pass
    
        # if self.pose_transformation:
        #    pose_bone = self.armature.pose.bones[obj.name]
        #
        #    pose_mat = Matrix(self.pose_transformation)
        #    trans = pose_mat.to_translation()
        #    rot = pose_mat.to_euler()
        #    rot = Euler((-rot.x, -rot.z, -rot.y))
        #
        #    mat = self.transformation.inverted() @ rot.to_matrix().to_4x4()
        #
        #    rotation = mat.to_euler()
        #
        #    pose_bone.rotation_mode = 'XYZ'
        #    pose_bone.rotation_euler = rotation

    def set_parent(self, obj: LS3DObject) -> None:
        parent = Libraries.Objects[obj.parent_index - 1]

        if parent.object_type == ObjectType.JOINT:
            self.bl_bone.parent = parent.mesh.bl_bone
            print(f"Pro {self.bl_bone.parent} je to {parent.mesh.bl_bone.name}")
        else:
            print(f"Pro {obj.name} neni {parent.name}")


class Occluder(LS3DMesh):
    positions: List[Vector]
    faces: List[Tuple[int, int, int]]

    def read(self, file: IStream) -> None:
        vertices_count: int = file.read("<I")
        faces_count: int = file.read("<I")

        self.positions = []
        self.faces = []

        for i in range(vertices_count):
            self.positions.append(file.read_vector3())
            file.stream.seek(4, 1)

        for i in range(faces_count):
            self.faces.append(file.read_face())

    def build_bl_obj(self, obj: LS3DObject) -> bpy.types.Object:
        bl_mesh = bpy.data.meshes.new(obj.name)
        bl_mesh.from_pydata(self.positions, [], self.faces)

        bl_obj = bpy.data.objects.new(obj.name, bl_mesh)
        bl_obj.color = Settings.OccluderColor

        return bl_obj

    def write(self, obj: LS3DObject, file: OStream) -> None:
        bm = get_bmesh(obj.bl_obj)

        vert_count = len(bm.verts)
        face_count = len(bm.faces)

        file.write("<II", vert_count, face_count)

        for vert in bm.verts:
            file.write_vector4(vert.co)

        for face in bm.faces:
            file.write_face(
                (face.loops[0].vert.index, face.loops[1].vert.index, face.loops[2].vert.index))

        bm.free()


@dataclass
class SubMesh(object):
    face_count: int
    material_index: int


class StandardLOD(object):
    draw_distance: float
    unk0: int
    positions: List[Vector]
    uvs: List[Tuple[float, float]]
    faces: List[Tuple[int, int, int]]
    submeshes: List[SubMesh]
    bl_obj: bpy.types.Object = None

    def read(self, file: IStream) -> None:
        self.draw_distance = sqrt(file.read("<f"))
        self.unk0 = file.read("<I")

        vertices_count: int = file.read("<H")
        self.positions = []
        self.uvs = []

        for i in range(vertices_count):
            self.positions.append(file.read_vector3())
            file.stream.seek(12, 1)  # We don't need the normals
            self.uvs.append(file.read("<2f"))

        submeshes_count: int = file.read("<B")
        self.submeshes = []
        self.faces = []

        for i in range(submeshes_count):
            faces_count: int = file.read("<H")

            for j in range(faces_count):
                self.faces.append(file.read_face())

            mat_index: int = file.read("<H")

            self.submeshes.append(SubMesh(faces_count, mat_index))

    def create_bl_mesh(self, name: str) -> bpy.types.Mesh:
        bl_mesh = bpy.data.meshes.new(name)

        bl_mesh.from_pydata(self.positions, [], self.faces)

        bm = bmesh.new()
        bm.from_mesh(bl_mesh)
        bm.faces.ensure_lookup_table()

        uv_layer = bm.loops.layers.uv.new()

        i = 0
        for submesh in self.submeshes:
            if submesh.material_index:
                bl_mesh.materials.append(
                    Libraries.Materials[submesh.material_index - 1].bl_mat)
                mat_index = len(bl_mesh.materials) - 1
            else:
                mat_index = 0

            for j in range(i, i + submesh.face_count):
                face = bm.faces[j]
                face.material_index = mat_index
                for vert, loop in zip(face.verts, face.loops):
                    uv = self.uvs[loop.vert.index]
                    loop[uv_layer].uv = (uv[0], 1.0 - uv[1])

            i += submesh.face_count

        bm.to_mesh(bl_mesh)
        bm.free()

        return bl_mesh


class StandardMesh(LS3DMesh):
    instance_index: int = 0
    lods: List[StandardLOD] = None

    def read(self, file: IStream) -> None:
        self.instance_index = file.read("<H") - 1

        if self.instance_index < 0:
            lod_count = file.read("<B")
            self.lods = []

            for i in range(lod_count):
                lod = StandardLOD()
                lod.read(file)
                self.lods.append(lod)

    def build_bl_obj(self, obj: LS3DObject) -> bpy.types.Object:
        if self.instance_index >= 0:
            bl_obj = Libraries.Objects[self.instance_index].bl_obj.copy()
            bl_obj.name = obj.name
            bl_obj.parent = None
        else:

            if len(self.lods) > 0:
                bl_mesh = self.lods[0].create_bl_mesh(obj.name)
                bl_obj = bpy.data.objects.new(obj.name, bl_mesh)

                props: LS3DObjectProperties
                props = bl_obj.ls3d_props
                props.draw_distance = self.lods[0].draw_distance
                self.lods[0].bl_obj = bl_obj
            else:
                bl_mesh = bpy.data.meshes.new(obj.name)
                bl_mesh.from_pydata([], [], [])
                bl_obj = bpy.data.objects.new(obj.name, bl_mesh)

        return bl_obj

    def post_create(self, obj: LS3DObject) -> None:
        if self.lods:
            if len(self.lods) > 1:
                parent = obj.bl_obj

                for i in range(1, len(self.lods)):
                    lod_name = f"{obj.name}.lod_{i}"
                    bl_mesh = self.lods[i].create_bl_mesh(lod_name)

                    bl_obj = bpy.data.objects.new(lod_name, bl_mesh)

                    bl_obj.parent = parent
                    parent = bl_obj

                    props: LS3DObjectProperties
                    props = bl_obj.ls3d_props
                    props.is_lod = True
                    props.draw_distance = self.lods[i].draw_distance

                    self.lods[i].bl_obj = bl_obj

                    # Link the LOD to the scene
                    bpy.context.scene.collection.objects.link(bl_obj)

    def write(self, obj: LS3DObject, file: OStream) -> None:
        file.write("<H", self.instance_index)

        if self.instance_index:
            return

        lod_count = 1
        if self.lods:
            lod_count += len(self.lods)

        file.write("<B", lod_count)

        def write_lod(bl_obj: bpy.types.Object) -> None:
            props: LS3DObjectProperties
            props = bl_obj.ls3d_props
            # The distance is squared
            file.write("<fI", props.draw_distance ** 2, 0)

            mats = bl_obj.data.materials
            positions = []
            uvs = None
            normals = []

            mat_count = len(mats)

            no_mats = mat_count == 0
            # When the object has no material, we still have to create one submesh (material index for no-mat faces is zero)
            if no_mats:
                mat_count = 1

            submeshes = [None] * mat_count
            for i in range(mat_count):
                submeshes[i] = []

            bm = get_bmesh(bl_obj)

            # If uvs are defined
            if len(bm.loops.layers.uv):
                uv_layer = bm.loops.layers.uv[0]
                verts = bm.verts
                normals = []
                uvs = []

                # Since Blender supports per-face uv mapping, we have to adjust our mesh to 4DS-supported per-vertex uv mapping
                for face in bm.faces:
                    for loop in face.loops:

                        vert = bm.verts[loop.vert.index]

                        # Check if the vertex is already in the list
                        in_list = False
                        if vert in positions:
                            in_list = True
                            vert_index = positions.index(vert)

                            uv = loop[uv_layer].uv

                            if uv != uvs[vert_index]:
                                in_list = False

                        if in_list:
                            submeshes[face.material_index].append(vert_index)
                        else:
                            # Add a new vertex
                            submeshes[face.material_index].append(
                                len(positions))
                            positions.append(vert)
                            normals.append(
                                vert.normal if face.smooth else face.normal)
                            uvs.append(loop[uv_layer].uv)
            else:
                positions = bm.verts

                for pos in positions:
                    normals.append(pos.normal)

                for face in bm.faces:
                    submesh = submeshes[face.material_index]

                    for loop in face.loops:
                        submesh.append(loop.vert.index)

            file.write("<H", len(positions))

            for i, vert in enumerate(positions):
                file.write_vector3(vert.co)
                file.write_vector3(normals[i])

                if uvs:
                    uv = uvs[i]
                    file.write("<2f", uv[0], 1.0 - uv[1])
                else:
                    file.write("<2f", 1.0, 0.0)

            submeshes_count = 0
            for submesh in submeshes:
                if len(submesh):
                    submeshes_count += 1

            file.write("<B", submeshes_count)

            for i, submesh in enumerate(submeshes):
                face_count = len(submesh)

                if face_count:
                    face_count //= 3
                    file.write("<H", face_count)

                    for j in range(face_count):
                        index = (j * 3)
                        file.write("<H", submesh[index + 2])
                        file.write("<H", submesh[index + 1])
                        file.write("<H", submesh[index])

                    file.write(
                        "<H", 0 if no_mats else Libraries.Materials.index(mats[i]) + 1)

            bm.free()

        # Writing the base lod
        write_lod(obj.bl_obj)

        # Writing all lower lods
        if self.lods:
            for lod in self.lods:
                write_lod(lod)


class BillboardAxis(IntEnum):
    X = 0
    Z = 1
    Y = 2


class Billboard(StandardMesh):
    axis: BillboardAxis
    all_axis: bool

    def read(self, file: IStream) -> None:
        super().read(file)

        self.axis = BillboardAxis(file.read("<I"))
        self.all_axis = not file.read("<?")

    def build_bl_obj(self, obj: LS3DObject) -> bpy.types.Object:
        bl_obj = super().build_bl_obj(obj)

        props: LS3DObjectProperties
        props = bl_obj.ls3d_props
        props.mesh_type = 'BILLBOARD'
        props.billboarding_axis = 'XYZ' if self.all_axis else 'X' if self.axis == BillboardAxis.X else 'Y' if self.axis == BillboardAxis.Y else 'Z'

        return bl_obj

    def write(self, obj: LS3DObject, file: OStream) -> None:
        super().write(obj, file)

        props: LS3DObjectProperties
        props = obj.bl_obj.ls3d_props
        axis = BillboardAxis.X if props.billboarding_axis == 'X' else BillboardAxis.Y if props.billboarding_axis == 'Y' else BillboardAxis.Z

        file.write("<I?", axis, props.billboarding_axis != 'XYZ')


class MorphedLOD:
    positions: List[Vector]
    positions_indices: List[int]


class Morph:
    morphed_lods: List[MorphedLOD]

    def read(self, file: IStream) -> None:
        frame_count: int = file.read("<B")
        lod_count: int = file.read("<B")
        unknown: int = file.read("<B")

        self.morphed_lods = []
        for i in range(lod_count):
            vertices_count: int = file.read("<H")

            if vertices_count == 0:
                continue

            lod = MorphedLOD()

            lod.positions = []
            lod.positions_indices = []

            for j in range(vertices_count):
                for k in range(frame_count):
                    lod.positions.append(file.read_vector3())
                    file.stream.seek(12, 1)  # We don't need the normals

            file.read("<B")  # Unknown

            for j in range(vertices_count):
                lod.positions_indices.append(file.read("<H"))

        file.stream.seek(48, 1)  # Reserved values


class MorphMesh(StandardMesh):
    morph: Morph

    def read(self, file: IStream) -> None:
        super().read(file)
        morph = Morph()
        morph.read(file)


@dataclass
class WeightVertex:
    joint_index: int
    weight: int


@dataclass
class SingleLOD():
    weighted_vertices: List[WeightVertex]


class SingleMesh(StandardMesh):
    joints_indices = []
    joints_transformations = []
    single_lods = []

    def read(self, file: IStream) -> None:
        super().read(file)
        joints_count: int = file.read("<B")
        file.stream.seek(32, 1)  # Bounding box

        self.joints_indices = []
        self.joints_transformations = []

        for i in range(joints_count):
            self.joints_indices.append(file.read("<B"))

        for i in range(joints_count):
            self.joints_transformations.append(
                (file.read("4f"), file.read("4f"), file.read("4f"), file.read("4f")))
            file.stream.seek(32, 1)  # Bounding box

        self.single_lods = []
        for i in range(len(self.lods)):
            vertices_count: int = file.read("<I")

            weighted_vertices = []
            for j in range(vertices_count):
                weighted_vertices.append(WeightVertex(*file.read("<BB")))

            self.single_lods.append(SingleLOD(weighted_vertices))

    def build_bl_obj(self, obj: LS3DObject) -> bpy.types.Object:
        bl_obj = super().build_bl_obj(obj)
        obj.create_armature(bl_obj)

        # for i in range(len(Libraries.Joints)):
        #    mat = Matrix(self.joints_transformations[i])
        #    vgs[i][1].mesh.pose_transformation = mat

        # Tohle da presne stejnej vystup jako puvodni joints indices
        # for i in range(len(Libraries.Joints)):
        #    parent = Libraries.Objects[vgs[i][1].parent_index - 1]
        #    if parent in Libraries.Joints:
        #        print(f"F: {parent.mesh.joint_index + 1}")
        #    else:
        #        print(f"F: {0}")

        return bl_obj

    def post_create(self, obj: LS3DObject) -> None:
        super().post_create(obj)

        if self.lods:
            bl_armature = obj.armature

            for lod, single_lod in zip(self.lods, self.single_lods):
                bl_obj = lod.bl_obj

                # Create a new armature modifier
                mod = bl_obj.modifiers.new(bl_armature.name, 'ARMATURE')
                mod.object = bl_armature

                vgs = [None] * len(self.joints_indices)

                for i, joint in enumerate(Libraries.Joints):
                    vg = bl_obj.vertex_groups.new(name=joint.name)
                    vgs[joint.mesh.joint_index] = (vg, joint)

                for i in range(len(Libraries.Joints)):
                    mat = Matrix(self.joints_transformations[i])
                    vgs[i][1].mesh.pose_transformation = mat

                for i, weighted_vertex in enumerate(single_lod.weighted_vertices):
                    vg_index = weighted_vertex.joint_index - 1

                    vgs[vg_index][0].add(
                        [i], 1.0 - (weighted_vertex.weight / 256.0), 'ADD')


class SingleMorph(SingleMesh):
    morph: Morph

    def read(self, file: IStream) -> None:
        super().read(file)
        morph = Morph()
        morph.read(file)


@dataclass
class SubLens:
    unk0: float
    unk1: float
    material_index: int


class Lens(LS3DMesh):
    sublenses: List[SubLens]

    def read(self, file: IStream) -> None:
        sublenses_count: int = file.read("<B")
        self.sublenses = []

        for i in range(sublenses_count):
            self.sublenses.append(SubLens(*file.read("<2fH")))

    def build_bl_obj(self, obj: LS3DObject) -> bpy.types.Object:
        light_data = bpy.data.lights.new(name=obj.name, type='POINT')
        bl_obj = bpy.data.objects.new(obj.name, light_data)

        props: LS3DObjectProperties
        props = bl_obj.ls3d_props

        for sublens in self.sublenses:
            lens = props.lenses.add()
            lens.unknown_a = sublens.unk0
            lens.unknown_b = sublens.unk1

            if sublens.material_index:
                lens.material = Libraries.Materials[sublens.material_index - 1].bl_mat

        return bl_obj

    def write(self, obj: LS3DObject, file: OStream) -> None:
        lenses: List[LS3DLensProperty]
        lenses = obj.bl_obj.ls3d_props.lenses

        file.write("<B", len(lenses))

        for sublens in lenses:
            mat = sublens.material
            if mat:
                mat_index = Libraries.Materials.index(mat) + 1
            else:
                mat_index = 0

            file.write("<2fH", sublens.unknown_a, sublens.unknown_b, mat_index)


class Target(LS3DMesh):
    unk: int
    targets: List[int]

    def read(self, file: IStream) -> None:
        self.unk = file.read("<H")
        targets_count: int = file.read("<B")

        self.targets = []
        for i in range(targets_count):
            self.targets.append(file.read("<H"))

    def build_bl_obj(self, obj: LS3DObject) -> bpy.types.Object:
        bl_obj = bpy.data.objects.new(obj.name, None)
        bl_obj.empty_display_type = 'SPHERE'
        bl_obj.empty_display_size = 0.1

        props: LS3DObjectProperties
        props = bl_obj.ls3d_props
        props.helper_type = 'TARGET'
        props.target_unknown = self.unk

        for target in self.targets:
            t = props.targets.add()
            t.unknown = target

        return bl_obj

    def write(self, obj: LS3DObject, file: OStream) -> None:
        props: LS3DObjectProperties
        props = obj.bl_obj.ls3d_props
        targets = props.targets

        file.write("<HB", props.target_unknown, len(targets))

        for target in targets:
            file.write("<H", target.unknown)
