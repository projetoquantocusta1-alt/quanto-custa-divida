"""Contas feitas a partir das séries oficiais (sem nada inventado: tudo sai das séries do Banco Central)."""
import math


def meses_ordenados(*series: dict) -> list[str]:
    return sorted(set().union(*[s.keys() for s in series]))


def soma_12(serie: dict, mes: str) -> float | None:
    """Soma dos 12 meses que terminam em `mes` (None se faltar algum)."""
    a, m = map(int, mes.split("-"))
    tot = 0.0
    for k in range(12):
        mm = m - k
        aa = a + (mm - 1) // 12
        mm = (mm - 1) % 12 + 1
        v = serie.get(f"{aa}-{mm:02d}")
        if v is None:
            return None
        tot += v
    return tot


def soma_ano(serie: dict, ano: int, ate_mes: int = 12) -> tuple[float, int]:
    vals = [serie[f"{ano}-{m:02d}"] for m in range(1, ate_mes + 1) if f"{ano}-{m:02d}" in serie]
    return sum(vals), len(vals)


def ipca_indice(ipca: dict) -> dict:
    """Número-índice do IPCA (base = 100 no primeiro mês da série)."""
    idx, nivel = {}, 100.0
    for mes in sorted(ipca):
        nivel *= 1 + ipca[mes] / 100
        idx[mes] = nivel
    return idx


def projecao(divida: dict, pib12: dict, meses_frente=27, janela=12) -> dict:
    """Projeção simples: a dívida continua crescendo no ritmo médio dos últimos `janela` meses
    e o PIB continua crescendo no ritmo dos últimos 12 meses. A faixa é de 90% (± 1,645 desvios
    do aumento mensal, que cresce com a raiz do número de meses). É uma estimativa, não uma previsão oficial."""
    meses = sorted(divida)
    if len(meses) < janela + 1:
        return {}
    ult = meses[-1]
    deltas = [divida[meses[-k]] - divida[meses[-k - 1]] for k in range(1, janela + 1)]
    mu = sum(deltas) / len(deltas)
    sd = math.sqrt(sum((d - mu) ** 2 for d in deltas) / (len(deltas) - 1))
    # PIB: crescimento mensal médio dos últimos 12 meses (usa o mês da dívida, ou o último PIB disponível)
    pm = sorted(pib12)
    p_ult = ult if ult in pib12 else pm[-1]
    i = pm.index(p_ult)
    g = (pib12[pm[i]] / pib12[pm[i - 12]]) ** (1 / 12) if i >= 12 else 1.0
    a, m = map(int, ult.split("-"))
    out = []
    for k in range(1, meses_frente + 1):
        mm = m + k
        aa, mm = a + (mm - 1) // 12, (mm - 1) % 12 + 1
        mes = f"{aa}-{mm:02d}"
        d = divida[ult] + mu * k
        faixa = 1.645 * sd * math.sqrt(k)
        pib = pib12[p_ult] * g ** _dist(p_ult, mes)   # o PIB pode já ter meses à frente da dívida
        out.append({"mes": mes, "divida": round(d, 1), "min": round(d - faixa, 1), "max": round(d + faixa, 1),
                    "pib12": round(pib, 1), "pct_pib": round(100 * d / pib, 2),
                    "pct_min": round(100 * (d - faixa) / pib, 2), "pct_max": round(100 * (d + faixa) / pib, 2)})
    return {"base": ult, "janela_meses": janela, "aumento_medio_mes": round(mu, 1), "desvio_mes": round(sd, 1),
            "crescimento_pib_12m": round(100 * (g ** 12 - 1), 2), "meses": out}


def _dist(m1: str, m2: str) -> int:
    a1, b1 = map(int, m1.split("-"))
    a2, b2 = map(int, m2.split("-"))
    return (a2 - a1) * 12 + (b2 - b1)
