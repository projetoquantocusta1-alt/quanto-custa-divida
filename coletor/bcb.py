"""Banco Central: séries do SGS, cronograma de vencimentos (Demab), Focus e IF.data."""
import csv
import io
import re
import time
from datetime import date, timedelta

import config
from coletor import http


# ---------------------------------------------------------------- SGS
def _get_json(url, tentativas=4):
    erro = None
    for i in range(tentativas):
        try:
            r = http.get(url, headers={"Accept": "application/json"}, timeout=90)
            return r.json()
        except Exception as e:  # noqa: BLE001 — o SGS às vezes devolve HTML de erro; tenta de novo
            erro = e
            time.sleep(3 * (i + 1))
    raise erro


def serie(codigo: int, ini: str = config.SERIE_INICIO) -> dict[str, float]:
    """{'AAAA-MM': valor} de uma série mensal do SGS."""
    out = {}
    for item in _get_json(config.SGS.format(codigo=codigo, ini=ini)):
        d, m, a = item["data"].split("/")
        v = item.get("valor")
        if v in (None, ""):
            continue
        out[f"{a}-{m}"] = float(v)
    return out


def ultimo(codigo: int) -> tuple[str, float]:
    item = _get_json(config.SGS_ULTIMO.format(codigo=codigo))[-1]
    d, m, a = item["data"].split("/")
    return f"{a}-{m}-{d}", float(item["valor"])


# ---------------------------------------------------------------- cronograma de vencimentos
def _num(s):
    s = (s or "").strip()
    if s in ("", "-"):
        return 0.0
    return float(s.replace(".", "").replace(",", "."))


def ler_cronograma(texto: str) -> dict:
    """Lê o CSV do Demab (um vencimento por linha) e soma por ano e por título."""
    linhas = [l for l in texto.splitlines() if l.strip()]
    ref = next((re.search(r"(\d{2}/\d{2}/\d{4})", l).group(1) for l in linhas[:5] if "REFER" in l.upper()), None)
    i = next(k for k, l in enumerate(linhas) if l.upper().startswith("VENCIMENTO"))
    cab = [c.strip() for c in linhas[i].split(";")]
    titulos = [c for c in cab[1:] if c.upper() not in ("TOTAL", "PART %")]
    por_ano, por_titulo, vencs = {}, {t: 0.0 for t in titulos}, []
    for l in linhas[i + 1:]:
        cel = [c.strip() for c in l.split(";")]
        if not re.match(r"\d{2}/\d{2}/\d{4}", cel[0]):
            continue
        d, m, a = cel[0].split("/")
        vals = dict(zip(cab, cel))
        tot = _num(vals.get("TOTAL"))
        if tot <= 0:
            continue
        o = por_ano.setdefault(a, {t: 0.0 for t in titulos} | {"total": 0.0})
        for t in titulos:
            v = _num(vals.get(t))
            o[t] += v
            por_titulo[t] += v
        o["total"] += tot
        vencs.append({"data": f"{a}-{m}-{d}", "total": tot, **{t: _num(vals.get(t)) for t in titulos if _num(vals.get(t))}})
    total = sum(v["total"] for v in por_ano.values())
    rd, rm, ra = (ref or "01/01/1900").split("/")
    return {"referencia": f"{ra}-{rm}-{rd}", "unidade": "R$ milhões", "titulos": titulos,
            "por_ano": {a: {k: round(v, 1) for k, v in o.items()} for a, o in sorted(por_ano.items())},
            "por_titulo": {t: round(v, 1) for t, v in por_titulo.items() if v},
            "total": round(total, 1),
            "proximos": [v for v in vencs if v["data"] <= _mais_meses(ref, 13)][:40]}


def _mais_meses(ref, n):
    d, m, a = (ref or "01/01/1900").split("/")
    mm = int(m) - 1 + n
    return f"{int(a) + mm // 12}-{mm % 12 + 1:02d}-{d}"


def cronograma(hoje: date) -> dict:
    # o Demab publica até dois dias úteis antes de hoje: tenta os últimos 8 dias
    for k in range(2, 10):
        dia = hoje - timedelta(days=k)
        if dia.weekday() >= 5:
            continue
        try:
            r = http.get(config.CRONOGRAMA.format(data=dia.strftime("%d/%m/%Y")), timeout=90)
            txt = r.content.decode("latin-1")
            if "VENCIMENTO" in txt.upper():
                c = ler_cronograma(txt)
                if c["total"] > 0:
                    return c
        except Exception:  # noqa: BLE001
            continue
    raise RuntimeError("cronograma de vencimentos indisponível")


