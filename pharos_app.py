import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import altair as alt
import os
import json
import matplotlib.pyplot as plt
import tempfile
import io

from fpdf import FPDF

# ------------------------------------------------------
# CONFIG & CONSTANTS
# ------------------------------------------------------
st.set_page_config(layout="wide", page_title="Pharos Capital: BTM Model", page_icon="🦅")

PROJECTS_FILE = "pharos_projects.json"

PROJECTS_FILE = "pharos_projects.json"
ATTACHMENTS_DIR = "pharos_attachments"

# Keys we want to persist per project
PROJECT_INPUT_KEYS = [
    "project_name", "client_name", "project_loc",
    "start_year", "start_q_str",
    "ppa_term", "link_inf", "tariff_val", "inf_val", "disc_val", "esc_val",
    "gen_val", "cons_val", "deg_val",
    "const_q", "capex_val", "opex_val", "oinf_val", "sga_val", "sga_const_val",
    "tax_val", "cg_val", "dep_val", "ftt_val", "ica_on", "ica_rate",
    "debt_on", "dr_val", "int_val", "tenor_val", "fee_val", "grace_val",
    "exit_method", "exit_yr", "exit_mult_val", "exit_asset_val", "ke_val",
    "fx_rate_current",
    "capex_benefit_on", "capex_benefit_years", "capex_benefit_capex_pct"
]


# ------------------------------------------------------
# PASSWORD PROTECTION
# ------------------------------------------------------
def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        if st.session_state["password"] == "pharos2025":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        if os.path.exists("logo.jpg"):
            st.image("logo.jpg", width=250)
        else:
            st.title("🦅 Pharos Capital: BTM Model")
            st.caption("Please upload 'logo.jpg' for full branding.")
        st.markdown("---")
        st.markdown("### Access Required")
        st.text_input("Enter Password", type="password",
                      on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Enter Password", type="password",
                      on_change=password_entered, key="password")
        st.error("😕 Password incorrect")
        return False
    else:
        return True


if not check_password():
    st.stop()


# ------------------------------------------------------
# SESSION STATE & RESET LOGIC
# ------------------------------------------------------
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
    st.session_state.uploaded_files = []
    st.session_state.fx_rate_current = 4100.0
    # Default project identifiers
    if "project_name" not in st.session_state:
        st.session_state.project_name = "Hampton Inn Bogota - Aeropuerto"
    if "client_name" not in st.session_state:
        st.session_state.client_name = "Hampton Inn"
    if "project_loc" not in st.session_state:
        st.session_state.project_loc = "Bogota, Colombia"


if "ppa_term" not in st.session_state:
    set_base_case()


# ------------------------------------------------------
# PROJECT PERSISTENCE (DISK)
# ------------------------------------------------------
def load_projects_from_disk():
    if os.path.exists(PROJECTS_FILE):
        try:
            with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                # Ensure each project has inputs, scenarios and files keys
                for k, v in data.items():
                    if "inputs" not in v:
                        v["inputs"] = {}
                    if "scenarios" not in v:
                        v["scenarios"] = {}
                    if "files" not in v:
                        v["files"] = []
                return data
        except Exception:
            pass
    return {}


def save_projects_to_disk():
    try:
        with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
            json.dump(st.session_state["projects"], f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"Could not save projects to disk: {e}")


if "projects" not in st.session_state:
    st.session_state["projects"] = load_projects_from_disk()

# Ensure at least one project exists
if not st.session_state["projects"]:
    st.session_state["projects"]["Default Project"] = {
        "inputs": {},
        "scenarios": {},
        "files": []
    }

if "active_project" not in st.session_state:
    st.session_state["active_project"] = list(st.session_state["projects"].keys())[0]


def apply_project_inputs(project_name: str):
    """Load saved inputs for a project into session_state."""
    proj = st.session_state["projects"].get(project_name, {})
    inputs = proj.get("inputs", {})
    for k, v in inputs.items():
        st.session_state[k] = v


def save_current_inputs_to_project():
    """Capture current session_state inputs into active project's 'inputs'."""
    proj_name = st.session_state["active_project"]
    proj_dict = st.session_state["projects"].setdefault(
        proj_name, {"inputs": {}, "scenarios": {}}
    )
    inputs = {}
    for key in PROJECT_INPUT_KEYS:
        if key in st.session_state:
            inputs[key] = st.session_state[key]
    proj_dict["inputs"] = inputs
    save_projects_to_disk()


# Apply project inputs only once on first load
if "projects_loaded" not in st.session_state:
    apply_project_inputs(st.session_state["active_project"])
    st.session_state["projects_loaded"] = True

# ------------------------------------------------------
# CUSTOM STYLING
# ------------------------------------------------------
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


# ------------------------------------------------------
# TRANSLATION DICTIONARY
# ------------------------------------------------------
LANG = {
    "English": {
        "header_proj": "Project Name", "header_client": "Client Name", "header_loc": "Location",
        "curr_title": "0. Currency & FX", "curr_display": "Display Currency",
        "curr_fx": "Current FX Rate (COP/USD)", "curr_inf": "US Inflation (Annual %)",

        "s1_title": "1. Timeline & Revenue", "s1_time": "Project Timeline",
        "s1_year": "Start Year", "s1_q": "Start Quarter",
        "s1_contract": "Contract Details", "s1_dur": "PPA Duration (Years)",
        "s1_tariff": "Current Tariff", "s1_inf": "Utility Inflation (Annual %)",
        "s1_disc": "Discount to Client (%)", "s1_link": "Index PPA Price to Inflation?",
        "s1_lock": "Escalator locked to Inflation", "s1_esc": "PPA Escalator (Annual %)",
        "s1_tech": "Technical & Generation", "s1_mod": "Modules",
        "s1_pow": "Module Power (W)", "s1_deg": "Degradation (Annual %)",
        "s1_gen_lbl": "Contracted Energy (MWh/yr)",
        "s1_cons": "Client Total Consumption (MWh/yr)",

        "s2_title": "2. Costs", "s2_const": "Construction Period (Quarters)",
        "s2_capex": "Total CAPEX", "s2_opex": "Annual OPEX",
        "s2_oinf": "OPEX Inflation (Annual %)",
        "s2_sga": "SGA (% of Gross Profit)",
        "s2_sgaconst": "SGA During Construction (%)",

        "s3_title": "3. Tax", "s3_tax": "Corporate Income Tax (%)",
        "s3_cap": "Capital Gains Tax (%)",
        "s3_dep": "Depreciation Term (Years)",
        "s3_dut": "Duties and Others",
        "s3_ftt": "4x1000 FTT Rate (%)",
        "s3_ica": "Include ICA Tax (2%)?",
        "s3_ica_rate": "ICA Rate (%)",
        "s3_capex_ben": "Apply CAPEX Tax Benefit (Law 1715, 50% of CAPEX)?",
        "s3_capex_years": "Benefit Window (Years after COD, max 15)",
        "s3_capex_pct": "Eligible CAPEX for Benefit (%)",

        "s4_title": "4. Financing", "s4_enable": "Include Debt?",
        "s4_ratio": "Debt Ratio (%)", "s4_int": "Interest Rate (Annual %)",
        "s4_tenor": "Loan Tenor (Years)", "s4_fee": "Structuring Fee (%)",
        "s4_grace": "Grace Period (Quarters)",

        "s5_title": "5. Scenario", "s5_method": "Exit Method",
        "s5_year": "Exit Year", "s5_val": "Asset Sale Value (M COP)",
        "s5_mult": "Valuation Multiple (x EBITDA)",
        "s5_ke": "Investor Discount Rate (Ke %)",

        "kpi_eq": "Equity Investment", "kpi_tar": "Start Contract Tariff",
        "kpi_irr": "Equity IRR", "kpi_npv": "Equity NPV",
        "kpi_moic": "MOIC", "kpi_cov": "Project Coverage",

        "card_proj": "🏗️ Project (Unlevered)",
        "card_eq": "🦅 Equity (Levered)",
        "card_lev": "⚖️ Leverage Boost",
        "lbl_lev": "Leverage",
        "lbl_nodebt": "Debt Disabled",

        "rev_proof": "🔎 Revenue Calculation Detail",
        "chart_cf": "💰 Cash Flow Comparison",
        "tab_full": "🔎 Full Cash Flow Statement",
        "tab_pl": "📑 Income Statement (P&L)",

        "sim_title": "⚡ 5. Simulation Matrix - Equity IRR Sensitivity for Client Asset Buy-Back (Asset Value Sale Back vs. Sale Year)",
        "sim_run": "▶️ Run Simulation",
        "sim_min": "Min Asset Value",
        "sim_max": "Max Asset Value",
        "sim_step": "Step Size",
        "sim_chart": "Equity IRR Sensitivity for Buy-Back Scenario",
        "sim_match_title": "Simulation points with IRR close to base case",

        "col_gen": "Generation",
        "col_rev": "Revenue",
        "col_price": "Avg Tariff",
        "col_ftt": "FTT Cost",

        "s6_title": "6. Document Audit Trail"
    },
    "Español": {
        "header_proj": "Nombre del Proyecto", "header_client": "Cliente",
        "header_loc": "Ubicación",
        "curr_title": "0. Moneda y TRM", "curr_display": "Moneda Visual",
        "curr_fx": "TRM Actual (COP/USD)", "curr_inf": "Inflación USA (Anual %)",

        "s1_title": "1. Plazos e Ingresos", "s1_time": "Cronograma",
        "s1_year": "Año Inicio", "s1_q": "Trimestre Inicio",
        "s1_contract": "Detalles del Contrato", "s1_dur": "Duración PPA (Años)",
        "s1_tariff": "Tarifa Actual", "s1_inf": "Inflación Servicios (Anual %)",
        "s1_disc": "Descuento al Cliente (%)",
        "s1_link": "¿Indexar PPA a Inflación?",
        "s1_lock": "Escalador atado a Inflación",
        "s1_esc": "Escalador PPA (Anual %)",
        "s1_tech": "Técnico y Generación",
        "s1_mod": "Módulos", "s1_pow": "Potencia Módulo (W)",
        "s1_deg": "Degradación (Anual %)",
        "s1_gen_lbl": "Energía Contratada (MWh/año)",
        "s1_cons": "Consumo Total Cliente (MWh/año)",

        "s2_title": "2. Costos",
        "s2_const": "Periodo Construcción (Trimestres)",
        "s2_capex": "CAPEX Total",
        "s2_opex": "OPEX Anual",
        "s2_oinf": "Inflación OPEX (Anual %)",
        "s2_sga": "SGA (% de Utilidad Bruta)",
        "s2_sgaconst": "SGA Durante Construcción (%)",

        "s3_title": "3. Impuestos", "s3_tax": "Impuesto de Renta (%)",
        "s3_cap": "Ganancia Ocasional (%)",
        "s3_dep": "Plazo Depreciación (Años)",
        "s3_dut": "Gravámenes y Otros",
        "s3_ftt": "Tasa 4x1000 (%)",
        "s3_ica": "¿Incluir Impuesto ICA (2%)?",
        "s3_ica_rate": "Tasa ICA (%)",
        "s3_capex_ben": "¿Aplicar beneficio Ley 1715 (50% CAPEX)?",
        "s3_capex_years": "Ventana Beneficio (Años después de COD, máx. 15)",
        "s3_capex_pct": "% de CAPEX Elegible para Beneficio",

        "s4_title": "4. Financiación",
        "s4_enable": "¿Incluir Deuda?",
        "s4_ratio": "Nivel de Deuda (%)",
        "s4_int": "Tasa Interés (Anual %)",
        "s4_tenor": "Plazo Crédito (Años)",
        "s4_fee": "Comisión Estructuración (%)",
        "s4_grace": "Periodo de Gracia (Trimestres)",

        "s5_title": "5. Escenario",
        "s5_method": "Método de Salida",
        "s5_year": "Año de Salida",
        "s5_val": "Valor Venta Activo (M COP)",
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

        "sim_title": "⚡ 5. Matriz de Simulación - Sensibilidad de TIR Equity para Recompra del Activo por el Cliente (Valor de Venta vs. Año de Venta)",
        "sim_run": "▶️ Ejecutar Simulación",
        "sim_min": "Valor Min",
        "sim_max": "Valor Max",
        "sim_step": "Paso",
        "sim_chart": "Sensibilidad de TIR Equity para Escenario de Recompra",
        "sim_match_title": "Puntos de simulación con TIR cercana al caso base",

        "col_gen": "Generación",
        "col_rev": "Ingresos",
        "col_price": "Tarifa Prom",
        "col_ftt": "Costo 4x1000",

        "s6_title": "6. Trazabilidad de Documentos"
    }
}


