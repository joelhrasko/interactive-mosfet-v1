import streamlit as st
import schemdraw
import schemdraw.elements as elm
import matplotlib.pyplot as plt

# --- 1. PAGE SETUP -----------------------------------------------------------------
st.set_page_config(page_title="CMOS Amplifier Designer", layout="wide")
st.title("Interactive CMOS Amplifier Designer (Multi-Stage)")

# --- 2. SIDEBAR PARAMETERS ---------------------------------------------------------------
st.sidebar.header("Global Settings")
zoom = st.sidebar.slider("Schematic Scale", 1.0, 5.0, 3.0, 0.25)
font_size = st.sidebar.slider("Text Size", 8, 24, 14, 1)
# Lowered minimum to 0.1 for tighter packing
wire_len = st.sidebar.slider("Wire Spacing (Grounds/Nodes)", 0.1, 3.0, 1.0, 0.1)

# --- HELPER: CALCULATE VALUES ---------------------------------------------------------------
def calculate_network(name, label_prefix, default_val):
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
        
    return enable, r_eq, r_series, r_par, is_parallel

# --- HELPER: DRAWER ---------------------------------------------------------------------------------------------------------------------------
def draw_resistor_network(d, enable, is_parallel, r_s, r_p, label, direction="right", spacing=1.0):
    if not enable:
        # Draw a wire if disabled (Short) + Spacing
        total_len = spacing + 2.0
        if direction == "right": d.add(elm.Line().right().length(total_len))
        elif direction == "up": d.add(elm.Line().up().length(total_len))
        elif direction == "down": d.add(elm.Line().down().length(total_len))
        return

    # 1. Draw Lead-in Wire (Spacing)
    if direction == "right": d.add(elm.Line().right().length(spacing))
    elif direction == "up": d.add(elm.Line().up().length(spacing))
    elif direction == "down": d.add(elm.Line().down().length(spacing))

    # 2. Draw Main Resistor
    lbl_s = f'$R_{{{label}1}}$\n{r_s:.0f}Ω'
    start_point = d.here
    
    if direction == "right": d.add(elm.Resistor().right().label(lbl_s))
    elif direction == "up": d.add(elm.Resistor().up().label(lbl_s))
    elif direction == "down": d.add(elm.Resistor().down().label(lbl_s))
        
    end_point = d.here 
    
    # 3. Draw Parallel Branch
    if is_parallel:
        d.push()
        d.here = start_point 
        lbl_p = f'$R_{{{label}2}}$\n{r_p:.0f}Ω'
        # Reduced offset to 1.8 to prevent overlap
        width_offset = 1.8 
        
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

# --- STAGE 1 INPUTS ---------------------------------------------------------------------------------------------------------------------------
st.sidebar.divider()
st.sidebar.header("Stage 1 Parameters")
s1_rg_en, s1_rg_total, s1_rg_s, s1_rg_p, s1_rg_is_par = calculate_network("Stage 1 Gate", "G", 10000.0)

s1_add_gate_div = st.sidebar.checkbox("Add Stage 1 Gate Divider")
s1_rg_div = 0
if s1_add_gate_div:
    s1_rg_div = st.sidebar.number_input("Stage 1 Gate Divider (Ω)", value=20000.0, step=1000.0)

s1_rd_en, s1_rd_total, s1_rd_s, s1_rd_p, s1_rd_is_par = calculate_network("Stage 1 Drain", "D", 5000.0)
s1_rs_en, s1_rs_total, s1_rs_s, s1_rs_p, s1_rs_is_par = calculate_network("Stage 1 Source", "S", 1000.0)


# --- STAGE 2 INPUTS ---------------------------------------------------------------------------------------------------------------------------
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
    s2_rd_en, s2_rd_total, s2_rd_s, s2_rd_p, s2_rd_is_par = calculate_network("Stage 2 Drain", "D", 5000.0)
    s2_rs_en, s2_rs_total, s2_rs_s, s2_rs_p, s2_rs_is_par = calculate_network("Stage 2 Source", "S", 500.0)

# --- MATH ENGINE ---------------------------------------------------------------------------------------------------------------------------
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

# --- DRAWING ENGINE -------------------------------------------------------------
st.subheader("Circuit Schematic")
d = schemdraw.Drawing()
d.config(unit=zoom, fontsize=font_size)

# --- DRAW STAGE 1 ---------------------------------------------------------------
# 1. Ground
d.add(elm.Ground())

# 2. Input Source
d.add(elm.SourceSin().up().label('$V_{in}$'))
d.add(elm.Line().up().length(wire_len))

# 3. Gate Network
d.add(elm.Dot())
d.push()
draw_resistor_network(d, s1_rg_en, s1_rg_is_par, s1_rg_s, s1_rg_p, "G", direction="right", spacing=wire_len)

# Gate Divider
if s1_add_gate_div:
    d.push()
    d.add(elm.Line().right(0.5)) 
    d.add(elm.Resistor().down().label(f'$R_{{div}}$\n{s1_rg_div:.0f}Ω'))
    d.add(elm.Line().down().length(wire_len))
    d.add(elm.Ground())
    d.pop()

# 4. MOSFET M1 (LOCKED: 180 + Flip)
# Adjusted M1 Label Offset: (1.5, -1.0) moves it down and right
Q1 = d.add(elm.NFet().theta(180).flip().anchor('gate').label('$M_1$', ofst=(1.5, -1.0)))

# Tweaked Pin Labels
# G: Moved down slightly (ofst=(0, -0.5))
# D: Moved up slightly (ofst=(0, 0.5))
d.add(elm.Label().at(Q1.gate).label('G', loc='left', ofst=(-0.2, -0.6), color='blue'))
d.add(elm.Label().at(Q1.drain).label('D', loc='bottom', ofst=(0.5, 0.5), color='blue'))
d.add(elm.Label().at(Q1.source).label('S', loc='top', ofst=(0.5, 0), color='blue'))

