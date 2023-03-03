#version 460
out vec4 fragColor;

uniform vec3 uEyePosition;
uniform float uTime;

uniform samplerCube uEnvMap;

const vec3 lightVector = vec3(1.0, 1.0, 1.0); // temporary

in DATA {
	vec3 position;
	vec3 normal;
	vec3 tangent;
	vec2 uv;
	mat3 tbn;
} fsIn;

#define PI 3.141592654

float pow5(float x) {
    return x * x * x * x * x;
}

vec3 DiffuseBRDF(vec3 color) {
    return color / PI;
}

float D(float NdH, float roughness) {
    float alpha = roughness * roughness;
    float alphaSq = alpha * alpha;
    float denom = PI * pow((pow(NdH, 2.0) * (alphaSq - 1.0) + 1.0), 2.0);
    return alphaSq / max(1e-5, denom);
}

float G1(float k, float NdX) {
    return NdX / ((NdX) * (1.0 - k) + k);
}

float G(float NdV, float NdL, float roughness) {
    float k = pow(roughness + 1.0, 2.0) / 8.0;
    return G1(k, NdV) * G1(k, NdL);
}

vec3 F(vec3 f0, float product) {
    float x = 1.0 - product;
    return mix(f0, vec3(1.0), pow5(x));
}

vec3 cookTorranceSpecular(float NdL, float NdH, float NdV, vec3 specular, float roughness) {
    float Dfact = D(NdH, roughness);
    float Gfact = G(NdV, NdL, roughness);
    float rim = mix(1.0 - roughness * 0.9, 1.0, NdV);
    return (1.0 / rim) * specular * Dfact * Gfact;
}

// from https://gist.github.com/galek/53557375251e1a942dfa
void main() {
    vec3 N = normalize(fsIn.normal);
    vec3 V = normalize(uEyePosition - fsIn.position);
    vec3 L = normalize(lightVector);
    vec3 H = normalize(V + L);
    
    const float roughness = 0.4;
    const float metallic = 0.0;
    const vec3 baseColor = vec3(1.0, 0.8, 0.2);
    const vec3 specular = mix(vec3(0.04), baseColor, metallic);

    float NdL = max(dot(N, L), 0.0);
    float NdV = max(dot(N, V), 1e-5);
    float NdH = max(dot(N, H), 1e-5);
    float HdV = max(dot(H, V), 1e-5);

    vec3 Ffact = F(specular, HdV);
    vec3 specularTerm = cookTorranceSpecular(NdL, NdH, NdV, Ffact, roughness) * NdL;
    vec3 diffuseTerm = (1.0 - Ffact) * (1.0 / PI) * NdL;
    diffuseTerm *= mix(baseColor, vec3(0.0), metallic);

    vec3 envDiffuseTerm = textureLod(uEnvMap, N, 5.0).rgb;

    diffuseTerm = envDiffuseTerm;

    fragColor = vec4(diffuseTerm + specularTerm, 1.0);
}