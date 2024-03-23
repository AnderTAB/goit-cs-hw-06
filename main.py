import mimetypes
import socket
import logging
from datetime import datetime
from urllib.parse import urlparse, unquote_plus
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

from pymongo.mongo_client import MongoClient


BASE_DIRECTORY = Path(__file__).parent


MONGODB_URI = "mongodb://mongodb:27017"
BUFFER_SIZE = 1024
HTTP_PORT = 3000
HTTP_HOST = '0.0.0.0'
SOCKET_HOST = '127.0.0.1'
SOCKET_PORT = 5000


def send_socket_message(message):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.connect((SOCKET_HOST, SOCKET_PORT))
        sock.send(message.encode('utf-8'))


class WebHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed_path = urlparse(self.path).path
        if parsed_path == "/":
            self.send_html_response("index.html")
        elif parsed_path == "#":
            self.send_html_response("index.html")
        elif parsed_path == "/message":
            self.send_html_response("message.html")
        else:
            requested_file = BASE_DIRECTORY.joinpath(parsed_path[1:])
            if requested_file.exists():
                self.send_static_response(requested_file)
            else:
                self.send_html_response("error.html", 404)

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length"))
        post_data = self.rfile.read(content_length).decode()
        logging.info(unquote_plus(post_data))
        send_socket_message(post_data)
        self.send_response(302)
        self.send_header("Location", "/")
        self.end_headers()

    def send_html_response(self, filename, status=200):
        self.send_response(status)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        with open(filename, "rb") as file:
            self.wfile.write(file.read())

    def send_static_response(self, filename, status=200):
        self.send_response(status)
        mimetype = mimetypes.guess_type(filename)[0] if mimetypes.guess_type(filename)[0] else "text/plain"
        self.send_header("Content-type", mimetype)
        self.end_headers()
        with open(filename, "rb") as file:
            self.wfile.write(file.read())


def save_to_database(data):
    client = MongoClient(MONGODB_URI)
    db = client.homework
    parsed_data = unquote_plus(data.decode())
    try:
        parsed_data = {key: value for key, value in [el.split("=") for el in parsed_data.split("&")]}
        parsed_data['date'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
        logging.info(f'Parsed data: {parsed_data}')
        db.messages.insert_one(parsed_data)
    except ValueError as e:
        logging.error(f"Parse error: {e}")
    except Exception as e:
        logging.error(f"Failed to save: {e}")
    finally:
        client.close()


def run_http_server():
    http_server = HTTPServer((HTTP_HOST, HTTP_PORT), WebHandler)
    try:
        logging.info(f"HTTP server started on http://{HTTP_HOST}:{HTTP_PORT}")
        http_server.serve_forever()
    except Exception as e:
        logging.error(f"HTTP server error: {e}")
    finally:
        logging.info("HTTP server stopped")
        http_server.server_close()


def run_socket_server():
    socket_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_server.bind((SOCKET_HOST, SOCKET_PORT))
    logging.info(f"Socket server started on socket://{SOCKET_HOST}:{SOCKET_PORT}")
    try:
        while True:
            data, address = socket_server.recvfrom(BUFFER_SIZE)
            logging.info(f"Received message from {address}: {data.decode()}")
            save_to_database(data)
    except Exception as e:
        logging.error(f"Socket server error: {e}")
    finally:
        logging.info("Socket server stopped")
        socket_server.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(threadName)s - %(message)s")
    http_thread = Thread(target=run_http_server, name="http_server_thread")
    http_thread.start()

    socket_thread = Thread(target=run_socket_server, name="socket_server_thread")
    socket_thread.start()