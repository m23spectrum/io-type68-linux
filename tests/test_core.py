# SPDX-License-Identifier: GPL-3.0-or-later
import json
import struct
import unittest
from unittest.mock import patch
from io_type68.core import Keyboard, KeyboardEffects, SmoothBrightness, apply, ROOT, validate_request
from io_type68.cli import key_ids

class MemoryDevice:
    def __init__(self):
        self.blocks = {0x10: bytearray(48), 0x13: bytearray(16), 0x14: bytearray(512), 0x17: bytearray((i*7)%256 for i in range(1024)), 0x11: bytearray(56)}
        self.writes = []
        self.blocks[0x13][10] = 3
    def read(self, cmd, size): return bytearray(self.blocks[cmd])
    def transfer(self, cmd, size, data): self.writes.append((cmd, bytes(data)))
    def write_checked(self, write, read, payload, normalized=None):
        self.writes.append((write, bytes(payload))); self.blocks[read] = bytearray(payload)

class CoreTests(unittest.TestCase):
    def test_smooth_brightness_preserves_per_key_colors_and_uses_volatile_frames(self):
        device = MemoryDevice()
        device.blocks[0x13][0] = 20
        device.blocks[0x13][9] = 5
        for key, rgb in ((34, (200, 100, 50)), (49, (10, 20, 30))):
            device.blocks[0x14][key*4:key*4+4] = bytes([key, *rgb])
        original = bytes(device.blocks[0x14])
        smooth = SmoothBrightness()
        smooth.set(device, 50)
        frame = device.writes[-1][1]
        entries = {frame[i]: frame[i+1:i+4] for i in range(0, len(frame), 4)}
        self.assertEqual(entries[34], bytes([100, 50, 25]))
        self.assertEqual(entries[49], bytes([5, 10, 15]))
        self.assertEqual(bytes(device.blocks[0x14]), original)
        smooth.set(device, 100)
        self.assertTrue(all(cmd == 0x32 for cmd, _ in device.writes))
        self.assertEqual(smooth.level, 100)
        smooth.reset()
        self.assertIsNone(smooth.level)

    def test_smooth_brightness_rejects_invalid_values_and_builtin_effects(self):
        device = MemoryDevice(); smooth = SmoothBrightness()
        for value in (-1, 101, True, 1.5):
            with self.assertRaises(ValueError): smooth.set(device, value)
        with self.assertRaises(ValueError): smooth.set(device, 50)
        self.assertEqual(device.writes, [])

    def test_smooth_brightness_sets_full_hardware_level_once(self):
        device = MemoryDevice(); device.blocks[0x13][0] = 20; device.blocks[0x13][9] = 2
        smooth = SmoothBrightness(); smooth.set(device, 50); smooth.set(device, 75)
        self.assertEqual([cmd for cmd, _ in device.writes], [0x23, 0x32, 0x32])
        self.assertEqual(device.blocks[0x13][9], 5)

    def test_magnetic_preserves_unselected_and_flag_bits(self):
        d = MemoryDevice(); original = bytes(d.blocks[0x17]); d.blocks[0x10][29]=2
        apply(d, {'kind':'keys','selected':[34], 'values':{'trigger':.1,'rapid':True,'press':.12,'release':3.2}})
        actual = d.blocks[0x17]; offset=34*8
        self.assertEqual(actual[:offset], original[:offset]); self.assertEqual(actual[offset+8:],original[offset+8:])
        self.assertEqual(actual[offset],original[offset]); self.assertEqual(actual[offset+1],original[offset+1]|1)
        self.assertEqual(struct.unpack_from('<HHH',actual,offset+2),(100,120,3200))
    def test_invalid_mixed_request_has_no_side_effect(self):
        d=MemoryDevice()
        for request in [
            {'kind':'lighting','values':{'color':'#112233','brightness':6}},
            {'kind':'keys','selected':[34], 'values':{'trigger':float('nan')}},
            {'kind':'deadzone','values':{'unknown':1}},
            {'kind':'lighting','values':{'color':'#112233'},'selected':[127]},
            {'kind':'lighting','values':{'brightness':True}},
        ]:
            with self.assertRaises(ValueError): apply(d,request)
        self.assertEqual(d.writes,[])
    def test_selected_color_preserves_other_slots(self):
        d=MemoryDevice(); original=bytes(d.blocks[0x14])
        apply(d,{'kind':'lighting','selected':[34], 'values':{'color':'#123456'}})
        actual=d.blocks[0x14]
        self.assertEqual(actual[:136],original[:136]); self.assertEqual(actual[140:],original[140:])
        self.assertEqual(actual[136:140],bytes([34,0x12,0x34,0x56]))
        self.assertEqual([cmd for cmd,_ in d.writes],[0x32,0x24,0x23])
    def test_deadzone_preserves_unrelated_bytes(self):
        d=MemoryDevice(); d.blocks[0x11]=bytearray(range(56)); before=bytes(d.blocks[0x11])
        apply(d,{'kind':'deadzone','values':{'topDeadZone':.25}})
        after=d.blocks[0x11]; self.assertEqual(after[8],25)
        self.assertEqual(after[:8]+after[9:],before[:8]+before[9:])
    def test_effects_are_volatile_frames(self):
        effect=KeyboardEffects(); ids=[k['value'] for row in json.loads((ROOT/'keys.json').read_text()) for k in row]
        self.assertEqual(len(ids),68); self.assertEqual(len(set(ids)),68)
        for mode in effect.MODES[1:]:
            effect.mode=mode
            a=effect.frame(0); b=effect.frame(1.37)
            self.assertEqual(len(a),272); self.assertEqual(list(a[::4]),ids); self.assertNotEqual(a,b)
            device=MemoryDevice()
            with patch.object(Keyboard,'__enter__',return_value=device), patch.object(Keyboard,'__exit__',return_value=None): effect.tick()
            self.assertEqual([cmd for cmd,_ in device.writes],[0x32])
    def test_cli_key_selection(self):
        self.assertEqual(key_ids('wasd'),[34,49,50,51]); self.assertEqual(len(key_ids('all')),68)
        with self.assertRaises(ValueError): key_ids('unknown')
    def test_packet_chunking(self):
        device=Keyboard(); device.fd=99; packets=[]; responses=[]
        def write(fd,packet):
            packets.append(bytes(packet)); count=packet[3]; addr=int.from_bytes(packet[4:6],'little')
            responses.append(bytes([0x55,0x17,count,addr&255,addr>>8,0,0,0])+bytes([addr//56])*count)
            return len(packet)
        def ready(*args): return ([99],[],[]) if args[3] and responses else ([],[],[])
        with patch('io_type68.core.os.write',side_effect=write), patch('io_type68.core.os.read',side_effect=lambda *_: responses.pop(0)), patch('io_type68.core.select.select',side_effect=ready):
            result=device.read(0x17,1024)
        self.assertEqual(len(packets),19); self.assertTrue(all(len(p)==65 and p[0]==0 for p in packets))
        self.assertEqual(packets[-1][3],16); self.assertEqual(packets[-1][7],1); self.assertEqual(len(result),1024)
        self.assertTrue(all(p[7]==0 for p in packets[:-1]))
    def test_disallowed_command(self):
        with self.assertRaises(ValueError): Keyboard().transfer(0xff,16)

if __name__ == '__main__': unittest.main()
