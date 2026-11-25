"""Robô do Quanto Custa — Dívida Pública.

Baixa as séries oficiais do Banco Central e monta os arquivos pequenos que o site lê:
  docs/dados/divida.json  — dívida, juros, composição, vencimentos e projeção
  docs/dados/bancos.json  — balanço de cada banco e financeira (IF.data, trimestral)
  docs/dados/meta.json    — data da coleta e situação de cada fonte
Se uma fonte falhar, o arquivo anterior daquela parte é mantido e o site avisa.
Uso: python atualizar.py [--sem-bancos]
"""
import json
import sys
import traceback
from datetime import date, datetime, timezone
from pathlib import Path

import config
from coletor import bcb, calculos, http

DADOS = Path(__file__).parent / "docs" / "dados"


def ler(nome):
    try:
        return json.loads((DADOS / nome).read_text("utf-8"))
    except Exception:  # noqa: BLE001
        return None


def gravar(nome, obj):
    DADOS.mkdir(parents=True, exist_ok=True)
    (DADOS / nome).write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), "utf-8")


def coletar_series() -> dict:
    s = {}
    for chave, (codigo, _desc, _un) in config.SERIES.items():
        s[chave] = bcb.serie(codigo)
        print(f"  {chave} ({codigo}): {len(s[chave])} meses, último {max(s[chave]) if s[chave] else '—'}")
    return s


def montar_divida(s: dict, extras: dict) -> dict:
    meses = calculos.meses_ordenados(s["dbgg"], s["dlsp"], s["juros"])
    meses = [m for m in meses if m >= "2001-12"]
    ref = max(s["dbgg"])                       # último mês com a dívida bruta publicada
    col = lambda k: [s[k].get(m) for m in meses]  # noqa: E731
    mensal = {"meses": meses, **{k: col(k) for k in config.SERIES}}
    # IPCA dos meses depois do último dado da dívida: a correção pela inflação vai até o último IPCA
    # divulgado (o mesmo mês de referência dos outros sites), não só até o mês da dívida
    mensal["ipca_extra"] = {m: v for m, v in sorted(s["ipca"].items()) if m > meses[-1] and v is not None}
    # números do mês de referência
    j12 = calculos.soma_12(s["juros"], ref)
    p12 = calculos.soma_12(s["primario"], ref)
    n12 = calculos.soma_12(s["nominal"], ref)
    ano = int(ref[:4])
    j_ano, n_meses = calculos.soma_ano(s["juros"], ano, int(ref[5:]))
    anos = []
    for a in range(2002, ano + 1):
        ult = max((m for m in s["dbgg"] if m.startswith(f"{a}-")), default=None) or \
            max((m for m in s["dlsp"] if m.startswith(f"{a}-")), default=None)
        if not ult:
            continue
        jj, nj = calculos.soma_ano(s["juros"], a)
        pp, _ = calculos.soma_ano(s["primario"], a)
        nn, _ = calculos.soma_ano(s["nominal"], a)
        ip = [s["ipca"][f"{a}-{m:02d}"] for m in range(1, 13) if f"{a}-{m:02d}" in s["ipca"]]
        fator = 1.0
        for v in ip:
            fator *= 1 + v / 100
        se = [s["selic"][f"{a}-{m:02d}"] for m in range(1, 13) if f"{a}-{m:02d}" in s["selic"]]
        anos.append({"ano": a, "mes_ref": ult, "meses": nj, "fechado": nj == 12,
                     "dbgg": s["dbgg"].get(ult), "dbgg_pib": s["dbgg_pib"].get(ult),
                     "dlsp": s["dlsp"].get(ult), "dlsp_pib": s["dlsp_pib"].get(ult),
                     "juros": round(jj, 1), "primario": round(pp, 1), "nominal": round(nn, 1),
                     "ipca": round(100 * (fator - 1), 2) if ip else None,
                     "selic_media": round(sum(se) / len(se), 2) if se else None})
    resumo = {
        "referencia": ref,
        "dbgg": s["dbgg"][ref], "dbgg_pib": s["dbgg_pib"].get(ref),
        "dlsp": s["dlsp"].get(ref), "dlsp_pib": s["dlsp_pib"].get(ref),
        "juros_12m": j12, "primario_12m": p12, "nominal_12m": n12,
        "juros_ano": round(j_ano, 1), "juros_ano_meses": n_meses,
        "juros_pib12": s["juros_pib12"].get(ref), "primario_pib12": s["primario_pib12"].get(ref),
        "nominal_pib12": s["nominal_pib12"].get(ref),
        "pib12": s["pib12"].get(ref),
        "dpmf_mercado": s["dpmf_mercado"].get(ref), "dpmf_bc": s["dpmf_bc"].get(ref),
        "dpmf_emitido": s["dpmf_emitido"].get(ref), "prazo_medio": s["prazo_medio"].get(ref),
        "esferas_juros_12m": {k: calculos.soma_12(s[k], ref) for k in ("juros_gf", "juros_bc", "juros_est", "juros_mun", "juros_estatais")},
        "esferas_dlsp": {k: s[k].get(ref) for k in ("dlsp_gf", "dlsp_bc", "dlsp_est", "dlsp_mun", "dlsp_estatais")},
        "indexadores": {k: s[k].get(max(s[k])) for k in config.SERIES if k.startswith("idx_")},
        "indexadores_mes": max(s["idx_selic"]),
    }
    return {"gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "fontes": {k: {"codigo": c, "descricao": d, "unidade": u} for k, (c, d, u) in config.SERIES.items()},
            "resumo": resumo, "anos": anos, "mensal": mensal,
            "projecao": calculos.projecao(s["dbgg"], s["pib12"]),
            "projecao_dlsp": calculos.projecao(s["dlsp"], s["pib12"]),
            **extras}


