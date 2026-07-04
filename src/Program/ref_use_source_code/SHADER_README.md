# Shader-Based Rendering Implementation

This project has been upgraded with a modern shader-based rendering pipeline using GLSL shaders.

## What's Been Added

### 1. Shader Files (`shaders/` directory)

#### Modern Shaders (OpenGL 3.3+)

- **`basic.vert`**: Vertex shader that transforms vertex positions and normals
- **`basic.frag`**: Fragment shader with support for:
  - Multiple light sources (main light, headlight, streetlights)
  - Phong lighting model (ambient, diffuse, specular)
  - Texture mapping
  - Spot lights and directional lights

#### Legacy Shaders (OpenGL 2.1+)

- **`legacy.vert`**: GLSL 1.20 compatible vertex shader
- **`legacy.frag`**: GLSL 1.20 compatible fragment shader
  - Simplified version for older hardware
  - Main light and headlight support

### 2. ShaderProgram Class (`src/ShaderProgram.py`)

A complete shader management system with:

- Shader loading from files
- Compilation and error checking
- Program linking
- Uniform variable management (cached for performance)
- Helper methods for setting uniforms:
  - `set_uniform_1f()`, `set_uniform_1i()` - scalars
  - `set_uniform_3f()`, `set_uniform_3fv()` - vectors
  - `set_uniform_4fv()` - 4D vectors
  - `set_uniform_matrix4fv()` - 4x4 matrices
  - `set_uniform_bool()` - booleans

### 3. Main.py Integration

#### New Functions

- `initShaders()`: Initializes shader programs with fallback support
- `getViewMatrix()`: Extracts current view matrix from OpenGL
- `getProjectionMatrix()`: Extracts current projection matrix from OpenGL
- `setShaderMatrices()`: Sets model/view/projection matrices in shaders
- `setShaderLighting()`: Configures all light source uniforms
- `setShaderMaterial()`: Sets material properties (ambient, diffuse, specular, shininess)

#### Global Variables

- `shaderProgram`: The active shader program instance
- `useShaders`: Boolean flag (True when shaders are active, False for fixed-function fallback)

## How It Works

### Rendering Pipeline

1. **Initialization** (in `main()`):

   ```python
   initShaders()  # Try modern → legacy → fixed-function fallback
   ```

2. **Per-Frame Setup** (in `display()`):

   ```python
   if useShaders and shaderProgram is not None:
       shaderProgram.use()
       setShaderLighting()
       setShaderMaterial(ambient, diffuse, specular, shininess)
   ```

3. **Per-Object Rendering**:
   - Matrix setup is handled automatically
   - Lighting calculations done in fragment shader
   - Fixed-function calls still work alongside shaders

### Lighting System

The shader supports up to 8 light sources:

- **Light 0**: Main scene light (sun/moon)
- **Light 1**: Jeep headlight (spotlight)
- **Lights 2-7**: Streetlights (dynamic spotlights)

Each light has properties for:

- Position (vec4: xyz position, w=1 for point light, w=0 for directional)
- Diffuse color
- Specular color
- Spotlight direction, cutoff angle, and exponent
- Attenuation factors (constant, linear, quadratic)

## Current Status

### ✅ Completed

- [x] Shader files created (modern + legacy versions)
- [x] ShaderProgram class implemented
- [x] Shader initialization with fallback system
- [x] Lighting system structure in shaders
- [x] Material property support
- [x] Matrix transformation helpers

### ⚠️ Partial/In Progress

- [ ] ImportObject.py uses legacy immediate mode (glBegin/glEnd)
- [ ] Display lists still used (need conversion to VBOs)
- [ ] Mixed rendering (some shader, some fixed-function)

### 🔄 Next Steps for Full Shader Support

To complete the shader implementation, the following needs to be done:

#### 1. Convert Immediate Mode to VBOs

The current code uses:

```python
glBegin(GL_POLYGON)
glNormal3f(...)
glTexCoord2f(...)
glVertex3f(...)
glEnd()
```

