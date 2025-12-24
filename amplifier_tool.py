import streamlit as st
import schemdraw
import schemdraw.elements as elm
import matplotlib.pyplot as plt
import math

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="CMOS Amplifier Designer", layout="wide")
st.title("Interactive CMOS Amplifier Designer (Multi-Stage)")

# --- 2. SIDEBAR PARAMETERS ---
st.sidebar.header("Global Settings")
# Changed Zoom: Now controls 'unit' directly. 
# Range 1.0 to 5.0. Default 2.5.
zoom = st.sidebar.slider("Schematic Scale (Zoom)", 1.0, 5.0, 2.5, 0.25)

# --- HELPER: CALCULATE VALUES ---
def calculate_network(name, default_val):
    """Creates sidebar UI for a resistor network and calculates equivalent R."""
    st.sidebar.markdown(f"**{name} Network**")
    # Removed question mark
    enable = st.sidebar.checkbox(f"Enable {name}", value=True, key=f"{name}_en")
    
    r_eq = 0.0
    r_series = 0.0
    r_par = 0.0
    is_parallel = False
    
    if enable:
        r_series = st.sidebar.number_input(f"{name} Series (Ω)", value=default_val, step=100.0, key=f"{name}_s")
        r_eq = r_series
        
        # Removed question mark
        is_parallel = st.sidebar.checkbox(f"Add Parallel to {name}", key=f"{name}_pen")
        if is_parallel:
            r_par = st.sidebar.number_input(f"{name} Parallel (Ω)", value=default_val, step=100.0, key=f"{name}_p")
            if (r_series + r_par) > 0:
                r_eq = (r_series * r_par) / (r_series + r_par)
        
        # Show total calculated value in sidebar
        st.sidebar.caption(f"Total {name} Resistance: {r_eq:.1f} Ω")
        
    return enable, r_eq, r_series, r_par, is_parallel

# --- HELPER: DRAW COMPONENTS ---
def draw_network_components(d, enable, is_parallel, r_series, r_par, label_prefix, direction="up"):
    """
    Draws either a wire, a single resistor, or a parallel resistor pair 
    based on the configuration.
    """
    if not enable:
        # Draw a short circuit wire
        if direction == "up": d.add(elm.Line().up())
        elif direction == "down": d.add(elm.Line().down())
        elif direction == "right": d.add(elm.Line().right())
        return

    if not is_parallel:
        # Draw Single Resistor
        label = f'$R_{{{label_prefix}}}$\n{r_series:.0f}Ω'
        if direction == "up": d.add(elm.Resistor().up().label(label))
        elif direction == "down": d.add(elm.Resistor().down().label(label))
        elif direction == "right": d.add(elm.Resistor().right().label(label))
    else:
        # Draw Parallel Configuration
        # 1. Split path
        d.push()
        
        # Branch A (Left or Top)
        if direction == "up" or direction == "down":
            d.add(elm.Line().left(1.0))
            if direction == "up": d.add(elm.Resistor().up().label(f'{r_series:.0f}Ω'))
            else: d.add(elm.Resistor().down().label(f'{r_series:.0f}Ω'))
            d.add(elm.Line().right(1.0))
            d.pop() # Back to start
            
            # Branch B (Right or Bottom)
            d.add(elm.Line().right(1.0))
            if direction == "up": d.add(elm.Resistor().up().label(f'{r_par:.0f}Ω'))
            else: d.add(elm.Resistor().down().label(f'{r_par:.0f}Ω'))
            d.add(elm.Line().left(1.0))
            
        elif direction == "right":
            d.add(elm.Line().up(1.0))
            d.add(elm.Resistor().right().label(f'{r_series:.0f}Ω'))
            d.add(elm.Line().down(1.0))
            d.pop()
            
            d.add(elm.Line().down(1.0))
            d.add(elm.Resistor().right().label(f'{r_par:.0f}Ω'))
            d.add(elm.Line().up(1.0))

