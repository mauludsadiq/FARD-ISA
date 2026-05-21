# FARD ISA

FARD ISA is the verifiable instruction-set layer between OMIR and future FARD hardware.

It defines:

- fixed-width FARD-ISA instruction encoding
- OMIR-to-ISA opcode mapping
- CanonicalEventV1 receipt event packing
- receipt accumulation
- a pure FARD ISA simulator
- equivalence test scaffolding for OMIR interpreter versus ISA simulator

The immediate purpose is not performance. The purpose is provability.

```text
FARD source
  -> OCIR
  -> OMIR
  -> FARD-ISA
  -> simulator / FPGA / ASIC
  -> CanonicalEventV1 receipt chain
```

## Files

```text
src/canonical_event_v1.fard     Canonical event packing and digest functions
src/fard_isa_opcodes.fard       Opcode constants and names
src/fard_isa_types.fard         Value, register, memory, and state helpers
src/omir_to_fard_isa.fard       OMIR-record to ISA-record mapping
src/fard_isa_sim.fard           ISA simulator with receipt accumulation
src/trust_semantics.fard        TRUST.* instruction semantics
src/fard_isa.fard               Public module facade

spec/FARD_ISA_SPEC_v1.md        Human-readable ISA specification
spec/CANONICAL_EVENT_V1.md      Exact 354-byte event layout
spec/TRUST_MODEL.md             Three-tier trust model

tests/test_canonical_event_v1.fard
tests/test_fard_isa_sim.fard
tests/test_omir_to_fard_isa.fard

examples/add2_isa.fard
```

## Non-negotiable invariants

```text
Every retired instruction emits exactly one CanonicalEventV1.
Every event advances the receipt accumulator.
Software cannot choose receipt events.
TRUST.EXTEND does not exist.
x86-64 is a Tier 1 commodity target.
FARD-ISA simulator/FPGA/ASIC are Tier 2/3 trust targets.
```
