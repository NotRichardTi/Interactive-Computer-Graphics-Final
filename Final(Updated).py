import math
import random
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

# Fountain body
FOUNTAIN_RADIUS = 0.6
FOUNTAIN_HEIGHT = 2.0

# Simulation constants
GRAVITY = 9.8
PARTICLE_LIFETIME = 3.0
PARTICLE_SIZE = 0.09
MAX_PARTICLES = 1000

# Adjustable ranges
MIN_SPEED, MAX_SPEED = 2.0, 10.0
MIN_CONE, MAX_CONE = 0.0, 45.0
MIN_RATE, MAX_RATE = 10.0, 500.0
MIN_PITCH, MAX_PITCH = 0.0, 60.0
MIN_DISTANCE, MAX_DISTANCE = 5.0, 40.0

def clamp(value, low, high):
    return max(low, min(high, value))

def spawnParticle(speed, coneAngle):
    # Pick a random spot on the mouth of the cylinder
    spawnAngle = random.uniform(0, 2 * math.pi)
    spawnRadius = random.uniform(0, FOUNTAIN_RADIUS * 0.8)

    x = math.cos(spawnAngle) * spawnRadius
    z = math.sin(spawnAngle) * spawnRadius

    # Pick a random direction inside the cone that points up
    tilt = math.radians(random.uniform(0, coneAngle))
    spin = random.uniform(0, 2 * math.pi)

    # Randomize the speed a little
    launchSpeed = speed * random.uniform(0.8, 1.0)

    vx = launchSpeed * math.sin(tilt) * math.cos(spin)
    vy = launchSpeed * math.cos(tilt)
    vz = launchSpeed * math.sin(tilt) * math.sin(spin)

    return {
        "pos": [x, FOUNTAIN_HEIGHT, z],
        "vel": [vx, vy, vz],
        "life": PARTICLE_LIFETIME
    }

def updateParticles(particles, dt):
    alive = []

    for p in particles:
        # Gravity only changes the vertical velocity
        p["vel"][1] -= GRAVITY * dt

        p["pos"][0] += p["vel"][0] * dt
        p["pos"][1] += p["vel"][1] * dt
        p["pos"][2] += p["vel"][2] * dt

        p["life"] -= dt

        # Keeps the particle until it expires
        if p["life"] > 0 and p["pos"][1] > 0:
            alive.append(p)

    return alive

def lifetimeColor(life):
    # Fresh particles are white, dying particles fade to blue
    fraction = clamp(life / PARTICLE_LIFETIME, 0.0, 1.0)

    r = fraction
    g = 0.3 + fraction * 0.7
    b = 1.0

    return r, g, b

def drawParticles(particles, quadric):
    for p in particles:
        r, g, b = lifetimeColor(p["life"])
        glColor3f(r, g, b)

        glPushMatrix()
        glTranslatef(p["pos"][0], p["pos"][1], p["pos"][2])
        gluSphere(quadric, PARTICLE_SIZE, 8, 8)
        glPopMatrix()

def drawFountain(quadric):
    glColor3f(0.55, 0.55, 0.60)

    glPushMatrix()

    # gluCylinder is built along z
    glRotatef(-90, 1, 0, 0)
    gluCylinder(quadric, FOUNTAIN_RADIUS, FOUNTAIN_RADIUS, FOUNTAIN_HEIGHT, 24, 1)

    # Cap the top of the cylinder
    glTranslatef(0, 0, FOUNTAIN_HEIGHT)
    gluDisk(quadric, 0, FOUNTAIN_RADIUS, 24, 1)

    glPopMatrix()

def drawFloor():
    d = 20

    glColor3f(0.18, 0.22, 0.28)

    glBegin(GL_QUADS)
    glNormal3f(0, 1, 0)
    glVertex3f(-d, 0, -d)
    glVertex3f(-d, 0, d)
    glVertex3f(d, 0, d)
    glVertex3f(d, 0, -d)
    glEnd()

hudFont = None
hudTexture = None

def getHudFont():
    global hudFont

    if hudFont is None:
        hudFont = pygame.font.Font(None, 24)

    return hudFont

def getHudTexture():
    global hudTexture

    if hudTexture is None:
        hudTexture = glGenTextures(1)

    return hudTexture

def drawText(x, y, text):
    # Draw the string into a surface, then paste that surface on a flat quad
    textSurface = getHudFont().render(text, True, (255, 255, 255))
    textData = pygame.image.tostring(textSurface, "RGBA", True)
    width, height = textSurface.get_size()

    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glPushAttrib(GL_ENABLE_BIT | GL_CURRENT_BIT | GL_TEXTURE_BIT)

    glDisable(GL_LIGHTING)
    glDisable(GL_DEPTH_TEST)
    glEnable(GL_TEXTURE_2D)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    glBindTexture(GL_TEXTURE_2D, getHudTexture())
    glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)
    glTexImage2D(
        GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, textData
    )
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    glColor4f(1, 1, 1, 1)

    # The texture is stored bottom up, so (0,0) belongs at the bottom left
    glBegin(GL_QUADS)
    glTexCoord2f(0, 0)
    glVertex2f(x, y)

    glTexCoord2f(1, 0)
    glVertex2f(x + width, y)

    glTexCoord2f(1, 1)
    glVertex2f(x + width, y + height)

    glTexCoord2f(0, 1)
    glVertex2f(x, y + height)
    glEnd()

    glPopAttrib()

    glPopMatrix()

    glMatrixMode(GL_PROJECTION)
    glPopMatrix()

    glMatrixMode(GL_MODELVIEW)