# ------------------------------------------------------
# LANGUAGE SELECTOR
# ------------------------------------------------------
sel_lang = st.sidebar.selectbox("Language / Idioma", ["English", "Español"])
T = LANG[sel_lang]


# ------------------------------------------------------
# RESET BUTTON
# ------------------------------------------------------
if st.sidebar.button("↺ Reset to Base Case"):
    set_base_case()
    save_current_inputs_to_project()
    st.rerun()


# ------------------------------------------------------
# PROJECT SELECTION (MULTI-PROJECT HANDLING)
# ------------------------------------------------------
st.markdown("### Active Project")

proj_names = sorted(st.session_state["projects"].keys())
current_proj = st.session_state["active_project"]
if current_proj not in proj_names:
    current_proj = proj_names[0]

col_p1, col_p2 = st.columns([3, 2])
with col_p1:
    selected_proj = st.selectbox(
        "Select project",
        proj_names,
        index=proj_names.index(current_proj)
    )
with col_p2:
    new_proj_name = st.text_input("New project name", value="", key="new_project_name")
    if st.button("➕ Create project"):
        name = new_proj_name.strip()
        if name:
            if name not in st.session_state["projects"]:
                st.session_state["projects"][name] = {"inputs": {}, "scenarios": {}}
                st.session_state["active_project"] = name
                save_projects_to_disk()
                apply_project_inputs(name)
                st.success(f"Project '{name}' created.")
                st.rerun()
            else:
                st.warning("A project with that name already exists.")
                
# --- Delete project ---
if len(st.session_state["projects"]) > 1:
    st.markdown("#### Delete project")
    col_dp1, col_dp2 = st.columns([3, 1])

    with col_dp1:
        project_to_delete = st.selectbox(
            "Select project to delete",
            proj_names,
            key="project_to_delete"
        )

    with col_dp2:
        if st.button("🗑️ Delete selected project"):
            if project_to_delete in st.session_state["projects"]:
                # Remove project
                del st.session_state["projects"][project_to_delete]

                # If we deleted the active project, move active to another remaining one
                if st.session_state["active_project"] == project_to_delete:
                    remaining = list(st.session_state["projects"].keys())
                    if remaining:
                        st.session_state["active_project"] = remaining[0]

                save_projects_to_disk()
                st.success(f"Project '{project_to_delete}' deleted.")
                st.rerun()
else:
    st.caption("At least one project must exist. Cannot delete the last project.")

# If user changed project, switch and rerun
if selected_proj != current_proj:
    st.session_state["active_project"] = selected_proj
    apply_project_inputs(selected_proj)
    st.rerun()

st.markdown("---")


# ------------------------------------------------------
# HEADER
# ------------------------------------------------------
col_logo, col_title = st.columns([1, 6])
with col_logo:
    if os.path.exists("logo.jpg"):
        st.image("logo.jpg", width=150)
    else:
        st.write("🦅")
with col_title:
    st.title("Pharos Capital: BTM Model")

c_proj1, c_proj2, c_proj3 = st.columns(3)
with c_proj1:
    project_name = st.text_input(
        T["header_proj"],
        key="project_name",
        value=st.session_state.get("project_name", "Hampton Inn Bogota - Aeropuerto")
    )
with c_proj2:
    client_name = st.text_input(
        T["header_client"],
        key="client_name",
        value=st.session_state.get("client_name", "Hampton Inn")
    )
with c_proj3:
    project_loc = st.text_input(
        T["header_loc"],
        key="project_loc",
        value=st.session_state.get("project_loc", "Bogota, Colombia")
    )

st.markdown("---")


# ------------------------------------------------------
# 0. SETTINGS
# ------------------------------------------------------
with st.sidebar.expander(T["curr_title"], expanded=True):
    currency_mode = st.radio(T["curr_display"],
                             ["COP (Millions)", "USD (Thousands)"],
                             horizontal=False)
    symbol = "$" if "USD" in currency_mode else ""
    fx_rate_current = st.number_input(T["curr_fx"],
                                      value=st.session_state.fx_rate_current,
                                      step=50.0, format="%.1f")
    st.session_state.fx_rate_current = fx_rate_current
    us_inflation_annual = st.number_input(T["curr_inf"],
                                          value=2.5, step=0.1,
                                          format="%.1f") / 100

inv_conv_factor_base = 1000 / st.session_state.fx_rate_current if "USD" in currency_mode else 1


