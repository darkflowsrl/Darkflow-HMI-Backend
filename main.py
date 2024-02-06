from src.can_bus import reader_loop, write_on_bus_all_rpm, write_on_bus_test, buffer, port_config
from src.canbus_parser import *
from threading import Thread
from time import sleep
import socket
import json
import os

"""
Los siguientes comandos de linux sirven para levantar la interfaz can0
desde el hardware.
"""
os.system("ip link set can0 down")
os.system("ip link set can0 type can restart")
os.system("ip link set can0 type can bitrate 250000")
os.system("ip link set can0 up")

HOST: str = '192.168.1.39'
PORT: int = 8080
FAMILY: int = socket.AF_INET
TYPE: int = socket.SOCK_STREAM
CONNECTED: bool = False

sock = socket.socket(FAMILY, TYPE)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind((HOST, PORT))
sock.listen()
conn, add = sock.accept(); CONNECTED = True

"""
DOCUMENTACIÓN:
Se propone el siguiente protocolo actualizado:
Al utilizar el socket y no utilizar comandos, para saber a que proceso
corresponde cada mensaje, se utilizará la variable command.

Protocolo de testing:
{
    command : "testing",
    nodos :  [1030, 1230, 1150]
}

Protocolo de funcionamiento normal:
{
    command : "normal",
    nodo : 1030,
    rpm1 : 2000,
    rpm2 : 2500,
    rpm3 : 1000,
    rpm4 : 0,
}

Protocolo de datos meteorológicos:
{
    command : "datosMeteorologicos",
    humedad : 78,
    velViento : 34,
    dirViento : 180,
    temperatura : 25,
    puntoDeRocio : 25
}

Protocolo de estado general del nodo:
{
    command : "estadoGeneralNodo",
    nodo : 1030,
    state1 : 3.1,
    state2 : 3.2,
    state3 : 3.3,
    state4 : 6.2,
    corr1 : 2000,
    corr2 : 2500,
    corr3 : 2000,
    corr4 : 500,
    rpm1 : 3.1,
    rpm2 : 3.2,
    rpm3 : 3.3,
    rpm4 : 6.2,
    voltaje : 12.8
}
"""

def send_data_over_socket() -> None:
    global CONNECTED
    while True:
        try:
            while True:
                if not CONNECTED:
                    break
                
                data_meteor = json.dumps(buffer.parse_meteor()).encode()
                data_node_data = json.dumps(buffer.parse_node()).encode()
                sleep(0.5)
                conn.sendall(data_meteor)
                sleep(0.5)
                conn.sendall(data_node_data)
                
        except Exception as e:
            CONNECTED = False
            print("[error] send_data_over_socket")
            print(e)
            
def send_data_over_node() -> None:
    global CONNECTED
    while True:
        try:
            while True:
                if not CONNECTED:
                    global conn, add
                    conn, add = sock.accept(); CONNECTED = True
                    break
                data = conn.recv(1024)
                if not data: break
                data = json.loads(data)
                command: str = data["command"] 

                if command == "testing":
                    for node in data["nodes"]:
                        write_on_bus_test(bus_config=port_config,
                                        params=BoardTest(node))
                elif command == "normal":
                    write_on_bus_all_rpm(bus_config=port_config,
                                            params=BoardParams(data["nodo"],
                                                        data["rpm1"],
                                                        data["rpm2"],
                                                        data["rpm3"],
                                                        data["rpm4"]))                         
        except Exception as e: 
            CONNECTED = False
            print("[error] send_data_over_node")
            print(e)
    
if __name__ == '__main__':
    while True:
        task_read = Thread(target=reader_loop, args=(port_config,))
        task_write_into_front = Thread(target=send_data_over_socket)
        task_write_into_node = Thread(target=send_data_over_node)

        task_read.start()
        task_write_into_front.start()
        task_write_into_node.start()
        
        task_read.join()
        task_write_into_front.join()
        task_write_into_node.join()