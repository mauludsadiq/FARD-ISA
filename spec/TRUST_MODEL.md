# FARD ISA Trust Model

## Tier 0 — Semantic Trust

```text
OMIR interpreter
CanonicalEventV1
software event stream
```

## Tier 1 — Commodity Native Trust

```text
FARD Prim -> x86-64 Mach-O / ELF
compile-stage receipts
epoch-level execution receipts
host CPU and OS outside trust boundary
```

## Tier 2 — FARD-ISA Event-Stream Trust

```text
FARD-ISA simulator / FPGA
per architectural instruction CanonicalEventV1
event stream equivalence against OMIR interpreter
```

## Tier 3 — Fuse-Rooted Silicon Trust

```text
ASIC with ROM/fuse root
hardware retirement receipt unit
hardware-owned attestation fields
```

x86-64 is a development and performance target.

FARD-ISA is the trust target.
