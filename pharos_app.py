import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import altair as alt
import os
from fpdf import FPDF

# --- PASSWORD PROTECTION ---
def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        if st.session_state["password"] == "pharos2025":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # --- VISUAL RENDERING BLOCK (FOR LOGIN PAGE) ---
        if os.path.exists("logo.jpg"):
            st.image("logo.jpg", width=250)
        else:
            st.title("🦅 Pharos Capital: BTM Model") 
            st.caption("Please upload 'logo.jpg' for full branding.")
        
        st.markdown("---") 
        st.markdown("### Access Required")
        # --- END VISUAL RENDERING BLOCK ---
        st.text_input("Enter Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Enter Password", type="password", on_change=password_entered, key="password")
        st.error("😕 Password incorrect")
        return False
    else:
        return True

if not check_password():
    st.stop()

# --- 1. SESSION STATE & RESET LOGIC ---
def set_base_case():
    st.session_state.ppa_term = 10
    st.session_state.link_inf = True
    st.session_state.tariff_val = 881.6
    st.session_state.inf_val = 5.0
    st.session_state.disc_val = 25.0
    st.session_state.esc_val = 3.5
    st.session_state.gen_val = 44.9
    st.session_state.cons_val = 560.8
    st.session_state.deg_val = 0.6
    st.session_state.const_q = 3
    st.session_state.capex_val = 120.0
    st.session_state.opex_val = 7.0
    st.session_state.oinf_val = 5.0
    st.session_state.sga_val = 10.0
    st.session_state.sga_const_val = 2.0 
    st.session_state.tax_val = 35.0
    st.session_state.cg_val = 20.0 
    st.session_state.dep_val = 5
    st.session_state.ftt_val = 0.4
    st.session_state.ica_on = False
    st.session_state.ica_rate = 2.0
    st.session_state.debt_on = False 
    st.session_state.dr_val = 70.0
    st.session_state.int_val = 12.1
    st.session_state.tenor_val = 9
    st.session_state.fee_val = 2.0
    st.session_state.grace_val = 3
    st.session_state.exit_method = "EBITDA Multiple"
    st.session_state.exit_yr = 4
    st.session_state.exit_mult_val = 5.0
    st.session_state.exit_asset_val = 10.0
    st.session_state.ke_val = 12.0

if "ppa_term" not in st.session_state:
    set_base_case()

# --- CUSTOM STYLING ---
st.markdown("""
<style>
    .stApp { background-color: #FFFFFF; }
    h1, h2, h3 { color: #0E2F44 !important; font-family: 'Helvetica Neue', sans-serif; }
    [data-testid="stSidebar"] { background-color: #F8F9FB; border-right: 1px solid #E6E9EF; }
    div[data-testid="stMetric"] {
        background-color: #FFFFFF; border: 1px solid #E6E9EF;
        padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center;
    }
    div[data-testid="stMetricLabel"] { color: #6E7781; font-size: 14px; font-weight: 500; }
    div[data-testid="stMetricValue"] { color: #0E2F44; font-size: 26px; font-weight: 700; }
    hr { margin-top: 1em; margin-bottom: 1em; border: 0; border-top: 2px solid #D4AF37; }
    div.stButton > button { background-color: #0E2F44; color: white; border-radius: 5px; border: none; padding: 10px 20px; }
    div.stButton > button:hover { background-color: #1C4E6B; color: white; }
</style>
""", unsafe_allow_html=True)

