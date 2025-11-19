#!/usr/bin/env python
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math, time, random, csv, datetime
import ImportObject
import PIL.Image as Image
import jeep, cone, star, ribbon, NurbsLoader
import tkinter as tk            
from tkinter import ttk          

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
        glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_DECAL)
        glBindTexture(GL_TEXTURE_2D, roadTextureID)

        glBegin(GL_POLYGON)

        glTexCoord2f(self.landH, self.landH)
        glVertex3f(self.landLength, 0, self.cont * self.landLength)

        glTexCoord2f(self.landH, self.landW)
        glVertex3f(self.landLength, 0, -self.landLength)

        glTexCoord2f(self.landW, self.landW)
        glVertex3f(-self.landLength, 0, -self.landLength)

        glTexCoord2f(self.landW, self.landH)
        glVertex3f(-self.landLength, 0, self.cont * self.landLength)
        glEnd()

        glDisable(GL_TEXTURE_2D)

#--------------------------------------populating scene----------------
def staticObjects():
    global objectArray
    objectArray.append(Scene())
    print ('append')


def display():
    global jeepObj, canStart, score, beginTime, countTime
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    setView()

    if lightMode == 0:  # Ambient light
        glDisable(GL_LIGHTING)
    else:
        glEnable(GL_LIGHTING)
        # Set light position based on mode
        if lightMode == 2:  # Directional
            light_pos = [0.0, 1.0, 1.0, 0.0]
        else:
            light_pos = [0.0, 1.0, 1.0, 1.0]
        
        glLightfv(GL_LIGHT0, GL_POSITION, light_pos)
        glLightfv(GL_LIGHT0, GL_DIFFUSE, light0_Intensity)
        
        if lightMode == 3:  # Spotlight
            glLightfv(GL_LIGHT0, GL_SPOT_DIRECTION, [0.0, -1.0, 0.0])
            glLightf(GL_LIGHT0, GL_SPOT_CUTOFF, 45.0)
            glLightf(GL_LIGHT0, GL_SPOT_EXPONENT, 2.0)
        else:
            glLightf(GL_LIGHT0, GL_SPOT_CUTOFF, 180.0)  # Disable spot for point/directional
        
        glEnable(GL_LIGHT0)

        # Draw test spheres for lighting
        glPushMatrix()
        glLoadIdentity()
        gluLookAt(0.0, 3.0, 5.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0)

        glLightfv(GL_LIGHT0, GL_POSITION, light_pos)
        pointPosition = [0.0,-10.0,0.0]

        glDisable(GL_LIGHTING)

        glColor3f(light0_Intensity[0], light0_Intensity[1], light0_Intensity[2])

        glTranslatef(light_pos[0], light_pos[1], light_pos[2])

        glutSolidSphere(0.025, 36, 24)

        glTranslatef(-light_pos[0], -light_pos[1], -light_pos[2])
        glEnable(GL_LIGHTING)
        glMaterialfv(GL_FRONT, GL_AMBIENT, matAmbient)
        for x in range(1,4):
            for z in range(1,4):
                 matDiffuse = [float(x) * 0.3, float(x) * 0.3, float(x) * 0.3, 1.0] 
                 matSpecular = [float(z) * 0.3, float(z) * 0.3, float(z) * 0.3, 1.0]  
                 matShininess = float(z * z) * 10.0
                 ## Set the material diffuse values for the polygon front faces. 
                 glMaterialfv(GL_FRONT, GL_DIFFUSE, matDiffuse)

                 ## Set the material specular values for the polygon front faces. 
                 glMaterialfv(GL_FRONT, GL_SPECULAR, matSpecular)

                 ## Set the material shininess value for the polygon front faces. 
                 glMaterialfv(GL_FRONT, GL_SHININESS, matShininess)

                 ## Draw a glut solid sphere with inputs radius, slices, and stacks
                 glutSolidSphere(0.25, 72, 64)
                 glTranslatef(1.0, 0.0, 0.0)

            glTranslatef(-3.0, 0.0, 1.0)
        glPopMatrix()
   
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

    for obj in objectArray:
        obj.draw()

    # --- NEW: Draw the Boost Ribbon ---
    # Disable lighting so it's always bright
    glDisable(GL_LIGHTING) 
    
    ribbonObj.draw() # <--- CALL THE OBJECT'S DRAW METHOD
    
    # Re-enable lighting if it was supposed to be on
    if lightMode != 0:
        glEnable(GL_LIGHTING)
    # --- End Boost Ribbon ---

    tunnelObj.draw()

    for cone in allcones:
        cone.draw()

    for star in allstars:
        star.draw()

    # if (usedDiamond == False):
    #     diamondObj.draw()
    
    jeepObj.draw()
    jeepObj.drawW1()
    jeepObj.drawW2()
    jeepObj.drawLight()
    glPopMatrix()
    #personObj.draw()
    glutSwapBuffers()

