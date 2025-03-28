import usb.core
import usb.util
from PySpice.Spice.Netlist import Circuit
from PySpice.Spice.NgSpice.Shared import NgSpiceShared
from scipy.optimize import curve_fit
import numpy as np
import matplotlib.pyplot as plt

NgSpiceShared.LIBRARY_PATH = r'C:\Program Files\Spice64_dll\dll-vs\ngspice-33.dll'  # Substitua pelo caminho correto

def resposta_teorica(t, V1, V0, tau):
    return (V1 - V0) * (1 - np.exp(-t / tau)) + V0


def simular_circuito_rc(R, C, T):
    circuit = Circuit("Circuito RC")
    circuit.V(1, 'input', circuit.gnd, 5)
    circuit.R(1, 'input', 'output', R)
    circuit.C(1, 'output', circuit.gnd, C)

    simulator = circuit.simulator(temperature=25)
    analysis = simulator.transient(step_time=1e-4, end_time=T)

    tempo = np.array(analysis.time)
    tensao_saida = np.array(analysis['output'])

    return tempo, tensao_saida


# Estimativa dos parâmetros do circuito usando ajuste de curva
def estimar_parametros(t_medido, vo_medido):
    popt, _ = curve_fit(resposta_teorica, t_medido, vo_medido, p0=[5, 0, 1e-3])
    V1_estimado, V0_estimado, tau_estimado = popt

    return V1_estimado, V0_estimado, tau_estimado


# Parâmetros iniciais do circuito
R = 1000  # Resistência em ohms
C = 1e-6  # Capacitância em farads (exemplo)
T = 0.01  # Período total da onda quadrada (10 ms)

print("Simulando circuito RC...")

# Simulação do circuito RC com PySpice
t_simulado, vo_simulado = simular_circuito_rc(R, C, T)

