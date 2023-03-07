#version 460
out vec4 fragColor;

const vec3 lightVector = vec3(1.0, 1.0, 1.0); // temporary

uniform sampler2D uGB_Albedo;
uniform sampler2D uGB_Normals;
uniform sampler2D uGB_Positions;
uniform sampler2D uGB_Material;

uniform samplerCube uEnvMap;
uniform sampler2D uEnvBRDF;

uniform vec3 uEyePosition;

in vec2 vUV;

#define PI 3.141592654
#define LAMBERT (1.0 / PI)

float pow5(float x) {
    return x * x * x * x * x;
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

vec3 F(float product, vec3 f0) {
    float x = 1.0 - product;
    return mix(f0, vec3(1.0), pow5(x));
}

vec3 cookTorranceSpecular(float NdL, float NdH, float NdV, vec3 specular, float roughness) {
    float Dfact = D(NdH, roughness);
    float Gfact = G(NdV, NdL, roughness);
    return specular * Dfact * Gfact;
}

vec3 iblLighting(vec3 N, vec3 R, float NdV, vec3 baseColor, float roughness, float metallic) {
    vec3 f0 = mix(vec3(0.04), baseColor, metallic);
    vec3 fr = max(vec3(1.0 - roughness), f0) - f0;

    vec3 Ffact = f0 + fr * pow5(1.0 - NdV);
    vec3 Ks = Ffact;
    vec3 Kd = (1.0 - Ks) * (1.0 - metallic);

    vec3 irradiance = textureLod(uEnvMap, N, 6.0).rgb;
    vec3 diffuse = irradiance * baseColor * LAMBERT;

    const float MAX_REFLECTION_LOD = 6.0;
    vec3 prefilteredColor = textureLod(uEnvMap, R, roughness * MAX_REFLECTION_LOD).rgb;   
    vec2 envBRDF  = texture(uEnvBRDF, vec2(NdV, roughness)).rg;
    vec3 specular = prefilteredColor * (Ffact * envBRDF.x + envBRDF.y);

    return Kd * diffuse + specular; // * ao
}

void main() {
    vec3 rN = texture(uGB_Normals, vUV).xyz;
    vec3 rP = texture(uGB_Positions, vUV).xyz;
    vec2 rM = texture(uGB_Material, vUV).xy;
    vec4 rA = texture(uGB_Albedo, vUV);

    vec3 N = normalize(rN * 2.0 - 1.0);

    vec3 V = normalize(uEyePosition - rP);
    vec3 L = normalize(lightVector);
    vec3 H = normalize(V + L);
    vec3 R = reflect(-V, N);
    
    float roughness = rM.x;
    float metallic = rM.y;
    vec3 baseColor = rA.rgb * rA.a;
    vec3 f0 = mix(vec3(0.04), baseColor, metallic);

    float NdL = max(dot(N, L), 0.0);
    float NdV = max(dot(N, V), 1e-5);
    float NdH = max(dot(N, H), 1e-5);
    float HdV = max(dot(H, V), 1e-5);

    vec3 Lo = iblLighting(N, R, NdV, baseColor, roughness, metallic);

    // lighting
    vec3 Ffact = F(NdV, f0);
    vec3 Ks = Ffact;
    vec3 Kd = (1.0 - Ks) * (1.0 - metallic);
    
    vec3 NDFG = cookTorranceSpecular(NdL, NdH, NdV, f0, roughness);
    vec3 numerator    = NDFG * Ffact;
    float denominator = max(4.0 * NdV * NdL, 1e-5);
    vec3 specular     = numerator / denominator;  
        
    // add to outgoing radiance Lo          
    Lo += (Kd * baseColor * LAMBERT + specular) /* TODO: Light color * radiance */ * NdL;

    // gamma correct
    vec3 color = Lo; // TODO: color is going to be ambient + Lo

    color = color / (color + vec3(1.0));
    color = pow(color, vec3(1.0/2.2)); 

    fragColor = vec4(color, 1.0);
}
