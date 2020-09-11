#!/usr/bin/env python

import argparse
import gc
import hashlib
import http.client
import io
import socket
import textwrap
import time
import urllib.parse
from typing import Callable, Tuple, Optional

import requests
import httpx
import numpy as np


_Method = Callable[[str], bytes]
METHODS = {}
CHECKSUMS = {
    10**6 + 128: 'fa82243e0db587af04504f5d3229ff7227f574f8f938edaad8be8e168bc2bc87',
    10**9 + 128: 'd699e2c306b897609be6222315366b25137778e18f8634c75b006cef50647978'
}


def method(name: str) -> Callable[[_Method], _Method]:
    def decorate(func: _Method) -> _Method:
        METHODS[name] = func
        return func

    return decorate


@method('httpclient-naive')
def load_httpclient_naive(url: str) -> bytes:
    parts = urllib.parse.urlparse(url)
    conn = http.client.HTTPConnection(parts.netloc)
    conn.request('GET', url)
    resp = conn.getresponse()
    return resp.read(resp.length)     # type: ignore


@method('requests-naive')
def load_requests_naive(url: str) -> bytes:
    with requests.get(url) as resp:
        return resp.content


@method('requests-stream-read')
def load_requests_stream(url: str) -> bytes:
    with requests.get(url, stream=True) as resp:
        return resp.raw.read()


@method('requests-stream-fp-read')
def load_requests_stream_fp_read(url: str) -> bytes:
    with requests.get(url, stream=True) as resp:
        return resp.raw._fp.read()


@method('httpx-naive')
def load_httpx_naive(url: str) -> bytes:
    return httpx.get(url).content


def prepare_socket(url: str) -> Tuple[io.BufferedIOBase, int]:
    parts = urllib.parse.urlparse(url)
    address = (parts.hostname, parts.port)
    sock = socket.socket()
    sock.connect(address)
    req_header = textwrap.dedent(f'''\
        GET {parts.path} HTTP/1.1
        Host: {parts.hostname}:{parts.port}
        User-Agent: python
        Connection: close
        Accept: */*

        ''').replace('\n', '\r\n').encode('ascii')
    fh = sock.makefile('rwb')
    fh.write(req_header)
    fh.flush()
    content_length: Optional[int] = None
    while True:
        line = fh.readline()
        if line == b'\r\n':
            if content_length is None:
                raise RuntimeError('Did not receive Content-Length header')
            return fh, content_length        # type: ignore
        else:
            text = line.decode('latin-1').rstrip().lower()
            if text.startswith('content-length: '):
                content_length = int(text.split(' ')[1])


@method('socket-read')
def load_socket_read(url: str) -> bytes:
    fh, content_length = prepare_socket(url)
    return fh.read(content_length)


@method('socket-readinto')
def load_socket_readinto(url: str) -> bytes:
    fh, content_length = prepare_socket(url)
    raw = bytearray(content_length)
    n = fh.readinto(raw)
    assert n == content_length
    return memoryview(raw)[:n]


def validate(data: bytes):
    size = len(data)
    try:
        checksum = CHECKSUMS[size]
    except KeyError:
        print('No checksum found')
    else:
        actual_checksum = hashlib.sha256(data).hexdigest()
        if actual_checksum != checksum:
            print(f'Checksum mismatch ({actual_checksum} != {checksum})')


def measure_method(method: str, args: argparse.Namespace) -> None:
    rates = []
    for i in range(args.passes):
        gc.collect()
        start = time.monotonic()
        data = METHODS[method](args.url)
        stop = time.monotonic()
        elapsed = stop - start
        rates.append(len(data) / elapsed)
        if i == 0:
            validate(data)
        del data
    mean = np.mean(rates)
    std = np.std(rates) / np.sqrt(args.passes - 1)
    print('{}: {:.1f} ± {:.1f} MB/s'.format(method, mean / 1e6, std / 1e6))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--passes', type=int, default=5)
    parser.add_argument('method')
    parser.add_argument('url')
    args = parser.parse_args()
    if args.method not in METHODS and args.method != 'all':
        parser.error('Method must be "all" or one of {}'.format(set(METHODS.keys())))

    if args.method == 'all':
        for method in METHODS:
            measure_method(method, args)
    else:
        measure_method(args.method, args)


if __name__ == '__main__':
    main()
