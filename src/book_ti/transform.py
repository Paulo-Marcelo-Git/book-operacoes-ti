"""Transforma a planilha de chamados no dicionário `D` consumido pelo template.

Regras validadas contra a planilha real (números-alvo no test_transform.py).
"""
import argparse
import json
import re
import unicodedata

import pandas as pd

from . import config
from .logging_setup import get_logger

log = get_logger()

GRUPO_VAZIO = "Não atribuído"
ANALISTA_VAZIO = "none"
SUBCAT_VAZIA = "Outros"

# Atenção às regras: NF e Estoque casam por substring; "Pedido" é PALAVRA EXATA
# (\bpedido\b) e NÃO casa "pedidos". Foi assim que o mock foi gerado. Não unificar.
KEYWORDS = [
    ("Nota Fiscal / NF", r"nota\s*fiscal|\bnf\b"),
    ("Estoque",          r"estoque"),
    ("Pedido",           r"\bpedido\b"),
]


def _norm(texto) -> str:
    """Minúsculas + sem acentos, para a busca de keywords ser robusta."""
    if pd.isna(texto):
        return ""
    s = unicodedata.normalize("NFKD", str(texto))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()


def ler_planilha(caminho):
    """Lê o xlsx e resolve os nomes reais das colunas a partir das letras."""
    df = pd.read_excel(caminho, header=0)
    cols = {chave: df.columns[config.col_idx(letra)]
            for chave, letra in config.COLUNAS.items()}
    return df, cols


def build(df: pd.DataFrame, cols: dict) -> dict:
    """Constrói o dicionário D a partir do DataFrame e do mapa de colunas."""
    c = cols

    grupo = (df[c["grupo"]].fillna(GRUPO_VAZIO).astype(str).str.strip()
             .replace("", GRUPO_VAZIO))
    analista = (df[c["analista"]].fillna(ANALISTA_VAZIO).astype(str).str.strip()
                .replace("", ANALISTA_VAZIO))
    subcat = (df[c["subcategoria"]].fillna(SUBCAT_VAZIA).astype(str).str.strip()
              .replace("", SUBCAT_VAZIA))
    solic = (df[c["solicitante"]].fillna("—").astype(str).str.strip()
             .replace("", "—"))
    desc_norm = df[c["descricao"]].map(_norm)

    is_inc = df[c["tipo"]].astype(str).str.strip().eq("Incidente")
    is_sol = df[c["tipo"]].astype(str).str.strip().eq("Solicitação")
    is_sla = df[c["sla"]].astype(str).str.strip().eq("Sim")
    is_res = df[c["status"]].astype(str).str.strip().eq("Resolvido")

    base = pd.DataFrame({
        "grupo": grupo, "analista": analista, "sub": subcat, "solic": solic,
        "inc": is_inc, "sol": is_sol, "sla": is_sla, "res": is_res,
    })

    # ---- grupos (Coluna P) ----
    grupos = []
    for g, sub in base.groupby("grupo"):
        grupos.append({"grupo": g, "total": int(len(sub)), "sla": int(sub.sla.sum()),
                       "inc": int(sub.inc.sum()), "sol": int(sub.sol.sum())})
    grupos.sort(key=lambda x: x["total"], reverse=True)
    grupos_list = sorted(base["grupo"].unique().tolist())

    # ---- analistas (Coluna Q) ----
    analistas = []
    for a, sub in base.groupby("analista"):
        modo = sub["grupo"].mode()
        analistas.append({"analista": a, "total": int(len(sub)), "sla": int(sub.sla.sum()),
                          "inc": int(sub.inc.sum()), "sol": int(sub.sol.sum()),
                          "grupo": modo.iloc[0] if len(modo) else GRUPO_VAZIO})
    analistas.sort(key=lambda x: x["total"], reverse=True)

    # ---- subcategorias x grupo (Coluna L x P), top 15 ----
    subcat_matrix = []
    for s, sub in base.groupby("sub"):
        por_grupo = {k: int(v) for k, v in sub.groupby("grupo").size().to_dict().items()}
        subcat_matrix.append({"sub": s, "total": int(len(sub)), "por_grupo": por_grupo})
    subcat_matrix.sort(key=lambda x: x["total"], reverse=True)
    subcat_matrix = subcat_matrix[:15]

    # ---- keywords na descrição (Coluna I), quebrado por grupo ----
    keywords = []
    for nome, pat in KEYWORDS:
        mask = desc_norm.str.contains(pat, regex=True, na=False)
        por_grupo = {k: int(v) for k, v in base["grupo"][mask].value_counts().to_dict().items()}
        keywords.append({"keyword": nome, "total": int(mask.sum()), "por_grupo": por_grupo})

    # ---- top 10 solicitantes (Coluna O) ----
    top = []
    for s, sub in base.groupby("solic"):
        top.append({"solicitante": s, "total": int(len(sub)), "sla": int(sub.sla.sum()),
                    "inc": int(sub.inc.sum()), "sol_count": int(sub.sol.sum())})
    top.sort(key=lambda x: x["total"], reverse=True)
    top = top[:10]

    return {
        "total": int(len(df)),
        "sla_total": int(is_sla.sum()),
        "inc_total": int(is_inc.sum()),
        "sol_total": int(is_sol.sum()),
        "res_total": int(is_res.sum()),
        "grupos": grupos,
        "analistas": analistas,
        "subcat_matrix": subcat_matrix,
        "grupos_list": grupos_list,
        "keywords": keywords,
        "top_solicitantes": top,
    }


def build_from_file(caminho) -> dict:
    df, cols = ler_planilha(caminho)
    return build(df, cols)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Valida o transform contra um xlsx.")
    p.add_argument("--arquivo", required=True, help="caminho do .xlsx")
    p.add_argument("--dry-run", action="store_true", help="só imprime os KPIs")
    args = p.parse_args()

    D = build_from_file(args.arquivo)
    print(json.dumps({k: D[k] for k in
                      ("total", "inc_total", "sol_total", "sla_total", "res_total")},
                     ensure_ascii=False, indent=2))
    print("keywords:", [(k["keyword"], k["total"]) for k in D["keywords"]])
