# SPDX-License-Identifier: Apache2.0
# Copyright (C) 2025 Ken Pettit

from machine import Pin, UART
from ttboard.cocotb.dut import DUT
from ttboard.demoboard import DemoBoard
from pal_test.pal_writer import PAL_PIOWriter
from pal_test.hello import hello_world_config
from pal_test.dont_panic import dont_panic_config
import time

# ======================================================
# Pre-canned configs
# ======================================================
configs = {
  0: hello_world_config(),
  1: dont_panic_config(),
}

# ======================================================
# Modified ASCII encoding we will use
# ======================================================
modified_ascii = {
       " ": 0, "!" : 27, "-" : 28, "." : 29, "_" : 30, "'" : 31
} | {chr(i + 0x41): i+1 for i in range(26)}

# ======================================================
# Controller for the PAL interface
# ======================================================
class PALController(DUT):
    def __init__(self, tt: DemoBoard):
        super().__init__("DUT")
        self.tt = tt
        tt.uio_oe_pico.value = 0b00000111 
        self.i_clk    = self.new_bit_attribute("i_clk", tt.uio_in, 2)
        self.i_config = self.new_bit_attribute("i_config", tt.uio_in, 0)
        self.i_enable = self.new_bit_attribute("i_enable", tt.uio_in, 1)

        self.i_ascii  = self.new_slice_attribute("i_ascii", tt.ui_in, 4, 0)
        self.i_state  = self.new_slice_attribute("i_state", tt.ui_in, 7, 5)

        self.o_state  = self.new_slice_attribute("o_state", tt.uo_out, 2, 0)
        self.o_valid  = self.new_bit_attribute("o_valid", tt.uo_out, 3)
        self.o_done   = self.new_bit_attribute("o_done", tt.uo_out, 4)
        self.o_all    = self.new_slice_attribute("o_all", tt.uo_out, 4, 0)

        self.pio      = PAL_PIOWriter()

    def pio_prog(self, data):
        # Disable the config
        self.i_enable.value = 0
        self.i_clk.value    = 0

        # Reset the design
        self.tt.reset_project(True)
        self.tt.reset_project(False)

        # Program the PIO FIFOs
        for d in data:
            self.pio.write(d)

        # Now kick off the SM to perform the programming
        self.pio.config()

        # Now enable the config
        self.i_enable.value = 1

# ======================================================
# Test a string against the PAL programming
# ======================================================
def test_string(tt, pal, msg, expectPass = True):
  # Initial condition
  state = 0
  done = 0
  pal.i_state.value = state

  # ==========================
  # Loop for all characters
  # ==========================
  for char in msg:
    # Lookup the modified ASCII code
    try:
      v = modified_ascii[char]
    except:
      v = 0
    pal.i_ascii.value = v

    # =========================================
    # Check the valid bit for state transition
    # =========================================
    if pal.o_valid.value == 1:
      print(f'{char} ✅  ', end='')

      state = int(pal.o_state.value)
      if int(pal.o_done.value) == 1:
          done = 1
      pal.i_state.value = state
    else:
      print(f'{char} ❌  ', end='')
      state = 0
  print()  # Terminate the test response line

  # =============================================
  # Test if done bit was detected / report result
  # =============================================
  if not done and expectPass:
    print(f'Did not detect!  Reporting non-zero for all 256 possibe inputs as debug:')
    for s in range(8):
      pal.i_state.value = s
      for i in range(32):
        pal.i_ascii.value = i
  
      if int(pal.o_all.value) != 0:
        print(f"S:{s} I:{i:02x}  O:{int(pal.o_all.value):02x}")
  else:
    if done:
      print('Done bit detected')
    else:
      print('Done bit not set')
    print('Test passed! 👍')

# ======================================================
# This is the main test entry
# ======================================================
def be_a_PAL(tt, config=0):

  # Enable the Easy PAL
  tt.shuttle.tt_um_MATTHIAS_M_PAL_TOP_WRAPPER.enable()
  tt.reset_project(True)
  tt.reset_project(False)

  pal = PALController(tt)

  # Get the configuration
  try:
    c = configs[config]
  except:
    # =========================================
    # Test if a config was passed in
    # =========================================
    if isinstance(config, dict) and 'msg' in config and 'prog' in config:
      c = config
    else:
      print(f'Config {config} not found')
      exit(1)

  # =========================================
  # Configure the PAL using the PIO
  # =========================================
  pal.pio_prog(c["prog"])
  msg = c["msg"]

  print('================================================')
  print(f'Testing target string {msg}')
  print('================================================')
  test_string(tt, pal, msg)

  print('')
  print('================================================')
  print("Testing other strings to ensure they don't work")
  print('================================================')
  for msg in ["DUBIOUS", "NOPE!", "DON'T BOTHER"]:
    print(f'Trying: "{msg}"')
    test_string(tt, pal, msg, False)
    
    print('')

# vim: sw=2 ts=2 et

