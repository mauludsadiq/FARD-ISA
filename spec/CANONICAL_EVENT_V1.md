# CanonicalEventV1

```text
size       = 354 bytes
encoding   = fixed-width
endianness = big-endian
padding    = none
```

## Layout

```text
offset  size  field
0       4     version = u32(1)
4       1     event_kind = u8(0x01)
5       8     epoch_id
13      8     seq
21      8     pc_before
29      8     pc_after
37      1     privilege_before
38      1     privilege_after
39      2     opcode
41      32    operand_digest
73      32    register_read_digest
105     32    register_write_digest
137     32    memory_read_digest
169     32    memory_write_digest
201     8     flags_before
209     8     flags_after
217     32    result_digest
249     32    trap_digest
281     32    state_pre_digest
313     32    state_post_digest
345     8     reserved_u64 = 0
353     1     terminator = 0xF1
```

## Hashing

```text
event_digest = SHA256("FARD.EVENT.v1" || event_bytes)

receipt_next =
  SHA256("FARD.RECEIPT.v1" || r_current || event_digest)
```

## Empty collection rule

Empty register/memory/operand collections are hashed as domain-separated empty collections.

`ZERO_DIGEST` is only for structurally absent fields such as `trap_digest` when no trap occurs.