# 5. Source Network
d.push()
d.move_from(Q1.source, dx=0, dy=0)
d.add(elm.Line().down().length(wire_len))
draw_resistor_network(d, s1_rs_en, s1_rs_is_par, s1_rs_s, s1_rs_p, "S", direction="down", spacing=0)
d.add(elm.Line().down().length(wire_len))
d.add(elm.Ground())
d.pop()

# 6. Drain Network
d.move_from(Q1.drain, dx=0, dy=0)
d.add(elm.Line().up().length(wire_len)) 
draw_resistor_network(d, s1_rd_en, s1_rd_is_par, s1_rd_s, s1_rd_p, "D", direction="up", spacing=0)
d.add(elm.Line().up().length(wire_len)) 
d.add(elm.Vdd().label('$V_{DD}$'))

# Probe Vout1
d.add(elm.Line().right().at(Q1.drain).length(1.5))
d.add(elm.Dot(open=True))
d.add(elm.Label().label('$V_{out1}$', loc='top'))
    
vout1_node = d.here 

# --- DRAW STAGE 2 ---------------------------------------------------------------------------------------------------------------------------
if enable_stage_2:
    d.move_from(vout1_node, dx=0, dy=0)
    
    # Interstage Coupling
    coupling_total_width = 6.0
    
    if interstage_type == "Resistor":
        d.add(elm.Line().right().length(1.5))
        d.add(elm.Resistor().right().length(3.0).label(r'$R_c$'))
        d.add(elm.Line().right().length(1.5))
    elif interstage_type == "Capacitor":
        d.add(elm.Line().right().length(1.5))
        d.add(elm.Capacitor().right().length(3.0).label(r'$C_c$'))
        d.add(elm.Line().right().length(1.5))
    elif interstage_type == "Series R+C": 
        d.add(elm.Resistor().right().length(3.0).label(r'$R_c$'))
        d.add(elm.Capacitor().right().length(3.0).label(r'$C_c$'))
    else: 
        d.add(elm.Line().right().length(coupling_total_width))

    # Stage 2 Gate Bias
    if s2_rg_total > 0:
        d.push()
        d.add(elm.Line().down().length(wire_len)) 
        d.add(elm.Resistor().down().label(f'{s2_rg_total}Ω'))
        d.add(elm.Line().down().length(wire_len)) 
        d.add(elm.Ground())
        d.pop()
        
    # MOSFET M2
    Q2 = d.add(elm.NFet().theta(180).flip().anchor('gate').label('$M_2$', ofst=(1.5, -1.0)))
    
    d.add(elm.Label().at(Q2.gate).label('G', loc='left', ofst=(-0.2, -0.6), color='blue'))
    d.add(elm.Label().at(Q2.drain).label('D', loc='bottom', ofst=(0.5, 0.5), color='blue'))
    d.add(elm.Label().at(Q2.source).label('S', loc='top', ofst=(0.5, 0), color='blue'))

    # Stage 2 Source
    d.push()
    d.move_from(Q2.source, dx=0, dy=0)
    d.add(elm.Line().down().length(wire_len)) 
    draw_resistor_network(d, s2_rs_en, s2_rs_is_par, s2_rs_s, s2_rs_p, "S", direction="down", spacing=0)
    d.add(elm.Line().down().length(wire_len)) 
    d.add(elm.Ground())
    d.pop()
    
    # Stage 2 Drain
    d.move_from(Q2.drain, dx=0, dy=0)
    d.add(elm.Line().up().length(wire_len)) 
    draw_resistor_network(d, s2_rd_en, s2_rd_is_par, s2_rd_s, s2_rd_p, "D", direction="up", spacing=0)
    d.add(elm.Line().up().length(wire_len)) 
    d.add(elm.Vdd().label('$V_{DD}$'))
    
    # Probe Vout2
    d.add(elm.Line().right().at(Q2.drain).length(1.5))
    d.add(elm.Dot(open=True))
    d.add(elm.Label().label('$V_{out2}$', loc='top'))

# --- RENDER ---------------------------------------------------------------------------------------------------------------------------
schem_fig = d.draw()

if schem_fig.fig:
    # WIDESCREEN RATIO FIX
    # We use a smaller height multiplier (1.8 instead of 2.5) to keep it "Short and Wide"
    schem_fig.fig.set_size_inches(zoom * 4.0, zoom * 1.8) 
    # Tight layout removes margins
    schem_fig.fig.subplots_adjust(left=0.02, bottom=0.02, right=0.98, top=0.98)
    st.pyplot(schem_fig.fig)
else:
    st.pyplot(schem_fig)

# --- RESULTS ---------------------------------------------------------------------------------------------------------------------------
st.divider()

g1, g2, g3 = st.columns(3)
g1.metric("Stage 1 Gain", f"{av1:.2f} V/V")
if enable_stage_2:
    g2.metric("Stage 2 Gain", f"{av2:.2f} V/V")
    g3.metric("Total Gain", f"{total_gain:.2f} V/V")
else:
    g2.metric("Total Gain", f"{av1:.2f} V/V")

st.divider()
r1, r2, r3, r4 = st.columns(4)
r1.metric("R_D1 Total", f"{s1_rd_total:.0f} Ω")
r2.metric("R_S1 Total", f"{s1_rs_total:.0f} Ω")

if enable_stage_2:
    r3.metric("R_D2 Total", f"{s2_rd_total:.0f} Ω")
    r4.metric("R_S2 Total", f"{s2_rs_total:.0f} Ω")