def coletar_bancos(hoje: date) -> dict:
    erros = []
    for anomes in bcb.ifdata_periodos(hoje):
        try:
            valores = {rel: bcb.ifdata_valores(anomes, rel) for rel in ("1", "2")}
            if not valores["2"]:
                erros.append(f"{anomes}: sem dados")
                continue
            cad = bcb.ifdata_cadastro(anomes)
            # resultado de 12 meses: os dois últimos semestres fechados (o IF.data acumula jan–jun e jul–dez)
            sems = bcb.semestres(anomes)
            resultados = [bcb.ifdata_valores(sm, "4") for sm in sems]
            if not all(resultados):
                raise RuntimeError(f"resultado semestral incompleto: {sems}")
            bancos = [b for b in bcb.montar_bancos(cad, valores, resultados) if (b.get("ativo") or 0) > 0]
            print(f"  IF.data {anomes}: {len(bancos)} instituições; resultado de {sems}")
            campos = ["cod", "nome", "segmento", "controle", "porte", "uf", "ativo", "tvm", "liquidez", "credito",
                      "renda_tvm", "renda_liquidez", "renda_credito", "lucro", "pl"]
            return {"periodo": anomes, "semestres": sems, "tipo": "conglomerados prudenciais e instituições independentes",
                    "unidade": "R$ milhões", "campos": campos, "linhas": [[b.get(c) for c in campos] for b in bancos],
                    "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        except Exception as e:  # noqa: BLE001
            erros.append(f"{anomes}: {e}")
    raise RuntimeError("; ".join(erros))


def main():
    hoje = date.today()
    meta = ler("meta.json") or {}
    situacao = {}
    extras = {}
    # partes menores: se falharem, guardam a versão anterior
    anterior = ler("divida.json") or {}
    for nome, f in (("cronograma", lambda: bcb.cronograma(hoje)), ("focus", bcb.focus)):
        try:
            extras[nome] = f()
            situacao[nome] = "ok"
        except Exception as e:  # noqa: BLE001
            print(f"  {nome}: falhou ({e})")
            extras[nome] = anterior.get(nome)
            situacao[nome] = f"falhou: {str(e)[:200]}"
    try:
        dia, v = bcb.ultimo(config.SELIC_META)
        extras["selic_meta"] = {"data": dia, "valor": v}
    except Exception as e:  # noqa: BLE001
        extras["selic_meta"] = anterior.get("selic_meta")
        situacao["selic_meta"] = f"falhou: {e}"
    try:
        r = http.get(config.POPULACAO, timeout=30).json()
        extras["populacao"] = {"valor": int(r["projecao"]["populacao"]), "fonte": "IBGE — projeção da população (API)", "data": hoje.isoformat()}
    except Exception as e:  # noqa: BLE001
        extras["populacao"] = anterior.get("populacao") or {"valor": config.POPULACAO_RESERVA, "fonte": "IBGE — estimativa da população em 1º/7/2025", "data": "2025-07-01"}
        situacao["populacao"] = f"reserva: {e}"
    # parte principal: séries do Banco Central
    try:
        s = coletar_series()
        div = montar_divida(s, extras)
        if not div["resumo"]["dbgg"] or div["resumo"]["dbgg"] < 1_000_000:
            raise RuntimeError("dívida bruta fora do esperado")
        gravar("divida.json", div)
        situacao["series"] = "ok"
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        situacao["series"] = f"falhou: {str(e)[:200]}"
    if "--sem-bancos" not in sys.argv:
        try:
            gravar("bancos.json", coletar_bancos(hoje))
            situacao["bancos"] = "ok"
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            situacao["bancos"] = f"falhou: {str(e)[:300]}"
    meta.update({"gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"), "situacao": situacao})
    gravar("meta.json", meta)
    print(json.dumps(situacao, ensure_ascii=False, indent=1))
    if situacao.get("series") != "ok" and not (DADOS / "divida.json").exists():
        sys.exit(1)


if __name__ == "__main__":
    main()
