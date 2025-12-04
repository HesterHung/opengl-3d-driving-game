from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import ShaderProgram

class StreetLight:
    def __init__(self, x, z, lightID=None):
        self.posX = x
        self.posY = 0.0
        self.posZ = z
        self.height = 6.0
        self.lightID = lightID # e.g., GL_LIGHT2, GL_LIGHT3...
        
        # Visual properties
        self.poleColor = [0.3, 0.3, 0.3]
        self.bulbColor = [1.0, 1.0, 0.8] # Warm yellow

    def draw(self):
        glPushMatrix()
        glTranslatef(self.posX, self.posY, self.posZ)
        
        # 1. Draw the Pole
        glColor3fv(self.poleColor)
        glPushMatrix()
        glScalef(0.3, self.height, 0.3) # Tall thin pole
        glTranslatef(0, 0.5, 0) # Move up so base is at 0
        glutSolidCube(1.0)
        glPopMatrix()

        # 2. Draw the Bulb (Sphere)
        glTranslatef(0, self.height, 0)
        
        # Emissive material so the bulb looks bright even in the dark
        glMaterialfv(GL_FRONT, GL_EMISSION, [1.0, 1.0, 0.8, 1.0])
        glColor3fv(self.bulbColor)
        glutSolidSphere(0.8, 15, 15)
        # Reset emission
        glMaterialfv(GL_FRONT, GL_EMISSION, [0.0, 0.0, 0.0, 1.0])

        # 3. Activate the Actual Light (if assigned)
        if self.lightID is not None:
            self.enableLight()

        glPopMatrix()

    def enableLight(self):
        # Configure the OpenGL light source at the bulb's position
        glEnable(self.lightID)
        if ShaderProgram.current_shader:
            idx = self.lightID - GL_LIGHT0
            ShaderProgram.current_shader.set_uniform_bool(f"lightEnabled[{idx}]", True)
        
        # Position: (x, y, z, w). w=1.0 means Point Light.
        # We use 0,0,0 here because we already Translated to the bulb position above
        lightPos = [0.0, 0.0, 0.0, 1.0] 
        
        # Yellowish light color
        yellowLight = [0.8, 0.8, 0.6, 1.0]
        
        glLightfv(self.lightID, GL_POSITION, lightPos)
        glLightfv(self.lightID, GL_DIFFUSE, yellowLight)
        glLightfv(self.lightID, GL_SPECULAR, yellowLight)
        
        # Attenuation (make light fade over distance)
        glLightf(self.lightID, GL_CONSTANT_ATTENUATION, 0.5)
        glLightf(self.lightID, GL_LINEAR_ATTENUATION, 0.05)
        glLightf(self.lightID, GL_QUADRATIC_ATTENUATION, 0.002)