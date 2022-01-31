# Copyright (c) 2020 BlenderNPR and contributors. MIT license.

from os import path

from Malt.GL.GL import *
from Malt.GL.RenderTarget import RenderTarget
from Malt.GL.Texture import Texture

from Malt.Render import Common
from Malt.Render import DepthToCompositeDepth
from Malt.Render import Lighting as Lighting
from Malt.Render import Line
from Malt.Render import Sampling

from Malt.Pipelines.NPR_Pipeline import NPR_Lighting

from Malt.Parameter import Parameter
from Malt.Pipeline import *


_DEFAULT_SHADER = None

_DEFAULT_SHADER_SRC='''
#include "Pipelines/NPR_Pipeline.glsl"

void COMMON_PIXEL_SHADER(Surface S, inout PixelOutput PO)
{
    PO.color.rgb = vec3(1,1,0);
}
'''

_BLEND_TRANSPARENCY_SHADER = None

_BLEND_TRANSPARENCY_SHADER_SRC='''
#include "Passes/BlendTransparency.glsl"
'''

class NPR_Pipeline(Pipeline):

    def __init__(self):
        super().__init__()

        self.sampling_grid_size = 2
        self.samples = None

        self.parameters.world['Background.Color'] = Parameter((0.5,0.5,0.5,1), Type.FLOAT, 4)
        self.parameters.scene['Line.Max Width'] = Parameter(10, Type.INT)
        self.parameters.scene['Samples.Grid Size'] = Parameter(8, Type.INT)
        self.parameters.scene['Samples.Grid Size @ Preview'] = Parameter(4, Type.INT)
        self.parameters.scene['Samples.Width'] = Parameter(1.5, Type.FLOAT)
        self.parameters.scene['ShadowMaps.Sun.Cascades.Distribution Scalar'] = Parameter(0.9, Type.FLOAT)
        self.parameters.scene['ShadowMaps.Sun.Cascades.Count'] = Parameter(4, Type.INT)
        self.parameters.scene['ShadowMaps.Sun.Cascades.Count @ Preview'] = Parameter(2, Type.INT)
        self.parameters.scene['ShadowMaps.Sun.Cascades.Max Distance'] = Parameter(100, Type.FLOAT)
        self.parameters.scene['ShadowMaps.Sun.Cascades.Max Distance @ Preview'] = Parameter(25, Type.FLOAT)
        self.parameters.scene['ShadowMaps.Sun.Resolution'] = Parameter(2048, Type.INT)
        #self.parameters.scene['ShadowMaps.Sun.Resolution @ Preview'] = Parameter(512, Type.INT)
        self.parameters.scene['ShadowMaps.Spot.Resolution'] = Parameter(2048, Type.INT)
        self.parameters.scene['ShadowMaps.Spot.Resolution @ Preview'] = Parameter(512, Type.INT)
        self.parameters.scene['ShadowMaps.Point.Resolution'] = Parameter(2048, Type.INT)
        self.parameters.scene['ShadowMaps.Point.Resolution @ Preview'] = Parameter(512, Type.INT)
        self.parameters.scene['Transparency.Layers'] = Parameter(4, Type.INT)
        self.parameters.scene['Transparency.Layers @ Preview'] = Parameter(1, Type.INT)
        
        self.parameters.world['Material Override'] = MaterialParameter('', 'mesh')
        
        self.parameters.light['Shader'] = MaterialParameter('', 'light')
        self.parameters.light['Light Group'] = Parameter(1, Type.INT)
        
        self.parameters.material['Light Groups.Light'] = Parameter([1,0,0,0], Type.INT, 4, 'mesh')
        self.parameters.material['Light Groups.Shadow'] = Parameter([1,0,0,0], Type.INT, 4, 'mesh')

        global _DEFAULT_SHADER
        if _DEFAULT_SHADER is None: _DEFAULT_SHADER = self.compile_material_from_source('mesh', _DEFAULT_SHADER_SRC)
        self.default_shader = _DEFAULT_SHADER

        global _BLEND_TRANSPARENCY_SHADER
        if _BLEND_TRANSPARENCY_SHADER is None: _BLEND_TRANSPARENCY_SHADER = self.compile_shader_from_source(_BLEND_TRANSPARENCY_SHADER_SRC)
        self.blend_transparency_shader = _BLEND_TRANSPARENCY_SHADER

        self.common_buffer = Common.CommonBuffer()
        self.lights_buffer = Lighting.get_lights_buffer()
        self.light_groups_buffer = NPR_Lighting.NPR_LightsGroupsBuffer()
        self.shadowmaps_opaque, self.shadowmaps_transparent = NPR_Lighting.get_shadow_maps()
        self.custom_light_shading = NPR_Lighting.NPR_LightShaders()

        self.line_rendering = Line.LineRendering()

        self.composite_depth = DepthToCompositeDepth.CompositeDepth()

        self.layer_queries = None

    def compile_material_from_source(self, material_type, source, include_paths=[]):
        if material_type == 'mesh':
            return self.compile_shaders_from_source(source, include_paths, {
                'PRE_PASS': ['IS_MESH_SHADER','PRE_PASS'],
                'MAIN_PASS': ['IS_MESH_SHADER','MAIN_PASS'],
                'SHADOW_PASS': ['IS_MESH_SHADER','SHADOW_PASS'],
            })
        elif material_type == 'screen':
            return self.compile_shaders_from_source(source, include_paths, {
                'SHADER': ['IS_SCREEN_SHADER'],
            })
        elif material_type == 'light':
            return self.compile_shaders_from_source(source, include_paths, {
                'SHADER': ['IS_LIGHT_SHADER'],
            })
        else:
            return 'Invalid material type. Valid extensions are .mesh.glsl, .light.glsl and .screen.glsl'
    
    def setup_render_targets(self, resolution):
        self.t_depth = Texture(resolution, GL_DEPTH_COMPONENT32F)
        
        self.t_prepass_normal_depth = Texture(resolution, GL_RGBA32F)
        self.t_prepass_id = Texture(resolution, GL_R32F, min_filter=GL_NEAREST, mag_filter=GL_NEAREST)
        self.fbo_prepass = RenderTarget([self.t_prepass_normal_depth, self.t_prepass_id], self.t_depth)
        
        self.t_last_layer_id = Texture(resolution, GL_R32F, min_filter=GL_NEAREST, mag_filter=GL_NEAREST)
        self.fbo_last_layer_id = RenderTarget([self.t_last_layer_id])
        
        self.t_main_color = Texture(resolution, GL_RGBA16F)
        self.t_line_color = Texture(resolution, GL_RGBA16F)
        self.t_line_data = Texture(resolution, GL_RGB16F)
        self.fbo_main = RenderTarget([self.t_main_color, self.t_line_color, self.t_line_data], self.t_depth)

        self.t_opaque_color = Texture(resolution, GL_RGBA16F)
        self.t_opaque_depth = Texture(resolution, GL_DEPTH_COMPONENT32F)
        self.fbo_opaque = RenderTarget([self.t_opaque_color], self.t_opaque_depth)

        self.t_transparent_color = Texture(resolution, GL_RGBA16F)
        self.t_transparent_depth = Texture(resolution, GL_DEPTH_COMPONENT32F)
        self.fbo_transparent = RenderTarget([self.t_transparent_color], self.t_transparent_depth)

        self.t_color = Texture(resolution, GL_RGBA16F)
        self.fbo_color = RenderTarget([self.t_color])

        self.t_color_accumulate = Texture(resolution, GL_RGBA32F)
        self.fbo_accumulate = RenderTarget([self.t_color_accumulate])

    def get_samples(self, width=1.0):
        if self.samples is None:
            self.samples = Sampling.get_RGSS_samples(self.sampling_grid_size, width)
        return self.samples

    def do_render(self, resolution, scene, is_final_render, is_new_frame):
        #SETUP SAMPLING
        if self.sampling_grid_size != scene.parameters['Samples.Grid Size']:
            self.sampling_grid_size = scene.parameters['Samples.Grid Size']
            self.samples = None

        if is_new_frame:
            self.fbo_accumulate.clear([(0,0,0,0)])
        self.fbo_opaque.clear([(0,0,0,0)])
        self.fbo_color.clear([(0,0,0,0)])
        
        sample_offset = self.get_samples(scene.parameters['Samples.Width'])[self.sample_count]

        material_override = scene.world_parameters['Material Override']
        if material_override:
            scene.world_parameters['Material Override'] = None
            scene.materials = [material_override]
            for object in scene.objects:
                object.material = material_override
            scene.batches = self.build_scene_batches(scene.objects)
        
        #SETUP SCENE BATCHES
        opaque_batches = {}
        transparent_batches = {}
        for material, meshes in scene.batches.items():
            if material and material.shader:
                if material.shader['MAIN_PASS'].uniforms['Settings.Transparency'].value[0] == True:
                    transparent_batches[material] = meshes
                    continue
            opaque_batches[material] = meshes

        #SETUP UNIFORM BLOCKS
        self.common_buffer.load(scene, resolution, sample_offset, self.sample_count)
        self.lights_buffer.load(scene, 
            scene.parameters['ShadowMaps.Sun.Cascades.Count'], 
            scene.parameters['ShadowMaps.Sun.Cascades.Distribution Scalar'],
            scene.parameters['ShadowMaps.Sun.Cascades.Max Distance'])
        self.light_groups_buffer.load(scene)
        self.shadowmaps_opaque.load(scene,
            scene.parameters['ShadowMaps.Spot.Resolution'],
            scene.parameters['ShadowMaps.Sun.Resolution'],
            scene.parameters['ShadowMaps.Point.Resolution'],
            scene.parameters['ShadowMaps.Sun.Cascades.Count'])
        self.shadowmaps_transparent.load(scene,
            scene.parameters['ShadowMaps.Spot.Resolution'],
            scene.parameters['ShadowMaps.Sun.Resolution'],
            scene.parameters['ShadowMaps.Point.Resolution'],
            scene.parameters['ShadowMaps.Sun.Cascades.Count'])
        
        UBOS = {
            'COMMON_UNIFORMS' : self.common_buffer,
            'SCENE_LIGHTS' : self.lights_buffer
        }

        #RENDER SHADOWMAPS
        def render_shadow_passes(lights, fbos_opaque, fbos_transparent, sample_offset = sample_offset):
            for light_index, light_matrices_pair in enumerate(lights.items()):
                light, matrices = light_matrices_pair
                for matrix_index, camera_projection_pair in enumerate(matrices): 
                    camera, projection = camera_projection_pair
                    i = light_index * len(matrices) + matrix_index
                    self.common_buffer.load(scene, fbos_opaque[i].resolution, sample_offset, self.sample_count, camera, projection)
                    def get_light_group_batches(batches):
                        result = {}
                        for material, meshes in batches.items():
                            if material and light.parameters['Light Group'] in material.parameters['Light Groups.Shadow']:
                                result[material] = meshes
                        return result
                    self.draw_scene_pass(fbos_opaque[i], get_light_group_batches(opaque_batches), 
                        'SHADOW_PASS', self.default_shader['SHADOW_PASS'], UBOS)
                    self.draw_scene_pass(fbos_transparent[i], get_light_group_batches(transparent_batches), 
                        'SHADOW_PASS', self.default_shader['SHADOW_PASS'], UBOS)
        
        render_shadow_passes(self.lights_buffer.spots,
            self.shadowmaps_opaque.spot_fbos, self.shadowmaps_transparent.spot_fbos)
        
        glEnable(GL_DEPTH_CLAMP)
        render_shadow_passes(self.lights_buffer.suns,
            self.shadowmaps_opaque.sun_fbos, self.shadowmaps_transparent.sun_fbos)
        glDisable(GL_DEPTH_CLAMP)

        render_shadow_passes(self.lights_buffer.points,
            self.shadowmaps_opaque.point_fbos, self.shadowmaps_transparent.point_fbos, (0,0))

        #SCENE RENDER
        #Load scene camera settings
        self.common_buffer.load(scene, resolution, sample_offset, self.sample_count)

        result = self.draw_layer(opaque_batches, scene, scene.world_parameters['Background.Color'])

        self.copy_textures(self.fbo_opaque, [result], self.t_depth)
        
        self.fbo_transparent.clear([(0,0,0,0)], -1)
        self.fbo_last_layer_id.clear([0])

        transparency_layers_count = scene.parameters['Transparency.Layers']
        self.layer_queries = gl_buffer(GL_UNSIGNED_INT, transparency_layers_count)
        glGenQueries(transparency_layers_count, self.layer_queries)

        for i in range(transparency_layers_count):
            if i > 0:
                glBeginConditionalRender(self.layer_queries[i-1], GL_QUERY_WAIT)
            result = self.draw_layer(transparent_batches, scene, prepass_query=self.layer_queries[i])
            self.copy_textures(self.fbo_last_layer_id, [self.t_prepass_id])

            self.blend_transparency_shader.textures['IN_BACK'] = result
            self.blend_transparency_shader.textures['IN_FRONT'] = self.t_transparent_color
            self.draw_screen_pass(self.blend_transparency_shader, self.fbo_color)
            
            self.copy_textures(self.fbo_transparent, [self.t_color], self.t_depth)
            if i > 0:
                glEndConditionalRender()
        
        glDeleteQueries(transparency_layers_count, self.layer_queries)

        self.blend_transparency_shader.textures['IN_BACK'] = self.t_opaque_color
        self.blend_transparency_shader.textures['IN_FRONT'] = self.t_transparent_color
        self.draw_screen_pass(self.blend_transparency_shader, self.fbo_color)

        # TEMPORAL SUPER-SAMPLING ACCUMULATION
        self.blend_texture(self.t_color, self.fbo_accumulate, 1.0 / (self.sample_count + 1))

        #COMPOSITE DEPTH
        composite_depth = None
        if is_final_render:
            composite_depth = self.composite_depth.render(self, self.common_buffer, self.t_opaque_depth)
        
        return {
            'COLOR' : self.t_color_accumulate,
            'DEPTH' : composite_depth,
        }
    
    def draw_layer(self, batches, scene, background_color=(0,0,0,0), prepass_query=None):
        UBOS = {
            'COMMON_UNIFORMS' : self.common_buffer,
            'SCENE_LIGHTS' : self.lights_buffer
        }
        
        callbacks = [
            lambda shader : self.light_groups_buffer.shader_callback(shader),
            lambda shader : self.shadowmaps_opaque.shader_callback(shader),
            lambda shader : self.shadowmaps_transparent.shader_callback(shader),
        ]

        #PRE-PASS
        textures = {
            'IN_OPAQUE_DEPTH': self.t_opaque_depth,
            'IN_TRANSPARENT_DEPTH': self.t_transparent_depth,
            'IN_LAST_ID': self.t_last_layer_id,
        }
        self.fbo_prepass.clear([(0,0,1,1), (0,0,0,0)], 1, 0)

        if prepass_query:
            glBeginQuery(GL_ANY_SAMPLES_PASSED, prepass_query)
        self.draw_scene_pass(self.fbo_prepass, batches, 'PRE_PASS', self.default_shader['PRE_PASS'], UBOS, {}, textures, callbacks)
        if prepass_query:
            glEndQuery(GL_ANY_SAMPLES_PASSED)

        #CUSTOM LIGHT SHADING
        self.custom_light_shading.load(self, self.t_depth, scene)
        callbacks.append(
            lambda shader : self.custom_light_shading.shader_callback(shader)
        )

        #MAIN-PASS
        textures = {
            'IN_NORMAL_DEPTH': self.t_prepass_normal_depth,
            'IN_ID': self.t_prepass_id,
            'IN_OPAQUE_DEPTH': self.t_opaque_depth,
            'IN_TRANSPARENT_DEPTH': self.t_transparent_depth,
            'IN_LAST_ID': self.t_last_layer_id,
        }
        self.fbo_main.clear([background_color, (0,0,0,1), (-1,-1,-1,-1)])
        self.draw_scene_pass(self.fbo_main, batches, 'MAIN_PASS', self.default_shader['MAIN_PASS'], UBOS, {}, textures, callbacks)        
        
        #COMPOSITE LINE
        composited_line = self.line_rendering.composite_line(
            scene.parameters['Line.Max Width'], self, self.common_buffer, 
            self.t_main_color, self.t_depth, self.t_prepass_id, self.t_line_color, self.t_line_data)
        
        return composited_line


PIPELINE = NPR_Pipeline