# ------------------------------------------------------
# 1. TIMELINE & REVENUE
# ------------------------------------------------------
with st.sidebar.expander(T["s1_title"], expanded=False):
    st.markdown(f"**{T['s1_time']}**")
    c_start1, c_start2 = st.columns(2)
    with c_start1:
        start_year = st.number_input(T["s1_year"],
                                     value=int(st.session_state.get("start_year", 2026)),
                                     step=1)
    with c_start2:
        start_q_str = st.selectbox(
            T["s1_q"],
            ["Q1", "Q2", "Q3", "Q4"],
            index=["Q1", "Q2", "Q3", "Q4"].index(
                st.session_state.get("start_q_str", "Q1")
            )
        )
    st.session_state["start_year"] = start_year
    st.session_state["start_q_str"] = start_q_str
    start_q_num = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}[start_q_str]

    st.markdown("---")
    st.markdown(f"**{T['s1_contract']}**")
    ppa_term_years = st.slider(T["s1_dur"], 5, 20, key="ppa_term")
    current_tariff = st.number_input(f"{T['s1_tariff']} ($/kWh)",
                                     key="tariff_val", step=10.0,
                                     format="%.1f")
    utility_inflation_annual = st.number_input(T["s1_inf"],
                                               key="inf_val",
                                               step=0.5,
                                               format="%.1f") / 100
    discount_rate = st.number_input(T["s1_disc"],
                                    key="disc_val",
                                    step=1.0,
                                    format="%.1f") / 100

    link_to_inflation = st.checkbox(T["s1_link"], key="link_inf")
    if link_to_inflation:
        pcp_escalator_annual = utility_inflation_annual
        st.info(f"🔒 {T['s1_lock']} ({utility_inflation_annual * 100:.1f}%)")
    else:
        pcp_escalator_annual = st.number_input(T["s1_esc"],
                                               key="esc_val",
                                               step=0.5,
                                               format="%.1f") / 100

    st.markdown("---")
    st.caption(T["s1_tech"])
    initial_gen_mwh_annual = st.number_input(T["s1_gen_lbl"],
                                             key="gen_val",
                                             step=0.1,
                                             format="%.1f")
    client_consumption = st.number_input(T["s1_cons"],
                                         key="cons_val",
                                         step=10.0,
                                         format="%.1f")
    if client_consumption > 0:
        coverage_pct = (initial_gen_mwh_annual / client_consumption) * 100
    else:
        coverage_pct = 0
    st.metric(T["kpi_cov"], f"{coverage_pct:.1f}%")
    degradation_annual = st.number_input(T["s1_deg"],
                                         key="deg_val",
                                         step=0.1,
                                         format="%.1f") / 100


# ------------------------------------------------------
# 2. COSTS
# ------------------------------------------------------
with st.sidebar.expander(T["s2_title"], expanded=False):
    st.markdown("**CAPEX & OPEX**")
    construction_quarters = st.slider(T["s2_const"], 0, 8, key="const_q")
    capex_million_cop = st.number_input(f"{T['s2_capex']} (M COP)",
                                        key="capex_val",
                                        step=10.0,
                                        format="%.1f")
    opex_million_cop_annual = st.number_input(
        f"{T['s2_opex']} (M COP/yr)", key="opex_val",
        step=0.5, format="%.1f"
    )
    opex_inflation_annual = st.number_input(T["s2_oinf"],
                                            key="oinf_val",
                                            step=0.5,
                                            format="%.1f") / 100
    sga_percent = st.number_input(T["s2_sga"],
                                  key="sga_val",
                                  step=1.0,
                                  format="%.1f") / 100

    sga_const_pct = st.number_input(
        T["s2_sgaconst"], key="sga_const_val",
        step=0.1, format="%.1f",
        help="SGA as % of CAPEX, capitalized during construction"
    ) / 100
    sga_const_cost_cop = capex_million_cop * sga_const_pct
    sga_const_cost_disp = sga_const_cost_cop * inv_conv_factor_base
    st.write(f"**Cost:** {symbol}{sga_const_cost_disp:,.1f} {currency_mode.split()[0]}")


# ------------------------------------------------------
# 3. TAX
# ------------------------------------------------------
with st.sidebar.expander(T["s3_title"], expanded=False):
    st.markdown("**Fiscal Regime**")
    tax_rate = st.number_input(T["s3_tax"],
                               key="tax_val",
                               step=1.0,
                               format="%.1f") / 100
    cap_gains_rate = st.number_input(T["s3_cap"],
                                     key="cg_val",
                                     step=1.0,
                                     format="%.1f") / 100
    depreciation_years = st.slider(T["s3_dep"], 3, 25, key="dep_val")

    st.markdown("---")
    st.caption(T["s3_dut"])
    ftt_rate = st.number_input(
        T["s3_ftt"], key="ftt_val",
        value=0.4, step=0.1,
        format="%.1f",
        help="Applied to cash disbursements: CAPEX, OPEX, SGA, Debt Service, Tax"
    ) / 1000

    enable_ica = st.checkbox(T["s3_ica"], key="ica_on")
    if enable_ica:
        ica_rate = st.number_input(
            T["s3_ica_rate"], key="ica_rate",
            value=2.0, step=0.1,
            format="%.1f",
            help="Applied to Total Revenue"
        ) / 100
    else:
        ica_rate = 0.0

    st.markdown("---")
    st.markdown("**Ley 1715 - CAPEX Tax Benefit**")
    enable_capex_benefit = st.checkbox(T["s3_capex_ben"], key="capex_benefit_on", value=False)
    if enable_capex_benefit:
        capex_benefit_years = st.slider(
            T["s3_capex_years"], 1, 15,
            value=int(st.session_state.get("capex_benefit_years", 10)),
            key="capex_benefit_years"
        )
        capex_benefit_capex_pct = st.slider(
            T["s3_capex_pct"], 0, 100,
            value=int(st.session_state.get("capex_benefit_capex_pct", 100)),
            key="capex_benefit_capex_pct"
        ) / 100.0
    else:
        capex_benefit_years = 0
        capex_benefit_capex_pct = 0.0
        st.session_state["capex_benefit_years"] = 0
        st.session_state["capex_benefit_capex_pct"] = 0.0


# ------------------------------------------------------
# 4. FINANCING
# ------------------------------------------------------
with st.sidebar.expander(T["s4_title"], expanded=False):
    st.markdown("**Debt Structure**")
    enable_debt = st.checkbox(T["s4_enable"], key="debt_on")
    if enable_debt:
        debt_ratio = st.slider(T["s4_ratio"], 0, 100, key="dr_val") / 100
        interest_rate_annual = st.number_input(T["s4_int"],
                                               key="int_val",
                                               step=0.1,
                                               format="%.1f") / 100
        loan_tenor_years = st.number_input(T["s4_tenor"],
                                           key="tenor_val", step=1)
        structuring_fee_pct = st.number_input(T["s4_fee"],
                                              key="fee_val",
                                              step=0.1,
                                              format="%.1f") / 100
        grace_period_quarters = st.number_input(T["s4_grace"],
                                                key="grace_val",
                                                step=1)
    else:
        debt_ratio = 0.0
        interest_rate_annual = 0.0
        loan_tenor_years = 0
        structuring_fee_pct = 0.0
        grace_period_quarters = 0


# ------------------------------------------------------
# 5. SCENARIO / EXIT
# ------------------------------------------------------
with st.sidebar.expander(T["s5_title"], expanded=False):
    st.markdown("**Valuation**")
    dash_exit_strategy = st.radio(T["s5_method"],
                                  ["Fixed Asset Value", "EBITDA Multiple"],
                                  key="exit_method")
    dash_exit_year = st.slider(T["s5_year"], 2, ppa_term_years, key="exit_yr")
    if dash_exit_strategy == "Fixed Asset Value":
        dash_exit_val_cop = st.number_input(T["s5_val"],
                                            key="exit_asset_val",
                                            step=5.0,
                                            format="%.1f")
        dash_exit_mult = 0
    else:
        dash_exit_mult = st.number_input(T["s5_mult"],
                                         key="exit_mult_val",
                                         step=0.5,
                                         format="%.1f")
        dash_exit_val_cop = 0

    st.markdown("---")
    investor_disc_rate = st.number_input(T["s5_ke"],
                                         key="ke_val",
                                         step=0.5,
                                         format="%.1f") / 100

# Save inputs for this project (auto)
save_current_inputs_to_project()


