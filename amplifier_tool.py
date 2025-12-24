import streamlit as st
import schemdraw
import schemdraw.elements as elm
import matplotlib.pyplot as plt

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="CMOS Amplifier Designer", layout="wide")
st.title("Interactive CMOS Amplifier Designer (Multi-Stage)")

# --- 2. SIDEBAR PARAMETERS ---
st.sidebar.header("Global Settings")
zoom = st.sidebar.slider("Schematic Scale (Zoom)", 1.0, 5.0, 2.5, 0.25)

# --- HELPER: CALCULATE VALUES ---
def calculate_network(name, default_val):
    """Creates sidebar UI for a resistor network and calculates equivalent R."""
    st.sidebar.markdown(f"**{name} Network**")
    enable = st.sidebar.checkbox(f"Enable {name}", value=True, key=f"{name}_en")
    
    r_eq = 0.0
    r_series = 0.0
    r_par = 0.0
    is_parallel = False
    
    if enable:
        r_series = st.sidebar.number_input(f"{name} Series (Ω)", value=default_val, step=100.0, key=f"{name}_s")
        r_eq = r_series
        
        is_parallel = st.sidebar.checkbox(f"Add Parallel to {name}", key=f"{name}_pen")
        if is_parallel:
            r_par = st.sidebar.number_input(f"{name} Parallel (Ω)", value=default_val, step=100.0, key=f"{name}_p")
            if (r_series + r_par) > 0:
                r_eq = (r_series * r_par) / (r_series + r_par)
        
        st.sidebar.caption(f"Total {name} Resistance: {r_eq:.1f} Ω")
        
    return enable, r_eq, r_series, r_par, is_parallel

# --- HELPER: ROBUST COMPONENT DRAWER ---
def draw_resistor_network(d, enable, is_parallel, r_s, r_p, label, direction="right"):
    """
    Draws a wire, a single resistor, or a parallel pair.
    CRITICAL: Keeps the main cursor strictly linear to avoid rotation bugs.
    """
    if not enable:
        # Just draw a wire in the requested direction
        if direction == "right": d.add(elm.Line().right())
        elif direction == "up": d.add(elm.Line().up())
        elif direction == "down": d.add(elm.Line().down())
        return

    # Draw the "Main" path component (Series Resistor)
    lbl_s = f'$R_{{{label}}}$\n{r_s:.0f}Ω'
    
    # We use 'd.here' to track where we started for the parallel branch
    start_point = d.here
    
    # DRAW MAIN BRANCH (Moves the cursor forward)
    if direction == "right":
        main_r = d.add(elm.Resistor().right().label(lbl_s))
    elif direction == "up":
        main_r = d.add(elm.Resistor().up().label(lbl_s))
    elif direction == "down":
        main_r = d.add(elm.Resistor().down().label(lbl_s))
        
    end_point = d.here # This is where we want to end up eventually
    
    # DRAW PARALLEL BRANCH (If enabled)
    # We use push/pop so this drawing logic NEVER affects the final cursor position/rotation
    if is_parallel:
        d.push() # Save cursor at 'end_point'
        
        # Go back to start to draw the second branch
        d.here = start_point 
        
        lbl_p = f'{r_p:.0f}Ω'
        
        # Offset logic depends on direction
        if direction == "right":
            d.add(elm.Line().up(1.0)) # Go up
            d.add(elm.Resistor().right().length(3).label(lbl_p)) # Draw R same length as main
            d.add(elm.Line().down(1.0).to(end_point)) # Connect back to end
        
        elif direction == "up":
            d.add(elm.Line().left(1.0)) 
            d.add(elm.Resistor().up().length(3).label(lbl_p))
            d.add(elm.Line().right(1.0).to(end_point))
            
        elif direction == "down":
            d.add(elm.Line().left(1.0))
            d.add(elm.Resistor().down().length(3).label(lbl_p))
            d.add(elm.Line().right(1.0).to(end_point))
            
        d.pop() # Restore cursor to 'end_point' so the next component attaches correctly

# --- STAGE 1 INPUTS ---
st.sidebar.divider()
st.sidebar.header("Stage 1 Parameters")
s1_rg_en, s1_rg_total, s1_rg_s, s1_rg_p, s1_rg_is_par = calculate_network("Stage 1 Gate", 10000.0)
s1_rd_en, s1_rd_total, s1_rd_s, s1_rd_p, s1_rd_is_par = calculate_network("Stage 1 Drain", 5000.0)
s1_rs_en, s1_rs_total, s1_rs_s, s1_rs_p, s1_rs_is_par = calculate_network("Stage 1 Source", 1000.0)

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
d.config(unit=zoom, fontsize=12)

# --- STAGE 1 DRAWING ---
d.add(elm.Ground())
d.add(elm.SourceSin().up().label('$V_{in}$'))

# 1. Gate Network (Draws Rightwards)
d.add(elm.Dot())
d.push() # Save "Input Node"
draw_resistor_network(d, s1_rg_en, s1_rg_is_par, s1_rg_s, s1_rg_p, "G1", direction="right")

