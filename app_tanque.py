# app_tempo_real.py
# Tanque de 5 L em tempo real. Página inicial com modelagem + simulador.
# Rodar: streamlit run app_tempo_real.py
# Dependências: streamlit numpy pandas matplotlib openpyxl

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

st.set_page_config(page_title="Tanque 5 L — modelagem e simulação", layout="wide")

# ============================================================
# FAIXAS DA REGRESSÃO (do experimento)
# ============================================================
CMC_G_MIN, CMC_G_MAX = 3.0, 7.0          # g de CMC por amostra
BAR_G_MIN, BAR_G_MAX = 46.0, 336.0       # g de barita por amostra
V_AMOSTRA_L = 1.0                         # volume da amostra (L) — AJUSTE se necessário

# Concentrações equivalentes na faixa da regressão [g/L]
C_CMC_MIN = CMC_G_MIN / V_AMOSTRA_L       # 3 g/L
C_CMC_MAX = CMC_G_MAX / V_AMOSTRA_L       # 7 g/L
C_BAR_MIN = BAR_G_MIN / V_AMOSTRA_L       # 46 g/L
C_BAR_MAX = BAR_G_MAX / V_AMOSTRA_L       # 336 g/L

# ============================================================
# NAVEGAÇÃO
# ============================================================
if "pagina" not in st.session_state:
    st.session_state.pagina = "Modelagem"

pagina = st.sidebar.radio(
    "Navegação",
    ["Modelagem", "Simulador"],
    index=0 if st.session_state.pagina == "Modelagem" else 1,
    key="nav",
)
st.session_state.pagina = pagina

