#!/usr/bin/env python3
"""Owned, disposable QEMU admin fixture. Run on Linux, never on the model host.

This prepares a machine and verifies KVM. Guest SSH is a separate test after
installation; a listening forwarded port does not establish a working guest.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import shutil
import stat
import subprocess
import time


def save(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    tmp.replace(path)


def run(args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()


class QMP:
    def __init__(self, path):
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.settimeout(10)
        self.sock.connect(str(path))
        self.file = self.sock.makefile('rwb', buffering=0)
        greeting = json.loads(self.file.readline())
        if 'QMP' not in greeting:
            raise RuntimeError('Not a QMP endpoint')
        self.call('qmp_capabilities')

    def call(self, command, arguments=None):
        payload = {'execute': command, 'id': command}
        if arguments is not None:
            payload['arguments'] = arguments
        self.file.write(json.dumps(payload).encode() + b'\n')
        while True:
            line = self.file.readline()
            if not line:
                raise RuntimeError('QMP disconnected before reply')
            reply = json.loads(line)
            if reply.get('id') != command:
                continue
            if 'error' in reply:
                raise RuntimeError(str(reply['error']))
            return reply['return']

    def close(self):
        self.file.close()
        self.sock.close()


def prepare(root):
    path = root / 'config.json'
    if path.exists():
        return json.loads(path.read_text())
    if any(root.iterdir()):
        raise RuntimeError('Prepare requires an empty, owned task directory')
    config = {'schema': 1, 'name': 'branchwrite-admin01', 'memory_mib': 4096,
              'cpus': 4, 'disk_gib': 32, 'ssh_port': 22220, 'http_port': 18080,
              'guest_user': 'maint', 'created_at': time.time()}
    run(['qemu-img', 'create', '-f', 'qcow2', str(root / 'disk.qcow2'), '32G'])
    run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'branchwrite-admin-fixture',
         '-f', str(root / 'guest-key')])
    save(path, config)
    return config


def arguments(root, config, iso=None, probe=False):
    args = ['qemu-system-x86_64', '-name', config['name'], '-machine', 'q35,accel=kvm',
            '-cpu', 'host', '-smp', str(config['cpus']), '-m', str(config['memory_mib']),
            '-drive', 'file=' + str(root / 'disk.qcow2') + ',format=qcow2,if=virtio',
            '-netdev', 'user,id=net0,hostfwd=tcp:127.0.0.1:' + str(config['ssh_port'])
              + '-:22,hostfwd=tcp:127.0.0.1:' + str(config['http_port']) + '-:80',
            '-device', 'virtio-net-pci,netdev=net0', '-display', 'none',
            '-vnc', 'unix:' + str(root / 'vnc.sock'),
            '-serial', 'file:' + str(root / 'serial.log'), '-monitor', 'none',
            '-qmp', 'unix:' + str(root / 'qmp.sock') + ',server=on,wait=off',
            '-pidfile', str(root / 'qemu.pid'), '-daemonize']
    if config.get('firmware') == 'uefi':
        code = Path('/usr/share/OVMF/OVMF_CODE_4M.fd')
        template = Path('/usr/share/OVMF/OVMF_VARS_4M.fd')
        variables = root / 'OVMF_VARS.fd'
        if not variables.exists():
            shutil.copyfile(template, variables); variables.chmod(0o600)
        args += ['-drive', 'if=pflash,format=raw,readonly=on,file=' + str(code),
                 '-drive', 'if=pflash,format=raw,file=' + str(variables)]
    if iso:
        # QEMU's legacy option parser interprets commas even without a shell.
        if ',' in str(iso):
            raise ValueError('Copy ISO to a filename without commas first')
        args += ['-drive', 'file=' + str(iso) + ',media=cdrom,format=raw,readonly=on',
                 '-boot', 'once=d,menu=on']
    if probe:
        args += ['-S', '-snapshot']
    return args


def connect(root):
    return QMP(root / 'qmp.sock')


def available(root):
    try:
        connection = connect(root)
    except (FileNotFoundError, ConnectionRefusedError):
        return
    connection.close()
    raise RuntimeError('An owned VM already has an active QMP endpoint')


def launch(root, config, iso=None, probe=False):
    available(root)
    if not os.access('/dev/kvm', os.R_OK | os.W_OK):
        raise RuntimeError('KVM access is required; no silent emulation fallback')
    for port in (config['ssh_port'], config['http_port']):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', port))
    argv = arguments(root, config, iso, probe)
    run(argv)
    connection = connect(root)
    try:
        result = {'time': time.time(), 'qemu': run(['qemu-system-x86_64', '--version']),
                  'argv': argv, 'kvm': connection.call('query-kvm'),
                  'status': connection.call('query-status'),
                  'cpus': len(connection.call('query-cpus-fast')),
                  'memory': connection.call('query-memory-size-summary'),
                  'guest_ssh': 'NOT_TESTED_NO_GUEST_YET' if probe else 'NOT_TESTED',
                  'pid': int((root / 'qemu.pid').read_text()),
                  'host_uid': os.getuid()}
        sockets = run(['ss', '-H', '-ltnp'])
        result['forwarded_listeners'] = [line for line in sockets.splitlines() if 'pid=' + str(result['pid']) + ',' in line]
        for port in (config['ssh_port'], config['http_port']):
            if not any('127.0.0.1:' + str(port) in line for line in result['forwarded_listeners']):
                raise RuntimeError('Expected loopback listener was not observed')
        if not result['kvm']['enabled']:
            raise RuntimeError('KVM was not enabled')
        save(root / ('hardware-check.json' if probe else 'launch.json'), result)
        return result
    finally:
        if probe:
            connection.call('quit')
        connection.close()
        if probe:
            # A successful QMP quit reply is not, by itself, exit evidence.
            pid = json.loads((root / 'hardware-check.json').read_text())['pid']
            exited = False
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                try:
                    proc = Path('/proc') / str(pid) / 'stat'
                    state = proc.read_text().rsplit(')', 1)[1].strip().split()[0]
                    if state == 'Z':
                        exited = True; break
                except FileNotFoundError:
                    exited = True; break
                time.sleep(.1)
            receipt = json.loads((root / 'hardware-check.json').read_text())
            receipt['probe_process_exited'] = exited
            save(root / 'hardware-check.json', receipt)
            if not exited:
                raise RuntimeError('Probe did not exit in time; inspect the owned QMP endpoint')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'check', 'start', 'status', 'powerdown', 'quit'])
    parser.add_argument('--root', type=Path, default=Path.home() / '.local/share/bw-vm/admin01')
    parser.add_argument('--iso', type=Path)
    parser.add_argument('--firmware', choices=['bios', 'uefi'], default='bios')
    options = parser.parse_args()
    os.umask(0o077)
    root = options.root.expanduser().absolute()
    if root.is_symlink():
        raise ValueError('Task directory cannot be a symlink')
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.resolve() != root or root.stat().st_uid != os.getuid() or stat.S_IMODE(root.stat().st_mode) != 0o700:
        raise ValueError('Task directory must be real, owned and mode 0700')
    if ',' in str(root) or len(os.fsencode(root / 'qmp.sock')) >= 104:
        raise ValueError('Choose a shorter task path without commas')
    if options.action == 'prepare':
        result = prepare(root)
    elif options.action in ('check', 'start'):
        config = json.loads((root / 'config.json').read_text())
        config['firmware'] = options.firmware
        iso = options.iso.resolve(strict=True) if options.iso else None
        if iso and not iso.is_file():
            raise ValueError('ISO must be a regular file')
        if iso:
            with iso.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            save(root / 'iso-receipt.json', {'path': str(iso), 'bytes': iso.stat().st_size,
                                           'sha256': digest, 'recorded_at': time.time()})
        result = launch(root, config, iso, probe=options.action == 'check')
    else:
        connection = connect(root)
        try:
            name = connection.call('query-name')
            config = json.loads((root / 'config.json').read_text())
            if name.get('name') != config['name']:
                raise RuntimeError('Unexpected VM identity')
            command = {'status': 'query-status', 'powerdown': 'system_powerdown', 'quit': 'quit'}[options.action]
            result = connection.call(command)
        finally:
            connection.close()
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
