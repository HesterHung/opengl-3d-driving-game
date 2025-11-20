#!/usr/bin/env python
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math, time, random, csv, datetime
import ImportObject
import PIL.Image as Image
import jeep, cone, star, ribbon, NurbsLoader, streetlight, sky
import tkinter as tk            
from tkinter import ttk          

# --- Mode Constants ---
MODE_GAME = 0
MODE_DISPLAY = 1
MODE_INTRO = 2
currentMode = MODE_GAME # Default

# --- Intro Story Variables ---
introTime = 0.0
villainStar = star.star(0, 50) # Spawn it further down the road
villainStar.sizeX = 3.0 # Make it a BIG boss star
villainStar.sizeY = 3.0
villainStar.sizeZ = 3.0
villainStar.posY = 20.0 # Start high in the air

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
mainWin = 0
centered = False

gameStartTime = 0.0
GAME_DURATION = 120.0
beginTime = 0
countTime = 0
score = 0
finalScore = 0
canStart = False
overReason = ""

stars_collected = 0
STARS_TO_WIN = 10

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
mouseSensitivity = 0.04

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

ribbonObj = ribbon.ribbon(z_pos=50.0, length=5.0, width=land)

tunnelObj = NurbsLoader.NurbsModel(
    0.0, 0.0, 100.0, 
    "../nurbs/tunnel.txt", 
    scale=(2.5, 3.5, 2.5), 
    color=(0.4, 0.4, 0.4)
)

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
        
        if lightMode == 0:
            glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_DECAL)
        else:
            glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)
            glColor3f(1.0, 1.0, 1.0)
            glMaterialfv(GL_FRONT, GL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
            glMaterialfv(GL_FRONT, GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])

        glBindTexture(GL_TEXTURE_2D, roadTextureID)

        L = self.landLength
        C = self.cont
        
        minX = -L
        maxX = L
        totalWidth = maxX - minX

        minZ = -L
        maxZ = C * L
        totalLength = maxZ - minZ

        startZ = minZ
        endZ = maxZ
        startX = minX
        endX = maxX
        
        step = 2.0

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

                v1 = (maxZ - z1) / totalLength
                v2 = (maxZ - z2) / totalLength

                glTexCoord2f(u1, v1); glVertex3f(x1, 0, z1)
                glTexCoord2f(u1, v2); glVertex3f(x1, 0, z2)
                glTexCoord2f(u2, v2); glVertex3f(x2, 0, z2)
                glTexCoord2f(u2, v1); glVertex3f(x2, 0, z1)
                
                x += step
            z += step
        glEnd()

        glDisable(GL_TEXTURE_2D)

#--------------------------------------populating scene----------------
def staticObjects():
    global objectArray
    objectArray.append(Scene())
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

