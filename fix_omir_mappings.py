from pathlib import Path
p = Path("src/omir_to_fard_isa.fard")
s = p.read_text()

# Add aliases and fix missing mappings
s = s.replace(
    'else if k == "add_reg_stack" then',
    'else if k == "add_reg_stack" || k == "add_slot" then'
)
s = s.replace(
    'else if k == "cmp_stack_zero" then',
    'else if k == "cmp_stack_zero" || k == "cmp_zero" then'
)
s = s.replace(
    'else if k == "jne" then',
    'else if k == "jne" || k == "br_ne" || k == "br_if_ne" then'
)
s = s.replace(
    'else if k == "write_fval_int" then',
    'else if k == "write_fval_int" || k == "fval_box_i64" then'
)
s = s.replace(
    'else if k == "unbox_int" then',
    'else if k == "unbox_int" || k == "fval_unbox_i64" then'
)

p.write_text(s)
print("Fixed omir_to_fard_isa.fard with aliases")