# ---------------------------------------------------------------- Focus
def focus() -> dict:
    """Última mediana do Focus para os indicadores de dívida (se o Banco Central publicar)."""
    js = _get_json(config.FOCUS)
    out = {}
    for r in js.get("value", []):
        ind = r.get("Indicador")
        ano = str(r.get("DataReferencia"))
        if r.get("baseCalculo") not in (0, None):   # 0 = todas as respostas
            continue
        chave = (ind, ano)
        if chave in out:
            continue
        out[chave] = {"indicador": ind, "ano": ano, "mediana": r.get("Mediana"), "data": r.get("Data"),
                      "respondentes": r.get("numeroRespondentes")}
    return {"itens": sorted(out.values(), key=lambda x: (x["indicador"], x["ano"]))}


# ---------------------------------------------------------------- IF.data
def _odata(caminho: str) -> list[dict]:
    js = _get_json(f"{config.IFDATA}/{caminho}")
    return js.get("value", [])


def _limpa(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


# colunas do IF.data usadas no site: chave -> (relatório, expressão que reconhece o nome da coluna)
COLUNAS = {
    "ativo": ("2", r"^Ativo Total \(k\)"),
    "tvm": ("2", r"^Títulos e Valores Mobiliários \(c\)$"),
    "liquidez": ("2", r"^Aplicações Interfinanceiras de Liquidez \(b\)$"),
    "credito": ("2", r"^Operações de Crédito \(e\)$"),
    "renda_tvm": ("4", r"^Rendas de Títulos e Valores Mobiliários \(b\)"),
    "renda_liquidez": ("4", r"^Rendas de Aplicações Interfinanceiras de Liquidez \(a\)$"),
    "renda_credito": ("4", r"^Rendas de Operações de Crédito \(c\)$"),
    "lucro": ("4", r"^Lucro Líquido \(z\)"),
    "pl": ("1", r"^Patrimônio Líquido$"),
}


def ifdata_periodos(hoje: date, n=6) -> list[str]:
    """Trimestres candidatos (AAAAMM), do mais recente para o mais antigo."""
    out, a, m = [], hoje.year, hoje.month
    m = ((m - 1) // 3) * 3          # último fim de trimestre já fechado
    if m == 0:
        a, m = a - 1, 12
    while len(out) < n:
        out.append(f"{a}{m:02d}")
        m -= 3
        if m <= 0:
            a, m = a - 1, m + 12
    return out


def ifdata_valores(anomes: str, relatorio: str) -> list[dict]:
    return _odata(f"IfDataValores(AnoMes=@AnoMes,TipoInstituicao=@TipoInstituicao,Relatorio=@Relatorio)"
                  f"?@AnoMes={anomes}&@TipoInstituicao={config.IFDATA_TIPO}&@Relatorio='{relatorio}'"
                  f"&$top=500000&$format=json&$select=CodInst,NomeColuna,Saldo")


def ifdata_cadastro(anomes: str) -> list[dict]:
    return _odata(f"IfDataCadastro(AnoMes=@AnoMes)?@AnoMes={anomes}&$top=100000&$format=json")


def montar_bancos(cadastro: list[dict], valores: dict[str, list[dict]]) -> list[dict]:
    """Junta o cadastro (nome, segmento, controle) com as colunas escolhidas de cada relatório."""
    por_cod = {c["CodInst"]: c for c in cadastro}
    # conglomerado: usa o nome da instituição líder (CNPJ líder) ou do primeiro membro
    for c in cadastro:
        for chave in ("CodConglomeradoPrudencial", "CodConglomeradoFinanceiro"):
            cg = c.get(chave)
            if not cg:
                continue
            lider = c.get("CnpjInstituicaoLider")
            atual = por_cod.get(cg)
            if atual is None or (lider and c["CodInst"] == lider and atual.get("_membro")):
                por_cod[cg] = {**c, "CodInst": cg, "_membro": not (lider and c["CodInst"] == lider)}
    bancos: dict[str, dict] = {}
    for chave, (rel, padrao) in COLUNAS.items():
        rx = re.compile(padrao)
        for v in valores.get(rel, []):
            if not rx.search(_limpa(v.get("NomeColuna"))):
                continue
            o = bancos.setdefault(v["CodInst"], {"cod": v["CodInst"]})
            if chave not in o and v.get("Saldo") is not None:
                o[chave] = round(float(v["Saldo"]) / 1000, 3)   # IF.data vem em R$ mil -> R$ milhões
    CONTROLE = {1: "Público", 2: "Privado nacional", 3: "Estrangeiro"}
    out = []
    for cod, o in bancos.items():
        c = por_cod.get(cod, {})
        nome = _limpa(c.get("NomeInstituicao")) or cod
        if c.get("_membro"):
            nome = nome + " (conglomerado)"
        out.append({**o, "nome": nome, "segmento": c.get("SegmentoTb") or "Não informado",
                    "controle": CONTROLE.get(c.get("Tc"), "Não informado"), "porte": c.get("Sr") or "",
                    "uf": c.get("Uf") or "", "municipio": c.get("Municipio") or ""})
    return sorted(out, key=lambda b: -(b.get("tvm") or 0))