# --- STAGE 1 INPUTS ---
st.sidebar.divider()
st.sidebar.header("Stage 1 Parameters")
# We unpack all 5 return values now
s1_rg_en, s1_rg_total, s1_rg_s, s1_rg_p, s1_rg_is_par = calculate_network("Stage 1 Gate", 10000.0)
s1_rd_en, s1_rd_total, s1_rd_s, s1_rd_p, s1_rd_is_par = calculate_network("Stage 1 Drain", 5000.0)
s1_rs_en, s1_rs_total, s1_rs_s, s1_rs_p, s1_rs_is_par = calculate_network("Stage 1 Source", 1000.0)

# Gate Divider
s1_add_gate_div = st.sidebar.checkbox("Add Stage 1 Gate Divider (Parallel to GND)")
s1_rg_div = 0
if s1_add_gate_div:
    s1_rg_div = st.sidebar.number_input("Stage 1 Gate Divider (Ω)", value=20000.0, step=1000.0)

# --- STAGE 2 INPUTS ---
st.sidebar.divider()
enable_stage_2 = st.sidebar.checkbox("Enable Stage 2 (Cascade)", value=False)

s2_rg_total = 0; s2_rd_total = 0; s2_rs_total = 0 
interstage_type = "None"

if enable_stage_2:
    st.sidebar.header("Interstage Coupling")
    interstage_type = st.sidebar.selectbox("Coupling Type", ["Direct Wire", "Resistor", "Capacitor", "Series R+C"])
    
    st.sidebar.header("Stage 2 Parameters")
    s2_add_bias = st.sidebar.checkbox("Add Stage 2 Gate Bias Resistor", value=True)
    if s2_add_bias:
        s2_rg_total = st.sidebar.number_input("Stage 2 Gate Bias (Ω)", value=10000.0, step=100.0)
    
    s2_rd_en, s2_rd_total, s2_rd_s, s2_rd_p, s2_rd_is_par = calculate_network("Stage 2 Drain", 5000.0)
    s2_rs_en, s2_rs_total, s2_rs_s, s2_rs_p, s2_rs_is_par = calculate_network("Stage 2 Source", 500.0)

# --- 3. MATH ENGINE ---
gm = 0.005 
av1 = 0
if s1_rd_total > 0:
    denom = (1/gm) + s1_rs_total
    av1 = -s1_rd_total / denom

av2 = 0
if enable_stage_2 and s2_rd_total > 0:
    denom2 = (1/gm) + s2_rs_total
    av2 = -s2_rd_total / denom2

total_gain = av1 * (av2 if enable_stage_2 else 1)

# --- 4. DRAWING ENGINE ---
st.subheader("Circuit Schematic")

d = schemdraw.Drawing()
# USE SLIDER VALUE FOR UNIT SIZE
d.config(unit=zoom, fontsize=12)

# --- DRAW STAGE 1 ---
# Ground and Source
d.add(elm.Ground())
d.add(elm.SourceSin().up().label('$V_{in}$'))

# Gate Resistor Network
d.add(elm.Dot())
d.push()
# Use Helper to draw single or parallel resistors
draw_network_components(d, s1_rg_en, s1_rg_is_par, s1_rg_s, s1_rg_p, "G1", direction="right")

# Gate Divider (Parallel to Ground)
if s1_add_gate_div:
    d.push()
    d.add(elm.Resistor().down().label(f'$R_{{div}}$\n{s1_rg_div:.0f}Ω'))
    d.add(elm.Ground())
    d.pop()

# MOSFET M1 - FLIPPED (Gate on Right)
# Note: When flipped, Source/Drain positions might invert depending on library version.
# Standard: Source is 'bottom' of the symbol.
Q1 = d.add(elm.NFet(flip=True).anchor('gate').label('$M_1$'))

# Labels (Adjusted for flip)
d.add(elm.Label().at(Q1.gate).label('G', loc='right', color='blue')) # Gate is now on right
d.add(elm.Label().at(Q1.drain).label('D', loc='top', color='blue'))
d.add(elm.Label().at(Q1.source).label('S', loc='bottom', color='blue'))

# Stage 1 Source Network
d.push()
d.move_from(Q1.source, dx=0, dy=0)
draw_network_components(d, s1_rs_en, s1_rs_is_par, s1_rs_s, s1_rs_p, "S1", direction="down")
d.add(elm.Ground())
d.pop()

