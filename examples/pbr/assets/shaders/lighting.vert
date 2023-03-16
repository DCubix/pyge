#version 460

out vec2 vUV;

const vec2 vPositions[6] = vec2[](
    vec2(0.0, 0.0),
    vec2(1.0, 0.0),
    vec2(1.0, 1.0),
    vec2(1.0, 1.0),
    vec2(0.0, 1.0),
    vec2(0.0, 0.0)
);

void main() {
    vec2 pos = vPositions[gl_VertexID];
    gl_Position = vec4(pos * 2.0 - 1.0, 0.0, 1.0);
    vUV = vPositions[gl_VertexID];
}
