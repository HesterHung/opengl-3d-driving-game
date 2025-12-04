#!/usr/bin/env python
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math, time, random, csv, datetime, json, os
import ImportObject
import PIL.Image as Image
import jeep, cone, star, ribbon, streetlight, sky
import tkinter as tk            
from tkinter import ttk          
from ShaderProgram import ShaderProgram

shaderProgram = None

class Projectile:
    def __init__(self, x, y, z, vx, vz, p_type="normal"):
        self.posX = x
        self.posY = y
        self.posZ = z
        self.velX = vx
        self.velZ = vz
        self.life = 5.0 # Seconds to live
        self.p_type = p_type
        self.rotation = 0.0

projectiles = []
boss_attack_timer = 0.0
projectileModel = None
jeep_blocked_vector = None

class JSONNurbsLoader:
    def __init__(self, filename, color=(0.5, 0.5, 0.5)):
        self.color = color
        self.nurbsRenderer = gluNewNurbsRenderer()
        
        # Setup rendering properties for "True" NURBS
        # Lower tolerance = smoother curve (default is 50.0)
        gluNurbsProperty(self.nurbsRenderer, GLU_SAMPLING_TOLERANCE, 5.0)
        # Switch to Fill mode for a solid surface
        gluNurbsProperty(self.nurbsRenderer, GLU_DISPLAY_MODE, GLU_FILL)
        
        # Load the JSON data
        self.valid = False
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            surface = data["nurbs_surface"]
            self.degree_u = surface["degree_u"]
            self.degree_v = surface["degree_v"]
            
            # RAW KNOTS
            self.knots_u = surface["knot_vector_u"]
            self.knots_v = surface["knot_vector_v"]
            
            # 1. Interpret JSON control points.
            # Analysis of the points suggests 8 strips of 5 points (Meridians).
            # 40 points total.
            raw_points = surface["control_points"]
            self.total_points = len(raw_points)

            # Heuristic to detect grid dimensions
            if self.total_points == 40:
                # Sphere/Dome: 8 strips of 5 points
                self.u_count = 8
                self.v_count = 5
            elif self.total_points == 10:
                # Arch/Tunnel: 5 strips of 2 points (Linear extrusion)
                self.u_count = 5
                self.v_count = 2
            else:
                # Fallback: Try to guess based on degree or just assume square
                # If degree_v is 1, it's likely v_count=2
                if self.degree_v == 1:
                     self.v_count = 2
                     self.u_count = self.total_points // 2
                else:
                     self.u_count = 4
                     self.v_count = 10
            
            # Reshape flat list into [u][v][4] (x,y,z,w)
            self.ctrlpoints = []
            
            idx = 0
            for i in range(self.u_count):
                row = []
                for j in range(self.v_count):
                    if idx < len(raw_points):
                        p = raw_points[idx]
                        # Create Rational Point (wx, wy, wz, w)
                        # Note: GLU expects pre-multiplied coordinates for Rational surfaces
                        wx = p['x'] * p['w']
                        wy = p['y'] * p['w']
                        wz = p['z'] * p['w']
                        row.append([wx, wy, wz, p['w']])
                    else:
                        row.append([0,0,0,1])
                    idx += 1
                self.ctrlpoints.append(row)
            
            # 2. Close the loop for the sphere (U direction)
            # Only apply this for the sphere model (40 points) which is known to be a revolution.
            if self.total_points == 40:
                first_strip = self.ctrlpoints[0]
                last_strip = self.ctrlpoints[-1]
                
                # Simple check: compare first point of first and last strip
                p1 = first_strip[0]
                p2 = last_strip[0]
                dist = math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2 + (p1[2]-p2[2])**2)
                
                if dist > 0.001:
                    print("Closing the NURBS loop by duplicating the first strip.")
                    self.ctrlpoints.append(first_strip)
                    self.u_count += 1

            # Check if knot vectors are valid, if not, regenerate them
            required_u = self.u_count + self.degree_u + 1
            required_v = self.v_count + self.degree_v + 1
            
            if len(self.knots_u) != required_u:
                print(f"Regenerating U knots. Expected {required_u}, got {len(self.knots_u)}")
                self.knots_u = self.generate_knot_vector(self.degree_u, self.u_count)

            if len(self.knots_v) != required_v:
                print(f"Regenerating V knots. Expected {required_v}, got {len(self.knots_v)}")
                self.knots_v = self.generate_knot_vector(self.degree_v, self.v_count)

            self.valid = True
            print(f"Loaded NURBS JSON: {self.u_count}x{self.v_count} grid.")

        except Exception as e:
            print(f"Failed to load NURBS JSON: {e}")

    def generate_knot_vector(self, degree, num_points):
        # Clamped uniform knot vector
        order = degree + 1
        num_segments = num_points - degree
        
        knots = [0.0] * order
        for i in range(1, num_segments):
            knots.append(i / float(num_segments))
        knots.extend([1.0] * order)
        
        return knots

    def makeDisplayLists(self):
        self.displayList = glGenLists(1)
        glNewList(self.displayList, GL_COMPILE)
        
        # Enable auto-normal generation for lighting
        glEnable(GL_AUTO_NORMAL)
        glEnable(GL_NORMALIZE)

        # Set Material Properties for the NURBS surface
        # A shiny red material to show curvature
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT, [0.2, 0.0, 0.0, 1.0])
        glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE, [0.8, 0.0, 0.0, 1.0])
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 50.0)

        gluBeginSurface(self.nurbsRenderer)
        try:
            # Use PyOpenGL's Pythonic gluNurbsSurface wrapper which
            # derives strides and orders automatically from the 3D
            # control-point array and knot vectors.
            gluNurbsSurface(
                self.nurbsRenderer,
                self.knots_u,
                self.knots_v,
                self.ctrlpoints,
                GL_MAP2_VERTEX_4
            )
        except Exception as e:
            print(f"NURBS surface render error: {e}")
        gluEndSurface(self.nurbsRenderer)
        
        glEndList()

    def draw(self):
        if not self.valid: return
        
        glPushMatrix()
        # Place the tunnel clearly in front of the jeeps, above the road
        glTranslatef(0.0, 0.0, 100.0)
        glScalef(20.0, 20.0, 40.0)
        
        if self.displayList:
            glCallList(self.displayList)
        else:
            self.makeDisplayLists()
            glCallList(self.displayList)
        
        glPopMatrix()

def initShaders():
    global shaderProgram
    shaderProgram = ShaderProgram("shaders/basic.vert", "shaders/basic.frag")
    if shaderProgram.program_id == 0:
        print("Shader compilation failed, falling back to fixed function pipeline.")
        shaderProgram = None

# --- Mode Constants ---
MODE_GAME = 0
MODE_DISPLAY = 1
MODE_INTRO = 2
MODE_VICTORY = 3
MODE_GAME_OVER = 4
currentMode = MODE_GAME # Default

# --- Intro Story Variables ---
introTime = 0.0
gameOverTimer = 0.0
villainStar = star.star(0, 50) # Spawn it further down the road
villainStar.sizeX = 3.0 # Make it a BIG boss star
villainStar.sizeY = 3.0
villainStar.sizeZ = 3.0
villainStar.posY = 20.0 # Start high in the air

victoryTimer = 0.0
victoryX = 0.0
victoryZ = 0.0
finalTimeStr = ""

minionStars = []
for _ in range(10):
    s = star.star(0, 0)
    s.sizeX = 0.8 # Smaller than normal stars
    s.sizeY = 0.8
    s.sizeZ = 0.8
    s.posY = 15.0 # Start high up (hidden)
    minionStars.append(s)

# windowSize = 600
windowWidth = 600
windowHeight = 600
isFullScreen = False
prevWidth, prevHeight = windowWidth, windowHeight
prevPosX, prevPosY = 0, 0

helpWindow = False
helpWin = 0
overWin = 0
mainWin = 0
centered = False

gameStartTime = 0.0
GAME_DURATION = 1000.0
timeLeft = GAME_DURATION
beginTime = 0
countTime = 0
score = 0
finalScore = 0
canStart = False
overReason = ""

stars_collected = 0
STARS_TO_WIN = 10
star_effect_timer = 0.0
last_star_x = 0.0
last_star_z = 0.0
boss_battle_active = False

#for wheel spinning
tickTime = 0

#creating objects
objectArray = []
jeep1Obj = jeep.jeep('p')
jeep2Obj = jeep.jeep('g')
jeep3Obj = jeep.jeep('r')

new_size = 0.85

# Apply to Player Jeep
jeep1Obj.sizeX = new_size
jeep1Obj.sizeY = new_size
jeep1Obj.sizeZ = new_size

# Apply to Friend Jeep
jeep2Obj.sizeX = new_size
jeep2Obj.sizeY = new_size
jeep2Obj.sizeZ = new_size

allJeeps = [jeep1Obj, jeep2Obj, jeep3Obj]
jeepNum = 0
jeepObj = allJeeps[jeepNum]

#concerned with camera
eyeX = 0.0
eyeY = 2.0
eyeZ = 10.0
midDown = False
topView = False
behindView = False

#concerned with panning
nowX = 0.0
nowY = 0.0
mouseSensitivity = 0.01

angle = 0.0
radius = 10.0
phi = 0.0

#concerned with scene development
land = 20
gameEnlarge = 10

#concerned with obstacles (cones) & rewards (stars)
coneAmount = 15
starAmount = 20 
diamondAmount = 1 
usedDiamond = False

allcones = []
allstars = []
allstreetlights = []

skyObj = sky.Sky()

obstacleCoord = []
rewardCoord = []
ckSense = 6.0

# Dictionary to hold the state of movement keys
keyState = {
    'up': False,
    'down': False,
    'left': False,
    'right': False
}

# Speeds for frame-rate-independent movement
moveSpeed = 10.0 # Units per second
rotSpeed = 90.0  # Degrees per second

# --- Store base speeds and define boost speeds ---
NORMAL_SPEED = moveSpeed
NORMAL_ROT_SPEED = rotSpeed
BOOST_SPEED = 25.0
BOOST_ROT_SPEED = 120.0 

ribbonObj = ribbon.RibbonManager(land)

tunnelObj = JSONNurbsLoader(os.path.join(os.path.dirname(__file__), "nurbs_export.json"), color=(0.4, 0.4, 0.4))

#concerned with lighting
applyLighting = False
lightMode = 0  # 0: ambient, 1: point, 2: directional, 3: spot

fov = 30.0
attenuation = 1.0

light0_Position = [0.0, 1.0, 1.0, 1.0]
light0_Intensity = [0.75, 0.75, 0.75, 0.25]

light1_Position = [0.0, 0.0, 0.0, 0.0]
light1_Intensity = [0.25, 0.25, 0.25, 0.25]

matAmbient = [1.0, 1.0, 1.0, 1.0]
matDiffuse = [0.5, 0.5, 0.5, 1.0]
matSpecular = [0.5, 0.5, 0.5, 1.0]
matShininess  = 100.0