# Stage 1 Drain Network
d.move_from(Q1.drain, dx=0, dy=0)
draw_network_components(d, s1_rd_en, s1_rd_is_par, s1_rd_s, s1_rd_p, "D1", direction="up")
d.add(elm.Vdd().label('$V_{DD}$'))

# Probe Vout1
d.add(elm.Line().left().at(Q1.drain).length(1)) # Moved to LEFT because mosfet is flipped
d.add(elm.Dot(open=True))
d.add(elm.Label().label('$V_{out1}$', loc='left'))
vout1_node = d.here 

# --- DRAW STAGE 2 ---
if enable_stage_2:
    d.move_from(vout1_node, dx=0, dy=0)
    
    # Coupling (Drawing Leftwards now because M1 is flipped facing Left)
    # Actually, if M1 is flipped (Gate Right), the drain is on the Left?
    # No, 'flip=True' usually puts the vertical bar on the right and gate on the right.
    # The connections (D/S) are on the Left. 
    # So we need to draw LEFT to connect to the next stage? 
    # Let's assume we want to stack them or move left. 
    # To keep it linear Left-to-Right, we usually don't flip the mosfet.
    # BUT, assuming you want the signal to propagate, let's draw Left.
    
    if interstage_type == "Resistor":
        d.add(elm.Resistor().left().label('R_{c}'))
    elif interstage_type == "Capacitor":
        d.add(elm.Capacitor().left().label('C_{c}'))
    elif interstage_type == "Series R+C":
        d.add(elm.Resistor().left())
        d.add(elm.Capacitor().left())
    else: 
        d.add(elm.Line().left())
        
    # Stage 2 Gate Bias
    if s2_rg_total > 0:
        d.push()
        d.add(elm.Resistor().down().label(f'{s2_rg_total}Ω'))
        d.add(elm.Ground())
        d.pop()
        
    # MOSFET M2 (Flipped)
    Q2 = d.add(elm.NFet(flip=True).anchor('gate').label('$M_2$'))
    
    d.add(elm.Label().at(Q2.gate).label('G', loc='right', color='blue'))
    d.add(elm.Label().at(Q2.drain).label('D', loc='top', color='blue'))
    d.add(elm.Label().at(Q2.source).label('S', loc='bottom', color='blue'))
    
    # Stage 2 Source
    d.push()
    d.move_from(Q2.source, dx=0, dy=0)
    draw_network_components(d, s2_rs_en, s2_rs_is_par, s2_rs_s, s2_rs_p, "S2", direction="down")
    d.add(elm.Ground())
    d.pop()
    
    # Stage 2 Drain
    d.move_from(Q2.drain, dx=0, dy=0)
    draw_network_components(d, s2_rd_en, s2_rd_is_par, s2_rd_s, s2_rd_p, "D2", direction="up")
    d.add(elm.Vdd().label('$V_{DD}$'))
    
    # Probe Vout2
    d.add(elm.Line().left().at(Q2.drain).length(1))
    d.add(elm.Dot(open=True))
    d.add(elm.Label().label('$V_{out2}$', loc='left'))

# --- RENDER ---
schem_fig = d.draw()

# Reduce Whitespace (Tight Layout)
if schem_fig.fig:
    schem_fig.fig.subplots_adjust(left=0.05, bottom=0.05, right=0.95, top=0.95)
    st.pyplot(schem_fig.fig)
else:
    st.pyplot(schem_fig)

# --- RESULTS ---
st.divider()
c1, c2, c3 = st.columns(3)

c1.metric("Stage 1 Gain", f"{av1:.2f} V/V")
# Display Total R for reference
st.caption(f"**Reference:** Rd1_Total={s1_rd_total:.0f}Ω | Rs1_Total={s1_rs_total:.0f}Ω")

if enable_stage_2:
    c2.metric("Stage 2 Gain", f"{av2:.2f} V/V")
    c3.metric("Total Gain", f"{total_gain:.2f} V/V")
    st.caption(f"**Reference:** Rd2_Total={s2_rd_total:.0f}Ω | Rs2_Total={s2_rs_total:.0f}Ω")
else:
    c2.metric("Total Gain", f"{av1:.2f} V/V")
