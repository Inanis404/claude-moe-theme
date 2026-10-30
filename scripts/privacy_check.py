#!/usr/bin/env python3
"""Scan only the public project allowlist. Findings never include matched values."""
import argparse
import base64
import json
import pathlib
import re
import shutil
import struct
import subprocess
import zlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIRECTORIES = {'assets', 'config', 'docs', 'runtime', 'scripts', 'tests', '.github'}
ROOT_FILES = {'README.md', 'LICENSE', 'NOTICE.md', 'CHANGELOG.md', 'CONTRIBUTING.md', 'SECURITY.md',
              '.gitignore', '.gitattributes', '.editorconfig', 'package.json', 'package-lock.json'}
IGNORED = {'.git', '.local', 'dist', 'node_modules', '__pycache__', '.pytest_cache', '.venv'}
TEXT_SUFFIXES = {'.md', '.json', '.py', '.cjs', '.js', '.html', '.css', '.sh', '.ps1', '.yml', '.yaml', '.svg'}
MEDIA_SUFFIXES = {'.png', '.jpg', '.jpeg', '.ico', '.mp4', '.wav'}
PRIVATE_FILES = {'appearance.json', 'environment.json', 'status.json', 'windows.json', 'background-diagnostics.json'}
DATA_URI = re.compile(r'data:(image/(?:png|jpeg|jpg)|audio/(?:wav|wave));base64,([A-Za-z0-9+/=\r\n]+)')
PATTERNS = {
    'personal Windows path': re.compile(r'[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s<>"\']+', re.I),
    'personal Linux path': re.compile(r'/home/[A-Za-z0-9_.-]+'),
    'machine identifier': re.compile(r'\b(?:LAPTOP|DESKTOP)-[A-Z0-9]{6,}\b'),
    'email address': re.compile(r'\b[A-Za-z0-9._%+-]+@(?!example\.(?:com|org|invalid)\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'),
    'private key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
    'provider token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-(?:ant-)?[A-Za-z0-9_-]{20,}|xox[baprs]-[A-Za-z0-9-]{20,}|AIza[A-Za-z0-9_-]{30,}|(?:AKIA|ASIA)[A-Z0-9]{16})\b'),
    'JWT credential': re.compile(r'\beyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\b'),
    'credential URL': re.compile(r'https?://[^\s/<>]+:[^\s/@<>]+@'),
    'assigned secret': re.compile(r'''(?ix)(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*["']?\s*[:=]\s*["'](?!<|example|placeholder|your_|test_|\$)[A-Za-z0-9_+/=.-]{16,}["']'''),
}


def source_files(root=ROOT):
    root = pathlib.Path(root)
    files, problems = [], []
    def visit(folder):
        for path in sorted(folder.iterdir()):
            rel = path.relative_to(root)
            name = rel.as_posix()
            if path.name in IGNORED:
                continue
            if path.is_symlink():
                problems.append((name, 'symlink is not public source'))
            elif path.is_dir():
                if len(rel.parts) == 1 and path.name not in DIRECTORIES:
                    problems.append((name, 'unexpected top-level directory'))
                else:
                    visit(path)
            elif len(rel.parts) == 1 and path.name not in ROOT_FILES:
                problems.append((name, 'unexpected top-level file'))
            elif path.name in PRIVATE_FILES or path.name.startswith('.env') or path.suffix.lower() in {'.key', '.pem', '.pfx', '.p12', '.log', '.lnk'}:
                problems.append((name, 'local configuration or credential file'))
            elif path.suffix.lower() not in TEXT_SUFFIXES | MEDIA_SUFFIXES and path.name not in ROOT_FILES:
                problems.append((name, 'unapproved file type'))
            elif path.stat().st_size >= 100 * 1024 * 1024:
                problems.append((name, 'file exceeds conservative source size threshold'))
            else:
                files.append(path)
    visit(root)
    return files, problems


