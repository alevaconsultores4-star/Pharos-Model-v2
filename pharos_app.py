import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import altair as alt

# --- PASSWORD PROTECTION ---
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == "pharos2025": # <--- CHANGE PASSWORD HERE
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Enter Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect, show input + error.
        st.text_input(
            "Enter Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True

if not check_password():
    st.stop()

# --- MAIN APP START ---
st.set_page_config(page_title="Pharos Investor Model (Secure)", layout="wide")
st.title("🦅 Pharos Capital: Investor Dashboard")

# ==========================================
# 0. GLOBAL SETTINGS (CURRENCY)
# ==========================================
st.sidebar.header("0. Currency & FX")
currency_mode = st.sidebar.radio("Display Currency", ["COP (Millions)", "USD (Thousands)"], horizontal=True)

with st.sidebar.expander("FX & Macro Assumptions", expanded=False):
    fx_rate_current = st.number_input("Current FX Rate (COP/USD)", value=4100.0, step=10.0, format="%.1f")
    us_inflation_annual = st.number_input("US Inflation (Annual %)", value=2.5, step=0.1, format="%.1f") / 100

# ==========================================
# 1. PPA & REVENUE
# ==========================================
st.sidebar.header("1. PPA & Revenue")
with st.sidebar.expander("Contract Details", expanded=False):
    ppa_term_years = st.slider("PPA Duration (Years)", 5, 20, 10)
    current_tariff = st.number_input("Current Tariff ($/kWh)", value=881.6, format="%.1f")
    utility_inflation_annual = st.number_input("Utility Inflation (Annual %)", value=5.0, format="%.1f") / 100
    discount_rate = st.number_input("Discount to Client (%)", value=25.0, format="%.1f") / 100
    
    link_to_inflation = st.checkbox("Index PPA Price to Inflation?", value=False)
    if link_to_inflation:
        pcp_escalator_annual = utility_inflation_annual
        st.info(f"🔒 Escalator locked to Inflation ({utility_inflation_annual*100:.1f}%)")
    else:
        pcp_escalator_annual = st.number_input("PPA Escalator (Annual %)", value=3.5, format="%.1f") / 100
    
    st.markdown("---")
    st.caption("Technical Specs")
    num_modules = st.number_input("Modules", value=45)
    module_power_w = st.number_input("Module Power (W)", value=650)
    system_size_kwp = (num_modules * module_power_w) / 1000
    
    initial_gen_mwh_annual = system_size_kwp * (44.86 / 29.25)
    st.info(f"⚡ **Contracted Energy:** {initial_gen_mwh_annual:.1f} MWh/yr")
    
    degradation_annual = st.number_input("Degradation (Annual %)", value=0.6, format="%.1f") / 100

# ==========================================
# 2. COSTS & CONSTRUCTION
# ==========================================
st.sidebar.header("2. Costs & Construction")
with st.sidebar.expander("CAPEX, Construction & OPEX", expanded=False):
    construction_quarters = st.slider("Construction Period (Quarters)", 0, 8, 2)
    capex_million_cop = st.number_input("Total CAPEX (M COP)", value=120.0, format="%.1f")
    opex_million_cop_annual = st.number_input("Annual OPEX (M COP/yr)", value=4.0, format="%.1f")
    opex_inflation_annual = st.number_input("OPEX Inflation (Annual %)", value=5.0, format="%.1f") / 100
    sga_percent = st.number_input("SGA (% of Gross Profit)", value=10.0, format="%.1f") / 100

# ==========================================
# 3. TAX & DEPRECIATION
# ==========================================
st.sidebar.header("3. Tax & Depreciation")
with st.sidebar.expander("Fiscal Regime", expanded=False):
    tax_rate = st.number_input("Corporate Income Tax (%)", value=35.0, format="%.1f") / 100
    cap_gains_rate = st.number_input("Capital Gains Tax (%)", value=10.0, format="%.1f") / 100
    depreciation_years = st.slider("Depreciation Term (Years)", 3, 25, 5)

# ==========================================
# 4. FINANCING
# ==========================================
st.sidebar.header("4. Financing")
with st.sidebar.expander("Debt Structure", expanded=True):
    enable_debt = st.checkbox("Include Debt?", value=True)
    if enable_debt:
        debt_ratio = st.slider("Debt Ratio (%)", 0, 100, 70) / 100
        interest_rate_annual = st.number_input("Interest Rate (Annual %)", value=12.1, format="%.1f") / 100
        loan_tenor_years = st.number_input("Loan Tenor (Years)", value=9)
        structuring_fee_pct = st.number_input("Structuring Fee (%)", value=2.0, format="%.1f") / 100
        grace_period_quarters = st.number_input("Grace Period (Quarters)", value=construction_quarters)
    else:
        debt_ratio = 0.0
        interest_rate_annual = 0.0
        loan_tenor_years = 0
        structuring_fee_pct = 0.0
        grace_period_quarters = 0

# ==========================================
# 5. DASHBOARD SCENARIO
# ==========================================
st.sidebar.header("5. Dashboard Scenario")
with st.sidebar.expander("Scenario & Valuation", expanded=True):
    dash_exit_strategy = st.radio("Exit Method", ["Fixed Asset Value", "EBITDA Multiple"])
    dash_exit_year = st.slider("Exit Year", 1, ppa_term_years, ppa_term_years)

    if dash_exit_strategy == "Fixed Asset Value":
        dash_exit_val_cop = st.number_input(f"Asset Sale Value (M COP)", value=10.0, format="%.1f")
        dash_exit_mult = 0
    else:
        dash_exit_mult = st.number_input("Valuation Multiple (x EBITDA)", value=7.0, step=0.5, format="%.1f")
        dash_exit_val_cop = 0
    
    st.markdown("---")
    investor_disc_rate = st.number_input("Investor Discount Rate (Ke %)", value=12.0, step=0.5, format="%.1f") / 100

# --- THE ENGINE ---
full_quarters = construction_quarters + (ppa_term_years * 4)
quarters_range = list(range(1, full_quarters + 1))

if enable_debt:
    structuring_fee = (capex_million_cop * debt_ratio) * structuring_fee_pct
    total_debt_principal = capex_million_cop * debt_ratio
    interest_rate_quarterly = interest_rate_annual / 4
    loan_tenor_quarters = loan_tenor_years * 4
    amort_quarters = loan_tenor_quarters - grace_period_quarters
    if amort_quarters > 0:
        quarterly_debt_pmt = -npf.pmt(interest_rate_quarterly, amort_quarters, total_debt_principal)
    else:
        quarterly_debt_pmt = 0
else:
    structuring_fee = 0
    total_debt_principal = 0
    interest_rate_quarterly = 0
    quarterly_debt_pmt = 0

equity_investment_levered_cop = (capex_million_cop + structuring_fee) - total_debt_principal
equity_investment_unlevered_cop = capex_million_cop

# Lists
q_list, gy_list = [], []
gen_list, price_list, rev_list = [], [], []
ebitda_list, ufcf_list, lfcf_list = [], [], []
debt_bal_list, book_val_list = [], []
fx_rate_list = []

debt_balance = total_debt_principal
accumulated_dep = 0

for q in quarters_range:
    # 0. FX Forecast (PPP)
    t_years = (q - 1) / 4
    fx_rate_q = fx_rate_current * ((1 + utility_inflation_annual) / (1 + us_inflation_annual)) ** t_years
    
    if q <= construction_quarters:
        phase = "Construction"
        op_year = 0
        q_op_index = 0
    else:
        phase = "Operation"
        q_op_index = q - construction_quarters
        op_year = (q_op_index - 1) // 4 + 1

    global_year = (q - 1) // 4 + 1 
    
    # 1. Operations (COP)
    if phase == "Operation":
        inf_factor = (1 + utility_inflation_annual) ** ((q_op_index - 1) / 4)
        esc_factor = (1 + pcp_escalator_annual) ** ((q_op_index - 1) / 4)
        deg_factor = (1 - degradation_annual) ** ((q_op_index - 1) / 4)
        opex_fac = (1 + opex_inflation_annual) ** ((q_op_index - 1) / 4)

        u_price = current_tariff * inf_factor
        p_price_start = current_tariff * (1 - discount_rate)
        p_price = p_price_start * esc_factor
        
        gen_quarterly = (initial_gen_mwh_annual / 4) * deg_factor
        rev = (gen_quarterly * p_price) / 1000
        
        opex = (opex_million_cop_annual / 4) * opex_fac
        gross = rev - opex
        ebitda = gross - (gross * sga_percent)
        
        dep = (capex_million_cop / depreciation_years) / 4 if op_year <= depreciation_years else 0
    else:
        p_price = 0
        gen_quarterly = 0
        rev, ebitda, dep = 0, 0, 0

    # 2. Capex (COP)
    if phase == "Construction" and construction_quarters > 0:
        capex_unlevered = capex_million_cop / construction_quarters
        capex_levered = equity_investment_levered_cop / construction_quarters
    else:
        capex_unlevered, capex_levered = 0, 0

    # 3. Debt Service (COP)
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

    # 4. Tax (COP)
    taxable_unlevered = ebitda - dep
    tax_unlevered = taxable_unlevered * tax_rate if taxable_unlevered > 0 else 0
    
    taxable_levered = ebitda - interest - dep
    tax_levered = taxable_levered * tax_rate if taxable_levered > 0 else 0

    # 5. Book Value (COP)
    accumulated_dep += dep
    book_val = max(0, capex_million_cop - accumulated_dep)

    # 6. Flows (COP)
    ufcf_op = ebitda - tax_unlevered - capex_unlevered
    lfcf_op = ebitda - tax_levered - interest - principal - capex_levered

    q_list.append(q)
    gy_list.append(global_year)
    gen_list.append(gen_quarterly)
    price_list.append(p_price)
    rev_list.append(rev)
    ebitda_list.append(ebitda)
    ufcf_list.append(ufcf_op)
    lfcf_list.append(lfcf_op)
    debt_bal_list.append(debt_balance)
    book_val_list.append(book_val)
    fx_rate_list.append(fx_rate_q)

df_full = pd.DataFrame({
    "Quarter": q_list,
    "Global_Year": gy_list,
    "FX_Rate": fx_rate_list,
    "Generation_MWh": gen_list,
    "Price_kWh": price_list,
    "Revenue_M_COP": rev_list,
    "EBITDA_M_COP": ebitda_list,
    "UFCF_M_COP": ufcf_list,
    "LFCF_M_COP": lfcf_list,
    "Debt_Balance_M_COP": debt_bal_list,
    "Book_Value_M_COP": book_val_list
})

# --- CURRENCY CONVERSION ---
conversion_factor = 1000 / df_full["FX_Rate"] if "USD" in currency_mode else 1

df_full["Revenue_Disp"] = df_full["Revenue_M_COP"] * conversion_factor
df_full["EBITDA_Disp"] = df_full["EBITDA_M_COP"] * conversion_factor
df_full["UFCF_Disp"] = df_full["UFCF_M_COP"] * conversion_factor
df_full["LFCF_Disp"] = df_full["LFCF_M_COP"] * conversion_factor
df_full["Debt_Disp"] = df_full["Debt_Balance_M_COP"] * conversion_factor
df_full["Book_Disp"] = df_full["Book_Value_M_COP"] * conversion_factor

# --- DASHBOARD LOGIC ---
if dash_exit_strategy == "Fixed Asset Value":
    final_exit_val_cop = dash_exit_val_cop
else:
    exit_q_idx = construction_quarters + (dash_exit_year * 4) - 1
    start_idx = max(0, exit_q_idx - 3)
    annual_ebitda = df_full.iloc[start_idx : exit_q_idx+1]["EBITDA_M_COP"].sum()
    final_exit_val_cop = annual_ebitda * dash_exit_mult

dash_exit_q = construction_quarters + (dash_exit_year * 4)
df_dash = df_full.iloc[:dash_exit_q].copy()

# Exit Logic (COP)
last_idx = len(df_dash) - 1
book_v_final = df_dash.iloc[last_idx]["Book_Value_M_COP"]
debt_b_final = df_dash.iloc[last_idx]["Debt_Balance_M_COP"]
gain = final_exit_val_cop - book_v_final
cg_tax = gain * cap_gains_rate if gain > 0 else 0

exit_inflow_unlevered_cop = final_exit_val_cop - cg_tax
exit_inflow_levered_cop = final_exit_val_cop - debt_b_final - cg_tax

final_fx = df_dash.iloc[last_idx]["FX_Rate"]
conv_factor_final = 1000 / final_fx if "USD" in currency_mode else 1

exit_inflow_unlevered_disp = exit_inflow_unlevered_cop * conv_factor_final
exit_inflow_levered_disp = exit_inflow_levered_cop * conv_factor_final

df_dash.at[last_idx, "UFCF_Disp"] += exit_inflow_unlevered_disp
df_dash.at[last_idx, "LFCF_Disp"] += exit_inflow_levered_disp

# Annual Aggregation
df_annual = df_dash.groupby("Global_Year")[["Generation_MWh", "Revenue_Disp", "EBITDA_Disp", "UFCF_Disp", "LFCF_Disp"]].sum().reset_index()
df_annual["Implied_Price_kWh"] = (df_dash.groupby("Global_Year")["Revenue_M_COP"].sum() * 1000) / df_annual["Generation_MWh"]
if "USD" in currency_mode:
    df_annual["Implied_Price_Unit"] = (df_annual["Revenue_Disp"] * 1000) / (df_annual["Generation_MWh"] * 1000) 
else:
    df_annual["Implied_Price_Unit"] = df_annual["Implied_Price_kWh"].fillna(0)

# Metrics
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

# --- DISPLAY ---
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.subheader(f"📊 Dashboard ({currency_mode})")
with col_head2:
    csv_data = df_annual.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Excel", csv_data, "pharos_cf.csv", "text/csv")

# HEADLINE METRICS
k1, k2, k3, k4 = st.columns(4)
symbol = "$" if "USD" in currency_mode else ""
k1.metric("Equity Investment", f"{symbol}{equity_inv_disp:,.1f}")
k2.metric("Year 1 Price", f"${df_annual.iloc[0]['Implied_Price_Unit']:.2f} /kWh")
k3.metric("Equity IRR", f"{irr_levered:.1f}%")
k4.metric("Equity NPV", f"{symbol}{npv_equity:,.1f}")

st.divider()

# COMPARISON CARDS
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("### 🏗️ Project (Unlevered)")
    st.metric("Project IRR", f"{irr_unlevered:.1f}%")
    st.caption("100% Equity")

with c2:
    st.markdown("### 🦅 Equity (Levered)")
    st.metric("MOIC", f"{moic_levered:.1f}x")
    if enable_debt:
        st.caption(f"Leverage: {debt_ratio*100:.0f}%")
    else:
        st.caption("Debt Disabled")

with c3:
    st.markdown("### ⚖️ Leverage Boost")
    st.metric("Delta", f"{irr_levered - irr_unlevered:+.1f}%", delta_color="normal")

st.divider()

# REVENUE PROOF
with st.expander("🔎 Revenue Calculation Detail", expanded=True):
    st.write("Revenue Proof")
    revenue_proof = df_annual[["Global_Year", "Generation_MWh", "Implied_Price_Unit", "Revenue_Disp"]].copy()
    revenue_proof = revenue_proof[revenue_proof["Generation_MWh"] > 0]
    
    st.dataframe(revenue_proof.style.format({
        "Global_Year": "{:.0f}",
        "Generation_MWh": "{:,.1f}",
        "Implied_Price_Unit": "${:,.2f}",
        "Revenue_Disp": "{:,.1f}"
    }))

st.markdown("##### 💰 Cash Flow Comparison")
df_melt = df_annual.melt(id_vars=["Global_Year"], value_vars=["UFCF_Disp", "LFCF_Disp"], var_name="Type", value_name="CashFlow")

base = alt.Chart(df_melt).encode(
    x=alt.X('Global_Year:O', title="Year"),
    y=alt.Y('CashFlow:Q', title=f"Net Cash Flow ({currency_mode})")
)

text = base.mark_text(dy=-10).encode(
    text=alt.Text('CashFlow:Q', format=',.1f'),
    color=alt.value('black')
)

bars = base.mark_bar().encode(
    color=alt.Color('Type', scale=alt.Scale(domain=['UFCF_Disp', 'LFCF_Disp'], range=['#808080', '#009355'])),
    tooltip=['Global_Year', 'CashFlow']
)

# FIXED CHART: Use single-level layering if faceting is tricky, or just side-by-side
# Simplest fix for the error: Group bars side-by-side instead of faceting, which is clearer
combined = alt.Chart(df_melt).mark_bar().encode(
    x=alt.X('Type:N', title=None, axis=None),
    y=alt.Y('CashFlow:Q', title=f"Cash Flow ({currency_mode})"),
