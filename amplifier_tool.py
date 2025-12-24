import streamlit as st
import schemdraw
import schemdraw.elements as elm
import matplotlib.pyplot as plt

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="CMOS Amplifier Designer", layout="wide")
st.title("Interactive CMOS Amplifier Designer (Multi-Stage)")

# --- 2. SIDEBAR PARAMETERS ---
st.sidebar.header("Global Settings")
zoom = st.sidebar.slider("Schematic Scale (Component Size)", 1.0, 5.0, 2.5, 0.25)

# Applied to ALL wires now
wire_len = st.sidebar.slider("Wire Length (Spacing)", 0.5, 5.0, 2.0, 0.25)

st.sidebar.divider()
st.sidebar.header("MOSFET Orientation Fix")
st.sidebar.info("Use these if the Gate appears on the wrong side.")
# The "Nuclear Option" to force rotation
mosfet_theta = st.sidebar.select_slider("Rotate MOSFET (°)", options=[0, 90, 180, 270], value=0)
mosfet_mirror = st.sidebar.checkbox("Mirror MOSFET (Flip Vertical)", value=False)

# --- HELPER: CALCULATE VALUES ---
def calculate_network(name, default_val):
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

# --- HELPER: DRAWER ---
def draw_resistor_network(d, enable, is_parallel, r_s, r_p, label, direction="right", spacing=1.0):
    if not enable:
        # Draw a wire if disabled
        if direction == "right": d.add(elm.Line().right().length(spacing))
        elif direction == "up": d.add(elm.Line().up().length(spacing))
        elif direction == "down": d.add(elm.Line().down().length(spacing))
        return

    lbl_s = f'$R_{{{label}}}$\n{r_s:.0f}Ω'
    start_point = d.here
    
    # Draw Main Resistor
    if direction == "right": d.add(elm.Resistor().right().label(lbl_s))
    elif direction == "up": d.add(elm.Resistor().up().label(lbl_s))
    elif direction == "down": d.add(elm.Resistor().down().label(lbl_s))
        
    end_point = d.here 
    
    # Draw Parallel Branch
    if is_parallel:
        d.push()
        d.here = start_point 
        lbl_p = f'{r_p:.0f}Ω'
        width_offset = 1.2
        
        if direction == "right":
            d.add(elm.Line().up(width_offset)) 
            d.add(elm.Resistor().right().label(lbl_p)) 
            d.add(elm.Line().down(width_offset).to(end_point))
        elif direction == "up":
            d.add(elm.Line().left(width_offset)) 
            d.add(elm.Resistor().up().label(lbl_p))
            d.add(elm.Line().right(width_offset).to(end_point))
        elif direction == "down":
            d.add(elm.Line().left(width_offset))
            d.add(elm.Resistor().down().label(lbl_p))
            d.add(elm.Line().right(width_offset).to(end_point))
        d.pop()

# --- STAGE 1 INPUTS ---
st.sidebar.divider()
st.sidebar.header("Stage 1 Parameters")
s1_rg_en, s1_rg_total, s1_rg_s, s1_rg_p, s1_rg_is_par = calculate_network("Stage 1 Gate", 10000.0)
s1_rd_en, s1_rd_total, s1_rd_s, s1_rd_p, s1_rd_is_par = calculate_network("Stage 1 Drain", 5000.0)
s1_rs_en, s1_rs_total, s1_rs_s, s1_rs_p, s1_rs_is_par = calculate_network("Stage 1 Source", 1000.0)

s1_add_gate_div = st.sidebar.checkbox("Add Stage 1 Gate Divider")
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

# --- MATH ENGINE ---
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

# --- DRAWING ENGINE ---
st.subheader("Circuit Schematic")
d = schemdraw.Drawing()
d.config(unit=zoom, fontsize=12)

# --- DRAW STAGE 1 ---
# 1. Ground
d.add(elm.Ground())

# 2. Input Source (Up from Ground) - Using Slider for length
d.add(elm.SourceSin().up().length(wire_len).label('$V_{in}$'))

# 3. Gate Network (Right from Input)
d.add(elm.Dot())
d.push()
# Using Slider for spacing
draw_resistor_network(d, s1_rg_en, s1_rg_is_par, s1_rg_s, s1_rg_p, "G1", direction="right", spacing=wire_len)

# Gate Divider (Down to Ground)
if s1_add_gate_div:
    d.push()
    d.add(elm.Resistor().down().label(f'$R_{{div}}$\n{s1_rg_div:.0f}Ω'))
    d.add(elm.Ground())
    d.pop()

# 4. MOSFET M1 (MANUAL CONTROL)
# theta sets rotation (0, 90, 180, 270)
# flip mirrors it if Drain/Source are inverted
if mosfet_mirror:
    Q1 = d.add(elm.NFet().theta(mosfet_theta).flip().anchor('gate').label('$M_1$'))
else:
    Q1 = d.add(elm.NFet().theta(mosfet_theta).anchor('gate').label('$M_1$'))

# Smart Label Placement based on rotation
if mosfet_theta == 0: # Standard Gate Left
    g_loc, d_loc, s_loc = 'left', 'top', 'bottom'
elif mosfet_theta == 180: # Gate Right
    g_loc, d_loc, s_loc = 'right', 'bottom', 'top' # Note: 180 flips D/S vertically usually
