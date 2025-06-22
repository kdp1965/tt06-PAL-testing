# SPDX-License-Identifier: Apache2.0
# Copyright (C) 2025 Ken Pettit

import rp2
from machine import Pin, mem32
import time

@rp2.asm_pio(
  out_init=rp2.PIO.OUT_LOW,
  out_shiftdir=rp2.PIO.SHIFT_RIGHT,
  set_init=rp2.PIO.OUT_LOW,
  fifo_join = rp2.PIO.JOIN_TX,
  autopull=True,
  pull_thresh=32
)
def pal_write():
  # Entry
  label("main_loop")
  wait(1, irq, 0)
  irq(clear, 0)

  # Prepare to shift 29 bytes
  set(y, 28)
  
  # Send 8 bits per byte
  label("byte_loop")
  set(x, 7)

  label("send_byte_loop")
  out(pins, 1)
  set(pins, 1)
  set(pins, 0)
  jmp(x_dec, "send_byte_loop")

  # Loop for number of bytes specified
  jmp(y_dec, "byte_loop")

  # Drop the 3 bytes we don't need
  out(null, 24)
  jmp("main_loop")


class PAL_PIOWriter:
  def __init__(self, sm_id=0, data_pin=21, clk_pin=23, freq=5_000_000):
    self.sms = []

    sm = rp2.StateMachine(
      sm_id,
      pal_write,
      freq=freq,
      out_base=Pin(data_pin),
      set_base=Pin(clk_pin),
      in_base=Pin(clk_pin),
      jmp_pin=Pin(clk_pin),
    )
    self.sms.append(sm)

    self.reset()

  def reset(self):
    self.op_index = 0

    # Step 4: Reactivate all SMs
    for sm in self.sms:
      sm.active(1)

  # Distribute Opcodes across 4 SMs
  def write(self, word):
    self.sms[self.op_index//8].put(word)
    self.op_index += 1

    # There are 28 bytes per configuration
    if self.op_index == 28:
      self.op_index = 0

  def config(self):
    # Kick off SM0
    self.sms[0].exec(f"irq(0)")

  def stop(self):
    for sm in self.sms:
      sm.active(0)

