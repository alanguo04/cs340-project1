#!/usr/bin/env python3
import socket
import sys
import os

HTML_HEADERS = {
    '200': 'HTTP/1.0 200 OK\r\n',
    '403': 'HTTP/1.0 403 Forbidden\r\n',
    '404': 'HTTP/1.0 404 Not Found\r\n',
}

def build_response_header(code, content_length=None):
    header = HTML_HEADERS[code]
    header += 'Content-Type: text/html; charset=UTF-8\r\n'
    if content_length is not None:
        header += f'Content-Length: {content_length}\r\n'
    header += 'Connection: Keep-Alive\r\n'
    header += '\r\n'
    return header.encode()


def handle_connection(conn):
    try:
        data = b''
        # Read
        while b'\r\n\r\n' not in data:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk

        if not data:
            return

        request_text = data.decode('utf-8', errors='replace')
    
        lines = request_text.split('\r\n')
        request_line = lines[0]
        parts = request_line.split()
        if len(parts) < 3:
            # Malformed request
            return
        method, path, _ = parts

        if method != 'GET':
            # Only GET supported: respond 403
            resp = build_response_header('403', content_length=0)
            conn.sendall(resp)
            return

        # get rid of / in path for file name
        path = path[1:]

        # Check file exists
        if not os.path.exists(path) or not os.path.isfile(path):
            body = b'<html><body><h1>404 Not Found</h1></body></html>\n'
            header = build_response_header('404', content_length=len(body))
            conn.sendall(header + body)
            return

        # Check extension
        if not (path.endswith('.html') or path.endswith('.htm')):
            body = b'<html><body><h1>403 Forbidden</h1></body></html>\n'
            header = build_response_header('403', content_length=len(body))
            conn.sendall(header + body)
            return

        # Serve file
        with open(path, 'rb') as f:
            content = f.read()
        header = build_response_header('200', content_length=len(content))
        conn.sendall(header)
        # send in chunks
        sent = 0
        while sent < len(content):
            chunk = content[sent:sent+4096]
            conn.sendall(chunk)
            sent += len(chunk)

    finally:
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        conn.close()


def main():
    # just checking some input constraints
    if len(sys.argv) != 2:
        sys.stderr.write('Usage: python3 http_server1.py [port]\n')
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
