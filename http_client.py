import socket
import sys

def parse_url(url): 
    # remove http://
    url_truncated = url[7:]
    
    # Split host and path
    if '/' in url_truncated:
        host_port, path = url_truncated.split('/', 1)
        if path != "" and path[-1] == '/':
            path = '/' + path[:-1]
        else:
            path = '/' + path
    else:
        host_port = url_truncated
        path = '/'
    
    # Split host and port
    if ':' in host_port:
        host, port_str = host_port.rsplit(':', 1)
        port = int(port_str)
    else:
        host = host_port
        port = 80
    
    return host, port, path

def send_http_request(host, port, path):
    """Send HTTP GET request and return response."""

    # Used this website as guidance on using socket
    # https://www.internalpointers.com/post/making-http-requests-sockets-python.html
    try:
        # connect to host and port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        
        # construct HTTP GET request
        request = f"GET {path} HTTP/1.0\r\nHost: {host}\r\nConnection: close\r\n\r\n"
        sock.sendall(request.encode())
        
        # receive response, loop if longer than 4096 bytes
        response = b""
        while True:
            part = sock.recv(4096)
            if not part:
                break
            response += part
        
        sock.close()
        return response.decode()
    except Exception as e:
        return None

def parse_response(response):
    """Parse HTTP response and return (status_code, headers, body)."""
    if not response:
        return None, {}, ""
    
    # Split headers and body
    parts = response.split('\r\n\r\n', 1)
    if len(parts) == 2:
        headers_section, body = parts
    else:
        headers_section = parts[0]
        body = ""
    
    # Parse status line
    lines = headers_section.split('\r\n')
    status_line = lines[0]
    
    try:
        status_code = int(status_line.split()[1])
    except Exception as e:
        return None, {}, ""
    
    # Parse headers
    headers = {}
    for line in lines[1:]:
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip().lower()] = value.strip()
    
    return status_code, headers, body

def fetch_url(url, redirects=0):
    """Fetch URL with redirect handling."""
    if redirects == 10:
        sys.stderr.write("Too many redirects\n")
        sys.exit(1)

    # Check if URL starts with http://
    if not url.startswith("http://"):
        sys.stderr.write("Error: URL must start with http://\n")
        sys.exit(1)
    
    # Parse URL
    parsed = parse_url(url)
    host, port, path = parsed
    
    # Send request
    response = send_http_request(host, port, path)
    if response is None:
        sys.stderr.write("Error: Failed to connect\n")
        sys.exit(1)
    
    # Parse response
    status_code, headers, body = parse_response(response)
    
    if status_code is None:
        sys.stderr.write("Error: Invalid response\n")
        sys.exit(1)
    
    # Handle redirects
    if status_code in [301, 302]:
        location = headers.get('location')
        sys.stderr.write(f"Redirected to: {location}\n")
        if location:
            # Check if redirect is to HTTPS
            if location.startswith("https://"):
                sys.stderr.write("Error: HTTPS is not supported\n")
                sys.exit(1)
            return fetch_url(location, redirects + 1)
        else:
            sys.stderr.write("Error: Redirect without location header\n")
            sys.exit(1)
    
    # Check status code
    if status_code >= 400:
        # Print body even on error >= 400
        sys.stdout.write(body)
        sys.exit(1)
    
    if status_code != 200:
        sys.stderr.write(f"Error: HTTP {status_code}\n")
        sys.exit(1)

    # Check content-type
    content_type = headers.get('content-type', '')
    if not content_type.startswith('text/html'):
        sys.stderr.write(f"Error: Invalid content-type: {content_type}\n")
        sys.exit(1)
    
    # Print body and exit successfully
    sys.stdout.write(body)
    sys.exit(0)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.stderr.write("Only one argument")
        sys.exit(1)
    
    url = sys.argv[1]
    fetch_url(url)