def display():
    global jeepObj, canStart, score, beginTime, countTime, lightMode
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    setView()

    glEnable(GL_NORMALIZE)

    # --- 1. GLOBAL LIGHTING SETUP ---
    if lightMode == 0:  # Ambient/Flat
        glDisable(GL_LIGHTING)
        glDisable(GL_LIGHT0)
    else:
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0) 

        current_light_color = light0_Intensity 
        light_pos = [0.0, 10.0, 5.0, 1.0]

        if lightMode == 4:
            # Moon Mode
            glLightModelfv(GL_LIGHT_MODEL_AMBIENT, [0.05, 0.05, 0.05, 1.0])
            moon_color = [0.15, 0.15, 0.25, 1.0] 
            current_light_color = moon_color
            light_pos = [0.0, 10.0, 5.0, 0.0] 

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
                if lightMode == 2: light_pos = [0.0, 1.0, 1.0, 0.0]
                elif lightMode == 3: 
                    light_pos = [0.0, 10.0, 0.0, 1.0]
                    glLightfv(GL_LIGHT0, GL_SPOT_DIRECTION, [0.0, -1.0, 0.0])
                    glLightf(GL_LIGHT0, GL_SPOT_CUTOFF, 45.0)

        glLightfv(GL_LIGHT0, GL_POSITION, light_pos)
        glLightfv(GL_LIGHT0, GL_DIFFUSE, current_light_color)
        glLightfv(GL_LIGHT0, GL_SPECULAR, current_light_color)

    skyObj.draw()

    # --- 2. DRAW BASED ON MODE ---
    if currentMode == MODE_INTRO:
        # === INTRO MODE RENDER ===
        # Draw Scene (Road, Sky, Tunnel)
        for obj in objectArray: 
            obj.draw()
            
        glDisable(GL_LIGHTING) 
        ribbonObj.draw() 
        if lightMode != 0: glEnable(GL_LIGHTING)
        
        tunnelObj.draw()

        # --- NEW: STREETLIGHTS ADDED BACK ---
        # 1. Calculate distance to current Jeep position
        light_distances = []
        for sl in allstreetlights:
            dist = abs(sl.posZ - jeepObj.posZ)
            light_distances.append((dist, sl))

        # 2. Sort so closest lights get priority
        light_distances.sort(key=lambda x: x[0])
        available_ids = [GL_LIGHT2, GL_LIGHT3, GL_LIGHT4, GL_LIGHT5, GL_LIGHT6, GL_LIGHT7]

        # 3. Reset hardware lights to prevent ghosts
        for i in available_ids: glDisable(i)

        # 4. Assign IDs and Draw
        for i, (dist, sl) in enumerate(light_distances):
            if i < len(available_ids):
                sl.lightID = available_ids[i]
            else:
                sl.lightID = None
            sl.draw() 
        # ------------------------------------
        
        # Draw Actors
        jeepObj.draw() 
        jeepObj.drawW1()
        jeepObj.drawW2()
        glPopMatrix() # Pop matrix from jeepObj.draw()
        
        jeep2Obj.draw() 
        jeep2Obj.drawW1()
        jeep2Obj.drawW2()
        glPopMatrix() # Pop matrix from jeep2Obj.draw()
        
        if introTime > 5.0:
            villainStar.draw()

        if introTime > 10.0: 
            for s in minionStars:
                s.draw()

        # --- HUD: 2D Overlay for Story & Skip Text ---
        glDisable(GL_LIGHTING)

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
        jeepObj.drawW1()
        jeepObj.drawW2()
        glPopMatrix() # <--- CRITICAL: Pop matrix from jeepObj.draw()
        
        glDisable(GL_LIGHTING)
        glColor3f(0.0, 1.0, 1.0)
        mode_name = "Ambient"
        if lightMode == 1: mode_name = "Point"
        elif lightMode == 2: mode_name = "Directional"
        elif lightMode == 3: mode_name = "Spotlight"
        elif lightMode == 4: mode_name = "Default (Moonlight)"
        text3d(f"Display Mode: {mode_name}", -2.0, 4.0, 0.0)
        
    else:
        # === GAME MODE RENDER ===
        # Headlights
        if jeepObj.lightOn and lightMode != 0: 
            glEnable(GL_LIGHT1)
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

        # Text
        glDisable(GL_LIGHTING)
        
        if timeLeft <= 0:
            # --- GAME OVER (Red) ---
            glColor3f(1.0, 0.0, 0.0) 
            text3d("GAME OVER", jeepObj.posX, jeepObj.posY + 3.0, jeepObj.posZ)
        else:
            # --- TIMER (Cyan) ---
            glColor3f(0.0, 1.0, 1.0)
            
            # Format minutes and seconds (MM:SS)
            mins = int(timeLeft // 60)
            secs = int(timeLeft % 60)
            timer_text = "Time left: {:02d}:{:02d}".format(mins, secs)
            
            text3d(timer_text, jeepObj.posX, jeepObj.posY + 3.0, jeepObj.posZ)

        if lightMode != 0:
            glEnable(GL_LIGHTING)

        if lightMode != 0:
            glEnable(GL_LIGHTING)

        # Draw Objects
        for obj in objectArray: 
            obj.draw()

        glDisable(GL_LIGHTING) 
        ribbonObj.draw() 
        if lightMode != 0: glEnable(GL_LIGHTING)

        if lightMode == 4:
            glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, [0.2, 0.2, 0.2, 1.0])
        else:
            glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, [0.0, 0.0, 0.0, 1.0])

        tunnelObj.draw()

        glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, [0.0, 0.0, 0.0, 1.0])

        # Streetlights Optimization
        light_distances = []
        for sl in allstreetlights:
            dist = abs(sl.posZ - jeepObj.posZ)
            light_distances.append((dist, sl))

        light_distances.sort(key=lambda x: x[0])
        available_ids = [GL_LIGHT2, GL_LIGHT3, GL_LIGHT4, GL_LIGHT5, GL_LIGHT6, GL_LIGHT7]

        # Reset lights
        for i in available_ids: glDisable(i)

        for i, (dist, sl) in enumerate(light_distances):
            if i < len(available_ids):
                sl.lightID = available_ids[i]
            else:
                sl.lightID = None

            sl.draw() 

        # Remaining objects
        for sl in allstreetlights: sl.draw()
        for cone in allcones: cone.draw()
        for star in allstars: star.draw()

        # Draw Player Jeep
        jeepObj.draw()
        jeepObj.drawW1()
        jeepObj.drawW2()
        jeepObj.drawLight()
        glPopMatrix() # <--- CRITICAL: Pop matrix from jeepObj.draw()
    
        # --- NEW: STAR SCOREBOARD (Top Left) ---
        # 1. Switch to 2D Overlay Mode
        glDisable(GL_LIGHTING) # Disable lighting so text is bright white
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, windowWidth, 0, windowHeight)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glDisable(GL_DEPTH_TEST) # Ensure HUD draws on top of everything

        # 2. Draw Star Icon (Yellow)
        # Position: x=30, y=Top-30
        drawGUIStar(30, windowHeight - 30, 20)

        # 3. Draw Score Text (White)
        glColor3f(1.0, 1.0, 1.0) 
        score_msg = ": {} / {}".format(stars_collected, STARS_TO_WIN)
        
        # Position text next to the star icon
        glRasterPos2f(55, windowHeight - 38) 
        for char in score_msg:
             glutBitmapCharacter(GLUT_BITMAP_TIMES_ROMAN_24, ord(char))

        # 4. Restore 3D Mode
        glEnable(GL_DEPTH_TEST)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        
        # Re-enable lighting if needed for the next frame
        if lightMode != 0: glEnable(GL_LIGHTING)

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
    global stars_collected, STARS_TO_WIN

    curTime = glutGet(GLUT_ELAPSED_TIME)
    tickTime =  curTime - prevTime
    prevTime = curTime
    
    if currentMode == MODE_GAME:
        # Calculate elapsed time
        elapsed = (curTime / 1000.0) - gameStartTime
        
        # Calculate Time Left
        timeLeft = GAME_DURATION - elapsed
        
        # Check for Game Over
        if timeLeft <= 0:
            timeLeft = 0
            canStart = False         # Lock movement
            jeepObj.wheelDir = 'stop' # Stop wheels visually
            
        score = timeLeft # Keep score variable synced just in case
    else:
        timeLeft = GAME_DURATION # Reset timer when not playing

    if tickTime == 0: 
        glutPostRedisplay()
        return

    seconds_passed = tickTime / 1000.0
    
    # --- CHANGED: Logic ONLY here. Drawing moved to display() ---
    if currentMode == MODE_INTRO:
            updateIntro(seconds_passed)

    elif currentMode == MODE_GAME:

        # Game Logic
        boost_on, boost_off, is_active = ribbonObj.update(seconds_passed, jeepObj.posZ)
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

            if keyState['up']:
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
        
        for s in allstars:
            s.update(seconds_passed) 
            
            # Move the star
            moveAmount = s.speed * seconds_passed
            s.posX += moveAmount * s.direction
            
            # Bounce off walls
            if s.posX > land - 5:
                s.posX = land - 5
                s.direction = -1
            elif s.posX < -land + 5:
                s.posX = -land + 5
                s.direction = 1

            if s.posY > 0: 
                # Check distance to Jeep
                if dist((jeepObj.posX, jeepObj.posZ), (s.posX, s.posZ)) < (jeepObj.sizeX + 1.0):
                    # HIT!
                    s.posY = -100.0 # Hide it underground
                    stars_collected += 1


        if jeepObj.wheelDir == 'fwd':
            jeepObj.rotateWheel(-0.1 * tickTime)
        elif jeepObj.wheelDir == 'back':
            jeepObj.rotateWheel(0.1 * tickTime)

    elif currentMode == MODE_DISPLAY:
        # Display Mode Logic
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
    global eyeX, eyeY, eyeZ, windowWidth, windowHeight, currentMode, introTime, jeepObj
    
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()

    if windowHeight == 0:
        windowHeight = 1
    
    aspect = float(windowWidth) / float(windowHeight)
    gluPerspective(90, aspect, 0.1, 1000.0)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    # --- CINEMATIC CAMERA (INTRO MODE) ---
    if currentMode == MODE_INTRO:
        
        # 1. CHILLING (0s - 5s)
        if introTime < 5.0: # Changed from 3.0
             gluLookAt(jeepObj.posX, jeepObj.posY + 4.0, jeepObj.posZ - 8.0,
                       jeepObj.posX, jeepObj.posY, jeepObj.posZ + 10.0, 
                       0.0, 1.0, 0.0)

        # 2. GIANT STAR FALLS (5s - 10s)
        elif introTime < 10.0: # Changed from 6.0
             starZ = jeepObj.posZ + 15.0
             gluLookAt(0.0, 6.0, starZ + 10.0,
                       jeepObj.posX, jeepObj.posY, jeepObj.posZ,
                       0.0, 1.0, 0.0)

        # 3. MINIONS SWARM (10s - 15s)
        elif introTime < 15.0: # Changed from 9.0
             gluLookAt(0.0, 35.0, jeepObj.posZ + 5.0,
                       0.0, 0.0, jeepObj.posZ + 5.0,
                       0.0, 0.0, -1.0)

        # 4. KIDNAPPING (15s+)
        else:
             gluLookAt(0.0, 0.5, jeepObj.posZ - 2.0,
                       0.0, 25.0, jeepObj.posZ + 60.0,
                       0.0, 1.0, 0.0)

    # --- GAMEPLAY CAMERA (NORMAL MODES) ---
    else:
        if topView:
            eye_x = jeepObj.posX
            eye_y = max(1.0, radius)
            eye_z = jeepObj.posZ
            center_x = jeepObj.posX
            center_y = jeepObj.posY
            center_z = jeepObj.posZ
            gluLookAt(eye_x, eye_y, eye_z, center_x, center_y, center_z, 0.0, 0.0, 1.0)

        elif behindView:
            behind_fraction = 0.8
            above_fraction  = 0.4
            behind_dist = max(1.0, radius * behind_fraction)
            above_dist  = max(0.5, radius * above_fraction)

            rad_angle = math.radians(jeepObj.rotation)
            eye_x = jeepObj.posX - behind_dist * math.sin(rad_angle)
            eye_y = jeepObj.posY + above_dist
            eye_z = jeepObj.posZ - behind_dist * math.cos(rad_angle)

            center_x = jeepObj.posX
            center_y = jeepObj.posY
            center_z = jeepObj.posZ

            gluLookAt(eye_x, eye_y, eye_z, center_x, center_y, center_z, 0.0, 1.0, 0.0)

        else:
            gluLookAt(eyeX, eyeY, eyeZ,
                      jeepObj.posX, jeepObj.posY, jeepObj.posZ,
                      0.0, 1.0, 0.0)

