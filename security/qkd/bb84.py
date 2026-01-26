"""
BB84 QKD simulation (protocol-accurate at a functional level).

This module intentionally avoids any "quantum hardware" claims.
It simulates BB84 steps:
- Alice chooses random bits and bases
- Bob chooses random bases and measures (matching basis yields correct bit unless noise/eavesdrop)
- Sifting: keep only positions where bases match
- QBER: estimate error rate on a sample
- Key acceptance / eavesdrop detection based on QBER threshold

Security note:
BB84 by itself does not authenticate endpoints. Use signatures/PQC/etc. for authentication
on the classical channel. This repo demonstrates QKD-derived key gating.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
import secrets
import math

Basis = int  # 0 or 1

@dataclass(frozen=True)
class BB84Params:
    n_qubits: int = 2048
    sample_size: int = 256
    qber_threshold: float = 0.11  # ~11% commonly cited theoretical bound for simple intercept-resend
    channel_noise: float = 0.0    # probability of bit flip even without eavesdropper
    rng_seed: Optional[int] = None  # unused (secrets-based); included for interface completeness

@dataclass
class BB84Transcript:
    alice_bits: List[int]
    alice_bases: List[Basis]
    bob_bases: List[Basis]
    bob_results: List[int]
    sift_indices: List[int]
    sifted_alice: List[int]
    sifted_bob: List[int]
    sample_indices: List[int]
    sample_errors: int
    qber: float
    accepted: bool
    reason: str

def _rand_bits(n: int) -> List[int]:
    # secrets is fine for simulation; deterministic RNG can be added for experiments if needed
    return [secrets.randbelow(2) for _ in range(n)]

def _rand_bases(n: int) -> List[Basis]:
    return [secrets.randbelow(2) for _ in range(n)]

def _flip(bit: int) -> int:
    return 1 - bit

def simulate_bb84(params: BB84Params, *, intercept_resend: bool = False) -> BB84Transcript:
    n = params.n_qubits
    if params.sample_size >= n:
        raise ValueError("sample_size must be < n_qubits")

    alice_bits = _rand_bits(n)
    alice_bases = _rand_bases(n)
    bob_bases = _rand_bases(n)

    # Eve intercept-resend model:
    # Eve chooses random basis, measures, and resends; induces ~25% error on sifted key (idealized).
    eve_bases = _rand_bases(n) if intercept_resend else None
    eve_results = [0] * n

    bob_results: List[int] = [0] * n
    for i in range(n):
        a_bit = alice_bits[i]
        a_basis = alice_bases[i]
        b_basis = bob_bases[i]

        transmitted_bit = a_bit

        if intercept_resend:
            e_basis = eve_bases[i]
            # Eve measures: if basis matches, she gets correct; else random
            if e_basis == a_basis:
                e_bit = transmitted_bit
            else:
                e_bit = secrets.randbelow(2)
            eve_results[i] = e_bit
            # Eve resends in her basis; Bob receives that state
            transmitted_bit = e_bit
            # If Bob measures in same basis as Eve, he gets transmitted_bit; else random
            if b_basis == e_basis:
                b_bit = transmitted_bit
            else:
                b_bit = secrets.randbelow(2)
        else:
            # No Eve: if Bob basis matches Alice, get bit; else random
            if b_basis == a_basis:
                b_bit = transmitted_bit
            else:
                b_bit = secrets.randbelow(2)

        # Channel noise (bit flip)
        if params.channel_noise > 0 and secrets.randbelow(10_000) < int(params.channel_noise * 10_000):
            b_bit = _flip(b_bit)

        bob_results[i] = b_bit

    # Sifting: keep indices where bases match
    sift_indices = [i for i in range(n) if alice_bases[i] == bob_bases[i]]
    sifted_alice = [alice_bits[i] for i in sift_indices]
    sifted_bob = [bob_results[i] for i in sift_indices]

    # Sample a subset of sifted positions to estimate QBER (without replacement)
    if len(sift_indices) < params.sample_size:
        # Too few sifted bits; this can happen if n_qubits is tiny.
        # In practice you'd increase n_qubits. Here we fail safe.
        return BB84Transcript(
            alice_bits, alice_bases, bob_bases, bob_results,
            sift_indices, sifted_alice, sifted_bob,
            [], 0, 1.0, False, "INSUFFICIENT_SIFTED_BITS"
        )

    sample_positions = set()
    while len(sample_positions) < params.sample_size:
        sample_positions.add(secrets.randbelow(len(sift_indices)))
    sample_indices = sorted(list(sample_positions))

    errors = 0
    for pos in sample_indices:
        if sifted_alice[pos] != sifted_bob[pos]:
            errors += 1

    qber = errors / params.sample_size
    accepted = qber <= params.qber_threshold
    reason = "OK" if accepted else "QKD_EAVESDROP_OR_NOISE_DETECTED"

    return BB84Transcript(
        alice_bits=alice_bits,
        alice_bases=alice_bases,
        bob_bases=bob_bases,
        bob_results=bob_results,
        sift_indices=sift_indices,
        sifted_alice=sifted_alice,
        sifted_bob=sifted_bob,
        sample_indices=sample_indices,
        sample_errors=errors,
        qber=qber,
        accepted=accepted,
        reason=reason,
    )

def derive_session_key(transcript: BB84Transcript, *, key_bytes: int = 32) -> bytes:
    """
    Derive a session key from the sifted key material.
    This is a demonstration-only KDF (hash stretching) suitable for *demo gating*,
    not a formal privacy amplification implementation.
    """
    if not transcript.accepted:
        raise ValueError("Cannot derive key: transcript not accepted")

    # Remove sampled bits from key material (as a stand-in for "revealed" bits)
    revealed = set(transcript.sample_indices)
    raw_bits = [b for idx, b in enumerate(transcript.sifted_bob) if idx not in revealed]
    if len(raw_bits) < 256:
        # ensure enough entropy for demo; in practice you'd run longer n_qubits
        raise ValueError("Insufficient raw bits to derive key")

    # Convert bits to bytes
    out = bytearray()
    cur = 0
    count = 0
    for bit in raw_bits:
        cur = (cur << 1) | bit
        count += 1
        if count == 8:
            out.append(cur)
            cur = 0
            count = 0

    # KDF: repeated SHA-256 chaining
    import hashlib
    key = b""
    seed = bytes(out)
    digest = hashlib.sha256(seed).digest()
    while len(key) < key_bytes:
        digest = hashlib.sha256(digest + seed).digest()
        key += digest
    return key[:key_bytes]
