import pytest
from scripts.calibrate_medical_reviewer import calibration_calls
from app.contracts import ContractViolation


def test_calibration_repairs_contract_once_and_does_not_send_expected_labels():
    attempts, outputs, payloads = [], [], []
    packet = {'claims': [{'index': 0, 'text': '本内容不代表个人诊断建议。'}],
              'evidence': [], 'policy_rules': {'educational_scope': '不替代个体诊断'}}
    class Model:
        def review(self, state):
            payloads.append(dict(state))
            assert set(state) <= {'review_packet', 'contract_repair'}
            return {'claims': [{'index': 0, 'kind': 'project_behavior', 'support_status': 'supported',
                'evidence_ids': [], 'policy_rules': [] if len(payloads) == 1 else ['educational_scope'], 'note': '模拟'}]}
    calibration_calls(Model(), packet, outputs, attempts)
    assert len(payloads) == 2 and len(outputs) == 1
    assert [a['status'] for a in attempts] == ['failed', 'completed']
    assert attempts[0]['diagnostic']['claim_index'] == 0


def test_calibration_second_contract_failure_is_recorded_without_third_call():
    attempts, outputs = [], []
    class Model:
        def review(self, state): return {'claims': [{'index': 0, 'kind': 'project_behavior',
            'support_status': 'supported', 'evidence_ids': [], 'policy_rules': [], 'note': '模拟'}]}
    packet = {'claims': [{'index': 0, 'text': '政策句。'}], 'evidence': [], 'policy_rules': {}}
    with pytest.raises(ContractViolation, match='POLICY_REQUIRED'):
        calibration_calls(Model(), packet, outputs, attempts)
    assert len(attempts) == 2 and not outputs
    assert all(a['status'] == 'failed' for a in attempts)
