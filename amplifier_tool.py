import streamlit as st
import schemdraw
import schemdraw.elements as elm
import matplotlib.pyplot as plt

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="CMOS Amplifier Designer", layout="wide")
st.title("Interactive CMOS Amplifier Designer (Multi-Stage)")

# --- 2. SIDEBAR PARAMETERS ---
st.sidebar.header("Global Settings")
zoom = st.sidebar.slider("Schematic Zoom Level", 0.5, 3.0, 1.0, 0.1)

# --- HELPER FUNCTION FOR RESISTOR NETWORKS ---
def calculate_network(name, default_val):
    """Creates sidebar UI for a resistor network (Series + Parallel)"""
    st.sidebar.markdown(f"**{name} Network**")
    enable = st.sidebar.checkbox(f"Enable {name}?", value=True, key=f"{name}_en")
    
    r_eq = 0.0
    if enable:
        # Series Resistor
        r_series = st.sidebar.number_input(f"{name} Series (Ω)", value=default_val, step=100.0, key=f"{name}_s")
        r_eq = r_series
        
        # Parallel Resistor
        add_parallel = st.sidebar.checkbox(f"Add Parallel to {name}?", key=f"{name}_pen")
        if add_parallel:
            r_par = st.sidebar.number_input(f"{name} Parallel (Ω)", value=default_val, step=100.0, key=f"{name}_p")
            if (r_series + r_par) > 0:
                r_eq = (r_series * r_par) / (r_series + r_par)
        
        st.sidebar.caption(f"Total {name} Resistance: {r_eq:.1f} Ω")
    return enable, r_eq

# --- STAGE 1 CONTROLS ---
st.sidebar.divider()
st.sidebar.header("Stage 1 Parameters")
s1_rg_en, s1_rg = calculate_network("Stage 1 Gate", 10000.0)
s1_rd_en, s1_rd = calculate_network("Stage 1 Drain", 5000.0)
s1_rs_en, s1_rs = calculate_network("Stage 1 Source", 1000.0)

# Gate Divider (Parallel Gate Resistor to Ground)
s1_add_gate_div = st.sidebar.checkbox("Add Stage 1 Gate Divider (Parallel to GND)?")
s1_rg_div = 0
if s1_add_gate_div:
    s1_rg_div = st.sidebar.number_input("Stage 1 Gate Divider (Ω)", value=20000.0, step=1000.0)

# --- STAGE 2 CONTROLS ---
st.sidebar.divider()
enable_stage_2 = st.sidebar.checkbox("Enable Stage 2 (Cascade)?", value=False)

s2_rg = 0; s2_rd = 0; s2_rs = 0 
interstage_type = "None"

if enable_stage_2:
    st.sidebar.header("Interstage Coupling")
    interstage_type = st.sidebar.selectbox("Coupling Type", ["Direct Wire", "Resistor", "Capacitor", "Series R+C"])
    
    st.sidebar.header("Stage 2 Parameters")
    # We assume Stage 2 is driven by Stage 1, so Gate Resistor is usually just bias
    s2_add_bias = st.sidebar.checkbox("Add Stage 2 Gate Bias Resistor?", value=True)
    if s2_add_bias:
        s2_rg = st.sidebar.number_input("Stage 2 Gate Bias (Ω)", value=10000.0, step=100.0)
    
    s2_rd_en, s2_rd = calculate_network("Stage 2 Drain", 5000.0)
    s2_rs_en, s2_rs = calculate_network("Stage 2 Source", 500.0)

# --- 3. MATH ENGINE (Simplified Estimates) ---
gm = 0.005 # Transconductance estimate
# Stage 1 Gain
av1 = 0
if s1_rd > 0:
    # Basic CS Gain: -gm * (Rd || ro), ignoring ro for now
    # If source degeneration (Rs > 0), Av = -Rd / (1/gm + Rs)
    denom = (1/gm) + s1_rs
    av1 = -s1_rd / denom

# Stage 2 Gain
av2 = 0
if enable_stage_2 and s2_rd > 0:
    denom2 = (1/gm) + s2_rs
    av2 = -s2_rd / denom2

total_gain = av1 * (av2 if enable_stage_2 else 1)

# --- 4. DRAWING ENGINE ---
st.subheader("Circuit Schematic")

d = schemdraw.Drawing()
d.config(unit=2.0, fontsize=12) # Adjusted base unit

# --- DRAW STAGE 1 ---
# 1. Input Source (Flipped orientation as requested)
# We draw the ground first, then go UP to the source
d.add(elm.Ground())
d.add(elm.SourceSin().up().label('$V_{in}$'))

# 2. Gate Resistor (Series)
d.add(elm.Dot())
d.push() # Save node after source
if s1_rg_en:
    d.add(elm.Resistor().right().label(f'$R_{{G1}}$\n{s1_rg:.0f}Ω'))
