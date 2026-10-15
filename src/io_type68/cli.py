# SPDX-License-Identifier: GPL-3.0-or-later
"""All operations use the daemon; no competing HID connection."""
import argparse
import json
import sys
from .core import ROOT, validate_request

def key_ids(selection):
    keys = [key for row in json.loads((ROOT/'keys.json').read_text()) for key in row]
    if selection == 'all': return [key['value'] for key in keys]
    if selection.lower() == 'wasd': selection = 'KeyW,KeyA,KeyS,KeyD'
    mapping = {key['key'].lower(): key['value'] for key in keys}
    mapping.update({key['name'].split()[0].lower(): key['value'] for key in keys})
    result = []
    for item in selection.split(','):
        if item.lower() in mapping: result.append(mapping[item.lower()])
        elif item.isdigit() and int(item) in mapping.values(): result.append(int(item))
        else: raise ValueError(f'Unknown key: {item}')
    return result

def main():
    parser = argparse.ArgumentParser(description='IO Type 68 Magnetic userspace driver')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('status')
    sub.add_parser('refresh')
    light = sub.add_parser('lighting')
    for flag in ('brightness', 'mode', 'speed', 'direction'): light.add_argument('--'+flag, type=int)
    light.add_argument('--color'); light.add_argument('--keys', default='all')
    keys = sub.add_parser('keys')
    keys.add_argument('--keys', default='all')
    for flag in ('trigger', 'press', 'release'): keys.add_argument('--'+flag, type=float)
    keys.add_argument('--rapid', choices=('on','off'))
    dead = sub.add_parser('deadzone')
    dead.add_argument('--top', type=float); dead.add_argument('--bottom', type=float)
    effect = sub.add_parser('effect')
    effect.add_argument('mode', choices=('none','aurora','breathing','comet','rainbow'))
    effect.add_argument('--color'); effect.add_argument('--speed', type=int)
    raw = sub.add_parser('apply'); raw.add_argument('json', help='Validated JSON request (not raw HID)')
    args = vars(parser.parse_args()); command = args.pop('command')
    try:
        if command not in ('status','refresh'):
            if command == 'apply': request = json.loads(args['json'])
            else:
                selected = key_ids(args.pop('keys')) if 'keys' in args else []
                if command == 'lighting' and len(selected) == 68: selected = []
                if command == 'deadzone': args = {'topDeadZone': args['top'], 'bottomDeadZone': args['bottom']}
                if args.get('rapid') is not None: args['rapid'] = args['rapid'] == 'on'
                request = {'kind': command, 'values': {k:v for k,v in args.items() if v is not None}, 'selected': selected}
            validate_request(request)
        import dbus
        interface = dbus.Interface(dbus.SessionBus().get_object('local.io.Keyboard', '/local/io/Keyboard'), 'local.io.Keyboard')
        if command == 'status': result = json.loads(interface.Snapshot())
        elif command == 'refresh': result = json.loads(interface.RefreshKeys())
        else: result = json.loads(interface.Apply(json.dumps(request), timeout=60))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get('ok', result.get('connected', False)) else 1
    except Exception as exc:
        print(str(exc), file=sys.stderr); return 1

if __name__ == '__main__': sys.exit(main())
