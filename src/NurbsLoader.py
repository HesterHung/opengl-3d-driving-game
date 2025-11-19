from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

class NurbsModel:
    # --- UPDATED INIT: Added 'scale' parameter (default is 1.0, 1.0, 1.0) ---
    def __init__(self, x, y, z, filename, scale=(1.0, 1.0, 1.0), color=(0.5, 0.5, 0.5)):
        self.posX = x
        self.posY = y
        self.posZ = z
        self.scale = scale   # Store the scale values
        self.color = color
        self.ctrlpoints = []
        
        # --- Load Control Points ---
        try:
            with open(filename, 'r') as f:
                temp_points = []
                for line in f:
                    parts = line.strip().split(',')
                    if len(parts) == 3:
                        pt = [float(parts[0]), float(parts[1]), float(parts[2])]
                        temp_points.append(pt)
                
                if len(temp_points) >= 16:
                    self.ctrlpoints = [
                        temp_points[0:4],
                        temp_points[4:8],
                        temp_points[8:12],
                        temp_points[12:16]
                    ]
                    print(f"Loaded NURBS: {filename}")
                else:
                    print(f"Error: {filename} needs 16 points.")
                    self.create_fallback()

        except Exception as e:
            print(f"Failed to load {filename}: {e}")
            self.create_fallback()

    def create_fallback(self):
        self.ctrlpoints = [
            [[-1,0,0], [-0.5,0,0], [0.5,0,0], [1,0,0]],
            [[-1,0,1], [-0.5,0,1], [0.5,0,1], [1,0,1]],
            [[-1,0,2], [-0.5,0,2], [0.5,0,2], [1,0,2]],
            [[-1,0,3], [-0.5,0,3], [0.5,0,3], [1,0,3]]
        ]

    def draw(self):
        glPushMatrix()
        glTranslatef(self.posX, self.posY, self.posZ)
        
        # --- UPDATED DRAW: Apply the stored scale ---
        glScalef(self.scale[0], self.scale[1], self.scale[2])
        # -------------------------------------------
        
        glColor3f(self.color[0], self.color[1], self.color[2])
        glMaterialfv(GL_FRONT, GL_DIFFUSE, [self.color[0], self.color[1], self.color[2], 1.0])
        glMaterialfv(GL_FRONT, GL_AMBIENT, [self.color[0]*0.5, self.color[1]*0.5, self.color[2]*0.5, 1.0])

        glEnable(GL_MAP2_VERTEX_3)
        glEnable(GL_AUTO_NORMAL)

        glMap2f(GL_MAP2_VERTEX_3, 0, 1, 0, 1, self.ctrlpoints)
        glMapGrid2f(20, 0.0, 1.0, 20, 0.0, 1.0)
        glEvalMesh2(GL_FILL, 0, 20, 0, 20)

        glDisable(GL_AUTO_NORMAL)
        glDisable(GL_MAP2_VERTEX_3)
        
        glPopMatrix()