else:
    g_loc, d_loc, s_loc = 'right', 'top', 'bottom'

d.add(elm.Label().at(Q1.gate).label('G', loc=g_loc, color='blue'))
d.add(elm.Label().at(Q1.drain).label('D', loc=d_loc, color='blue'))
d.add(elm.Label().at(Q1.source).label('S', loc=s_loc, color='blue'))

# 5. Source Network (Down from M1 Source)
d.push()
d.move_from(Q1.source, dx=0, dy=0)
draw_resistor_network(d, s1_rs_en, s1_rs_is_par, s1_rs_s, s1_rs_p, "S1", direction="down", spacing=wire_len)
d.add(elm.Ground())
d.pop()

# 6. Drain Network (Up from M1 Drain)
d.move_from(Q1.drain, dx=0, dy=0)
draw_resistor_network(d, s1_rd_en, s1_rd_is_par, s1_rd_s, s1_rd_p, "D1", direction="up", spacing=wire_len)
d.add(elm.Vdd().label('$V_{DD}$'))

# Probe Vout1
# Direction depends on where the Gate is. If Gate is Right (180), Probe must go Left.
probe_dir = 'right' if (mosfet_theta == 0) else 'left'

if probe_dir == 'right':
    d.add(elm.Line().right().at(Q1.drain).length(wire_len))
    d.add(elm.Dot(open=True))
    d.add(elm.Label().label('$V_{out1}$', loc='right'))
else:
    d.add(elm.Line().left().at(Q1.drain).length(wire_len))
    d.add(elm.Dot(open=True))
    d.add(elm.Label().label('$V_{out1}$', loc='left'))
    
vout1_node = d.here 

# --- DRAW STAGE 2 ---
if enable_stage_2:
    d.move_from(vout1_node, dx=0, dy=0)
    
    # Interstage Coupling
    if probe_dir == 'right':
        if interstage_type == "Resistor": d.add(elm.Resistor().right().label('R_{c}'))
        elif interstage_type == "Capacitor": d.add(elm.Capacitor().right().label('C_{c}'))
        elif interstage_type == "Series R+C": 
            d.add(elm.Resistor().right())
            d.add(elm.Capacitor().right())
        else: d.add(elm.Line().right().length(wire_len))
    else:
        # If drawing leftwards
        d.add(elm.Line().left().length(wire_len))

    # Stage 2 Gate Bias
    if s2_rg_total > 0:
        d.push()
        d.add(elm.Resistor().down().label(f'{s2_rg_total}Ω'))
        d.add(elm.Ground())
        d.pop()
        
    # MOSFET M2
    if mosfet_mirror:
        Q2 = d.add(elm.NFet().theta(mosfet_theta).flip().anchor('gate').label('$M_2$'))
    else:
        Q2 = d.add(elm.NFet().theta(mosfet_theta).anchor('gate').label('$M_2$'))
    
    d.add(elm.Label().at(Q2.gate).label('G', loc=g_loc, color='blue'))
    d.add(elm.Label().at(Q2.drain).label('D', loc=d_loc, color='blue'))
    d.add(elm.Label().at(Q2.source).label('S', loc=s_loc, color='blue'))

    # Stage 2 Source
    d.push()
    d.move_from(Q2.source, dx=0, dy=0)
    draw_resistor_network(d, s2_rs_en, s2_rs_is_par, s2_rs_s, s2_rs_p, "S2", direction="down", spacing=wire_len)
    d.add(elm.Ground())
    d.pop()
    
    # Stage 2 Drain
    d.move_from(Q2.drain, dx=0, dy=0)
    draw_resistor_network(d, s2_rd_en, s2_rd_is_par, s2_rd_s, s2_rd_p, "D2", direction="up", spacing=wire_len)
    d.add(elm.Vdd().label('$V_{DD}$'))
    
    # Probe Vout2
    if probe_dir == 'right':
        d.add(elm.Line().right().at(Q2.drain).length(wire_len))
        d.add(elm.Dot(open=True))
        d.add(elm.Label().label('$V_{out2}$', loc='right'))
    else:
        d.add(elm.Line().left().at(Q2.drain).length(wire_len))
        d.add(elm.Dot(open=True))
        d.add(elm.Label().label('$V_{out2}$', loc='left'))

# --- RENDER ---
schem_fig = d.draw()

if schem_fig.fig:
    schem_fig.fig.subplots_adjust(left=0.05, bottom=0.05, right=0.95, top=0.95)
    st.pyplot(schem_fig.fig)
else:
    st.pyplot(schem_fig)

# --- RESULTS ---
st.divider()
c1, c2, c3 = st.columns(3)

c1.metric("Stage 1 Gain", f"{av1:.2f} V/V")
st.caption(f"**Ref:** Rd1_Tot={s1_rd_total:.0f}Ω | Rs1_Tot={s1_rs_total:.0f}Ω")

if enable_stage_2:
    c2.metric("Stage 2 Gain", f"{av2:.2f} V/V")
    c3.metric("Total Gain", f"{total_gain:.2f} V/V")
    st.caption(f"**Ref:** Rd2_Tot={s2_rd_total:.0f}Ω | Rs2_Tot={s2_rs_total:.0f}Ω")
else:
    c2.metric("Total Gain", f"{av1:.2f} V/V")
