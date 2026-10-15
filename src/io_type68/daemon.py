# SPDX-License-Identifier: GPL-3.0-or-later
import json
import signal
import time
from .core import Keyboard, KeyboardEffects, snapshot, apply, validate_request
BUS = 'local.io.Keyboard'  # Compatible with the original KDE brightness extension.
PATH = '/local/io/Keyboard'

def main():
    import dbus
    import dbus.service
    from dbus.mainloop.glib import DBusGMainLoop
    from gi.repository import GLib
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()
    name = dbus.service.BusName(BUS, bus, do_not_queue=True)
    loop = GLib.MainLoop()
    effects = KeyboardEffects()
    cached = None
    source = None

    def state(full=False):
        nonlocal cached
        try:
            with Keyboard() as keyboard:
                cached = snapshot(keyboard, None if full else cached)
            result = dict(cached, lighting=dict(cached['lighting']))
            if effects.mode != 'none':
                result['lighting'].update(color=effects.color, speed=effects.speed)
        except Exception as exc:
            cached = None
            result = dict(connected=False, error=str(exc))
        result['effect'] = effects.status()
        return result

    def pump():
        nonlocal source
        source = None
        started = time.monotonic()
        effects.tick()
        if effects.mode != 'none':
            source = GLib.timeout_add(max(1, round((1/30-(time.monotonic()-started))*1000)), pump)
        else:
            bridge.changed()
        return False

    class Bridge(dbus.service.Object):
        @dbus.service.signal('org.freedesktop.DBus.Properties', signature='sa{sv}as')
        def PropertiesChanged(self, iface, changed, invalidated): pass

        def changed(self):
            result = state()
            self.PropertiesChanged(BUS, {'State': json.dumps(result)}, [])
            return result

        @dbus.service.method('org.freedesktop.DBus.Properties', in_signature='s', out_signature='a{sv}')
        def GetAll(self, iface):
            return {'State': json.dumps(state())} if iface == BUS else {}

        @dbus.service.method('org.freedesktop.DBus.Properties', in_signature='ss', out_signature='v')
        def Get(self, iface, prop):
            if iface != BUS or prop != 'State':
                raise dbus.exceptions.DBusException('Unknown property', name='org.freedesktop.DBus.Error.UnknownProperty')
            return json.dumps(state())

        @dbus.service.method(BUS, in_signature='', out_signature='s')
        def Snapshot(self): return json.dumps(state())

        @dbus.service.method(BUS, in_signature='', out_signature='s')
        def RefreshKeys(self): return json.dumps(state(True))

        @dbus.service.method(BUS, in_signature='s', out_signature='s')
        def Apply(self, text):
            nonlocal cached, source
            try:
                if len(text) > 16384: raise ValueError('Request too large')
                request = json.loads(text)
                validate_request(request)
                kind = request['kind']
                if kind == 'effect':
                    effects.configure(request['values'])
                    if source is None and effects.mode != 'none': source = GLib.timeout_add(1, pump)
                else:
                    patch = dict(request['values'])
                    if kind == 'lighting' and effects.mode != 'none':
                        if 'mode' in patch or request.get('selected'):
                            effects.stop()
                        else:
                            effect_patch = {key: patch.pop(key) for key in ('color', 'speed') if key in patch}
                            if effect_patch: effects.configure(effect_patch)
                    if patch:
                        with Keyboard() as keyboard: apply(keyboard, dict(request, values=patch))
                        cached = None
                        if effects.saved_led is not None and kind == 'lighting' and 'brightness' in patch:
                            effects.saved_led[9] = patch['brightness']
                result = state(kind in ('keys', 'deadzone'))
                self.PropertiesChanged(BUS, {'State': json.dumps(result)}, [])
                return json.dumps(dict(ok=True, state=result))
            except Exception as exc:
                return json.dumps(dict(ok=False, error=str(exc)))

    bridge = Bridge(name, PATH)
    def stop():
        loop.quit()
        return False
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, stop)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, stop)
    try: loop.run()
    finally:
        try: effects.stop()
        finally: Keyboard.close_shared()

if __name__ == '__main__': main()
