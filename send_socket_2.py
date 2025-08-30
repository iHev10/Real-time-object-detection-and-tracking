from queue import Queue
import socket
import time
import yaml

from PyQt6.QtCore import QThread, QMutex, QWaitCondition


with open('config.yaml', 'r') as f:
    config = yaml.load(f, Loader=yaml.SafeLoader)


class SocketThread2(QThread):
    def __init__(self):
        super().__init__()
        self.running = False
        self.data_queue = Queue(maxsize=1)
        self.mutex = QMutex()
        self.condition = QWaitCondition()
        self.socket = None
        self.host = config.get("HOST2")
        self.port = config.get("PORT2")
        
    def add_data(self, data):
        self.mutex.lock()
        if self.data_queue.qsize() < self.data_queue.maxsize:
            self.data_queue.put(data.copy())
            self.condition.wakeAll()
        self.mutex.unlock()

    def run(self):
        self.running = True
        self.connect_socket()

        while self.running:
            self.mutex.lock()
            if self.data_queue.empty():
                self.condition.wait(self.mutex)

            if not self.running:
                self.mutex.unlock()
                break

            data = self.data_queue.get()
            self.mutex.unlock()

            self.send_to_pico(data)

        self.socket.close()

    def connect_socket(self):
        try:
            self.socket = socket.socket()
            self.socket.bind(('', self.port))
            print(f'socket binded to port {self.port}')
            self.socket.listen(4)
            print('socket is listening')
        except Exception as e:
            print(f"Socket connection failed: {e}")

    def send_to_pico(self, data):
        try:
            message =\
                f"{data.get('flag', 0)}_" \
                f"{data.get('pan', 0)}_" \
                f"{data.get('tilt', 0)}\n" 

            print("transmitted data to jetson: " + message)
            c, addr = self.socket.accept()
            # print('got connection from', addr)
            c.send(message.encode())
            
            print("recieved data from jetson: " + c.recv(1024).decode())
            print("____________________________________________________")
        except Exception as e:
            print(f"Send error: {e}")
            self.reconnect_socket()

    def reconnect_socket(self):
        try:
            self.socket.close()
        except:
            pass
        time.sleep(1)
        self.connect_socket()

    def stop(self):
        self.running = False
        print("----------------------------------------------------------------")
        self.condition.wakeAll()
        self.wait()
