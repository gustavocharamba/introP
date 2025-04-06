import numpy as np
from scipy.optimize import curve_fit
from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import *

def modelo_carregamento(t, tau, V_max):
    return V_max * (1 - np.exp(-t / tau))

def medir_capacitancia(R_valor_ohm, C_real_farads, V_pulso=5, periodo_inicial=0.03):
    erro_alvo = 2.0  # erro alvo (%)
    erro_atual = 100.0
    periodo = periodo_inicial
    max_iter = 15
    tentativa = 0

    while erro_atual > erro_alvo and tentativa < max_iter:
        tentativa += 1

        circuit = Circuit("Ajuste Automático de Período")
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

        time = np.array(analysis.time)
        voltage_out = np.array(analysis['vout'])

        janela = (time >= 0.001) & (time <= periodo / 2)
        time_ajuste = time[janela]
        voltage_ajuste = voltage_out[janela]

        chute_inicial = [R_valor_ohm * C_real_farads, V_pulso]

        try:
            param_otimos, covariancia = curve_fit(modelo_carregamento,
                                                  time_ajuste, voltage_ajuste,
                                                  p0=chute_inicial,
                                                  maxfev=5000)

            tau_estimado = param_otimos[0]
            Vmax_estimado = param_otimos[1]
            C_estimado = tau_estimado / R_valor_ohm
            erro_atual = abs(C_estimado - C_real_farads) / C_real_farads * 100
            razao_tau_periodo = tau_estimado / (periodo / 2)

            if erro_atual <= erro_alvo and 0.3 <= razao_tau_periodo <= 0.9:
                break

            if razao_tau_periodo > 0.9:
                periodo *= 1.2
            elif razao_tau_periodo < 0.3:
                periodo *= 0.8
            else:
                periodo *= 1.05

        except RuntimeError:
            periodo *= 1.2
            continue

    print(f'''\n{' RESULTADO DA MEDIÇÃO ':=^70}
Tentativas Necessárias: {tentativa}
Resistência: {R_valor_ohm:.0f} Ω
Tensão de Pulso: {V_pulso:.2f} V
Período Final da Onda: {periodo:.4f} s
Tau Estimado: {tau_estimado:.5e} s
Capacitância Estimada: {C_estimado:.3e} F
Erro Relativo: {erro_atual:.2f}%
{'='*70}''')

    return C_estimado, erro_atual, periodo

medir_capacitancia(R_valor_ohm=10_000, C_real_farads=17e-9, V_pulso=3, periodo_inicial=0.02)