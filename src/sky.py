from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import random

class Sky:
    def __init__(self):
        self.star_positions = []
        self.num_stars = 150
        
        # Generate random positions for stars
        # We place them far away (e.g., radius 200-300)
        for _ in range(self.num_stars):
            x = random.uniform(-300, 300)
            y = random.uniform(50, 300)  # Keep them in the upper hemisphere
            z = random.uniform(-300, 300)
            self.star_positions.append((x, y, z))

    def draw(self):
        # 1. Save current state
        glPushMatrix()
        
        # 2. Disable lighting so stars/moon glow (use pure color)
        glDisable(GL_LIGHTING)
        glDisable(GL_TEXTURE_2D) # Ensure no textures are applied

        # --- DRAW STARS ---
        glColor3f(1.0, 1.0, 0.8) # Light yellow/white stars
        glPointSize(2.0)         # Make them visible
        
        glBegin(GL_POINTS)
        for pos in self.star_positions:
            glVertex3f(pos[0], pos[1], pos[2])
        glEnd()

        # --- DRAW MOON ---
        # Position the moon high up and somewhat in front/right
        glTranslatef(50.0, 100.0, -150.0) 
        
        # Moon Color (Pale Yellow/White)
        glColor3f(0.9, 0.9, 0.8) 
        
        # Draw Moon Sphere
        glutSolidSphere(15.0, 20, 20) 

        # 3. Restore lighting (if it was enabled previously)
        glEnable(GL_LIGHTING)
        glPopMatrix()