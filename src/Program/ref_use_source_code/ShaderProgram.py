from OpenGL.GL import *
from OpenGL.GL import shaders
import os

current_shader = None

class ShaderProgram:
    def __init__(self, vertex_path, fragment_path):
        self.program_id = None
        self.uniforms = {}
        self.vertex_path = vertex_path
        self.fragment_path = fragment_path
        self.compile()

    def compile(self):
        try:
            with open(self.vertex_path, 'r') as f:
                vertex_code = f.read()
            with open(self.fragment_path, 'r') as f:
                fragment_code = f.read()

            vertex_shader = shaders.compileShader(vertex_code, GL_VERTEX_SHADER)
            fragment_shader = shaders.compileShader(fragment_code, GL_FRAGMENT_SHADER)

            self.program_id = shaders.compileProgram(vertex_shader, fragment_shader)
            
            # Cache uniform locations
            self.cache_uniforms()
            
            print(f"Shader compiled successfully: {self.vertex_path}, {self.fragment_path}")
            
        except Exception as e:
            print(f"Error compiling shader: {e}")
            self.program_id = 0

    def cache_uniforms(self):
        if not self.program_id:
            return
            
        count = glGetProgramiv(self.program_id, GL_ACTIVE_UNIFORMS)
        for i in range(count):
            name, size, type = glGetActiveUniform(self.program_id, i)
            # name is bytes, decode to string
            name = name.decode('utf-8')
            # Handle array names (e.g. "lights[0].position" -> we might want to access by base name too?)
            # For now, just store the exact name
            loc = glGetUniformLocation(self.program_id, name)
            self.uniforms[name] = loc

    def use(self):
        if self.program_id:
            glUseProgram(self.program_id)
            global current_shader
            current_shader = self

    def stop(self):
        glUseProgram(0)
        global current_shader
        current_shader = None

    def get_uniform_location(self, name):
        if name not in self.uniforms:
            loc = glGetUniformLocation(self.program_id, name)
            self.uniforms[name] = loc
        return self.uniforms[name]

    def set_uniform_1f(self, name, value):
        if not self.program_id: return
        loc = self.get_uniform_location(name)
        if loc != -1:
            glUniform1f(loc, value)

    def set_uniform_1i(self, name, value):
        if not self.program_id: return
        loc = self.get_uniform_location(name)
        if loc != -1:
            glUniform1i(loc, value)
            
    def set_uniform_bool(self, name, value):
        self.set_uniform_1i(name, 1 if value else 0)

    def set_uniform_3f(self, name, x, y, z):
        if not self.program_id: return
        loc = self.get_uniform_location(name)
        if loc != -1:
            glUniform3f(loc, x, y, z)
            
    def set_uniform_3fv(self, name, value):
        if not self.program_id: return
        loc = self.get_uniform_location(name)
        if loc != -1:
            glUniform3fv(loc, 1, value)

    def set_uniform_4fv(self, name, value):
        if not self.program_id: return
        loc = self.get_uniform_location(name)
        if loc != -1:
            glUniform4fv(loc, 1, value)

    def set_uniform_matrix4fv(self, name, value, transpose=False):
        if not self.program_id: return
        loc = self.get_uniform_location(name)
        if loc != -1:
            glUniformMatrix4fv(loc, 1, transpose, value)
