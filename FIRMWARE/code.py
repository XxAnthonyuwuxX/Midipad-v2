import board
import busio
import time
from kmk.kmk_keyboard import KMKKeyboard
from kmk.scanners.keypad import MatrixScanner
from kmk.keys import KC
from kmk.modules.encoder import EncoderHandler
from kmk.extensions.media_keys import MediaKeys
import usb_midi
import adafruit_midi
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff
import neopixel

pixels = neopixel.NeoPixel(board.D9, 12, brightness=0.3, auto_write=False)

COLOR_OFF = (0, 0, 0)
COLOR_ACTIVE = (0, 255, 0)
COLOR_OCTAVE_DOWN = (255, 0, 0)
COLOR_OCTAVE_UP = (0, 0, 255)
COLOR_MODE = (255, 255, 0)
COLOR_ARPEG = (255, 0, 255)

midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=0)

keyboard = KMKKeyboard()

encoder_handler = EncoderHandler()
keyboard.modules.append(encoder_handler)

keyboard.extensions.append(MediaKeys())

ROWS = (board.D0, board.D1, board.D2, board.D3)
COLS = (board.D4, board.D5, board.D6)

keyboard.matrix = MatrixScanner(
    rows=ROWS,
    cols=COLS,
    pulldown=True,
)

encoder_handler.pins = ((board.D7, board.D8, board.D10),)
encoder_handler.map = [
    (KC.AUDIO_VOL_UP, KC.AUDIO_VOL_DOWN),
]

octave = 4
mode = 0
arpeggiator_active = False
arpeg_notes = []
arpeg_index = 0
arpeg_speed = 100

note_map = {
    0: 60, 1: 62, 2: 64, 3: 65, 4: 67,
    5: 69, 6: 71, 7: 72, 8: 74,
    9: -1, 10: -1, 11: -1,
}

last_arpeg_time = time.monotonic()

def send_note_on(note_number):
    midi.send(NoteOn(note_number, 100))

def send_note_off(note_number):
    midi.send(NoteOff(note_number, 0))

def update_leds():
    pixels.fill(COLOR_OFF)
    
    for i in range(9):
        pixels[i] = COLOR_ACTIVE
    
    pixels[9] = COLOR_OCTAVE_DOWN
    
    if arpeggiator_active:
        pixels[10] = COLOR_ARPEG
    else:
        pixels[10] = COLOR_MODE
    
    pixels[11] = COLOR_OCTAVE_UP
    
    pixels.show()

def toggle_arpeggiator():
    global arpeggiator_active
    arpeggiator_active = not arpeggiator_active
    update_leds()

def increase_octave():
    global octave
    if octave < 8:
        octave += 1

def decrease_octave():
    global octave
    if octave > 0:
        octave -= 1

def toggle_mode():
    global mode
    mode = (mode + 1) % 2

def handle_button_press(button_index):
    if button_index < 9:
        note = note_map[button_index] + (octave - 4) * 12
        send_note_on(note)
        
        if arpeggiator_active:
            arpeg_notes.append(note)
    
    elif button_index == 9:
        decrease_octave()
    
    elif button_index == 10:
        toggle_arpeggiator()
    
    elif button_index == 11:
        increase_octave()

def handle_button_release(button_index):
    if button_index < 9:
        note = note_map[button_index] + (octave - 4) * 12
        send_note_off(note)

def process_arpeggiator():
    global arpeg_index, last_arpeg_time, arpeg_notes
    
    if not arpeggiator_active or not arpeg_notes:
        return
    
    current_time = time.monotonic()
    if current_time - last_arpeg_time > (arpeg_speed / 1000.0):
        if arpeg_index < len(arpeg_notes):
            send_note_on(arpeg_notes[arpeg_index])
            arpeg_index += 1
        else:
            arpeg_index = 0
        
        last_arpeg_time = current_time

keyboard.keymap = [
    [
        KC.NO, KC.NO, KC.NO,
        KC.NO, KC.NO, KC.NO,
        KC.NO, KC.NO, KC.NO,
        KC.NO, KC.NO, KC.NO,
    ],
]

original_process_key = keyboard.process_key

def custom_process_key(key, is_pressed, int_coord):
    row, col = int_coord
    button_index = row * 3 + col
    
    if is_pressed:
        handle_button_press(button_index)
    else:
        handle_button_release(button_index)

keyboard.process_key = custom_process_key

update_leds()

if __name__ == '__main__':
    try:
        while True:
            keyboard.scan_matrix()
            process_arpeggiator()
            time.sleep(0.01)
    except KeyboardInterrupt:
        pixels.fill(COLOR_OFF)
        pixels.show()