#--------------------------------------developing scene---------------
def drawGUIStar(x, y, radius):
    """ Draws a 2D yellow star at screen coordinates (x,y) """
    glPushMatrix()
    glTranslatef(x, y, 0)
    glScalef(radius, radius, 1.0)
    
    glColor3f(1.0, 0.8, 0.0) # Gold/Yellow
    glBegin(GL_TRIANGLE_FAN)
    glVertex2f(0.0, 0.0) # Center
    for i in range(11):
        angle = math.radians(i * 36)
        r = 1.0 if i % 2 == 0 else 0.4
        glVertex2f(r * math.sin(angle), r * math.cos(angle))
    glEnd()
    glPopMatrix()

class Scene:
    axisColor = (0.5, 0.5, 0.5, 0.5)
    axisLength = 50   # Extends to positive and negative on all axes
    landColor = (.47, .53, .6, 0.5) #Light Slate Grey
    landLength = land  # Extends to positive and negative on x and y axis
    landW = 1.0
    landH = 0.0
    cont = gameEnlarge
    
    def draw(self):
        self.drawAxis()
        self.drawLand()

    def drawAxis(self):
        glColor4f(self.axisColor[0], self.axisColor[1], self.axisColor[2], self.axisColor[3])
        glBegin(GL_LINES)
        glVertex(-self.axisLength, 0, 0)
        glVertex(self.axisLength, 0, 0)
        glVertex(0, -self.axisLength, 0)
        glVertex(0, self.axisLength, 0)
        glVertex(0, 0, -self.axisLength)
        glVertex(0, 0, self.axisLength)
        glEnd()

    def drawLand(self):
        glEnable(GL_TEXTURE_2D)
        if shaderProgram: shaderProgram.set_uniform_bool("useTexture", True)
        
        if lightMode == 0:
            glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_DECAL)
        else:
            glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)
            glColor3f(1.0, 1.0, 1.0)
            glMaterialfv(GL_FRONT, GL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
            glMaterialfv(GL_FRONT, GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
            glMaterialfv(GL_FRONT, GL_SPECULAR, [0.0, 0.0, 0.0, 1.0])

        glBindTexture(GL_TEXTURE_2D, roadTextureID)

        L = self.landLength
        
        minX = -L
        maxX = L
        totalWidth = maxX - minX

        # --- INFINITE ROAD LOGIC ---
        # Draw road relative to Jeep to appear infinite
        currentZ = jeepObj.posZ
        
        # Draw from behind the jeep to far ahead
        startZ = currentZ - 50.0
        endZ = currentZ + 300.0 
        
        # Snap to grid to prevent jittering
        step = 2.0
        startZ = math.floor(startZ / step) * step
        endZ = math.ceil(endZ / step) * step

        startX = minX
        endX = maxX
        
        glNormal3f(0.0, 1.0, 0.0) 

        glBegin(GL_QUADS)
        z = startZ
        while z < endZ:
            x = startX
            while x < endX:
                x1, z1 = x, z
                x2, z2 = x + step, z + step

                u1 = (L - x1) / totalWidth
                u2 = (L - x2) / totalWidth

                # Use world Z coordinates for V to allow infinite tiling
                # Scaling factor 0.05 controls texture repetition frequency
                v1 = z1 * 0.05
                v2 = z2 * 0.05

                glTexCoord2f(u1, v1); glVertex3f(x1, 0, z1)
                glTexCoord2f(u1, v2); glVertex3f(x1, 0, z2)
                glTexCoord2f(u2, v2); glVertex3f(x2, 0, z2)
                glTexCoord2f(u2, v1); glVertex3f(x2, 0, z1)
                
                x += step
            z += step
        glEnd()

        glDisable(GL_TEXTURE_2D)
        if shaderProgram: shaderProgram.set_uniform_bool("useTexture", False)

#--------------------------------------populating scene----------------
def staticObjects():
    global objectArray, projectileModel
    objectArray.append(Scene())
    projectileModel = star.star(0,0)
    projectileModel.sizeX = 0.5
    projectileModel.sizeY = 0.5
    projectileModel.sizeZ = 0.5
    print ('append')


def drawDisplayModeEnvironment():
    # Draw Axis
    glColor4f(0.5, 0.5, 0.5, 0.5)
    glBegin(GL_LINES)
    glVertex(-20, 0, 0); glVertex(20, 0, 0)
    glVertex(0, -20, 0); glVertex(0, 20, 0)
    glVertex(0, 0, -20); glVertex(0, 0, 20)
    glEnd()

    glDisable(GL_TEXTURE_2D)
    glNormal3f(0.0, 1.0, 0.0)
    
    if lightMode != 0:
        glMaterialfv(GL_FRONT, GL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
        glMaterialfv(GL_FRONT, GL_DIFFUSE, [0.6, 0.6, 0.6, 1.0])
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.0, 0.0, 0.0, 1.0]) 
    
    glColor3f(0.6, 0.6, 0.6)
    
    floorRadius = 15 
    step = 0.5 
    
    y = -0.01 

    glBegin(GL_QUADS)
    x = -floorRadius
    while x < floorRadius:
        z = -floorRadius
        while z < floorRadius:
            glVertex3f(x, y, z)
            glVertex3f(x, y, z + step)
            glVertex3f(x + step, y, z + step)
            glVertex3f(x + step, y, z)
            z += step
        x += step
    glEnd()

def isColliding():
    current_hitbox_radius = ckSense * jeepObj.sizeX 

    for obstacle in obstacleCoord: 
        d = math.sqrt((jeepObj.posX - obstacle[0])**2 + (jeepObj.posZ - obstacle[1])**2)
        if d <= current_hitbox_radius: 
            return True
            
    safe_road_width = land - (2.0 * jeepObj.sizeX)
    
    if (jeepObj.posX >= safe_road_width or jeepObj.posX <= -safe_road_width): 
        return True
        
    return False

def calculateSpotlightIntensity(tx, ty, tz, jeep):
    # 1. Calculate Light World Position
    # Local: (0, 1, 3) relative to Jeep
    # Rotated around Y by jeep.rotation
    rad = math.radians(jeep.rotation)
    sin_r = math.sin(rad)
    cos_r = math.cos(rad)
    
    # Offset from jeep center
    lx_offset = 3.0 * sin_r
    ly_offset = 1.0
    lz_offset = 3.0 * cos_r
    
    light_x = jeep.posX + lx_offset
    light_y = jeep.posY + ly_offset
    light_z = jeep.posZ + lz_offset
    
    # 2. Calculate Light World Direction
    # Local Direction: (0, -1, 1)
    # Rotated: x' = sin, y' = -1, z' = cos
    dir_x = sin_r
    dir_y = -1.0
    dir_z = cos_r
    
    # Normalize direction
    dir_len = math.sqrt(dir_x*dir_x + dir_y*dir_y + dir_z*dir_z)
    dir_x /= dir_len
    dir_y /= dir_len
    dir_z /= dir_len
    
    # 3. Vector to Target
    to_target_x = tx - light_x
    to_target_y = ty - light_y
    to_target_z = tz - light_z
    
    dist_sq = to_target_x**2 + to_target_y**2 + to_target_z**2
    dist = math.sqrt(dist_sq)
    
    if dist == 0: return 1.0
    if dist > 25.0: return 0.0 # Max range (increased for better feel)
    
    # Normalize vector to target
    to_target_x /= dist
    to_target_y /= dist
    to_target_z /= dist
    
    # 4. Dot Product (Cosine of angle)
    dot = to_target_x * dir_x + to_target_y * dir_y + to_target_z * dir_z
    
    # Cutoff is 60 degrees. cos(60) = 0.5
    if dot < 0.5: return 0.0
    
    # Intensity based on angle (dot) and distance
    dist_factor = 1.0 - (dist / 25.0)
    angle_factor = (dot - 0.5) * 2.0
    
    return dist_factor * angle_factor

def display():
    global jeepObj, canStart, score, beginTime, countTime, lightMode, timeLeft, GAME_DURATION
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    setView()

    glEnable(GL_NORMALIZE)

    if shaderProgram:
        shaderProgram.use()
        shaderProgram.set_uniform_1i("useLighting", 1 if lightMode != 0 else 0)
        shaderProgram.set_uniform_1i("useTexture", 0)
        for i in range(8):
             shaderProgram.set_uniform_bool(f"lightEnabled[{i}]", False)

    # --- 1. GLOBAL LIGHTING SETUP ---
    if lightMode == 0:  # Ambient/Flat
        glDisable(GL_LIGHTING)
        glDisable(GL_LIGHT0)
        if shaderProgram: shaderProgram.set_uniform_bool("lightEnabled[0]", False)
    else:
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0) 
        if shaderProgram: shaderProgram.set_uniform_bool("lightEnabled[0]", True) 

        current_light_color = light0_Intensity 
        light_pos = [0.0, 10.0, 5.0, 1.0]

        if lightMode == 4:
            # Moon Mode
            glLightModelfv(GL_LIGHT_MODEL_AMBIENT, [0.05, 0.05, 0.05, 1.0])
            moon_color = [0.15, 0.15, 0.25, 1.0] 
            current_light_color = moon_color
            light_pos = [0.0, 10.0, 5.0, 0.0] 
            glLightf(GL_LIGHT0, GL_SPOT_CUTOFF, 180.0)

        else:
            # Day Modes
            glLightModelfv(GL_LIGHT_MODEL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
            
            if currentMode == MODE_DISPLAY:
                if lightMode == 1: # Point
                    light_pos = [0.0, 6.0, 0.0, 1.0]
                    glLightf(GL_LIGHT0, GL_SPOT_CUTOFF, 180.0)
                elif lightMode == 2: # Directional
                    light_pos = [1.0, 1.0, 1.0, 0.0]
                    glLightf(GL_LIGHT0, GL_SPOT_CUTOFF, 180.0)
                elif lightMode == 3: # Spot
                    light_pos = [0.0, 8.0, 0.0, 1.0]
                    glLightfv(GL_LIGHT0, GL_SPOT_DIRECTION, [0.0, -1.0, 0.0])
                    glLightf(GL_LIGHT0, GL_SPOT_CUTOFF, 30.0)
                    glLightf(GL_LIGHT0, GL_SPOT_EXPONENT, 5.0)
                
                if lightMode != 2:
                    glPushMatrix()
                    glDisable(GL_LIGHTING)
                    glColor3f(1.0, 1.0, 0.0)
                    glTranslatef(light_pos[0], light_pos[1], light_pos[2])
                    glutWireSphere(0.2, 10, 10)
                    glEnable(GL_LIGHTING)
                    glPopMatrix()
            else:
                if lightMode == 1: # Point
                    light_pos = [0.0, 10.0, 5.0, 1.0]
                    glLightf(GL_LIGHT0, GL_SPOT_CUTOFF, 180.0)
                elif lightMode == 2: # Directional
                    light_pos = [0.0, 1.0, 1.0, 0.0]
                    glLightf(GL_LIGHT0, GL_SPOT_CUTOFF, 180.0)
                elif lightMode == 3: # Spot
                    light_pos = [0.0, 10.0, 0.0, 1.0]
                    glLightfv(GL_LIGHT0, GL_SPOT_DIRECTION, [0.0, -1.0, 0.0])
                    glLightf(GL_LIGHT0, GL_SPOT_CUTOFF, 45.0)

        glLightfv(GL_LIGHT0, GL_POSITION, light_pos)
        glLightfv(GL_LIGHT0, GL_DIFFUSE, current_light_color)
        glLightfv(GL_LIGHT0, GL_SPECULAR, current_light_color)

    if shaderProgram: shaderProgram.set_uniform_bool("useLighting", False)
    
    # Move sky with player to create infinite background effect
    glPushMatrix()
    glTranslatef(jeepObj.posX, 0.0, jeepObj.posZ)
    skyObj.draw()
    glPopMatrix()
    
    if shaderProgram and lightMode != 0: shaderProgram.set_uniform_bool("useLighting", True)

    # --- 2. DRAW BASED ON MODE ---
    if currentMode == MODE_INTRO:
        # === INTRO MODE RENDER ===
        
        # --- NEW: Setup Streetlights BEFORE drawing the scene ---
        # 1. Calculate distance to current Jeep position
        light_distances = []
        for sl in allstreetlights:
            dist = abs(sl.posZ - jeepObj.posZ)
            light_distances.append((dist, sl))

        # 2. Sort so closest lights get priority
        light_distances.sort(key=lambda x: x[0])
        available_ids = [GL_LIGHT2, GL_LIGHT3, GL_LIGHT4, GL_LIGHT5, GL_LIGHT6, GL_LIGHT7]

        # 3. Reset hardware lights to prevent ghosts
        for i in available_ids: 
            glDisable(i)
            if shaderProgram: shaderProgram.set_uniform_bool(f"lightEnabled[{i-GL_LIGHT0}]", False)

        # 4. Assign IDs and Enable Lights
        for i, (dist, sl) in enumerate(light_distances):
            if i < len(available_ids):
                sl.lightID = available_ids[i]
                # Enable the light now so it affects the floor
                glPushMatrix()
                glTranslatef(sl.posX, sl.height, sl.posZ)
                sl.enableLight()
                glPopMatrix()
            else:
                sl.lightID = None
        # ------------------------------------

        # Draw Scene (Road, Sky, Tunnel)
        for obj in objectArray: 
            obj.draw()
            
        glDisable(GL_LIGHTING) 
        if shaderProgram: 
            shaderProgram.set_uniform_bool("useTexture", False)
            shaderProgram.set_uniform_bool("useLighting", False)
        ribbonObj.draw() 
        if lightMode != 0: 
            glEnable(GL_LIGHTING)
            if shaderProgram: shaderProgram.set_uniform_bool("useLighting", True)
        
        tunnelObj.draw()
        
        # Draw Streetlights
        for sl in allstreetlights:
            sl.draw()
        
        # Draw Actors
        jeepObj.draw() 
        jeep2Obj.draw()
        
        if introTime > 5.0:
            villainStar.draw()

        if introTime > 10.0: 
            for s in minionStars:
                s.draw()

        # --- HUD: 2D Overlay for Story & Skip Text ---
        glDisable(GL_LIGHTING)
        if shaderProgram: shaderProgram.stop()

        # 1. Switch to 2D View
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, windowWidth, 0, windowHeight)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glDisable(GL_DEPTH_TEST) # Draw on top of everything

        # --- STORY TEXT (Top, Yellow, HUGE) ---
        glColor3f(1.0, 1.0, 0.0) # Yellow
        glLineWidth(3.0)         # Make the text bold/thick

        msg = ""
        if introTime < 5.0: msg = "Just chilling with my friend..."  
        elif introTime < 10.0: msg = "OH NO! A Giant Star appeared!" 
        elif introTime < 15.0: msg = "There are too many of them!"
        else: msg = "THEY TOOK HIM! I MUST SAVE HIM!"

        # --- NEW STROKE FONT LOGIC ---
        # 1. Define Scale (0.2 is approx size 24. Try 0.3 or 0.4 for HUGE)
        text_scale = 0.35 
        
        # 2. Calculate Exact Width to Center it
        text_width_units = 0
        for char in msg:
            text_width_units += glutStrokeWidth(GLUT_STROKE_ROMAN, ord(char))
        
        real_width = text_width_units * text_scale
        start_x = (windowWidth - real_width) / 2
        start_y = windowHeight - 100

        # 3. Draw Stroke Text
        glPushMatrix()
        glTranslatef(start_x, start_y, 0)        # Move to position
        glScalef(text_scale, text_scale, 1.0)    # Scale it up
        for char in msg:
            glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(char))
        glPopMatrix()
        
        glLineWidth(1.0) # Reset line width for other objects

        # --- SKIP TEXT (Bottom, White, Normal) ---
        glColor3f(1.0, 1.0, 1.0) # White
        skip_msg = "[Press SPACE to Skip]"
        
        # Calculate center position (Approximate width for Helvetica 18)
        skip_width = len(skip_msg) * 9
        glRasterPos2f((windowWidth - skip_width) / 2, 30) 
        for char in skip_msg:
            glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))

        # 3. Restore 3D View
        glEnable(GL_DEPTH_TEST)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        
        if lightMode != 0: glEnable(GL_LIGHTING)

    elif currentMode == MODE_DISPLAY:
        # === DISPLAY MODE RENDER ===
        drawDisplayModeEnvironment()
        jeepObj.draw()
        
        glDisable(GL_LIGHTING)
        if shaderProgram: shaderProgram.stop()
        glColor3f(0.0, 1.0, 1.0)
        mode_name = "Ambient"
        if lightMode == 1: mode_name = "Point"
        elif lightMode == 2: mode_name = "Directional"
        elif lightMode == 3: mode_name = "Spotlight"
        elif lightMode == 4: mode_name = "Default (Moonlight)"
        text3d(f"Display Mode: {mode_name}", -2.0, 4.0, 0.0)
        
    elif currentMode == MODE_GAME_OVER:
        # === GAME OVER RENDER ===
        
        # Fade out lighting based on timer (starts after 1s, fades over 4s)
        fade = 1.0
        if gameOverTimer > 1.0:
            fade = max(0.0, 1.0 - ((gameOverTimer - 1.0) * 0.25))
        
        if lightMode != 0:
            glEnable(GL_LIGHTING)
            # Dim global light
            dimmed_light = [c * fade for c in light0_Intensity]
            glLightfv(GL_LIGHT0, GL_DIFFUSE, dimmed_light)
            glLightfv(GL_LIGHT0, GL_SPECULAR, dimmed_light)
        
        # Draw Scene
        for obj in objectArray: obj.draw()
        tunnelObj.draw()
        ribbonObj.draw()
        
        # Draw Boss
        villainStar.draw()
        
        # Draw Projectile (Big Red Star)
        for p in projectiles:
            glPushMatrix()
            glTranslatef(p.posX, p.posY, p.posZ)
            glRotatef(p.rotation, 0.0, 1.0, 0.0)
            glScalef(5.0, 5.0, 5.0) # HUGE
            
            # Glowing Red
            if lightMode != 0:
                glPushAttrib(GL_LIGHTING_BIT)
                glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, [1.0 * fade, 0.0, 0.0, 1.0])
                
            if projectileModel: projectileModel.obj.drawObject()
            
            if lightMode != 0: glPopAttrib()
            glPopMatrix()
            
        # Draw Jeep
        jeepObj.draw()
        
        # Draw "GAME OVER" Text
        glDisable(GL_LIGHTING)
        if shaderProgram: shaderProgram.stop()
        
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, windowWidth, 0, windowHeight)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glDisable(GL_DEPTH_TEST)
        
        glColor3f(1.0, 0.0, 0.0) # Red, staying bright
        msg = "GAME OVER"
        glLineWidth(4.0)
        
        glPushMatrix()
        # Center text roughly
        glTranslatef(windowWidth/2 - 150, windowHeight/2 + 50, 0)
        glScalef(0.5, 0.5, 1.0)
        for char in msg: glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(char))
        glPopMatrix()
        
        glLineWidth(1.0)

        # Reason
        glColor3f(1.0, 1.0, 1.0)
        glRasterPos2f(windowWidth/2 - 100, windowHeight/2 - 20)
        for char in str(overReason): glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))

        # Restart Instruction
        if gameOverTimer > 1.0:
            glColor3f(1.0, 1.0, 0.0)
            restart_msg = "Press 'r' to Restart"
            glRasterPos2f(windowWidth/2 - 100, windowHeight/2 - 100)
            for char in restart_msg: glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))

        glEnable(GL_DEPTH_TEST)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        
        if lightMode != 0: glEnable(GL_LIGHTING)

    elif currentMode == MODE_VICTORY:
        # 1. Draw Environment
        if shaderProgram: shaderProgram.set_uniform_bool("useLighting", False)
        skyObj.draw()
        if shaderProgram and lightMode != 0: shaderProgram.set_uniform_bool("useLighting", True)
        
        if lightMode != 0: glEnable(GL_LIGHTING)
        
        # --- NEW: Setup Streetlights BEFORE drawing the scene ---
        light_distances = []
        for sl in allstreetlights:
            dist = abs(sl.posZ - jeepObj.posZ)
            light_distances.append((dist, sl))

        light_distances.sort(key=lambda x: x[0])
        available_ids = [GL_LIGHT2, GL_LIGHT3, GL_LIGHT4, GL_LIGHT5, GL_LIGHT6, GL_LIGHT7]

        # Reset lights
        for i in available_ids: 
            glDisable(i)
            if shaderProgram: shaderProgram.set_uniform_bool(f"lightEnabled[{i-GL_LIGHT0}]", False)

        # Assign and Enable Lights
        for i, (dist, sl) in enumerate(light_distances):
            if i < len(available_ids):
                sl.lightID = available_ids[i]
                # Enable the light now so it affects the floor
                glPushMatrix()
                glTranslatef(sl.posX, sl.height, sl.posZ)
                sl.enableLight()
                glPopMatrix()
            else:
                sl.lightID = None
        # -------------------------------------------------------
        
        for obj in objectArray: obj.draw() # Floor/Axis
        tunnelObj.draw()
        
        glDisable(GL_LIGHTING)
        if shaderProgram: 
            shaderProgram.set_uniform_bool("useTexture", False)
            shaderProgram.set_uniform_bool("useLighting", False)
        ribbonObj.draw()
        if lightMode != 0: 
            glEnable(GL_LIGHTING)
            if shaderProgram: shaderProgram.set_uniform_bool("useLighting", True)
        
        # Draw Streetlights
        for sl in allstreetlights: sl.draw()

        # 2. Draw the Happy Jeeps
        jeepObj.draw()
        jeep2Obj.draw() 

        # 3. Draw Victory HUD
        glDisable(GL_LIGHTING)
        if shaderProgram: shaderProgram.stop()
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, windowWidth, 0, windowHeight)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glDisable(GL_DEPTH_TEST)

        # -- Main Text --
        glColor3f(0.0, 1.0, 0.0) # Green
        msg = "You Saved Your Friend!"
        glLineWidth(3.0)
        
        glPushMatrix()
        glTranslatef(50, 150, 0) 
        glScalef(0.25, 0.25, 1.0)
        for char in msg: glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(char))
        glPopMatrix()

        # -- Time Text --
        glColor3f(1.0, 1.0, 1.0) # White
        time_msg = finalTimeStr
        
        glPushMatrix()
        glTranslatef(50, 100, 0)
        glScalef(0.15, 0.15, 1.0)
        for char in time_msg: glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(char))
        glPopMatrix()

        # Restart Instruction
        if victoryTimer > 1.0:
            glColor3f(1.0, 1.0, 0.0)
            restart_msg = "Press 'r' to Restart"
            glRasterPos2f(50, 50)
            for char in restart_msg: glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))

        glLineWidth(1.0)
        glEnable(GL_DEPTH_TEST)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        if lightMode != 0: glEnable(GL_LIGHTING)

    else:
        # === GAME MODE RENDER ===
        # Headlights
        if jeepObj.lightOn and lightMode != 0: 
            glEnable(GL_LIGHT1)
            if shaderProgram: shaderProgram.set_uniform_bool("lightEnabled[1]", True)
            glPushMatrix()
            glTranslatef(jeepObj.posX, jeepObj.posY, jeepObj.posZ)
            glRotatef(jeepObj.rotation, 0.0, 1.0, 0.0)
            glScalef(jeepObj.sizeX, jeepObj.sizeY, jeepObj.sizeZ)
            headlightColor = [1.5, 1.5, 1.5, 1.0]
            glLightfv(GL_LIGHT1, GL_DIFFUSE, headlightColor)
            glLightfv(GL_LIGHT1, GL_SPECULAR, headlightColor)
            glLightfv(GL_LIGHT1, GL_POSITION, [0.0, 1.0, 3.0, 1.0])
            glLightfv(GL_LIGHT1, GL_SPOT_DIRECTION, [0.0, -1.0, 1.0])
            glLightf(GL_LIGHT1, GL_SPOT_CUTOFF, 60.0)
            glLightf(GL_LIGHT1, GL_SPOT_EXPONENT, 2.0)
            glLightf(GL_LIGHT1, GL_CONSTANT_ATTENUATION, 0.1)
            glLightf(GL_LIGHT1, GL_LINEAR_ATTENUATION, 0.01)
            glPopMatrix()
        else:
            glDisable(GL_LIGHT1)
            if shaderProgram: shaderProgram.set_uniform_bool("lightEnabled[1]", False)

        # Text
        glDisable(GL_LIGHTING)
        
        glDisable(GL_LIGHTING)
        if timeLeft <= 0:
            glColor3f(1.0, 0.0, 0.0) # Red
            # Draw "GAME OVER" floating above the jeep
            text3d("GAME OVER", jeepObj.posX, jeepObj.posY + 3.0, jeepObj.posZ)
        
        if lightMode != 0:
            glEnable(GL_LIGHTING)

        # --- NEW: Setup Streetlights BEFORE drawing the scene ---
        light_distances = []
        for sl in allstreetlights:
            dist = abs(sl.posZ - jeepObj.posZ)
            light_distances.append((dist, sl))

        light_distances.sort(key=lambda x: x[0])
        available_ids = [GL_LIGHT2, GL_LIGHT3, GL_LIGHT4, GL_LIGHT5, GL_LIGHT6, GL_LIGHT7]

        # Reset lights
        for i in available_ids: 
            glDisable(i)
            if shaderProgram: shaderProgram.set_uniform_bool(f"lightEnabled[{i-GL_LIGHT0}]", False)

        # Assign and Enable Lights
        for i, (dist, sl) in enumerate(light_distances):
            if i < len(available_ids):
                sl.lightID = available_ids[i]
                # Enable the light now so it affects the floor
                glPushMatrix()
                glTranslatef(sl.posX, sl.height, sl.posZ)
                sl.enableLight()
                glPopMatrix()
            else:
                sl.lightID = None
        # -------------------------------------------------------

        # Draw Objects
        for obj in objectArray: 
            obj.draw()

        glDisable(GL_LIGHTING) 
        if shaderProgram: 
            shaderProgram.set_uniform_bool("useTexture", False)
            shaderProgram.set_uniform_bool("useLighting", False)
        ribbonObj.draw() 
        if lightMode != 0: 
            glEnable(GL_LIGHTING)
            if shaderProgram: shaderProgram.set_uniform_bool("useLighting", True)

        if lightMode == 4:
            glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, [0.2, 0.2, 0.2, 1.0])
        else:
            glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, [0.0, 0.0, 0.0, 1.0])

        tunnelObj.draw()

        glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, [0.0, 0.0, 0.0, 1.0])

        # Remaining objects
        for sl in allstreetlights: sl.draw()
        for cone in allcones: cone.draw()
        for star in allstars: star.draw()

        # Draw Player Jeep
        jeepObj.draw()

        if star_effect_timer > 0:
            glDisable(GL_LIGHTING) 
            glDisable(GL_TEXTURE_2D)
            
            progress = 1.0 - (star_effect_timer / 0.4) 
            expansion = 1.5 + (progress * 3.0)
            
            glColor4f(1.0, 0.8, 0.0, 1.0 - progress) 
            
            glPushMatrix()
            
            # Make the effect follow the Jeep
            glTranslatef(jeepObj.posX, jeepObj.posY + 1.0, jeepObj.posZ) 
            
            glLineWidth(3.0)
            glutWireSphere(expansion, 10, 10)
            glLineWidth(1.0)
            
            glPopMatrix()
            
            if lightMode != 0: glEnable(GL_LIGHTING)

        if boss_battle_active:
            villainStar.draw()
            
            # Draw Projectiles
            for p in projectiles:
                glPushMatrix()
                glTranslatef(p.posX, p.posY, p.posZ)
                glRotatef(p.rotation, 0.0, 1.0, 0.0)
                
                # Scale based on type
                scale = 2.0
                if p.p_type == "big_star":
                    scale = 3.0
                
                glScalef(scale, scale, scale)
                
                # Make them glow red/orange
                if lightMode != 0:
                    glPushAttrib(GL_LIGHTING_BIT)
                    # High emission to look like fire/energy
                    glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, [1.0, 0.2, 0.0, 1.0])
                    
                if projectileModel:
                    projectileModel.obj.drawObject()
                
                if lightMode != 0:
                    glPopAttrib()
                    
                glPopMatrix()
    
        glDisable(GL_LIGHTING) 
        if shaderProgram: shaderProgram.stop()
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, windowWidth, 0, windowHeight)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glDisable(GL_DEPTH_TEST) 

        # --- 1. SCOREBOARD (Top Left) ---
        # Draw Star Icon (Scaled up)
        drawGUIStar(40, windowHeight - 40, 30)

        # Draw Score Text (Stroke Font = Scalable)
        glColor3f(1.0, 1.0, 1.0) 
        if boss_battle_active:
            score_msg = ": HIT THE BOSS!"
            # Flash Red/White for urgency
            if int(introTime * 10) % 2 == 0: glColor3f(1.0, 0.0, 0.0)
        else:
            score_msg = ": {} / {}".format(stars_collected, STARS_TO_WIN)
        
        glPushMatrix()
        glTranslatef(75, windowHeight - 50, 0) # Position next to star
        glScalef(0.3, 0.3, 1.0)                # Scale size (0.3 is large)
        glLineWidth(2.0)                       # Thicker lines
        for char in score_msg:
             glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(char))
        glPopMatrix()

        # --- 2. TIMER (Top Right) ---
        glColor3f(0.0, 1.0, 1.0) # Cyan

        mins = int(timeLeft // 60)
        secs = int(timeLeft % 60)
        timer_msg = "Time: {:02d}:{:02d}".format(mins, secs)
        
        # Calculate width to align to right
        timer_scale = 0.3
        timer_width = 0
        for char in timer_msg:
            timer_width += glutStrokeWidth(GLUT_STROKE_ROMAN, ord(char))
        
        real_timer_width = timer_width * timer_scale
        timer_x = windowWidth - real_timer_width - 30 # 30px padding from right
        
        glPushMatrix()
        glTranslatef(timer_x, windowHeight - 50, 0)
        glScalef(timer_scale, timer_scale, 1.0)
        glLineWidth(2.0)
        for char in timer_msg:
             glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(char))
        glPopMatrix()

        glLineWidth(1.0) # Reset line width
        
        # Restore 3D Mode
        glEnable(GL_DEPTH_TEST)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        
        if currentMode == MODE_VICTORY:
             glDisable(GL_LIGHTING)
             glMatrixMode(GL_PROJECTION)
             glPushMatrix()
             glLoadIdentity()
             gluOrtho2D(0, windowWidth, 0, windowHeight)
             glMatrixMode(GL_MODELVIEW)
             glPushMatrix()
             glLoadIdentity()
             
             glColor3f(1.0, 1.0, 0.0)
             drawTextBitmap("Press 'r' to Restart", windowWidth/2 - 80, windowHeight/2 - 100)
             
             glPopMatrix()
             glMatrixMode(GL_PROJECTION)
             glPopMatrix()
             glMatrixMode(GL_MODELVIEW)
             if lightMode != 0: glEnable(GL_LIGHTING)

        if lightMode != 0: glEnable(GL_LIGHTING)

    if shaderProgram:
        shaderProgram.stop()

    glutSwapBuffers()