# --- TRANSLATION DICTIONARY ---
LANG = {
    "English": {
        "header_proj": "Project Name", "header_client": "Client Name", "header_loc": "Location",
        "curr_title": "0. Currency & FX", "curr_display": "Display Currency", "curr_fx": "Current FX Rate (COP/USD)", "curr_inf": "US Inflation (Annual %)",
        "s1_title": "1. Timeline & Revenue", "s1_time": "Project Timeline", "s1_year": "Start Year", "s1_q": "Start Quarter",
        "s1_contract": "Contract Details", "s1_dur": "PPA Duration (Years)", "s1_tariff": "Current Tariff", "s1_inf": "Utility Inflation (Annual %)",
        "s1_disc": "Discount to Client (%)", "s1_link": "Index PPA Price to Inflation?", "s1_lock": "Escalator locked to Inflation", "s1_esc": "PPA Escalator (Annual %)",
        "s1_tech": "Technical & Generation", "s1_mod": "Modules", "s1_pow": "Module Power (W)", "s1_deg": "Degradation (Annual %)",
        "s1_gen_lbl": "Contracted Energy (MWh/yr)", "s1_cons": "Client Total Consumption (MWh/yr)",
        "s2_title": "2. Costs", "s2_const": "Construction Period (Quarters)", "s2_capex": "Total CAPEX", "s2_opex": "Annual OPEX", "s2_oinf": "OPEX Inflation (Annual %)", "s2_sga": "SGA (% of Gross Profit)", "s2_sgaconst": "SGA During Construction (%)",
        "s3_title": "3. Tax", "s3_tax": "Corporate Income Tax (%)", "s3_cap": "Capital Gains Tax (%)", "s3_dep": "Depreciation Term (Years)", "s3_dut": "Duties and Others", "s3_ftt": "4x1000 FTT Rate (%)", "s3_ica": "Include ICA Tax (2%)?", "s3_ica_rate": "ICA Rate (%)",
        "s4_title": "4. Financing", "s4_enable": "Include Debt?", "s4_ratio": "Debt Ratio (%)", "s4_int": "Interest Rate (Annual %)", "s4_tenor": "Loan Tenor (Years)", "s4_fee": "Structuring Fee (%)", "s4_grace": "Grace Period (Quarters)",
        "s5_title": "5. Scenario", "s5_method": "Exit Method", "s5_year": "Exit Year", "s5_val": "Asset Sale Value", "s5_mult": "Valuation Multiple (x EBITDA)", "s5_ke": "Investor Discount Rate (Ke %)",
        "kpi_eq": "Equity Investment", "kpi_tar": "Start Contract Tariff", "kpi_irr": "Equity IRR", "kpi_npv": "Equity NPV", "kpi_moic": "MOIC", "kpi_cov": "Project Coverage",
        "card_proj": "🏗️ Project (Unlevered)", "card_eq": "🦅 Equity (Levered)", "card_lev": "⚖️ Leverage Boost", "lbl_lev": "Leverage", "lbl_nodebt": "Debt Disabled",
        "rev_proof": "🔎 Revenue Calculation Detail", "chart_cf": "💰 Cash Flow Comparison", "tab_full": "🔎 Full Cash Flow Statement", "tab_pl": "📑 Income Statement (P&L)",
        "sim_title": "⚡ 5. Simulation Matrix (Equity IRR)",
        "sim_run": "▶️ Run Simulation",
        "sim_min": "Min Asset Value",
        "sim_max": "Max Asset Value",
        "sim_step": "Step Size",
        "sim_chart": "Equity IRR Sensitivity",
        "col_gen": "Generation",
        "col_rev": "Revenue",
        "col_price": "Avg Tariff",
        "col_ftt": "FTT Cost"
    },
    "Español": {
        "header_proj": "Nombre del Proyecto", "header_client": "Cliente", "header_loc": "Ubicación",
        "curr_title": "0. Moneda y TRM", "curr_display": "Moneda Visual", "curr_fx": "TRM Actual (COP/USD)", "curr_inf": "Inflación USA (Anual %)",
        "s1_title": "1. Plazos e Ingresos", "s1_time": "Cronograma", "s1_year": "Año Inicio", "s1_q": "Trimestre Inicio",
        "s1_contract": "Detalles del Contrato", "s1_dur": "Duración PPA (Años)", "s1_tariff": "Tarifa Actual", "s1_inf": "Inflación Servicios (Anual %)",
        "s1_disc": "Descuento al Cliente (%)", "s1_link": "¿Indexar PPA a Inflación?", "s1_lock": "Escalador atado a Inflación", "s1_esc": "Escalador PPA (Anual %)",
        "s1_tech": "Técnico y Generación", "s1_mod": "Módulos", "s1_pow": "Potencia Módulo (W)", "s1_deg": "Degradación (Anual %)",
        "s1_gen_lbl": "Energía Contratada (MWh/año)", "s1_cons": "Consumo Total Cliente (MWh/año)",
        "s2_title": "2. Costos", "s2_const": "Periodo Construcción (Trimestres)", "s2_capex": "CAPEX Total", "s2_opex": "OPEX Anual", "s2_oinf": "Inflación OPEX (Anual %)", "s2_sga": "SGA (% de Utilidad Bruta)", "s2_sgaconst": "SGA Durante Construcción (%)",
        "s3_title": "3. Impuestos", "s3_tax": "Impuesto de Renta (%)", "s3_cap": "Ganancia Ocasional (%)", "s3_dep": "Plazo Depreciación (Años)", "s3_dut": "Gravámenes y Otros", "s3_ftt": "Tasa 4x1000 (%)", "s3_ica": "¿Incluir Impuesto ICA (2%)?", "s3_ica_rate": "Tasa ICA (%)",
        "s4_title": "4. Financiación", "s4_enable": "¿Incluir Deuda?", "s4_ratio": "Nivel de Deuda (%)", "s4_int": "Tasa Interés (Anual %)", "s4_tenor": "Plazo Crédito (Años)", "s4_fee": "Comisión Estructuración (%)", "s4_grace": "Periodo de Gracia (Trimestres)",
        "s5_title": "5. Escenario",
        "s5_method": "Método de Salida",
        "s5_year": "Año de Salida",
        "s5_val": "Valor Venta Activo",
        "s5_mult": "Múltiplo Valoración (x EBITDA)",
        "s5_ke": "Tasa Descuento Inversionista (Ke %)",
        "kpi_eq": "Inversión Equity",
        "kpi_tar": "Tarifa PPA Año 1",
        "kpi_irr": "TIR Inversionista",
        "kpi_npv": "VPN Inversionista",
        "kpi_moic": "Multiplo (MOIC)",
        "kpi_cov": "Cobertura Proyecto",
        "card_proj": "🏗️ Proyecto (Sin Deuda)",
        "card_eq": "🦅 Equity (Con Deuda)",
        "card_lev": "⚖️ Efecto Apalancamiento",
        "lbl_lev": "Nivel Deuda",
        "lbl_nodebt": "Sin Deuda",
        "rev_proof": "🔎 Detalle Cálculo de Ingresos",
        "chart_cf": "💰 Comparación Flujo de Caja",
        "tab_full": "🔎 Flujo de Caja Detallado",
        "tab_pl": "📑 Estado de Resultados (P&L)",
        "sim_title": "⚡ 5. Matriz de Simulación (TIR Equity)",
        "sim_run": "▶️ Ejecutar Simulación",
        "sim_min": "Valor Min",
        "sim_max": "Valor Max",
        "sim_step": "Paso",
        "sim_chart": "Sensibilidad TIR Equity",
        "col_gen": "Generación",
        "col_rev": "Ingresos",
        "col_price": "Tarifa Prom",
        "col_ftt": "Costo 4x1000"
    }
}

