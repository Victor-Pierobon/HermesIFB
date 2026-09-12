"""Roda a simulação ponta-a-ponta dentro do pytest (HERMES.md seção 9: pytest verde a cada commit)."""
from hermes.simulacao_e2e import executar_simulacao


def test_ciclo_completo_solic_ack_confirmado():
    executar_simulacao()
