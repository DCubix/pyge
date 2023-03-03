#version 460
layout (location=0) in vec3 vPosition;
layout (location=1) in vec3 vNormal;
layout (location=2) in vec2 vTexCoord;
layout (location=3) in vec3 vTangent;

uniform mat4 uProjection;
uniform mat4 uModel;
uniform mat4 uView;

out DATA {
    vec3 position;
    vec3 normal;
    vec3 tangent;
    vec2 uv;
    mat3 tbn;
} vsOut;

void main() {
    vec4 pos = uModel * vec4(vPosition, 1.0);
    gl_Position = uProjection * uView * pos;

    vsOut.position = pos.xyz;
    vsOut.uv = vTexCoord;

    vsOut.normal = normalize((uModel * vec4(vNormal, 0.0)).xyz);
    vsOut.tangent = normalize((uModel * vec4(vTangent, 0.0)).xyz);
    vsOut.tangent = normalize(vsOut.tangent - dot(vsOut.tangent, vsOut.normal) * vsOut.normal);

    vec3 b = cross(vsOut.tangent, vsOut.normal);
    vsOut.tbn = mat3(vsOut.tangent, b, vsOut.normal);
}