def image_metadata(data, extension):
    """Return metadata payloads; never scan compressed picture pixels as text."""
    result = []
    if extension == '.png':
        if not data.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError('invalid PNG')
        offset = 8
        while offset + 12 <= len(data):
            size = struct.unpack_from('>I', data, offset)[0]
            kind = data[offset+4:offset+8]
            payload = data[offset+8:offset+8+size]
            if len(payload) != size or offset+12+size > len(data):
                raise ValueError('truncated PNG')
            if kind in {b'tEXt', b'eXIf'}:
                result.append(payload)
            elif kind == b'zTXt':
                key, content = payload.split(b'\0', 1)
                result.extend([key, zlib.decompress(content[1:])])
            elif kind == b'iTXt':
                key, content = payload.split(b'\0', 1)
                flag, method = content[:2]
                language, translated, text = content[2:].split(b'\0', 2)
                result.extend([key, language, translated, zlib.decompress(text) if flag else text])
            offset += size + 12
            if kind == b'IEND':
                if offset != len(data):
                    result.append(data[offset:])
                break
    elif extension in {'.jpg', '.jpeg'}:
        if not data.startswith(b'\xff\xd8'):
            raise ValueError('invalid JPEG')
        offset = 2
        while offset < len(data):
            if data[offset] != 255:
                raise ValueError('invalid JPEG marker')
            while offset < len(data) and data[offset] == 255:
                offset += 1
            marker = data[offset]
            offset += 1
            if marker in {0xda, 0xd9}:
                break
            if marker in range(0xd0, 0xd8) or marker == 1:
                continue
            size = int.from_bytes(data[offset:offset+2], 'big')
            if size < 2 or offset+size > len(data):
                raise ValueError('truncated JPEG')
            if marker in {0xe1, 0xed, 0xfe}:
                result.append(data[offset+2:offset+size])
            offset += size
    elif extension == '.ico':
        if data[:4] != b'\0\0\1\0':
            raise ValueError('invalid ICO')
        count = int.from_bytes(data[4:6], 'little')
        for i in range(count):
            size, offset = struct.unpack_from('<II', data, 6+16*i+8)
            payload = data[offset:offset+size]
            if len(payload) != size:
                raise ValueError('truncated ICO')
            if payload.startswith(b'\x89PNG'):
                result.extend(image_metadata(payload, '.png'))
    elif extension == '.wav':
        if data[:4] != b'RIFF' or data[8:12] != b'WAVE':
            raise ValueError('invalid WAV')
        offset = 12
        while offset+8 <= len(data):
            kind = data[offset:offset+4]
            size = int.from_bytes(data[offset+4:offset+8], 'little')
            if kind not in {b'fmt ', b'data', b'fact', b'JUNK'}:
                result.append(data[offset+8:offset+8+size])
            offset += 8+size+(size % 2)
    return result


def check(root=ROOT, deny_terms=()):
    root = pathlib.Path(root).resolve()
    files, problems = source_files(root)
    def scan(name, text):
        for reason, pattern in PATTERNS.items():
            if pattern.search(text):
                problems.append((name, reason))
        if any(term and term.casefold() in text.casefold() for term in deny_terms):
            problems.append((name, 'private term supplied to checker'))
    def scan_metadata(name, payloads):
        for payload in payloads:
            scan(name, payload.decode('utf8', errors='replace'))
            if b'\0' in payload:
                scan(name, payload.decode('utf-16-le', errors='replace'))
    probe = shutil.which('ffprobe')
    for path in files:
        name, extension = path.relative_to(root).as_posix(), path.suffix.lower()
        scan(name, name)
        try:
            if extension == '.mp4':
                if not probe:
                    problems.append((name, 'FFprobe required to inspect video metadata'))
                    continue
                proc = subprocess.run([probe, '-v', 'error', '-show_entries', 'format_tags:stream_tags', '-of', 'json', str(path)], capture_output=True, text=True, timeout=30)
                if proc.returncode:
                    raise ValueError('video metadata inspection failed')
                scan(name, json.dumps(json.loads(proc.stdout), ensure_ascii=False))
            elif extension in MEDIA_SUFFIXES:
                scan_metadata(name, image_metadata(path.read_bytes(), extension))
            else:
                text = path.read_text(encoding='utf-8-sig')
                matches = list(DATA_URI.finditer(text))
                scan(name, DATA_URI.sub('<embedded-media>', text))
                for match in matches:
                    data = base64.b64decode(re.sub(r'\s+', '', match.group(2)), validate=True)
                    media_type = match.group(1)
                    ext = '.wav' if media_type.startswith('audio/') else ('.png' if media_type.endswith('png') else '.jpg')
                    scan_metadata(name, image_metadata(data, ext))
        except (ValueError, UnicodeError, OSError, struct.error, zlib.error, subprocess.TimeoutExpired):
            problems.append((name, 'unreadable source or media metadata'))
    return files, sorted(set(problems))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=pathlib.Path, default=ROOT)
    parser.add_argument('--deny-term', action='append', default=[], help='Extra private identifier; matched values are never printed')
    args = parser.parse_args()
    files, problems = check(args.root, args.deny_term)
    print(json.dumps({'passed': not problems, 'sourceFileCount': len(files), 'findings': [{'file': f, 'reason': r} for f, r in problems]}, ensure_ascii=False, indent=2))
    raise SystemExit(bool(problems))