def updateIntro(dt):
    global introTime, jeepObj, jeep2Obj, villainStar, currentMode, minionStars
    
    introTime += dt
    
    myLane = -5   
    friendLane = 5
    
    # -- SCENE 1: Chilling (0s to 5s) --
    if introTime < 5.0: # Changed from 3.0
        speed = 5.0 * dt
        jeepObj.posZ += speed
        jeep2Obj.posZ += speed
        
        jeepObj.posX = myLane      
        jeep2Obj.posX = friendLane 
        
        jeepObj.wheelDir = 'fwd'
        jeep2Obj.wheelDir = 'fwd'
        jeepObj.rotateWheel(-0.1 * (dt*1000))
        jeep2Obj.rotateWheel(-0.1 * (dt*1000))

    # -- SCENE 2: The Boss Appears (5s to 10s) --
    elif introTime < 10.0: # Changed from 6.0
        jeepObj.wheelDir = 'stop'
        jeep2Obj.wheelDir = 'stop'
        
        # Giant Star Drops
        targetY = 3.0
        if villainStar.posY > targetY:
            villainStar.posY -= 30.0 * dt
        
        villainStar.posZ = jeepObj.posZ + 15.0
        villainStar.posX = (myLane + friendLane) / 2.0 

    # -- SCENE 3: Minions Swarm (10s to 15s) --
    elif introTime < 15.0: # Changed from 9.0
        # 1. Calculate Center of "US"
        centerX = (jeepObj.posX + jeep2Obj.posX) / 2.0
        centerZ = jeepObj.posZ
        
        circle_radius = 12.0 
        orbit_speed = 2.5
        
        # 2. Update every Minion position
        for i, s in enumerate(minionStars):
            angle_offset = (math.pi * 2 / 10) * i
            current_angle = (introTime * orbit_speed) + angle_offset
            
            s.posX = centerX + math.cos(current_angle) * circle_radius
            s.posZ = centerZ + math.sin(current_angle) * circle_radius
            s.posY = 4.0 + math.sin(introTime * 5.0 + i) 
            s.rotation += 200 * dt

    # -- SCENE 4: Kidnapping (15s to 19s) --
    elif introTime < 19.0: # Changed from 11.0
        fly_speed = 40.0 * dt
        
        villainStar.posZ += fly_speed
        jeep2Obj.posZ += fly_speed 
        
        for s in minionStars:
            s.posZ += fly_speed

    else:
        startGameplay()

