# FARD ISA

The instruction set architecture for FARD — a deterministic, self-compiling language where every execution is a cryptographic proof.

FARD-ISA is designed for provability AND performance. Every instruction that retires produces a canonical event. The accumulator advances with every retirement. A sealed epoch is a cryptographic proof that a specific program ran, produced a specific output, and did so on a specific device. Optimizations that reduce instruction count -- register allocation, peephole copy propagation and dead-store elimination -- reduce retirements directly, making proofs cheaper without weakening them: see "Optimization Impact on Epoch Cost" below.

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
     fard_isa_regmap.fard      FARD Prim register/stack-slot operands -> ISA reg file (1-31)
     fard_isa_registers.fard   32 registers, r_zero reads unit, SysV ABI mapping
     fard_isa_sim.fard         simulator: all opcodes incl. LOAD_SLOT, ADD3/SUB3/MUL3/CMP3
     fard_isa_types.fard       FardVal layout (tag+4, payload+8), validation, hex helpers
     fard_isa.fard             top-level re-export
     omir_isa_fixups.fard      resolves Label/Jne/Jmp/CallReloc into concrete PC targets
                               (register-aliasing dialect -- non-recursive only, see below)
     omir_to_fard_isa_mem.fard memory-backed lowering: real per-call-frame stack via R_SP +
                               LOAD_MEM64/STORE_MEM64 -- correct for recursion
     omir_to_fard_isa.fard     maps OMIR ops to ISA instructions (legacy 13-op + FARD Prim
                               post-RA/peephole dialect via map_fard_prim_program)
     trust_semantics.fard      TRUST.READ/FINALIZE/LOCK/ATTEST/VERIFY semantics

---

## Instructions

Fixed-width 16 bytes per instruction. Every instruction retirement produces a CanonicalEventV1.

   LOAD.IMM64     load immediate 64-bit value into register
   LOAD_SLOT      load from stack slot into register
   STORE_SLOT     store register to stack slot
   ADD_SLOT       add register and stack slot (2-address, implicit accumulator)
   CMP_ZERO       compare register/slot to zero, sets flags
   ADD3           rd = rs1 + rs2   (3-address, reg or slot operands)
   SUB3           rd = rs1 - rs2
   MUL3           rd = rs1 * rs2
   CMP3           rd = (rs1 cmp rs2), predicate in imm64
                  (0=eq 1=ne 2=lt 3=le 4=gt 5=ge)
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

## Branch and Call Resolution

omir_isa_fixups.fard resolves FARD Prim's Label/Jne/Jmp/CallReloc OMIR
into concrete FARD-ISA PC targets, analogous to x86_64_fixups.fard but
trivial: every ISA instruction is a fixed 16 bytes, so a target is just
(mapped_instruction_index * 16). Verified end-to-end on max(10,42) with
real if/else branches (BR_NE/BR_UNCOND), and on fact(5)'s CallReloc
(self-recursive CALL_REL32/RET_I64 -- halts cleanly with a balanced
call stack).

## Recursive Correctness: Memory-Backed Stack (omir_to_fard_isa_mem)

The register-aliasing mapping above (fard_isa_regmap + omir_to_fard_isa)
is correct for non-recursive control flow (verified on max(10,42)) but
NOT for recursion: every {k:"stack",slot:N} operand aliases a FIXED
register-file index regardless of call depth, so a recursive CallReloc
clobbers the caller's still-live locals before it reads them back
(fact(5) computed 1, not 120).

omir_to_fard_isa_mem.fard fixes this by giving FARD-ISA a real stack:
register R_SP (index 31, reserved) holds a memory address, and
{k:"stack",slot:N} becomes mem[R_SP+N] via LOAD_MEM64/STORE_MEM64.
Prologue/Epilogue adjust R_SP by frame_size (and push/pop
used_callee_saved registers to memory), exactly like real x86-64 `sub
rsp,N` / `add rsp,N` -- so each recursive call gets a fresh,
non-aliased frame, just like the native binary.

One OMIR instruction now expands to several ISA instructions (e.g. a
stack read is LOAD_IMM64+ADD3+LOAD_MEM64), so map_program computes
flattened instruction offsets for branch/call-target fixups directly
(superseding omir_isa_fixups for this dialect).

Verified correct end-to-end:

   fact(5) = 120
   fib(3)  = 2     (fib(5)=5 and fib(8)=21 also verified manually;
                     fib(8) takes ~100 min due to fard_isa_memory's
                     full memory-root rehash on every store -- a
                     pre-existing perf issue, not a correctness one)
   max(10,42) = 42  (non-recursive control flow, unchanged)

This is the two dialects' tradeoff: omir_to_fard_isa (register
aliasing) gives the retirement-count results in "Optimization Impact
on Epoch Cost" above and is correct for non-recursive programs;
omir_to_fard_isa_mem (real stack memory) is correct for ALL programs
including recursion, at the cost of more retirements per OMIR
instruction (memory load/store sequences) and current simulator
slowness on deep recursion. Unifying these -- e.g. only spilling to
memory for slots that are provably cross-call-live, keeping
non-cross-call slots register-resident -- is future work.

## Heap Programs and the Function Table (map_module)

