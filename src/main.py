#!/usr/bin/env python
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math, time, random, csv, datetime
import ImportObject
import PIL.Image as Image
import jeep, cone, star, ribbon, NurbsLoader, streetlight
import tkinter as tk            
from tkinter import ttk          

# --- Mode Constants ---
MODE_GAME = 0
MODE_DISPLAY = 1
currentMode = MODE_GAME # Default

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

beginTime = 0
countTime = 0
score = 0
finalScore = 0
canStart = False
overReason = ""

#for wheel spinning
tickTime = 0

#creating objects
objectArray = []
jeep1Obj = jeep.jeep('p')
jeep2Obj = jeep.jeep('g')
jeep3Obj = jeep.jeep('r')

allJeeps = [jeep1Obj, jeep2Obj, jeep3Obj]
jeepNum = 0
jeepObj = allJeeps[jeepNum]
#personObj = person.person(10.0,10.0)

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
starAmount = 5 #val = -10 pts
diamondAmount = 1 #val = deducts entire by 1/2
# diamondObj = diamond.diamond(random.randint(-land, land), random.randint(10.0, land*gameEnlarge))
usedDiamond = False

allcones = []
allstars = []
allstreetlights = []

obstacleCoord = []
rewardCoord = []
ckSense = 5.0

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
BOOST_ROT_SPEED = 120.0 # Make turning a bit faster too

# We pass it the Z position, its length, and the width of the road (`land`)
ribbonObj = ribbon.ribbon(z_pos=50.0, length=5.0, width=land)

tunnelObj = NurbsLoader.NurbsModel(
    0.0, 0.0, 20.0, 
    "../nurbs/tunnel.txt", 
    scale=(2.5, 2.5, 2.5), 
    color=(0.4, 0.4, 0.4)
)


