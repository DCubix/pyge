from typing import Dict, Callable
import pygame
from pygame.event import Event

class DeviceButtonState:
    def __init__(self):
        self.pressed = False
        self.released = False
        self.held = False

class DeviceState:
    def __init__(self):
        self.state: Dict[int, DeviceButtonState] = {}

    def get_state(self, button: int):
        if button not in self.state.keys():
            self.state[button] = DeviceButtonState()
        return self.state[button]
    
    def is_pressed(self, button: int):
        return self.get_state(button).pressed

    def is_released(self, button: int):
        return self.get_state(button).released

    def is_held(self, button: int):
        return self.get_state(button).held

    def reset(self):
        for _, v in self.state.items():
            v.pressed = False
            v.released = False

class InputHandler:
    def __init__(self, on_exit_message: Callable[[], bool]=None, on_event: Callable[[Event], None]=None):
        self.keyboard = DeviceState()
        self.mouse = DeviceState()

        self.on_event = on_event
        self.on_exit = on_exit_message

        self.mouse_position = (0, 0)

    def poll_events(self):
        # reset pressed/released
        self.keyboard.reset()
        self.mouse.reset()

        running = True
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                state = self.keyboard.get_state(event.key)
                state.pressed = True
                state.held = True
            elif event.type == pygame.KEYUP:
                state = self.keyboard.get_state(event.key)
                state.released = True
                state.held = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.mouse_position = pygame.mouse.get_pos()
                state = self.mouse.get_state(event.button)
                state.pressed = True
                state.held = True
            elif event.type == pygame.MOUSEBUTTONUP:
                self.mouse_position = pygame.mouse.get_pos()
                state = self.mouse.get_state(event.button)
                state.released = True
                state.held = False
            elif event.type == pygame.MOUSEMOTION:
                self.mouse_position = event.pos

            if self.on_event: self.on_event(event)

            if event.type == pygame.QUIT:
                running = self.on_exit() if self.on_exit else False
        
        return running