def idle():
    global tickTime, prevTime, score, keyState, jeepObj, canStart, moveSpeed, rotSpeed
    global aiStar, aiStarSpeed, aiStarDir, lightMode, gameStartTime, timeLeft
    global stars_collected, STARS_TO_WIN, star_effect_timer
    global boss_battle_active, villainStar, currentMode, victoryTimer, gameOverTimer
    global jeep_blocked_vector, projectiles, overReason, finalScore

    curTime = glutGet(GLUT_ELAPSED_TIME)
    tickTime =  curTime - prevTime
    prevTime = curTime
    
    if currentMode == MODE_GAME:
        # Calculate elapsed time
        elapsed = (curTime / 1000.0) - gameStartTime
        timeLeft = GAME_DURATION - elapsed
        
        if timeLeft <= 0:
            timeLeft = 0
            canStart = False
            jeepObj.wheelDir = 'stop'
            
            # Transition to Game Over
            currentMode = MODE_GAME_OVER
            gameOverTimer = 0.0
            overReason = "Time's Up!"
            finalScore = score
            
            # Move player to center so they get hit
            jeepObj.posX = 0.0
            
            # Setup Boss
            villainStar.posX = 0.0
            villainStar.posZ = jeepObj.posZ + 40.0
            villainStar.posY = 5.0
            villainStar.rotation = 180.0 
            
            # Clear projectiles and add the "Big Red Star"
            projectiles = []
            # Create a big star moving towards player
            p = Projectile(villainStar.posX, villainStar.posY, villainStar.posZ, 0.0, -15.0, "game_over_star")
            projectiles.append(p)
            
        score = timeLeft 

    if tickTime == 0: 
        glutPostRedisplay()
        return

    seconds_passed = tickTime / 1000.0

    if currentMode == MODE_VICTORY:
        victoryTimer += seconds_passed
        
        base_height = 2.0
        jump_height = abs(math.sin(victoryTimer * 8.0)) * 1.5
        
        jeepObj.posY = base_height + jump_height
        jeep2Obj.posY = base_height + jump_height
        
        # Spin wheels while in air
        jeepObj.rotateWheel(-5.0 * seconds_passed)
        jeep2Obj.rotateWheel(-5.0 * seconds_passed)
        
        glutPostRedisplay()
        return
    
    if currentMode == MODE_GAME_OVER:
        gameOverTimer += seconds_passed
        
        # Update Projectiles (The Big Red Star)
        for p in projectiles:
            # Move projectile
            p.posZ += p.velZ * seconds_passed
            p.rotation += 200 * seconds_passed
            
            # Check collision with Jeep
            if dist((jeepObj.posX, jeepObj.posZ), (p.posX, p.posZ)) < 4.0:
                # Hit! Push player back into darkness
                push_speed = 40.0
                jeepObj.posZ -= push_speed * seconds_passed
                
                # Keep projectile attached
                p.posZ = jeepObj.posZ + 3.0 
                p.velZ = -push_speed # Match speed
                
                # Spin jeep out of control
                jeepObj.rotation += 360 * seconds_passed
        
        glutPostRedisplay()
        return

    if currentMode == MODE_INTRO:
            updateIntro(seconds_passed)

    elif currentMode == MODE_GAME:

        if star_effect_timer > 0:
            star_effect_timer -= seconds_passed

        # --- Jeep Movement Logic ---
        boost_on, boost_off, is_active = ribbonObj.update(seconds_passed, jeepObj.posZ, jeepObj.posX)
        if boost_on:
            moveSpeed = BOOST_SPEED
            rotSpeed = BOOST_ROT_SPEED
        elif boost_off:
            moveSpeed = NORMAL_SPEED
            rotSpeed = NORMAL_ROT_SPEED

        if canStart:
            moveAmount = moveSpeed * seconds_passed
            rotAmount = rotSpeed * seconds_passed

            oldX = jeepObj.posX
            oldZ = jeepObj.posZ
            isMoving = False

            # --- Check for blocked movement ---
            blocked_forward = False
            if jeep_blocked_vector:
                rad = math.radians(jeepObj.rotation)
                fx = math.sin(rad)
                fz = math.cos(rad)
                bx, bz = jeep_blocked_vector
                if (fx * bx + fz * bz) > 0: blocked_forward = True

            if keyState['up']:
                if not blocked_forward:
                    jeepObj.move(False, moveAmount)
                    jeepObj.wheelDir = 'fwd'
                    isMoving = True
            elif keyState['down']:
                jeepObj.move(False, -moveAmount)
                jeepObj.wheelDir = 'back'
                isMoving = True
            else:
                jeepObj.wheelDir = 'stop'

            if keyState['left']:
                jeepObj.move(True, rotAmount)
                isMoving = True 
            elif keyState['right']:
                jeepObj.move(True, -rotAmount)
                isMoving = True 

            if isMoving and isColliding(): 
                jeepObj.posX = oldX
                jeepObj.posZ = oldZ
                jeepObj.wheelDir = 'stop'

        # --- INFINITE WORLD RECYCLING ---
        # Recycle objects that are too far behind (or ahead) of the jeep
        recycle_dist = 50.0
        spawn_dist = 200.0
        total_span = recycle_dist + spawn_dist
        
        # 1. Streetlights
        for sl in allstreetlights:
            # Too far behind (Player moving forward)
            if sl.posZ < jeepObj.posZ - recycle_dist:
                sl.posZ += total_span
            # Too far ahead (Player moving backward)
            elif sl.posZ > jeepObj.posZ + spawn_dist:
                sl.posZ -= total_span
        
        # 2. Stars (Only if not in boss battle)
        if not boss_battle_active:
            for s in allstars:
                # Too far behind
                if s.posZ < jeepObj.posZ - recycle_dist:
                    s.posZ += total_span
                    s.posY = 2.0 # Reset height if it was collected
                    s.posX = random.uniform(-land + 5, land - 5) # Randomize X
                # Too far ahead
                elif s.posZ > jeepObj.posZ + spawn_dist:
                    s.posZ -= total_span
                    s.posY = 2.0
                    s.posX = random.uniform(-land + 5, land - 5)
        
        # 3. Cones
        for c in allcones:
            # Too far behind
            if c.posZ < jeepObj.posZ - recycle_dist:
                c.posZ += total_span
                c.posX = random.uniform(-land + 2, land - 2)
            # Too far ahead
            elif c.posZ > jeepObj.posZ + spawn_dist:
                c.posZ -= total_span
                c.posX = random.uniform(-land + 2, land - 2)
                # Update collision coord list (This is tricky with the current list structure)
                # Ideally, we should rebuild obstacleCoord list every frame or use objects directly
                # For now, we'll just update the object position.
                # The collision check uses 'obstacleCoord' which is a list of tuples.
                # We need to update that list.
        
        # Rebuild obstacleCoord list for collision detection
        obstacleCoord[:] = [] # Clear list
        for c in allcones:
            obstacleCoord.append((c.posX, c.posZ))

        
        # --- 1. NORMAL GAME LOOP (Collecting Stars) ---
        if not boss_battle_active:
            jeep_blocked_vector = None
            for s in allstars:
                s.update(seconds_passed) 
                
                # --- LIGHT REACTION LOGIC ---
                # Default speed
                current_star_speed = s.speed
                
                # 1. Check Main Light (GL_LIGHT0)
                # Only Point (1) and Spot (3) have a specific position that matters for proximity
                main_light_pos = None
                if lightMode == 1: # Point
                    main_light_pos = (0.0, 6.0, 0.0)
                elif lightMode == 3: # Spot
                    main_light_pos = (0.0, 8.0, 0.0)
                
                if main_light_pos:
                    dist_sq = (s.posX - main_light_pos[0])**2 + \
                              (s.posY - main_light_pos[1])**2 + \
                              (s.posZ - main_light_pos[2])**2
                    if dist_sq < 100.0: # Distance < 10
                        current_star_speed *= 0.3 # Slow down significantly
                
                # 2. Check Streetlights
                for sl in allstreetlights:
                    # Streetlight bulb is at (sl.posX, sl.height, sl.posZ)
                    sl_y = sl.height
                    dist_sq = (s.posX - sl.posX)**2 + \
                              (s.posY - sl_y)**2 + \
                              (s.posZ - sl.posZ)**2
                    
                    if dist_sq < 36.0: # Distance < 6 (Close to the pole)
                        current_star_speed *= 0.3
                        break # Found one, no need to check others

                # 3. Check Jeep Headlights
                if jeepObj.lightOn:
                    intensity = calculateSpotlightIntensity(s.posX, s.posY, s.posZ, jeepObj)
                    if intensity > 0:
                        # Slow down based on intensity (Higher intensity = Slower speed)
                        # At max intensity (1.0), speed is reduced by 80%
                        current_star_speed *= (1.0 - 0.8 * intensity)

                # Move the star
                moveAmount = current_star_speed * seconds_passed
                s.posX += moveAmount * s.direction
                
                # Bounce off walls
                if s.posX > land - 5:
                    s.posX = land - 5
                    s.direction = -1
                elif s.posX < -land + 5:
                    s.posX = -land + 5
                    s.direction = 1

                # Collision Check (Player vs Small Star)
                if s.posY > 0: 
                    if dist((jeepObj.posX, jeepObj.posZ), (s.posX, s.posZ)) < (jeepObj.sizeX + 1.0):
                        
                        # 1. Visual Effects
                        last_star_x = s.posX
                        last_star_z = s.posZ
                        s.posY = -100.0 # Hide the star
                        stars_collected += 1
                        star_effect_timer = 0.4

                        # 2. CHECK TRIGGER FOR BOSS (10/10)
                        if stars_collected >= 10: #TESTING USE, should be 10
                            boss_battle_active = True
                            
                            # Clear small stars
                            for star_obj in allstars: star_obj.posY = -100.0
                            
                            # Summon Giant Star
                            villainStar.posX = 0.0
                            villainStar.posZ = jeepObj.posZ + 50.0
                            
                            villainStar.posY = 3.6
                            
                            villainStar.sizeX = 4.0 
                            villainStar.sizeY = 4.0
                            villainStar.sizeZ = 4.0
                            
                            print("BOSS SUMMONED!")

            # Animation for wheels
            if jeepObj.wheelDir == 'fwd':
                jeepObj.rotateWheel(-0.1 * tickTime)
            elif jeepObj.wheelDir == 'back':
                jeepObj.rotateWheel(0.1 * tickTime)

        # --- 2. BOSS BATTLE LOGIC ---
        else:
            # --- BOSS ATTACK LOGIC ---
            global boss_attack_timer
            boss_attack_timer -= seconds_passed
            if boss_attack_timer <= 0:
                boss_attack_timer = 2.0 # Attack every 2 seconds
                
                # Determine number of attacks (30% chance for double attack)
                num_attacks = 1
                if random.random() < 0.3:
                    num_attacks = 2
                    print("Boss Double Attack Triggered!")
                
                for _ in range(num_attacks):
                    attack_type = random.choice(['direct', 'spread', 'big_star'])
                    
                    if attack_type == 'direct':
                        # Calculate vector to jeep
                        dx = jeepObj.posX - villainStar.posX
                        dz = jeepObj.posZ - villainStar.posZ
                        dist_val = math.sqrt(dx*dx + dz*dz)
                        speed = 15.0
                        if dist_val > 0:
                            vx = (dx / dist_val) * speed
                            vz = (dz / dist_val) * speed
                            projectiles.append(Projectile(villainStar.posX, villainStar.posY, villainStar.posZ, vx, vz, "direct"))
                            print("Boss Attack: Direct Shot!")
                    
                    elif attack_type == 'spread':
                        # Shoot 3 stars
                        dx = jeepObj.posX - villainStar.posX
                        dz = jeepObj.posZ - villainStar.posZ
                        angle_to_player = math.atan2(dx, dz) 
                        
                        speed = 12.0
                        offsets = [-0.3, 0.0, 0.3] # Radians
                        
                        for offset in offsets:
                            angle = angle_to_player + offset
                            vx = math.sin(angle) * speed
                            vz = math.cos(angle) * speed
                            projectiles.append(Projectile(villainStar.posX, villainStar.posY, villainStar.posZ, vx, vz, "spread"))
                        print("Boss Attack: Spread Shot!")

                    elif attack_type == 'big_star':
                        # Shoot 1 BIG star
                        dx = jeepObj.posX - villainStar.posX
                        dz = jeepObj.posZ - villainStar.posZ
                        dist_val = math.sqrt(dx*dx + dz*dz)
                        speed = 10.0 # Slower but bigger
                        if dist_val > 0:
                            vx = (dx / dist_val) * speed
                            vz = (dz / dist_val) * speed
                            projectiles.append(Projectile(villainStar.posX, villainStar.posY, villainStar.posZ, vx, vz, "big_star"))
                        print("Boss Attack: BIG STAR!")

            # Update Projectiles
            new_blocked_vector = None
            for p in projectiles[:]:
                p.posX += p.velX * seconds_passed
                p.posZ += p.velZ * seconds_passed
                p.rotation += 300 * seconds_passed
                p.life -= seconds_passed
                
                if p.life <= 0:
                    projectiles.remove(p)
                    continue
                
                # Collision with Jeep
                hit_radius = 2.5
                if p.p_type == "big_star":
                    hit_radius = 3.5 # Larger hit radius for big star

                if dist((jeepObj.posX, jeepObj.posZ), (p.posX, p.posZ)) < hit_radius: 
                    # Continuous Push Effect
                    # Instead of removing the projectile, we push the player along with it
                    
                    # 1. Calculate potential new X position
                    next_posX = jeepObj.posX + p.velX * seconds_passed
                    
                    # Match safe_limit with isColliding() logic: land - (2.0 * sizeX)
                    # We subtract a small buffer (0.2) to ensure we are strictly inside
                    safe_limit = land - (2.0 * jeepObj.sizeX) - 0.2
                    
                    # 2. Check if this push would send the jeep out of bounds
                    if next_posX > safe_limit:
                        # The player is being pinned against the wall.
                        # Destroy the projectile and clamp position with buffer
                        jeepObj.posX = safe_limit
                        projectiles.remove(p)
                        continue # Stop processing this projectile
                    elif next_posX < -safe_limit:
                        jeepObj.posX = -safe_limit
                        projectiles.remove(p)
                        continue

                    # 3. Apply velocity to player (Push them)
                    jeepObj.posX = next_posX
                    jeepObj.posZ += p.velZ * seconds_passed
                    
                    # 4. Set blocked vector
                    new_blocked_vector = (p.posX - jeepObj.posX, p.posZ - jeepObj.posZ)
            
            jeep_blocked_vector = new_blocked_vector

            # Rotate the boss to look menacing
            villainStar.rotation += 100 * seconds_passed
            
            # --- BOSS MOVEMENT ---
            # 1. Calculate Speed (React to Light)
            boss_speed = 4.0 # Base speed (slower than jeep's normal speed)
            
            # Check Main Light
            main_light_pos = None
            if lightMode == 1: main_light_pos = (0.0, 6.0, 0.0)
            elif lightMode == 3: main_light_pos = (0.0, 8.0, 0.0)
            
            if main_light_pos:
                dist_sq = (villainStar.posX - main_light_pos[0])**2 + \
                          (villainStar.posY - main_light_pos[1])**2 + \
                          (villainStar.posZ - main_light_pos[2])**2
                if dist_sq < 100.0: boss_speed *= 0.2 # Slow down A LOT
            
            # Check Streetlights
            for sl in allstreetlights:
                sl_y = sl.height
                dist_sq = (villainStar.posX - sl.posX)**2 + \
                          (villainStar.posY - sl_y)**2 + \
                          (villainStar.posZ - sl.posZ)**2
                if dist_sq < 36.0: 
                    boss_speed *= 0.2
                    break

            # Check Jeep Headlights
            if jeepObj.lightOn:
                intensity = calculateSpotlightIntensity(villainStar.posX, villainStar.posY, villainStar.posZ, jeepObj)
                if intensity > 0:
                    boss_speed *= (1.0 - 0.8 * intensity)

            # 2. Move Forward
            villainStar.posZ += boss_speed * seconds_passed
            
            # 3. Move Left/Right (Sine Wave)
            # Use rotation as a time proxy since it increments steadily
            # Amplitude = 10, Frequency = based on rotation speed
            villainStar.posX = 10.0 * math.sin(villainStar.rotation * 0.02)

            # Allow player to drive towards boss
            if jeepObj.wheelDir == 'fwd':
                jeepObj.rotateWheel(-0.1 * tickTime)
            
            # Check Collision
            if dist((jeepObj.posX, jeepObj.posZ), (villainStar.posX, villainStar.posZ)) < (villainStar.sizeX + 2.0):
                 # 1. Turn off the battle flag IMMEDIATELY so this doesn't run again
                 boss_battle_active = False
                 
                 # 2. Stop the game logic
                 canStart = False 
                 currentMode = -1 # Optional: Switch to a "Safe" mode
                 
                 # 3. Trigger Win Screen ONCE
                 gameSuccess()

    elif currentMode == MODE_DISPLAY:
        # Display Mode Logic (Unchanged)
        moveAmount = moveSpeed * seconds_passed
        rotAmount = rotSpeed * seconds_passed
        
        if keyState['up']:
            jeepObj.move(False, moveAmount)
            jeepObj.wheelDir = 'fwd'
        elif keyState['down']:
            jeepObj.move(False, -moveAmount)
            jeepObj.wheelDir = 'back'
        else:
            jeepObj.wheelDir = 'stop'

        if keyState['left']:
            jeepObj.move(True, rotAmount)
        elif keyState['right']:
            jeepObj.move(True, -rotAmount)
            
        if jeepObj.wheelDir == 'fwd':
            jeepObj.rotateWheel(-0.1 * tickTime)
        elif jeepObj.wheelDir == 'back':
            jeepObj.rotateWheel(0.1 * tickTime)
    
    glutPostRedisplay() 

