# FARD ISA

The instruction set architecture for FARD — a deterministic, self-compiling language where every execution is a cryptographic proof.

FARD-ISA is designed for provability, not performance. Every instruction that retires produces a canonical event. The accumulator advances with every retirement. A sealed epoch is a cryptographic proof that a specific program ran, produced a specific output, and did so on a specific device.

---

## What This Is

FARD-ISA is the bridge between the software pipeline and silicon. It sits between OMIR (machine IR) and physical execution:

   FARD source
     -> fardlex -> fardparse -> fard_lower
     -> OCIR -> OMIR
     -> FARD-ISA binary
     -> simulator | FPGA | silicon
     -> canonical event stream
     -> EpochReceiptV1

Every layer above FARD-ISA is already written in pure FARD.

---

## Trust Tiers

   Tier 0  Semantic     Program is correct per OMIR spec
   Tier 1  Native       Program executed on some x86-64 machine
   Tier 2  FPGA         Program executed on FARD-ISA, events match golden interpreter
   Tier 3  Silicon      Program executed on a specific provisioned die,
                        chaining back to its ROM, with no unsealed gap

This repo targets Tier 2. Tier 3 requires silicon provisioning.

---

## Source

   src/
     canonical_event_v1.fard   canonical event schema, accumulator, epoch sealing
     fard_isa_encoding.fard    16-byte fixed-width instruction encoding and decoding
     fard_isa_memory.fard      page-aligned memory model, u64 little-endian store/load
     fard_isa_opcodes.fard     opcode constants
     fard_isa_registers.fard   32 registers, r_zero reads unit, SysV ABI mapping
     fard_isa_sim.fard         simulator: ADD, FVAL.CHECK_TAG, STORE/LOAD.MEM64
     fard_isa_types.fard       FardVal layout (tag+4, payload+8), validation, hex helpers
     fard_isa.fard             top-level re-export
     omir_to_fard_isa.fard     maps OMIR ops to ISA instructions
     trust_semantics.fard      TRUST.READ/FINALIZE/LOCK/ATTEST/VERIFY semantics

---

## Instructions

Fixed-width 16 bytes per instruction. Every instruction retirement produces a CanonicalEventV1.

   LOAD.IMM64     load immediate 64-bit value into register
   LOAD_SLOT      load from stack slot into register
   STORE_SLOT     store register to stack slot
   ADD_SLOT       add register and stack slot
   CMP_ZERO       compare stack slot to zero
   STORE_PARAM    store ABI argument register to stack slot at function entry
   LOAD_ARG       load stack slot into ABI argument register before call
   FVAL_BOX_I64   box integer into FardVal (tag=0, pad=0, payload=i64)
   FVAL_UNBOX_I64 unbox FardVal payload into integer register
   BR_NE          branch if not equal
   BR_UNCOND      unconditional branch
   CALL_REL32     call with rel32 reloc
   RET_I64        return integer from rax

Trust instructions:

   TRUST.READ     read current epoch accumulator R_n into register
   TRUST.FINALIZE seal epoch, emit EpochReceiptV1, start next epoch
   TRUST.LOCK     freeze accumulator within current privilege domain
   TRUST.ATTEST   emit HardwareAttestation signed by fuse-derived key
   TRUST.VERIFY   assert prior_epoch_receipt matches expected digest, fault if not

---

## FardVal Layout

   +0   tag     u32   0=INT 1=BOOL
   +4   pad     u32   always 0
   +8   payload u64   i64 bits or bool 0/1

Total: 16 bytes, repr(C), stable ABI.

---

## Canonical Event

Every instruction retirement emits:

   opcode      which instruction
   slot        destination
   value       result
   pc          program counter
   timestamp   cycle count

Accumulator: R_{n+1} = SHA256(R_n || canonical(event_n))

Epoch seal: SHA256("FARD.EPOCH.v1" || genesis || R_final || final_state || output || exit_code)

---