def idle():
    global tickTime, prevTime, score, keyState, jeepObj, canStart, moveSpeed, rotSpeed
    global aiStar, aiStarSpeed, aiStarDir, lightMode
    # (No ribbon globals needed here anymore)

    # --- Handle Time and Score ---
    curTime = glutGet(GLUT_ELAPSED_TIME)
    tickTime =  curTime - prevTime
    prevTime = curTime
    score = curTime/1000

    if tickTime == 0: # Avoid issues if frame is too fast
        glutPostRedisplay()
        return

    # --- NEW: Handle Boost Logic ---
    seconds_passed = tickTime / 1000.0
    
    # Call the ribbon's update method
    # It needs the time delta and the jeep's Z position
    boost_on, boost_off, is_active = ribbonObj.update(seconds_passed, jeepObj.posZ)
    
    # React to the returned state changes
    if boost_on:
        moveSpeed = BOOST_SPEED
        rotSpeed = BOOST_ROT_SPEED
        # print("Boost ON!") # Optional: for debugging
    elif boost_off:
        moveSpeed = NORMAL_SPEED
        rotSpeed = NORMAL_ROT_SPEED
        # print("Boost OFF!") # Optional: for debugging
    # --- End Boost Logic ---


    # --- Handle Movement Logic ---
    if canStart:
        # 1. Calculate frame-independent movement/rotation amounts
        #    (These now use moveSpeed/rotSpeed, which might be boosted)
        moveAmount = moveSpeed * seconds_passed
        rotAmount = rotSpeed * seconds_passed

        # 2. Handle Forward/Backward Movement
        if keyState['up']:
            jeepObj.move(False, moveAmount) # Move forward
            jeepObj.wheelDir = 'fwd'
        elif keyState['down']:
            jeepObj.move(False, -moveAmount) # Move backward
            jeepObj.wheelDir = 'back'
        else:
            jeepObj.wheelDir = 'stop'

        # 3. Handle Rotation
        if keyState['left']:
            jeepObj.move(True, rotAmount) # Rotate left (positive)
        elif keyState['right']:
            jeepObj.move(True, -rotAmount) # Rotate right (negative)
    
    # --- Handle AI Star Movement (Reacts to Light) ---
    for s in allstars:
        # 1. Update the star's internal timer (for 'hit' color)
        s.update(seconds_passed) # <--- MODIFIED
        
        # 2. Calculate frame-independent move amount for this star
        moveAmount = s.speed * seconds_passed
        
        # 3. Update this star's position
        s.posX += moveAmount * s.direction
        
        # 4. Check patrol bounds, reverse direction, and trigger 'hit'
        if s.posX > land - 5:
            s.posX = land - 5
            s.direction = -1
            s.hit() # <--- MODIFIED
        elif s.posX < -land + 5:
            s.posX = -land + 5
            s.direction = 1
            s.hit() # <--- MODIFIED

    # --- Handle Wheel Spinning ---
    if jeepObj.wheelDir == 'fwd':
        jeepObj.rotateWheel(-0.1 * tickTime) # Keep original spin speed
    elif jeepObj.wheelDir == 'back':
        jeepObj.rotateWheel(0.1 * tickTime)
    
    # --- Redraw ---
    glutPostRedisplay()
    

