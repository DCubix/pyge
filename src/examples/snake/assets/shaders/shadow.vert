#version 330 core
layout (location = 0) in vec3 vPos;
layout (location=2) in vec2 vTex;

uniform mat4 uProj;
uniform mat4 uView;
uniform mat4 uModel;

out vec2 vUV;

void main() {
    mat4 vm = uView * uModel;
    vec4 pos = vm * vec4(vPos, 1.0);
    gl_Position = uProj * pos;
    vUV = vTex;
}