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

from datetime import datetime

from .io_utils import OStream

def get_all_fcurves(action):
    """Blender 5.0 hotfix using channelbags instead of read from fcurves directly"""
    fcurves = []

    if not action:
        return fcurves

    for layer in action.layers:
        for strip in layer.strips:
            # Each can contain multiple channelbags
            for channelbag in strip.channelbags:
                for fc in channelbag.fcurves:
                    fcurves.append(fc)

    return fcurves

def export_5ds(filepath: str) -> None:

    # get frame range, which should always start at zero
    # if frames are set before 0 they will be ignored
    start_frame = 0

    # TODO: In the future we may wanna check if end frame is below 65535, the format wont support more than that
    end_frame = int(bpy.context.scene.frame_end)

    num_objects = 0
    per_obj_data = []

    for obj in bpy.data.objects:
        ad = obj.animation_data
        if not (ad and ad.action):
            continue

        fcurves = get_all_fcurves(ad.action)

        if not fcurves:
            continue

        if not any(len(fc.keyframe_points) for fc in fcurves):
            continue

        num_objects = num_objects + 1

        rot_frames = set()
        loc_frames = set()
        scale_frames = set()

        for fc in fcurves:
            path = fc.data_path
            for kp in fc.keyframe_points:
                framei = int(round(kp.co.x))
                if not (start_frame <= framei <= end_frame):
                    continue

                if path.endswith('rotation_quaternion'):
                    rot_frames.add(framei)
                elif path.endswith('rotation_euler'):
                    rot_frames.add(framei)
                elif path.endswith('rotation_axis_angle'):
                    rot_frames.add(framei)
                elif path.endswith('location'):
                    loc_frames.add(framei)
                elif path.endswith('scale'):
                    scale_frames.add(framei)

        per_obj_data.append({
            'obj': obj,
            'rot_frames': sorted(rot_frames),
            'loc_frames': sorted(loc_frames),
            'scale_frames': sorted(scale_frames),
            })


    file = OStream(filepath)

    file.stream.write(b'5DS\x00')
    file.write("<H", 122)

    filetime = int(datetime.timestamp(datetime.now())) * 10000000 + 116444736000000000 # Datetime * hundreds of nanoseconds + epoch as filetime
    file.write("<Q", filetime)

    # placeholder for file size, we will come back in the end when known
    file.write("<I", 0)

    file.write("<H", num_objects)
    file.write("<H", end_frame)

    # offset table placeholder start
    offset_table_start = file.stream.tell()
    for _ in range(num_objects):
        file.write("<I", 0) # placeholder for offset names,
        file.write("<I", 0) # placeholder for offset data

    # for some reason there is always an empty integer here
    file.write("<I", 0)

    # some empty arrays that we need to patch the offsets later
    name_offsets = [0] * num_objects
    data_offsets = [0] * num_objects

    # when export is done, we use this to set previous selection
    depsgraph = bpy.context.evaluated_depsgraph_get()
    orig_frame = bpy.context.scene.frame_current

    try:
        for idx, info in enumerate(per_obj_data):
            obj = info['obj']
            rot_frames = info['rot_frames']
            loc_frames = info['loc_frames']
            scale_frames = info['scale_frames']

            # mark start of this object's data block (absolute file position)
            data_offsets[idx] = file.stream.tell() - 18 # store relative-to-18 as importer expects 

            # animationFlag which transforms are used: translation and or rotation and or scale
            animationFlag = 0
            if loc_frames:
                animationFlag |= 0x02
            if rot_frames:
                animationFlag |= 0x04
            if scale_frames:
                animationFlag |= 0x08

            # animationFlag has the bits set, writing it out now
            file.write("<I", animationFlag)

            # In the files it always starts with rotation, if bit is set
            if animationFlag & 0x04:
                numberOfFrames = len(rot_frames)
                file.write("<H", numberOfFrames)
                # write frame names
                for fr in rot_frames:
                    file.write("<H", fr)

                # pad so that (current_pos - 18) % 16 == 0
                cur = file.stream.tell()
                offset_from_18 = (cur - 18) % 16
                if offset_from_18 != 0:
                    pad = 16 - offset_from_18
                    for _ in range(pad):
                        file.write("<B",0)
                    
                # write quaternion data per keyframe (w, x, y, z floats)
                for fr in rot_frames:
                    bpy.context.scene.frame_set(fr)
                    depsgraph.update()
                    obj_eval = obj.evaluated_get(depsgraph)
                    quat = obj_eval.matrix_basis.to_quaternion()
                    file.write_quaternion(quat)

            # Translation block
            if animationFlag & 0x02:
                numberOfFrames = len(loc_frames)
                file.write("<H", numberOfFrames)
                for fr in loc_frames:
                    file.write("<H", fr)

                # if numberOfFrames is even -> write two zero bytes
                if not (numberOfFrames & 1):
                    file.write("<H", 0)

                for fr in loc_frames:
                    bpy.context.scene.frame_set(fr)
                    depsgraph.update()
                    obj_eval = obj.evaluated_get(depsgraph)
                    loc = obj_eval.matrix_basis.to_translation()
                    file.write_vector3(loc)   

            # Scale block
            if animationFlag & 0x08:
                numberOfFrames = len(scale_frames)
                file.write("<H", numberOfFrames)
                for fr in scale_frames:
                    file.write("<H", fr)

                # if numberOfFrames is even -> write two zero bytes
                if not (numberOfFrames & 1):
                    file.write("<H", 0)

                for fr in scale_frames:
                    bpy.context.scene.frame_set(fr)
                    depsgraph.update()
                    obj_eval = obj.evaluated_get(depsgraph)
                    sc = obj_eval.matrix_basis.to_scale()
                    file.write_vector3(sc) 

        # Now that all datablocks are written, we can add all the object names to the end
        for idx, info in enumerate(per_obj_data):
            name_offsets[idx] = file.stream.tell() - 18
            file.write_string(str(info['obj'].name).encode("ascii", errors="replace").decode("ascii"))
            file.write("<B", 0)


        # All animation data written. Now we know the full file size
        # so lets patch the data size the format expects
        eof = file.stream.tell()
        file.stream.seek(14,0)
        file.write("<I", eof - 18)

        # At last, dont forget to patch the offset table
        file.stream.seek(offset_table_start,0)
        for i in range(num_objects):
            file.write("<I", name_offsets[i])
            file.write("<I", data_offsets[i])

    finally:
        # select frame again that user may have viewed
        bpy.context.scene.frame_set(orig_frame)
        file.close()

def save_5ds(context: bpy.types.Context, filepath: str) -> Set[str]:
    export_5ds(filepath)

    return {'FINISHED'}