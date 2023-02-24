#version 330 core
layout (location=0) in vec3 vPos;
layout (location=1) in vec3 vNrm;
layout (location=2) in vec2 vTex;

uniform mat4 uProj;
uniform mat4 uView;
uniform mat4 uModel;

uniform mat4 uLightMatrix;

out vec2 vUV;
out vec3 vNorm;
out vec3 vPosi;
out vec4 vLightPosi;

void main() {
    mat4 vm = uView * uModel;
    vec4 pos = vm * vec4(vPos, 1.0);
    gl_Position = uProj * pos;
    vUV = vTex;
    vPosi = pos.xyz;
    vLightPosi = uLightMatrix * uModel * vec4(vPos, 1.0);
    vNorm = normalize(vm * vec4(vNrm, 0.0)).xyz;
}
