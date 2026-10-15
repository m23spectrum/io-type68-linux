# SPDX-License-Identifier: GPL-3.0-or-later
"""Reverse-engineered userspace HID protocol for IO Type 68 Magnetic."""
import colorsys
import fcntl
import json
import math
import os
import re
import select
import struct
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parent

def checked_color(color):
    if not isinstance(color, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
        raise ValueError('Цвет должен иметь вид #RRGGBB')
    return color.lower()


class KeyboardEffects:
    MODES = ('none', 'aurora', 'breathing', 'comet', 'rainbow')

    def __init__(self):
        self.mode = 'none'
        self.color = '#800020'
        self.speed = 3
        self.error = ''
        self.saved_led = None
        self.started = 0
        self.frames = 0
        self.positions = [(key['value'], col / max(1, len(row)-1), y / 4) for y, row in enumerate(json.loads((ROOT/'keys.json').read_text())) for col, key in enumerate(row)]

    def configure(self, values):
        mode = values.get('mode', self.mode)
        if mode not in self.MODES:
            raise ValueError('Неизвестный программный эффект')
        color = checked_color(values.get('color', self.color))
        speed = bounded(values.get('speed', self.speed), 1, 5)
        if mode == 'none':
            self.stop()
        elif self.mode == 'none':
            with Keyboard() as k:
                self.saved_led = k.read(0x13, 16)
            self.started = time.monotonic()
            self.frames = 0
        self.mode, self.color, self.speed, self.error = mode, color, speed, ''

    def stop(self):
        self.mode = 'none'
        saved, self.saved_led = self.saved_led, None
        if saved is not None:
            with Keyboard() as k:
                apply(k, {'kind': 'lighting', 'values': {'mode': 128 if saved[0] == 20 else saved[0], 'brightness': saved[9], 'speed': saved[10], 'direction': saved[11]}})

    def frame(self, elapsed):
        rgb = tuple(int(self.color[i:i+2],16)/255 for i in (1,3,5))
        hue, saturation, value = colorsys.rgb_to_hsv(*rgb)
        phase = elapsed * self.speed / 3
        result = bytearray()
        for key, x, y in self.positions:
            if self.mode == 'breathing':
                gain = .08 + .92 * (.5 - .5 * math.cos(phase * math.tau / 5))
                color = tuple(c*gain for c in rgb)
            elif self.mode == 'comet':
                head = (phase / 3) % 1.6 - .3
                gain = .035 + .965 * math.exp(-((x-head)/.18)**2)
                color = tuple(c*gain for c in rgb)
            elif self.mode == 'rainbow':
                color = colorsys.hsv_to_rgb((x*.75+y*.12+phase*.08)%1, .95, value)
            else:
                wave = .5+.5*math.sin(x*5+y*2-phase*1.1)
                color = colorsys.hsv_to_rgb((hue+.10*math.sin(x*3-y*2+phase*.6))%1, max(.55,saturation), value*(.18+.82*wave))
            result.extend([key, *(max(0,min(255,round(c*255))) for c in color)])
        return result

    def tick(self):
        if self.mode != 'none':
            try:
                frame = self.frame(time.monotonic()-self.started)
                with Keyboard() as k:
                    # Vendor setMusicData USB route: volatile 0x32, no 0x24/flash writes.
                    k.transfer(0x32, len(frame), frame)
                self.frames += 1
            except Exception as exc:
                self.error = str(exc)
                try:
                    self.stop()
                except Exception:
                    self.error += '; не удалось восстановить встроенный эффект'
        return True

    def status(self):
        return dict(mode=self.mode, color=self.color, speed=self.speed, error=self.error, frames=self.frames)


class Keyboard:
    _cached_device = None
    _shared_fd = None

    @classmethod
    def close_shared(cls):
        if cls._shared_fd is not None:
            os.close(cls._shared_fd)
        cls._shared_fd = None
        cls._cached_device = None

    def __enter__(self):
        runtime = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}'))
        self._lock = os.open(runtime / 'io-type68.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(self._lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return self._open()
        except BaseException:
            os.close(self._lock)
            raise

    def _open(self):
        if Keyboard._cached_device:
            entry, generation = Keyboard._cached_device
            try:
                if os.readlink(entry / 'device') == generation:
                    self.fd = Keyboard._shared_fd
                    return self
            except OSError:
                pass
            Keyboard.close_shared()
        for entry in Path('/sys/class/hidraw').glob('*'):
            try:
                info = (entry / 'device/uevent').read_text()
                descriptor = (entry / 'device/report_descriptor').read_bytes()
            except FileNotFoundError:
                continue
            if 'HID_ID=0003:00000C45:00000256' not in info:
                continue
            if descriptor.startswith(bytes.fromhex('0668ff')):
                self.fd = os.open('/dev/' + entry.name, os.O_RDWR | os.O_NONBLOCK)
                Keyboard._shared_fd = self.fd
                Keyboard._cached_device = (entry, os.readlink(entry / 'device'))
                return self
        raise RuntimeError('Клавиатура IO Type 68 Magnetic не подключена')

    def __exit__(self, *args):
        # The bridge serializes all HID operations on its main loop. Keeping
        # the vendor interface open avoids its costly first-open activation.
        try:
            if args and args[0] and issubclass(args[0], OSError):
                Keyboard.close_shared()
        finally:
            os.close(self._lock)

    def transfer(self, cmd, size, data=None):
        if type(cmd) is not int or cmd not in (0x10, 0x11, 0x13, 0x14, 0x17, 0x21, 0x23, 0x24, 0x27, 0x32):
            raise ValueError('Unsupported HID command')
        if type(size) is not int or not 1 <= size <= 1024 or (data is not None and len(data) != size):
            raise ValueError('Invalid report size')
        result = bytearray()
        for addr in range(0, size, 56):
            count = min(56, size - addr)
            packet = bytearray(65)  # hidraw requires report ID zero before the 64-byte report
            packet[1:9] = bytes([0xAA, cmd, count, addr & 255, addr >> 8, 0, int(addr + count == size), 0])
            if data is not None:
                packet[9:9 + count] = data[addr:addr + count]
            while select.select([self.fd], [], [], 0)[0]:
                os.read(self.fd, 1024)
            if os.write(self.fd, packet) != len(packet):
                raise RuntimeError('Short HID write')
            deadline = time.monotonic() + 2
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not select.select([self.fd], [], [], remaining)[0]:
                    raise RuntimeError(f'Нет ответа USB: команда {cmd:02x}, адрес {addr}')
                response = os.read(self.fd, 1024)
                if len(response) >= 8 and response[:2] == bytes([0x55, cmd]) and int.from_bytes(response[3:5], 'little') == addr:
                    break
            if len(response) < 8 + count:
                raise RuntimeError('Неполный ответ клавиатуры')
            result.extend(response[8:8 + count])
        return result

    def read(self, cmd, size):
        return self.transfer(cmd, size)

    def write_checked(self, write_cmd, read_cmd, payload, normalized=None):
        self.transfer(write_cmd, len(payload), payload)
        actual = self.read(read_cmd, len(payload))
        if normalized:
            if normalized(actual) != normalized(payload):
                raise RuntimeError('Проверка сохранённых настроек не прошла')
        elif actual != payload:
            raise RuntimeError('Проверка сохранённых настроек не прошла')
        return actual


def bounded(value, lo, hi):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not lo <= value <= hi:
        raise ValueError(f'Значение должно быть от {lo} до {hi}')
    return value


def snapshot(k, previous=None):
    info = k.read(0x10, 48) if previous is None else None
    led = k.read(0x13, 16)
    mode = 128 if led[0] == 20 else led[0]
    if mode == 128:
        if previous and previous['lighting']['mode'] == mode and previous['lighting'].get('color'):
            color = previous['lighting']['color']
        else:
            color = '#' + k.read(0x14, 512)[1:4].hex()
    else:
        color = '#' + led[1:4].hex()
    if previous is None:
        rt, game = k.read(0x17, 1024), k.read(0x11, 56)
        precision = info[29]
        trigger_scale, rt_scale = (1000 if precision == 2 else 100), (1000 if precision > 0 else 100)
        keys = json.loads((ROOT / 'keys.json').read_text())
        for row in keys:
            for key in row:
                axis, flags, trigger, press, release = struct.unpack_from('<BBHHH', rt, key['value'] * 8)
                key.update(trigger=trigger / trigger_scale, rapid=bool(flags & 1), press=press / rt_scale, release=release / rt_scale)
        result = dict(connected=True, firmware=f'{((info[8] & 15) + (info[8] >> 4) * 10 + info[9] * 100) / 100:.2f}', keys=keys, topDeadZone=game[8]/100, bottomDeadZone=game[9]/100)
    else:
        result = dict(previous)
    result['lighting'] = dict(mode=mode, color=color, colorMode=led[8], brightness=led[9], speed=led[10], direction=led[11])
    return result


def apply(k, request):
    validate_request(request)
    kind = request['kind']
    if kind == 'lighting':
        data = k.read(0x13, 16)
        if data[0] == 20:
            data[0] = 128
        fields = {'mode': (0, 0, 128), 'brightness': (9, 0, 5), 'speed': (10, 1, 5), 'direction': (11, 0, 3)}
        patch = request['values']
        if set(patch) - set(fields) - {'color'}:
            raise ValueError('Неизвестный параметр подсветки')
        for name, (offset, lo, hi) in fields.items():
            if name in patch:
                value = bounded(patch[name], lo, hi)
                if int(value) != value or (name == 'mode' and value not in list(range(20)) + [128]):
                    raise ValueError('Недопустимый режим')
                data[offset] = int(value)
        if 'color' in patch:
            color = checked_color(patch['color'])
            if not isinstance(color, str) or len(color) != 7 or color[0] != '#':
                raise ValueError('Цвет должен иметь вид #RRGGBB')
            rgb = bytes.fromhex(color[1:])
            if len(rgb) != 3:
                raise ValueError('Цвет должен содержать ровно три байта RGB')
            selected = request.get('selected') or [x['value'] for row in json.loads((ROOT / 'keys.json').read_text()) for x in row]
            valid = {x['value'] for row in json.loads((ROOT / 'keys.json').read_text()) for x in row}
            if any(type(x) is not int or x not in valid for x in selected):
                raise ValueError('Неизвестная клавиша')
            whole_keyboard = set(selected) == valid
            if whole_keyboard:
                frame = bytearray(v for key in sorted(valid) for v in (key, *rgb))
                k.transfer(0x32, len(frame), frame)
            custom = k.read(0x14, 512)
            for key in selected:
                custom[key * 4:key * 4 + 4] = bytes([key]) + rgb
            # Update the visible frame immediately; save and verify the same
            # colors afterward rather than waiting for the whole table roundtrip.
            if not whole_keyboard:
                frame = bytearray(v for key in sorted(valid) for v in (key, *custom[key*4+1:key*4+4]))
                k.transfer(0x32, len(frame), frame)
            k.write_checked(0x24, 0x14, custom)
            data[0] = 128
        data[4], data[14], data[15] = 255, 170, 85
        # 1.37 accepts mode/brightness/speed/direction here, but rewrites RGB.
        # Arbitrary RGB uses the separately verified per-key table, mode 128.
        k.write_checked(0x23, 0x13, data, lambda v: bytes([128 if v[0] == 20 else v[0], v[9], v[10], v[11]]))
    elif kind == 'keys':
        valid = {x['value'] for row in json.loads((ROOT / 'keys.json').read_text()) for x in row}
        selected = request['selected']
        if not selected or any(type(x) is not int or x not in valid for x in selected):
            raise ValueError('Выберите клавиши')
        patch = request['values']
        if set(patch) - {'trigger', 'rapid', 'press', 'release'}:
            raise ValueError('Неизвестный параметр магнитных клавиш')
        for name in ('trigger', 'press', 'release'):
            if name in patch:
                bounded(patch[name], .1, 3.2)
        if 'rapid' in patch and type(patch['rapid']) is not bool:
            raise ValueError('Rapid Trigger должен быть логическим значением')
        info = k.read(0x10, 48)
        data = k.read(0x17, 1024)
        for key in selected:
            offset = key * 8
            if 'rapid' in patch:
                data[offset + 1] = (data[offset + 1] & ~1) | int(patch['rapid'])
            for name, position, scale in [('trigger', 2, 1000 if info[29] == 2 else 100), ('press', 4, 1000 if info[29] else 100), ('release', 6, 1000 if info[29] else 100)]:
                if name in patch:
                    struct.pack_into('<H', data, offset + position, round(patch[name] * scale))
        k.write_checked(0x27, 0x17, data)
    elif kind == 'deadzone':
        data = k.read(0x11, 56)
        for name, offset in [('topDeadZone', 8), ('bottomDeadZone', 9)]:
            if name in request['values']:
                data[offset] = round(bounded(request['values'][name], 0, .5) * 100)
        k.write_checked(0x21, 0x11, data)
    else:
        raise ValueError('Неизвестная операция')



def validate_request(request):
    """Reject invalid input before touching hardware, including mixed patches."""
    if not isinstance(request, dict) or set(request) - {'kind', 'values', 'selected'}:
        raise ValueError('Expected kind, values and optional selected')
    kind, values = request.get('kind'), request.get('values')
    fields = {'lighting': {'mode', 'brightness', 'speed', 'direction', 'color'},
              'keys': {'trigger', 'rapid', 'press', 'release'},
              'deadzone': {'topDeadZone', 'bottomDeadZone'},
              'effect': {'mode', 'color', 'speed'}}
    if kind not in fields or not isinstance(values, dict) or not values or set(values) - fields[kind]:
        raise ValueError('Unknown operation or empty/unknown settings')
    valid = {key['value'] for row in json.loads((ROOT/'keys.json').read_text()) for key in row}
    selected = request.get('selected', [])
    if not isinstance(selected, list) or any(type(x) is not int or x not in valid for x in selected):
        raise ValueError('Invalid key selection')
    if kind == 'keys' and not selected:
        raise ValueError('Select at least one key')
    for name, value in values.items():
        if name == 'color': checked_color(value)
        elif name == 'rapid':
            if type(value) is not bool: raise ValueError('rapid must be boolean')
        elif name == 'mode' and kind == 'effect':
            if value not in KeyboardEffects.MODES: raise ValueError('Unknown effect')
        elif name in ('trigger', 'press', 'release'): bounded(value, .1, 3.2)
        elif name in ('topDeadZone', 'bottomDeadZone'): bounded(value, 0, .5)
        else:
            limits = {'mode': (0, 128), 'brightness': (0, 5), 'speed': (1, 5), 'direction': (0, 3)}
            bounded(value, *limits[name])
            if type(value) is not int: raise ValueError('Expected integer')
            if name == 'mode' and value not in (*range(20), 128): raise ValueError('Unknown mode')
