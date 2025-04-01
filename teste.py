import usbtmc

# Listar dispositivos USBTMC
dispositivos = usbtmc.list_devices()
if dispositivos:
    for i in dispositivos:
        print(f"ID: {i}")
else:
    print("Nenhum dispositivo USBTMC encontrado.")
