from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math, time
import ImportObject


class star:
    # --- Add a constant for the hit effect ---
    HIT_DURATION = 0.5 # 0.5 seconds
    
    obj = 0
    displayList = 0 # We won't use this, but keep the variable
    
    posX = 0.0
    posY = 0.0
    posZ = 0.0

    sizeX = 1.0
    sizeY = 1.0
    sizeZ = 1.0

    rotation = 0.0

    speed = 5.0
    direction = 1
    
    # --- Add a timer for the hit effect ---
    hit_timer = 0.0
    
    def __init__(self, x, z):
        self.obj = ImportObject.ImportedObject("objects/star")
        self.posX = x
        self.posZ = z
        self.hit_timer = 0.0 # Ensure it's initialized
        
    def makeDisplayLists(self):
        self.obj.loadOBJ()
        
        # --- MODIFICATION ---
        # We are *not* creating a display list.
        # We need to draw the object directly to change its color.
        
        # self.displayList = glGenLists(1)
        # glNewList(self.displayList, GL_COMPILE)
        # self.obj.drawObject()
        # glEndList()
    
    def draw(self):
        glPushMatrix()
        
        glTranslatef(self.posX,self.posY,self.posZ)
        glRotatef(self.rotation,0.0,1.0,0.0)
        glScalef(self.sizeX,self.sizeY,self.sizeZ)

        # --- MODIFICATION ---
        
        is_hit = self.hit_timer > 0
        original_set_model_color = None # Store for safekeeping
        
        if is_hit:
            # 1. Set the material to red
            glMaterialfv(GL_FRONT, GL_AMBIENT, [1.0, 0.0, 0.0, 1.0])
            glMaterialfv(GL_FRONT, GL_DIFFUSE, [1.0, 0.0, 0.0, 1.0])
            glMaterialfv(GL_FRONT, GL_EMISSION, [1.0, 0.0, 0.0, 1.0])
            
            # 2. Temporarily "disable" the object's setModelColor method
            #    so it doesn't overwrite our red color.
            original_set_model_color = self.obj.setModelColor
            self.obj.setModelColor = lambda material: None
        
        # 3. Draw the object directly (NOT from a list)
        self.obj.drawObject()
        
        if is_hit:
            # 4. Restore the original setModelColor function
            self.obj.setModelColor = original_set_model_color
            
            # 5. Reset emission so other objects aren't affected
            glMaterialfv(GL_FRONT, GL_EMISSION, [0.0, 0.0, 0.0, 1.0])

        glPopMatrix()

    # --- NEW METHOD ---
    def hit(self):
        """Call this to activate the 'hit' state."""
        self.hit_timer = self.HIT_DURATION

    # --- NEW METHOD ---
    def update(self, seconds_passed):
        """
        Updates the star's internal state, called once per frame.
        This will count down the hit_timer.
        """
        if self.hit_timer > 0:
            self.hit_timer -= seconds_passed
            if self.hit_timer < 0:
                self.hit_timer = 0.0