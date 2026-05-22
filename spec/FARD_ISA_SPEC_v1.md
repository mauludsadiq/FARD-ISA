# FARD-ISA Specification v1

## Purpose

FARD-ISA is a minimal fixed-width instruction set that preserves OMIR semantics and emits a canonical receipt event for every retired instruction.

The ISA is designed for provability, deterministic replay, hardware event emission, and receipt equivalence. Performance is secondary.

## Instruction encoding

instruction_size = 16 bytes
endianness       = big-endian
pc_unit          = byte address
pc_increment     = 16

Generic instruction shape:

byte 0..1   opcode:u16
byte 2      rd:u8
byte 3      rs1:u8
byte 4      rs2:u8
byte 5      flags:u8
byte 6..7   imm16:u16
byte 8..15  imm64:u64 / rel64:u64 / payload:u64

## Opcode classes

0x01xx LOAD / STORE
0x02xx INTEGER
0x03xx FARDVAL
0x04xx CONTROL
0x05xx CALL / ABI
0x06xx TRUST
0x07xx TRAP / HALT

## Required v1 instructions

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

## Program counter model

The program counter is a byte address into the instruction stream.

All architectural instructions are 16 bytes.

Sequential execution advances:

pc_next = pc + 16

Branch, jump, and call targets are byte addresses. OMIR instruction indexes are lowered to byte addresses by multiplying by 16.

LABEL is pseudo only. It never retires and never emits an event.

## Architectural state

The v1 architectural state is:

pc
flags
privilege
regs
memory
memory_root
call_stack
epoch_id
prior_epoch_digest
receipt
locked
halted
chip_id
rom_root
attest_counter

No silent architectural state exists.

Every state transition caused by a retired instruction must be reflected in CanonicalEventV1.

## Register model

Registers are numbered integer slots.

rd, rs1, and rs2 are encoded as u8 fields.

The simulator currently treats registers as FardVal records.

FardVal v1 layout:

tag:u32
pad:u32
payload:u64

Known tags:

TAG_INT  = 0
TAG_BOOL = 1
TAG_UNIT = 2

## Memory model

Memory is byte-addressed.

memory_root is the canonical digest of architectural memory state.

TRUST.READ, TRUST.ATTEST, and TRUST.VERIFY read or write memory through explicit addresses held in registers. Memory effects are architectural and must affect memory_root.

## Flag model

flags is an integer field.

CMP.ZERO writes flags:

flags = 1 if compared value is zero
flags = 0 otherwise

BR.NE branches when flags != 1.

## Privilege model

privilege is encoded as an architectural integer level.

v1 uses privilege value 0 for normal execution.

TRUST.LOCK may restrict future trust state mutation. Once locked, hardware implementations must prevent unauthorized mutation of ROM root, chip identity, and protected trust fields.

Privilege before and after each instruction is emitted in CanonicalEventV1.

## Instruction semantics

### LOAD.IMM64

Writes imm64 as FardVal INT into rd.

pc_next = pc + 16

### LOAD.SLOT

Loads a local slot into rd.

The slot index is imm64.

pc_next = pc + 16

### STORE.SLOT

Stores rs1 into local slot imm64.

pc_next = pc + 16

### STORE.PARAM

Stores a parameter or ABI argument value into slot/register mapping defined by the simulator ABI.

pc_next = pc + 16

### LOAD.ARG

Loads an ABI argument into rd or target slot according to v1 ABI mapping.

pc_next = pc + 16

### ADD.SLOT

Reads rd and slot imm64 as integer FardVals.

Writes rd = rd + slot.

Non-integer operands trap.

pc_next = pc + 16

### CMP.ZERO

Reads compared register or slot selected by operands.

Sets flags to 1 if payload is zero, otherwise 0.

pc_next = pc + 16

### FVAL.BOX_I64

Reads integer payload from rs1 and writes FardVal INT into rd.

pc_next = pc + 16

