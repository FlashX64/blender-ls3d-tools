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

from typing import Optional, Set
import bpy
from bpy.props import (
        StringProperty,
        BoolProperty,
        IntProperty,
        FloatProperty,
        FloatVectorProperty,
        EnumProperty,
        CollectionProperty,
        PointerProperty,
        )

from bpy_extras.node_utils import find_node_input

NODE_DIFFUSE = "DiffuseTex"
NODE_ALPHA = "AlphaTex"
NODE_ENVIRONMENT = "EnvironmentTex"
NODE_OUTPUT = "LS3DOutput"
NODE_SHADER = "LS3DShader"

def get_image_from_node(node: bpy.types.Node, input_name: str) -> Optional[bpy.types.Image]:
    input = find_node_input(node, input_name)
    if input:
        for link in input.links:
            node = link.from_node
            if node:
                if isinstance(node, bpy.types.ShaderNodeTexImage):
                    return node.image
    return None

def panel_tex_image_draw(layout: bpy.types.UILayout, ntree: bpy.types.NodeTree, node_name: str) -> None:
    # Look for needed image node
    if node_name in ntree.nodes:
        node = ntree.nodes[node_name]
        layout.template_image(node, "image", node.image_user)
    else:
        layout.label(text="Incompatible image node")

def create_ls3d_material(material: bpy.types.Material) -> None:
    material.use_nodes = True
    props = material.ls3d_props
    ntree = material.node_tree
    ntree.nodes.clear()

    # Output node
    output = ntree.nodes.new(type="ShaderNodeOutputMaterial")
    output.name = NODE_OUTPUT
    output.location = (300, 0)

    # Shader node
    bsdf = ntree.nodes.new(type="ShaderNodeBsdfPrincipled")
    bsdf.name = NODE_SHADER
    bsdf.inputs["Specular"].default_value = 0.0
    ntree.links.new(output.inputs["Surface"], bsdf.outputs["BSDF"])

    # Diffuse TexImage
    diffuse = ntree.nodes.new(type="ShaderNodeTexImage")
    diffuse.name = NODE_DIFFUSE
    diffuse.location = (-300, -80)

    # Alpha TexImage
    alpha = ntree.nodes.new(type="ShaderNodeTexImage")
    alpha.name = NODE_ALPHA
    alpha.location = (-300, -437)

    # Environment TexImage
    environment = ntree.nodes.new(type="ShaderNodeTexImage")
    environment.name = NODE_ENVIRONMENT
    environment.location = (-600, -80)

    # Linking
    if props.diffuse_texture:
        ntree.links.new(bsdf.inputs["Base Color"], diffuse.outputs["Color"])

    if props.alpha_texture and not props.diffuse_alpha:
        ntree.links.new(bsdf.inputs["Alpha"], alpha.outputs["Color"])
        material.blend_method = 'BLEND'
    elif props.diffuse_alpha:
        ntree.links.new(bsdf.inputs["Alpha"], diffuse.outputs["Alpha"])
        material.blend_method = 'BLEND'

class LS3DConvertMaterial(bpy.types.Operator):
    bl_idname = "material.ls3d_convert_material"
    bl_label = "Convert to LS3D material"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return context.active_object.active_material is not None

    def execute(self, context: bpy.types.Context) -> Set[str]:
        obj = context.active_object
        material = obj.active_material

        diffuse_image = alpha_image = diffuse_color = None

        if material.use_nodes:
            ntree = material.node_tree

            if "Principled BSDF" in ntree.nodes:
                bsdf = ntree.nodes["Principled BSDF"]

                if "Base Color" in bsdf.inputs:
                    diffuse_color = bsdf.inputs["Base Color"].default_value

                diffuse_image = get_image_from_node(bsdf, "Base Color")
                alpha_image = get_image_from_node(bsdf, "Alpha")

        create_ls3d_material(material)

        if diffuse_image:
            ntree.nodes[NODE_DIFFUSE].image = diffuse_image
        
        if alpha_image:
            ntree.nodes[NODE_ALPHA].image = alpha_image

        if diffuse_color:
            ntree.nodes[NODE_SHADER].inputs["Base Color"].default_value = diffuse_color

        return {'FINISHED'}

class LS3DAnimatedMapProperties(bpy.types.PropertyGroup):
    frame_count: IntProperty(
        name="Frames",
        description="Total amount of animated frames",
        min=1,
        default=1
    )

    frame_time: IntProperty(
        name="Frame time",
        description="Frame period in miliseconds",
        min=1,
        default=1000,
        step=10
    )

    unknown_a: IntProperty(
        name="Unknown",
        description=""
    )

    unknown_b: IntProperty(
        name="Unknown",
        description=""
    )

    unknown_c: IntProperty(
        name="Unknown",
        description=""
    )
    