This needs to be converted to:

```python
# Create VBO once
vao = glGenVertexArrays(1)
vbo = glGenBuffers(1)
glBindVertexArray(vao)
glBindBuffer(GL_ARRAY_BUFFER, vbo)
glBufferData(GL_ARRAY_BUFFER, vertex_data, GL_STATIC_DRAW)

# Set vertex attributes
glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, position_offset)
glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, normal_offset)
glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, stride, texcoord_offset)

# Render
glDrawArrays(GL_TRIANGLES, 0, vertex_count)
```

#### 2. Update ImportObject.py

Replace `drawObject()` method to:

- Build vertex arrays with interleaved data (position, normal, texcoord)
- Create and bind VAO/VBO
- Use `glDrawArrays()` or `glDrawElements()`
- Enable vertex attribute arrays at locations 0, 1, 2

#### 3. Replace Display Lists

Convert all `glNewList()` / `glCallList()` usage to:

- Generate vertex data once
- Store in VBOs
- Render using draw calls

#### 4. Update Object Classes

Modify `jeep.py`, `cone.py`, `star.py`, etc. to:

- Call `setShaderMatrices()` before drawing
- Pass model matrix to shader
- Remove fixed-function `glMaterial*()` calls

## Compatibility Mode

The system includes automatic fallback:

1. **Modern Mode** (OpenGL 3.3+): Uses `basic.vert`/`basic.frag`
2. **Legacy Mode** (OpenGL 2.1+): Uses `legacy.vert`/`legacy.frag`
3. **Fixed-Function Mode**: Uses original OpenGL 1.x rendering

The active mode is determined at runtime based on shader compilation success.

## Benefits of Shader Rendering

- **Better Performance**: GPU-side lighting calculations
- **More Flexibility**: Easy to add effects (shadows, fog, etc.)
- **Modern Pipeline**: Compatible with modern OpenGL standards
- **Enhanced Lighting**: Per-pixel lighting instead of per-vertex
- **Texture Control**: Better texture blending and effects

## Usage Example

```python
# In your rendering code:
if useShaders:
    shaderProgram.use()

    # Set material
    setShaderMaterial(
        ambient=[0.2, 0.2, 0.2, 1.0],
        diffuse=[0.8, 0.0, 0.0, 1.0],  # Red
        specular=[1.0, 1.0, 1.0, 1.0],
        shininess=64.0
    )

    # Set model matrix (for this object)
    model_matrix = np.eye(4, dtype=np.float32)
    # ... apply transformations ...
    setShaderMatrices(model_matrix)

    # Draw object (using VBOs)
    obj.draw()

    shaderProgram.unuse()
```

## Troubleshooting

### Shaders not loading

- Check that shader files exist in `../shaders/` relative to `src/`
- Check console output for compilation errors
- Verify OpenGL version: Run `glGetString(GL_VERSION)`

### Black screen

- Ensure lighting is enabled: `lightMode != 0`
- Check material properties are set
- Verify matrices are being set correctly

### Performance issues

- Convert more code to use VBOs
- Reduce number of shader state changes
- Use display lists → VBOs for static geometry

## File Structure

```
project/
├── shaders/
│   ├── basic.vert        # Modern vertex shader
│   ├── basic.frag        # Modern fragment shader
│   ├── legacy.vert       # Legacy vertex shader
│   └── legacy.frag       # Legacy fragment shader
└── src/
    ├── main.py           # Updated with shader support
    ├── ShaderProgram.py  # Shader management class
    ├── ImportObject.py   # Needs VBO conversion
    ├── jeep.py           # Object classes
    ├── cone.py
    └── ...
```

## Notes

- The shader system is designed to coexist with fixed-function rendering
- Full benefits require converting all immediate mode calls to VBOs
- Current implementation provides the foundation for modern rendering
- Lighting works in both fixed-function and shader modes
