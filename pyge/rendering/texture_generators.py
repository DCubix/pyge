from pyge.rendering import Shader, Texture2D, TextureCubeMap, Sampler
from OpenGL.GL import *

class GeneratorParams:
    local_size_x: int
    local_size_y: int

    def __init__(self, local_size_x: int=1, local_size_y: int=1):
        self.local_size_x = local_size_x
        self.local_size_y = local_size_y

class TextureGenerator:
    def __init__(self):
        self.shader = Shader()
        self.shader.add_shader(self.get_shader_code(), GL_COMPUTE_SHADER)
        self.shader.link()
    
    def begin_processing(self):
        self.shader.use()

    def dispatch(self, out_width: int, out_height: int, out_depth: int = 1):
        params = self.get_generator_params()

        glDispatchCompute(out_width // params.local_size_x, out_height // params.local_size_y, out_depth)
        glMemoryBarrier(GL_SHADER_IMAGE_ACCESS_BARRIER_BIT)

        # imageData = images.SetupPixelRead(format, output.size, type)
        # buffSize = out_width * out_height * components
        # glGetTextureImage(output.id, 0, format, type, buffSize, imageData)

    def process(self):
        pass

    def get_shader_code(self):
        return ''

    def get_generator_params(self):
        return GeneratorParams()


class ImageBasedLightingBRDFLUT(TextureGenerator):
    def __init__(self, out_width: int, out_height: int):
        super().__init__()

        self.output = Texture2D(out_width, out_height, GL_RG8)

    def process(self):
        self.begin_processing()
        glBindImageTexture(0, self.output.id, 0, False, 0, GL_WRITE_ONLY, GL_RG8)
        self.shader.set_uniform('uOutput', 0)
        self.dispatch(self.output.size[0], self.output.size[1])
        return self.output

    def get_shader_code(self):
        return """#version 460
        layout (local_size_x=4, local_size_y=4) in;

        layout (rg8, binding=0) uniform image2D uOutput;

        #define PI 3.141592654

        float RadicalInverse_VdC(uint bits) {
            bits = (bits << 16u) | (bits >> 16u);
            bits = ((bits & 0x55555555u) << 1u) | ((bits & 0xAAAAAAAAu) >> 1u);
            bits = ((bits & 0x33333333u) << 2u) | ((bits & 0xCCCCCCCCu) >> 2u);
            bits = ((bits & 0x0F0F0F0Fu) << 4u) | ((bits & 0xF0F0F0F0u) >> 4u);
            bits = ((bits & 0x00FF00FFu) << 8u) | ((bits & 0xFF00FF00u) >> 8u);
            return float(bits) * 2.3283064365386963e-10; // / 0x100000000
        }

        vec2 Hammersley(uint i, uint N) {
            return vec2(float(i)/float(N), RadicalInverse_VdC(i));
        }

        vec3 ImportanceSampleGGX(vec2 Xi, vec3 N, float roughness) {
            float a = roughness*roughness;
            
            float phi = 2.0 * PI * Xi.x;
            float cosTheta = sqrt((1.0 - Xi.y) / (1.0 + (a*a - 1.0) * Xi.y));
            float sinTheta = sqrt(1.0 - cosTheta*cosTheta);
            
            // from spherical coordinates to cartesian coordinates
            vec3 H;
            H.x = cos(phi) * sinTheta;
            H.y = sin(phi) * sinTheta;
            H.z = cosTheta;
            
            // from tangent-space vector to world-space sample vector
            vec3 up        = abs(N.z) < 0.999 ? vec3(0.0, 0.0, 1.0) : vec3(1.0, 0.0, 0.0);
            vec3 tangent   = normalize(cross(up, N));
            vec3 bitangent = cross(N, tangent);
            
            vec3 sampleVec = tangent * H.x + bitangent * H.y + N * H.z;
            return normalize(sampleVec);
        }

        float GeometrySchlickGGX(float NdotV, float roughness) {
            float a = roughness;
            float k = (a * a) / 2.0;

            float nom   = NdotV;
            float denom = NdotV * (1.0 - k) + k;

            return nom / denom;
        }
        
        float GeometrySmith(vec3 N, vec3 V, vec3 L, float roughness) {
            float NdotV = max(dot(N, V), 0.0);
            float NdotL = max(dot(N, L), 0.0);
            float ggx2 = GeometrySchlickGGX(NdotV, roughness);
            float ggx1 = GeometrySchlickGGX(NdotL, roughness);

            return ggx1 * ggx2;
        }

        vec2 IntegrateBRDF(float NdotV, float roughness) {
            vec3 V;
            V.x = sqrt(1.0 - NdotV*NdotV);
            V.y = 0.0;
            V.z = NdotV;

            float A = 0.0;
            float B = 0.0;

            vec3 N = vec3(0.0, 0.0, 1.0);

            const uint SAMPLE_COUNT = 1024u;
            for(uint i = 0u; i < SAMPLE_COUNT; ++i) {
                vec2 Xi = Hammersley(i, SAMPLE_COUNT);
                vec3 H  = ImportanceSampleGGX(Xi, N, roughness);
                vec3 L  = normalize(2.0 * dot(V, H) * H - V);

                float NdotL = max(L.z, 0.0);
                float NdotH = max(H.z, 0.0);
                float VdotH = max(dot(V, H), 0.0);

                if (NdotL > 0.0) {
                    float G = GeometrySmith(N, V, L, roughness);
                    float G_Vis = (G * VdotH) / (NdotH * NdotV);
                    float Fc = pow(1.0 - VdotH, 5.0);

                    A += (1.0 - Fc) * G_Vis;
                    B += Fc * G_Vis;
                }
            }
            A /= float(SAMPLE_COUNT);
            B /= float(SAMPLE_COUNT);
            return vec2(A, B);
        }
        
        float d_ggx(float dotNH, float roughness) {
            float alpha = roughness * roughness;
            float alpha2 = alpha * alpha;
            float denom = dotNH * dotNH * (alpha2 - 1.0) + 1.0;
            return alpha2 / (PI * denom * denom); 
        }

        void main() {
            vec2 sz = vec2(gl_NumWorkGroups.xy * 4);
            vec2 pos = vec2(gl_GlobalInvocationID.xy) / sz;

            vec2 brdf = IntegrateBRDF(pos.x, pos.y);
            imageStore(uOutput, ivec2(pos*sz), vec4(brdf, 0.0, 1.0));
        }
        """
    
    def get_generator_params(self):
        return GeneratorParams(local_size_x=4, local_size_y=4)

class PrefilteredCubeMap(TextureGenerator):
    def __init__(self, original: TextureCubeMap, mip_levels: int=TextureCubeMap.DEFAULT_MIPS):
        super().__init__()

        self.original = original
        self.output = TextureCubeMap(original.size[0], original.size[1], GL_RGB8, self.original.levels)
        for i in range(6):
            self.output.update_face(i, None, GL_RGB, GL_UNSIGNED_BYTE)
        self.output.generate_mipmaps()
        
        self.mip_levels = mip_levels

        self.sampler = Sampler()
        self.sampler.filter()
        self.sampler.wrap(GL_CLAMP_TO_EDGE, GL_CLAMP_TO_EDGE, GL_CLAMP_TO_EDGE)
    
    def get_generator_params(self):
        return GeneratorParams(local_size_x=16, local_size_y=16)
    
    def process(self):
        self.begin_processing()
        
        self.original.bind(1)
        self.sampler.bind(1)

        self.shader.set_uniform('uInput', 1)
        self.shader.set_uniform('uCubemapSize', float(self.output.size[0]), float(self.output.size[0]))
        self.shader.set_uniform('uOutput', 0)

        # set mips
        for i in range(self.mip_levels):
            mip_size = self.output.size[0] >> i
            roughness = i / (self.mip_levels-1)
            glBindImageTexture(0, self.output.id, i, True, 0, GL_READ_WRITE, GL_RGBA8)

            self.shader.set_uniform('uMipSize', float(mip_size), float(mip_size))
            self.shader.set_uniform('uRoughness', roughness)

            self.dispatch(mip_size, mip_size, 6)
            print(f'Wrote to mip #{i} ({mip_size}, {roughness})')

        return self.output

    def get_shader_code(self):
        return """#version 460
        layout (local_size_x=16, local_size_y=16, local_size_z=1) in;

        layout (rgba8, binding=0) uniform imageCube uOutput;
        
        uniform samplerCube uInput;

        uniform vec2 uMipSize;
        uniform vec2 uCubemapSize;
        uniform float uRoughness;

        #define PI 3.141592654
        #define SAMPLE_COUNT 1024u

        float RadicalInverse_VdC(uint bits) {
            bits = (bits << 16u) | (bits >> 16u);
            bits = ((bits & 0x55555555u) << 1u) | ((bits & 0xAAAAAAAAu) >> 1u);
            bits = ((bits & 0x33333333u) << 2u) | ((bits & 0xCCCCCCCCu) >> 2u);
            bits = ((bits & 0x0F0F0F0Fu) << 4u) | ((bits & 0xF0F0F0F0u) >> 4u);
            bits = ((bits & 0x00FF00FFu) << 8u) | ((bits & 0xFF00FF00u) >> 8u);
            return float(bits) * 2.3283064365386963e-10; // / 0x100000000
        }

        vec2 Hammersley(uint i, uint N) {
            return vec2(float(i)/float(N), RadicalInverse_VdC(i));
        }

        vec3 ImportanceSampleGGX(vec2 Xi, vec3 N, float roughness) {
            float a = roughness*roughness;
            
            float phi = 2.0 * PI * Xi.x;
            float cosTheta = sqrt((1.0 - Xi.y) / (1.0 + (a*a - 1.0) * Xi.y));
            float sinTheta = sqrt(1.0 - cosTheta*cosTheta);
            
            // from spherical coordinates to cartesian coordinates
            vec3 H;
            H.x = cos(phi) * sinTheta;
            H.y = sin(phi) * sinTheta;
            H.z = cosTheta;
            
            // from tangent-space vector to world-space sample vector
            vec3 up        = abs(N.z) < 0.999 ? vec3(0.0, 0.0, 1.0) : vec3(1.0, 0.0, 0.0);
            vec3 tangent   = normalize(cross(up, N));
            vec3 bitangent = cross(N, tangent);
            
            vec3 sampleVec = tangent * H.x + bitangent * H.y + N * H.z;
            return normalize(sampleVec);
        }

        vec3 cubeToWorld(ivec3 cubeCoord, vec2 cubemapSize) {
            vec2 texCoord = vec2(cubeCoord.xy) / cubemapSize;
            texCoord = texCoord  * 2.0 - 1.0; // -1..1

            switch(cubeCoord.z) {
                case 0: return vec3(1.0, -texCoord.yx);             // posx
                case 1: return vec3(-1.0, -texCoord.y, texCoord.x); // negx
                case 2: return vec3(texCoord.x, 1.0, texCoord.y);   // posy
                case 3: return vec3(texCoord.x, -1.0, -texCoord.y); // negy
                case 4: return vec3(texCoord.x, -texCoord.y, 1.0);  // posz
                case 5: return vec3(-texCoord.xy, -1.0);            // negz
            }

            return vec3(0.0);
        }
                
        void main() {
            ivec3 cubeCoord = ivec3(gl_GlobalInvocationID);
            vec3 worldPos = cubeToWorld(cubeCoord, uMipSize);

            vec3 N = normalize(worldPos);
            vec3 R = N;
            vec3 V = N;

            float totalWeight = 0.0;   
            vec3 prefilteredColor = vec3(0.0);     
            for(uint i = 0u; i < SAMPLE_COUNT; ++i) {
                vec2 Xi = Hammersley(i, SAMPLE_COUNT);
                vec3 H  = ImportanceSampleGGX(Xi, N, uRoughness);
                vec3 L  = normalize(2.0 * dot(V, H) * H - V);

                float NdotL = max(dot(N, L), 0.0);
                if (NdotL > 0.0) {
                    prefilteredColor += texture(uInput, L).rgb * NdotL;
                    totalWeight      += NdotL;
                }
            }
            prefilteredColor = prefilteredColor / totalWeight;

            imageStore(uOutput, cubeCoord, vec4(prefilteredColor, 1.0));
        }
        """
