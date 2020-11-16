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

bl_info = {
    "name" : "LS3D tools",
    "author" : "Filip Vencelides",
    "description" : "Import-Export native LS3D engine v5.559 formats",
    "blender" : (2, 90, 0),
    "version" : (0, 0, 1),
    "location" : "File > Import-Export",
    "warning" : "",
    "category" : "Import-Export"
}

import bpy
from bpy_extras.io_utils import ImportHelper, ExportHelper
from bpy.props import StringProperty
from bpy.types import Operator

from .ls3d_object import(
    LS3DObjectProperties,
    LS3DObjectProperty,
    LS3D_PT_ObjectPanel,
    LS3D_UL_ls3d_props,
    LS3DAddProperty,
    LS3DRemoveProperty,
    LS3DDistanceFromCamera
)

from .ls3d_sector import(
    LS3DSectorProperties
)

from .ls3d_portal import(
    LS3DPortalProperties,
    LS3D_PT_PortalPanel
)

from .ls3d_mirror import(
    LS3DMirrorProperties,
    LS3D_PT_MirrorPanel
)

from .ls3d_lens import(
    LS3DLensProperty,
    LS3D_UL_ls3d_lenses,
    LS3DAddLens,
    LS3DRemoveLens
)

from .ls3d_target import(
    LS3DTargetProperty,
    LS3D_UL_ls3d_targets,
    LS3DAddTarget,
    LS3DRemoveTarget
)

from .ls3d_material import(
    LS3DMaterialProperties,
    LS3DAnimatedMapProperties,
    LS3D_PT_MaterialPanel,
    LS3D_PT_MapsPanel,
    LS3D_PT_AnimatedMapPanel,
    LS3DConvertMaterial
)

from .ls3d_helpers import(
    LS3DHidePortals,
    LS3DShowPortals,
    LS3DHideSectors,
    LS3DShowSectors,
    LS3DHideOccluders,
    LS3DShowOccluders,
    LS3DShowLods,
    LS3DHideLods,
    LS3D_PT_HelperPanel
)

class Import4DS(Operator, ImportHelper):
    """Load a LS3D 4DS file"""
    bl_idname = "import_scene.4ds"
    bl_label = "Import 4DS"

    filename_ext = ".4ds"

    filter_glob: StringProperty(
        default="*.4ds",
        options={'HIDDEN'}
    )

    def execute(self, context):
        from . import import_4ds
        return import_4ds.load_4ds(self, self.filepath)

def menu_func_import(self, context):
    self.layout.operator(Import4DS.bl_idname, text="LS3D 4DS (.4ds)")

class Export4DS(Operator, ExportHelper):
    """Save a LS3D 4DS file"""
    bl_idname = "export_scene.4ds"
    bl_label = "Export 4DS"

    filename_ext = ".4ds"

    filter_glob: StringProperty(
        default="*.4ds",
        options={'HIDDEN'}
    )

    def execute(self, context):
        from . import export_4ds

        return export_4ds.save_4ds(context, self.filepath)

def menu_func_export(self, context):
    self.layout.operator(Export4DS.bl_idname, text="LS3D 4DS (.4ds)")

classes = [
    LS3DObjectProperty,
    LS3DLensProperty,
    LS3DTargetProperty,
    LS3DSectorProperties,
    LS3DPortalProperties,
    LS3DMirrorProperties,
    LS3DObjectProperties,

    LS3DAnimatedMapProperties,
    LS3DMaterialProperties,

    LS3D_UL_ls3d_props,
    LS3D_UL_ls3d_lenses,
    LS3D_UL_ls3d_targets,

    LS3DAddProperty,
    LS3DRemoveProperty,
    LS3DAddLens,
    LS3DRemoveLens,
    LS3DAddTarget,
    LS3DRemoveTarget,
    LS3DDistanceFromCamera,
    LS3DConvertMaterial,

    LS3DHidePortals,
    LS3DShowPortals,
    LS3DHideSectors,
    LS3DShowSectors,
    LS3DHideOccluders,
    LS3DShowOccluders,
    LS3DHideLods,
    LS3DShowLods,

    LS3D_PT_ObjectPanel,
    LS3D_PT_PortalPanel,
    LS3D_PT_MirrorPanel,
    LS3D_PT_MaterialPanel,
    LS3D_PT_MapsPanel,
    LS3D_PT_AnimatedMapPanel,
    LS3D_PT_HelperPanel,

    Import4DS,
    Export4DS
]

def register():    
    for cls in classes:
        bpy.utils.register_class(cls)

    # Initialize LS3D properties
    bpy.types.Object.ls3d_props = bpy.props.PointerProperty(type=LS3DObjectProperties)
    bpy.types.Material.ls3d_props = bpy.props.PointerProperty(type=LS3DMaterialProperties)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    # Remove LS3D properties
    del bpy.types.Object.ls3d_props
    del bpy.types.Material.ls3d_props

    for cls in classes:
        bpy.utils.unregister_class(cls)

    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()