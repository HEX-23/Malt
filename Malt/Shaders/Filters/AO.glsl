#ifndef AO_GLSL
#define AO_GLSL

#include "Common/Math.glsl"
#include "Common/Transform.glsl"

/*  META
    @meta: internal=true;
    @position: subtype=Vector; default=POSITION;
    @normal: subtype=Normal; default=NORMAL;
    @samples: default=8;
    @radius: default=1.0;
    @distribution_exponent: default=5.0;
    @bias: default=0.01;
*/
float ao(sampler2D depth_texture, int depth_channel, vec3 position, vec3 normal, int samples, float radius, float distribution_exponent, float bias)
{
    //Loosely based on https://learnopengl.com/Advanced-Lighting/SSAO
    float occlusion = 0;

    if(samples <= 0 || radius <= 0.0)
    {
        return 1.0;
    }
    
    for(int i = 0; i < samples; i++)
    {
        // Generate a random TBN matrix
        vec3 random_vec = random_per_pixel(i).xyz;
        random_vec.xyz = random_vec.xyz * 2.0 - 1.0;

        vec3 normal = transform_normal(CAMERA, normal);
        vec3 tangent = normalize(random_vec - normal * dot(random_vec, normal));
        vec3 bitangent = cross(normal, tangent);
        mat3 TBN = mat3(tangent, bitangent, normal);

        vec3 random_offset = random_per_pixel(samples+i).xyz;
        // Make samples close to the center more likely, based on distribution exponent
        random_offset = normalize(random_offset) * pow(length(random_offset), distribution_exponent);
        random_offset *= radius;

        vec3 sample_offset = TBN * random_offset;
        vec3 sample_position = transform_point(CAMERA, position) + sample_offset;

        vec3 sample_uv = project_point_to_screen_coordinates(PROJECTION, sample_position);

        float sampled_depth = texture(depth_texture, sample_uv.xy)[depth_channel];
        sampled_depth = screen_to_camera(sample_uv.xy, sampled_depth).z;

        float range_check = smoothstep(0.0, 1.0, radius / abs(sample_position.z - sampled_depth));
        
        occlusion += (sampled_depth >= sample_position.z + bias ? 1.0 : 0.0) * range_check;
    }

    return 1.0 - (occlusion / samples);
}

#endif //AO_GLSL
