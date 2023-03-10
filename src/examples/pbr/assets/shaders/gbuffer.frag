#version 460
layout (location=0) out vec3 oAlbedo;
layout (location=1) out vec3 oNormals;
layout (location=2) out vec3 oPositions;
layout (location=3) out vec3 oMaterial; // R, M ...

in DATA {
    vec4 position;
    vec3 normal;
    vec3 tangent;
    vec2 uv;
    mat3 tbn;
} fsIn;

uniform vec2 uRoughnessMetallic;
uniform vec3 uBaseColor;

// TODO: normal mapping
uniform sampler2D uAlbedoMap;
uniform bool uAlbedoMapOn;
uniform bool uAlbedoMapTriplanar;

uniform sampler2D uRoughnessMetallicMap;
uniform bool uRoughnessMetallicMapOn;
uniform bool uRoughnessMetallicMapTriplanar;

vec3 triplanarMapping(sampler2D tex, vec3 wP, vec3 N) {
    vec2 uv_front = wP.xy;
    vec2 uv_side = wP.zy;
    vec2 uv_top = wP.xz;

    // read texture at uv position of the three projections
    vec3 col_front = texture(tex, uv_front).rgb;
    vec3 col_side = texture(tex, uv_side).rgb;
    vec3 col_top = texture(tex, uv_top).rgb;

    vec3 weights = abs(normalize(N));
    weights /= (weights.x + weights.y + weights.z);

    col_front *= weights.z;
    col_side *= weights.x;
    col_top *= weights.y;

    return (col_front + col_side + col_top);
}

vec3 LinearTosRGB(vec3 linear) {
    return pow(linear, vec3(2.2));
}

void main() {
    vec3 P = fsIn.position.xyz;
    oPositions = fsIn.position.xyz;

    oAlbedo = uBaseColor;

    if (uAlbedoMapOn) {
        if (uAlbedoMapTriplanar) {
            oAlbedo = triplanarMapping(uAlbedoMap, P, fsIn.normal);
        } else {
            oAlbedo = texture(uAlbedoMap, fsIn.uv).rgb;
        }
    }

    oAlbedo = LinearTosRGB(oAlbedo);

    // TODO: Normal mapping
    oNormals = fsIn.normal * 0.5 + 0.5;

    oMaterial = vec3(uRoughnessMetallic, 0.0);
    if (uRoughnessMetallicMapOn) {
        if (uRoughnessMetallicMapTriplanar) {
            oMaterial.rg = triplanarMapping(uRoughnessMetallicMap, fsIn.position.xyz, fsIn.normal).rg;
        } else {
            oMaterial.rg = texture(uRoughnessMetallicMap, fsIn.uv).rg;
        }
    }
}