#---------------------------------setting camera----------------------------
def setView():
    global eyeX, eyeY, eyeZ, windowWidth, windowHeight
    
    # --- 1. Set the PROJECTION Matrix ---
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()

    # Avoid division by zero
    if windowHeight == 0:
        windowHeight = 1
    
    aspect = float(windowWidth) / float(windowHeight)
    gluPerspective(90, aspect, 0.1, 1000.0)  # extend far plane a bit for zoomed-out views

    # --- 2. Set the MODELVIEW Matrix ---
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    # --- 3. Set the Camera (View) ---
    if topView:
        # Use radius as the camera height (zoom in/out changes height)
        eye_x = jeepObj.posX
        eye_y = max(1.0, radius)  # keep a minimum height
        eye_z = jeepObj.posZ
        center_x = jeepObj.posX
        center_y = jeepObj.posY
        center_z = jeepObj.posZ
        # Up vector points along +Z for a true top-down on XZ ground plane
        gluLookAt(eye_x, eye_y, eye_z, center_x, center_y, center_z, 0.0, 0.0, 1.0)

    elif behindView:
        # Use radius to control how far and how high the camera is
        # Split radius into behind and above components for a natural chase-cam
        # Tune these weights to taste
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
        # Default orbit camera around the jeep using angle/phi/radius
        # recalculateEyePos() already sets eyeX/eyeY/eyeZ from radius/angle/phi
        # Make sure those are up-to-date when this path is used.
        gluLookAt(eyeX, eyeY, eyeZ,
                  jeepObj.posX, jeepObj.posY, jeepObj.posZ,
                  0.0, 1.0, 0.0)

    glutPostRedisplay()

def setObjView():
    # things to do
    # realize a view following the jeep
    # refer to setview
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
            angle -= mouseSensitivity # Adjust sensitivity
        elif (nowX - pastX < 0):
            angle += mouseSensitivity
        
        if (nowY - pastY > 0): # Mouse moved down
            phi += mouseSensitivity # <-- MODIFIED LINE
        elif (nowY - pastY < 0): # Mouse moved up
            phi -= mouseSensitivity # <-- MODIFIED LINE

        # Clamp phi to prevent the camera from flipping over the top or bottom
        if (phi > math.pi / 2.0 - 0.01):
            phi = math.pi / 2.0 - 0.01
        if (phi < -math.pi / 2.0 + 0.01):
            phi = -math.pi / 2.0 + 0.01

        recalculateEyePos() # Update camera position

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
        # ... (your existing help window logic) ...
        print ("h pushed"+ str(helpWindow))
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
            #glutDestroyWindow(helpWin)
            glutMainLoop()

    # --- Object Controls ---
    elif key == b' ': # Spacebar
        jeepObj.wheelDir = 'stop' # Stop the wheels
    elif key == b'+' or key == b'=':
        jeepObj.sizeX += 0.1
        jeepObj.sizeY += 0.1
        jeepObj.sizeZ += 0.1
    elif key == b'-' or key == b'_':
        if jeepObj.sizeX > 0.2: # Add check to prevent negative scale
            jeepObj.sizeX -= 0.1
            jeepObj.sizeY -= 0.1
            jeepObj.sizeZ -= 0.1

    # --- Camera Controls ---
    elif key == b'z': # Zoom in
        radius -= 0.5
        if radius < 1.0: radius = 1.0 # Don't go inside the origin
        recalculateEyePos()
    elif key == b'x': # Zoom out
        radius += 0.5
        recalculateEyePos()
    
    elif key == b't': # Top View
        topView = not topView
        behindView = False
    elif key == b'b': # Behind View
        behindView = not behindView
        topView = False
    elif key == b'c': # Center (Default) View
        behindView = False
        topView = False
        # Reset camera to default
        eyeX = 0.0
        eyeY = 2.0
        eyeZ = 10.0
        angle = 0.0
        radius = 10.0
        phi = 0.0

        recalculateEyePos()

    setView() # Update the view after a keypress
    # things can do
    # this is the part to set special functions, such as help window.

