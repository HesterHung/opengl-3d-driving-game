from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math, time
import ImportObject
import ShaderProgram


class jeep:
    obj = 0
    displayList = 0
    wheel1DL = 0
    wheel2DL = 0
    dimDL = 0
    litDL = 0

    dimL = 0
    litL = 0
    lightOn = False
    
    wheel1 = 0
    wheel2 = 0

    wheelTurn = 0.0
    revWheelTurn = 360.0
    #allWheels=[wheel1,wheel2]

    wheelDir = 'stop'
    
    posX = 0.0
    posY = 2.45
    posZ = 0.0

##    wheel1LocX =0 
##    wheel1LocZ = 0
##    wheel2LocX = 0
##    wheel2LocZ = 0 

    sizeX = 1.0
    sizeY = 1.0
    sizeZ = 1.0

    rotation = 0.0
    
    def __init__(self, color):
        if (color == 'p'):
            self.obj = ImportObject.ImportedObject("../objects/jeepbare")
        elif (color == 'g'):
            self.obj = ImportObject.ImportedObject("../objects/jeepbare2")
        elif (color == 'r'):
            self.obj = ImportObject.ImportedObject("../objects/jeepbare3")
        self.wheel1 = ImportObject.ImportedObject("../objects/frontwheel")
        self.wheel2 = ImportObject.ImportedObject("../objects/backwheel")
        self.dimL = ImportObject.ImportedObject("../objects/dimlight")
        self.litL = ImportObject.ImportedObject("../objects/litlight")
    
    def makeDisplayLists(self):
        self.obj.loadOBJ()
        self.wheel1.loadOBJ()
        self.wheel2.loadOBJ()
        self.dimL.loadOBJ()
        self.litL.loadOBJ()

        self.displayList = glGenLists(1)
        glNewList(self.displayList, GL_COMPILE)
        self.obj.drawObject()
        glEndList()

        self.wheel1DL = glGenLists(1)
        glNewList(self.wheel1DL, GL_COMPILE)
        self.wheel1.drawObject()
        glEndList()

        self.wheel2DL = glGenLists(1)
        glNewList(self.wheel2DL, GL_COMPILE)
        self.wheel2.drawObject()
        glEndList()

        self.dimDL = glGenLists(1)
        glNewList(self.dimDL, GL_COMPILE)
        self.dimL.drawObject()
        glEndList()

        self.litDL = glGenLists(1)
        glNewList(self.litDL, GL_COMPILE)
        self.litL.drawObject()
        glEndList()
        
    
    def draw(self):
        # Ensure textures are disabled for the Jeep to prevent "gold" effect
        if ShaderProgram.current_shader:
            ShaderProgram.current_shader.set_uniform_bool("useTexture", False)

        glPushMatrix() # This is the start of the master transform
        
        # 1. Move to the jeep's (x,z) position on the ground plane
        glTranslatef(self.posX, 0.0, self.posZ) 
        
        # 2. Rotate the jeep on the ground
        glRotatef(self.rotation, 0.0, 1.0, 0.0)
        
        # 3. Scale the *entire* jeep coordinate system from the ground
        glScalef(self.sizeX, self.sizeY, self.sizeZ)
        
        # 4. Now, lift the scaled jeep up to its body origin height
        glTranslatef(0.0, self.posY, 0.0)

        # 5. Draw the body
        glCallList(self.displayList)
        # self.obj.drawObject()
        
        # 6. Draw wheels and lights (using the current transform context)
        self._drawW1()
        self._drawW2()
        self.drawLight()
        
        glPopMatrix() # End of master transform - NOW SELF-CONTAINED!

    def _drawW1(self):
        # Private method - called internally by draw()
        # The master transform (pos, rot, scale) is ALREADY active
        glPushMatrix() # Save the master transform state
        
        # 1. Translate to the wheel's *rotation axis*
        #    (relative to the jeep's origin)
        glTranslatef(0.0, -1.3146, 2.9845)
        
        # 2. Apply the wheel spin rotation
        if self.wheelDir == 'fwd': 
            glRotatef(self.revWheelTurn,1.0,0.0,0.0)
        elif self.wheelDir == 'back':
            glRotatef(self.wheelTurn,1.0,0.0,0.0)
    
        # 3. Apply the original code's "hack" translation to
        #    move from the rotation axis to the model's origin.
        glTranslatef(0.0, 1.3146, -2.9845)
        
        # 4. Draw the wheel
        glCallList(self.wheel1DL)
        # self.wheel1.drawObject()
        
        glPopMatrix() # Restore back to the master transform

    def _drawW2(self):
        # Private method - called internally by draw()
        # The master transform (pos, rot, scale) is ALREADY active
        glPushMatrix() # Save the master transform state
        
        # 1. Translate to the wheel's *rotation axis*
        #    (relative to the jeep's origin)
        glTranslatef(0.0, -1.3146, -2.9845) # Note the negative Z
        
        # 2. Apply the wheel spin rotation
        if self.wheelDir == 'fwd': 
            glRotatef(self.revWheelTurn,1.0,0.0,0.0)
        elif self.wheelDir == 'back':
            glRotatef(self.wheelTurn,1.0,0.0,0.0)
    
        # 3. Apply the original code's "offset" translation
        #    (using the original 3.3 value)
        glTranslatef(0.0, 1.3146, 3.3)
        
        # 4. Draw the wheel
        glCallList(self.wheel2DL)
        # self.wheel2.drawObject()
        
        glPopMatrix() # Restore back to the master transform

    def rotateWheel(self, newTheta):
        global wheelTurn
        self.wheelTurn = self.wheelTurn + newTheta
        self.wheelTurn = self.wheelTurn % 360
        self.revWheelTurn = 360 - self.wheelTurn

    def drawLight(self):
        # Private method - called internally by draw()
        # The master transform (pos, rot, scale) is ALREADY active
        # These lights are drawn relative to the jeep's origin
        
        if self.lightOn == True:
            glCallList(self.litDL)
            # self.litL.drawObject()
        elif self.lightOn == False:
            glCallList(self.dimDL)
            # self.dimL.drawObject()
  
    def move(self, rot, val): 
        if rot == False: 
            self.posZ += val * math.cos(math.radians(self.rotation)) #must make more sophisticated to go in direction
            self.posX += val * math.sin(math.radians(self.rotation))
##            self.wheel1LocZ += val * math.cos(math.radians(self.rotation))
##            self.wheel1LocX += val * math.sin(math.radians(self.rotation))
##            self.wheel2LocZ += val * math.cos(math.radians(self.rotation))
##            self.wheel2LocX += val * math.sin(math.radians(self.rotation))
        elif rot == True: 
            self.rotation+= val

    def toggleLight(self):
        self.lightOn = not self.lightOn
        print(f"Headlights: {self.lightOn}")

        
        