# --- LANGUAGE SELECTOR ---
sel_lang = st.sidebar.selectbox("Language / Idioma", ["English", "Español"])
T = LANG[sel_lang]

# --- RESET BUTTON ---
if st.sidebar.button("↺ Reset to Base Case"):
    set_base_case()
    st.rerun()

# --- HEADER ---
col_logo, col_title = st.columns([1, 4])
with col_logo:
    if os.path.exists("logo.jpg"):
        st.image("logo.jpg", width=150)
    else:
        st.write("🦅") 
with col_title:
    st.title("Pharos Capital: BTM Model")

# --- PROJECT DETAILS ---
c_proj1, c_proj2, c_proj3 = st.columns(3)
with c_proj1:
    project_name = st.text_input(T["header_proj"], value="Hampton Inn Bogota - Aeropuerto")
with c_proj2:
    client_name = st.text_input(T["header_client"], value="Hampton Inn")
with c_proj3:
    project_loc = st.text_input(T["header_loc"], value="Bogota, Colombia")

st.markdown("---")

# ==========================================
# 0. SETTINGS
# ==========================================
st.sidebar.header(T["curr_title"])
currency_mode = st.sidebar.radio(T["curr_display"], ["COP (Millions)", "USD (Thousands)"], horizontal=True)

# Define Symbol and Initial Conversion Factor (CRITICAL FOR PDF/DISPLAY)
symbol = "$" if "USD" in currency_mode else ""
inv_conv_factor_base = 1000 / st.session_state.fx_rate_current if "USD" in currency_mode else 1

with st.sidebar.expander("FX & Macro", expanded=False):
    fx_rate_current = st.number_input(T["curr_fx"], value=4100.0, step=50.0, format="%.1f")
    us_inflation_annual = st.number_input(T["curr_inf"], value=2.5, step=0.1, format="%.1f") / 100

# ==========================================
# 1. INPUTS
# ==========================================
st.sidebar.header(T["s1_title"])
with st.sidebar.expander(T["s1_time"], expanded=False): # COLLAPSED
    c_start1, c_start2 = st.columns(2)
    with c_start1:
        start_year = st.number_input(T["s1_year"], value=2026, step=1)
    with c_start2:
        start_q_str = st.selectbox(T["s1_q"], ["Q1", "Q2", "Q3", "Q4"], index=0)
    start_q_num = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}[start_q_str]

with st.sidebar.expander(T["s1_contract"], expanded=False): # COLLAPSED
    ppa_term_years = st.slider(T["s1_dur"], 5, 20, key="ppa_term")
    current_tariff = st.number_input(f"{T['s1_tariff']} ($/kWh)", key="tariff_val", step=10.0, format="%.1f")
    utility_inflation_annual = st.number_input(T["s1_inf"], key="inf_val", step=0.5, format="%.1f") / 100
    discount_rate = st.number_input(T["s1_disc"], key="disc_val", step=1.0, format="%.1f") / 100
    
    link_to_inflation = st.checkbox(T["s1_link"], key="link_inf")
    if link_to_inflation:
        pcp_escalator_annual = utility_inflation_annual
        st.info(f"🔒 {T['s1_lock']} ({utility_inflation_annual*100:.1f}%)")
    else:
        pcp_escalator_annual = st.number_input(T["s1_esc"], key="esc_val", step=0.5, format="%.1f") / 100
    
    st.markdown("---")
    st.caption(T["s1_tech"])
    initial_gen_mwh_annual = st.number_input(T["s1_gen_lbl"], key="gen_val", step=0.1, format="%.1f")
    client_consumption = st.number_input(T["s1_cons"], key="cons_val", step=10.0, format="%.1f")
    if client_consumption > 0:
        coverage_pct = (initial_gen_mwh_annual / client_consumption) * 100
    else:
        coverage_pct = 0
    st.metric(T["kpi_cov"], f"{coverage_pct:.1f}%")
    degradation_annual = st.number_input(T["s1_deg"], key="deg_val", step=0.1, format="%.1f") / 100