def update_diffuse_texture(self, context: bpy.types.Context) -> None:
    if not context.active_object:
        return

    material = context.active_object.active_material

    if material:
        props = material.ls3d_props

        ntree = material.node_tree

        if NODE_SHADER in ntree.nodes:
            shader_node = ntree.nodes[NODE_SHADER]

            if not props.diffuse_texture:

                input = find_node_input(shader_node, "Base Color")

                if input:
                    for link in input.links:
                        node = link.from_node

                        if node:
                            ntree.links.remove(link)
            else:
                if NODE_DIFFUSE in ntree.nodes:
                    diffuse_node = ntree.nodes[NODE_DIFFUSE]

                    ntree.links.new(shader_node.inputs["Base Color"], diffuse_node.outputs["Color"])

def update_alpha_texture(self, context: bpy.types.Context) -> None:
    if not context.active_object:
        return

    material = context.active_object.active_material

    if material:
        props = material.ls3d_props

        ntree = material.node_tree

        if NODE_SHADER in ntree.nodes:
            shader_node = ntree.nodes[NODE_SHADER]

            if not props.alpha_texture and not props.diffuse_alpha:
                material.blend_method = 'OPAQUE'

                input = find_node_input(shader_node, "Alpha")

                if input:
                    for link in input.links:
                        node = link.from_node

                        if node:
                            ntree.links.remove(link)
            else:
                material.blend_method = 'BLEND'

                if props.alpha_texture and not props.diffuse_alpha:
                    if NODE_ALPHA in ntree.nodes:
                        alpha_node = ntree.nodes[NODE_ALPHA]

                        ntree.links.new(shader_node.inputs["Alpha"], alpha_node.outputs["Color"])
                else:
                    if NODE_DIFFUSE in ntree.nodes:
                        diffuse_node = ntree.nodes[NODE_DIFFUSE]

                        ntree.links.new(shader_node.inputs["Alpha"], diffuse_node.outputs["Alpha"])


class LS3DMaterialProperties(bpy.types.PropertyGroup):
    ambient_color: FloatVectorProperty(
        name="Ambient Color",
        subtype='COLOR',
        size=4,
        default=(0.8, 0.8, 0.8, 1.0)
    )

    specular_color: FloatVectorProperty(
        name="Specular Color",
        subtype='COLOR',
        size=4,
        default=(0.8, 0.8, 0.8, 1.0)
    )

    coloring: BoolProperty(
        name="Coloring",
        description="Enables diffuse and emission colors",
        default=False
    )

    mipmapping: BoolProperty(
        name="Mipmapping",
        description="Enables generation of mipmaps",
        default=True
    )

    diffuse_alpha: BoolProperty(
        name="Diffuse Alpha",
        description="Enables diffuse texture alpha channel (TGA textures only)",
        default=False,
        update=update_alpha_texture
    )

    additive_blending: BoolProperty(
        name="Additive Blending",
        description="",
        default=False
    )

    color_keying: BoolProperty(
        name="Color Keying",
        description="First color in the texture color table represents a color, which is replaced by alpha (16bpp BMP textures only). Not shown in Blender",
        default=False
    )

    texture_animation: BoolProperty(
        name="Diffuse Animation",
        description="The diffuse texture is represented by a group of more individual texture frames",
        default=False
    )

    anm_props: PointerProperty(type=LS3DAnimatedMapProperties)

    diffuse_texture: BoolProperty(
        name="Diffuse Texture",
        description="Enables diffuse mapping",
        default=False,
        update=update_diffuse_texture
    )

    alpha_texture: BoolProperty(
        name="Alpha Texture",
        description="Enables alpha mapping",
        default=False,
        update=update_alpha_texture
    )

    env_texture: BoolProperty(
        name="Environment Texture",
        description="Enables environment mapping (not shown in Blender)",
        default=False,
    )

    env_base_mixing: BoolProperty(
        name="Base Environment Mixing",
        description="Diffuse and environment textures are mixed in defined ratio",
        default=False,
    )

    env_ratio: FloatProperty(
        name="Mixing Ratio",
        description="",
        default=0.5,
        min=0.0,
        max=1.0
    )

    env_mix_type: EnumProperty(
        name="Mixing Method",
        description="Mixing method",
        default='NONE',
        items=[
            ('NONE', "None", ""),
            ('MULTIPLY', "Multiplication", "Diffuse and environment textures are mixed by multiplication"),
            ('ADD', "Addition", "Diffuse and environment textures are mixed by addition")
        ]
    )

    env_projection_axis: EnumProperty(
        name="Projection Axis",
        description="Environment texture projection axis",
        default='NONE',
        items=[
            ('NONE', "None", ""),
            ('Y', "Y", ""),
            ('Z', "Z", ""),
            ('YZ', "YZ", "")
        ]
    )
    