# Gate Divider (Parallel to Ground)
if s1_add_gate_div:
    d.push() # Save position at Gate
    d.add(elm.Resistor().down().label(f'$R_{{div}}$\n{s1_rg_div:.0f}Ω'))
    d.add(elm.Ground())
    d.pop()

# 2. MOSFET M1 (Standard Orientation: Gate Left, Drain Top, Source Bottom)
# We anchor to the Gate to ensure precise connection
Q1 = d.add(elm.NFet().anchor('gate').label('$M_1$'))

# Labels (Gate on Left, so label goes Left)
d.add(elm.Label().at(Q1.gate).label('G', loc='left', color='blue'))
d.add(elm.Label().at(Q1.drain).label('D', loc='top', color='blue'))
d.add(elm.Label().at(Q1.source).label('S', loc='bottom', color='blue'))

# 3. Source Network (Draws Downwards from Source)
d.push()
d.move_from(Q1.source, dx=0, dy=0)
draw_resistor_network(d, s1_rs_en, s1_rs_is_par, s1_rs_s, s1_rs_p, "S1", direction="down")
d.add(elm.Ground())
d.pop()

# 4. Drain Network (Draws Upwards from Drain)
d.move_from(Q1.drain, dx=0, dy=0)
draw_resistor_network(d, s1_rd_en, s1_rd_is_par, s1_rd_s, s1_rd_p, "D1", direction="up")
d.add(elm.Vdd().label('$V_{DD}$'))

# Probe Vout1 (Draws to the Right from Drain)
d.add(elm.Line().right().at(Q1.drain).length(1))
d.add(elm.Dot(open=True))
d.add(elm.Label().label('$V_{out1}$', loc='right'))
vout1_node = d.here 

# --- STAGE 2 DRAWING ---
if enable_stage_2:
    d.move_from(vout1_node, dx=0, dy=0)
    
    # Interstage Coupling (Drawing Rightwards)
    if interstage_type == "Resistor":
        d.add(elm.Resistor().right().label('R_{c}'))
    elif interstage_type == "Capacitor":
        d.add(elm.Capacitor().right().label('C_{c}'))
    elif interstage_type == "Series R+C":
        d.add(elm.Resistor().right())
        d.add(elm.Capacitor().right())
    else: 
        d.add(elm.Line().right())
        
    # Stage 2 Gate Bias
    if s2_rg_total > 0:
        d.push()
        d.add(elm.Resistor().down().label(f'{s2_rg_total}Ω'))
        d.add(elm.Ground())
        d.pop()
        
    # MOSFET M2 (Standard)
    Q2 = d.add(elm.NFet().anchor('gate').label('$M_2$'))
    
    d.add(elm.Label().at(Q2.gate).label('G', loc='left', color='blue'))
    d.add(elm.Label().at(Q2.drain).label('D', loc='top', color='blue'))
    d.add(elm.Label().at(Q2.source).label('S', loc='bottom', color='blue'))
    
    # Stage 2 Source
    d.push()
    d.move_from(Q2.source, dx=0, dy=0)
    draw_resistor_network(d, s2_rs_en, s2_rs_is_par, s2_rs_s, s2_rs_p, "S2", direction="down")
    d.add(elm.Ground())
    d.pop()
    
    # Stage 2 Drain
    d.move_from(Q2.drain, dx=0, dy=0)
    draw_resistor_network(d, s2_rd_en, s2_rd_is_par, s2_rd_s, s2_rd_p, "D2", direction="up")
    d.add(elm.Vdd().label('$V_{DD}$'))
    
    # Probe Vout2
    d.add(elm.Line().right().at(Q2.drain).length(1))
    d.add(elm.Dot(open=True))
    d.add(elm.Label().label('$V_{out2}$', loc='right'))

# --- RENDER ---
schem_fig = d.draw()

if schem_fig.fig:
    # Tight layout to remove excess whitespace
    schem_fig.fig.subplots_adjust(left=0.05, bottom=0.05, right=0.95, top=0.95)
    st.pyplot(schem_fig.fig)
else:
    st.pyplot(schem_fig)

# --- RESULTS ---
st.divider()
c1, c2, c3 = st.columns(3)

c1.metric("Stage 1 Gain", f"{av1:.2f} V/V")
st.caption(f"**Reference:** Rd1_Total={s1_rd_total:.0f}Ω | Rs1_Total={s1_rs_total:.0f}Ω")

if enable_stage_2:
    c2.metric("Stage 2 Gain", f"{av2:.2f} V/V")
    c3.metric("Total Gain", f"{total_gain:.2f} V/V")
    st.caption(f"**Reference:** Rd2_Total={s2_rd_total:.0f}Ω | Rs2_Total={s2_rs_total:.0f}Ω")
else:
    c2.metric("Total Gain", f"{av1:.2f} V/V")