st.sidebar.header(T["s2_title"])
with st.sidebar.expander("CAPEX & OPEX", expanded=False): # COLLAPSED
    construction_quarters = st.slider(T["s2_const"], 0, 8, key="const_q")
    capex_million_cop = st.number_input(f"{T['s2_capex']} (M COP)", key="capex_val", step=10.0, format="%.1f")
    opex_million_cop_annual = st.number_input(f"{T['s2_opex']} (M COP/yr)", key="opex_val", step=0.5, format="%.1f")
    opex_inflation_annual = st.number_input(T["s2_oinf"], key="oinf_val", step=0.5, format="%.1f") / 100
    sga_percent = st.number_input(T["s2_sga"], key="sga_val", step=1.0, format="%.1f") / 100
    
    # SGA During Construction Cost
    sga_const_pct = st.number_input(T["s2_sgaconst"], key="sga_const_val", step=0.1, format="%.1f", help="SGA as % of CAPEX, capitalized during construction") / 100
    
    sga_const_cost_cop = capex_million_cop * sga_const_pct
    sga_const_cost_disp = sga_const_cost_cop * inv_conv_factor_base
    st.write(f"**Cost:** {symbol}{sga_const_cost_disp:,.1f} {currency_mode.split()[0]}")

st.sidebar.header(T["s3_title"])
with st.sidebar.expander("Fiscal Regime", expanded=False): # COLLAPSED
    tax_rate = st.number_input(T["s3_tax"], key="tax_val", step=1.0, format="%.1f") / 100
    cap_gains_rate = st.number_input(T["s3_cap"], key="cg_val", step=1.0, format="%.1f") / 100
    depreciation_years = st.slider(T["s3_dep"], 3, 25, key="dep_val")
    
    # NEW DUTIES GROUP
    st.markdown("---")
    st.caption(T["s3_dut"])
    ftt_rate = st.number_input(T["s3_ftt"], key="ftt_val", value=0.4, step=0.1, format="%.1f", help="Applied to cash disbursements: CAPEX, OPEX, SGA, Debt Service, Tax") / 1000
    
    # NEW ICA TAX
    enable_ica = st.checkbox(T["s3_ica"], key="ica_on")
    if enable_ica:
        ica_rate = st.number_input(T["s3_ica_rate"], key="ica_rate", value=2.0, step=0.1, format="%.1f", help="Applied to Total Revenue") / 100
    else:
        ica_rate = 0.0

st.sidebar.header(T["s4_title"])
with st.sidebar.expander("Debt Structure", expanded=False): # COLLAPSED
    enable_debt = st.checkbox(T["s4_enable"], key="debt_on")
    if enable_debt:
        debt_ratio = st.slider(T["s4_ratio"], 0, 100, key="dr_val") / 100
        interest_rate_annual = st.number_input(T["s4_int"], key="int_val", step=0.1, format="%.1f") / 100
        loan_tenor_years = st.number_input(T["s4_tenor"], key="tenor_val", step=1)
        structuring_fee_pct = st.number_input(T["s4_fee"], key="fee_val", step=0.1, format="%.1f") / 100
        grace_period_quarters = st.number_input(T["s4_grace"], key="grace_val", step=1)
    else:
        debt_ratio = 0.0
        interest_rate_annual = 0.0
        loan_tenor_years = 0
        structuring_fee_pct = 0.0
        grace_period_quarters = 0

st.sidebar.header(T["s5_title"])
with st.sidebar.expander("Valuation", expanded=False): # COLLAPSED
    dash_exit_strategy = st.radio(T["s5_method"], ["Fixed Asset Value", "EBITDA Multiple"], key="exit_method")
    dash_exit_year = st.slider(T["s5_year"], 2, ppa_term_years, key="exit_yr")
    if dash_exit_strategy == "Fixed Asset Value":
        dash_exit_val_cop = st.number_input(f"{T['s5_val']} (M COP)", key="exit_asset_val", step=5.0, format="%.1f")
        dash_exit_mult = 0
    else:
        dash_exit_mult = st.number_input(T["s5_mult"], key="exit_mult_val", step=0.5, format="%.1f")
        dash_exit_val_cop = 0
    st.markdown("---")
    investor_disc_rate = st.number_input(T["s5_ke"], key="ke_val", step=0.5, format="%.1f") / 100

# --- ENGINE ---
full_quarters = construction_quarters + (ppa_term_years * 4)
quarters_range = list(range(1, full_quarters + 1))

# Initial Capitalization
sga_const_cost = capex_million_cop * sga_const_pct
if enable_debt:
    structuring_fee = (capex_million_cop * debt_ratio) * structuring_fee_pct
    total_debt_principal = capex_million_cop * debt_ratio
    interest_rate_quarterly = interest_rate_annual / 4
    loan_tenor_quarters = loan_tenor_years * 4
    quarterly_debt_pmt = -npf.pmt(interest_rate_quarterly, loan_tenor_quarters - grace_period_quarters, total_debt_principal) if (loan_tenor_quarters - grace_period_quarters) > 0 else 0
else:
    structuring_fee = 0
    total_debt_principal = 0
    interest_rate_quarterly = 0
    quarterly_debt_pmt = 0

total_capex_cost = capex_million_cop + structuring_fee + sga_const_cost
equity_investment_levered_cop = total_capex_cost - total_debt_principal
equity_investment_unlevered_cop = total_capex_cost 

