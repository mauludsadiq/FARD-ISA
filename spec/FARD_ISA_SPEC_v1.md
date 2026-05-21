# FARD-ISA Specification v1

## Purpose

FARD-ISA is a minimal fixed-width instruction set that preserves OMIR semantics and emits a canonical receipt event for every retired instruction.

The ISA is designed for provability, not performance.

## Instruction width

```text
instruction_size = 16 bytes
endianness       = big-endian
```

Generic instruction shape:

```text
byte 0      opcode_hi
byte 1      opcode_lo
byte 2      rd
byte 3      rs1
byte 4      rs2
byte 5      flags
byte 6..7   imm16
byte 8..15  imm64 / rel64 / payload
```

## Opcode classes

```text
0x01xx LOAD / STORE
0x02xx INTEGER
0x03xx FARDVAL
0x04xx CONTROL
0x05xx CALL / ABI
0x06xx TRUST
0x07xx TRAP / HALT
```

## Required v1 instructions

```text
LOAD.IMM64
LOAD.SLOT
STORE.SLOT
STORE.PARAM
LOAD.ARG
ADD.SLOT
CMP.ZERO
FVAL.BOX_I64
FVAL.UNBOX_I64
FVAL.CHECK_TAG
BR.NE
BR.UNCOND
CALL.REL32
RET.I64
TRUST.READ
TRUST.FINALIZE
TRUST.LOCK
TRUST.ATTEST
TRUST.VERIFY
TRAP
HALT
```

## Label handling

`LABEL` is pseudo only. It never retires and never emits an event.

## Core retirement rule

```text
instruction retires
  -> CanonicalEventV1 emitted
  -> event_digest computed
  -> R_next computed
```

No silent side effects exist.
