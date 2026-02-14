#!/usr/bin/env python3
"""
serve.py
========

Convenience script to run a local HTTP server for previewing the
generated election maps and website.  By default it serves the
``site`` directory on port 8000.  This allows you to test the
interactive pages before deploying them to GitHub Pages.

Usage::

    python3 scripts/serve.py

or to serve a different directory/port::

    python3 scripts/serve.py --dir site --port 8080

Once running, open http://localhost:PORT in your browser to view the site.
"""

import argparse
import http.server
import os
import socketserver


def main() -> None:
    parser = argparse.ArgumentParser(description='Serve a directory via a simple HTTP server.')
    parser.add_argument('--dir', default='site', help='Directory to serve (default: site).')
    parser.add_argument('--port', type=int, default=8000, help='Port to listen on (default: 8000).')
    args = parser.parse_args()
    os.chdir(args.dir)
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(('', args.port), handler) as httpd:
        print(f"Serving {args.dir} at http://localhost:{args.port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == '__main__':
    main()