import threading
import time
import random
import paho.mqtt.client as mqtt

# Configurações iniciais
CITY_WIDTH = 1000
CITY_HEIGHT = 1000
STREET_WIDTH = 10
MAX_SPEED = 5
UPDATE_INTERVAL = 1  # Segundos


# Classe de comunicação via MQTT e chamadas de função
class Communication:
    def __init__(self):
        self.clients = {}
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.connect("127.0.0.1", 1883, 60)
        self.mqtt_client.loop_start()

    def register(self, name, callback):
        self.clients[name] = callback
        self.mqtt_client.subscribe(name)

    def send(self, destination, message):
        if destination in self.clients:
            self.clients[destination](message)
        else:
            self.mqtt_client.publish(destination, message)

    def on_message(self, client, userdata, msg):
        if msg.topic in self.clients:
            self.clients[msg.topic](msg.payload.decode())


# Classe da Central de Controle
class ControlCenter:
    def __init__(self, comms):
        self.comms = comms
        self.vehicles = {}
        self.lock = threading.Lock()
        self.history = {}
        comms.register("control_center", self.receive_message)

    def register_vehicle(self, vehicle):
        with self.lock:
            self.vehicles[vehicle.id] = vehicle
            self.history[vehicle.id] = []

    def receive_message(self, message):
        print(f"Central recebeu mensagem: {message}")

    def assign_vehicle(self, person_id, position):
        with self.lock:
            for vehicle in self.vehicles.values():
                if vehicle.available:
                    vehicle.set_destination(position)
                    return vehicle.id
        return None

    def update_vehicle_status(self, vehicle_id, position, speed):
        with self.lock:
            self.history[vehicle_id].append((position, speed))
            print(f"Atualizando veículo {vehicle_id} posição {position} e velocidade {speed}")


# Classe do Veículo Autônomo
class Vehicle(threading.Thread):
    def __init__(self, vehicle_id, position, comms):
        super().__init__()
        self.id = vehicle_id
        self.position = position
        self.speed = 0
        self.destination = None
        self.available = True
        self.comms = comms
        self.lock = threading.Lock()
        comms.register(self.id, self.receive_message)

    def run(self):
        while True:
            time.sleep(UPDATE_INTERVAL)
            with self.lock:
                if self.destination:
                    self.move()
                self.comms.send("control_center", f"{self.id},{self.position},{self.speed}")

    def move(self):
        if self.position != self.destination:
            self.speed = MAX_SPEED
            self.position = (self.position[0] + self.speed, self.position[1] + self.speed)
        else:
            self.speed = 0
            self.available = True
            self.destination = None
            self.comms.send("control_center", f"{self.id} chegou ao destino")

    def set_destination(self, destination):
        with self.lock:
            self.destination = destination
            self.available = False

    def receive_message(self, message):
        print(f"Veículo {self.id} recebeu: {message}")


# Simulação
comms = Communication()
control_center = ControlCenter(comms)

# Criando veículos
vehicles = [Vehicle(f"car_{i}", (random.randint(0, CITY_WIDTH), random.randint(0, CITY_HEIGHT)), comms) for i in
            range(5)]
for vehicle in vehicles:
    control_center.register_vehicle(vehicle)
    vehicle.start()

# Criando uma solicitação de transporte
person_position = (500, 500)
assigned_vehicle = control_center.assign_vehicle("person_1", person_position)
print(f"Veículo {assigned_vehicle} atribuído para buscar a pessoa em {person_position}")