import os
import socket
import threading
import cv2

VIDEO_DIR = "video_repository"
THUMBNAIL_DIR = "thumbnails"

# FUncao para gerar thumb do video
def ensure_thumbnails():
    for video_file in os.listdir(VIDEO_DIR):
        video_path = os.path.join(VIDEO_DIR, video_file)
        thumbnail_path = os.path.join(THUMBNAIL_DIR, f"{video_file}.jpg")

        if not os.path.exists(thumbnail_path):
            video_capture = cv2.VideoCapture(video_path)
            success, frame = video_capture.read()
            frame = cv2.resize(frame, (160, 90))
            cv2.imwrite(thumbnail_path, frame)
            video_capture.release()

# Envia thumb
def send_thumbnail(client_socket, thumbnail_name):
    thumbnail_path = os.path.join(THUMBNAIL_DIR, thumbnail_name)

    if not os.path.exists(thumbnail_path):
        error_response = "HTTP/1.1 404 Not Found\r\n\r\nThum nao encontrada."
        client_socket.sendall(error_response.encode())
        return

    with open(thumbnail_path, "rb") as thumbnail_file:
        thumbnail_data = thumbnail_file.read()
        response_header = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: image/jpeg\r\n"
            f"Content-Length: {len(thumbnail_data)}\r\n\r\n"
        )
        client_socket.sendall(response_header.encode() + thumbnail_data)

# Envia video para o navegador
def send_video_file(client_socket, video_name, range_header):
    video_path = os.path.join(VIDEO_DIR, video_name)

    if not os.path.exists(video_path):
        error_response = "HTTP/1.1 404 Not Found\r\n\r\nVideo not found."
        client_socket.sendall(error_response.encode())
        return

    file_size = os.path.getsize(video_path)

    start, end = 0, file_size - 1
    if range_header:
        range_values = range_header.replace("bytes=", "").split("-")
        start = int(range_values[0]) if range_values[0] else 0
        end = int(range_values[1]) if range_values[1] else file_size - 1

    with open(video_path, "rb") as video_file:
        video_file.seek(start)
        chunk = video_file.read(end - start + 1)

        response_header = (
            "HTTP/1.1 206 Partial Content\r\n"
            f"Content-Type: video/mp4\r\n"
            f"Content-Length: {len(chunk)}\r\n"
            f"Content-Range: bytes {start}-{end}/{file_size}\r\n"
            "Accept-Ranges: bytes\r\n\r\n"
        )
        client_socket.sendall(response_header.encode() + chunk)

# Lista os videos disponíveis
def send_video_list(client_socket):
    video_files = os.listdir(VIDEO_DIR)
    html_list = ""
    for video in video_files:
        thumbnail_path = f"/thumbnails/{video}.jpg"
        html_list += f"""
        <li>
            <img src="{thumbnail_path}" alt="{video}" style="width:160px;height:90px;">
            <br>
            <a href="/video/{video}">{video}</a>
        </li>
        """

    html = f"""
    <html>
    <head>
        <title>Videos Disponiveis</title>
    </head>
    <body>
        <h1>Videos Disponiveis</h1>
        <ul style="list-style-type:none;">
            {html_list}
        </ul>
    </body>
    </html>
    """
    response = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/html\r\n"
        "Content-Length: " + str(len(html)) + "\r\n\r\n" + html
    )
    client_socket.sendall(response.encode())

# Trata as requisições
def handle_client(client_socket):
    try:
        request = client_socket.recv(1024).decode()
        headers = request.split("\r\n")
        request_line = headers[0]
        method, path, _ = request_line.split()

        range_header = None
        for header in headers:
            if header.startswith("Range:"):
                range_header = header.split(": ", 1)[1]
                break

        if method == "GET":
            if path == "/":
                send_video_list(client_socket)
            elif path.startswith("/video/"):
                video_name = path[len("/video/"):]
                send_video_file(client_socket, video_name, range_header)
            elif path.startswith("/thumbnails/"):
                thumbnail_name = path[len("/thumbnails/"):]
                send_thumbnail(client_socket, thumbnail_name)
            else:
                response = "HTTP/1.1 404 Not Found\r\n\r\nResource not found."
                client_socket.sendall(response.encode())
        else:
            response = "HTTP/1.1 405 Method Not Allowed\r\n\r\nOnly GET is supported."
            client_socket.sendall(response.encode())
    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        client_socket.close()

ensure_thumbnails()
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(("0.0.0.0", 8080))
server_socket.listen(5)

print("Servidor alocado em http://127.0.0.1:8080")

while True:
    client_socket, addr = server_socket.accept()
    print(f"Conexão estabelecida")
    client_handler = threading.Thread(target=handle_client, args=(client_socket,))
    client_handler.start()