# Output Lists
q_list, gy_list, cal_list = [], [], []
gen_list, rev_list, ebitda_list = [], [], []
opex_list, sga_list, gross_list = [], [], []
dep_list, int_list, tax_list, ftt_list, ica_list = [], [], [], [], [] 
ufcf_list, lfcf_list, debt_bal_list, book_val_list, fx_rate_list = [], [], [], [], []

debt_balance = total_debt_principal
accumulated_dep = 0

for i, q in enumerate(quarters_range):
    abs_q = (start_q_num - 1) + i 
    cal_year = start_year + (abs_q // 4)
    cal_q = (abs_q % 4) + 1
    
    t_years = i / 4
    fx_rate_q = fx_rate_current * ((1 + utility_inflation_annual) / (1 + us_inflation_annual)) ** t_years
    
    if q <= construction_quarters:
        phase, op_year, q_op_index = "Construction", 0, 0
    else:
        phase, op_year, q_op_index = "Operation", q - construction_quarters, q - construction_quarters
        op_year = (q_op_index - 1) // 4 + 1
    
    global_year = (q - 1) // 4 + 1 
    
    if phase == "Operation":
        inf_factor = (1 + utility_inflation_annual) ** ((q_op_index - 1) / 4)
        esc_factor = (1 + pcp_escalator_annual) ** ((q_op_index - 1) / 4)
        deg_factor = (1 - degradation_annual) ** ((q_op_index - 1) / 4)
        opex_fac = (1 + opex_inflation_annual) ** ((q_op_index - 1) / 4)

        u_price = current_tariff * inf_factor
        p_price = current_tariff * (1 - discount_rate) * esc_factor
        gen_quarterly = (initial_gen_mwh_annual / 4) * deg_factor
        rev = (gen_quarterly * p_price) / 1000
        opex = (opex_million_cop_annual / 4) * opex_fac
        gross = rev - opex
        sga = gross * sga_percent
        ica_cost = rev * ica_rate if enable_ica else 0.0
        
        ebitda = gross - sga - ica_cost 
        dep = (capex_million_cop / depreciation_years) / 4 if op_year <= depreciation_years else 0
    else:
        rev, opex, gross, sga, ebitda, dep, gen_quarterly, ica_cost = 0, 0, 0, 0, 0, 0, 0, 0

    if phase == "Construction" and construction_quarters > 0:
        capex_unlevered = capex_million_cop / construction_quarters
        capex_levered = equity_investment_levered_cop / construction_quarters
        sga_const_outflow = sga_const_cost / construction_quarters
        capex_levered += sga_const_outflow
    else:
        capex_unlevered, capex_levered, sga_const_outflow = 0, 0, 0

    if debt_balance > 0:
        interest = debt_balance * interest_rate_quarterly
        if q > grace_period_quarters:
            principal = quarterly_debt_pmt - interest
            if principal > debt_balance: principal = debt_balance
        else:
            principal = 0
        debt_balance -= principal
    else:
        interest, principal = 0, 0

    tax_unlevered = (ebitda - dep) * tax_rate if (ebitda - dep) > 0 else 0
    taxable_inc = ebitda - interest - dep
    tax_levered = taxable_inc * tax_rate if taxable_inc > 0 else 0

    total_disbursements = capex_levered + opex + sga + principal + interest + tax_levered
    ftt_cost = total_disbursements * ftt_rate
    
    accumulated_dep += dep
    book_val = max(0, capex_million_cop - accumulated_dep)

    q_list.append(q)
    gy_list.append(global_year)
    cal_list.append(cal_year)
    gen_list.append(gen_quarterly)
    rev_list.append(rev)
    opex_list.append(opex)
    gross_list.append(gross)
    sga_list.append(sga)
    ica_list.append(ica_cost)
    ebitda_list.append(ebitda)
    dep_list.append(dep)
    int_list.append(interest)
    tax_list.append(tax_levered) 
    ftt_list.append(ftt_cost) 
    
    ufcf_list.append(ebitda - tax_unlevered - capex_unlevered)
    lfcf_list.append(ebitda - tax_levered - interest - principal - capex_levered - ftt_cost)

    debt_bal_list.append(debt_balance)
    book_val_list.append(book_val)
    fx_rate_list.append(fx_rate_q)

df_full = pd.DataFrame({
    "Quarter": q_list, "Global_Year": gy_list, "Calendar_Year": cal_list,
    "FX_Rate": fx_rate_list, "Generation_MWh": gen_list, 
    "Revenue_M_COP": rev_list, "OPEX_M_COP": opex_list, "Gross_M_COP": gross_list,
    "SGA_M_COP": sga_list, "ICA_M_COP": ica_list, "EBITDA_M_COP": ebitda_list, "Depreciation_M_COP": dep_list,
    "Interest_M_COP": int_list, "Tax_M_COP": tax_list, "FTT_M_COP": ftt_list,
    "UFCF_M_COP": ufcf_list, "LFCF_M_COP": lfcf_list, 
    "Debt_Balance_M_COP": debt_bal_list, "Book_Value_M_COP": book_val_list
})

# CONVERSION
conversion_factor = 1000 / df_full["FX_Rate"] if "USD" in currency_mode else 1
for col in ["Revenue", "OPEX", "Gross", "SGA", "ICA", "EBITDA", "Depreciation", "Interest", "Tax", "FTT", "UFCF", "LFCF"]:
    df_full[f"{col}_Disp"] = df_full[f"{col}_M_COP"] * conversion_factor

# DASHBOARD LOGIC
if dash_exit_strategy == "Fixed Asset Value":
    final_exit_val_cop = dash_exit_val_cop
else:
    exit_q_idx = construction_quarters + (dash_exit_year * 4) - 1
    start_idx = max(0, exit_q_idx - 3)
    annual_ebitda = df_full.iloc[start_idx : exit_q_idx+1]["EBITDA_M_COP"].sum()
    final_exit_val_cop = annual_ebitda * dash_exit_mult

dash_exit_q = construction_quarters + (dash_exit_year * 4)
df_dash = df_full.iloc[:dash_exit_q].copy()

last_idx = len(df_dash) - 1
book_v_final = df_dash.iloc[last_idx]["Book_Value_M_COP"]
debt_b_final = df_dash.iloc[last_idx]["Debt_Balance_M_COP"]
gain = final_exit_val_cop - book_v_final
cg_tax = gain * cap_gains_rate if gain > 0 else 0

final_fx = df_dash.iloc[last_idx]["FX_Rate"]
conv_factor_final = 1000 / final_fx if "USD" in currency_mode else 1

exit_inflow_unlevered_disp = (final_exit_val_cop - cg_tax) * conv_factor_final
exit_inflow_levered_disp = (final_exit_val_cop - debt_b_final - cg_tax) * conv_factor_final

df_dash.at[last_idx, "UFCF_Disp"] += exit_inflow_unlevered_disp
df_dash.at[last_idx, "LFCF_Disp"] += exit_inflow_levered_disp

# Aggregate by CALENDAR YEAR for Dashboard
agg_cols = ["Generation_MWh", "Revenue_Disp", "OPEX_Disp", "Gross_Disp", "SGA_Disp", "ICA_Disp",
            "EBITDA_Disp", "Depreciation_Disp", "Interest_Disp", "Tax_Disp", "FTT_Disp",
            "UFCF_Disp", "LFCF_Disp"]
df_annual_dash = df_dash.groupby("Calendar_Year")[agg_cols].sum().reset_index()

# FULL DATA FOR TABLES
df_annual_full = df_full.groupby("Calendar_Year")[agg_cols].sum().reset_index()

# FIXED PRICE CALCULATION
df_annual_dash["Implied_Price_Unit"] = 0.0
mask = df_annual_dash["Generation_MWh"] > 0
if "USD" in currency_mode:
    df_annual_dash.loc[mask, "Implied_Price_Unit"] = (df_annual_dash.loc[mask, "Revenue_Disp"] / df_annual_dash.loc[mask, "Generation_MWh"]) 
else:
    df_annual_dash.loc[mask, "Implied_Price_Unit"] = (df_annual_dash.loc[mask, "Revenue_Disp"] / df_annual_dash.loc[mask, "Generation_MWh"]) * 1000

def get_irr(stream):
    try:
        q_irr = npf.irr(stream)
        return ((1 + q_irr) ** 4 - 1) * 100
    except: return 0

inv_conv = 1000 / fx_rate_current if "USD" in currency_mode else 1
equity_inv_disp = equity_investment_levered_cop * inv_conv
irr_unlevered = get_irr(df_dash["UFCF_Disp"])
irr_levered = get_irr(df_dash["LFCF_Disp"])
moic_levered = df_dash["LFCF_Disp"].sum() / equity_inv_disp if equity_inv_disp > 0 else 0
npv_equity = npf.npv(investor_disc_rate / 4, [0] + df_dash["LFCF_Disp"].tolist())

symbol = "$" if "USD" in currency_mode else ""

# --- OUTPUT ---
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.subheader(f"📊 {currency_mode}")
with col_head2:
    class PDF(FPDF):
        def header(self):
            if os.path.exists("logo.jpg"):
                self.image("logo.jpg", 10, 8, 33)
            self.set_font('Arial', 'B', 15)
            self.cell(80) 
            self.cell(30, 10, 'Pharos Capital: BTM Model', 0, 0, 'C')
            self.ln(20)
        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def create_pdf(df_agg, proj_name, cli_name, loc, curr_sym):
        pdf = PDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        pdf.set_fill_color(14, 47, 68) 
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 10, "1. Project Overview", 0, 1, 'L', 1)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
        pdf.cell(90, 7, f"Project: {proj_name}", 0, 0)
        pdf.cell(90, 7, f"Client: {cli_name}", 0, 1)
        pdf.cell(90, 7, f"Location: {loc}", 0, 1)
        pdf.ln(5)
        
        pdf.set_fill_color(14, 47, 68)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 10, "2. Key Assumptions", 0, 1, 'L', 1)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
        # Row 1
        pdf.cell(60, 7, f"Start: {start_year} {start_q_str}", 0, 0)
        pdf.cell(60, 7, f"Term: {ppa_term_years} Years", 0, 0)
        pdf.cell(60, 7, f"Tariff: ${current_tariff:,.1f}/kWh", 0, 1)
        # Row 2
        pdf.cell(60, 7, f"Energy: {initial_gen_mwh_annual:,.1f} MWh", 0, 0)
        pdf.cell(60, 7, f"CAPEX: {curr_sym}{capex_million_cop*inv_conv:,.1f} {currency_mode.split()[0]}", 0, 0)
        pdf.cell(60, 7, f"Leverage: {debt_ratio*100:.0f}%", 0, 1)
        pdf.ln(5)

        pdf.set_fill_color(14, 47, 68)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 10, "3. Executive Summary", 0, 1, 'L', 1)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(45, 10, f"Eq Inv: {curr_sym}{equity_inv_disp:,.1f}", 1, 0, 'C')
        pdf.cell(45, 10, f"IRR: {irr_levered:.1f}%", 1, 0, 'C')
        pdf.cell(45, 10, f"NPV: {curr_sym}{npv_equity:,.1f}", 1, 0, 'C')
        pdf.cell(45, 10, f"MOIC: {moic_levered:,.1f}x", 1, 1, 'C')
        pdf.set_font("Arial", size=12)
        pdf.ln(5)
        
        # 4. Financial Summary Table
        pdf.set_fill_color(14, 47, 68)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 10, "4. Financial Summary", 0, 1, 'L', 1)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
        pdf.set_font("Arial", size=9)
        headers = ["Year", "Rev", "EBITDA", "NetInc", "FCF"]
        w = [25, 40, 40, 40, 40]
        pdf.set_fill_color(200, 200, 200)
        for i, h in enumerate(headers):
            pdf.cell(w[i], 7, h, 1, 0, 'C', 1)
        pdf.ln()
        
        df_p = df_agg.copy()
        df_p["EBIT"] = df_p["EBITDA_Disp"] - df_p["Depreciation_Disp"]
        df_p["NetInc"] = df_p["EBIT"] - df_p["Interest_Disp"] - df_p["Tax_Disp"]
        
        for index, row in df_p.iterrows():
            pdf.cell(w[0], 7, str(int(row["Calendar_Year"])), 1, 0, 'C')
            pdf.cell(w[1], 7, f"{row['Revenue_Disp']:,.1f}", 1, 0, 'R')
            pdf.cell(w[2], 7, f"{row['EBITDA_Disp']:,.1f}", 1, 0, 'R')
            pdf.cell(w[3], 7, f"{row['NetInc']:,.1f}", 1, 0, 'R')
            pdf.cell(w[4], 7, f"{row['LFCF_Disp']:,.1f}", 1, 0, 'R')
            pdf.ln()
        return pdf.output(dest='S').encode('latin-1')

    pdf_bytes = create_pdf(df_annual_dash, project_name, client_name, project_loc, symbol)
    st.download_button(label="📄 Download PDF Report", data=pdf_bytes, file_name="pharos_memo.pdf", mime="application/pdf")

