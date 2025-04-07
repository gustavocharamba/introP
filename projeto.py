import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import *


# Modelo matemático de carregamento do capacitor
def modelo_carregamento(t, tau, V_max):
    return V_max * (1 - np.exp(-t / tau))


# Função para simular o circuito RC com NgSpice
def simular_circuito_ngspice(R_valor_ohm, C_real_farads, V_pulso=5, periodo=0.03):
    """
    Simula um circuito RC usando NgSpice e retorna os dados simulados.

    Parâmetros:
    - R_valor_ohm: Resistência em ohms.
    - C_real_farads: Capacitância real em farads.
    - V_pulso: Tensão máxima do pulso (em volts).
    - periodo: Período da onda quadrada (em segundos).

    Retorna:
    - time: Array de tempo (s).
    - voltage_out: Array de tensão no capacitor (V).
    """
    circuit = Circuit("Simulação Circuito RC")
    circuit.PulseVoltageSource('input', 'vin', circuit.gnd,
                               initial_value=0 @ u_V,
                               pulsed_value=V_pulso @ u_V,
                               pulse_width=(periodo / 2) @ u_s,
                               period=periodo @ u_s,
                               rise_time=1 @ u_ns,
                               fall_time=1 @ u_ns)
    circuit.R(1, 'vin', 'vout', R_valor_ohm @ u_Ω)
    circuit.C(1, 'vout', circuit.gnd, C_real_farads @ u_F)

    simulator = circuit.simulator()
    analysis = simulator.transient(step_time=10 @ u_us, end_time=periodo @ u_s)

    # Extrair os dados simulados
    time = np.array(analysis.time)
    voltage_out = np.array(analysis['vout'])

    return time, voltage_out


# Função para ler dados do CSV
def ler_dados_csv(file_path):
    """
    Lê os dados de um arquivo CSV contendo tempo e tensão e retorna os arrays correspondentes.

    Parâmetros:
    - file_path: Caminho para o arquivo CSV.

    Retorna:
    - time: Array de tempo (s).
    - voltage: Array de tensão no capacitor (V).
    """
    data = pd.read_csv(file_path)

    # Limpar e organizar os dados
    cleaned_data = data.iloc[1:]  # Ignorar cabeçalhos adicionais
    cleaned_data.columns = ['time', 'voltage']  # Renomear colunas
    cleaned_data['time'] = pd.to_numeric(cleaned_data['time'], errors='coerce')  # Converter tempo para numérico
    cleaned_data['voltage'] = pd.to_numeric(cleaned_data['voltage'], errors='coerce')  # Converter tensão para numérico
    cleaned_data = cleaned_data.dropna()  # Remover linhas inválidas

    # Extrair arrays de tempo e tensão
    time = cleaned_data['time'].values
    voltage = cleaned_data['voltage'].values

    return time, voltage


# Função principal para medir a capacitância
def medir_capacitancia(R_valor_ohm=None, C_real_farads=None, V_pulso=5, periodo_inicial=0.03,
                       file_path=None):
    """
    Mede a capacitância usando dados simulados ou um arquivo CSV.

    Parâmetros:
    - R_valor_ohm: Resistência em ohms (necessário para simulação).
    - C_real_farads: Capacitância real em farads (necessário para simulação).
    - V_pulso: Tensão máxima do pulso (em volts) [apenas para simulação].
    - periodo_inicial: Período inicial da onda quadrada [apenas para simulação].
    - file_path: Caminho para o arquivo CSV contendo os dados.

    Retorna:
    - Capacitância estimada (F), constante de tempo estimada (s), erro relativo (%).
    """

    if file_path is not None:
        # Ler dados do CSV
        time, voltage_out = ler_dados_csv(file_path)
        chute_inicial = [1e-3, max(voltage_out)]  # Chute inicial genérico para ajuste

        print("Usando dados do CSV...")

        # Ajustar período genérico baseado nos dados do CSV
        periodo = time[-1] * 2  # Supõe que o tempo final seja metade do período total

    elif R_valor_ohm is not None and C_real_farads is not None:
        # Simular circuito com NgSpice
        print("Simulando circuito com NgSpice...")
        periodo = periodo_inicial
        time, voltage_out = simular_circuito_ngspice(R_valor_ohm, C_real_farads, V_pulso, periodo)
        chute_inicial = [R_valor_ohm * C_real_farads, V_pulso]

    else:
        raise ValueError("Você deve fornecer um arquivo CSV ou os parâmetros R_valor_ohm e C_real_farads.")

    try:
        # Ajustar a curva usando o modelo de carregamento exponencial
        param_otimos, _ = curve_fit(modelo_carregamento, time, voltage_out, p0=chute_inicial)

        tau_estimado = param_otimos[0]
        Vmax_estimado = param_otimos[1]

        if R_valor_ohm is not None:
            C_estimado = tau_estimado / R_valor_ohm  # Calcular capacitância se a resistência for conhecida
            erro_relativo = abs(C_estimado - C_real_farads) / C_real_farads * 100 if C_real_farads else None
        else:
            C_estimado = None
            erro_relativo = None

        print(f'''\n{' RESULTADO DA MEDIÇÃO ':=^70}
Constante de Tempo Estimada (Tau): {tau_estimado:.5e} s
Tensão Máxima Estimada (V_max): {Vmax_estimado:.3f} V''')

        if C_estimado is not None:
            print(f'''Capacitância Estimada: {C_estimado:.3e} F
Erro Relativo: {erro_relativo:.2f}%''')

        print('=' * 70)

        return C_estimado, tau_estimado, erro_relativo

    except RuntimeError:
        print("Erro: Não foi possível ajustar os dados ao modelo.")
        return None, None, None


# Exemplo de uso com NgSpice:
medir_capacitancia(R_valor_ohm=10_000, C_real_farads=17e-9, V_pulso=3)

# Exemplo de uso com CSV:
# medir_capacitancia(file_path='dados_osciloscopio.csv')
