import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coletor import bcb, calculos  # noqa: E402

CSV = """CRONOGRAMA DE VENCIMENTOS - TÍTULOS FEDERAIS NO MERCADO
DATA DE REFERENCIA: 19/11/2026
VALORES EM MILHÕES DE REAIS
VENCIMENTO;LTN;LFT;NTN-B;NTN-B1;NTN-C;NTN-F;NTN-I;NTN-P;TOTAL;PART %
23/11/2026;-;-;-;-;-;-;-;-;0;0,00
01/01/2027;5637;-;-;-;-;114261;-;1;119899;1,30
01/03/2027;-;591322;-;-;-;-;-;-;591322;6,43
15/08/2028;-;-;231763;-;-;-;25;-;231788;2,52
"""


def test_cronograma_soma_por_ano_e_titulo():
    c = bcb.ler_cronograma(CSV)
    assert c["referencia"] == "2026-11-19"
    assert c["por_ano"]["2027"]["total"] == 119899 + 591322
    assert c["por_ano"]["2027"]["LFT"] == 591322
    assert c["por_titulo"]["NTN-B"] == 231763
    assert c["total"] == 119899 + 591322 + 231788
    assert "2026" not in c["por_ano"]          # vencimento zerado não conta
    assert [v["data"] for v in c["proximos"]] == ["2027-01-01", "2027-03-01"]


def test_soma_12_exige_os_12_meses():
    s = {f"2025-{m:02d}": 1.0 for m in range(1, 13)}
    assert calculos.soma_12(s, "2025-12") == 12
    assert calculos.soma_12(s, "2026-01") is None


def test_projecao_ritmo_medio():
    div = {f"2025-{m:02d}": 100.0 + 10 * m for m in range(1, 13)} | {"2024-12": 100.0}
    pib = {f"2024-{m:02d}": 1000.0 for m in range(1, 13)} | {f"2025-{m:02d}": 1000.0 for m in range(1, 13)}
    p = calculos.projecao(div, pib, meses_frente=3)
    assert p["aumento_medio_mes"] == 10
    assert p["meses"][0] == {"mes": "2026-01", "divida": 230.0, "min": 230.0, "max": 230.0, "pib12": 1000.0,
                             "pct_pib": 23.0, "pct_min": 23.0, "pct_max": 23.0}
    assert p["meses"][2]["mes"] == "2026-03"


def test_montar_bancos_junta_cadastro_e_colunas():
    cad = [{"CodInst": "111", "NomeInstituicao": "BANCO A S.A.", "SegmentoTb": "Banco Múltiplo", "Tc": 2, "Sr": "S1",
            "CodConglomeradoPrudencial": "C1", "CnpjInstituicaoLider": "111"},
           {"CodInst": "222", "NomeInstituicao": "BANCO B", "SegmentoTb": "Banco Comercial", "Tc": 1, "Sr": "S3"}]
    val = {"2": [{"CodInst": "C1", "NomeColuna": "Títulos e Valores Mobiliários \n(c)", "Saldo": 5_000_000},
                 {"CodInst": "C1", "NomeColuna": "Ativo Total \n(k) = (a) + (b)", "Saldo": 9_000_000},
                 {"CodInst": "222", "NomeColuna": "Títulos e Valores Mobiliários \n(c)", "Saldo": 7_000_000}],
           "4": [{"CodInst": "C1", "NomeColuna": "Rendas de Títulos e Valores Mobiliários  (b)", "Saldo": 300_000}]}
    b = bcb.montar_bancos(cad, val)
    assert [x["cod"] for x in b] == ["222", "C1"]          # ordem: maior carteira de títulos
    c1 = b[1]
    assert c1["nome"] == "BANCO A S.A." and c1["controle"] == "Privado nacional" and c1["segmento"] == "Banco Múltiplo"
    assert c1["tvm"] == 5000 and c1["ativo"] == 9000 and c1["renda_tvm"] == 300   # R$ mil -> R$ milhões
    assert b[0]["controle"] == "Público"


def test_periodos_ifdata():
    from datetime import date
    assert bcb.ifdata_periodos(date(2026, 11, 24), 3) == ["202609", "202606", "202603"]
    assert bcb.ifdata_periodos(date(2026, 2, 1), 2) == ["202512", "202509"]
