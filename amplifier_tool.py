import streamlit as st
import schemdraw
import schemdraw.elements as elm
import matplotlib.pyplot as plt

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="CMOS Amplifier Designer", layout="wide")
st.title("Interactive CMOS Common Source Designer")

# --- 2. SIDEBAR (The "Element List") ---
st.sidebar.header("Component Parameters")

# Drain Resistor Controls
st.sidebar.subheader("Drain Network (Rd)")
rd_base = st.sidebar.slider("Base Rd Value (Ω)", 100, 10000, 2000, step=100)

# Feature: dynamic adding of a parallel resistor
add_parallel_rd = st.sidebar.checkbox("Add Parallel Resistor to Drain?")
if add_parallel_rd:
    rd_parallel = st.sidebar.slider("Parallel Rd Value (Ω)", 100, 10000, 2000, step=100)
    # Calculate equivalent resistance
    rd_total = (rd_base * rd_parallel) / (rd_base + rd_parallel)
    st.sidebar.info(f"Equivalent Rd: {rd_total:.1f} Ω")
else:
    rd_total = rd_base

# Gate Resistor Controls
st.sidebar.subheader("Gate Network (Rg)")
rg_val = st.sidebar.slider("Gate Resistor (Ω)", 100, 100000, 10000, step=1000)

# MOSFET Parameters (Hidden tuning values)
gm_per_A = 20e-3 # Simplified transconductance parameter for estimation

# --- 3. THE MATH ENGINE ---
# Simple Common Source Gain Approximation: Av = -gm * Rd
# We assume a small bias current to get a theoretical gm
gain = -gm_per_A * rd_total

# --- 4. DYNAMIC SCHEMATIC DRAWING ---
st.subheader("Circuit Schematic")

# We create the drawing without the 'with' context manager to avoid display errors
# if something goes wrong during element addition.
d = schemdraw.Drawing()
d.config(unit=2.5) # Scale of drawing

# Draw the MOSFET (Using NFet instead of Mosfet)
Q1 = d.add(elm.NFet().label('M1'))

# Draw Source (Grounded as requested)
d.add(elm.Ground().at(Q1.source))

# Draw Drain Network
# If user checked "Add Parallel", we visually draw two resistors
if add_parallel_rd:
    d.add(elm.Line().up(1.0).at(Q1.drain))
    d.add(elm.Dot())
    
    # Branch 1 (Left)
    d.push() # Save current position
    d.add(elm.Line().left(1.0))
    d.add(elm.Resistor().down().label(f'{rd_base}Ω', loc='bottom'))
    d.add(elm.Line().right(1.0))
    d.pop()  # Return to dot
    
    # Branch 2 (Right)
    d.add(elm.Line().right(1.0))
    d.add(elm.Resistor().down().label(f'{rd_parallel}Ω', loc='bottom'))
    d.add(elm.Line().left(1.0))
    
    # Reconnect to VDD
    d.add(elm.Line().up(1.5).at(Q1.drain)) # Go up past the parallel mess
    d.add(elm.Vdd().label('VDD'))
    
else:
    # Standard Single Resistor drawing
    d.add(elm.Resistor().up().at(Q1.drain).label(f'Rd\n{rd_total}Ω'))
    d.add(elm.Vdd().label('VDD'))

# Draw Gate Network
d.add(elm.Line().left().at(Q1.gate).length(1))
d.add(elm.Resistor().left().label(f'Rg\n{rg_val}Ω'))
d.add(elm.Dot())

# Input label
d.add(elm.Line().left().length(0.5))
d.add(elm.SourceSin().label('Vin'))
d.add(elm.Ground())

# Draw and display specifically for Streamlit
fig = d.draw()
st.pyplot(fig)

# --- 5. RESULTS DISPLAY ---
st.divider()
col1, col2 = st.columns(2)

with col1:
    st.metric(label="Total Drain Resistance", value=f"{rd_total:.1f} Ω")

with col2:
    # Color code the gain: Green if high, Red if low (just for fun UI)
    st.metric(label="Calculated DC Gain (Av)", value=f"{gain:.2f} V/V")

st.info("Note: Gain assumes an ideal current source load behavior approximation for demonstration.")
