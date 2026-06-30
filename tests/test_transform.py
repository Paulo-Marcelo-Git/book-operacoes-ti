"""Valida a integridade estrutural do transform.

A fixture sample.xlsx NÃO é versionada (contém dados reais).
Coloque a planilha em tests/fixtures/ antes de rodar.
Se ausente (ex.: clone limpo), os testes são pulados automaticamente.
"""
from pathlib import Path

import pytest

from src.book_ti import transform

FIXTURE = Path(__file__).parent / "fixtures" / "sample.xlsx"
skip_sem_fixture = pytest.mark.skipif(
    not FIXTURE.exists(),
    reason="fixture sample.xlsx ausente (dados reais não versionados)",
)


@skip_sem_fixture
def test_kpis_totais():
    D = transform.build_from_file(FIXTURE)
    assert D["total"] > 0
    assert D["inc_total"] + D["sol_total"] == D["total"]
    assert 0 <= D["sla_total"] <= D["total"]
    assert 0 <= D["res_total"] <= D["total"]


@skip_sem_fixture
def test_keywords():
    D = transform.build_from_file(FIXTURE)
    assert len(D["keywords"]) == len(transform.KEYWORDS)
    for kw in D["keywords"]:
        assert kw["total"] >= 0
        assert "por_grupo" in kw


@skip_sem_fixture
def test_estruturas_de_lista():
    D = transform.build_from_file(FIXTURE)
    assert len(D["top_solicitantes"]) <= 10
    assert len(D["subcat_matrix"]) <= 15
    assert all("por_grupo" in k for k in D["keywords"])
