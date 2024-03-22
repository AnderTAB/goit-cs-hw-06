import mimetypes
import pathlib
import urllib.parse
import multiprocessing
from http.server import HTTPServer, BaseHTTPRequestHandler
from server import Server

class HttpHandler(BaseHTTPRequestHandler):
    def __init__(self, logger):
        self.logger = logger

    async def do_POST(self):
        data = await self.rfile.read(int(self.headers["Content-Length"]))
        self.logger.info(
            f"POST request: Path: {self.path}; Headers: {self.headers}; Body: {data.decode()}"
        )
        data_parse = urllib.parse.unquote_plus(data.decode())
        self.logger.info(
            f"POST request: Path: {self.path}; Headers: {self.headers}; Body: {data_parse}"
        )
        data_dict = {
            key: value for key, value in [el.split("=") for el in data_parse.split("&")]
        }
        await self.send_response(302)
        await self.send_header("Location", "/")
        await self.end_headers()

    async def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
        self.logger.info(
            f"GET request: Path: {self.path}; Headers: {self.headers}; Query: {pr_url.query}"
        )
        if pr_url.path == "/":
            self.logger.info(f"GET request: index: {pr_url}")
            await self.send_html_file("index.html")
        elif pr_url.path == "/contact":
            self.logger.info(f"GET request: contact: {pr_url}")
            await self.send_html_file("contact.html")
        else:
            if pathlib.Path().joinpath(pr_url.path[1:]).exists():
                await self.send_static()
            else:
                self.logger.info(f"GET request: URL error: {pr_url}")
                await self.send_html_file("error.html", 404)

    async def send_html_file(self, filename, status=200):
        await self.send_response(status)
        await self.send_header("Content-type", "text/html")
        await self.end_headers()
        async with open(filename, "rb") as fd:
            await self.wfile.write(fd.read())

    async def send_static(self):
        await self.send_response(200)
        mt = mimetypes.guess_type(self.path)
        if mt:
            await self.send_header("Content-type", mt[0])
        else:
            await self.send_header("Content-type", "text/plain")
        await self.end_headers()
        async with open(f".{self.path}", "rb") as file:
            await self.wfile.write(file.read())

async def run_http_server(server_class=HTTPServer, handler_class=HttpHandler):
    server_address = ("localhost", 3000)
    http = server_class(server_address, handler_class)
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        http.server_close()

async def run_server(logger, server_class=HTTPServer, handler_class=HttpHandler):
    server = Server(logger)
    async with websockets.serve(server.ws_handler, "localhost", 5000):
        try:
            await asyncio.Future()
        except KeyboardInterrupt:
            server.unregister()
    asyncio.run(serve())

async def start_http_server():
    await run_http_server()

async def start_socket_server():
    await run_server()


if __name__ == "__main__":
    http_server_process = multiprocessing.Process(target=start_http_server)
    http_server_process.start()

    socket_server = multiprocessing.Process(target=start_socket_server)
    socket_server.start()

    http_server_process.join()
    socket_server.join()
