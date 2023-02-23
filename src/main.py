from typing import List
from pyge.application import Application
from pyge.rendering import Mesh, Shader, Texture2D, Sampler, RenderTarget, Utils

import math, pygame, random
import numpy as np
from OpenGL.GL import *

from pygame.event import Event

from pyge.vmath import Matrix4, Vector3, Transform, Quaternion

vshader = """
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
"""

fshader = """
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
"""

v_shadow_shader = """
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
"""

f_shadow_shader = """
#version 330 core

uniform sampler2D tex;

in vec2 vUV;

void main() {
    if (texture(tex, vUV).a <= 0.5) discard;
}  
"""

lightProj = Matrix4.from_orthographic(-30, 30, -30, 30, 0.001, 600.0)

class App(Application):
    def __init__(self):
        self.setup(opengl=True, size=(1280, 720))

        self.snake_body_mesh = Mesh.from_wavefront('assets/snake_body.obj')['mesh']
        self.snake_tail_mesh = Mesh.from_wavefront('assets/snake_tail.obj')['mesh']
        self.snake_head_mesh = Mesh.from_wavefront('assets/snake_head.obj')['mesh']

        self.apple_mesh = Mesh.from_wavefront('assets/apple.obj')['mesh']

        self.level_meshes = Mesh.from_wavefront('assets/level.obj')
        print(self.level_meshes.keys())

        self.snake_tex = Texture2D.from_image_file('assets/snake.png')
        self.apple_tex = Texture2D.from_image_file('assets/apple.png')
        self.level_tex = Texture2D.from_image_file('assets/grass.png')

        self.shader = Shader()
        self.shader.add_shader(vshader, GL_VERTEX_SHADER)
        self.shader.add_shader(fshader, GL_FRAGMENT_SHADER)
        self.shader.link()

        self.shadow_shader = Shader()
        self.shadow_shader.add_shader(v_shadow_shader, GL_VERTEX_SHADER)
        self.shadow_shader.add_shader(f_shadow_shader, GL_FRAGMENT_SHADER)
        self.shadow_shader.link()

        self.shadow_buffer = RenderTarget(1024, 1024)
        self.shadow_buffer.add_depth_attachment()

        self.sample = Sampler()
        self.sample.filter()
        self.sample.wrap(GL_REPEAT, GL_REPEAT)

        self.ramp_sample = Sampler()
        self.ramp_sample.filter()
        self.ramp_sample.wrap(GL_CLAMP_TO_BORDER, GL_CLAMP_TO_BORDER)

        self.shadow_sample = Sampler()
        self.shadow_sample.wrap(GL_CLAMP_TO_BORDER, GL_CLAMP_TO_BORDER)

        ### Game Related
        self.camera_pos_offset = cam_pos = Vector3(0.0, 25, 30.0)
        self.camera = Transform(translation=cam_pos, rotation=Quaternion.from_look_at(cam_pos, Vector3(0.0, 0.0, 0.0)))
        self.light = Transform(rotation=Quaternion.from_look_at(Vector3(2, 2, 2), Vector3(0.0, 0.0, 0.0)))
        self.ground = Transform(translation=Vector3(0.0, -1.3, 0.0), scale=Vector3(2.0, 2.0, 2.0))

        self.t = 0

        self.snake_body = []
        self.snake_head = Transform()
        self.snake_axis = 0
        self.snake_gap = 14
        self.snake_speed = 3.0
        self.position_history = []

        self.apples: List[Transform] = []

        self.create_snake()

        for i in range(20):
            self.spawn_apple()

    def create_snake(self, size: int = 1):
        for _ in range(size+1): # + tail
            xform = Transform(translation=Vector3(0.0, 0.0, 0.0))
            self.snake_body.append(xform)

    def spawn_apple(self):
        rx = random.uniform(-18, 18)
        ry = random.uniform(-18, 18)
        self.apples.append(
            Transform(
                translation=Vector3(rx, 0, ry),
                rotation=Quaternion.from_angle_axis(random.uniform(-math.pi, math.pi), Vector3(0, 1, 0))
            )
        )

    def on_event(self, event: Event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_LEFT:
            self.snake_axis = 1
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_RIGHT:
            self.snake_axis = -1
        else:
            self.snake_axis = 0

    def on_update(self, dt):
        self.t += dt

        # move snake head
        self.snake_head.translation += self.snake_head.rotation.transform_vector(Vector3(1, 0, 0)) * self.snake_speed * dt
        self.snake_head.rotation *= Quaternion.from_angle_axis(self.snake_axis * 3.0 * dt, Vector3(0, 1, 0))

        # camera follow snake head
        self.camera.translation = self.camera.translation.lerp(self.snake_head.translation + self.camera_pos_offset, 0.4)

        # move snake body
        self.position_history.insert(0, self.snake_head.translation.copy())
        i = 0
        for xform in self.snake_body:
            point = self.position_history[min(i * self.snake_gap, len(self.position_history)-1)]
            move_dir = point - xform.translation
            xform.translation += move_dir * self.snake_speed * dt
            xform.rotation = Quaternion.from_look_rotation(move_dir.normalize(), Vector3(0, 1, 0))
            i += 1

        # rotate apples
        for xform in self.apples:
            xform.rotation *= Quaternion.from_angle_axis(3.0 * dt, Vector3(0, 1, 0))

        # small detail: move apples away from the body
        for apple in self.apples:
            for body in self.snake_body:
                vec = (apple.translation - body.translation)
                dist = vec.length()
                if dist <= 1.25:
                    apple.translation += vec * dt * 5.0

        # check for snake head collision with apples
        for apple in self.apples:
            dist = (apple.translation - self.snake_head.translation).length()
            if dist <= 0.7:
                self.apples.remove(apple)
                # grow snake
                self.snake_body.append(self.snake_body[-1].copy())
                self.spawn_apple()
                break


    def on_draw(self):
        glClearColor(0.0, 0.1, 0.35, 1.0)
        glClearDepth(1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        view = self.camera.to_matrix4().inverse()
        proj = Matrix4.from_perspective(math.pi / 5, self.display.get_width() / self.display.get_height(), 0.01, 10000.0)

        self.shadow_shader.use()
        self.draw_shadows()

        lightMatrix = lightProj * self.light.to_matrix4().inverse()

        self.shader.use()
        self.shader.set_uniform('lightDir', *self.light.transform_vector(Vector3(0, 0, 1)).raw)
        self.shader.set_uniform('uLightMatrix', *lightMatrix.raw)
        self.shader.set_uniform('shadowMap', 1)

        self.shadow_sample.bind(1)
        self.shadow_buffer.depth_attachment.bind(1)

        self.draw_scene(self.shader, view, proj)

        # aspect = self.display.get_width() / self.display.get_height()
        # Utils.draw_quad(self.shadow_buffer.depth_attachment, 0.01, -0.1, 0.8, 0.8 * aspect)

    def draw_scene(self, shader: Shader, view: Matrix4, proj: Matrix4, cull_level: bool=True):
        if cull_level: glDisable(GL_CULL_FACE)
        self.draw_level(shader, view, proj)
        if cull_level: glEnable(GL_CULL_FACE)

        self.draw_snake(shader, view, proj)
        self.draw_apples(shader, view, proj)

    def draw_shadows(self):
        self.shadow_shader.use()
        self.shadow_buffer.bind()
        glClear(GL_DEPTH_BUFFER_BIT)
        self.draw_scene(self.shadow_shader, self.light.to_matrix4().inverse(), lightProj, False)
        self.shadow_buffer.unbind()

    def draw_level(self, shader: Shader, view: Matrix4, proj: Matrix4):
        shader.use()
        shader.set_uniform('uView', *view.raw)
        shader.set_uniform('uProj', *proj.raw)
        shader.set_uniform('tex', 0)

        self.level_tex.bind(0)
        self.sample.bind(0)

        for mesh in self.level_meshes.values():
            shader.set_uniform('uModel', *self.ground.to_matrix4().raw)
            mesh.draw()

    def draw_apples(self, shader: Shader, view: Matrix4, proj: Matrix4):
        shader.use()
        shader.set_uniform('uView', *view.raw)
        shader.set_uniform('uProj', *proj.raw)
        shader.set_uniform('tex', 0)

        self.apple_tex.bind(0)
        self.sample.bind(0)

        for xform in self.apples:
            model = xform.to_matrix4()
            shader.set_uniform('uModel', *model.raw)
            self.apple_mesh.draw()

    def draw_snake(self, shader: Shader, view: Matrix4, proj: Matrix4):
        shader.use()
        shader.set_uniform('uView', *view.raw)
        shader.set_uniform('uProj', *proj.raw)
        shader.set_uniform('tex', 0)

        self.snake_tex.bind(0)
        self.sample.bind(0)

        i = 0
        for xform in self.snake_body:
            model = xform.to_matrix4()
            shader.set_uniform('uModel', *model.raw)

            if i == 0:
                self.snake_head_mesh.draw()
            elif i == len(self.snake_body)-1:
                self.snake_tail_mesh.draw()
            else:
                self.snake_body_mesh.draw()

            i += 1


if __name__ == '__main__':
    App().run()