# ------------------------------------------------------
# 6. DOCUMENT AUDIT TRAIL (per project)
# ------------------------------------------------------
with st.sidebar.expander(T["s6_title"], expanded=False):
    uploaded_files = st.file_uploader(
        "Upload Source Documents (PDFs, Images, CSVs)",
        type=['pdf', 'png', 'jpg', 'jpeg', 'csv'],
        accept_multiple_files=True
    )

    # Ensure current project record has a 'files' list
    active_proj = st.session_state["active_project"]
    proj_entry = st.session_state["projects"].setdefault(
        active_proj,
        {"inputs": {}, "scenarios": {}, "files": []}
    )
    files_list = proj_entry.setdefault("files", [])

    # Handle new uploads
    if uploaded_files:
        os.makedirs(ATTACHMENTS_DIR, exist_ok=True)
        proj_folder = os.path.join(
            ATTACHMENTS_DIR,
            active_proj.replace(" ", "_")
        )
        os.makedirs(proj_folder, exist_ok=True)

        for file in uploaded_files:
            raw_data = file.read()

            # Build a safe, non-colliding path
            base_name, ext = os.path.splitext(file.name)
            save_path = os.path.join(proj_folder, file.name)
            counter = 1
            while os.path.exists(save_path):
                save_path = os.path.join(
                    proj_folder,
                    f"{base_name}_{counter}{ext}"
                )
                counter += 1

            # Write to disk
            with open(save_path, "wb") as f:
                f.write(raw_data)

            # Add metadata if not already there
            if not any(fm.get("path") == save_path for fm in files_list):
                files_list.append({
                    "name": file.name,
                    "type": file.type,
                    "path": save_path
                })

        save_projects_to_disk()
        st.success(f"Uploaded {len(uploaded_files)} file(s) to project '{active_proj}'.")

    # List existing files for this project

    # List existing files for this project
    if files_list:
        st.markdown("##### Files stored for this project")

        # We iterate with index so we can safely delete entries
        for idx, fm in enumerate(list(files_list)):  # list() to avoid mutation issues
            fname = fm.get("name", "Unnamed")
            ftype = fm.get("type", "unknown")
            fpath = fm.get("path")

            c1, c2, c3 = st.columns([4, 1, 1])

            with c1:
                st.write(f"📄 **{fname}**  _({ftype})_")

            # Download button — key uses idx so duplicates are allowed
            with c2:
                if fpath and os.path.exists(fpath):
                    with open(fpath, "rb") as f:
                        st.download_button(
                            label="⬇️",
                            data=f.read(),
                            file_name=fname,
                            mime=ftype or "application/octet-stream",
                            key=f"download_{active_proj}_{idx}"
                        )
                else:
                    st.caption("Missing")

            # Delete button
            with c3:
                if st.button("🗑️", key=f"delete_{active_proj}_{idx}"):
                    # Remove file from disk if still present
                    if fpath and os.path.exists(fpath):
                        try:
                            os.remove(fpath)
                        except Exception as e:
                            st.warning(f"Could not delete file from disk: {e}")

                    # Remove from metadata list
                    try:
                        del files_list[idx]
                        save_projects_to_disk()
                    except Exception as e:
                        st.warning(f"Error updating file list: {e}")

                    st.success(f"File '{fname}' deleted from project '{active_proj}'.")
                    st.rerun()
    else:
        st.caption("No files uploaded yet for this project.")


# ------------------------------------------------------
# ENGINE
# ------------------------------------------------------
full_quarters = construction_quarters + (ppa_term_years * 4)
quarters_range = list(range(1, full_quarters + 1))

if enable_debt:
    structuring_fee = (capex_million_cop * debt_ratio) * structuring_fee_pct
    total_debt_principal = capex_million_cop * debt_ratio
    interest_rate_quarterly = interest_rate_annual / 4
    loan_tenor_quarters = loan_tenor_years * 4
    quarterly_debt_pmt = -npf.pmt(
        interest_rate_quarterly,
        loan_tenor_quarters - grace_period_quarters,
        total_debt_principal
    ) if (loan_tenor_quarters - grace_period_quarters) > 0 else 0
else:
    structuring_fee = 0
    total_debt_principal = 0
    interest_rate_quarterly = 0.0
    quarterly_debt_pmt = 0

sga_const_cost_cop = capex_million_cop * sga_const_pct
total_capex_cost = capex_million_cop + structuring_fee + sga_const_cost_cop
equity_investment_levered_cop = total_capex_cost - total_debt_principal
equity_investment_unlevered_cop = total_capex_cost

# CAPEX tax benefit pool (Ley 1715)
if enable_capex_benefit and capex_benefit_years > 0:
    eligible_capex = capex_million_cop * capex_benefit_capex_pct
    capex_benefit_total = 0.5 * eligible_capex
    capex_benefit_remaining = capex_benefit_total
else:
    eligible_capex = 0.0
    capex_benefit_total = 0.0
    capex_benefit_remaining = 0.0

q_list, gy_list, cal_list = [], [], []
gen_list, rev_list, ebitda_list = [], [], []
opex_list, sga_list, gross_list = [], [], []
dep_list, int_list, tax_list, ftt_list, ica_list = [], [], [], [], []
ufcf_list, lfcf_list, debt_bal_list, book_val_list, fx_rate_list = [], [], [], [], []

# NEW: debt schedule breakdown
opening_debt_list = []
principal_list = []

# Tax base tracking
base_unlev_list, base_lev_list = [], []
base_lev_pre_list = []
cum_base_unlev_list, cum_base_lev_list = [], []
cum_tax_unlev_list, cum_tax_lev_list = [], []
capex_benefit_q_list = []

debt_balance = total_debt_principal
accumulated_dep = 0

cum_base_unlev = 0.0
cum_base_lev = 0.0
cum_tax_unlev = 0.0
cum_tax_lev = 0.0
cum_base_lev_pre = 0.0

op_start_calendar_year = None