k1, k2, k3, k4 = st.columns(4)
k1.metric(T["kpi_eq"], f"{symbol}{equity_inv_disp:,.1f}")
start_p = current_tariff * (1 - discount_rate)
if "USD" in currency_mode: start_p /= fx_rate_current
k2.metric(T["kpi_tar"], f"${start_p:,.2f} /kWh")
k3.metric(T["kpi_irr"], f"{irr_levered:.1f}%")
k4.metric(T["kpi_npv"], f"{symbol}{npv_equity:,.1f}")

st.divider()

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"### {T['card_proj']}")
    st.metric("TIR", f"{irr_unlevered:.1f}%")
with c2:
    st.markdown(f"### {T['card_eq']}")
    st.metric(T["kpi_moic"], f"{moic_levered:.1f}x")
    st.caption(f"{T['lbl_lev']}: {debt_ratio*100:.0f}%" if enable_debt else T["lbl_nodebt"])
with c3:
    st.markdown(f"### ⚖️ Leverage Boost")
    st.metric("Delta", f"{irr_levered - irr_unlevered:+.1f}%", delta_color="normal")

st.divider()

with st.expander(T["rev_proof"], expanded=True):
    st.write("Revenue Proof")
    proof_df = df_annual_dash[["Calendar_Year", "Generation_MWh", "Revenue_Disp"]].copy()
    proof_df.columns = ["Year", T["col_gen"], T["col_rev"]]
    st.dataframe(proof_df.style.format({
        "Year": "{:.0f}", T["col_gen"]: "{:,.1f}", T["col_rev"]: "{:,.1f}"
    }))

