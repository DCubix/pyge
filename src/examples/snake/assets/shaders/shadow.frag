#version 330 core

uniform sampler2D tex;

in vec2 vUV;

void main() {
    if (texture(tex, vUV).a <= 0.5) discard;
}