else:
    d.add(elm.Line().right())

# 3. Gate Divider (Parallel to Ground)
gate_node = d.here # Current position is the Gate of M1
if s1_add_gate_div:
    d.push()
    d.add(elm.Resistor().down().label(f'$R_{{div}}$\n{s1_rg_div:.0f}Ω'))
    d.add(elm.Ground())
    d.pop()

# 4. MOSFET M1
# We anchor the Gate to the current position
Q1 = d.add(elm.NFet().anchor('gate').label('$M_1$'))

# *** FIX: Changed .text() to .label() here ***
d.add(elm.Label().at(Q1.gate).label('G', loc='left', color='blue'))
d.add(elm.Label().at(Q1.drain).label('D', loc='top', color='blue'))
d.add(elm.Label().at(Q1.source).label('S', loc='bottom', color='blue'))

# 5. Stage 1 Source Network
d.push()
d.move_from(Q1.source, dx=0, dy=0)
if s1_rs_en:
    d.add(elm.Resistor().down().label(f'$R_{{S1}}$\n{s1_rs:.0f}Ω'))
else:
    d.add(elm.Line().down())
d.add(elm.Ground())
d.pop()

# 6. Stage 1 Drain Network
d.move_from(Q1.drain, dx=0, dy=0)
if s1_rd_en:
    d.add(elm.Resistor().up().label(f'$R_{{D1}}$\n{s1_rd:.0f}Ω'))
else:
    d.add(elm.Line().up())
d.add(elm.Vdd().label('$V_{DD}$'))

# 7. Probe Vout1
d.add(elm.Line().right().at(Q1.drain).length(1))
d.add(elm.Dot(open=True))
d.add(elm.Label().label('$V_{out1}$').loc('right'))
vout1_node = d.here # Save this spot to connect Stage 2

# --- DRAW STAGE 2 (If Enabled) ---
if enable_stage_2:
    # Move to Vout1 node
    d.move_from(vout1_node, dx=0, dy=0)
    
    # Interstage Coupling
    if interstage_type == "Resistor":
        d.add(elm.Resistor().right().label('R_{c}'))
    elif interstage_type == "Capacitor":
        d.add(elm.Capacitor().right().label('C_{c}'))
    elif interstage_type == "Series R+C":
        d.add(elm.Resistor().right())
        d.add(elm.Capacitor().right())
    else: # Direct Wire
        d.add(elm.Line().right())
        
    # Stage 2 Gate Bias (to Ground)
    if s2_rg > 0:
        d.push()
        d.add(elm.Resistor().down().label(f'{s2_rg}Ω'))
        d.add(elm.Ground())
        d.pop()
        
    # MOSFET M2
    Q2 = d.add(elm.NFet().anchor('gate').label('$M_2$'))
    
    # *** FIX: Changed .text() to .label() here ***
    d.add(elm.Label().at(Q2.gate).label('G', loc='left', color='blue'))
    d.add(elm.Label().at(Q2.drain).label('D', loc='top', color='blue'))
    d.add(elm.Label().at(Q2.source).label('S', loc='bottom', color='blue'))
    
    # Stage 2 Source
    d.push()
    d.move_from(Q2.source, dx=0, dy=0)
    if s2_rs_en:
        d.add(elm.Resistor().down().label(f'$R_{{S2}}$\n{s2_rs:.0f}Ω'))
    else:
        d.add(elm.Line().down())
    d.add(elm.Ground())
    d.pop()
    
    # Stage 2 Drain
    d.move_from(Q2.drain, dx=0, dy=0)
    if s2_rd_en:
        d.add(elm.Resistor().up().label(f'$R_{{D2}}$\n{s2_rd:.0f}Ω'))
    else:
        d.add(elm.Line().up())
    d.add(elm.Vdd().label('$V_{DD}$'))
    
    # Probe Vout2
    d.add(elm.Line().right().at(Q2.drain).length(1))
    d.add(elm.Dot(open=True))
    d.add(elm.Label().label('$V_{out2}$').loc('right'))

# --- RENDER ---
schem_fig = d.draw()

# Apply Zoom (Resize the Matplotlib Figure)
if schem_fig.fig:
    # Default size is usually around [6.4, 4.8]. We multiply by zoom factor.
    w, h = schem_fig.fig.get_size_inches()
    schem_fig.fig.set_size_inches(w * zoom, h * zoom)
    st.pyplot(schem_fig.fig)
else:
    # Fallback if fig wrapper changes
    st.pyplot(schem_fig)

# --- RESULTS ---
st.divider()
c1, c2, c3 = st.columns(3)
c1.metric("Stage 1 Gain", f"{av1:.2f} V/V