def menuFunc(value):
    global lightMode, isFullScreen, windowWidth, windowHeight
    global prevWidth, prevHeight, prevPosX, prevPosY

    if 0 <= value <= 3: # Lighting options
        print(f"Lighting mode set to: {value}")
        lightMode = value
    
    # --- Resolution Options ---
    elif value == 101: # 600x600
        if not isFullScreen:
            glutReshapeWindow(600, 600)
    
    elif value == 102: # 800x800
        if not isFullScreen:
            glutReshapeWindow(800, 800)

    elif value == 103: # 1024x768
        if not isFullScreen:
            glutReshapeWindow(1024, 768)

    # --- Fullscreen Toggle ---
    elif value == 200:
        if not isFullScreen:
            # Save current window state
            prevWidth = windowWidth
            prevHeight = windowHeight
            prevPosX = glutGet(GLUT_WINDOW_X)
            prevPosY = glutGet(GLUT_WINDOW_Y)
            
            # Go fullscreen
            glutFullScreen()
            isFullScreen = True
        else:
            # Restore previous window state
            glutReshapeWindow(prevWidth, prevHeight)
            glutPositionWindow(prevPosX, prevPosY)
            isFullScreen = False

    glutPostRedisplay()
    return 0

#-------------------------------------------------tools----------------------       
def drawTextBitmap(string, x, y): #for writing text to display
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

    # 1. Calculate the *offset* from the center point
    offsetX = radius * math.cos(phi) * math.sin(angle)
    offsetY = radius * math.sin(phi)
    offsetZ = radius * math.cos(phi) * math.cos(angle)
    
    # 2. Add that offset to the jeep's current position
    eyeX = jeepObj.posX + offsetX
    eyeY = jeepObj.posY + offsetY
    eyeZ = jeepObj.posZ + offsetZ

def reshape(w, h):
    global windowWidth, windowHeight
    
    # Store new dimensions
    windowWidth = w
    windowHeight = h
    
    # Set the viewport to cover the new window
    glViewport(0, 0, w, h)
    
    # Since the projection matrix depends on the aspect ratio,
    # we need to update it. The easiest way is to call setView().
    setView()

#--------------------------------------------making game more complex--------
def addCone(x,z):
    allcones.append(cone.cone(x,z))
    obstacleCoord.append((x,z))

def addStar(x,z):
    # Create the star object first
    new_star = star.star(x,z)
    
    new_star.posY = 2.0 

    new_star.speed = random.uniform(3.0, 7.0) 
    new_star.direction = random.choice([1, -1])
    # -----------------------
    
    allstars.append(new_star)
    rewardCoord.append((x,z))