st.markdown(f"##### {T['chart_cf']}")
df_melt = df_annual_dash.melt(id_vars=["Calendar_Year"], value_vars=["UFCF_Disp", "LFCF_Disp"], var_name="Type", value_name="CashFlow")

base = alt.Chart(df_melt).encode(
    x=alt.X('Type:N', title=None, axis=None),
    y=alt.Y('CashFlow:Q', title=f"Cash Flow ({currency_mode})")
)
bars = base.mark_bar().encode(
    color=alt.Color('Type', scale=alt.Scale(domain=['UFCF_Disp', 'LFCF_Disp'], range=['#808080', '#009355'])),
    tooltip=['Calendar_Year', 'Type', 'CashFlow']
)
text = base.mark_text(dy=-10).encode(text=alt.Text('CashFlow:Q', format='.1f'), color=alt.value('black'))
chart = alt.layer(bars, text).properties(width=55).facet(
    column=alt.Column('Calendar_Year:O', title="Year", header=alt.Header(labelAngle=0, labelAlign='center'))
)
st.altair_chart(chart)

# --- TABLES (LAYOUT TOGGLE) ---
st.markdown("---")
table_layout = st.radio("Table Layout", ["Horizontal (Years as Columns)", "Vertical (Years as Rows)"], horizontal=True)