### FVAL.UNBOX_I64

Reads FardVal from rs1.

If tag is TAG_INT, writes integer FardVal INT payload into rd.

If tag is not TAG_INT, traps.

pc_next = pc + 16

### FVAL.CHECK_TAG

Checks source value tag against expected tag encoded in imm64 or operand payload.

On match, writes boolean true to rd.

On mismatch, traps.

pc_next = pc + 16 on success.

### BR.NE

If flags != 1, pc_next = imm64.

Otherwise pc_next = pc + 16.

### BR.UNCOND

pc_next = imm64.

### CALL.REL32

Pushes return address pc + 16 to call_stack.

pc_next = imm64.

### RET.I64

Pops return address from call_stack.

pc_next = popped return address.

If call_stack is empty, execution halts or traps according to simulator semantics.

### TRUST.READ

Reads current trust receipt material into memory at address in rs1.

pc_next = pc + 16

### TRUST.FINALIZE

Computes EpochReceiptV1 digest from:

epoch_genesis
r_final
final_state_digest
output_digest
exit_code

Stores the resulting epoch digest as prior_epoch_digest for the next epoch and halts/seals the current epoch.

### TRUST.LOCK

Locks trust configuration.

After lock, trust-root mutation is forbidden.

pc_next = pc + 16

### TRUST.ATTEST

Computes Tier2AttestationV1 material using:

chip_id
rom_root
privilege
epoch_id
prior_epoch_digest
current_r
counter

Writes attestation digest bytes to memory at address in rs1.

Increments attest_counter.

pc_next = pc + 16

### TRUST.VERIFY

Reads expected digest bytes from memory at address in rs1.

Compares against prior_epoch_digest.

On match, execution continues.

On mismatch, traps.

pc_next = pc + 16 on success.

### TRAP

Emits a trap event and halts.

### HALT

Halts execution.

HALT retires and emits CanonicalEventV1.

## Canonical event rule

Every retired architectural instruction emits exactly one CanonicalEventV1.

Pseudo instructions emit no event.

The event commits to:

epoch_id
seq
pc_before
pc_after
privilege_before
privilege_after
opcode
operand_digest
register_read_digest
register_write_digest
memory_read_digest
memory_write_digest
flags_before
flags_after
result_digest
trap_digest
state_pre_digest
state_post_digest

After event emission:

event_digest = CanonicalEventV1.digest(event)
receipt_next = receipt_next(receipt_prev, event_digest)

No state transition is valid unless the receipt chain advances exactly once for the retired instruction.

## Epoch receipt rule

EpochReceiptV1 commits to:

epoch_id
epoch_genesis
r_final
final_state_digest
output_digest
exit_code
event_count
digest

The epoch digest is computed by trust_semantics.epoch_digest.

## Trust and attestation rule

Tier2AttestationV1 commits to:

chip_id
rom_root
privilege
epoch_id
prior_epoch_digest
current_r
counter
attest_digest

The attestation digest is computed by trust_semantics.attest.

Hardware and simulator attestation must match for identical inputs.

## Hardware output requirements

For Phase 4, CanonicalEventV1 must leave the RTL core through a hardware output port.

It must not be reconstructed only by testbench software.

Required hardware outputs:

event_valid
event_payload
event_digest
receipt_out
halted
trap

A testbench may consume these ports, but it may not invent missing event fields.

## Determinism requirements

For a fixed instruction stream, initial state, memory image, chip_id, rom_root, and epoch_id:

final architectural state must be identical
CanonicalEventV1 stream must be identical
receipt chain must be identical
EpochReceiptV1 must be identical
Tier2AttestationV1 must be identical

## Phase 4 compliance definition

The ISA specification is finalized when:

encoding is fixed
all v1 instructions are listed
pc model is byte-addressed
event emission is mandatory
epoch sealing is defined
trust and privilege model are defined
hardware event output requirements are defined
simulator and RTL have one shared observable contract
