"""Quanto Custa — Dívida Pública (configuração)."""

USER_AGENT = "QuantoCusta/1.0 (painel de transparencia com dados abertos)"
PAUSA_ENTRE_REQUISICOES = 0.5

# --- Banco Central: Sistema Gerenciador de Séries Temporais (SGS) ---
# Cada código foi conferido no catálogo de dados abertos do Banco Central (dadosabertos.bcb.gov.br).
SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json&dataInicial={ini}"
SGS_ULTIMO = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados/ultimos/1?formato=json"

# séries mensais: chave no site -> (código SGS, descrição oficial, unidade)
SERIES = {
    # dívida bruta do governo geral (DBGG) — metodologia a partir de 2008 (série começa em dez/2006)
    "dbgg": (13761, "Dívida bruta do governo geral - Saldos em R$ milhões", "R$ milhões"),
    "dbgg_pib": (13762, "Dívida bruta do governo geral (% PIB) - Metodologia utilizada a partir de 2008", "% PIB"),
    # dívida líquida do setor público (DLSP)
    "dlsp": (4478, "Dívida Líquida do Setor Público - Saldos em R$ milhões - Total - Setor público consolidado", "R$ milhões"),
    "dlsp_pib": (4513, "Dívida Líquida do Setor Público (% PIB) - Total - Setor público consolidado", "% PIB"),
    "dlsp_gf": (4469, "DLSP - Saldos em R$ milhões - Governo Federal", "R$ milhões"),
    "dlsp_bc": (4470, "DLSP - Saldos em R$ milhões - Banco Central", "R$ milhões"),
    "dlsp_est": (4472, "DLSP - Saldos em R$ milhões - Governos estaduais", "R$ milhões"),
    "dlsp_mun": (4473, "DLSP - Saldos em R$ milhões - Governos municipais", "R$ milhões"),
    "dlsp_estatais": (4474, "DLSP - Saldos em R$ milhões - Empresas estatais", "R$ milhões"),
    "dlgg_pib": (4536, "Dívida líquida do governo geral (% PIB)", "% PIB"),
    # juros nominais (NFSP sem desvalorização cambial), fluxo mensal, R$ milhões
    "juros": (4616, "NFSP - Fluxo mensal corrente - Juros nominais - Setor público consolidado", "R$ milhões"),
    "juros_gf": (4607, "NFSP - Fluxo mensal - Juros nominais - Governo Federal", "R$ milhões"),
    "juros_bc": (4608, "NFSP - Fluxo mensal - Juros nominais - Banco Central", "R$ milhões"),
    "juros_est": (4610, "NFSP - Fluxo mensal - Juros nominais - Governos estaduais", "R$ milhões"),
    "juros_mun": (4611, "NFSP - Fluxo mensal - Juros nominais - Governos municipais", "R$ milhões"),
    "juros_estatais": (4612, "NFSP - Fluxo mensal - Juros nominais - Empresas estatais", "R$ milhões"),
    "juros_pib12": (5760, "NFSP (% PIB) - Fluxo acumulado em 12 meses - Juros nominais - Setor público consolidado", "% PIB"),
    # resultado primário e nominal (NFSP: positivo = déficit, negativo = superávit)
    "primario": (4649, "NFSP - Fluxo mensal corrente - Resultado primário - Setor público consolidado", "R$ milhões"),
    "nominal": (4583, "NFSP - Fluxo mensal corrente - Resultado nominal - Setor público consolidado", "R$ milhões"),
    "primario_pib12": (5793, "NFSP (% PIB) - 12 meses - Resultado primário - Setor público consolidado", "% PIB"),
    "nominal_pib12": (5727, "NFSP (% PIB) - 12 meses - Resultado nominal - Setor público consolidado", "% PIB"),
    # PIB acumulado nos últimos 12 meses (valores correntes), usado pelo Banco Central nas razões dívida/PIB
    "pib12": (4382, "PIB acumulado dos últimos 12 meses - Valores correntes", "R$ milhões"),
    # juros básicos e inflação
    "selic": (4189, "Taxa de juros - Selic acumulada no mês anualizada base 252", "% ao ano"),
    "ipca": (433, "Índice nacional de preços ao consumidor-amplo (IPCA)", "% no mês"),
    # dívida mobiliária federal (títulos do Tesouro)
    "dpmf_emitido": (4151, "Dívida mobiliária - Títulos do Tesouro Nacional - Total emitido", "R$ milhões"),
    "dpmf_mercado": (4154, "Dívida mobiliária - Títulos do Tesouro Nacional - Total em mercado", "R$ milhões"),
    "dpmf_bc": (4152, "Dívida mobiliária - Títulos do Tesouro Nacional - Carteira do Banco Central", "R$ milhões"),
    "prazo_medio": (10618, "Dívida mobiliária federal - Títulos do Tesouro Nacional - Emitidos - Prazo médio - Total", "meses"),
    # participação por indexador (% da dívida mobiliária em mercado)
    "idx_selic": (4177, "Participação por indexador - Over/Selic", "%"),
    "idx_pre": (4178, "Participação por indexador - Prefixado", "%"),
    "idx_ipca": (12001, "Participação por indexador - Índice de preços (IPCA)", "%"),
    "idx_cambio": (4173, "Participação por indexador - Câmbio", "%"),
    "idx_tr": (4174, "Participação por indexador - TR", "%"),
    "idx_igpm": (4175, "Participação por indexador - IGP-M", "%"),
    "idx_igpdi": (4176, "Participação por indexador - IGP-DI", "%"),
    "idx_outros": (4180, "Participação por indexador - Outros", "%"),
}
SERIE_INICIO = "01/12/2001"
SELIC_META = 432   # meta Selic definida pelo Copom (diária; só o último valor)

# --- Banco Central: cronograma de vencimentos dos títulos federais em mercado (Demab) ---
CRONOGRAMA = ("https://www4.bcb.gov.br/pom/demab/cronograma/vencdata_csv.asp"
              "?data={data}&abertura=anos&indice=todos&formato=milhoes")

# --- Banco Central: IF.data (balanço de cada banco e financeira, trimestral) ---
IFDATA = "https://olinda.bcb.gov.br/olinda/servico/IFDATA/versao/v1/odata"
IFDATA_TIPO = 1   # 1 = conglomerados prudenciais e instituições independentes (como o IF.data mostra)

# --- Banco Central: Focus (expectativas de mercado) ---
FOCUS = ("https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais"
         "?$top=400&$orderby=Data%20desc&$format=json&$filter=startswith(Indicador,'D%C3%ADvida')")

# --- IBGE: população (projeção do dia) ---
POPULACAO = "https://servicodados.ibge.gov.br/api/v1/projecoes/populacao"
POPULACAO_RESERVA = 213_421_037   # estimativa oficial do IBGE para 1º/7/2025 (DOU, ago/2025), usada se a API não responder