for i, q in enumerate(quarters_range):
    abs_q = (start_q_num - 1) + i
    cal_year = start_year + (abs_q // 4)
    t_years = i / 4
    fx_rate_q = fx_rate_current * ((1 + utility_inflation_annual) / (1 + us_inflation_annual)) ** t_years

    if q <= construction_quarters:
        phase = "Construction"
        q_op_index = 0
        op_year = 0
    else:
        phase = "Operation"
        q_op_index = q - construction_quarters
        op_year = (q_op_index - 1) // 4 + 1
        if op_start_calendar_year is None:
            op_start_calendar_year = cal_year

    global_year = (q - 1) // 4 + 1

    if phase == "Operation":
        esc_factor = (1 + pcp_escalator_annual) ** ((q_op_index - 1) / 4)
        deg_factor = (1 - degradation_annual) ** ((q_op_index - 1) / 4)
        opex_fac = (1 + opex_inflation_annual) ** ((q_op_index - 1) / 4)

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
        gen_quarterly = rev = opex = gross = sga = ica_cost = ebitda = dep = 0

    if phase == "Construction" and construction_quarters > 0:
        capex_unlevered = capex_million_cop / construction_quarters
        capex_levered = equity_investment_levered_cop / construction_quarters
        sga_const_outflow = sga_const_cost_cop / construction_quarters
        capex_levered += sga_const_outflow
    else:
        capex_unlevered = capex_levered = sga_const_outflow = 0

    for i, q in enumerate(quarters_range):
        abs_q = (start_q_num - 1) + i
        cal_year = start_year + (abs_q // 4)
        ...
        op_year = (q_op_index - 1) // 4 + 1
        ...
    
        # NEW: store opening balance for this quarter
        opening_debt = debt_balance
    
        if debt_balance > 0:
            interest = debt_balance * interest_rate_quarterly
            if q > grace_period_quarters:
                principal = quarterly_debt_pmt - interest
                if principal > debt_balance:
                    principal = debt_balance
            else:
                principal = 0
            debt_balance -= principal
        else:
            interest = principal = 0

    if debt_balance > 0:
        interest = debt_balance * interest_rate_quarterly
        if q > grace_period_quarters:
            principal = quarterly_debt_pmt - interest
            if principal > debt_balance:
                principal = debt_balance
        else:
            principal = 0
        debt_balance -= principal
    else:
        interest = principal = 0

    # Tax base before benefit
    base_lev_pre = ebitda - interest - dep

    prev_cum_base_lev_pre = cum_base_lev_pre
    cum_base_lev_pre += base_lev_pre

    eff_base_q = max(cum_base_lev_pre, 0) - max(prev_cum_base_lev_pre, 0)

    capex_tax_benefit_q = 0.0

    if (
        enable_capex_benefit
        and phase == "Operation"
        and op_start_calendar_year is not None
        and cal_year >= op_start_calendar_year + 1
        and cal_year < op_start_calendar_year + 1 + capex_benefit_years
        and capex_benefit_remaining > 0
        and eff_base_q > 0
    ):
        max_allowed_this_q = 0.5 * eff_base_q
        capex_tax_benefit_q = min(capex_benefit_remaining, max_allowed_this_q)
        capex_benefit_remaining -= capex_tax_benefit_q

    base_unlev = ebitda - dep - capex_tax_benefit_q
    base_lev = base_lev_pre - capex_tax_benefit_q

    cum_base_unlev += base_unlev
    cum_base_lev += base_lev

    theor_tax_unlev = tax_rate * max(cum_base_unlev, 0)
    theor_tax_lev = tax_rate * max(cum_base_lev, 0)

    tax_unlevered = max(0, theor_tax_unlev - cum_tax_unlev)
    tax_levered = max(0, theor_tax_lev - cum_tax_lev)

    cum_tax_unlev += tax_unlevered
    cum_tax_lev += tax_levered

    if enable_debt:
        total_disbursements = capex_levered + opex + sga + principal + interest + tax_levered
    else:
        total_disbursements = capex_unlevered + opex + sga + tax_unlevered

    ftt_cost = total_disbursements * ftt_rate

    accumulated_dep += dep
    book_val = max(0, capex_million_cop - accumulated_dep)

    ufcf = ebitda - tax_unlevered - capex_unlevered - ftt_cost
    if enable_debt:
        lfcf = ebitda - tax_levered - interest - principal - capex_levered - ftt_cost
    else:
        lfcf = ufcf

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

    ufcf_list.append(ufcf)
    lfcf_list.append(lfcf)

    # NEW: save debt schedule info
    opening_debt_list.append(opening_debt)
    principal_list.append(principal)
    debt_bal_list.append(debt_balance)
    book_val_list.append(book_val)
    fx_rate_list.append(fx_rate_q)

    base_unlev_list.append(base_unlev)
    base_lev_list.append(base_lev)
    base_lev_pre_list.append(base_lev_pre)
    cum_base_unlev_list.append(cum_base_unlev)
    cum_base_lev_list.append(cum_base_lev)
    cum_tax_unlev_list.append(cum_tax_unlev)
    cum_tax_lev_list.append(cum_tax_lev)
    capex_benefit_q_list.append(capex_tax_benefit_q)

df_full = pd.DataFrame({
    "Quarter": q_list, "Global_Year": gy_list, "Calendar_Year": cal_list,
    "FX_Rate": fx_rate_list, "Generation_MWh": gen_list,
    "Revenue_M_COP": rev_list, "OPEX_M_COP": opex_list, "Gross_M_COP": gross_list,
    "SGA_M_COP": sga_list, "ICA_M_COP": ica_list, "EBITDA_M_COP": ebitda_list,
    "Depreciation_M_COP": dep_list, "Interest_M_COP": int_list, "Tax_M_COP": tax_list,
    "FTT_M_COP": ftt_list, "UFCF_M_COP": ufcf_list, "LFCF_M_COP": lfcf_list,
    # NEW:
    "Opening_Debt_M_COP": opening_debt_list,
    "Principal_M_COP": principal_list,
    "Debt_Balance_M_COP": debt_bal_list, "Book_Value_M_COP": book_val_list,
    "Tax_Base_Unlev_M_COP": base_unlev_list,
    "Tax_Base_Lev_PreBenefit_M_COP": base_lev_pre_list,
    "Tax_Base_Lev_M_COP": base_lev_list,
    "Tax_Base_Unlev_Cum_M_COP": cum_base_unlev_list,
    "Tax_Base_Lev_Cum_M_COP": cum_base_lev_list,
    "Tax_Unlev_Cum_M_COP": cum_tax_unlev_list,
    "Tax_Lev_Cum_M_COP": cum_tax_lev_list,
    "Capex_Tax_Benefit_M_COP": capex_benefit_q_list
})

conversion_factor = 1000 / df_full["FX_Rate"] if "USD" in currency_mode else 1
for col in ["Revenue", "OPEX", "Gross", "SGA", "ICA", "EBITDA",
            "Depreciation", "Interest", "Tax", "FTT", "UFCF", "LFCF"]:
    df_full[f"{col}_Disp"] = df_full[f"{col}_M_COP"] * conversion_factor


# Exit logic
if dash_exit_strategy == "Fixed Asset Value":
    final_exit_val_cop = dash_exit_val_cop
else:
    exit_q_idx = construction_quarters + (dash_exit_year * 4) - 1
    start_idx = max(0, exit_q_idx - 3)
    annual_ebitda = df_full.iloc[start_idx:exit_q_idx + 1]["EBITDA_M_COP"].sum()
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

agg_cols = ["Generation_MWh", "Revenue_Disp", "OPEX_Disp", "Gross_Disp",
            "SGA_Disp", "ICA_Disp", "EBITDA_Disp", "Depreciation_Disp",
            "Interest_Disp", "Tax_Disp", "FTT_Disp",
            "UFCF_Disp", "LFCF_Disp"]
df_annual_dash = df_dash.groupby("Calendar_Year")[agg_cols].sum().reset_index()
df_annual_full = df_full.groupby("Calendar_Year")[agg_cols].sum().reset_index()

df_annual_dash["Implied_Price_Unit"] = 0.0
mask = df_annual_dash["Generation_MWh"] > 0
if "USD" in currency_mode:
    df_annual_dash.loc[mask, "Implied_Price_Unit"] = (
        df_annual_dash.loc[mask, "Revenue_Disp"] / df_annual_dash.loc[mask, "Generation_MWh"]
    )
else:
    df_annual_dash.loc[mask, "Implied_Price_Unit"] = (
        df_annual_dash.loc[mask, "Revenue_Disp"] / df_annual_dash.loc[mask, "Generation_MWh"]
    ) * 1000


def get_irr(stream):
    try:
        q_irr = npf.irr(stream)
        return ((1 + q_irr) ** 4 - 1) * 100
    except Exception:
        return 0


inv_conv = 1000 / fx_rate_current if "USD" in currency_mode else 1
equity_inv_disp = equity_investment_levered_cop * inv_conv
irr_unlevered = get_irr(df_dash["UFCF_Disp"])
irr_levered = get_irr(df_dash["LFCF_Disp"])
moic_levered = df_dash["LFCF_Disp"].sum() / equity_inv_disp if equity_inv_disp > 0 else 0
npv_equity = npf.npv(investor_disc_rate / 4, [0] + df_dash["LFCF_Disp"].tolist())
symbol = "$" if "USD" in currency_mode else ""


# ------------------------------------------------------
# SCENARIO MANAGEMENT (PER PROJECT)
# ------------------------------------------------------
st.markdown("### Scenario Management")

active_proj = st.session_state["active_project"]
proj_entry = st.session_state["projects"].setdefault(
    active_proj,
    {"inputs": {}, "scenarios": {}, "files": []}
)
scenarios_dict = proj_entry.setdefault("scenarios", {})

# --- Save scenario ---
scenario_name = st.text_input(
    "Scenario name (e.g. 'Base COP with debt 70%')",
    value="",
    key="scenario_name"
)

if st.button("💾 Save current scenario"):
    if not scenario_name.strip():
        st.warning("Please enter a scenario name before saving.")
    else:
        # 1st-year PPA price to client (COP $/kWh)
        ppa_price_year1_cop = current_tariff * (1 - discount_rate)

        scenarios_dict[scenario_name] = {
            "Equity_Investment": equity_inv_disp,
            "IRR_Levered_%": irr_levered,
            "MOIC_x": moic_levered,
            "Exit_Method": dash_exit_strategy,
            "Exit_Year": dash_exit_year,
            "Exit_Value_M_COP": final_exit_val_cop,
            "Client_Tariff_$perkWh": current_tariff,
            "PPA_Year1_$perkWh": ppa_price_year1_cop,
            "PPA_Years": ppa_term_years,
        }
        save_projects_to_disk()
        st.success(f"Scenario '{scenario_name}' saved for project '{active_proj}'.")

# --- Delete scenario (per project) ---
if scenarios_dict:
    st.markdown("#### Delete saved scenario (current project)")
    col_del1, col_del2 = st.columns([3, 1])

    with col_del1:
        scenario_to_delete = st.selectbox(
            "Select scenario to delete",
            list(scenarios_dict.keys()),
            key="scenario_to_delete"
        )

    with col_del2:
        if st.button("🗑️ Delete selected scenario"):
            if scenario_to_delete in scenarios_dict:
                del scenarios_dict[scenario_to_delete]
                save_projects_to_disk()
                st.success(f"Scenario '{scenario_to_delete}' deleted from project '{active_proj}'.")
                st.rerun()
else:
    st.caption("No saved scenarios for this project.")

def generate_excel_file():
    """
    Build a multi-sheet Excel workbook with:
    - Inputs
    - Quarterly model (full engine)
    - Annual summary
    - P&L (annual)
    - Tax diagnostics (levered)
    - Debt schedule
    - Scenarios (per project)
    - Simulation matrix (if run)
    - Summary KPIs
    """
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # 1) Inputs sheet from session_state
        inputs_rows = []
        for key in PROJECT_INPUT_KEYS:
            inputs_rows.append({
                "Input": key,
                "Value": st.session_state.get(key, None)
            })
        df_inputs = pd.DataFrame(inputs_rows)
        df_inputs.to_excel(writer, sheet_name="Inputs", index=False)

        # 2) Full quarterly model
        df_full.to_excel(writer, sheet_name="Quarterly_Model", index=False)

        # 3) Annual summary (your aggregated view)
        df_annual_full.to_excel(writer, sheet_name="Annual_Summary", index=False)

        # 4) P&L (annual) – rebuild like on screen
        pnl_data = df_annual_full.copy()
        pnl_data["EBIT_Disp"] = pnl_data["EBITDA_Disp"] - pnl_data["Depreciation_Disp"]
        pnl_data["EBT_Disp"] = pnl_data["EBIT_Disp"] - pnl_data["Interest_Disp"]
        pnl_data["Net_Income_Disp"] = pnl_data["EBT_Disp"] - pnl_data["Tax_Disp"]
        pnl_data.to_excel(writer, sheet_name="P&L_Annual", index=False)

        # 5) Tax diagnostics (levered)
        tax_view_xls = df_full[[
            "Calendar_Year",
            "Quarter",
            "EBITDA_M_COP",
            "Interest_M_COP",
            "Depreciation_M_COP",
            "Tax_Base_Lev_PreBenefit_M_COP",
            "Capex_Tax_Benefit_M_COP",
            "Tax_Base_Lev_M_COP",
            "Tax_Base_Lev_Cum_M_COP",
            "Tax_M_COP",
            "Tax_Lev_Cum_M_COP"
        ]].copy()
        tax_view_xls.to_excel(writer, sheet_name="Tax_Diagnostics", index=False)

        # 6) Debt schedule (opening, interest, principal, closing)
        debt_cols = [
            "Calendar_Year",
            "Quarter",
            "Opening_Debt_M_COP",
            "Interest_M_COP",
            "Principal_M_COP",
            "Debt_Balance_M_COP"
        ]
        debt_df = df_full[debt_cols].copy()
        debt_df.to_excel(writer, sheet_name="Debt_Schedule", index=False)

        # 7) Scenarios (for this project), if any
        if scenarios_dict:
            scen_df = pd.DataFrame.from_dict(scenarios_dict, orient="index")
            scen_df.index.name = "Scenario"
            scen_df.reset_index(inplace=True)
            scen_df.to_excel(writer, sheet_name="Scenarios", index=False)

        # 8) Simulation matrix, if user has run it in this session
        sim_df = st.session_state.get("sim_df", None)
        if sim_df is not None:
            sim_df.to_excel(writer, sheet_name="Simulation", index=False)

        # 9) Summary KPIs
        summary_data = {
            "Metric": [
                "Display Currency",
                "Equity Investment (disp units)",
                "Unlevered IRR (%)",
                "Levered IRR (%)",
                "Equity NPV (disp units)",
                "MOIC (x)"
            ],
            "Value": [
                currency_mode,
                equity_inv_disp,
                irr_unlevered,
                irr_levered,
                npv_equity,
                moic_levered
            ]
        }
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name="Summary", index=False)

        # Basic, global column width formatting
        for sheet_name in writer.sheets:
            ws = writer.sheets[sheet_name]
            ws.set_column(0, 0, 24)   # first col wider
            ws.set_column(1, 15, 18)  # rest

    output.seek(0)
    return output.getvalue()


# ------------------------------------------------------
# PDF HELPER FUNCTIONS (CHARTS)
# ------------------------------------------------------
def make_fcf_chart_image(df_annual_dash_local, currency_mode_local):
    unit_label = currency_mode_local
    years = df_annual_dash_local["Calendar_Year"].astype(int)
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.bar(years - 0.15, df_annual_dash_local["UFCF_Disp"],
           width=0.3, label="UFCF")
    ax.bar(years + 0.15, df_annual_dash_local["LFCF_Disp"],
           width=0.3, label="LFCF")
    ax.set_title(f"Free Cash Flows by Year ({unit_label})")
    ax.set_xlabel("Year")
    ax.set_ylabel(unit_label)
    ax.legend()
    fig.tight_layout()
    tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    fig.savefig(tmpfile.name, dpi=150)
    plt.close(fig)
    return tmpfile.name


def make_sim_heatmap_image(sim_df_local, T_local, currency_mode_local):
    if sim_df_local is None or sim_df_local.empty:
        return None

    # sim_df_local must have ExitYear, ExitValue, IRR
    pivot = sim_df_local.pivot(index="ExitYear", columns="ExitValue", values="IRR")
    years = pivot.index.values
    vals = pivot.columns.values

    fig, ax = plt.subplots(figsize=(6, 4))
    c = ax.imshow(pivot.values, aspect="auto", origin="lower")
    ax.set_xticks(np.arange(len(vals)))
    ax.set_xticklabels(vals, rotation=45, ha="right")
    ax.set_yticks(np.arange(len(years)))
    ax.set_yticklabels(years)
    ax.set_xlabel(T_local["s5_val"])
    ax.set_ylabel(T_local["s5_year"])
    ax.set_title(f"{T_local['sim_chart']} ({currency_mode_local})")
    fig.colorbar(c, ax=ax, label="IRR %")
    fig.tight_layout()
    tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    fig.savefig(tmpfile.name, dpi=150)
    plt.close(fig)
    return tmpfile.name


# ------------------------------------------------------
# PDF GENERATION
# ------------------------------------------------------
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


def create_pdf(df_agg, df_annual_dash_local, proj_name, cli_name, loc,
               curr_sym, currency_mode_local, fx_rate_current_local,
               sim_df_local=None, close_df_local=None):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Units note
    pdf.set_font("Arial", 'I', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"All monetary figures in {currency_mode_local}", 0, 1, 'R')
    pdf.ln(2)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", size=12)

    # Compute Year-1 PPA price to client
    ppa_price_year1_cop = current_tariff * (1 - discount_rate)
    if "USD" in currency_mode_local:
        ppa_price_year1_disp = ppa_price_year1_cop / fx_rate_current_local
    else:
        ppa_price_year1_disp = ppa_price_year1_cop

    # 1. Project Overview
    pdf.set_fill_color(14, 47, 68)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, "1. Project Overview", 0, 1, 'L', 1)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)
    pdf.cell(90, 7, f"Project: {proj_name}", 0, 0)
    pdf.cell(90, 7, f"Client: {cli_name}", 0, 1)
    pdf.cell(90, 7, f"Location: {loc}", 0, 1)
    pdf.ln(5)

    # 2. Key Assumptions
    pdf.set_fill_color(14, 47, 68)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, "2. Key Assumptions", 0, 1, 'L', 1)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    # Row 1: timing
    pdf.cell(60, 7, f"Start: {start_year} {start_q_str}", 0, 0)
    pdf.cell(60, 7, f"Term: {ppa_term_years} Years", 0, 1)

    # Row 2: tariffs
    pdf.cell(60, 7, f"Client Tariff: ${current_tariff:,.1f}/kWh", 0, 0)
    pdf.cell(60, 7, f"Discount Offered: {discount_rate*100:.1f}%", 0, 0)
    pdf.cell(60, 7, f"Year 1 PPA Price: ${ppa_price_year1_disp:,.2f}/kWh", 0, 1)

    # Row 3: energy & capex
    pdf.cell(60, 7, f"Energy: {initial_gen_mwh_annual:,.1f} MWh", 0, 0)
    pdf.cell(
        60, 7,
        f"CAPEX: {curr_sym}{capex_million_cop*inv_conv:,.1f} {currency_mode_local.split()[0]}",
        0, 0
    )
    pdf.cell(60, 7, f"Leverage: {debt_ratio*100:.0f}%", 0, 1)
    pdf.ln(5)

    # 3. Executive Summary
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

    # 4. FCF Overview (Chart)
    pdf.set_fill_color(14, 47, 68)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, "4. Free Cash Flow Overview", 0, 1, 'L', 1)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)
    try:
        fcf_img = make_fcf_chart_image(df_annual_dash_local, currency_mode_local)
        pdf.image(fcf_img, x=10, y=None, w=180)
    except Exception as e:
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 6, f"(Could not render FCF chart: {e})", 0, 1)
    pdf.ln(5)

    # 5. Simulation Matrix - IRR Sensitivity
    if sim_df_local is not None and not sim_df_local.empty:
        pdf.set_fill_color(14, 47, 68)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(
            0, 10,
            "5. Simulation Matrix - Equity IRR Sensitivity for Client Asset Buy-Back",
            0, 1, 'L', 1
        )
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
        try:
            sim_img = make_sim_heatmap_image(sim_df_local, T, currency_mode_local)
            if sim_img:
                pdf.image(sim_img, x=10, y=None, w=180)
        except Exception as e:
            pdf.set_font("Arial", '', 10)
            pdf.cell(0, 6, f"(Could not render sensitivity heatmap: {e})", 0, 1)
        pdf.ln(5)

        # 5a. Simulation Table (excerpt)
        pdf.set_fill_color(14, 47, 68)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 10, "5a. Simulation Table (Exit Year vs Asset Value)", 0, 1, 'L', 1)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
        pdf.set_font("Arial", size=9)

        sim_tbl = sim_df_local.copy()

        # Normalize column names regardless of language / history
        if "ExitYear" in sim_tbl.columns and "ExitValue" in sim_tbl.columns:
            pass
        elif T["s5_year"] in sim_tbl.columns and T["s5_val"] in sim_tbl.columns:
            sim_tbl = sim_tbl.rename(columns={
                T["s5_year"]: "ExitYear",
                T["s5_val"]: "ExitValue"
            })
        elif "Exit Year" in sim_tbl.columns and "Exit Value (M COP)" in sim_tbl.columns:
            sim_tbl = sim_tbl.rename(columns={
                "Exit Year": "ExitYear",
                "Exit Value (M COP)": "ExitValue"
            })
        else:
            year_col = next(
                (c for c in sim_tbl.columns if "Year" in c or "Año" in c),
                None
            )
            val_col = next(
                (c for c in sim_tbl.columns if c not in ("IRR", year_col)),
                None
            )
            if year_col and val_col:
                sim_tbl = sim_tbl.rename(columns={
                    year_col: "ExitYear",
                    val_col: "ExitValue"
                })
            else:
                return pdf.output(dest='S').encode('latin-1', 'replace')

        sim_tbl = sim_tbl.sort_values(["ExitYear", "ExitValue"])
        sim_tbl = sim_tbl[["ExitYear", "ExitValue", "IRR"]].head(25)

        headers_sim = ["Exit Year", "Exit Value (M COP)", "IRR %"]
        widths_sim = [25, 55, 25]

        pdf.set_fill_color(220, 220, 220)
        for w, h in zip(widths_sim, headers_sim):
            pdf.cell(w, 7, h, 1, 0, 'C', 1)
        pdf.ln()

        for _, row in sim_tbl.iterrows():
            pdf.cell(widths_sim[0], 6, f"{int(row['ExitYear'])}", 1, 0, 'C')
            pdf.cell(widths_sim[1], 6, f"{row['ExitValue']:,.1f}", 1, 0, 'R')
            pdf.cell(widths_sim[2], 6, f"{row['IRR']:,.1f}", 1, 0, 'R')
            pdf.ln()

        pdf.ln(5)

    # 6. Alternatives Matching Base IRR
    if close_df_local is not None and not close_df_local.empty:
        pdf.set_fill_color(14, 47, 68)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 10, "6. Alternatives with IRR Close to Base Case", 0, 1, 'L', 1)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
        pdf.set_font("Arial", size=9)

        close_pdf = close_df_local.head(10).copy()
        headers = ["Exit Year", "Exit Value (M COP)", "IRR %", "Delta IRR vs Base"]
        widths = [25, 55, 25, 30]
        pdf.set_fill_color(220, 220, 220)
        for w, h in zip(widths, headers):
            pdf.cell(w, 7, h, 1, 0, 'C', 1)
        pdf.ln()

        for _, row in close_pdf.iterrows():
            pdf.cell(widths[0], 6, f"{int(row['Exit Year'])}", 1, 0, 'C')
            pdf.cell(widths[1], 6, f"{row['Exit Value (M COP)']:,.1f}", 1, 0, 'R')
            pdf.cell(widths[2], 6, f"{row['IRR']:,.1f}", 1, 0, 'R')
            pdf.cell(widths[3], 6, f"{row['ΔIRR_vs_Base']:+.1f}", 1, 0, 'R')
            pdf.ln()

    return pdf.output(dest='S').encode('latin-1', 'replace')