#---------------------------------setting camera----------------------------
def setView():
    global eyeX, eyeY, eyeZ, windowWidth, windowHeight, currentMode, introTime, jeepObj, victoryTimer
    global victoryX, victoryZ
    
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()

    if windowHeight == 0: windowHeight = 1
    aspect = float(windowWidth) / float(windowHeight)
    gluPerspective(90, aspect, 0.1, 1000.0)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    # --- CINEMATIC CAMERA (INTRO MODE) ---
    if currentMode == MODE_INTRO:
        if introTime < 5.0:
             gluLookAt(jeepObj.posX, jeepObj.posY + 4.0, jeepObj.posZ - 8.0,
                       jeepObj.posX, jeepObj.posY, jeepObj.posZ + 10.0, 0.0, 1.0, 0.0)
        elif introTime < 10.0:
             starZ = jeepObj.posZ + 15.0
             gluLookAt(0.0, 6.0, starZ + 10.0, jeepObj.posX, jeepObj.posY, jeepObj.posZ, 0.0, 1.0, 0.0)
        elif introTime < 15.0:
             gluLookAt(0.0, 35.0, jeepObj.posZ + 5.0, 0.0, 0.0, jeepObj.posZ + 5.0, 0.0, 0.0, -1.0)
        else:
             gluLookAt(0.0, 0.5, jeepObj.posZ - 2.0, 0.0, 25.0, jeepObj.posZ + 60.0, 0.0, 1.0, 0.0)

    # --- VICTORY CAMERA (ORBIT) ---
    elif currentMode == MODE_VICTORY:
        # Increased Radius to 22.0 to fix "Too Close" issue
        orbit_radius = 22.0 
        orbit_speed = 0.5
        
        # Center point is the victory location
        center_x = victoryX 
        center_z = victoryZ
        
        # Calculate Rotating Eye Position
        camX = center_x + math.cos(victoryTimer * orbit_speed) * orbit_radius
        camZ = center_z + math.sin(victoryTimer * orbit_speed) * orbit_radius
        camY = 6.0 # Look from slightly higher up
        
        gluLookAt(camX, camY, camZ,
                  center_x, 2.0, center_z,
                  0.0, 1.0, 0.0)

    # --- GAMEPLAY CAMERA ---
    else:
        if topView:
            gluLookAt(jeepObj.posX, max(1.0, radius), jeepObj.posZ, jeepObj.posX, jeepObj.posY, jeepObj.posZ, 0.0, 0.0, 1.0)
        elif behindView:
            rad_angle = math.radians(jeepObj.rotation)
            eye_x = jeepObj.posX - max(1.0, radius * 0.8) * math.sin(rad_angle)
            eye_y = jeepObj.posY + max(0.5, radius * 0.4)
            eye_z = jeepObj.posZ - max(1.0, radius * 0.8) * math.cos(rad_angle)
            gluLookAt(eye_x, eye_y, eye_z, jeepObj.posX, jeepObj.posY, jeepObj.posZ, 0.0, 1.0, 0.0)
        else:
            gluLookAt(eyeX, eyeY, eyeZ, jeepObj.posX, jeepObj.posY, jeepObj.posZ, 0.0, 1.0, 0.0)

