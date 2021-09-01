//Copyright (c) 2020 BlenderNPR and contributors. MIT license.

#ifndef FILTERS_BEVEL_GLSL
#define FILTERS_BEVEL_GLSL

#include "Common/Math.glsl"
#include "Common/Transform.glsl"

#ifndef BEVEL_ID_SAMPLER
    #define BEVEL_ID_SAMPLER sampler2D
#endif

#ifndef BEVEL_FETCH_ID
    #define BEVEL_FETCH_ID(texture, texel, channel) int(round(texelFetch(texture, texel, 0)[channel]))
#endif

vec3 bevel_ex
(
    sampler2D normal_texture, sampler2D depth_texture, int depth_channel,
    int id, bool filter_by_id, BEVEL_ID_SAMPLER id_texture, int id_channel,
    int samples, float radius, float distribution_pow,
    bool hard_bevel, float hard_bevel_max_dot
)
{
    vec2 uv = screen_uv();

    vec3 pixel_normal = texture(normal_texture, uv).xyz;
    float pixel_depth = texture(depth_texture, uv)[depth_channel];
    vec3 pixel_position = screen_to_camera(uv, pixel_depth);

    float closest_distance = radius;
    
    vec3 normal = pixel_normal;

    float screen_radius = radius / pixel_world_size_at(pixel_depth);

    for(int i = 0; i < samples; i++)
    {
        vec2 offset = random_vector(random_per_pixel, i).xy;
        if(length(offset) > 1)
        {
            offset = normalize(offset);
        }
        offset = offset * 2.0 - 1.0;
        if(distribution_pow > 1)
        {
            offset = pow(abs(offset), vec2(distribution_pow)) * sign(offset);
        }
        offset *= screen_radius;

        vec2 offset_uv = uv + (offset / vec2(RESOLUTION));
        ivec2 offset_texel = ivec2(RESOLUTION * offset_uv);

        if(filter_by_id)
        {
            int offset_id = BEVEL_FETCH_ID(id_texture, offset_texel, id_channel);
            if (offset_id != id)
            {
                continue;
            }
        }

        vec3 offset_normal = texelFetch(normal_texture, offset_texel, 0).xyz;
        float offset_depth = texelFetch(depth_texture, offset_texel, 0)[depth_channel];

        vec3 offset_position = screen_to_camera(offset_uv, offset_depth);
        float offset_distance = distance(pixel_position, offset_position);

        if(offset_distance < radius)
        {
            if(hard_bevel)
            {
                float offset_dot = dot(pixel_normal, offset_normal);
                if(offset_dot <= hard_bevel_max_dot)
                {
                    if(offset_distance < closest_distance)
                    {
                        closest_distance = offset_distance;
                        normal = offset_normal;
                    }
                }
            }
            else
            {
                normal += offset_normal;
            }
        }
    }

    if(hard_bevel)
    {
        float mix_factor = 1.0 - (closest_distance / screen_radius);
        mix_factor = saturate(pow(mix_factor, distribution_pow) * distribution_pow);
        return normalize(mix(NORMAL, normalize(NORMAL + normalize(normal)), mix_factor));
    }
    else
    {
        return normalize(normal);
    }
}

#endif //FILTERS_BEVEL_GLSL