# ------------------------------------------------------
# TOP KPIs & PDF BUTTON
# ------------------------------------------------------
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.subheader(f"📊 {currency_mode}")
with col_head2:
    sim_df_for_pdf = st.session_state.get("sim_df", None)
    close_df_for_pdf = st.session_state.get("sim_close_df", None)
    pdf_bytes = create_pdf(
        df_annual_dash,
        df_annual_dash,
        project_name,
        client_name,
        project_loc,
        symbol,
        currency_mode,
        fx_rate_current,
        sim_df_local=sim_df_for_pdf,
        close_df_local=close_df_for_pdf
    )

    # Use scenario name (if any) for the PDF file name
    project_label = st.session_state.get("active_project", "").strip()
    project_label = project_label.replace(" ", "_") or "Project"

    scen_label = st.session_state.get("scenario_name", "").strip()
    scen_label = scen_label.replace(" ", "_") or "memo"

    file_name = f"{project_label}__{scen_label}.pdf"


    st.download_button(
        label="📄 Download PDF Report",
        data=pdf_bytes,
        file_name=file_name,
        mime="application/pdf"
    )

    # --- Excel export (Pharos Model V2) ---
    excel_bytes = generate_excel_file()
    excel_file_name = f"{project_label}__{scen_label}.xlsx"

    st.download_button(
        label="📊 Download Excel Model",
        data=excel_bytes,
        file_name=excel_file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )



k1, k2, k3, k4 = st.columns(4)
k1.metric(T["kpi_eq"], f"{symbol}{equity_inv_disp:,.1f}")
start_p = current_tariff * (1 - discount_rate)
if "USD" in currency_mode:
    start_p /= fx_rate_current
k2.metric(T["kpi_tar"], f"${start_p:,.2f} /kWh")
k3.metric(T["kpi_irr"], f"{irr_levered:.1f}%")
k4.metric(T["kpi_npv"], f"{symbol}{npv_equity:,.1f}")

st.divider()

# Saved scenarios comparison (per project)
if scenarios_dict:
    st.markdown("### Saved Scenarios Comparison (current project)")
    df_scen = pd.DataFrame.from_dict(
        scenarios_dict,
        orient="index"
    )
    df_scen.index.name = "Scenario"
    df_scen.reset_index(inplace=True)

    cols_order = [
        "Scenario",
        "PPA_Years",
        "Equity_Investment",
        "IRR_Levered_%",
        "MOIC_x",
        "Exit_Method",
        "Exit_Year",
        "Exit_Value_M_COP",
        "PPA_Year1_$perkWh",
        "Client_Tariff_$perkWh",
    ]

    for col in cols_order:
        if col not in df_scen.columns:
            df_scen[col] = np.nan

    # Backward compatibility: if old Tariff_$perkWh exists, map to PPA_Year1
    if "Tariff_$perkWh" in df_scen.columns:
        df_scen["PPA_Year1_$perkWh"] = df_scen["PPA_Year1_$perkWh"].fillna(
            df_scen["Tariff_$perkWh"]
        )

    df_scen = df_scen[cols_order]

    st.dataframe(
        df_scen.style.format({
            "PPA_Years": "{:.0f}",
            "Equity_Investment": "{:,.1f}",
            "IRR_Levered_%": "{:,.1f}",
            "MOIC_x": "{:,.2f}",
            "Exit_Year": "{:.0f}",
            "Exit_Value_M_COP": "{:,.1f}",
            "PPA_Year1_$perkWh": "{:,.1f}",
            "Client_Tariff_$perkWh": "{:,.1f}",
        }),
        use_container_width=True
    )
else:
    st.markdown("_No scenarios saved yet for this project. Use **'Save current scenario'** above to store one._")

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"### {T['card_proj']}")
    st.metric("TIR", f"{irr_unlevered:.1f}%")
with c2:
    st.markdown(f"### {T['card_eq']}")
    st.metric(T["kpi_moic"], f"{moic_levered:.1f}x")
    st.caption(f"{T['lbl_lev']}: {debt_ratio * 100:.0f}%" if enable_debt else T["lbl_nodebt"])
with c3:
    st.markdown("### ⚖️ Leverage Boost")
    st.metric("Delta", f"{irr_levered - irr_unlevered:+.1f}%", delta_color="normal")

st.divider()

# Revenue proof
with st.expander(T["rev_proof"], expanded=False):
    st.write("Revenue Proof: **Generation (MWh) × Price ($/kWh) = Revenue (M)**")
    proof_df = df_annual_dash[["Calendar_Year", "Generation_MWh", "Revenue_Disp"]].copy()
    proof_df.columns = ["Year", T["col_gen"], T["col_rev"]]
    st.dataframe(
        proof_df.style.format({
            "Year": "{:.0f}",
            T["col_gen"]: "{:,.1f}",
            T["col_rev"]: "{:,.1f}"
        })
    )