#concerned with lighting#########################!!!!!!!!!!!!!!!!##########
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
        
        # 1. Light Mode Check
        if lightMode == 0:
            glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_DECAL)
        else:
            glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)
            glColor3f(1.0, 1.0, 1.0)
            glMaterialfv(GL_FRONT, GL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
            glMaterialfv(GL_FRONT, GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])

        glBindTexture(GL_TEXTURE_2D, roadTextureID)

        # 2. Define Road Boundaries for Texture Mapping
        # We need these to calculate the "percentage" of the road we are at
        L = self.landLength
        C = self.cont
        
        minX = -L
        maxX = L
        totalWidth = maxX - minX

        minZ = -L
        maxZ = C * L
        totalLength = maxZ - minZ

        # 3. Draw the Subdivided Grid
        startZ = minZ
        endZ = maxZ
        startX = minX
        endX = maxX
        
        step = 2.0  # Tile size

        glNormal3f(0.0, 1.0, 0.0) 

        glBegin(GL_QUADS)
        
        z = startZ
        while z < endZ:
            x = startX
            while x < endX:
                # Grid coordinates
                x1, z1 = x, z
                x2, z2 = x + step, z + step

                # Map x and z to a 0.0 - 1.0 range based on the WHOLE road size.
                u1 = (L - x1) / totalWidth
                u2 = (L - x2) / totalWidth

                v1 = (maxZ - z1) / totalLength
                v2 = (maxZ - z2) / totalLength

                # Draw the quad
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
    """
    Draws a HIGHLY TESSELLATED square floor. 
    Tessellation (many small squares) is crucial for Spotlights to work 
    correctly, as OpenGL fixed-function calculates lighting only at vertices.
    """
    # Draw Axis
    glColor4f(0.5, 0.5, 0.5, 0.5)
    glBegin(GL_LINES)
    glVertex(-20, 0, 0); glVertex(20, 0, 0)
    glVertex(0, -20, 0); glVertex(0, 20, 0)
    glVertex(0, 0, -20); glVertex(0, 0, 20)
    glEnd()

    glDisable(GL_TEXTURE_2D)
    glNormal3f(0.0, 1.0, 0.0)
    
    # Set material for lighting
    if lightMode != 0:
        # Matte gray floor to show lights clearly
        glMaterialfv(GL_FRONT, GL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
        glMaterialfv(GL_FRONT, GL_DIFFUSE, [0.6, 0.6, 0.6, 1.0])
        glMaterialfv(GL_FRONT, GL_SPECULAR, [0.0, 0.0, 0.0, 1.0]) # No shine on floor
    
    glColor3f(0.6, 0.6, 0.6)
    
    # --- TESSELLATION LOOP ---
    floorRadius = 15 # -15 to 15
    step = 0.5 # Smaller step = more vertices = better spotlight circle
    
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


def display():
    global jeepObj, canStart, score, beginTime, countTime, lightMode
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    setView()

    # --- 1. GLOBAL LIGHTING SETUP ---
    if lightMode == 0:  # Ambient/Flat
        glDisable(GL_LIGHTING)
        glDisable(GL_LIGHT0)
    else:
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0) # Always enable the main light (Sun or Moon)

        # Default "Sun" settings
        current_light_color = light0_Intensity 
        light_pos = [0.0, 10.0, 5.0, 1.0] # Default fallback

        if lightMode == 4:
            # === MODE 4 (Moonlight / Dark) ===
            # 1. Low Ambient (Base darkness)
            glLightModelfv(GL_LIGHT_MODEL_AMBIENT, [0.05, 0.05, 0.05, 1.0])
            
            # 2. "Moon" Settings (Dim Blue-ish Light)
            # This ensures the road and tunnel get lit, not just the Jeep
            moon_color = [0.15, 0.15, 0.25, 1.0] 
            current_light_color = moon_color
            
            # Position: Directional light from above
            light_pos = [0.0, 10.0, 5.0, 0.0] 

        else:
            # === MODES 1, 2, 3 (Standard Day) ===
            glLightModelfv(GL_LIGHT_MODEL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
            
            # Position Logic
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
                
                # Debug Sphere
                if lightMode != 2:
                    glPushMatrix()
                    glDisable(GL_LIGHTING)
                    glColor3f(1.0, 1.0, 0.0)
                    glTranslatef(light_pos[0], light_pos[1], light_pos[2])
                    glutWireSphere(0.2, 10, 10)
                    glEnable(GL_LIGHTING)
                    glPopMatrix()
            else:
                # Game Mode Positions
                if lightMode == 2: light_pos = [0.0, 1.0, 1.0, 0.0]
                elif lightMode == 3: 
                    light_pos = [0.0, 10.0, 0.0, 1.0]
                    glLightfv(GL_LIGHT0, GL_SPOT_DIRECTION, [0.0, -1.0, 0.0])
                    glLightf(GL_LIGHT0, GL_SPOT_CUTOFF, 45.0)

        # --- APPLY THE CALCULATED LIGHT SETTINGS ---
        glLightfv(GL_LIGHT0, GL_POSITION, light_pos)
        
        # Important: Apply the color we chose (Sun or Moon)
        glLightfv(GL_LIGHT0, GL_DIFFUSE, current_light_color)
        glLightfv(GL_LIGHT0, GL_SPECULAR, current_light_color)


    # --- 2. DRAW BASED ON MODE ---
    if currentMode == MODE_DISPLAY:
        drawDisplayModeEnvironment()
        jeepObj.draw()
        jeepObj.drawW1()
        jeepObj.drawW2()
        
        glDisable(GL_LIGHTING)
        glColor3f(0.0, 1.0, 1.0)
        mode_name = "Ambient"
        if lightMode == 1: mode_name = "Point"
        elif lightMode == 2: mode_name = "Directional"
        elif lightMode == 3: mode_name = "Spotlight"
        elif lightMode == 4: mode_name = "Default (Moonlight)"
        text3d(f"Display Mode: {mode_name}", -2.0, 4.0, 0.0)
        
    else:
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

        beginTime = 6-score
        countTime = score-6
        if (score <= 5):
            canStart = False
            glColor3f(1.0,0.0,1.0)
            text3d("Begins in: "+str(beginTime), jeepObj.posX, jeepObj.posY + 3.0, jeepObj.posZ)
        elif (score == 6):
            canStart = True
            glColor(1.0,0.0,1.0)
            text3d("GO!", jeepObj.posX, jeepObj.posY + 3.0, jeepObj.posZ)
        else:
            canStart = True
            glColor3f(0.0,1.0,1.0)
            text3d("Scoring: "+str(countTime), jeepObj.posX, jeepObj.posY + 3.0, jeepObj.posZ)

        if lightMode != 0:
            glEnable(GL_LIGHTING)

        # Draw Objects
        for obj in objectArray: 
            obj.draw()

        glDisable(GL_LIGHTING) 
        ribbonObj.draw() 
        if lightMode != 0: glEnable(GL_LIGHTING)

        tunnelObj.draw()

        for sl in allstreetlights: sl.draw()
        for cone in allcones: cone.draw()
        for star in allstars: star.draw()

        jeepObj.draw()
        jeepObj.drawW1()
        jeepObj.drawW2()
        jeepObj.drawLight()
    
    glPopMatrix()
    glutSwapBuffers()

def idle():
    global tickTime, prevTime, score, keyState, jeepObj, canStart, moveSpeed, rotSpeed
    global aiStar, aiStarSpeed, aiStarDir, lightMode
    
    curTime = glutGet(GLUT_ELAPSED_TIME)
    tickTime =  curTime - prevTime
    prevTime = curTime
    
    if currentMode == MODE_GAME:
        score = curTime/1000
    else:
        score = 0 

    if tickTime == 0: 
        glutPostRedisplay()
        return

    seconds_passed = tickTime / 1000.0
    
    if currentMode == MODE_GAME:
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
        
        for s in allstars:
            s.update(seconds_passed) 
            moveAmount = s.speed * seconds_passed
            s.posX += moveAmount * s.direction
            if s.posX > land - 5:
                s.posX = land - 5
                s.direction = -1
                s.hit()
            elif s.posX < -land + 5:
                s.posX = -land + 5
                s.direction = 1
                s.hit()

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
    global eyeX, eyeY, eyeZ, windowWidth, windowHeight
    
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()

    if windowHeight == 0:
        windowHeight = 1
    
    aspect = float(windowWidth) / float(windowHeight)
    gluPerspective(90, aspect, 0.1, 1000.0)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

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

    glutPostRedisplay()

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

    elif key == b' ': 
        jeepObj.wheelDir = 'stop' 
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
    drawTextBitmap("'l': Toggle Headlights", -0.8, 0.2) # <--- ADDED THIS LINE

    glColor3f(0.0, 1.0, 0.0)
    drawTextBitmap("Camera Controls:", -0.9, 0.0) # Moved down slightly to fit above
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
    
    # Create lights along the road (z-axis)
    # Start from z=0 and go up to the end of the land
    for z_pos in range(0, int(land * gameEnlarge), 40): # Every 40 units
        
        # Assign a real light ID if we have any left
        current_id = None
        if light_idx < len(available_lights):
            current_id = available_lights[light_idx]
            light_idx += 1
            
        # Left Side Light
        sl_left = streetlight.StreetLight(-land - 2, z_pos, current_id)
        allstreetlights.append(sl_left)

        # Assign next ID for right side if available
        current_id = None
        if light_idx < len(available_lights):
            current_id = available_lights[light_idx]
            light_idx += 1

        # Right Side Light
        sl_right = streetlight.StreetLight(land + 2, z_pos, current_id)
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
        
        # 1. Resolution / Fullscreen
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

        # 2. Game Mode Selection
        mode_selection = mode_var.get()
        if mode_selection == "Display Mode (Lighting Test)":
            currentMode = MODE_DISPLAY
            lightMode = 0
            behindView = False
            print("Starting in Display Mode")
        else:
            currentMode = MODE_GAME
            lightMode = 4
            behindView = True
            print("Starting in Game Mode")
        
        root.destroy()

    root = tk.Tk()
    root.title("Game Launcher")

    frame = ttk.Frame(root, padding="20")
    frame.grid(row=0, column=0)
    
    # --- Section 1: Mode Selection ---
    ttk.Label(frame, text="Select Game Mode:", font=('Helvetica', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0,5))
    mode_var = tk.StringVar(value="Game Mode (Racing)")
    
    modes = ["Game Mode (Racing)", "Display Mode (Lighting Test)"]
    for i, m in enumerate(modes):
        ttk.Radiobutton(frame, text=m, variable=mode_var, value=m).grid(row=i+1, column=0, sticky=tk.W, padx=20)

    ttk.Separator(frame, orient='horizontal').grid(row=3, column=0, sticky="ew", pady=10)

    # --- Section 2: Resolution Selection ---
    ttk.Label(frame, text="Select Resolution:", font=('Helvetica', 10, 'bold')).grid(row=4, column=0, sticky=tk.W, pady=(0,5))
    resolution_var = tk.StringVar(value="800x800") 
    
    display_options = ["600x600", "800x800", "1024x768", "Start in Fullscreen"]
    for i, option in enumerate(display_options):
        ttk.Radiobutton(frame, text=option, variable=resolution_var, value=option).grid(row=5+i, column=0, sticky=tk.W, padx=20)

    # Start Button
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

    # Sub-menus
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

    # Populate objects (Game Mode specific mostly)
    for i in range(coneAmount):
        addCone(random.randint(-land, land), random.randint(10.0, land*gameEnlarge))

    addStar(-land + 5, 10) 
    for i in range(starAmount):
        addStar(random.randint(-land, land), random.randint(10.0, land*gameEnlarge))

    for cone in allcones:
        cone.makeDisplayLists()

    for star in allstars:
        star.makeDisplayLists()
    
    staticObjects()
    if (applyLighting == True):
        initializeLight()
    glutMainLoop()
    
main()