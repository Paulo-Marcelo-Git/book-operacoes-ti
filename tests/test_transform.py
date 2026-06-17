"""Valida o transform contra a planilha real (números confirmados).

A fixture sample.xlsx contém dados reais e NÃO é versionada (ver .gitignore).
Se ela não estiver presente (ex.: clone limpo), os testes são pulados.
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
    assert D["total"] == 1595
    assert D["inc_total"] == 1248
    assert D["sol_total"] == 347
    assert D["sla_total"] == 64
    assert D["res_total"] == 1589


@skip_sem_fixture
def test_keywords():
    D = transform.build_from_file(FIXTURE)
    kw = {k["keyword"]: k["total"] for k in D["keywords"]}
    assert kw["Nota Fiscal / NF"] == 101
    assert kw["Estoque"] == 35
    assert kw["Pedido"] == 167   # palavra exata: NÃO conta "pedidos"


@skip_sem_fixture
def test_estruturas_de_lista():
    D = transform.build_from_file(FIXTURE)
    assert len(D["top_solicitantes"]) <= 10
    assert len(D["subcat_matrix"]) <= 15
    assert all("por_grupo" in k for k in D["keywords"])
