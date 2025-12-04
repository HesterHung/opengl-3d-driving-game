from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random

class ribbon:
    # --- Constants ---
    BOOST_DURATION = 3.0 # How long the boost lasts in seconds

    # --- Properties ---
    def __init__(self, x_pos, z_pos, length, width):
        self.posX = x_pos
        self.posY = 0.01 # Slightly above the road to prevent z-fighting
        self.posZ = z_pos
        self.length = length # How long the ribbon is (along Z-axis)
        self.width = width   # How wide the ribbon is (using `land` from main)

        # --- State ---
        self.boost_active = False
        self.boost_timer = 0.0
        self.collected = False

    def draw(self):
        """
        Draws the ribbon. This method assumes GL_LIGHTING has been
        disabled *before* it is called, as it's a simple, unlit polygon.
        """
        # Removed "if self.collected: return" to make it persistent

        if self.boost_active:
            glColor3f(1.0, 0.5, 0.0) # Orange when active
        else:
            glColor3f(0.0, 1.0, 1.0) # Cyan when inactive
        
        glBegin(GL_POLYGON)
        glVertex3f(self.posX - self.width, self.posY, self.posZ)
        glVertex3f(self.posX + self.width, self.posY, self.posZ)
        glVertex3f(self.posX + self.width, self.posY, self.posZ + self.length)
        glVertex3f(self.posX - self.width, self.posY, self.posZ + self.length)
        glEnd()

    def update(self, seconds_passed, jeep_z_pos):
        # Deprecated method, logic moved to RibbonManager
        pass

class RibbonManager:
    def __init__(self, land_width):
        self.ribbons = []
        self.land_width = land_width
        self.boost_active = False
        self.boost_timer = 0.0
        self.BOOST_DURATION = 3.0
        
        self.next_spawn_z = 50.0
        
    def update(self, seconds_passed, jeep_z, jeep_x):
        # Update boost timer
        boost_just_activated = False
        boost_just_deactivated = False
        
        if self.boost_active:
            self.boost_timer -= seconds_passed
            if self.boost_timer <= 0:
                self.boost_active = False
                boost_just_deactivated = True
        
        # Check collisions
        for r in self.ribbons:
            # Check Z bounds
            if (jeep_z >= r.posZ and jeep_z <= (r.posZ + r.length)):
                # Check X bounds
                if (jeep_x >= r.posX - r.width and jeep_x <= r.posX + r.width):
                    # Hit!
                    self.boost_active = True
                    self.boost_timer = self.BOOST_DURATION
                    boost_just_activated = True
                    
                    # Mark this specific ribbon as active so it changes color
                    r.boost_active = True
            else:
                # Reset color if not on it (optional, or keep it lit for a bit?)
                # Requirement says "when using the ribbon", implying while on it or while boost is active.
                # If we want it to light up ONLY when on it:
                r.boost_active = False
        
        # Generate new ribbons
        while self.next_spawn_z < jeep_z + 300.0:
            # Random width: 0.3 * land to 1.0 * land (Half-width)
            # Road width is 2 * land_width. 
            # Requirement: min width = 0.3 * road width = 0.6 * land_width.
            # So min half-width = 0.3 * land_width.
            
            half_w = random.uniform(0.3 * self.land_width, 0.8 * self.land_width)
            
            # Random X Position
            # Must fit within [-land_width, land_width]
            min_x = -self.land_width + half_w
            max_x = self.land_width - half_w
            
            if min_x < max_x:
                x_pos = random.uniform(min_x, max_x)
            else:
                x_pos = 0
            
            length = 5.0
            r = ribbon(x_pos, self.next_spawn_z, length, half_w)
            self.ribbons.append(r)
            
            # Next spawn distance
            self.next_spawn_z += random.uniform(100.0, 300.0)
            
        # Cleanup
        self.ribbons = [r for r in self.ribbons if r.posZ > jeep_z - 50.0]
        
        return boost_just_activated, boost_just_deactivated, self.boost_active

    def draw(self):
        for r in self.ribbons:
            r.draw()