class LS3D_PT_MaterialPanel(bpy.types.Panel):
    bl_label = "LS3D Material"
    bl_idname = "SCENE_PT_ls3d_material"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return context.active_object.active_material != None

    def draw(self, context: bpy.types.Context) -> None:
        material = context.active_object.active_material
        props = material.ls3d_props

        layout = self.layout

        split = layout.split()

        row = layout.row()
        row.prop(props, "mipmapping")
        row.prop(props, "coloring")

        row = layout.row()
        row.prop(material, "use_backface_culling")
        row.prop(props, "additive_blending")

        row = layout.row()
        row.prop(props, "color_keying")
        row.prop(props, "diffuse_alpha")

        ntree = material.node_tree

        if NODE_SHADER in ntree.nodes:
            shader_node = ntree.nodes[NODE_SHADER]

            # Colors
            layout.prop(props, "ambient_color")
            layout.prop(shader_node.inputs["Base Color"], "default_value", text="Diffuse color")
            layout.prop(props, "specular_color")
            layout.prop(shader_node.inputs["Emission"], "default_value", text="Emission color")

            # Opacity
            row = layout.row()
            row.prop(shader_node.inputs["Alpha"], "default_value", text="Opacity")
            row.prop(shader_node.inputs["Metallic"], "default_value", text="Glossiness")

        else:
            row = layout.row()
            row.alignment = 'CENTER'
            row.label(text="Incompatible shader", icon='ERROR')
            layout.operator("material.ls3d_convert_material")

class LS3D_PT_AnimatedMapPanel(bpy.types.Panel):
    bl_label = "Animated Texture"
    bl_idname = "SCENE_PT_ls3d_animated_map"
    bl_parent_id = "SCENE_PT_ls3d_material"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"
    bl_order = 1
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context: bpy.types.Context) -> None:
        material = context.active_object.active_material

        props = material.ls3d_props
        anm_props = props.anm_props

        layout = self.layout

        layout.prop(material.ls3d_props, "texture_animation")

        split = layout.split()
        col = split.column()

        col.enabled = props.texture_animation

        row = col.row()
        row.prop(props.anm_props, "frame_count")
        row.prop(props.anm_props, "frame_time")

        col.prop(props.anm_props, "unknown_a")
        col.prop(props.anm_props, "unknown_b")
        col.prop(props.anm_props, "unknown_c")

class LS3D_PT_MapsPanel(bpy.types.Panel):
    bl_label = "Maps"
    bl_idname = "SCENE_PT_ls3d_maps"
    bl_parent_id = "SCENE_PT_ls3d_material"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"
    bl_order = 0

    def draw(self, context: bpy.types.Context) -> None:
        material = context.active_object.active_material
        props = material.ls3d_props

        layout = self.layout

        ntree = material.node_tree
        output_node = ntree.get_output_node('EEVEE')

        if output_node:
            if output_node.name == NODE_OUTPUT:
                # Diffuse texture
                row = layout.row()
                row.label(text="Diffuse texture:", icon='TEXTURE')
                row.prop(props, "diffuse_texture", text="", icon='NODE_MATERIAL')
                layout.separator(factor=1.0)
                panel_tex_image_draw(layout, ntree, NODE_DIFFUSE)

                layout.separator(factor=4.0)

                # Alpha texture
                row = layout.row()
                row.label(text="Alpha texture:", icon='TEXTURE')
                row.prop(props, "alpha_texture", text="", icon='NODE_MATERIAL')
                layout.separator(factor=1.0)
                panel_tex_image_draw(layout, ntree, NODE_ALPHA)

                layout.separator(factor=4.0)

                # Environment texture
                row = layout.row()
                row.label(text="Environment texture:", icon='TEXTURE')
                row.prop(props, "env_texture", text="", icon='NODE_MATERIAL')
                layout.separator(factor=1.0)
                panel_tex_image_draw(layout, ntree, NODE_ENVIRONMENT)
                
                layout.alignment = 'RIGHT'
                layout.prop(props, "env_base_mixing")
                row = layout.row()
                row.label(text="Overlay Mixing Ratio")
                row.prop(props, "env_ratio", text="", slider=True)
                row.enabled = props.env_base_mixing
                layout.prop(props, "env_mix_type")
            else:
                layout.label(text="Incompatible output node", icon='ERROR')
        else:
            layout.label(text="No output node", icon='ERROR')