def collisionCheck():
    global overReason, score, usedDiamond, countTime
    for obstacle in obstacleCoord:
        if dist((jeepObj.posX, jeepObj.posZ), obstacle) <= ckSense:
            overReason = "You hit an obstacle!"
            gameOver()
    if (jeepObj.posX >= land or jeepObj.posX <= -land):
        overReason = "You ran off the road!"
        gameOver()

    # if (dist((jeepObj.posX, jeepObj.posZ), (diamondObj.posX, diamondObj.posZ)) <= ckSense and usedDiamond ==False):
    #     print ("Diamond bonus!")
    #     countTime /= 2
    #     usedDiamond = True
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
    #recordGame() #add to excel
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
    #recordGame() #add to excel
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
    
    # Title
    glColor3f(1.0, 0.0, 0.0)
    drawTextBitmap("Help Guide" , -0.2, 0.85)
    
    # --- Jeep Controls ---
    glColor3f(0.0, 1.0, 0.0)
    drawTextBitmap("Jeep Controls:", -0.9, 0.7) 
    glColor3f(1.0, 1.0, 1.0)
    drawTextBitmap("Up/Down Arrows: Move Forward / Backward", -0.8, 0.6)
    drawTextBitmap("Left/Right Arrows: Turn Jeep Left / Right", -0.8, 0.5)
    drawTextBitmap("Spacebar: Stop wheel rotation (Brake)", -0.8, 0.4)
    drawTextBitmap("'+' / '-': Increase / Decrease Jeep Size", -0.8, 0.3)

    # --- Camera Controls ---
    glColor3f(0.0, 1.0, 0.0)
    drawTextBitmap("Camera Controls:", -0.9, 0.1)
    glColor3f(1.0, 1.0, 1.0)
    drawTextBitmap("Middle Mouse + Drag: Orbit Camera", -0.8, 0.0)
    drawTextBitmap("'z' / 'x': Zoom In / Zoom Out", -0.8, -0.1)
    drawTextBitmap("'t': Toggle Top-Down View", -0.8, -0.2)
    drawTextBitmap("'b': Toggle Behind-Jeep View", -0.8, -0.3)
    drawTextBitmap("'c': Reset Camera to Default (orbits jeep)", -0.8, -0.4) 

    # --- Other Controls ---
    glColor3f(0.0, 1.0, 0.0)
    drawTextBitmap("Other:", -0.9, -0.6)
    glColor3f(1.0, 1.0, 1.0)
    drawTextBitmap("'h': Close this Help Window", -0.8, -0.7)
    drawTextBitmap("Right Mouse Click: Open Main Menu", -0.8, -0.8)
    drawTextBitmap("  -> Lighting, Resolution, Fullscreen", -0.7, -0.9) 

    glutSwapBuffers()

#----------------------------------------------texture development-----------
def loadTexture(imageName):
    texturedImage = Image.open(imageName)
    try:
        imgX = texturedImage.size[0]
        imgY = texturedImage.size[1]
        img = texturedImage.tobytes("raw","RGBX",0,-1)#tostring("raw", "RGBX", 0, -1)
    except Exception:
        print ("Error:")
        print ("Switching to RGBA mode.")
        imgX = texturedImage.size[0]
        imgY = texturedImage.size[1]
        img = texturedImage.tobytes("raw","RGB",0,-1)#tostring("raw", "RGBA", 0, -1)

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
    
#-----------------------------------------------lighting work--------------
def initializeLight():
    glEnable(GL_DEPTH_TEST)              
    glEnable(GL_NORMALIZE)               
    glClearColor(0.1, 0.1, 0.1, 0.0)

#~~~~~~~~~~~~~~~~~~~~~~~~~the finale!!!~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def show_launcher():
    global windowWidth, windowHeight, isFullScreen

    # This function is called when the "Start" button is clicked
    def start_game():
        global windowWidth, windowHeight, isFullScreen
        
        # Get the selected option (e.g., "800x800" or "Start in Fullscreen")
        selection = selection_var.get()

        if selection == "Start in Fullscreen":
            isFullScreen = True
            # We must set a default windowed size for the "Toggle Fullscreen"
            # menu option to work correctly.
            windowWidth = 800  # Default windowed size
            windowHeight = 600 # Default windowed size
        else:
            isFullScreen = False
            # Parse the resolution string (e.g., "600x600")
            w, h = selection.split('x')
            windowWidth = int(w)
            windowHeight = int(h)
        
        # Close the launcher window and continue the script
        root.destroy()

    # --- Create the main Tkinter window ---
    root = tk.Tk()
    root.title("Game Settings")

    # --- Create a variable to hold the single selection ---
    # We set a default selection
    selection_var = tk.StringVar(value="800x800") 

    # --- Create the UI elements ---
    frame = ttk.Frame(root, padding="20")
    frame.grid(row=0, column=0)
    
    ttk.Label(frame, text="Select Display Mode:").grid(row=0, column=0, sticky=tk.W, pady=5)
    
    # All display options, including fullscreen
    display_options = [
        "600x600", 
        "800x800", 
        "1024x768", 
        "1280x720", 
        "Start in Fullscreen"
    ]
    
    # Create a radio button for each option
    for i, option in enumerate(display_options):
        ttk.Radiobutton(
            frame, 
            text=option, 
            variable=selection_var, 
            value=option
        ).grid(row=i+1, column=0, sticky=tk.W, padx=20)

    # Start button (moved down slightly)
    ttk.Button(frame, text="Start Game", command=start_game).grid(row=len(display_options)+1, column=0, pady=10)

    # --- Center the window and run it ---
    root.eval('tk::PlaceWindow . center')
    
    # This runs the Tkinter window. The script will *pause* here
    # until the window is destroyed (by clicking the button).
    root.mainloop()

