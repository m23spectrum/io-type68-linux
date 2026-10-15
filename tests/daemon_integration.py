# SPDX-License-Identifier: GPL-3.0-or-later
"""Run with dbus-run-session; uses an in-memory device, never real HID."""
import json
import subprocess
import sys
import time
from pathlib import Path

if '--daemon' in sys.argv:
    from test_core import MemoryDevice
    import io_type68.core as core
    import io_type68.daemon as daemon
    device = MemoryDevice()
    device.blocks[0x10][8:10] = bytes([0x37, 1])
    class FakeKeyboard:
        def __enter__(self): return device
        def __exit__(self, *args): pass
        @classmethod
        def close_shared(cls): pass
    core.Keyboard = daemon.Keyboard = FakeKeyboard
    daemon.main()
else:
    import dbus
    child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--daemon'])
    try:
        bus = dbus.SessionBus()
        for _ in range(100):
            if child.poll() is not None: raise RuntimeError('Daemon exited')
            if bus.name_has_owner('local.io.Keyboard'): break
            time.sleep(.02)
        obj = bus.get_object('local.io.Keyboard','/local/io/Keyboard')
        bridge = dbus.Interface(obj,'local.io.Keyboard')
        state = json.loads(bridge.Snapshot())
        assert state['connected'] and state['firmware'] == '1.37'
        result = json.loads(bridge.Apply(json.dumps({'kind':'keys','selected':[34],'values':{'trigger':.2,'rapid':True,'press':.1,'release':.15}})))
        assert result['ok']
        key = next(k for row in result['state']['keys'] for k in row if k['value']==34)
        assert key['trigger']==.2 and key['rapid']
        invalid=json.loads(bridge.Apply(json.dumps({'kind':'deadzone','values':{'oops':2}})))
        assert not invalid['ok']
        assert json.loads(bridge.Apply(json.dumps({'kind':'effect','values':{'mode':'rainbow'}})))['ok']
        time.sleep(.12)
        assert json.loads(bridge.Snapshot())['effect']['frames']>0
        # A global color update must preserve a running host effect.
        result=json.loads(bridge.Apply(json.dumps({'kind':'lighting','values':{'color':'#123456'}})))
        assert result['ok'] and result['state']['effect']['mode']=='rainbow'
        assert result['state']['lighting']['color']=='#123456'
        assert json.loads(bridge.Apply(json.dumps({'kind':'effect','values':{'mode':'none'}})))['ok']
        props = dbus.Interface(obj,'org.freedesktop.DBus.Properties')
        assert json.loads(str(props.Get('local.io.Keyboard','State')))['connected']
        print('Isolated D-Bus daemon integration: PASS (simulated hardware)')
    finally:
        child.terminate()
        try: child.wait(timeout=5)
        except subprocess.TimeoutExpired: child.kill(); child.wait(); raise