def setObjView():
    pass

#-------------------------------------------user inputs------------------
def mouseHandle(button, state, x, y):
    global midDown
    if (button == GLUT_MIDDLE_BUTTON and state == GLUT_DOWN):
        midDown = True
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

        if (nowX - pastX > 0):
            angle -= mouseSensitivity 
        elif (nowX - pastX < 0):
            angle += mouseSensitivity
        
        if (nowY - pastY > 0): 
            phi += mouseSensitivity 
        elif (nowY - pastY < 0): 
            phi -= mouseSensitivity 

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
    global currentMode

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
        jeepObj.toggleLight()

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
    currentMode = MODE_GAME
    
    jeepObj.posX = 0.0
    jeepObj.posZ = 0.0
    
    canStart = True 
    stars_collected = 0
    
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

    if (jeepObj.posZ >= land*gameEnlarge):
        gameSuccess()
        
#----------------------------------multiplayer dev (using tracker)-----------
def recordGame():
    with open('results.csv', 'wt') as csvfile:
        spamwriter = csv.writer(csvfile, delimiter=',',quotechar='|', quoting=csv.QUOTE_MINIMAL)
        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        print(st)
        spamwriter.writerow([st] + [finalScore])
    
#-------------------------------------developing additional windows/options----
def gameOver():
    global finalScore
    print ("Game completed!")
    finalScore = score-6
    glutHideWindow()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA | GLUT_DEPTH)
    glutInitWindowSize(windowWidth, windowHeight)
    glutInitWindowPosition(600,100)
    overWin = glutCreateWindow("Game Over!")
    glutDisplayFunc(overScreen)
    glutMainLoop()
    
def gameSuccess():
    global finalScore
    print ("Game success!")
    finalScore = score-6
    glutHideWindow()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA | GLUT_DEPTH)
    glutInitWindowSize(200,200)
    glutInitWindowPosition(600,100)
    overWin = glutCreateWindow("Complete!")
    glutDisplayFunc(winScreen)
    glutMainLoop()

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
    roadTextureID = loadTexture("../img/road2.png")

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

    jeep1Obj.makeDisplayLists()
    jeep2Obj.makeDisplayLists()
    jeep3Obj.makeDisplayLists()

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
    if (applyLighting == True):
        initializeLight()
    glutMainLoop()
    
main()