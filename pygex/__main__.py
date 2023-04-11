import sys

pygex_application_template = '''from pygex import Application

class {class_name}(Application):
    def __init__(self):
        self.setup(size=(1280, 720))
    
    def on_start(self):
        pass

    def on_update(self, delta_time: float):
        pass

    def on_draw(self):
        pass

    def on_exit(self):
        return False
'''

pygex_game_object_template = '''from pygex.core import GameObject
from pygex.rendering import Renderer

class {class_name}(GameObject):
    def __init__(self):
        super().__init__()
    
    def on_create(self):
        pass

    def on_destroy(self):
        pass

    def on_update(self, delta_time: float):
        pass

    def on_render(self, renderer: Renderer):
        pass
'''

def cmd_create_app(args: list):
    if len(args) == 0:
        print('Usage: pygex create_app <class_name> [<file_name>]')
        return

    class_name: str = args.pop()
    if len(args) > 0:
        file_name = args.pop()
    else:
        file_name = f'{class_name.lower()}.py'
    
    with open(file_name, 'w') as f:
        f.write(pygex_application_template.format(class_name=class_name))

def cmd_create_game_object(args: list):
    if len(args) == 0:
        print('Usage: pygex create_game_object <class_name> [<file_name>]')
        return

    class_name: str = args.pop()
    if len(args) > 0:
        file_name = args.pop()
    else:
        file_name = f'{class_name.lower()}.py'
    
    with open(file_name, 'w') as f:
        f.write(pygex_game_object_template.format(class_name=class_name))

commands = {
    'create_app': cmd_create_app,
    'create_game_object': cmd_create_game_object
}

if __name__ == '__main__':
    # parse args
    args = sys.argv[1:]

    cmd = args[0].lower()
    cmd_args = args[1:]

    if cmd not in commands:
        print(f'Unknown command: {cmd}')
    else:
        commands[cmd](cmd_args)
