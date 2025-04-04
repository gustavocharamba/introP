import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import *

# ==============================================
# Configuração do Circuito RC para caracterização
# ==============================================

circuit = Circuit("Medidor de Capacitância Dinâmico")

# Parâmetros do circuito
R_value = 10 @ u_kΩ  # Resistência padrão de referência
C_real = 1 @ u_nF    # Valor real usado na simulação

# Configuração da fonte de pulso retangular
circuit.PulseVoltageSource('input', 'vin', circuit.gnd,
                           initial_value=0 @ u_V,
                           pulsed_value=5 @ u_V,
                           pulse_width=15 @ u_ms,
                           period=30 @ u_ms,
                           rise_time=1 @ u_ns,
                           fall_time=1 @ u_ns)

circuit.R(1, 'vin', 'vout', R_value)
circuit.C(1, 'vout', circuit.gnd, C_real)

# ==============================================
# Simulação do Comportamento Dinâmico
# ==============================================

simulator = circuit.simulator()
analysis = simulator.transient(step_time=10 @ u_us, end_time=30 @ u_ms)

# Extração de dados formatados para numpy
time = np.array(analysis.time)
voltage_out = np.array(analysis['vout'])

# ==============================================
# Modelo Matemático e Ajuste de Curva
# ==============================================

def modelo_carregamento(t, tau, V_max):
    """Modelo teórico de carga do capacitor"""
    return V_max * (1 - np.exp(-t / tau))

# Seleciona janela de análise (exclui transientes iniciais)
janela_analise = (time >= 0.001) & (time <= 0.015)  # Ajuste para a região de carga
time_ajuste = time[janela_analise]
voltage_ajuste = voltage_out[janela_analise]

# Estimativa inicial inteligente (R*C típico para 1µF = 10ms)
R_ohm = float(R_value)
chute_inicial = [R_ohm * 1e-6, 5]  # Assume ~1µF como estimativa

# Executa ajuste não-linear
param_otimos, covariancia = curve_fit(modelo_carregamento,
                                      time_ajuste, voltage_ajuste,
                                      p0=chute_inicial,
                                      maxfev=5000)

tau_estimado = param_otimos[0]
Vmax_estimado = param_otimos[1]
C_estimado = tau_estimado / R_ohm

# Calcula incertezas
erros = np.sqrt(np.diag(covariancia))
incerteza_tau = erros[0]
incerteza_C = incerteza_tau / R_ohm

# ==============================================
# Visualização Profissional dos Resultados
# ==============================================

plt.style.use('seaborn-v0_8-notebook')
fig, ax = plt.subplots(figsize=(12, 7), dpi=300)

# Plot dados brutos
ax.plot(time, voltage_out, 'bo', markersize=4, alpha=0.6,
        label='Dados Simulados', markeredgewidth=0)

# Curva ajustada
ax.plot(time, modelo_carregamento(time, *param_otimos),
        'r-', linewidth=2.5,
        label=f'Ajuste: τ = {tau_estimado:.4f} s\nC = {C_estimado:.2e} F ± {incerteza_C:.1e} F')

# Configurações do gráfico
ax.set_title('Caracterização Dinâmica de Capacitor', fontsize=16)
ax.set_xlabel('Tempo (s)', fontsize=14)
ax.set_ylabel('Tensão (V)', fontsize=14)
ax.grid(True, linestyle="--", alpha=0.7)
ax.legend(fontsize=12)
ax.set_xlim([0, 0.02])
ax.set_ylim([-0.5, 5.5])

plt.tight_layout()
plt.show()

# ==============================================
# Saída Numérica Detalhada
# ==============================================

erro_relativo = abs(C_estimado - float(C_real)) * 1e6

print(f'''\n{' RESULTADOS DA CARACTERIZAÇÃO ':=^70}
Resistência de Referência: {float(R_value):.2f} {R_value.unit}
Tau Estimado: {tau_estimado:.5f} s ± {incerteza_tau:.5f} s
Capacitância Calculada: {C_estimado:.3e} F ± {incerteza_C:.1e} F
Erro Relativo: {erro_relativo:.2f}%''')