def setObjView():
    pass

#-------------------------------------------user inputs------------------
def mouseHandle(button, state, x, y):
    global midDown, nowX, nowY
    if (button == GLUT_MIDDLE_BUTTON and state == GLUT_DOWN):
        midDown = True
        nowX = x
        nowY = y
        print ('pushed')
    else:
        midDown = False    
        
def motionHandle(x,y):
    global nowX, nowY, angle, eyeX, eyeY, eyeZ, phi
    if (midDown == True):
        pastX = nowX
        pastY = nowY 
        nowX = x
        nowY = y

        angle -= (nowX - pastX) * mouseSensitivity
        phi += (nowY - pastY) * mouseSensitivity

        if (phi > math.pi / 2.0 - 0.01):
            phi = math.pi / 2.0 - 0.01
        if (phi < -math.pi / 2.0 + 0.01):
            phi = -math.pi / 2.0 + 0.01

        recalculateEyePos() 

    if centered == False:
        setView()
    elif centered == True:
        setObjView()


def specialKeys(keypress, mX, mY):
    global keyState
    if keypress == GLUT_KEY_UP:
        keyState['up'] = True
    elif keypress == GLUT_KEY_DOWN:
        keyState['down'] = True
    elif keypress == GLUT_KEY_LEFT:
        keyState['left'] = True
    elif keypress == GLUT_KEY_RIGHT:
        keyState['right'] = True