FARD Prim compiles every program with heap allocation (lists, records,
strings, closures) to MULTIPLE functions -- e.g. get0([10,20,30])
produces fard_alloc (called), get0, AND fard_main, with fard_main
issuing CallReloc to both fard_alloc and get0. The single-function
entry_offset()=0 convention (correct for fact/fib's self-recursion)
cannot resolve these cross-function calls.

map_module(funcs) builds a real function table:
  - LoadHeap{dst,ptr,offset}, StoreHeap{ptr,offset,src}, and
    LoadHeapDyn{dst,ptr,idx} (8-byte header + idx*8 element offset)
    are mapped to address-computation + LOAD_MEM64/STORE_MEM64,
    the same pattern as stack-slot access -- zero new opcodes.
  - fard_alloc is a synthetic 3-instruction function at offset 0,
    mirroring the real x86-64 bump-allocator stub exactly:
    R_BUMP (register 20) holds the bump pointer; fard_alloc returns
    the old value in rax and advances R_BUMP by rdi (the requested
    size).
  - Every compiled function follows at its own base offset; Jne/Jmp
    resolve to (function_base + local_label_offset)*16, and
    CallReloc{name} resolves to fn_table[name]*16 for ANY function,
    not just self-recursion.
  - The program's entry point is fn_table["fard_main"]*16.

Verified correct end-to-end:

   get0([10,20,30]) = 10   (LoadHeapDyn, list indexing)
   geta({a:42,b:7}) = 42   (LoadHeap, record field access)

Both run in single-digit seconds (no deep recursion, so
fard_isa_memory's per-store rehash cost stays small).

## Optimization Impact on Epoch Cost

FARD Prim's register allocator (callee-saved r12-r15 for values live
across recursive calls) plus a cross-block-safe peephole pass (copy
propagation + dead-store elimination) reduce FARD-ISA retirements
directly -- every eliminated OMIR instruction is one fewer canonical
event per epoch:

   program    pre-RA retirements   post-RA retirements   reduction
   fact(5)    27                   24                     -11.1%
   fib(10)    36                   34                     -5.6%

The entire reduction is LOAD_SLOT (eliminated CopyI64 chains). For
fib(35) -- 29,860,703 calls -- this is 2 fewer retirements per call,
~59.7M fewer canonical events total for the identical program output,
matching the 0.128s -> 0.108s native x86-64 wall-clock improvement
measured in FARD Prim. Verified in tests/test_retirement_reduction.fard.

## Register File

32 registers, index 0 (r_zero) is hardwired: reads as unit, writes
discarded. Indices 1-31 are general purpose.

FARD Prim's compiled OMIR (post register-allocation and peephole) uses
named x86-64 registers (rax, rcx, ..., r15) and stack slots (-8, -16,
..., -120). fard_isa_regmap.fard maps these onto indices 1-31:

   index  1-16   rax,rcx,rdx,rbx,rsp,rbp,rsi,rdi,r8..r15
   index 17-31   stack slots -8 .. -120 (slot -8N -> index 16+N)

This means FARD Prim's optimized OMIR -- the same code that runs
natively on x86-64/ARM64 -- is *directly* a FARD-ISA program via
omir_to_fard_isa.map_fard_prim_program. No separate "ISA dialect":
register allocation that reduces native instruction count also
reduces FARD-ISA instruction retirements, which reduces canonical
events per epoch.

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

   fardrun test --program tests/test_canonical_event_v1.fard             2 passed
   fardrun test --program tests/test_closure_capture_programs.fard           3 passed
   fardrun test --program tests/test_omir_to_fard_isa.fard               2 passed
   fardrun test --program tests/test_fard_isa_encoding.fard              3 passed
   fardrun test --program tests/test_fard_isa_registers.fard             6 passed
   fardrun test --program tests/test_fard_isa_memory.fard                6 passed
   fardrun test --program tests/test_fard_isa_sim.fard                  19 passed
   fardrun test --program tests/test_golden_interpreter_equivalence.fard 16 passed
   fardrun test --program tests/test_golden_omir_interpreter.fard        8 passed
   fardrun test --program tests/test_omir_to_isa_receipt_equivalence.fard 8 passed
   fardrun test --program tests/test_phase3_pipeline_receipt.fard        4 passed
   fardrun test --program tests/test_recursive_programs.fard             3 passed
   fardrun test --program tests/test_tier2_attestation.fard             3 passed
   fardrun test --program tests/test_fard_prim_omir_mapping.fard         4 passed
   fardrun test --program tests/test_retirement_reduction.fard           2 passed
   fardrun test --program tests/test_branch_call_fixups.fard             3 passed
   fardrun test --program tests/test_omir_to_fard_isa_mem.fard           3 passed
   fardrun test --program tests/test_omir_to_fard_isa_mem_heap.fard       2 passed
   fardrun test --program tests/test_multiarg.fard                        2 passed
   fardrun test --program tests/test_closures_mem.fard                   1 passed

   Total: 100 tests, all passing

   (test_golden_interpreter_equivalence.fard grew from 10 -> 16 with
   receipt-equivalence checks for LOAD_SLOT, ADD3, SUB3, MUL3, CMP3, and
   CMP_ZERO-on-register -- the opcodes FARD Prim's register allocator
   and peephole pass actually emit. test_fard_isa_registers.fard grew
   from 4 -> 6 to reflect REG_COUNT=64.)

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
- [x] OMIR to ISA mapping (13 ops, legacy lowercase-kind dialect)
- [x] FARD Prim post-RA/peephole OMIR mapping (map_fard_prim_program):
      ADD3/SUB3/MUL3/CMP3 (3-address reg/slot), LOAD_SLOT as generic
      register move, register-file unification of all r10-r15 +
      stack slots into indices 1-31
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

- [x] fard_eval.fard handles full language (while, fs, imports)
- [x] Golden interpreter takes OMIR, produces EpochReceiptV1
- [x] Same program through golden interpreter and simulator produces matching receipts
- [x] Test suite: lex -> parse -> OMIR -> simulator -> receipt
- [x] Test suite: recursive programs verified
- [x] Test suite: closure and capture verified
- [x] Tier 2 attestation formally defined and tested

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

# License

MUI