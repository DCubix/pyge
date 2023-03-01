#version 330 core
out vec4 fragColor;

uniform sampler2D tex;
uniform sampler2D shadowMap;

in vec2 vUV;
in vec3 vNorm;
in vec3 vPosi;
in vec4 vLightPosi;

uniform vec3 lightDir;

vec2 poissonDisk[24] = vec2[](
  vec2(0.01020043f, 0.3103616f),
  vec2(-0.4121873f, -0.1701329f),
  vec2(0.4333374f, 0.6148015f),
  vec2(0.1092096f, -0.2437763f),
  vec2(0.6641068f, -0.1210794f),
  vec2(-0.1726627f, 0.8724736f),
  vec2(-0.8549297f, 0.2836411f),
  vec2(0.5146544f, -0.6802685f),
  vec2(0.04769185f, -0.879628f),
  vec2(-0.9373617f, -0.2187589f),
  vec2(-0.69226f, -0.6652822f),
  vec2(0.9230682f, 0.3181772f),
  // these points might be bad:
  vec2(-0.1565961f, 0.8773971f),
  vec2(-0.5258075f, 0.3916658f),
  vec2(0.515902f, 0.3077986f),
  vec2(-0.006838934f, 0.2577735f),
  vec2(-0.9315282f, -0.04518054f),
  vec2(-0.3417063f, -0.1195169f),
  vec2(-0.3221133f, -0.8118886f),
  vec2(0.425082f, -0.3786222f),
  vec2(0.3917231f, 0.9194779f),
  vec2(0.8819267f, -0.1306234f),
  vec2(-0.7906089f, -0.5639677f),
  vec2(0.2073919f, -0.9611396f)
);

float ShadowCalculation(vec4 fragPosLightSpace, float nl) {
    vec3 projCoords = fragPosLightSpace.xyz / fragPosLightSpace.w;
    projCoords = projCoords * 0.5 + 0.5;

    if (projCoords.z > 1.0) return 0.0;

    float currentDepth = projCoords.z;
    float bias = max(0.005 * (1.0 - nl), 0.001);
    float shadow = 0.0;

    for (int i = 0; i < 24; i++) {
        float pcfDepth = texture(shadowMap, projCoords.xy + poissonDisk[i] * 0.0025).r;
        shadow += currentDepth - bias > pcfDepth  ? 1.0 : 0.0;
    }
    
    return shadow / 24.0;
}

void main() {
    vec3 L = normalize(lightDir);
    vec3 V = normalize(-vPosi);
    vec3 R = normalize(reflect(L, vNorm));

    float nl = clamp(dot(vNorm, L), 0.0, 1.0);
    float rim = 1.0 - clamp(dot(vNorm, V), 0.0, 1.0);
    rim = smoothstep(0.5, 1.0, rim);

    vec3 ambientColor = vec3(0.30, 0.24, 0.2);

    float spec = max(dot(R, -V), 0.0);
    float specTerm = pow(spec, 8.0);

    vec4 tcol = texture(tex, vUV);

    float shadow = ShadowCalculation(vLightPosi, nl);

    float occlusion = nl * (1.0 - shadow);

    vec3 ambient = occlusion + ambientColor;
    vec3 diffuse = ambient * (tcol.rgb + tcol.rgb * rim + vec3(tcol.r * specTerm * 0.6));

    if (tcol.a <= 0.3) discard;

    fragColor = vec4(diffuse, 1.0);
}
