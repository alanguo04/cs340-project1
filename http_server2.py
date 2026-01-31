#!/usr/bin/env python3
import socket
import sys
import os
import select

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

def handle_connection(conn, data):
    # Read
    while b'\r\n\r\n' not in data:
        chunk = conn.recv(4096)
        if not chunk:
            break
        data += chunk

    if not data:
        return
    request_text = data.decode()

    lines = request_text.split('\r\n')
    if not lines:
        return
    request_line = lines[0]
    parts = request_line.split()
    if len(parts) < 3:
        return
    method, path, _ = parts

    if method != 'GET':
        resp = build_response_header('403', content_length=0)
        try:
            conn.sendall(resp)
        except Exception:
            pass
        return

    # get rid of leading '/' in path for file name
    if path.startswith('/'):
        path = path[1:]

    if path == '':
        path = 'index.html'

    # Check file exists
    if not os.path.exists(path) or not os.path.isfile(path):
        body = b'<html><body><h1>404 Not Found</h1></body></html>\n'
        header = build_response_header('404', content_length=len(body))
        try:
            conn.sendall(header + body)
        except Exception:
            pass
        return

    # Check extension
    if not (path.endswith('.html') or path.endswith('.htm')):
        body = b'<html><body><h1>403 Forbidden</h1></body></html>\n'
        header = build_response_header('403', content_length=len(body))
        try:
            conn.sendall(header + body)
        except Exception:
            pass
        return

    # Serve file
    try:
        with open(path, 'rb') as f:
            content = f.read()
    except Exception:
        body = b'<html><body><h1>404 Not Found</h1></body></html>\n'
        header = build_response_header('404', content_length=len(body))
        try:
            conn.sendall(header + body)
        except Exception:
            pass
        return

    header = build_response_header('200', content_length=len(content))
    try:
        conn.sendall(header)
        sent = 0
        while sent < len(content):
            chunk = content[sent:sent+4096]
            conn.sendall(chunk)
            sent += len(chunk)
    except Exception:
        pass


def main():
    # just checking some input constraints
    if len(sys.argv) != 2:
        sys.stderr.write('Usage: python3 http_server2.py [port]\n')
        sys.exit(1)

    try:
        port = int(sys.argv[1])
    except ValueError:
        sys.stderr.write('Port must be an integer\n')
        sys.exit(1)

    if port < 1024:
        sys.stderr.write('Port must be >= 1024\n')
        sys.exit(1)

    # Use a non-blocking accept socket and select to handle multiple
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as accept_sock:
        accept_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        accept_sock.bind(('', port))
        accept_sock.listen(5)
        accept_sock.setblocking(False)
        sys.stderr.write(f'Listening on port {port}...\n')

        connections = []  # socket -> bytearray buffer

        while True:
            read_list = [accept_sock] + connections
            readable, _, _ = select.select(read_list, [], [])

            for s in readable:
                if s == accept_sock:
                    conn, _ = accept_sock.accept()
                    conn.setblocking(False)
                    connections.append(conn)
                else:
                    # trying a byte
                    data = s.recv(1)
                    if not data:
                        s.close()
                        connections.remove(s)
                        continue

                    # cnonecting! also sending the byte "data"
                    handle_connection(s, data)
                    try:
                        s.shutdown(socket.SHUT_RDWR)
                    except Exception:
                        pass
                    s.close()
                    connections.remove(s)
    
if __name__ == '__main__':
    main()
