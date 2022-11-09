#ifndef NPR_SHADING_GLSL
#define NPR_SHADING_GLSL

#include "NPR_Lighting.glsl"
#include "Shading/ShadingModels.glsl"

/*  META GLOBAL
    @meta: internal=true;
*/

#define _LIT_SCENE_MACRO(callback, light_group, shadows, self_shadows)\
    vec3 result = vec3(0,0,0);\
    for (int i = 0; i < LIGHTS.lights_count; i++)\
    {\
        if(LIGHT_GROUP_INDEX(i) != light_group) continue;\
        Light L = LIGHTS.lights[i];\
        LitSurface LS = npr_lit_surface(position, normal, ID.x, L, i, shadows, self_shadows);\
        result += (callback);\
    }\
    return result;\

/*  META
    @meta: subcategory=Diffuse;
    @position: subtype=Vector; default=POSITION;
    @normal: subtype=Normal; default=NORMAL;
    @light_group: default=1;
    @shadows: default=true;
    @self_shadows: default=true;
*/
vec3 diffuse_shading(vec3 position, vec3 normal, int light_group, bool shadows, bool self_shadows) 
{ 
    _LIT_SCENE_MACRO(diffuse_lit_surface(LS), light_group, shadows, self_shadows);
}
/*  META
    @meta: subcategory=Diffuse;
    @position: subtype=Vector; default=POSITION;
    @normal: subtype=Normal; default=NORMAL;
    @light_group: default=1;
    @shadows: default=true;
    @self_shadows: default=true;
*/
vec3 diffuse_half_shading(vec3 position, vec3 normal, int light_group, bool shadows, bool self_shadows) 
{ 
    _LIT_SCENE_MACRO(diffuse_half_lit_surface(LS), light_group, shadows, self_shadows);
}
/*  META
    @meta: subcategory=Diffuse;
    @position: subtype=Vector; default=POSITION;
    @normal: subtype=Normal; default=NORMAL;
    @light_group: default=1;
    @shadows: default=true;
    @self_shadows: default=true;
*/
vec3 diffuse_gradient_shading(vec3 position, vec3 normal, sampler1D gradient, int light_group, bool shadows, bool self_shadows)
{
    _LIT_SCENE_MACRO(diffuse_gradient_lit_surface(LS, gradient), light_group, shadows, self_shadows);
}
/*  META
    @meta: subcategory=Specular;
    @position: subtype=Vector; default=POSITION;
    @normal: subtype=Normal; default=NORMAL;
    @roughness: default=0.5;
    @light_group: default=1;
    @shadows: default=true;
    @self_shadows: default=true;
*/
vec3 specular_shading(vec3 position, vec3 normal, float roughness, int light_group, bool shadows, bool self_shadows) 
{
    _LIT_SCENE_MACRO(specular_lit_surface(LS, roughness), light_group, shadows, self_shadows);
}
/*  META
    @meta: subcategory=Specular;
    @position: subtype=Vector; default=POSITION;
    @normal: subtype=Normal; default=NORMAL;
    @roughness: default=0.5;
    @light_group: default=1;
    @shadows: default=true;
    @self_shadows: default=true;
*/
vec3 specular_gradient_shading(vec3 position, vec3 normal, float roughness, sampler1D gradient, int light_group, bool shadows, bool self_shadows)
{
    _LIT_SCENE_MACRO(specular_gradient_lit_surface(LS, roughness, gradient), light_group, shadows, self_shadows);
}
/*  META
    @meta: subcategory=Specular;
    @position: subtype=Vector; default=POSITION;
    @normal: subtype=Normal; default=NORMAL;
    @tangent: subtype=Normal; default=radial_tangent(NORMAL, vec3(0,0,1));
    @anisotropy: default=0.5;
    @roughness: default=0.5;
    @light_group: default=1;
    @shadows: default=true;
    @self_shadows: default=true;
*/
vec3 specular_anisotropic_shading(vec3 position, vec3 normal, vec3 tangent, float anisotropy, float roughness, int light_group, bool shadows, bool self_shadows)
{
    _LIT_SCENE_MACRO(specular_anisotropic_lit_surface(LS, tangent, anisotropy, roughness), light_group, shadows, self_shadows);
}
/*  META
    @meta: subcategory=Specular;
    @position: subtype=Vector; default=POSITION;
    @normal: subtype=Normal; default=NORMAL;
    @tangent: subtype=Normal; default=radial_tangent(NORMAL, vec3(0,0,1));
    @anisotropy: default=0.5;
    @roughness: default=0.5;
    @light_group: default=1;
    @shadows: default=true;
    @self_shadows: default=true;
*/
vec3 specular_anisotropic_gradient_shading(vec3 position, vec3 normal, vec3 tangent, float anisotropy, float roughness, sampler1D gradient, int light_group, bool shadows, bool self_shadows)
{
    _LIT_SCENE_MACRO(specular_anisotropic_gradient_lit_surface(LS, tangent, anisotropy, roughness, gradient), light_group, shadows, self_shadows);
}
/*  META
    @position: subtype=Vector; default=POSITION;
    @normal: subtype=Normal; default=NORMAL;
    @size: default=0.49;
    @light_group: default=1;
    @shadows: default=true;
    @self_shadows: default=true;
*/
vec3 toon_shading(vec3 position, vec3 normal, float size, float gradient_size, float specularity, float offset, int light_group, bool shadows, bool self_shadows)
{
    _LIT_SCENE_MACRO(toon_lit_surface(LS, size, gradient_size, specularity, offset), light_group, shadows, self_shadows);
}

#endif //NPR_SHADING_GLSL
