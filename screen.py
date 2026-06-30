import sys
import pygame
import datetime
import threading
import subprocess
import time
import os

pygame.init()
fps = 60
clock = pygame.time.Clock()
width = 320
height = 240

screen = pygame.display.set_mode((width, height))
running = True

BINS_PATH = 'saves/bins'

font = pygame.font.SysFont('arial',40)
header_font = pygame.font.SysFont('arial', 13)

HEADER_HEIGHT = 25 
HEADER_BG = (30, 30, 30)

dot_colors = {
    'idle': (100, 100, 100),
    'connected': (0, 255, 0),
    'reading': (255, 165, 0),
    'writing': (0, 150, 255),
    'backup': (255, 255, 0),
    'error': (255, 0, 0),
}

app_state = {
    'chip': None,       # string like "W25Q64FV" or None
    'status': 'idle',   # idle / connected / reading / writing / backup / error
    'connected': False  # CH341A detected
}

def draw_header():
    pygame.draw.rect(screen, HEADER_BG, (0, 0, width, HEADER_HEIGHT))

    # left - chip name
    chip_text = app_state['chip'] or 'No Chip'
    chip_surf = header_font.render(chip_text, True, (200, 200, 200))
    screen.blit(chip_surf, (5, 4))

    # center - indicator 
    dot_color = dot_colors[app_state['status']]
    pygame.draw.circle(screen, dot_color, (width // 2, HEADER_HEIGHT // 2), 6)

    # right - time
    time_text = datetime.datetime.now().strftime('%H:%M')
    time_surf = header_font.render(time_text, True, (200, 200, 200))
    screen.blit(time_surf, (width - time_surf.get_width() - 5, 4))

    # divider line under header 
    pygame.draw.line(screen, (60, 60, 60), (0, HEADER_HEIGHT), (width, HEADER_HEIGHT), 1)

class Navigator():
    def __init__(self, first_screen):
        self.stack = [first_screen]

    def push(self, s):
        self.stack.append(s)
    def pop(self):
        if len(self.stack) > 1: 
            self.stack.pop()
    def current(self):
        return self.stack[-1]

class Screen():
    def __init__(self, name, items): 
        self.name = name
        self.items = items  # list of buttons or options
        self.cursor = 0

    def handle_input(self, event, nav):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.cursor = (self.cursor + 1) % len(self.items)
            elif event.key == pygame.K_UP:
                self.cursor = (self.cursor - 1) % len(self.items)
            elif event.key == pygame.K_RETURN:
                selected = self.items[self.cursor]
                if selected.enabled_check():
                    selected.onclickfunction(nav)
            elif event.key == pygame.K_BACKSPACE:
                nav.pop()

    def next(self, s):
        screen_stack.append(s)

    def draw(self):
        for i, item in enumerate(self.items):
            item.process(i == self.cursor)
    
class Button():
    def __init__(self, x, y, width, height, buttontext='button', onclickfunction=None, enabled_check=None):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.onclickfunction = onclickfunction
        self.alreadypressed = False
        self.enabled_check = enabled_check or (lambda: True)

        self.fillcolors = {
            'normal': '#ffffff',
            'hover': '#666666',
            'pressed': '#333333',
            'disabled': '#444444'
        }
        self.buttonsurface = pygame.Surface((self.width, self.height))
        self.buttonrect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.buttontext = buttontext
        self.buttonsurf = font.render(buttontext, True, (20, 20, 20))

    def process(self, is_focused):
        enabled = self.enabled_check()

        if not enabled:
            self.buttonsurface.fill(self.fillcolors['disabled'])
        else:
            self.buttonsurface.fill(self.fillcolors['normal'])
            if is_focused:
                self.buttonsurface.fill(self.fillcolors['hover'])
                if pygame.key.get_pressed()[pygame.K_RETURN]:
                    self.buttonsurface.fill(self.fillcolors['pressed'])

        text_color = (100, 100, 100) if not enabled else (20, 20, 20)
        surf = font.render(self.buttontext, True, text_color)
        self.buttonsurface.blit(surf, [
            self.buttonrect.width/2 - surf.get_rect().width/2,
            self.buttonrect.height/2 - surf.get_rect().height/2
        ])
        screen.blit(self.buttonsurface, self.buttonrect)

class DetectScreen(Screen):
    def __init__(self):
        super().__init__('Detect', [])
        self.results = []
        self.cursor = 0 
        self.status = 'scanning'
        self._start_detect()

    def _start_detect(self):
        thread = threading.Thread(target=self._run_flashrom)
        thread.daemon = True
        thread.start()

    def _run_flashrom(self):
        app_state['status'] = 'connected'
        result = subprocess.run(
                ['flashrom', '-p', 'ch341a_spi'],
                capture_output=True,
                text=True
        )
        output = result.stdout + result.stderr
        self.results = self._parse_chips(output)

        # time.sleep(2)  # fake scan delay
        
        # fake results, swap these to test each case
        # self.results = ['W25Q64FV', 'W25Q64BV']  # multiple
        # self.results = ['W25Q64FV']             # single
        # self.results = []                       # none found

        if len(self.results) == 0:
            self.status = 'none'
            app_state['status'] = 'error'
        elif len(self.results) == 1:
            self.status = 'done'
            app_state['chip'] = self.results[0]
            app_state['status'] = 'connected'
        else: 
            self.status = 'multiple' # user needs to pick

    def _parse_chips(self, output): 
        chips = []
        for line in output.splitline():
            if line.startswith('Found'):
                chips.append(line)
        return chips

    def handle_input(self, event, nav):
        if event.type == pygame.KEYDOWN:
            if self.status == 'multiple':
                if event.key == pygame.K_DOWN:
                    self.cursor = (self.cursor + 1) % len(self.results)
                elif event.key == pygame.K_UP:
                    self.cursor = (self.cursor - 1) % len(self.results)
                elif event.key == pygame.K_RETURN:
                    app_state['chip'] = self.results[self.cursor]
                    app_state['status'] = 'connected'
                    nav.pop()
            elif self.status in ('done', 'none'):
                if event.key == pygame.K_RETURN or event.key == pygame.K_BACKSPACE:
                    nav.pop()

    def draw(self):
            y = HEADER_HEIGHT + 10
            if self.status == 'scanning':
                text = header_font.render('Detecting...', True, (200, 200, 200))
                screen.blit(text, (10, y))

            elif self.status == 'none':
                text = header_font.render('No chip found', True, (255, 0, 0))
                screen.blit(text, (10, y))
                hint = header_font.render('Press ENTER to go back', True, (150, 150, 150))
                screen.blit(hint, (10, y + 20))

            elif self.status == 'done':
                text = header_font.render(f'Found: {self.results[0]}', True, (0, 255, 0))
                screen.blit(text, (10, y))
                hint = header_font.render('Press ENTER to confirm', True, (150, 150, 150))
                screen.blit(hint, (10, y + 20))

            elif self.status == 'multiple':
                label = header_font.render('Multiple chips found:', True, (200, 200, 200))
                screen.blit(label, (10, y))
                for i, chip in enumerate(self.results):
                    color = (0, 255, 0) if i == self.cursor else (200, 200, 200)
                    chip_surf = header_font.render(chip, True, color)
                    screen.blit(chip_surf, (10, y + 20 + i * 20))

class ReadScreen(Screen):
    def __init__(self):
        super().__init__('Read', [])
        self.status = 'idle'
        self.progress = 0
        self.log_lines = []
        self.scroll = 0

    def _run_read(self):
        app_state['status'] = 'reading'
        self.status = 'reading'

        process = subprocess.Popen(
            ['flashrom', '-p', 'ch341a_spi', '-r', 'saves/backups/read_temp.bin'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        for line in process.stdout:
            self.log_lines.append(line.strip())
            if 'Reading' in line:
                try:
                    self.progress = int(line.split('%')[0].split()[-1])
                except:
                    pass

        process.wait()

        if process.returncode == 0:
            self.status = 'done'
            app_state['status'] = 'connected'
        else:
            self.status = 'error'
            app_state['status'] = 'error'
    # Mock
        # fake_lines = [
        #           'Found Winbond flash chip "W25Q64FV"',
        #           'Reading flash... ',
        #           'Reading... 25%',
        #           'Reading... 50%',
        #           'Reading... 75%',
        #           'Reading... 100%',
        #           'Done.',
        #       ]
        # for i, line in enumerate(fake_lines):
        #     time.sleep(0.5)
        #     self.log_lines.append(line)
        #     self.progress = int((i + 1) / len(fake_lines) * 100)

        # self.status = 'done'
        # app_state['status'] = 'connected'

    def start_read(self):
        thread = threading.Thread(target=self._run_read)
        thread.daemon = True
        thread.start()

    def handle_input(self, event, nav):
        if event.type == pygame.KEYDOWN:
            if self.status == 'idle':
                if event.key == pygame.K_RETURN:
                    self.start_read()
                elif event.key == pygame.K_BACKSPACE:
                    nav.pop()
            elif self.status == 'reading':
                pass  # block all input while reading
            elif self.status == 'done':
                if event.key == pygame.K_RETURN:
                    self._prompt_save()
                elif event.key == pygame.K_BACKSPACE:
                    nav.pop()
            elif self.status == 'error':
                if event.key == pygame.K_BACKSPACE:
                    nav.pop()
            # scroll log with up/down
            if event.key == pygame.K_DOWN:
                self.scroll = min(self.scroll + 1, max(0, len(self.log_lines) - 5))
            elif event.key == pygame.K_UP:
                self.scroll = max(self.scroll - 1, 0)
    def _prompt_save(self):
        # placeholder for now
        print("Save prompt here")

    def _draw_progress_bar(self, y):
        bar_x = 10
        bar_w = width - 20
        bar_h = 12
        # background
        pygame.draw.rect(screen, (60, 60, 60), (bar_x, y, bar_w, bar_h))
        # fill
        fill_w = int((self.progress / 100) * bar_w)
        pygame.draw.rect(screen, (0, 150, 255), (bar_x, y, fill_w, bar_h))
        # percentage text
        pct = header_font.render(f'{self.progress}%', True, (200, 200, 200))
        screen.blit(pct, (bar_x + bar_w // 2 - pct.get_width() // 2, y - 15))
        
    def draw(self):
        y = HEADER_HEIGHT + 10

        if self.status == 'idle':
            msg = header_font.render('Press ENTER to read chip', True, (200, 200, 200))
            screen.blit(msg, (10, y))

        elif self.status == 'reading':
            self._draw_progress_bar(y + 20)
            # log output below bar
            log_y = y + 50
            visible = self.log_lines[self.scroll:self.scroll + 5]
            for line in visible:
                surf = header_font.render(line, True, (150, 150, 150))
                screen.blit(surf, (10, log_y))
                log_y += 16

        elif self.status == 'done':
            msg = header_font.render('Read complete!', True, (0, 255, 0))
            screen.blit(msg, (10, y))
            self._draw_progress_bar(y + 20)
            hint = header_font.render('ENTER to save  BACKSPACE to go back', True, (150, 150, 150))
            screen.blit(hint, (10, y + 45))
            # show log
            log_y = y + 70
            visible = self.log_lines[self.scroll:self.scroll + 5]
            for line in visible:
                surf = header_font.render(line, True, (150, 150, 150))
                screen.blit(surf, (10, log_y))
                log_y += 16

        elif self.status == 'error':
            msg = header_font.render('Read failed!', True, (255, 0, 0))
            screen.blit(msg, (10, y))
            hint = header_font.render('BACKSPACE to go back', True, (150, 150, 150))
            screen.blit(hint, (10, y + 20))

class WriteScreen(Screen):
    def __init__(self, bin_path):
        super().__init__('Write', [])
        self.bin_path = bin_path       # full path to the .bin file selected from Bins
        self.status = 'confirm'        # confirm / backing_up / writing / done / error
        self.progress = 0
        self.log_lines = []
        self.scroll = 0

    def _run_backup_then_write(self):
        # --- backup step ---
        app_state['status'] = 'backup'
        self.status = 'backing_up'
        self.log_lines.append('Backing up current chip...')

        os.makedirs('saves/backups', exist_ok=True)
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
        backup_path = f'saves/backups/backup_{timestamp}.bin'

        # --- real flashrom (uncomment on Pi) ---
        backup_result = subprocess.run(
            ['flashrom', '-p', 'ch341a_spi', '-r', backup_path],
            capture_output=True, text=True
        )
        if backup_result.returncode != 0:
            self.status = 'error'
            app_state['status'] = 'error'
            self.log_lines.append('Backup failed, aborting write.')
            return

        # --- mock backup ---
        # time.sleep(1)
        # self.log_lines.append(f'Backup saved: {backup_path}')

        # --- write step ---
        app_state['status'] = 'writing'
        self.status = 'writing'
        self.log_lines.append(f'Writing {self.bin_path}...')

        # --- real flashrom (uncomment on Pi) ---
        process = subprocess.Popen(
            ['flashrom', '-p', 'ch341a_spi', '-w', self.bin_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        for line in process.stdout:
            self.log_lines.append(line.strip())
            if 'Writing' in line:
                try:
                    self.progress = int(line.split('%')[0].split()[-1])
                except:
                    pass
        process.wait()
        if process.returncode == 0:
            self.status = 'done'
            app_state['status'] = 'connected'
        else:
            self.status = 'error'
            app_state['status'] = 'error'

        # --- mock write ---
        # fake_lines = ['Erasing...', 'Writing... 25%', 'Writing... 50%', 'Writing... 75%', 'Writing... 100%', 'Verifying...', 'Done.']
        # for i, line in enumerate(fake_lines):
        #     time.sleep(0.5)
        #     self.log_lines.append(line)
        #     self.progress = int((i + 1) / len(fake_lines) * 100)

        # self.status = 'done'
        # app_state['status'] = 'connected'

    def start_write(self):
        thread = threading.Thread(target=self._run_backup_then_write)
        thread.daemon = True
        thread.start()

    def handle_input(self, event, nav):
        if event.type == pygame.KEYDOWN:
            if self.status == 'confirm':
                if event.key == pygame.K_RETURN:
                    self.start_write()
                elif self.status in ('done', 'error'):
                    if event.key == pygame.K_BACKSPACE:
                        nav.stack = [main_menu]   # clear stack, jump home
            elif self.status in ('backing_up', 'writing'):
                pass  # block input during the process
            elif self.status in ('done', 'error'):
                if event.key == pygame.K_BACKSPACE:
                    nav.pop()
            if event.key == pygame.K_DOWN:
                self.scroll = min(self.scroll + 1, max(0, len(self.log_lines) - 5))
            elif event.key == pygame.K_UP:
                self.scroll = max(self.scroll - 1, 0)

    def _draw_progress_bar(self, y):
        bar_x = 10
        bar_w = width - 20
        bar_h = 12
        pygame.draw.rect(screen, (60, 60, 60), (bar_x, y, bar_w, bar_h))
        fill_w = int((self.progress / 100) * bar_w)
        pygame.draw.rect(screen, (0, 150, 255), (bar_x, y, fill_w, bar_h))
        pct = header_font.render(f'{self.progress}%', True, (200, 200, 200))
        screen.blit(pct, (bar_x + bar_w // 2 - pct.get_width() // 2, y - 15))

    def _draw_log(self, y):
        visible = self.log_lines[self.scroll:self.scroll + 5]
        for line in visible:
            surf = header_font.render(line, True, (150, 150, 150))
            screen.blit(surf, (10, y))
            y += 16

    def draw(self):
        y = HEADER_HEIGHT + 10

        if self.status == 'confirm':
            msg = header_font.render(f'Write: {os.path.basename(self.bin_path)}', True, (200, 200, 200))
            screen.blit(msg, (10, y))
            warn = header_font.render('This will backup then overwrite the chip.', True, (255, 165, 0))
            screen.blit(warn, (10, y + 20))
            hint = header_font.render('ENTER to confirm  BACKSPACE to cancel', True, (150, 150, 150))
            screen.blit(hint, (10, y + 40))

        elif self.status == 'backing_up':
            msg = header_font.render('Backing up current chip...', True, (255, 255, 0))
            screen.blit(msg, (10, y))
            self._draw_log(y + 25)

        elif self.status == 'writing':
            self._draw_progress_bar(y + 5)
            self._draw_log(y + 30)

        elif self.status == 'done':
            msg = header_font.render('Write complete!', True, (0, 255, 0))
            screen.blit(msg, (10, y))
            self._draw_progress_bar(y + 20)
            hint = header_font.render('BACKSPACE to go back', True, (150, 150, 150))
            screen.blit(hint, (10, y + 40))
            self._draw_log(y + 60)

        elif self.status == 'error':
            msg = header_font.render('Write failed!', True, (255, 0, 0))
            screen.blit(msg, (10, y))
            hint = header_font.render('BACKSPACE to go back', True, (150, 150, 150))
            screen.blit(hint, (10, y + 20))
            self._draw_log(y + 40)

class ListScreen(Screen):
    def __init__(self, title, items, on_select):
        super().__init__(title, [])
        self.title = title
        self.list_items = items   # plain strings
        self.cursor = 0
        self.on_select = on_select  # function called with selected item

    def handle_input(self, event, nav):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self.cursor = (self.cursor + 1) % len(self.list_items)
            elif event.key == pygame.K_UP:
                self.cursor = (self.cursor - 1) % len(self.list_items)
            elif event.key == pygame.K_RETURN:
                self.on_select(self.list_items[self.cursor], nav)
            elif event.key == pygame.K_BACKSPACE:
                nav.pop()

    def draw(self):
        y = HEADER_HEIGHT + 10

        # title
        title_surf = header_font.render(self.title, True, (200, 200, 200))
        screen.blit(title_surf, (10, y))
        y += 20

        # divider
        pygame.draw.line(screen, (60, 60, 60), (10, y), (width - 10, y), 1)
        y += 8

        if not self.list_items:
            empty = header_font.render('Nothing here yet', True, (100, 100, 100))
            screen.blit(empty, (10, y))
            return

        # visible items (scroll window of 7)
        max_visible = 7
        start = max(0, self.cursor - max_visible // 2)
        visible = self.list_items[start:start + max_visible]

        for i, item in enumerate(visible):
            actual_index = start + i
            is_focused = actual_index == self.cursor
            color = (0, 255, 0) if is_focused else (200, 200, 200)
            prefix = '> ' if is_focused else '  '
            surf = header_font.render(prefix + item, True, color)
            screen.blit(surf, (10, y))
            y += 18

def make_bins_screen():
    brands = sorted([
        d for d in os.listdir(BINS_PATH)
        if os.path.isdir(os.path.join(BINS_PATH, d))
    ])
    return ListScreen('Bins', brands, on_brand_select)

def on_brand_select(brand, nav):
    brand_path = os.path.join(BINS_PATH, brand)
    models = sorted([
        d for d in os.listdir(brand_path)
        if os.path.isdir(os.path.join(brand_path, d))
    ])
    nav.push(ListScreen(brand, models,
        lambda model, nav: on_model_select(brand, model, nav)
    ))

def on_model_select(brand, model, nav):
    model_path = os.path.join(BINS_PATH, brand, model)
    files = sorted([
        f for f in os.listdir(model_path)
        if f.endswith('.bin')
    ])
    nav.push(ListScreen(model, files,
        lambda f, nav: on_file_select(brand, model, f, nav)
    ))

def on_file_select(brand, model, filename, nav):
    full_path = os.path.join(BINS_PATH, brand, model, filename)
    print(f'Viewing: {full_path}')  # placeholder until detail screen exists

def make_write_picker():
    chip = app_state['chip']
    matches = []

    for brand in os.listdir(BINS_PATH):
        brand_path = os.path.join(BINS_PATH, brand)
        if not os.path.isdir(brand_path):
            continue
        for model in os.listdir(brand_path):
            model_path = os.path.join(brand_path, model)
            if not os.path.isdir(model_path):
                continue
            for f in os.listdir(model_path):
                if f.endswith('.bin') and chip in f:
                    full_path = os.path.join(model_path, f)
                    matches.append((f'{brand}/{model}/{f}', full_path))

    if not matches:
        return ListScreen(f'No bins for {chip}', [], lambda item, nav: None)

    labels = [label for label, path in matches]
    paths = {label: path for label, path in matches}

    return ListScreen(f'Write: {chip}', labels,
        lambda label, nav: nav.push(WriteScreen(paths[label]))
    )

detect_screen = Screen('Detect', [])    # fill in later
read_screen = Screen('Read', [])
write_screen = Screen('Write', [])
bins_screen = Screen('Bins', [])

main_menu = Screen('Main Menu', [
    Button(10, 40, 300, 40, 'Detect', lambda nav: nav.push(DetectScreen())),
    Button(10, 90, 300, 40, 'Read', lambda nav: nav.push(ReadScreen()),
           enabled_check=lambda: app_state['chip'] is not None),
    Button(10, 140, 300, 40, 'Write', lambda nav: nav.push(make_write_picker()),
           enabled_check=lambda: app_state['chip'] is not None),
    Button(10, 190, 300, 40, 'Bins', lambda nav: nav.push(make_bins_screen())),
])

nav = Navigator(main_menu)

while running:
    screen.fill((20, 20, 20))
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                statuses = ['idle', 'connected', 'reading', 'writing', 'backup', 'error']
                current = statuses.index(app_state['status'])
                app_state['status'] = statuses[(current + 1) % len(statuses)]
        nav.current().handle_input(event, nav)

    nav.current().draw()
    draw_header()
    pygame.display.flip()
    clock.tick(fps)
pygame.quit()