# ============================================================
# PÁGINA 1 — MODELAGEM
# ============================================================
if pagina == "Modelagem":
    st.title("Modelagem do tanque de mistura")
    st.caption("Documentação das equações, método de solução, parâmetros e modo de uso.")

    st.header("1. Descrição do sistema")
    st.markdown(r"""
Um tanque de **mistura perfeita (CSTR)** de capacidade $V_{max}=5\ \mathrm{L}$, com
**vertedouro** na altura de $V_{max}$, recebe **três correntes de entrada** e é
esvaziado por uma bomba de saída:

- **Lama de barita** (vazão $Q_b$): barita em água, com concentração ajustável $C_{f,b}$.
- **Solução de CMC** (vazão $Q_c$): CMC em água, com concentração ajustável $C_{f,c}$.
- **Água pura** (vazão $Q_a$): serve para **diluir** e é o que permite fixar
  $C_{bar}$ e $C_{cmc}$ no tanque de forma **independente**.

O tanque é de **mistura perfeita**: a corrente de saída (bomba + vertedouro) tem a
**mesma composição do conteúdo do tanque**. Escala de bancada: as vazões são da
ordem de **mL/s**.

**Por que três correntes?** Com apenas barita e CMC, as duas concentrações ficam
acopladas pela razão $Q_b/Q_c$ e não é possível percorrer toda a faixa
experimental. Com a água como terceira entrada, qualquer ponto da caixa
$[C_{bar,min};C_{bar,max}]\times[C_{cmc,min};C_{cmc,max}]$ é alcançável, desde que as
alimentações sejam mais concentradas que o alvo (seção 8).
    """)

    st.header("2. Faixa de validade da regressão")
    st.markdown(rf"""
A regressão de viscosidade foi ajustada com amostras contendo:

- **CMC:** {CMC_G_MIN:.0f}–{CMC_G_MAX:.0f} g por amostra (3,28 a 6,70 g na planilha)
- **barita:** {BAR_G_MIN:.0f}–{BAR_G_MAX:.0f} g por amostra
- **volume da amostra:** {V_AMOSTRA_L:.1f} L (ajustável no código)

Concentrações equivalentes (faixa em que a regressão é válida):

- **$C_{{cmc}}$:** {C_CMC_MIN:.1f}–{C_CMC_MAX:.1f} g/L
- **$C_{{bar}}$:** {C_BAR_MIN:.1f}–{C_BAR_MAX:.1f} g/L

**Fora dessa faixa, a regressão extrapola** e o valor de μ deixa de ser confiável.
O simulador exibe um alerta sempre que as concentrações saem da faixa.
O **objetivo do simulador** é operar o tanque **dentro** dessa faixa, em qualquer ponto
dela, e acompanhar a viscosidade resultante.
    """)

    st.header("3. Variáveis de estado")
    st.markdown(r"""
| Símbolo | Significado | Unidade |
|---|---|---|
| $V$ | volume de mistura no tanque | m³ |
| $m_f$ | massa de fluido base (água) | kg |
| $m_b$ | massa de barita | kg |
| $m_c$ | massa de CMC | kg |

Massa total: $m = m_f + m_b + m_c$. Densidade do tanque (e da saída):
$\rho = m/V$. Concentrações: $C_{bar} = m_b/V$ e $C_{cmc} = m_c/V$
(kg/m³ ≡ g/L, numericamente iguais).
    """)

    st.header("4. Correntes de alimentação")
    st.markdown(r"""
Cada lama é definida por **uma única grandeza**: a massa de sólido por litro de
mistura, $C_f$ (g/L). Assumindo **volumes aditivos** (sólido + água), a densidade e a
fração mássica de sólido da corrente são:

$$
\rho_{corr} = C_f + 1000\left(1 - \frac{C_f}{\rho_s}\right), \qquad
w = \frac{C_f}{\rho_{corr}}
$$

com $\rho_{s,bar} = 4200\ \mathrm{kg/m^3}$ (barita) e
$\rho_{s,cmc} = 1600\ \mathrm{kg/m^3}$ (CMC). Assim, por construção,
$\rho_{corr}\,w = C_f$: **cada 1 mL/s da corrente entrega $C_f$ mg/s de sólido**.

| Corrente | $C_f$ padrão | $\rho_{corr}$ | $w$ |
|---|---|---|---|
| Lama de barita | 500 g/L | 1381,0 kg/m³ | 0,362 |
| Solução de CMC | 30 g/L | 1011,2 kg/m³ | 0,0297 |
| Água | — | 1000 kg/m³ | 0 |

Ambas as concentrações são **sliders** na barra lateral. A de barita deve ser
**maior que a barita máxima desejada** no tanque ($> 336$ g/L) e a de CMC maior que a
CMC máxima ($> 6{,}7$ g/L); caso contrário o alvo é inviável.
    """)

    st.header("5. Equações diferenciais (EDOs)")
    st.markdown(r"""
O balanço de massa global e por componente, com mistura perfeita e vertedouro, é:

$$
\begin{aligned}
\frac{dV}{dt} &= Q_b + Q_c + Q_a - Q_s - Q_{ov} \\[4pt]
\frac{dm_f}{dt} &= Q_b\,\rho_b(1-w_b) + Q_c\,\rho_c(1-w_c) + Q_a\,\rho_a - (Q_s+Q_{ov})\,\rho\,\frac{m_f}{m} \\[4pt]
\frac{dm_b}{dt} &= Q_b\,\rho_b\,w_b - (Q_s+Q_{ov})\,\rho\,\frac{m_b}{m} \\[4pt]
\frac{dm_c}{dt} &= Q_c\,\rho_c\,w_c - (Q_s+Q_{ov})\,\rho\,\frac{m_c}{m}
\end{aligned}
$$

Aqui $\rho_b$, $\rho_c$ e $\rho_a$ são as **densidades das correntes** (seção 4). A
água entra apenas no balanço de $m_f$, pois não carrega sólido.

**Bomba de saída.** Há dois modos:

- **Manter nível** (padrão): $Q_s = Q_b + Q_c + Q_a$, e o volume fica constante em $V_0$.
- **Manual**: $Q_s$ é o valor do slider. Nesse caso $V$ é a integral de
  $Q_{in}-Q_s$ e pode derivar.

A bomba nunca puxa mais do que existe: $Q_s^{\text{efetivo}} = \min(Q_s,\ Q_{in}+V/\Delta t)$.

**Vertedouro.** Se a integração levar $V$ acima de $V_{max}$:

$$
Q_{ov} = \max\!\left(0,\ \frac{V + (Q_{in}-Q_s)\Delta t - V_{max}}{\Delta t}\right),
\qquad V \leftarrow \min(V, V_{max}).
$$

O vertedouro **arrasta sólido** (sai com a composição do tanque), por isso $Q_{ov}$
multiplica $\rho\,m_i/m$ nos balanços de componente.

**Limite de concentração de sólidos.** Para evitar lodo fisicamente impossível:

$$
\frac{m_b}{m} \le \varphi_b^{max} = 0{,}40, \qquad
\frac{m_c}{m} \le \varphi_c^{max} = 0{,}20.
$$

Ao atingir o limite, a massa em excesso é descartada e o painel exibe um alerta.
    """)

    st.header("6. Propriedades de saída")
    st.markdown(r"""
**Densidade de saída** (mistura perfeita):

$$
\rho_{out} = \rho = \frac{m_f+m_b+m_c}{V}.
$$

**Viscosidade aparente** — regressão linear ajustada aos dados experimentais
(médias por combinação CMC × barita):

$$
\mu = a + b\,C_{cmc} + c\,C_{bar},
$$

com $C_{cmc}$ e $C_{bar}$ em **g/L** (numericamente iguais aos gramas por amostra de
1 L). O valor é saturado em $[1;\ 500]\ \mathrm{cP}$ apenas para evitar números
absurdos; o valor **bruto** (antes da saturação) também é avaliado como diagnóstico.
Quando o bruto sai dessa faixa, a regressão está extrapolando.

**Sem a planilha carregada, μ fica indisponível**: o simulador mostra apenas
densidade, volume e concentrações.
    """)

    st.header("7. Atingindo um alvo no regime estacionário")
    st.markdown(r"""
**O que é o "alvo".** É a **concentração final** que você quer no tanque
($C_{bar}^*$ e $C_{cmc}^*$), isto é, o ponto em que ele vai se **estabilizar**. O
bloco "Alvo no tanque" é uma **calculadora de vazões**, não um controlador:

1. você escolhe $C_{bar}^*$, $C_{cmc}^*$ (dentro da faixa da regressão) e a vazão total $Q_{in}$;
2. o app calcula quanto de barita, CMC e água precisa entrar para o tanque **tender** a essa composição (ou avisa que o alvo é inviável);
3. o botão **"Aplicar vazões do alvo"** coloca essas vazões nas entradas.

O tanque **não salta** para o alvo: ele **caminha** até lá, partindo da condição
inicial, com constante de tempo $\tau = V/Q_{in}$. Chegando lá, permanece, a menos que
as vazões sejam alteradas.

Com nível constante e $Q_{in} = Q_b+Q_c+Q_a$, o tanque tende a

$$
C_{bar}^{\infty} = \frac{Q_b\,C_{f,b}}{Q_{in}}, \qquad
C_{cmc}^{\infty} = \frac{Q_c\,C_{f,c}}{Q_{in}}.
$$

Invertendo, para um alvo $(C_{bar}^*, C_{cmc}^*)$ e uma vazão total $Q_{in}$:

$$
Q_b = Q_{in}\,\frac{C_{bar}^*}{C_{f,b}}, \qquad
Q_c = Q_{in}\,\frac{C_{cmc}^*}{C_{f,c}}, \qquad
Q_a = Q_{in} - Q_b - Q_c.
$$

O alvo só é **viável** se $Q_a \ge 0$, isto é,

$$
\frac{C_{bar}^*}{C_{f,b}} + \frac{C_{cmc}^*}{C_{f,c}} \le 1.
$$

O bloco **"Alvo no tanque"** da barra lateral faz essa conta e o botão
**"Aplicar vazões do alvo"** preenche os sliders. Com os valores padrão, a fração de
água $Q_a/Q_{in}$ nos cantos da faixa experimental é:

| $C_{bar}$ [g/L] | $C_{cmc}$ [g/L] | $Q_a/Q_{in}$ |
|---|---|---|
| 46,1 | 3,28 | 0,80 |
| 336,1 | 3,28 | 0,22 |
| 46,1 | 6,70 | 0,68 |
| 336,1 | 6,70 | 0,10 |

O tempo para chegar ao alvo é da ordem de $\tau = V/Q_{in}$ (≈ 400 s para 4 L e
10 mL/s); após cerca de $3\tau$ o tanque está a ~95% do alvo.
    """)

    st.header("8. Método de solução")
    st.markdown(r"""
- **Integração no tempo:** Euler explícito com subpassos de
  $\Delta t = 0{,}05\ \mathrm{s}$ simulados. A cada atualização do painel, o tempo
  simulado avança $\Delta t_{sim} = \Delta t_{real}\times\text{velocidade}$.
- **Atualização em tempo real:** `st.fragment(run_every=Δt_real)` re-renderiza só o
  painel a cada $\Delta t_{real}$ segundos reais, sem reiniciar a página.
- **Estado persistente** em `st.session_state`, então o histórico não se perde.
- **Estabilidade:** com $\tau = V/Q \sim 400\ \mathrm{s} \gg \Delta t = 0{,}05\ \mathrm{s}$,
  o Euler explícito é estável e preciso.
- **Vertedouro:** projeção ($V_{pred}$) seguida de correção, garantindo
  $V \le V_{max}$ a cada passo.
- **Limite de sólidos:** truncamento de $m_b$ e $m_c$ após o passo.
- **Alertas:** quando $C_{cmc}$, $C_{bar}$ ou μ bruto saem da faixa de validade.
    """)

    st.header("9. Condição inicial")
    st.markdown(r"""
O volume inicial é $V_0 = 4{,}0\ \mathrm{L}$. As concentrações iniciais são
**sliders** ($C_{bar,0}$ e $C_{cmc,0}$), aplicados ao clicar em **↺ Reiniciar**; por
padrão o tanque começa no **canto inferior da faixa** (46,1 g/L de barita e 3,28 g/L
de CMC). Então:

$$
m_{b,0} = C_{bar,0}\,V_0, \qquad m_{c,0} = C_{cmc,0}\,V_0, \qquad
m_{f,0} = 1000\left(V_0 - \frac{m_{b,0}}{\rho_{s,bar}} - \frac{m_{c,0}}{\rho_{s,cmc}}\right),
$$

ou seja, a água completa o volume $V_0$ com os sólidos (volumes aditivos), e
$\rho_0 = (m_{f,0}+m_{b,0}+m_{c,0})/V_0$.

**O simulador não começa em regime estacionário.** Ele começa nessa condição inicial
com as **três vazões em zero**: sem vazão, nada muda e a composição fica parada. Ao
aplicar vazões, a composição se move rumo ao estacionário dessas vazões (seção 7),
levando cerca de $3\tau$ para chegar a ~95% dele. Para $V_0 = 4\ \mathrm{L}$ e
$Q_{in} = 10\ \mathrm{mL/s}$, $\tau \approx 400\ \mathrm{s}$, ou seja, cerca de 20 min
simulados.

Dois modos de uso:

- **Partir já no estacionário de um ponto:** ajuste $C_{bar,0}$ e $C_{cmc,0}$ iguais ao
  alvo, clique em **↺ Reiniciar**, aplique as vazões do alvo e inicie. A composição
  fica constante desde o primeiro instante.
- **Simular a passagem de um ponto a outro:** comece em um ponto (condição inicial) e
  aplique o alvo do outro. O gráfico mostra o transiente entre os dois.
    """)

    st.header("10. Como usar o simulador")
    st.markdown(r"""
1. Vá para a página **Simulador**.
2. **Suba a planilha** (`Valores de entrada`: CMC, barita; `Valores de saída`: μ).
   Sem ela, μ fica indisponível.
3. Defina as **concentrações das lamas de alimentação** (maiores que os máximos desejados).
4. Escolha o **alvo** ($C_{bar}^*$, $C_{cmc}^*$) e a **vazão total**; clique em
   **Aplicar vazões do alvo**.
5. Clique em **▶ Iniciar**. O tanque evolui da condição inicial até o alvo.
6. Para **varrer a faixa**, mude o alvo e aplique de novo, sem reiniciar. Você também
   pode ajustar à mão: os botões **+ / −** de cada corrente **somam ou subtraem** (de
   1 em 1 mL/s, ou o passo que você escolher) à vazão que já está entrando. A vazão
   atual de cada corrente aparece na barra lateral e no painel.
7. **⏸ Pausar** congela; **▶ Retomar** continua; **↺ Reiniciar** volta à condição
   inicial (mantendo a planilha).
    """)

    st.header("11. Observações importantes")
    st.markdown(rf"""
- **Concentração no tanque ≠ concentração na alimentação.** O tanque só chega em
  $C_{{f,b}}$ se não houver diluição; em geral fica em $Q_b C_{{f,b}}/Q_{{in}}$.
- **Reduzir $Q_b$ sozinho não derruba $\rho$ imediatamente**: parar de alimentar não
  remove o sólido já no tanque. A concentração cai com a escala de tempo $V/Q_{{in}}$,
  mais rápido se $Q_a$ aumentar.
- **Nível constante:** com "Manter nível" ligado, $V$ fica em $V_0$ e o vertedouro não
  atua. Desligando, $V$ deriva se $Q_{{in}}\ne Q_s$ e só o vertedouro segura em
  $V_{{max}}$.
- **Faixa da regressão:** $C_{{cmc}} \in [{C_CMC_MIN:.1f},\,{C_CMC_MAX:.1f}]$ g/L e
  $C_{{bar}} \in [{C_BAR_MIN:.0f},\,{C_BAR_MAX:.0f}]$ g/L. Fora disso, μ é extrapolação
  e o simulador avisa.
- **Sal:** a planilha varia o teor de sal (66 a 139), mas a regressão atual usa
  **apenas CMC e barita**. Se o sal influenciar a viscosidade, o ajuste carrega esse
  erro como ruído.
- **Alimentação de CMC concentrada** (padrão 30 g/L) é escolha de modelagem para dar
  folga de diluição; na prática, uma solução tão concentrada é muito viscosa. Ajuste
  conforme o que for possível preparar.
- **Volumes aditivos:** a densidade das correntes e do tanque assume que sólido e água
  não alteram o volume um do outro; CMC hidratada pode desviar disso.
- **Unidades:** $1\ \mathrm{{kg/m^3}} = 1\ \mathrm{{g/L}}$. As concentrações do tanque são
  $m_i/V$ em kg/m³, que já é g/L, sem fator de 1000.
    """)

