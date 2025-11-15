from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math

class ribbon:
    # --- Constants ---
    BOOST_DURATION = 3.0 # How long the boost lasts in seconds

    # --- Properties ---
    def __init__(self, z_pos, length, width):
        self.posY = 0.01 # Slightly above the road to prevent z-fighting
        self.posZ = z_pos
        self.length = length # How long the ribbon is (along Z-axis)
        self.width = width   # How wide the ribbon is (using `land` from main)

        # --- State ---
        self.boost_active = False
        self.boost_timer = 0.0

    def draw(self):
        """
        Draws the ribbon. This method assumes GL_LIGHTING has been
        disabled *before* it is called, as it's a simple, unlit polygon.
        """
        if self.boost_active:
            glColor3f(1.0, 0.5, 0.0) # Orange when active
        else:
            glColor3f(0.0, 1.0, 1.0) # Cyan when inactive
        
        glBegin(GL_POLYGON)
        glVertex3f(-self.width, self.posY, self.posZ)
        glVertex3f(self.width, self.posY, self.posZ)
        glVertex3f(self.width, self.posY, self.posZ + self.length)
        glVertex3f(-self.width, self.posY, self.posZ + self.length)
        glEnd()

    def update(self, seconds_passed, jeep_z_pos):
        """
        Updates the ribbon's internal timer and collision state.
        
        Args:
            seconds_passed (float): Time elapsed since the last frame.
            jeep_z_pos (float): The jeep's current Z position.
            
        Returns:
            tuple (bool, bool, bool): 
                (boost_just_activated, 
                 boost_just_deactivated, 
                 is_currently_active)
        """
        
        boost_just_activated = False 
        boost_just_deactivated = False

        if self.boost_active:
            # --- Timer is running ---
            self.boost_timer -= seconds_passed
            if self.boost_timer <= 0:
                self.boost_active = False
                self.boost_timer = 0.0
                boost_just_deactivated = True
        else:
            # --- Check for collision ---
            if (jeep_z_pos >= self.posZ and 
                jeep_z_pos <= (self.posZ + self.length)):
                
                # Hit the ribbon!
                self.boost_active = True
                self.boost_timer = self.BOOST_DURATION
                boost_just_activated = True
        
        return boost_just_activated, boost_just_deactivated, self.boost_active