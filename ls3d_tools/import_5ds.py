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
from mathutils import Matrix, Quaternion, Vector

from .io_utils import IStream


def import_5ds(import_ctx: bpy.types.Context, filepath: str) -> None:

    file = IStream(filepath)

    signature = file.read("<4s")

    if signature != b'5DS\x00':
        raise IOError("Invalid 5DS signature")

    version = file.read("<H")

    if version != 122:
        raise IOError("Unsupported 5DS version")

    # Skip the filetime timestamp
    file.stream.seek(8, 1)

    dataSize = file.read("<I")
    numberOfObjects = file.read("<H")
    animRange = file.read("<H")

    # set animation range in blender scene
    bpy.context.scene.frame_start = 0
    bpy.context.scene.frame_end = animRange
    bpy.context.scene.frame_set(0)

    # read offset tabel first
    offsetObjectNames = []
    offsetObects = []
    for i in range(numberOfObjects):
        offsetObjectNames.append(file.read("<I"))
        offsetObects.append(file.read("<I"))


    for i in range(numberOfObjects):

        file.stream.seek(18 + offsetObjectNames[i], 0)
        ObjectName = file.read_C_string()
        # find object in blender scene
        obj = bpy.data.objects.get(ObjectName)
        isBone = False
        if obj is None:
            # If here, there was no object with this name
            # check if there are bones with that name
            arm = next((ob for ob in bpy.data.objects if ob.type == 'ARMATURE'), None)
            if arm:
                obj = arm.pose.bones[ObjectName]
                isBone = True
            if obj is None:
                # continue
                raise ValueError(f"Object '{ObjectName}' does not exist in scene! Have you importet the correct 4ds file?")
        
        file.stream.seek(18 + offsetObects[i], 0)

        animationFlag = file.read("<I")

        if animationFlag & 0x04:
            obj.rotation_mode = "QUATERNION"
            numberOfFrames = file.read("<H")
            frames = []

            for frame in range(numberOfFrames):
                frames.append(file.read("<H"))
             # skip padding
            filePos = file.stream.tell()
            filePos = (filePos - 18) % 16
            if filePos: file.stream.seek(16 - filePos, 1)

            for keyframe in range(numberOfFrames):
                # rotations.append(file.read_quaternion())
                # if isBone:

                #    rest_mat = obj.bone.matrix_local
                #    rest_quat = rest_mat.to_quaternion()
                #    print(rest_quat[0], rest_quat[1], rest_quat[2], rest_quat[3])
                #    file.close()
                #    return
                #    pose_quat = rest_quat.inverted() @ file.read_quaternion()

                #     obj.rotation_quaternion = pose_quat
                # else:
                obj.rotation_quaternion = file.read_quaternion()

                obj.keyframe_insert(data_path="rotation_quaternion", frame = frames[keyframe])
        if isBone: continue
        if animationFlag & 0x02:
            numberOfFrames = file.read("<H")
            frames = []

            for frame in range(numberOfFrames):
                frames.append(file.read("<H"))
             # skip padding
            if not numberOfFrames & 1:
                file.stream.seek(2, 1)

            for keyframe in range(numberOfFrames):
                if isBone:
                    rest_loc = obj.bone.matrix_local.to_translation()
                    pose_loc = file.read_vector3() - rest_loc
                    obj.location = pose_loc
                else:
                    obj.location = file.read_vector3()
                obj.keyframe_insert(data_path="location", frame=frames[keyframe])

        if animationFlag & 0x08:
            numberOfFrames = file.read("<H")
            frames = []

            for frame in range(numberOfFrames):
                frames.append(file.read("<H"))
             # skip padding
            if not numberOfFrames & 1:
                file.stream.seek(2, 1)

            for keyframe in range(numberOfFrames):
                obj.scale = file.read_vector3()
                obj.keyframe_insert(data_path="scale", frame=frames[keyframe])


    file.close()
    # do this, otherwise it will look wrong
    bpy.context.view_layer.update()

def load_5ds(import_ctx: bpy.types.Context, filepath: str) -> Set[str]:
    import_5ds(import_ctx, filepath)

    return {'FINISHED'}