# ============================================================
# PÁGINA 2 — SIMULADOR
# ============================================================
else:
    st.title("Tanque de 5 L em tempo real")
    st.caption("Três entradas (barita, CMC, água). Use \"Alvo no tanque\" na barra lateral para varrer toda a faixa da regressão.")

    # ---------------- PARÂMETROS FÍSICOS ----------------
    # Três correntes de entrada: lama de barita, solução de CMC e ÁGUA pura.
    # A água permite fixar C_barita e C_CMC de forma independente em qualquer
    # ponto da caixa [C_BAR_MIN, C_BAR_MAX] x [C_CMC_MIN, C_CMC_MAX].
    RHO_S_BAR, RHO_S_CMC = 4200.0, 1600.0     # densidade dos sólidos [kg/m3]

    st.sidebar.header("Correntes de alimentação")
    CF_B = st.sidebar.slider("Lama de barita [g de barita/L de lama]", 100.0, 1000.0, 500.0, 10.0,
                             help="Precisa ser MAIOR que a barita máxima desejada no tanque.")
    CF_C = st.sidebar.slider("Solução de CMC [g de CMC/L de solução]", 5.0, 100.0, 30.0, 1.0,
                             help="Precisa ser MAIOR que a CMC máxima desejada no tanque.")

    def propriedades_corrente(cf, rho_s):
        """Corrente com cf g de sólido por litro de mistura (volumes aditivos)."""
        rho = cf + 1000.0 * (1.0 - cf / rho_s)    # kg/m3
        return rho, cf / rho                       # densidade, fração mássica

    RHO_B, W_B = propriedades_corrente(CF_B, RHO_S_BAR)
    RHO_C, W_C = propriedades_corrente(CF_C, RHO_S_CMC)
    RHO_A = 1000.0

    QS_NOM = 0.010                    # L/s
    V_MAX = 0.005                     # m³
    V0    = 0.004                     # m³

    st.sidebar.header("Condição inicial (aplicada em ↺ Reiniciar)")
    CB_INI = st.sidebar.slider("C_barita inicial [g/L]", 0.0, 400.0, float(C_BAR_MIN), 1.0)
    CC_INI = st.sidebar.slider("C_CMC inicial [g/L]", 0.0, 10.0, float(C_CMC_MIN), 0.1)
    MB0   = CB_INI * V0               # kg  (g/L x m³ = kg)
    MC0   = CC_INI * V0               # kg
    MF0   = 1000.0 * (V0 - MB0/RHO_S_BAR - MC0/RHO_S_CMC)   # água que completa V0
    M0    = MF0 + MB0 + MC0
    RHO0  = M0 / V0
    MU_MIN, MU_MAX = 1.0, 500.0
    MU_EIXO_MAX = 20.0                # limite superior só do EIXO do gráfico de μ [cP]

    PHI_B_MAX = 0.40
    PHI_C_MAX = 0.20

    def estado_inicial():
        rho0 = (MF0 + MB0 + MC0) / V0
        return {
            "t": 0.0,
            "V": V0, "mf": MF0, "mb": MB0, "mc": MC0,
            "hist_t": [0.0], "hist_rho": [rho0],
            "hist_V": [V0], "hist_mu": [np.nan], "hist_mu_raw": [np.nan],
            "hist_Cb": [MB0/V0], "hist_Cc": [MC0/V0],
            "hist_Qout": [0.0], "hist_Qov": [0.0],
            "hist_sat": [0],
            "rodando": False, "iniciado": False,
            "Qb": 0.0, "Qc": 0.0, "Qa": 0.0,
            "coef_mu": None,
        }

    if "tanque" not in st.session_state:
        st.session_state.tanque = estado_inicial()
    S = st.session_state.tanque
    S.setdefault("Qa", 0.0)

    # ---------------- UPLOAD ----------------
    st.sidebar.header("Planilha da viscosidade")
    arquivo = st.sidebar.file_uploader(
        "Excel com abas 'Valores de entrada' (CMC, barita) e 'Valores de saída' (μ)",
        type=["xlsx"], key="upload",
    )
    if arquivo is not None and S["coef_mu"] is None:
        try:
            ent = pd.read_excel(arquivo, sheet_name='Valores de entrada')
            sai = pd.read_excel(arquivo, sheet_name='Valores de saída')
            dados = pd.DataFrame({
                'cmc':    ent.iloc[1:, 0].to_numpy(float),
                'barita': ent.iloc[1:, 1].to_numpy(float),
                'mu':     sai.iloc[:-1, 1].to_numpy(float),
            }).dropna()
            dados = dados.groupby(['cmc','barita'], as_index=False).mean()
            A = np.c_[np.ones(len(dados)), dados['cmc'], dados['barita']]
            a, b, c = np.linalg.lstsq(A, dados['mu'], rcond=None)[0]
            S["coef_mu"] = (float(a), float(b), float(c))
            st.sidebar.success(f"Regressão: μ = {a:.3f} + {b:.3f}·CMC[g] + {c:.5f}·barita[g]")
        except Exception as e:
            st.sidebar.error(f"Falha ao ler a planilha: {e}")

    if S["coef_mu"] is None:
        st.sidebar.warning("Sem planilha: μ indisponível (só ρ e V).")
    else:
        a, b, c = S["coef_mu"]
        st.sidebar.caption(f"μ = {a:.3f} + {b:.3f}·CMC[g] + {c:.5f}·barita[g]")
        st.sidebar.caption(
            f"Faixa válida: C_CMC ∈ [{C_CMC_MIN:.0f}, {C_CMC_MAX:.0f}] g/L, "
            f"C_bar ∈ [{C_BAR_MIN:.0f}, {C_BAR_MAX:.0f}] g/L"
        )

    # ---------------- CONTROLES ----------------
    # ---- Ajuda: vazões para atingir um alvo no regime estacionário ----
    st.sidebar.header("Alvo no tanque (regime estacionário)")
    cb_alvo = st.sidebar.slider("C_barita alvo [g/L]", float(C_BAR_MIN), float(C_BAR_MAX),
                                float(C_BAR_MIN), 1.0)
    cc_alvo = st.sidebar.slider("C_CMC alvo [g/L]", float(C_CMC_MIN), float(C_CMC_MAX),
                                float(C_CMC_MIN), 0.1)
    q_tot_mls = st.sidebar.slider("Vazão total de entrada [mL/s]", 2.0, 20.0, 10.0, 1.0)
    fb, fc = cb_alvo / CF_B, cc_alvo / CF_C
    fa = 1.0 - fb - fc
    viavel = fa >= 0.0
    if viavel:
        st.sidebar.caption(
            f"Qb={q_tot_mls*fb:.2f} | Qc={q_tot_mls*fc:.2f} | Qa={q_tot_mls*fa:.2f} mL/s"
        )
    else:
        st.sidebar.error(
            "Alvo inviável: aumente a concentração das lamas de alimentação "
            f"(faltam {-fa*100:.0f}% de vazão)."
        )

    QMAX_MLS = 50.0

    def aplicar_alvo():
        """Define as vazões (substitui as atuais) para atingir o alvo."""
        if viavel:
            T = st.session_state.tanque
            T["Qb"] = round(q_tot_mls * fb, 4) / 1e6
            T["Qc"] = round(q_tot_mls * fc, 4) / 1e6
            T["Qa"] = round(q_tot_mls * fa, 4) / 1e6

    def somar_vazao(chave, delta_mls):
        """Soma delta (mL/s, pode ser negativo) à vazão que já está entrando."""
        T = st.session_state.tanque
        novo_mls = round(T[chave] * 1e6 + delta_mls, 4)
        T[chave] = min(max(novo_mls, 0.0), QMAX_MLS) / 1e6

    def zerar_vazoes():
        T = st.session_state.tanque
        T["Qb"] = T["Qc"] = T["Qa"] = 0.0

    st.sidebar.button("Aplicar vazões do alvo", on_click=aplicar_alvo,
                      use_container_width=True, disabled=not viavel)

    st.sidebar.header("Vazões de entrada (somam ao que já está)")
    desab = not S["iniciado"]
    passo_mls = st.sidebar.number_input("Quanto somar/subtrair por clique [mL/s]",
                                        min_value=1.0, max_value=20.0, value=1.0, step=1.0,
                                        key="passo_q")
    for chave, nome, kb in (("Qb", "Barita", "qb"), ("Qc", "CMC", "qc"), ("Qa", "Água", "qa")):
        atual = S[chave] * 1e6
        st.sidebar.markdown(f"**{nome}:** {atual:.0f} mL/s" if abs(atual - round(atual)) < 1e-9
                            else f"**{nome}:** {atual:.2f} mL/s")
        cm, cp = st.sidebar.columns(2)
        cm.button(f"− {passo_mls:g}", key=f"menos_{kb}", use_container_width=True,
                  on_click=somar_vazao, args=(chave, -passo_mls))
        cp.button(f"+ {passo_mls:g}", key=f"mais_{kb}", use_container_width=True,
                  on_click=somar_vazao, args=(chave, +passo_mls))
    st.sidebar.button("Zerar todas as entradas", on_click=zerar_vazoes, use_container_width=True)
    st.sidebar.caption(
        f"Entrada total: {(S['Qb']+S['Qc']+S['Qa'])*1e6:.2f} mL/s "
        f"(máx. {QMAX_MLS:.0f} mL/s por corrente)"
    )

    st.sidebar.header("Bomba de saída")
    nivel_auto = st.sidebar.checkbox("Manter nível: Qsaída = Qb + Qc + Qa", value=True)
    Qs_mls = st.sidebar.slider("Q saída nominal [mL/s]", 0.0, 50.0, QS_NOM*1e3, 1.0,
                               disabled=desab or nivel_auto)
    QS = Qs_mls / 1e6

    st.sidebar.header("Simulação")
    velocidade = st.sidebar.slider("Velocidade (× tempo real)", 0.1, 20.0, 5.0, 0.1)
    dt_real    = st.sidebar.slider("Intervalo de atualização [s]", 0.1, 2.0, 0.3, 0.1)

    st.sidebar.header("Controle")
    c1, c2, c3 = st.sidebar.columns(3)
    if c1.button("▶ Iniciar", use_container_width=True, disabled=S["iniciado"]):
        S["iniciado"] = True; S["rodando"] = True; st.rerun()
    if c2.button("⏸ Pausar" if S["rodando"] else "▶ Retomar",
                 use_container_width=True, disabled=not S["iniciado"]):
        S["rodando"] = not S["rodando"]; st.rerun()
    if c3.button("↺ Reiniciar", use_container_width=True):
        st.session_state.tanque = estado_inicial(); st.rerun()

    st.sidebar.caption(
        f"t={S['t']:.2f}s | V={S['V']*1000:.2f}/{V_MAX*1000:.0f}L | "
        f"{'rodando' if S['rodando'] else 'pausado' if S['iniciado'] else 'aguardando'}"
    )
    if S["hist_sat"][-1]:
        st.sidebar.warning("⚠ Limite de sólidos atingido: alimentação saturada.")

    # ---------------- VISCOSIDADE ----------------
    def mu_raw_e_clip(mc_kg, mb_kg, V_m3):
        """Retorna (mu_bruto, mu_saturado). Concentrações em kg/m³ ≡ g/L."""
        if S["coef_mu"] is None or V_m3 <= 1e-12:
            return np.nan, np.nan
        a, b, c = S["coef_mu"]
        C_cmc = mc_kg / V_m3
        C_bar = mb_kg / V_m3
        raw = a + b*C_cmc + c*C_bar
        return float(raw), float(np.clip(raw, MU_MIN, MU_MAX))

    # ---------------- PASSO ----------------
    def passo(dt):
        V, mf, mb, mc = S["V"], S["mf"], S["mb"], S["mc"]
        m = mf + mb + mc
        if m <= 1e-12:
            return
        rho = m / V if V > 1e-12 else RHO_C
        qb, qc, qa = S["Qb"], S["Qc"], S["Qa"]
        q_in = qb + qc + qa
        qs_cmd = q_in if nivel_auto else QS
        q_out = min(qs_cmd, q_in + max(V, 0.0)/dt) if V > 1e-12 else q_in
        q_out = max(q_out, 0.0)

        q_ov = 0.0
        V_pred = V + (q_in - q_out)*dt
        if V_pred > V_MAX:
            q_ov = max((V_pred - V_MAX)/dt, 0.0)
        dV = q_in - q_out - q_ov
        arr = q_out + q_ov

        dmf = qb*RHO_B*(1-W_B) + qc*RHO_C*(1-W_C) + qa*RHO_A - arr*rho*mf/m
        dmb = qb*RHO_B*W_B                        - arr*rho*mb/m
        dmc = qc*RHO_C*W_C                        - arr*rho*mc/m

        V_new  = min(max(V + dV*dt, 0.0), V_MAX)
        mf_new = max(mf + dmf*dt, 0.0)
        mb_new = max(mb + dmb*dt, 0.0)
        mc_new = max(mc + dmc*dt, 0.0)

        # ---------- limite de sólidos ----------
        sat = 0
        m_new = mf_new + mb_new + mc_new
        if m_new > 1e-12:
            if mb_new / m_new > PHI_B_MAX:
                mb_new = PHI_B_MAX * m_new
                sat = 1
            m_new = mf_new + mb_new + mc_new
            if m_new > 1e-12 and mc_new / m_new > PHI_C_MAX:
                mc_new = PHI_C_MAX * m_new
                sat = 1

        S["V"]  = V_new
        S["mf"] = mf_new
        S["mb"] = mb_new
        S["mc"] = mc_new
        S["t"] += dt

        rho_new = (S["mf"]+S["mb"]+S["mc"]) / S["V"] if S["V"] > 1e-12 else RHO_C
        mu_raw, mu_sat = mu_raw_e_clip(S["mc"], S["mb"], S["V"])
        Cb_new  = S["mb"] / S["V"] if S["V"] > 1e-12 else 0.0   # g/L
        Cc_new  = S["mc"] / S["V"] if S["V"] > 1e-12 else 0.0   # g/L

        S["hist_t"].append(S["t"]); S["hist_rho"].append(rho_new)
        S["hist_V"].append(S["V"])
        S["hist_mu"].append(mu_sat); S["hist_mu_raw"].append(mu_raw)
        S["hist_Cb"].append(Cb_new); S["hist_Cc"].append(Cc_new)
        S["hist_Qout"].append(q_out*1000); S["hist_Qov"].append(q_ov*1000)
        S["hist_sat"].append(sat)
        if len(S["hist_t"]) > 60000:
            for k in ("hist_t","hist_rho","hist_V","hist_mu","hist_mu_raw",
                      "hist_Cb","hist_Cc","hist_Qout","hist_Qov","hist_sat"):
                S[k] = S[k][-30000:]

    # ---------------- PAINEL TEMPO REAL ----------------
    @st.fragment(run_every=dt_real)
    def painel():
        if not S["iniciado"]:
            st.info("Suba a planilha (opcional, para μ), ajuste os parâmetros e clique em **▶ Iniciar**.")
            return
        if S["rodando"]:
            dt_sim_total = dt_real * velocidade
            n_sub = max(1, int(dt_sim_total / 0.05))
            dt_sub = dt_sim_total / n_sub
            for _ in range(n_sub):
                passo(dt_sub)

        rho_atual    = S["hist_rho"][-1]
        mu_atual     = S["hist_mu"][-1]
        mu_raw_atual = S["hist_mu_raw"][-1]
        Cb_atual     = S["hist_Cb"][-1]   # já é g/L
        Cc_atual     = S["hist_Cc"][-1]   # já é g/L

        c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
        c1.metric("t [s]", f"{S['t']:.2f}")
        c2.metric("V [L]", f"{S['V']*1000:.3f}", f"{(S['V']-V0)*1000:+.3f}")
        c3.metric("ρ [kg/m³]", f"{rho_atual:.1f}")
        c4.metric("m_barita [g]", f"{S['mb']*1000:.2f}")
        c5.metric("C_CMC [g/L]", f"{Cc_atual:.2f}",
                  f"{Cc_atual - cc_alvo:+.2f}" if C_CMC_MIN <= Cc_atual <= C_CMC_MAX else "⚠ fora")
        c6.metric("C_barita [g/L]", f"{Cb_atual:.2f}",
                  "⚠ fora" if not (C_BAR_MIN <= Cb_atual <= C_BAR_MAX) else None)
        c7.metric("μ [cP]", "—" if np.isnan(mu_atual) else f"{mu_atual:.2f}")

        # vazões atuais (o que já está entrando / saindo)
        q_in_mls  = (S["Qb"] + S["Qc"] + S["Qa"]) * 1e6
        q_out_mls = S["hist_Qout"][-1] * 1e3     # hist_Qout está em L/s
        q_ov_mls  = S["hist_Qov"][-1] * 1e3
        d1, d2, d3, d4, d5, d6 = st.columns(6)
        d1.metric("Q barita [mL/s]", f"{S['Qb']*1e6:.2f}")
        d2.metric("Q CMC [mL/s]",    f"{S['Qc']*1e6:.2f}")
        d3.metric("Q água [mL/s]",   f"{S['Qa']*1e6:.2f}")
        d4.metric("Q entrada total [mL/s]", f"{q_in_mls:.2f}")
        d5.metric("Q saída (bomba) [mL/s]", f"{q_out_mls:.2f}")
        d6.metric("Q vertedouro [mL/s]",    f"{q_ov_mls:.2f}")

        # avisos de faixa
        avisos = []
        if not np.isnan(mu_raw_atual) and (mu_raw_atual < MU_MIN or mu_raw_atual > MU_MAX):
            avisos.append(
                f"⚠ μ bruto = {mu_raw_atual:.2f} cP fora da faixa [{MU_MIN}; {MU_MAX}] — "
                "a regressão está extrapolando."
            )
        if not (C_CMC_MIN <= Cc_atual <= C_CMC_MAX):
            avisos.append(
                f"⚠ C_CMC = {Cc_atual:.2f} g/L fora da faixa [{C_CMC_MIN:.0f}; {C_CMC_MAX:.0f}] g/L — "
                "μ é extrapolação."
            )
        if not (C_BAR_MIN <= Cb_atual <= C_BAR_MAX):
            avisos.append(
                f"⚠ C_barita = {Cb_atual:.2f} g/L fora da faixa [{C_BAR_MIN:.0f}; {C_BAR_MAX:.0f}] g/L — "
                "μ é extrapolação."
            )
        if S["hist_sat"][-1]:
            avisos.append("⚠ Limite de concentração de sólidos atingido — alimentação saturada.")
        for av in avisos:
            st.warning(av)

        t   = np.asarray(S["hist_t"])
        rh  = np.asarray(S["hist_rho"])
        Vv  = np.asarray(S["hist_V"])*1000
        mu  = np.asarray(S["hist_mu"])
        qov = np.asarray(S["hist_Qov"])
        Cb  = np.asarray(S["hist_Cb"])
        Cc  = np.asarray(S["hist_Cc"])
        if len(t) > 3000:
            idx = np.linspace(0, len(t)-1, 3000).astype(int)
            t, rh, Vv, mu, qov, Cb, Cc = t[idx], rh[idx], Vv[idx], mu[idx], qov[idx], Cb[idx], Cc[idx]

        fig, axs = plt.subplots(6, 1, figsize=(10, 13), sharex=True)
        axs[0].plot(t, rh, 'y-', lw=2); axs[0].set_ylabel("ρ [kg/m³]"); axs[0].grid(True)
        axs[0].axhline(RHO_C, color='gray', ls=':', lw=1)
        axs[0].axhline(RHO_B, color='gray', ls='--', lw=1)
        axs[1].plot(t, Vv, 'c-', lw=2); axs[1].axhline(V_MAX*1000, color='k', ls='--', lw=1)
        axs[1].set_ylabel("V [L]"); axs[1].set_ylim(0, V_MAX*1000*1.05); axs[1].grid(True)
        axs[2].plot(t, Cc, 'g-', lw=2); axs[2].set_ylabel("C_CMC [g/L]"); axs[2].grid(True)
        axs[2].axhline(C_CMC_MIN, color='k', ls=':', lw=1, label='faixa regressão')
        axs[2].axhline(C_CMC_MAX, color='k', ls=':', lw=1)
        axs[2].legend(fontsize=8)
        axs[3].plot(t, Cb, 'brown', lw=2); axs[3].set_ylabel("C_barita [g/L]"); axs[3].grid(True)
        axs[3].axhline(C_BAR_MIN, color='k', ls=':', lw=1, label='faixa regressão')
        axs[3].axhline(C_BAR_MAX, color='k', ls=':', lw=1)
        axs[3].legend(fontsize=8)
        axs[4].plot(t, qov, 'm-', lw=2); axs[4].set_ylabel("vertedouro [L/s]"); axs[4].grid(True)
        axs[5].plot(t, mu, 'r-', lw=2); axs[5].set_ylabel("μ [cP]"); axs[5].set_xlabel("t [s]"); axs[5].grid(True)
        axs[5].set_ylim(MU_MIN, MU_EIXO_MAX)
        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

    painel()