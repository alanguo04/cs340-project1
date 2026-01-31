#!/usr/bin/env python3
import socket
import sys
import json
import math

HTML_HEADERS = {
    '200': 'HTTP/1.0 200 OK\r\n',
    '400': 'HTTP/1.0 400 Bad Request\r\n',
    '404': 'HTTP/1.0 404 Not Found\r\n',
}

def build_response(status_code, body_bytes):
    header = HTML_HEADERS[status_code]
    header += 'Content-Type: application/json\r\n'
    header += f'Content-Length: {len(body_bytes)}\r\n'
    header += 'Connection: Keep-Alive\r\n'
    header += '\r\n'
    return header.encode() + body_bytes


def process_product_query(query):
    if not query:
        return None, '400'

    pairs = query.split('&')
    params = []
    for p in pairs:
        if p == '':
            continue
        if '=' in p:
            k, v = p.split('=', 1)
        else:
            # parameter without value
            return None, '400'
        # empty value
        if v == '':
            return None, '400'
        params.append((k, v))

    if not params:
        return None, '400'

    multiples = []
    for _, val in params:
        try:
            f = float(val)
        except Exception:
            return None, '400'
        if math.isfinite(f) and f.is_integer():
            v = int(f)
        else:
            v = f
        multiples.append(v)

    prod = 1.0
    for v in multiples:
        prod *= float(v)

    # process infiity
    if math.isinf(prod):
        result = "inf" if prod > 0 else "-inf"
    else:
        if math.isfinite(prod) and float(prod).is_integer():
            result = int(prod)
        else:
            result = prod

    body_obj = {
        'operation': 'product',
        'operands': multiples,
        'result': result,
    }

    body_bytes = json.dumps(body_obj).encode()
    return body_bytes, '200'


def handle_connection(conn):
    try:
        data = b''
        # read
        while b'\r\n\r\n' not in data:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk

        if not data:
            return

        request_text = data.decode()

        lines = request_text.split('\r\n')
        request_line = lines[0] if lines else ''
        parts = request_line.split()
        _, full_path, _ = parts

        # parsing parameters
        if '?' in full_path:
            path, query = full_path.split('?', 1)
        else:
            path = full_path
            query = ''

        if path != '/product':
            body = json.dumps({'error': 'Not Found'}).encode()
            resp = build_response('404', body)
            conn.sendall(resp)
            return

        body_bytes, status = process_product_query(query)
        if status != '200':
            body = json.dumps({'error': 'Bad Request'}).encode()
            resp = build_response('400', body)
            conn.sendall(resp)
            return

        # Success
        resp = build_response('200', body_bytes)
        conn.sendall(resp)

    finally:
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        conn.close()


def main():
    # just checking some input constraints
    if len(sys.argv) != 2:
        sys.stderr.write('Usage: python3 http_server3.py [port]\n')
        sys.exit(1)

    try:
        port = int(sys.argv[1])
    except ValueError:
        sys.stderr.write('Port must be an integer\n')
        sys.exit(1)

    if port < 1024:
        sys.stderr.write('Port must be >= 1024\n')
        sys.exit(1)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('', port))
        s.listen(5)
        sys.stderr.write(f'Listening on port {port}...\n')

        while True:
            conn, _ = s.accept()
            handle_connection(conn)


if __name__ == '__main__':
    main()