def main():
    pygame.init()

    display = (1000, 800)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Particle Fountain")

    clock = pygame.time.Clock()

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60, display[0] / display[1], 0.1, 200)

    glMatrixMode(GL_MODELVIEW)

    glEnable(GL_DEPTH_TEST)
    glEnable(GL_NORMALIZE)

    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.15, 0.15, 0.15, 1))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (1.0, 1.0, 1.0, 1))
    glLightfv(GL_LIGHT0, GL_SPECULAR, (1.0, 1.0, 1.0, 1))

    glClearColor(0.05, 0.06, 0.10, 1)

    # One quadric is reused for the spheres and the cylinder
    quadric = gluNewQuadric()
    gluQuadricNormals(quadric, GLU_SMOOTH)

    particles = []

    # Values the keys change
    speed = 6.0
    coneAngle = 20.0
    spawnRate = 150.0
    pitch = 20.0
    distance = 14.0

    # Leftover fraction of a particle from the last frame
    spawnCarry = 0.0

    running = True

    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN and event.key == K_ESCAPE:
                running = False

        keys = pygame.key.get_pressed()

        # Launch speed
        if keys[K_LEFT]:
            speed = clamp(speed - 4.0 * dt, MIN_SPEED, MAX_SPEED)
        if keys[K_RIGHT]:
            speed = clamp(speed + 4.0 * dt, MIN_SPEED, MAX_SPEED)

        # Cone angle on the "<" and ">" keys
        if keys[K_COMMA]:
            coneAngle = clamp(coneAngle - 20.0 * dt, MIN_CONE, MAX_CONE)
        if keys[K_PERIOD]:
            coneAngle = clamp(coneAngle + 20.0 * dt, MIN_CONE, MAX_CONE)

        # Spawn rate
        if keys[K_MINUS] or keys[K_KP_MINUS]:
            spawnRate = clamp(spawnRate - 200.0 * dt, MIN_RATE, MAX_RATE)
        if keys[K_EQUALS] or keys[K_PLUS] or keys[K_KP_PLUS]:
            spawnRate = clamp(spawnRate + 200.0 * dt, MIN_RATE, MAX_RATE)

        # Rotation around the x axis
        if keys[K_UP]:
            pitch = clamp(pitch + 30.0 * dt, MIN_PITCH, MAX_PITCH)
        if keys[K_DOWN]:
            pitch = clamp(pitch - 30.0 * dt, MIN_PITCH, MAX_PITCH)

        # Camera in and out
        if keys[K_w]:
            distance = clamp(distance - 10.0 * dt, MIN_DISTANCE, MAX_DISTANCE)
        if keys[K_s]:
            distance = clamp(distance + 10.0 * dt, MIN_DISTANCE, MAX_DISTANCE)

        # Spawn new particles,
        spawnCarry += spawnRate * dt
        newCount = int(spawnCarry)
        spawnCarry -= newCount

        # Clamp the total
        room = MAX_PARTICLES - len(particles)
        newCount = min(newCount, max(0, room))

        for _ in range(newCount):
            particles.append(spawnParticle(speed, coneAngle))

        particles = updateParticles(particles, dt)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        # Camera looks at the middle of the fountain
        gluLookAt(0, FOUNTAIN_HEIGHT, distance,
                  0, FOUNTAIN_HEIGHT, 0,
                  0, 1, 0)

        # Rotate the scene around the x axis
        glRotatef(pitch, 1, 0, 0)

        # Light sits above the fountain
        glLightfv(GL_LIGHT0, GL_POSITION, (0, 12, 0, 1))

        drawFloor()
        drawFountain(quadric)
        drawParticles(particles, quadric)

        drawText(20, 770, f"Speed: {speed:.1f}  (left/right)")
        drawText(20, 740, f"Cone: {coneAngle:.1f} deg  (< / >)")
        drawText(20, 710, f"Rate: {spawnRate:.0f} /sec  (+ / -)")
        drawText(20, 680, f"Rotation: {pitch:.1f} deg  (up/down)")
        drawText(20, 650, f"Distance: {distance:.1f}  (W/S)")
        drawText(20, 620, f"Particles: {len(particles)} / {MAX_PARTICLES}")

        pygame.display.flip()

    pygame.quit()

main()
