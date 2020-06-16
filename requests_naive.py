#!/usr/bin/env python

import argparse
import io
import socket
import textwrap
import time
import urllib.parse
from typing import Callable, Tuple, Optional

import requests
import httpx
import numpy as np


_Method = Callable[[str], int]
METHODS = {}


def method(name: str) -> Callable[[_Method], _Method]:
    def decorate(func: _Method) -> _Method:
        METHODS[name] = func
        return func

    return decorate


def readarray(fp: io.BufferedIOBase) -> np.ndarray:
    version = np.lib.format.read_magic(fp)
    if version == (1, 0):
        shape, fortran_order, dtype = np.lib.format.read_array_header_1_0(fp)
    elif version == (2, 0):
        shape, fortran_order, dtype = np.lib.format.read_array_header_2_0(fp)
    else:
        raise ValueError('Unsupported .npy version {}'.format(version))
    if dtype.hasobject:
        raise ValueError('Object arrays are not supported')
    count = int(np.product(shape))
    data = np.ndarray(count, dtype=dtype)
    bytes_read = fp.readinto(memoryview(data.view(np.uint8)))
    if bytes_read != data.nbytes:
        raise ValueError(f'Unexpected EOF: read {bytes_read}, expected {data.nbytes}')
    if fortran_order:
        data.shape = shape[::-1]
        data = data.transpose()
    else:
        data.shape = shape
    return data


@method('requests-naive')
def load_requests_naive(url: str) -> int:
    with requests.Session() as session:
        with session.get(url) as resp:
            data = resp.content
    fp = io.BytesIO(data)
    array = np.load(fp, allow_pickle=False)
    return array.nbytes


@method('httpx-naive')
def load_httpx_naive(url: str) -> int:
    with httpx.Client() as client:
        r = client.get(url)
    fp = io.BytesIO(r.content)
    array = np.load(fp, allow_pickle=False)
    return array.nbytes


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
            return fh, content_length
        else:
            text = line.decode('latin-1').rstrip().lower()
            if text.startswith('content-length: '):
                content_length = int(text.split(' ')[1])


@method('socket-readarray')
def load_socket_readarray(url: str) -> int:
    fh, _ = prepare_socket(url)
    array = readarray(fh)
    return array.nbytes


@method('socket-direct')
def load_socket_direct(url: str) -> int:
    fh, _ = prepare_socket(url)
    array = np.lib.format.read_array(fh, allow_pickle=False)
    return array.nbytes


@method('socket-read')
def load_socket_read(url: str) -> int:
    fh, content_length = prepare_socket(url)
    data = fh.read(content_length)
    array = np.lib.format.read_array(io.BytesIO(data), allow_pickle=False)
    return array.nbytes


@method('socket-readinto')
def load_socket_readinto(url: str) -> int:
    fh, content_length = prepare_socket(url)
    raw = bytearray(content_length)
    n = fh.readinto(raw)
    assert n == content_length
    array = np.lib.format.read_array(io.BytesIO(raw), allow_pickle=False)
    return array.nbytes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('method')
    parser.add_argument('url')
    args = parser.parse_args()
    if args.method not in METHODS:
        parser.error('Method must be one of {}'.format(set(METHODS.keys())))

    start = time.monotonic()
    size = METHODS[args.method](args.url)
    stop = time.monotonic()
    elapsed = stop - start
    rate = size / elapsed
    print('{:.1f} MB/s'.format(rate / 1e6))


if __name__ == '__main__':
    main()
