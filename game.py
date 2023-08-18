import sys
import math
import random
import os

import pygame

from scripts.utils import load_image, load_images, Animation
from scripts.entities import PhysicsEntity, Player, Enemy
from scripts.tilemap import Tilemap
from scripts.clouds import Clouds
from scripts.particle import Particle
from scripts.spark import Spark

class Game:
    def __init__(self):
        pygame.init()

        pygame.display.set_caption('Platformer')
        
        self.screen = pygame.display.set_mode((640, 480))
        # display is the surface the outline is rendered to
        self.display = pygame.Surface((320, 240), pygame.SRCALPHA)
        # display_2 is the surface everything else is rendered to.
        self.display_2 = pygame.Surface((320, 240))

        self.clock = pygame.time.Clock()
        # boolean to check if play is moving in [x, y]
        self.movement = [False, False]
        
        # load png assets
        self.assets = {
            'decor': load_images('tiles/decor'),
            'grass': load_images('tiles/grass'),
            'large_decor': load_images('tiles/large_decor'),
            'stone': load_images('tiles/stone'),
            'player': load_image('entities/player.png'),
            'background': load_image('background.png'),
            'clouds': load_images('clouds'),
            'enemy/idle': Animation(load_images('entities/enemy/idle'), img_dur=6),
            'enemy/run': Animation(load_images('entities/enemy/run'), img_dur=4),
            'player/idle': Animation(load_images('entities/player/idle'), img_dur=6),
            'player/run': Animation(load_images('entities/player/run'), img_dur=4),
            'player/jump': Animation(load_images('entities/player/jump')),
            'player/slide': Animation(load_images('entities/player/slide')),
            'player/wall_slide': Animation(load_images('entities/player/wall_slide')),
            'particle/leaf': Animation(load_images('particles/leaf'), img_dur=20, loop=False),
            'particle/particle': Animation(load_images('particles/particle'), img_dur=6, loop=False),
            'gun': load_image('gun.png'),
            'projectile': load_image('projectile.png'),
        }
        
        # load the sound effects
        self.sfx = {
            'jump': pygame.mixer.Sound('data/sfx/jump.wav'),
            'dash': pygame.mixer.Sound('data/sfx/dash.wav'),
            'hit': pygame.mixer.Sound('data/sfx/hit.wav'),
            'shoot': pygame.mixer.Sound('data/sfx/shoot.wav'),
            'ambience': pygame.mixer.Sound('data/sfx/ambience.wav'),
        }

        # set the volume to each different sound effect
        self.sfx['jump'].set_volume(0.7)
        self.sfx['dash'].set_volume(0.3)
        self.sfx['hit'].set_volume(0.8)
        self.sfx['shoot'].set_volume(0.4)
        self.sfx['ambience'].set_volume(0.2)

        self.clouds = Clouds(self.assets['clouds'], count=16)
        
        self.player = Player(self, (50, 50), (8, 15))
        
        self.tilemap = Tilemap(self, tile_size=16)

        self.level = 0
        self.load_level(self.level) # increments up when level ends, up to number of levels in directory

        self.screenshake = 0


    def load_level(self, map_id):
        self.tilemap.load('data/maps/' + str(map_id) + '.json')
        # ------------------
        # lists keep track of all of the things that need to be tracked in the level.

        self.leaf_spawners = []
        for tree in self.tilemap.extract([('large_decor', 2)], keep=True):
            self.leaf_spawners.append(pygame.Rect(4 + tree['pos'][0], 4 + tree['pos'][1], 23, 13))
        
        self.enemies = []
        for spawner in self.tilemap.extract([('spawners', 0), ('spawners', 1)]):
            if spawner['variant'] == 0:
                self.player.pos = spawner['pos']
                self.player.air_time = 0
            else:
                self.enemies.append(Enemy(self, spawner['pos'], (8,15)))

        self.projectiles = []
        self.particles = []
        self.sparks = []
        
        self.scroll = [0, 0]
        self.dead = 0
        self.transition = -30 
        # ------------------
        
    def run(self):
        pygame.mixer.music.load('data/music.wav')
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(-1)
        self.sfx['ambience'].play(-1)


        while True:
            self.display.fill((0, 0, 0, 0)) # set the alpha display for the outlines
            self.display_2.blit(self.assets['background'], (0, 0)) # display the background

            self.screenshake = max(0, self.screenshake - 1)

            if not len(self.enemies): # are all the enemies defeated?
                self.transition += 1 # start the transition to the next level
                if self.transition > 30: # once the transition has made the screen black
                    self.level = min(self.level + 1, len(os.listdir('data/maps')) - 1)
                    self.load_level(self.level) # load the next level
            if self.transition < 0:
                self.transition += 1

            if self.dead:
                self.dead += 1
                if self.dead >=10: # if the player's died, start the transition
                    self.transition = min(30, self.transition + 1) # stop the transition just before the level gets incremented
                if self.dead > 40:
                    self.load_level(self.level) # load the level and 0 out dead again (in load_level declaration)
            
            self.scroll[0] += (self.player.rect().centerx - self.display.get_width() / 2 - self.scroll[0]) / 30
            self.scroll[1] += (self.player.rect().centery - self.display.get_height() / 2 - self.scroll[1]) / 30
            render_scroll = (int(self.scroll[0]), int(self.scroll[1]))
            
            for rect in self.leaf_spawners: # create leaf particles for each leafy tree in level
                if random.random() * 49999 < rect.width * rect.height:
                    pos = (rect.x + random.random() * rect.width, rect.y + random.random() * rect.height)
                    self.particles.append(Particle(self, 'leaf', pos, velocity=[-0.1, 0.3], frame=random.randint(0, 20)))
            
            self.clouds.update()
            self.clouds.render(self.display_2, offset=render_scroll) # clouds rendered only on display_2, cause we don't want outline
            
            self.tilemap.render(self.display, offset=render_scroll)

            for enemy in self.enemies.copy(): # for each enemy in the level
                kill = enemy.update(self.tilemap, (0, 0)) # update and render
                enemy.render(self.display, offset=render_scroll)
                if kill: # if update returns True (because enemy is killed)
                    self.enemies.remove(enemy) # remove enemy
            
            if not self.dead:
                self.player.update(self.tilemap, (self.movement[1] - self.movement[0], 0))
                self.player.render(self.display, offset=render_scroll)

            for projectile in self.projectiles.copy():
                projectile[0][0] += projectile[1]
                projectile[2] += 1
                img = self.assets['projectile'] # center the img on the location, and display
                self.display.blit(img, (projectile[0][0] - img.get_width() / 2 - render_scroll[0], projectile[0][1] - img.get_height() / 2 - render_scroll[1]))
                if self.tilemap.solid_check(projectile[0]): # did it hit something
                    self.projectiles.remove(projectile) # if so, remove it and display sparks
                    for i in range(4):
                            self.sparks.append(Spark(projectile[0], random.random() - 0.5 + (math.pi if projectile[1] > 0 else 0), 2 + random.random()))
                elif projectile[2] > 360: # remove projectiles that have flown a long time to avoid dragging performance
                    self.projectiles.remove(projectile)
                elif abs(self.player.dashing) < 50: # if player is not dashing
                    if self.player.rect().collidepoint(projectile[0]): # and a projectile hits them
                        self.projectiles.remove(projectile) # remove the projectile
                        self.dead += 1 
                        self.sfx['hit'].play() # player is dead, player the hit sound, shake the screen
                        self.screenshake = max(16, self.screenshake)
                        for i in range(30): # show lots of sparks and particles
                            angle = random.random() * math.pi * 2
                            speed = random.random() * 5
                            self.sparks.append(Spark(self.player.rect().center, angle, 2 + random.random()))
                            self.particles.append(Particle(self, 'particle', self.player.rect().center, velocity=[math.cos(angle + math.pi) * speed * 0.5, math.sin(angle + math.pi) * speed * 0.5], frame = random.randint(0, 7)))

            for spark in self.sparks.copy():
                kill = spark.update() # updates the speed of sparks, once they slow down enough, they disappear
                spark.render(self.display, offset=render_scroll)
                if kill:
                    self.sparks.remove(spark)
            
            display_mask = pygame.mask.from_surface(self.display)
            display_sillhouette = display_mask.to_surface(setcolor = (0, 0, 0, 180), unsetcolor = (0, 0, 0, 0))
            for offset in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                self.display_2.blit(display_sillhouette, offset) # offsets the outline display 1 pixel in each direction,

            for particle in self.particles.copy():
                kill = particle.update()
                particle.render(self.display, offset=render_scroll)
                if particle.type == 'leaf':
                    particle.pos[0] += math.sin(particle.animation.frame * 0.035) * 0.3 # leaves should gently fall
                if kill:
                    self.particles.remove(particle)
            
            # ------------- Process input -----------
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_a:
                        self.movement[0] = True
                    if event.key == pygame.K_d:
                        self.movement[1] = True
                    if event.key == pygame.K_w:
                        if self.player.jump():
                            self.sfx['jump'].play()
                    if event.key == pygame.K_x:
                        self.player.dash()
                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_a:
                        self.movement[0] = False
                    if event.key == pygame.K_d:
                        self.movement[1] = False
            # ---------------------------------------

            if self.transition:
                transition_surf = pygame.Surface(self.display.get_size())
                pygame.draw.circle(transition_surf, (255, 255, 255), (self.display.get_width() // 2, self.display.get_height() // 2), (30 - abs(self.transition)) * 8)
                transition_surf.set_colorkey((255, 255, 255))
                self.display.blit(transition_surf, (0, 0)) 
                # the transition draws a black circle over the display that shrinks down to hide the game transition to a new level

            self.display_2.blit(self.display, (0, 0)) # blit the display over the outline (display_2)

            screenshake_offset = (random.random() * self.screenshake - self.screenshake / 2, random.random() * self.screenshake - self.screenshake / 2)
            self.screen.blit(pygame.transform.scale(self.display_2, self.screen.get_size()), screenshake_offset)
            pygame.display.update()
            self.clock.tick(60)

Game().run()