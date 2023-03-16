#version 460
out vec4 fragColor;

struct Light {
    int type; // 0 = directional, 1 = point, 2 = spot
    vec4 color; // r, g, b, intensity
    vec3 position;
    vec3 direction;
    float radius;
    float cutoff;
};

uniform sampler2D uGB_Albedo;
uniform sampler2D uGB_Normals;
uniform sampler2D uGB_Positions;
uniform sampler2D uGB_Material;

uniform samplerCube uEnvMap;
uniform sampler2D uEnvBRDF;

uniform vec3 uEyePosition;

uniform int uLightingMode; // 0 = Ambient (IBL), 1 = Lights
uniform Light uLight;

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

// Source: https://lisyarus.github.io/blog/graphics/2022/07/30/point-light-attenuation.html
float sqr(float x) {
	return x * x;
}

float attenuateNoCusp(float distance, float radius, float max_intensity, float falloff) {
	float s = distance / radius;

	if (s >= 1.0)
		return 0.0;

	float s2 = sqr(s);

	return max_intensity * sqr(1 - s2) / (1 + falloff * s2);
}

void calculateDirectionalLight(Light light, out vec3 L, out float attenuation) {
    L = normalize(-light.direction);
    attenuation = 1.0;
}

void calculatePointLight(Light light, vec3 wP, out vec3 L, out float attenuation) {
    L = light.position - wP;
    
    float dist = length(L);
    L = normalize(L);

    attenuation = attenuateNoCusp(dist, light.radius, 1.0, 0.65);
}

void calculateSpotLight(Light light, vec3 wP, out vec3 L, out float attenuation) {
    calculatePointLight(light, wP, L, attenuation);

    float S = dot(L, normalize(-light.direction));
    float c = cos(light.cutoff);
    if (S > c) {
        attenuation *= (1.0 - (1.0 - S) * 1.0 / (1.0 - c));
    }
}

void calculateLight(Light light, vec3 wP, out vec3 L, out float attenuation) {
    switch (light.type) {
        case 0: calculateDirectionalLight(light, L, attenuation); break;
        case 1: calculatePointLight(light, wP, L, attenuation); break;
        case 2: calculateSpotLight(light, wP, L, attenuation); break;
        default: break;
    }
}

vec3 ACES(vec3 x) {
    float a = 2.51;
    float b = 0.03;
    float c = 2.43;
    float d = 0.59;
    float e = 0.14;
    return clamp((x*(a*x+b))/(x*(c*x+d)+e), 0.0, 1.0);
}

vec3 sRGBToLinear(vec3 sRGB) {
    return pow(sRGB, vec3(1.0 / 2.2));
}

void main() {
    vec3 rN = texture(uGB_Normals, vUV).xyz;
    vec3 rP = texture(uGB_Positions, vUV).xyz;
    vec2 rM = texture(uGB_Material, vUV).xy;
    vec4 rA = texture(uGB_Albedo, vUV);

    vec3 N = normalize(rN * 2.0 - 1.0);

    vec3 V = normalize(uEyePosition - rP);
    vec3 R = reflect(-V, N);
    
    float roughness = rM.x;
    float metallic = rM.y;
    vec3 baseColor = sRGBToLinear(rA.rgb * rA.a);
    vec3 f0 = mix(vec3(0.04), baseColor, metallic);

    if (uLightingMode == 0) {
        float NdV = max(dot(N, V), 1e-5);
        fragColor.rgb = iblLighting(N, R, NdV, baseColor, roughness, metallic);
    } else if (uLightingMode == 1) {
        vec3 L = vec3(0.0);
        float attenuation = 1.0;
        calculateLight(uLight, rP, L, attenuation);

        vec3 H = normalize(V + L);

        float NdL = max(dot(N, L), 0.0);
        float NdV = max(dot(N, V), 1e-5);
        float NdH = max(dot(N, H), 1e-5);
        // float HdV = max(dot(H, V), 1e-5);

        vec3 Ffact = F(NdV, f0);
        vec3 Ks = Ffact;
        vec3 Kd = (1.0 - Ks) * (1.0 - metallic);
        
        vec3 NDFG = cookTorranceSpecular(NdL, NdH, NdV, f0, roughness);
        vec3 numerator    = NDFG * Ffact;
        float denominator = max(4.0 * NdV * NdL, 1e-5);
        vec3 specular     = numerator / denominator;  
            
        // add to outgoing radiance Lo 
        float fact = NdL * uLight.color.a * attenuation;
        fragColor.rgb = (Kd * baseColor * LAMBERT + specular) * uLight.color.rgb * fact;
    }
    // gamma correct
    fragColor.rgb = ACES(fragColor.rgb);
    fragColor.rgb = pow(fragColor.rgb, vec3(1.0/2.2)); 
    fragColor.a = 1.0;
}