def specialKeysUp(keypress, mX, mY):
    global keyState
    if keypress == GLUT_KEY_UP:
        keyState['up'] = False
    elif keypress == GLUT_KEY_DOWN:
        keyState['down'] = False
    elif keypress == GLUT_KEY_LEFT:
        keyState['left'] = False
    elif keypress == GLUT_KEY_RIGHT:
        keyState['right'] = False

def myKeyboard(key, mX, mY):
    global eyeX, eyeY, eyeZ, angle, radius, helpWindow, centered, helpWin, overReason, topView, behindView, phi, jeepObj
    global currentMode, gameOverTimer, victoryTimer

    if key == b'h':
        winNum = glutGetWindow()
        if helpWindow == False:
            helpWindow = True
            glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA | GLUT_DEPTH)
            glutInitWindowSize(500,300)
            glutInitWindowPosition(600,0)
            helpWin = glutCreateWindow(b'Help Guide')
            glutDisplayFunc(showHelp)
            glutKeyboardFunc(myKeyboard)
            glutMainLoop()
        elif helpWindow == True and winNum!=1:
            helpWindow = False
            print (glutGetWindow())
            glutHideWindow()
            glutMainLoop()

    elif key == b'+' or key == b'=':
        jeepObj.sizeX += 0.1
        jeepObj.sizeY += 0.1
        jeepObj.sizeZ += 0.1
    elif key == b'-' or key == b'_':
        if jeepObj.sizeX > 0.2: 
            jeepObj.sizeX -= 0.1
            jeepObj.sizeY -= 0.1
            jeepObj.sizeZ -= 0.1

    elif key == b'z': 
        radius -= 0.5
        if radius < 1.0: radius = 1.0 
        recalculateEyePos()
    elif key == b'x': 
        radius += 0.5
        recalculateEyePos()
    
    elif key == b't': 
        topView = not topView
        behindView = False
    elif key == b'b': 
        behindView = not behindView
        topView = False
    elif key == b'c': 
        behindView = False
        topView = False
        eyeX = 0.0
        eyeY = 2.0
        eyeZ = 10.0
        angle = 0.0
        radius = 10.0
        phi = 0.0
        recalculateEyePos()

    elif key == b'l': 
        if currentMode != MODE_VICTORY:
            jeepObj.toggleLight()

    elif key == b'r':
        if (currentMode == MODE_GAME_OVER and gameOverTimer > 1.0) or \
           (currentMode == MODE_VICTORY and victoryTimer > 1.0):
            resetGame()

    elif key == b' ': 
        if currentMode == MODE_INTRO:
            startGameplay() # Skip intro
        else:
            jeepObj.wheelDir = 'stop' 

    setView()

def menuFunc(value):
    global lightMode, isFullScreen, windowWidth, windowHeight
    global prevWidth, prevHeight, prevPosX, prevPosY

    if 0 <= value <= 4: 
        print(f"Lighting mode set to: {value}")
        lightMode = value
    
    elif value == 101: 
        if not isFullScreen:
            glutReshapeWindow(600, 600)
    
    elif value == 102: 
        if not isFullScreen:
            glutReshapeWindow(800, 800)

    elif value == 103: 
        if not isFullScreen:
            glutReshapeWindow(1024, 768)

    elif value == 200:
        if not isFullScreen:
            prevWidth = windowWidth
            prevHeight = windowHeight
            prevPosX = glutGet(GLUT_WINDOW_X)
            prevPosY = glutGet(GLUT_WINDOW_Y)
            glutFullScreen()
            isFullScreen = True
        else:
            glutReshapeWindow(prevWidth, prevHeight)
            glutPositionWindow(prevPosX, prevPosY)
            isFullScreen = False

    glutPostRedisplay()
    return 0

#-------------------------------------------------tools----------------------       
def drawTextBitmap(string, x, y): 
    glRasterPos2f(x, y)
    for char in string:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))

def text3d(string, x, y, z):
    glRasterPos3f(x,y,z)
    for char in string:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(char))

def dist(pt1, pt2):
    a = pt1[0]
    b = pt1[1]
    x = pt2[0]
    y = pt2[1]
    return math.sqrt((a-x)**2 + (b-y)**2)

def recalculateEyePos():
    global eyeX, eyeY, eyeZ, radius, angle, phi
    offsetX = radius * math.cos(phi) * math.sin(angle)
    offsetY = radius * math.sin(phi)
    offsetZ = radius * math.cos(phi) * math.cos(angle)
    eyeX = jeepObj.posX + offsetX
    eyeY = jeepObj.posY + offsetY
    eyeZ = jeepObj.posZ + offsetZ

def reshape(w, h):
    global windowWidth, windowHeight
    windowWidth = w
    windowHeight = h
    glViewport(0, 0, w, h)
    setView()

def startGameplay():
    global currentMode, jeepObj, canStart, gameStartTime, stars_collected
    global stars_collected, boss_battle_active

    currentMode = MODE_GAME
    
    jeepObj.posX = 0.0
    jeepObj.posZ = 0.0
    
    canStart = True 
    stars_collected = 0
    boss_battle_active = False
    
    for s in allstars:
        s.posY = 2.0

    gameStartTime = glutGet(GLUT_ELAPSED_TIME) / 1000.0
    print("Game Started!")

#--------------------------------------------making game more complex--------
def addCone(x,z):
    allcones.append(cone.cone(x,z))
    obstacleCoord.append((x,z))

def addStar(x,z):
    new_star = star.star(x,z)
    new_star.posY = 2.0 
    new_star.speed = random.uniform(3.0, 7.0) 
    new_star.direction = random.choice([1, -1])
    allstars.append(new_star)
    rewardCoord.append((x,z))

def collisionCheck():
    global overReason, score, usedDiamond, countTime
    if currentMode != MODE_GAME: return 

    for obstacle in obstacleCoord:
        if dist((jeepObj.posX, jeepObj.posZ), obstacle) <= ckSense:
            overReason = "You hit an obstacle!"
            gameOver()
    if (jeepObj.posX >= land or jeepObj.posX <= -land):
        overReason = "You ran off the road!"
        gameOver()

    # Removed fixed finish line for infinite road
    # if (jeepObj.posZ >= land*gameEnlarge):
    #    gameSuccess()
        
#----------------------------------multiplayer dev (using tracker)-----------
def recordGame():
    with open('results.csv', 'wt') as csvfile:
        spamwriter = csv.writer(csvfile, delimiter=',',quotechar='|', quoting=csv.QUOTE_MINIMAL)
        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        print(st)
        spamwriter.writerow([st] + [finalScore])
    
#-------------------------------------developing additional windows/options----
def resetGame():
    global currentMode, jeepObj, jeep2Obj, canStart, score, stars_collected
    global boss_battle_active, villainStar, projectiles, introTime, timeLeft
    global overWin, mainWin, gameStartTime, allstars, allcones, obstacleCoord
    global jeep_blocked_vector, allstreetlights
    
    # Reset Mode
    currentMode = MODE_INTRO
    introTime = 0.0
    canStart = False
    boss_battle_active = False
    score = 0
    stars_collected = 0
    timeLeft = GAME_DURATION
    jeep_blocked_vector = None
    
    # Reset Objects
    jeepObj.posX = 0.0
    jeepObj.posZ = 0.0
    jeepObj.rotation = 0.0
    jeepObj.wheelDir = 'stop'
    jeepObj.lightOn = False
    
    jeep2Obj.posX = 3.0
    jeep2Obj.posZ = 0.0
    jeep2Obj.rotation = 0.0
    jeep2Obj.wheelDir = 'stop'
    
    villainStar.posY = 20.0 # Reset boss position
    villainStar.posX = 0.0
    villainStar.posZ = 0.0 # Will be set in intro
    villainStar.rotation = 0.0
    
    projectiles = []
    
    # Reset Stars
    for s in allstars:
        s.posY = 2.0
        s.posX = random.uniform(-land + 5, land - 5)
        s.posZ = random.randint(10, int(land*gameEnlarge))

    # Reset Cones
    obstacleCoord[:] = []
    for c in allcones:
        c.posX = random.uniform(-land + 2, land - 2)
        c.posZ = random.randint(10, int(land*gameEnlarge))
        obstacleCoord.append((c.posX, c.posZ))

    # Reset Streetlights (Fix for missing lights on restart)
    allstreetlights[:] = []
    setupStreetLights()

    # Handle Windows
    if overWin != 0:
        glutDestroyWindow(overWin)
        overWin = 0
        glutSetWindow(mainWin)
        glutShowWindow()
    
    gameStartTime = glutGet(GLUT_ELAPSED_TIME) / 1000.0
    print("Game Reset!")

def gameOver():
    global finalScore, currentMode, gameOverTimer
    print ("Game completed!")
    finalScore = score-6
    currentMode = MODE_GAME_OVER
    gameOverTimer = 0.0
    
