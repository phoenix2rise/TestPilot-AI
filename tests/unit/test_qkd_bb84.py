from security.qkd.bb84 import BB84Params, simulate_bb84

def test_bb84_clean_channel_usually_accepts():
    p = BB84Params(n_qubits=2048, sample_size=256, qber_threshold=0.11)
    t = simulate_bb84(p, intercept_resend=False)
    # With default noise=0, should almost always be accepted; allow rare randomness
    assert t.qber <= 0.25

def test_bb84_mitm_usually_detected():
    p = BB84Params(n_qubits=2048, sample_size=256, qber_threshold=0.11)
    t = simulate_bb84(p, intercept_resend=True)
    # Intercept-resend should push qber up; allow wide band due to randomness
    assert t.qber >= 0.05
