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

// TODO: Textures, normal mapping, etc...
uniform sampler2D uAlbedoMap;
uniform bool uAlbedoMapOn;

uniform sampler2D uRoughnessMetallicMap;
uniform bool uRoughnessMetallicMapOn;

void main() {
    oAlbedo = uBaseColor;

    if (uAlbedoMapOn) {
        oAlbedo = texture(uAlbedoMap, fsIn.uv).rgb;
    }

    oNormals = fsIn.normal * 0.5 + 0.5;
    oPositions = fsIn.position.xyz;
    oMaterial = vec3(uRoughnessMetallic, 0.0);

    if (uRoughnessMetallicMapOn) {
        oMaterial.rg = texture(uRoughnessMetallicMap, fsIn.uv).rg;
    }
}