def gameSuccess():
    global currentMode, victoryTimer, jeepObj, jeep2Obj, villainStar, boss_battle_active
    global finalTimeStr, timeLeft, GAME_DURATION
    global victoryX, victoryZ
    
       
    print("Game success! Starting Victory Sequence...")
    
    # 1. Calculate Final Time String (Capture it NOW before it resets)
    time_used = GAME_DURATION - timeLeft
    mins = int(time_used // 60)
    secs = int(time_used % 60)
    finalTimeStr = "Time used: {:02d}:{:02d}".format(mins, secs)
    
    # 2. Switch Mode
    currentMode = MODE_VICTORY
    victoryTimer = 0.0
    boss_battle_active = False
    
    # 3. Hide the Boss
    villainStar.posY = -100.0
    
    # 4. Position Jeeps at the Victory Location (Where the boss was beaten)
    # Capture the location where the event happened
    victoryX = jeepObj.posX
    victoryZ = jeepObj.posZ
    
    # Place them side-by-side at this location
    jeepObj.posX = victoryX - 3.5
    jeepObj.posZ = victoryZ
    jeepObj.posY = 2.0
    
    jeep2Obj.posX = victoryX + 3.5
    jeep2Obj.posZ = victoryZ
    jeep2Obj.posY = 2.0
    
    # 5. Stop wheels and orient forward
    jeepObj.wheelDir = 'stop'
    jeep2Obj.wheelDir = 'stop'
    jeepObj.rotation = 0
    jeep2Obj.rotation = 0
    
    # 6. Turn off headlights
    jeepObj.lightOn = False

def winScreen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glColor3f(0.0,1.0,0.0)
    drawTextBitmap("Completed Trial!" , -0.6, 0.85)
    glColor3f(0.0,1.0,0.0)
    drawTextBitmap("Your score is: ", -1.0, 0.0)
    glColor3f(1.0,1.0,1.0)
    drawTextBitmap(str(finalScore), -1.0, -0.15)
    glutSwapBuffers()


def overScreen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glColor3f(1.0,0.0,1.0)
    drawTextBitmap("Incomplete Trial" , -0.6, 0.85)
    glColor3f(0.0,1.0,0.0)
    drawTextBitmap("Because you..." , -1.0, 0.5)
    glColor3f(1.0,1.0,1.0)
    drawTextBitmap(overReason, -1.0, 0.35)
    glColor3f(0.0,1.0,0.0)
    drawTextBitmap("Your score stopped at: ", -1.0, 0.0)
    glColor3f(1.0,1.0,1.0)
    drawTextBitmap(str(finalScore), -1.0, -0.15)
    
    glColor3f(1.0, 1.0, 0.0)
    drawTextBitmap("Press 'r' to Restart", -1.0, -0.4)
    
    glutSwapBuffers()

def showHelp():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    
    glColor3f(1.0, 0.0, 0.0)
    drawTextBitmap("Help Guide" , -0.2, 0.85)
    
    glColor3f(0.0, 1.0, 0.0)
    drawTextBitmap("Jeep Controls:", -0.9, 0.7) 
    glColor3f(1.0, 1.0, 1.0)
    drawTextBitmap("Up/Down Arrows: Move Forward / Backward", -0.8, 0.6)
    drawTextBitmap("Left/Right Arrows: Turn Jeep Left / Right", -0.8, 0.5)
    drawTextBitmap("Spacebar: Stop wheel rotation (Brake)", -0.8, 0.4)
    drawTextBitmap("'+' / '-': Increase / Decrease Jeep Size", -0.8, 0.3)
    drawTextBitmap("'l': Toggle Headlights", -0.8, 0.2) 

    glColor3f(0.0, 1.0, 0.0)
    drawTextBitmap("Camera Controls:", -0.9, 0.0) 
    glColor3f(1.0, 1.0, 1.0)
    drawTextBitmap("Middle Mouse + Drag: Orbit Camera", -0.8, -0.1)
    drawTextBitmap("'z' / 'x': Zoom In / Zoom Out", -0.8, -0.2)
    drawTextBitmap("'t': Toggle Top-Down View", -0.8, -0.3)
    drawTextBitmap("'b': Toggle Behind-Jeep View", -0.8, -0.4)
    drawTextBitmap("'c': Reset Camera to Default (orbits jeep)", -0.8, -0.5) 

    glColor3f(0.0, 1.0, 0.0)
    drawTextBitmap("Other:", -0.9, -0.7)
    glColor3f(1.0, 1.0, 1.0)
    drawTextBitmap("'h': Close this Help Window", -0.8, -0.8)
    drawTextBitmap("Right Mouse Click: Open Main Menu", -0.8, -0.9) 

    glutSwapBuffers()

#----------------------------------------------texture development-----------
def loadTexture(imageName):
    texturedImage = Image.open(imageName)
    try:
        imgX = texturedImage.size[0]
        imgY = texturedImage.size[1]
        img = texturedImage.tobytes("raw","RGBX",0,-1)
    except Exception:
        print ("Error:")
        print ("Switching to RGBA mode.")
        imgX = texturedImage.size[0]
        imgY = texturedImage.size[1]
        img = texturedImage.tobytes("raw","RGB",0,-1)

    tempID = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tempID)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_MIRRORED_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_MIRRORED_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
    glTexImage2D(GL_TEXTURE_2D, 0, 3, imgX, imgY, 0, GL_RGBA, GL_UNSIGNED_BYTE, img)
    return tempID

def loadSceneTextures():
    global roadTextureID
    roadTextureID = loadTexture("img/road2.png")

def setupStreetLights():
    # We have GL_LIGHT2 through GL_LIGHT7 available (6 lights)
    available_lights = [GL_LIGHT2, GL_LIGHT3, GL_LIGHT4, GL_LIGHT5, GL_LIGHT6, GL_LIGHT7]
    light_idx = 0
    
    for z_pos in range(0, int(land * gameEnlarge), 40): 
        
        sl_left = streetlight.StreetLight(-land + 2, z_pos, None)
        allstreetlights.append(sl_left)

        sl_right = streetlight.StreetLight(land - 2, z_pos, None)
        allstreetlights.append(sl_right)
    
#-----------------------------------------------lighting work--------------
def initializeLight():
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_NORMALIZE)               
    glClearColor(0.1, 0.1, 0.1, 0.0)

#~~~~~~~~~~~~~~~~~~~~~~~~~the finale!!!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def show_launcher():
    global windowWidth, windowHeight, isFullScreen, currentMode

    def start_game():
        global windowWidth, windowHeight, isFullScreen, currentMode, lightMode, behindView
        
        res_selection = resolution_var.get()
        if res_selection == "Start in Fullscreen":
            isFullScreen = True
            windowWidth = 800  
            windowHeight = 600 
        else:
            isFullScreen = False
            w, h = res_selection.split('x')
            windowWidth = int(w)
            windowHeight = int(h)

        mode_selection = mode_var.get()
        if mode_selection == "Display Mode (Lighting Test)":
            currentMode = MODE_DISPLAY
            lightMode = 0
            behindView = False
            print("Starting in Display Mode")
        else:
            currentMode = MODE_INTRO 
            lightMode = 4
            behindView = True
            
            jeep2Obj.posX = 3.0
            jeep2Obj.posZ = 0.0

            print("Starting Intro Sequence...")
        
        root.destroy()

    root = tk.Tk()
    root.title("Game Launcher")

    frame = ttk.Frame(root, padding="20")
    frame.grid(row=0, column=0)
    
    ttk.Label(frame, text="Select Game Mode:", font=('Helvetica', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0,5))
    mode_var = tk.StringVar(value="Game Mode (Racing)")
    
    modes = ["Game Mode (Racing)", "Display Mode (Lighting Test)"]
    for i, m in enumerate(modes):
        ttk.Radiobutton(frame, text=m, variable=mode_var, value=m).grid(row=i+1, column=0, sticky=tk.W, padx=20)

    ttk.Separator(frame, orient='horizontal').grid(row=3, column=0, sticky="ew", pady=10)

    ttk.Label(frame, text="Select Resolution:", font=('Helvetica', 10, 'bold')).grid(row=4, column=0, sticky=tk.W, pady=(0,5))
    resolution_var = tk.StringVar(value="800x800") 
    
    display_options = ["600x600", "800x800", "1024x768", "Start in Fullscreen"]
    for i, option in enumerate(display_options):
        ttk.Radiobutton(frame, text=option, variable=resolution_var, value=option).grid(row=5+i, column=0, sticky=tk.W, padx=20)

    ttk.Button(frame, text="Start Application", command=start_game).grid(row=10, column=0, pady=20)

    root.eval('tk::PlaceWindow . center')
    root.mainloop()

def main():
    show_launcher()

    glutInit()

    global prevTime, mainWin
    prevTime = glutGet(GLUT_ELAPSED_TIME)
    
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA | GLUT_DEPTH)
    glutInitWindowSize(windowWidth, windowHeight)
    glutInitWindowPosition(0, 0)
    mainWin = glutCreateWindow(b'CS4182')

    if isFullScreen:
        global prevWidth, prevHeight, prevPosX, prevPosY
        prevWidth = windowWidth
        prevHeight = windowHeight
        prevPosX = glutGet(GLUT_WINDOW_X)
        prevPosY = glutGet(GLUT_WINDOW_Y)
        glutFullScreen()

    glutDisplayFunc(display)
    glutIdleFunc(idle)

    setView()
    glLoadIdentity()
    glEnable(GL_DEPTH_TEST)   

    glutMouseFunc(mouseHandle)
    glutMotionFunc(motionHandle)
    glutSpecialFunc(specialKeys)
    glutSpecialUpFunc(specialKeysUp)
    glutKeyboardFunc(myKeyboard)
    glutReshapeFunc(reshape)

    lightMenu = glutCreateMenu(menuFunc)
    glutAddMenuEntry("Ambient Light", 0)
    glutAddMenuEntry("Point Light", 1)
    glutAddMenuEntry("Directional Light", 2)
    glutAddMenuEntry("Spotlight", 3)
    glutAddMenuEntry("Default (Dark)", 4)

    resMenu = glutCreateMenu(menuFunc)
    glutAddMenuEntry("600 x 600", 101)
    glutAddMenuEntry("800 x 800", 102)
    glutAddMenuEntry("1024 x 768", 103)

    glutCreateMenu(menuFunc)
    glutAddSubMenu("Lighting", lightMenu)
    glutAddSubMenu("Resolution", resMenu)
    glutAddMenuEntry("Toggle Fullscreen", 200)

    glutAttachMenu(GLUT_RIGHT_BUTTON)

    loadSceneTextures()

    initShaders()

    jeep1Obj.makeDisplayLists()
    jeep2Obj.makeDisplayLists()
    jeep3Obj.makeDisplayLists()
    
    tunnelObj.makeDisplayLists()

    setupStreetLights()

    for i in range(coneAmount):
        addCone(random.randint(-land, land), random.randint(10.0, land*gameEnlarge))

    addStar(-land + 5, 10) 
    for i in range(starAmount):
        addStar(random.randint(-land, land), random.randint(10.0, land*gameEnlarge))

    for cone in allcones:
        cone.makeDisplayLists()

    villainStar.makeDisplayLists()

    for s in minionStars:
        s.makeDisplayLists()

    for star in allstars:
        star.makeDisplayLists()
    
    staticObjects()
    
    # Ensure projectile model is loaded
    if projectileModel:
        projectileModel.makeDisplayLists()
        
    if (applyLighting == True):
        initializeLight()
    glutMainLoop()
    
main()