# Tax diagnostics (levered)
with st.expander("Tax Base & Loss Carryforward (Levered view)", expanded=False):
    tax_view = df_full[[
        "Calendar_Year",
        "Quarter",
        "EBITDA_M_COP",
        "Interest_M_COP",
        "Depreciation_M_COP",
        "Tax_Base_Lev_PreBenefit_M_COP",
        "Capex_Tax_Benefit_M_COP",
        "Tax_Base_Lev_M_COP",
        "Tax_Base_Lev_Cum_M_COP",
        "Tax_M_COP",
        "Tax_Lev_Cum_M_COP"
    ]].copy()
    tax_view.rename(columns={
        "EBITDA_M_COP": "EBITDA",
        "Interest_M_COP": "Interest",
        "Depreciation_M_COP": "Depreciation",
        "Tax_Base_Lev_PreBenefit_M_COP": "Tax Base Pre-Benefit",
        "Capex_Tax_Benefit_M_COP": "CAPEX Benefit Used",
        "Tax_Base_Lev_M_COP": "Tax Base After Benefit",
        "Tax_Base_Lev_Cum_M_COP": "Tax Base Cumulative",
        "Tax_M_COP": "Tax (Quarter)",
        "Tax_Lev_Cum_M_COP": "Tax Cumulative"
    }, inplace=True)
    st.dataframe(
        tax_view.style.format({
            "EBITDA": "{:,.1f}",
            "Interest": "{:,.1f}",
            "Depreciation": "{:,.1f}",
            "Tax Base Pre-Benefit": "{:,.1f}",
            "CAPEX Benefit Used": "{:,.1f}",
            "Tax Base After Benefit": "{:,.1f}",
            "Tax Base Cumulative": "{:,.1f}",
            "Tax (Quarter)": "{:,.1f}",
            "Tax Cumulative": "{:,.1f}",
        }),
        use_container_width=True
    )

st.markdown(f"##### {T['chart_cf']}")
df_melt = df_annual_dash.melt(
    id_vars=["Calendar_Year"],
    value_vars=["UFCF_Disp", "LFCF_Disp"],
    var_name="Type",
    value_name="CashFlow"
)
base_chart = alt.Chart(df_melt).encode(
    x=alt.X('Type:N', title=None, axis=None),
    y=alt.Y('CashFlow:Q', title=f"Cash Flow ({currency_mode})")
)
bars = base_chart.mark_bar().encode(
    color=alt.Color('Type:N'),
    tooltip=['Calendar_Year', 'Type', 'CashFlow']
)
text = base_chart.mark_text(dy=-10).encode(
    text=alt.Text('CashFlow:Q', format='.1f')
)
chart = alt.layer(bars, text).properties(width=80).facet(
    column=alt.Column('Calendar_Year:O', title="Year",
                      header=alt.Header(labelAngle=0, labelAlign='center'))
)
st.altair_chart(chart, use_container_width=True)

st.markdown("---")
table_layout = st.radio("Table Layout",
                        ["Horizontal (Years as Columns)", "Vertical (Years as Rows)"],
                        horizontal=True)

st.markdown(f"### {T['tab_pl']}")
pnl_data = df_annual_full.copy()
pnl_data["EBIT_Disp"] = pnl_data["EBITDA_Disp"] - pnl_data["Depreciation_Disp"]
pnl_data["EBT_Disp"] = pnl_data["EBIT_Disp"] - pnl_data["Interest_Disp"]
pnl_data["Net_Income_Disp"] = pnl_data["EBT_Disp"] - pnl_data["Tax_Disp"]

pnl_view = pnl_data[[
    "Calendar_Year", "Revenue_Disp", "OPEX_Disp", "Gross_Disp",
    "SGA_Disp", "EBITDA_Disp", "Depreciation_Disp", "EBIT_Disp",
    "Interest_Disp", "EBT_Disp", "Tax_Disp", "Net_Income_Disp"
]].set_index("Calendar_Year")

if "Horizontal" in table_layout:
    pnl_view = pnl_view.T
    pnl_view.index = [
        "Revenue", "(-) OPEX", "(=) Gross Profit", "(-) SGA", "(=) EBITDA",
        "(-) Depreciation", "(=) EBIT", "(-) Interest",
        "(=) EBT", "(-) Taxes", "(=) Net Income"
    ]
    st.dataframe(pnl_view.style.format("{:,.1f}"))
else:
    st.dataframe(pnl_view.style.format("{:,.1f}"))

st.markdown(f"### {T['tab_full']}")
cf_cols = ["Generation_MWh", "Revenue_Disp", "OPEX_Disp",
           "EBITDA_Disp", "UFCF_Disp", "LFCF_Disp"]
cf_view = df_annual_full.set_index("Calendar_Year")[cf_cols]

if "Horizontal" in table_layout:
    cf_view = cf_view.T
    cf_view.index = ["Generation (MWh)", "Revenue", "(-) OPEX",
                     "(=) EBITDA", "Unlevered FCF", "Levered FCF"]
    st.dataframe(cf_view.style.format("{:,.1f}"))
else:
    st.dataframe(cf_view.style.format("{:,.1f}"))

# ------------------------------------------------------
# SIMULATION
# ------------------------------------------------------
st.markdown("---")
st.header(T["sim_title"])
with st.expander("Config", expanded=True):
    c_sim1, c_sim2 = st.columns(2)
    with c_sim1:
        sim_years = st.slider(T["s5_year"], 2, ppa_term_years, (5, 10))
    with c_sim2:
        base_val = int(final_exit_val_cop) if final_exit_val_cop > 0 else 100
        min_v = st.number_input(f"{T['sim_min']} (COP)",
                                value=max(10, base_val - 50),
                                step=10)
        max_v = st.number_input(f"{T['sim_max']} (COP)",
                                value=base_val + 50,
                                step=10)
        step_v = st.number_input(T["sim_step"], value=10, step=1)


def calculate_sim_irr(y_exit, v_exit_cop):
    exit_q = construction_quarters + (y_exit * 4)
    if exit_q > len(df_full):
        return 0
    df_slice = df_full.iloc[:exit_q].copy()
    last_r = df_slice.iloc[-1]
    gain_local = v_exit_cop - last_r["Book_Value_M_COP"]
    tax_local = gain_local * cap_gains_rate if gain_local > 0 else 0
    net_exit_cop = v_exit_cop - last_r["Debt_Balance_M_COP"] - tax_local
    df_slice.at[len(df_slice) - 1, "LFCF_M_COP"] += net_exit_cop
    return get_irr(df_slice["LFCF_M_COP"])


if st.button(T["sim_run"]):
    years_to_sim = list(range(sim_years[0], sim_years[1] + 1))
    vals_to_sim = list(range(int(min_v), int(max_v) + int(step_v), int(step_v)))
    sim_data = []
    for v in vals_to_sim:
        for y in years_to_sim:
            sim_data.append({
                "ExitYear": y,
                "ExitValue": v,
                "IRR": round(calculate_sim_irr(y, v), 1)
            })

    sim_df = pd.DataFrame(sim_data)

    heatmap = alt.Chart(sim_df).mark_rect().encode(
        x=alt.X('ExitValue:O', title=T["s5_val"]),
        y=alt.Y('ExitYear:O', title=T["s5_year"]),
        color=alt.Color(
            'IRR:Q',
            scale=alt.Scale(scheme='redyellowgreen'),
            title='IRR %'
        ),
        tooltip=['ExitYear', 'ExitValue', 'IRR']
    ).properties(title=T["sim_chart"])

    text_sim = heatmap.mark_text(
        baseline='middle'
    ).encode(
        text=alt.Text('IRR:Q', format='.1f'),
        color=alt.value('black')
    )

    st.altair_chart(heatmap + text_sim, use_container_width=True)

    # Sensitivity summary around base IRR
    target_irr = irr_levered
    lower_bound = target_irr * 0.9
    upper_bound = target_irr * 1.1

    close_df = sim_df[
        (sim_df["IRR"] >= lower_bound) &
        (sim_df["IRR"] <= upper_bound)
    ].copy()

    if not close_df.empty:
        close_df["ΔIRR_vs_Base"] = (close_df["IRR"] - target_irr).round(1)
        close_df = close_df.sort_values(
            by="ΔIRR_vs_Base",
            key=lambda s: s.abs()
        )
        # Rename to human-readable labels for display
        close_df = close_df.rename(columns={
            "ExitYear": "Exit Year",
            "ExitValue": "Exit Value (M COP)"
        })
        close_df = close_df[[
            "Exit Year", "Exit Value (M COP)", "IRR", "ΔIRR_vs_Base"
        ]].head(15)

        st.markdown(f"#### {T['sim_match_title']}")
        st.caption(
            f"Base case IRR: {target_irr:.1f}%. "
            f"Showing alternatives with IRR between {lower_bound:.1f}% and {upper_bound:.1f}%."
        )
        st.dataframe(
            close_df.style.format({
                "Exit Year": "{:.0f}",
                "Exit Value (M COP)": "{:,.1f}",
                "IRR": "{:.1f}",
                "ΔIRR_vs_Base": "{:+.1f}"
            }),
            use_container_width=True
        )
    else:
        close_df = None
        st.info(
            f"No simulation points found with IRR within ±10% of base case ({target_irr:.1f}%). "
            f"Try widening the year/value ranges."
        )

    # Store for PDF
    st.session_state["sim_df"] = sim_df
    st.session_state["sim_close_df"] = close_df