st.markdown(f"### {T['tab_pl']}")
pnl_data = df_annual_full.copy()
pnl_data["EBIT_Disp"] = pnl_data["EBITDA_Disp"] - pnl_data["Depreciation_Disp"]
pnl_data["EBT_Disp"] = pnl_data["EBIT_Disp"] - pnl_data["Interest_Disp"]
pnl_data["Net_Income_Disp"] = pnl_data["EBT_Disp"] - pnl_data["Tax_Disp"]

pnl_view = pnl_data[["Calendar_Year", "Revenue_Disp", "OPEX_Disp", "Gross_Disp", "SGA_Disp", 
                     "EBITDA_Disp", "Depreciation_Disp", "EBIT_Disp", "Interest_Disp", 
                     "EBT_Disp", "Tax_Disp", "Net_Income_Disp"]].set_index("Calendar_Year")

if "Horizontal" in table_layout:
    pnl_view = pnl_view.T
    pnl_view.index = ["Revenue", "(-) OPEX", "(=) Gross Profit", "(-) SGA", "(=) EBITDA", 
                      "(-) Depreciation", "(=) EBIT", "(-) Interest", "(=) EBT", "(-) Taxes", "(=) Net Income"]
    st.dataframe(pnl_view.style.format("{:,.1f}"))
else:
    st.dataframe(pnl_view.style.format("{:,.1f}"))

st.markdown(f"### {T['tab_full']}")
cf_cols = ["Generation_MWh", "Revenue_Disp", "OPEX_Disp", "EBITDA_Disp", "UFCF_Disp", "LFCF_Disp"]
cf_view = df_annual_full.set_index("Calendar_Year")[cf_cols]

if "Horizontal" in table_layout:
    cf_view = cf_view.T
    cf_view.index = ["Generation (MWh)", "Revenue", "(-) OPEX", "(=) EBITDA", "Unlevered FCF", "Levered FCF"]
    st.dataframe(cf_view.style.format("{:,.1f}"))
else:
    st.dataframe(cf_view.style.format("{:,.1f}"))

st.markdown("---")
st.header(T["sim_title"])
with st.expander("Config", expanded=True):
    c_sim1, c_sim2 = st.columns(2)
    with c_sim1:
        sim_years = st.slider(T["s5_year"], 2, ppa_term_years, (5, 10))
    with c_sim2:
        base_val = int(final_exit_val_cop) if final_exit_val_cop > 0 else 100
        min_v = st.number_input(f"{T['sim_min']} (COP)", value=max(10, base_val - 50), step=10)
        max_v = st.number_input(f"{T['sim_max']} (COP)", value=base_val + 50, step=10)
        step_v = st.number_input("Step Size", value=10, step=1)

def calculate_sim_irr(y_exit, v_exit_cop):
    exit_q = construction_quarters + (y_exit * 4)
    if exit_q > len(df_full): return 0
    df_slice = df_full.iloc[:exit_q].copy()
    last_r = df_slice.iloc[-1]
    gain = v_exit_cop - last_r["Book_Value_M_COP"]
    tax = gain * cap_gains_rate if gain > 0 else 0
    net_exit_cop = v_exit_cop - last_r["Debt_Balance_M_COP"] - tax
    df_slice.at[len(df_slice)-1, "LFCF_M_COP"] += net_exit_cop
    return get_irr(df_slice["LFCF_M_COP"])

if st.button(T["sim_run"]):
    years_to_sim = list(range(sim_years[0], sim_years[1] + 1))
    vals_to_sim = list(range(int(min_v), int(max_v) + int(step_v), int(step_v)))
    sim_data = []
    for v in vals_to_sim:
        for y in years_to_sim:
            sim_data.append({T["s5_year"]: y, "Sale Value": v, "IRR": round(calculate_sim_irr(y, v), 1)})
    
    heatmap = alt.Chart(pd.DataFrame(sim_data)).mark_rect().encode(
        x=alt.X(f'{T["s5_val"]}:O'),
        y=alt.Y(f'{T["s5_year"]}:O'),
        color=alt.Color('IRR:Q', scale=alt.Scale(scheme='redyellowgreen'), title='IRR %'),
        tooltip=[T["s5_year"], T["s5_val"], 'IRR']
    ).properties(title=T["sim_chart"])
    
    text = heatmap.mark_text(baseline='middle').encode(text='IRR:Q', color=alt.value('black'))
    st.altair_chart(heatmap + text, use_container_width=True)