## Tests

   fardrun test --program tests/test_canonical_event_v1.fard    2 passed
   fardrun test --program tests/test_omir_to_fard_isa.fard      2 passed
   fardrun test --program tests/test_fard_isa_encoding.fard     3 passed
   fardrun test --program tests/test_fard_isa_registers.fard    6 passed
   fardrun test --program tests/test_fard_isa_memory.fard       6 passed
   fardrun test --program tests/test_fard_isa_sim.fard          4 passed

   Total: 23 tests, all passing

---

## Roadmap

### Phase 1 — ISA Foundation (complete)

- [x] Canonical event schema (CanonicalEventV1)
- [x] Fixed-width 16-byte instruction encoding
- [x] Instruction decoding and roundtrip
- [x] 32 registers with r_zero semantics
- [x] SysV AMD64 ABI register mapping
- [x] Page-aligned memory model
- [x] u64 little-endian store/load
- [x] Memory root hash after every store
- [x] OMIR to ISA mapping (13 ops)
- [x] Trust instruction semantics (epoch_digest, attest)
- [x] Simulator: ADD, FVAL.CHECK_TAG, STORE/LOAD.MEM64

### Phase 2 — Simulator Completion

- [x] All 13 OMIR-mapped instructions simulated
- [x] FVAL_BOX_I64 and FVAL_UNBOX_I64 in simulator
- [x] STORE_PARAM and LOAD_ARG in simulator
- [x] BR_NE and BR_UNCOND in simulator
- [x] CALL_REL32 and RET_I64 in simulator
- [x] Trust instructions in simulator (READ, FINALIZE, LOCK, ATTEST, VERIFY)
- [x] Full canonical event emission for every instruction
- [x] Epoch sealing in simulator
- [x] Simulator verified against golden interpreter on 10+ programs

### Phase 3 — Golden Interpreter Verification

- [ ] fard_eval.fard handles full language (while, fs, imports)
- [x] Golden interpreter takes OMIR, produces EpochReceiptV1
- [x] Same program through golden interpreter and simulator produces matching receipts
- [x] Test suite: lex -> parse -> OMIR -> simulator -> receipt
- [ ] Test suite: recursive programs verified
- [ ] Test suite: closure and capture verified
- [ ] Tier 2 attestation formally defined and tested

### Phase 4 — FPGA Implementation

- [ ] ISA specification document finalized (encoding, events, trust, privilege model)
- [ ] Verilog implementation of FARD-ISA core
- [ ] Canonical event output port implemented as hardware output (not software side channel)
- [ ] HDL simulation passing against ISA simulator output
- [ ] Deployed to FPGA board (Digilent Arty A7 or equivalent)
- [ ] Full test suite passing on FPGA hardware
- [ ] Canonical event stream from FPGA matches simulator on all tests
- [ ] Tier 2 attestation demonstrated on physical hardware

### Phase 5 — Trust Infrastructure

- [ ] FuseGenesisRoot provisioning protocol defined
- [ ] ROM epoch genesis computation specified
- [ ] ProvisionRecord schema finalized
- [ ] TRUST.ATTEST signing verified end to end
- [ ] TRUST.VERIFY fault behavior tested
- [ ] Epoch chain continuity verified across privilege boundaries
- [ ] Interrupt and exception canonical event emission specified

### Phase 6 — Silicon

- [ ] RTL finalized and formally reviewed
- [ ] Synthesis (Synopsys or Yosys)
- [ ] Place and route
- [ ] GDSII tapeout
- [ ] Photomask generation
- [ ] Fabrication
- [ ] Post-fab fuse programming
- [ ] ProvisionRecord issued
- [ ] Tier 3 attestation demonstrated on physical die

---

## Context

FARD is in Stage 8 of self-hosting. The software pipeline is:

   source -> lex -> parse -> lower -> OCIR -> OMIR -> x86-64 -> MH_EXECUTE

written entirely in FARD, producing cryptographic receipts at every step.

FARD-ISA makes the execution tier of those receipts hardware-rooted.

   https://github.com/mauludsadiq/FARD