def main():
    show_launcher()

    glutInit()

    global prevTime, mainWin
    prevTime = glutGet(GLUT_ELAPSED_TIME)
    
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGBA | GLUT_DEPTH)
    # things to do
    # change the window resolution in the game
    glutInitWindowSize(windowWidth, windowHeight)
    
    glutInitWindowPosition(0, 0)
    mainWin = glutCreateWindow(b'CS4182')

    # --- CHECK FOR FULLSCREEN ---
    # If the user checked the fullscreen box in the launcher,
    # we enter fullscreen mode immediately.
    if isFullScreen:
        # We still save the windowed-mode dimensions
        # so the "Toggle Fullscreen" menu option works correctly.
        prevWidth = windowWidth
        prevHeight = windowHeight
        prevPosX = glutGet(GLUT_WINDOW_X)
        prevPosY = glutGet(GLUT_WINDOW_Y)
        glutFullScreen()
    # ----------------------------

    glutDisplayFunc(display)
    glutIdleFunc(idle)#wheel turn

    setView()
    glLoadIdentity()
    glEnable(GL_DEPTH_TEST)   

    glutMouseFunc(mouseHandle)
    glutMotionFunc(motionHandle)
    glutSpecialFunc(specialKeys)
    glutSpecialUpFunc(specialKeysUp)
    glutKeyboardFunc(myKeyboard)
    glutReshapeFunc(reshape)
    # things to do
    # add a menu 

    # Create a sub-menu for lighting
    lightMenu = glutCreateMenu(menuFunc)
    glutAddMenuEntry("Ambient Light", 0)
    glutAddMenuEntry("Point Light", 1)
    glutAddMenuEntry("Directional Light", 2)
    glutAddMenuEntry("Spotlight", 3)

    # Create a sub-menu for resolution
    resMenu = glutCreateMenu(menuFunc)
    glutAddMenuEntry("600 x 600", 101)
    glutAddMenuEntry("800 x 800", 102)
    glutAddMenuEntry("1024 x 768", 103)

    # Create the main menu
    glutCreateMenu(menuFunc)
    glutAddSubMenu("Lighting", lightMenu)
    glutAddSubMenu("Resolution", resMenu)
    glutAddMenuEntry("Toggle Fullscreen", 200) # Add toggle option

    # Attach the main menu to the right mouse button
    glutAttachMenu(GLUT_RIGHT_BUTTON)

    loadSceneTextures()

    jeep1Obj.makeDisplayLists()
    jeep2Obj.makeDisplayLists()
    jeep3Obj.makeDisplayLists()
    #personObj.makeDisplayLists()

    # things to do
    # add a automatic object
    for i in range(coneAmount):#create cones randomly for obstacles, making sure to give a little lag time in beginning by adding 10.0 buffer
        addCone(random.randint(-land, land), random.randint(10.0, land*gameEnlarge))

    # Add the original "aiStar" to the allstars list
    addStar(-land + 5, 10) 
    
    # Create the other random stars
    for i in range(starAmount):#create stars randomly for rewards
        addStar(random.randint(-land, land), random.randint(10.0, land*gameEnlarge))

    for cone in allcones:
        cone.makeDisplayLists()

    for star in allstars:
        star.makeDisplayLists()
    
    # diamondObj.makeDisplayLists()
    
    staticObjects()
    if (applyLighting == True):
        initializeLight()
    glutMainLoop()



    
main()