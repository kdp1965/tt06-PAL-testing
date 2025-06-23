import sys
import argparse
import subprocess
from generate_bitstream_multiple_outputs import *

modified_ascii = {
       " ": 0, "!" : 27, "-" : 28, "." : 29, "_" : 30, "'" : 31
} | {chr(i + 0x41): i+1 for i in range(26)}

o_terms = ["" for i in range(5)]

# ====================================================================================
# Argument parser
# ====================================================================================
parser = argparse.ArgumentParser(description='Generate equations for string detect FSM')
parser.add_argument('string', help='String to parse')
parser.add_argument('filename', help='Output filename')
args = parser.parse_args()

filename = args.filename
string   = args.string

if string != string.upper():
   string = string.upper()
   print(f'Converted to upercase {string}')

# ====================================================================================
# Function to help built T product terms
# ====================================================================================
def write_bit(input, active, file, first=False):
   if not first:
      print(' & ', end='', file=file)

   if active > 0:
      print(f' I{input}', end='', file=file)
   else:
      print(f'~I{input}', end='', file=file)

# ====================================================================================
# Function to help build O terms
# ====================================================================================
def add_o_term(o, term):
   if len(o_terms[o]) > 0:
      o_terms[o] += " | "
   o_terms[o] += f'T{term}'

# ====================================================================================
# Validate the string isn't too long
# ====================================================================================
if len(string) > 11:
   print(f'Oops, {len(string)} too long ... can only support up to 11 characters')
   exit(2)

# ====================================================================================
# Validate we can support all input characters
# ====================================================================================
valid = True
for c in string:
   if c not in modified_ascii:
      print(f'Oops, character {c} not supported!')
      valid = False

if not valid:
   exit(2)

# ====================================================================================
# Open the output file
# ====================================================================================
with open(filename, 'w') as file:

   # ====================================================================================
   # Generate the product terms
   # ====================================================================================
   state = 0
   term  = 0
   last_term  = 0
   for c in string:
      # First output terms for the state
      print(f'T{term:<2d} = ', end='', file=file)
      write_bit(7, state & 4, file, True) 
      write_bit(6, state & 2, file) 
      write_bit(5, state & 1, file) 

      v = modified_ascii[c]
      write_bit(4, v & 0x10, file) 
      write_bit(3, v & 0x08, file) 
      write_bit(2, v & 0x04, file) 
      write_bit(1, v & 0x02, file) 
      write_bit(0, v & 0x01, file) 
    
      # Print the state and character as a comment
      print(f'      # S:{state}  {c} ({v})', file=file)

      # Advance the state
      state += 1
      if state == 8:
         state = 0

      # Add this term to the output terms
      if state & 1:
         add_o_term(0, term)
      if state & 2:
         add_o_term(1, term)
      if state & 4:
         add_o_term(2, term)
      add_o_term(3, term)

      last_term = term
      term  += 1

   # Now add the done term
   add_o_term(4, last_term)

   # Print the outout terms to the file
   print('', file=file)
   for i in range(5):
      print(f'O{i} = {o_terms[i]}', file=file)

# Run the bitstream generator
result = generate_bitstream(filename, True)

# The output should include something like:
# 'prog' : [0x..., 0x..., ...]
# We'll extract that
prog_line = None
for line in result:
    line = line.strip()
    if line.startswith("'prog'"):
        prog_line = line
        break

if prog_line is None:
    raise RuntimeError("Couldn't find the 'prog' output in the bitstream script output.")

# Example: filename = "hello.txt"
module_name = filename.rsplit('.', 1)[0]  # → "hello"
pyname = module_name + '.py'
msg = string.lower().replace(' ', '_').translate(str.maketrans('', '', "'!.-"))
func_name = f'{msg}_config'

with open(pyname, 'w') as out:
    out.write(f"def {func_name}():\n")
    out.write(f"    return {{\n")
    out.write(f'        "msg": "{string}",\n')
    for line in result:
        out.write(f"    {line}\n")
    out.write(f"    }}\n")

