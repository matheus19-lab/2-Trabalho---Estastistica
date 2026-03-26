"""
================================================================================
  Trabalho 02 — Medidas de Posição e Variabilidade
  Disciplina de Estatística — UFPI · Sistemas de Informação
  Professor: Dr. Francisco Airton Pereira da Silva
================================================================================

  Script auxiliar para:
    1. Coleta de dados via Open-Meteo Historical Weather API
    2. Organização da base em CSV
    3. Cálculo de todas as medidas obrigatórias
    4. Geração dos gráficos (histogramas e boxplots)
    5. Exportação da tabela resumo

  COMO USAR:
    1. Instale as dependências:  pip install requests pandas matplotlib seaborn
    2. Configure as CIDADES e o PERÍODO na seção "Configuração do grupo"
    3. Execute:  python trabalho02.py
    4. Os arquivos serão salvos na pasta "saida/"

  IMPORTANTE: substitua as cidades, coordenadas e período pelo recorte do SEU grupo.
  Os dados aqui são apenas exemplos — cada grupo deve usar suas próprias cidades.
================================================================================
"""

import os
import json
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from datetime import date

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÃO DO GRUPO — edite esta seção
# ─────────────────────────────────────────────────────────────────────────────

# Defina as 3 cidades do seu grupo.
# Pelo menos 1 deve ser do Piauí.
# Fonte de coordenadas: https://www.latlong.net ou Google Maps (clique com botão direito)

CIDADES = [
    {
        "nome":      "Teresina",          # Nome para exibição nos gráficos
        "latitude":  -5.0892,             # Latitude (negativo = Sul)
        "longitude": -42.8019,            # Longitude (negativo = Oeste)
        "estado":    "PI",
    },
    {
        "nome":      "Fortaleza",
        "latitude":  -3.7319,
        "longitude": -38.5267,
        "estado":    "CE",
    },
    {
        "nome":      "Belém",
        "latitude":  -1.4558,
        "longitude": -48.5044,
        "estado":    "PA",
    },
]

# Período: exatamente 90 dias consecutivos em 2025
# Adapte conforme o recorte do seu grupo
DATA_INICIO = "2025-01-01"
DATA_FIM    = "2025-03-31"   # 31 de março = 90 dias a partir de 1º de janeiro

# Variáveis a coletar (obrigatórias + opcionais)
# Variáveis disponíveis: https://open-meteo.com/en/docs#hourly
VARIAVEIS_DIARIAS = [
    "temperature_2m_mean",    # Temperatura média diária (°C) — OBRIGATÓRIA
    "temperature_2m_max",     # Temperatura máxima diária (°C) — opcional
    "temperature_2m_min",     # Temperatura mínima diária (°C) — opcional
    "precipitation_sum",      # Precipitação acumulada diária (mm) — OBRIGATÓRIA
]

# Pasta de saída
PASTA_SAIDA = "saida"

# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÕES DE COLETA
# ─────────────────────────────────────────────────────────────────────────────

BASE_URL = "https://archive-api.open-meteo.com/v1/archive"

def construir_endpoint(cidade):
    """Retorna a URL completa para a cidade fornecida."""
    params = {
        "latitude":   cidade["latitude"],
        "longitude":  cidade["longitude"],
        "start_date": DATA_INICIO,
        "end_date":   DATA_FIM,
        "daily":      ",".join(VARIAVEIS_DIARIAS),
        "timezone":   "America/Sao_Paulo",
    }
    req = requests.Request("GET", BASE_URL, params=params)
    prepared = req.prepare()
    return prepared.url


def coletar_cidade(cidade):
    """
    Consulta a API e retorna um DataFrame com as colunas:
      data | cidade | temperature_2m_mean | precipitation_sum | ...
    """
    url = construir_endpoint(cidade)
    print(f"  → Coletando {cidade['nome']} ({cidade['estado']})...")
    print(f"    Endpoint: {url}")

    resp = requests.get(BASE_URL, params={
        "latitude":   cidade["latitude"],
        "longitude":  cidade["longitude"],
        "start_date": DATA_INICIO,
        "end_date":   DATA_FIM,
        "daily":      ",".join(VARIAVEIS_DIARIAS),
        "timezone":   "America/Sao_Paulo",
    }, timeout=30)

    if resp.status_code != 200:
        raise RuntimeError(
            f"Erro ao coletar {cidade['nome']}: status {resp.status_code}\n{resp.text}"
        )

    dados = resp.json()
    daily = dados.get("daily", {})

    df = pd.DataFrame(daily)
    df.rename(columns={"time": "data"}, inplace=True)
    df["data"]   = pd.to_datetime(df["data"])
    df["cidade"] = cidade["nome"]
    df["estado"] = cidade["estado"]

    # Reordena colunas
    colunas_fixas = ["data", "cidade", "estado"]
    colunas_dados = [c for c in df.columns if c not in colunas_fixas]
    df = df[colunas_fixas + colunas_dados]

    print(f"    ✓ {len(df)} dias coletados, {df.isnull().sum().sum()} valores faltantes")
    return df, url


def coletar_todos():
    """Coleta dados de todas as cidades e concatena em um único DataFrame."""
    frames = []
    endpoints = {}

    for cidade in CIDADES:
        df, url = coletar_cidade(cidade)
        frames.append(df)
        endpoints[cidade["nome"]] = url

    base = pd.concat(frames, ignore_index=True)
    return base, endpoints


# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÕES DE ANÁLISE
# ─────────────────────────────────────────────────────────────────────────────

def calcular_medidas(serie):
    """
    Recebe uma pd.Series numérica e retorna um dicionário com todas as
    medidas obrigatórias do Trabalho 02.
    """
    q1 = serie.quantile(0.25)
    q3 = serie.quantile(0.75)
    iqr = q3 - q1
    media = serie.mean()
    dp = serie.std(ddof=1)

    # Outliers pelo critério de Tukey
    limite_inf = q1 - 1.5 * iqr
    limite_sup = q3 + 1.5 * iqr
    n_outliers = int(((serie < limite_inf) | (serie > limite_sup)).sum())

    return {
        "N":          int(serie.count()),
        "Média":      round(media, 2),
        "Mediana":    round(serie.median(), 2),
        "Mínimo":     round(serie.min(), 2),
        "Máximo":     round(serie.max(), 2),
        "Q1":         round(q1, 2),
        "Q3":         round(q3, 2),
        "Amplitude":  round(serie.max() - serie.min(), 2),
        "Variância":  round(serie.var(ddof=1), 2),
        "DP":         round(dp, 2),
        "CV (%)":     round((dp / media) * 100, 1) if media != 0 else None,
        "IQR":        round(iqr, 2),
        "Outliers":   n_outliers,
    }


def tabela_resumo(base):
    """
    Calcula as medidas para temperatura e precipitação em cada cidade.
    Retorna um DataFrame no formato longo, adequado para inserção no artigo.
    """
    variaveis = {
        "temperature_2m_mean": "Temperatura média (°C)",
        "precipitation_sum":   "Precipitação (mm)",
    }

    linhas = []
    for cidade in base["cidade"].unique():
        sub = base[base["cidade"] == cidade]
        for col, rotulo in variaveis.items():
            if col not in sub.columns:
                continue
            m = calcular_medidas(sub[col].dropna())
            m["Cidade"]   = cidade
            m["Variável"] = rotulo
            linhas.append(m)

    df_resumo = pd.DataFrame(linhas)
    # Reordena colunas
    cols_id   = ["Cidade", "Variável"]
    cols_med  = [c for c in df_resumo.columns if c not in cols_id]
    return df_resumo[cols_id + cols_med]


# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÕES DE VISUALIZAÇÃO
# ─────────────────────────────────────────────────────────────────────────────

# Paleta consistente com os slides da disciplina
CORES_CIDADES = ["#B04A2F", "#4E7C6C", "#B07D2A"]
ESTILO = {
    "font.family":   "DejaVu Sans",
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "axes.grid":         True,
    "grid.alpha":        0.3,
    "grid.linestyle":    "--",
}
plt.rcParams.update(ESTILO)


def histogramas_temperatura(base, pasta):
    """
    Histograma da temperatura média diária para cada cidade,
    com linha vertical de média (vermelho) e mediana (verde).
    """
    cidades = base["cidade"].unique()
    fig, axes = plt.subplots(1, len(cidades), figsize=(5 * len(cidades), 4.5), sharey=False)
    if len(cidades) == 1:
        axes = [axes]

    fig.suptitle(
        f"Temperatura Média Diária por Cidade\n{DATA_INICIO} a {DATA_FIM}",
        fontsize=13, fontweight="bold", color="#1C2E45", y=1.02
    )

    for ax, cidade, cor in zip(axes, cidades, CORES_CIDADES):
        dados = base[base["cidade"] == cidade]["temperature_2m_mean"].dropna()
        media  = dados.mean()
        mediana = dados.median()

        ax.hist(dados, bins=15, color=cor, alpha=0.75, edgecolor="white", linewidth=0.8)
        ax.axvline(media,   color="#B04A2F", linewidth=2, linestyle="--", label=f"Média: {media:.1f}°C")
        ax.axvline(mediana, color="#4E7C6C", linewidth=2, linestyle="-",  label=f"Mediana: {mediana:.1f}°C")

        ax.set_title(cidade, fontsize=12, fontweight="bold", color="#1C2E45")
        ax.set_xlabel("Temperatura (°C)")
        ax.set_ylabel("Frequência" if ax == axes[0] else "")
        ax.legend(fontsize=9)

    fig.tight_layout()
    caminho = os.path.join(pasta, "hist_temperatura.png")
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → Histograma de temperatura salvo: {caminho}")
    return caminho


def histogramas_precipitacao(base, pasta):
    """
    Histograma da precipitação diária para cada cidade.
    A precipitação costuma ser fortemente assimétrica à direita.
    """
    cidades = base["cidade"].unique()
    fig, axes = plt.subplots(1, len(cidades), figsize=(5 * len(cidades), 4.5))
    if len(cidades) == 1:
        axes = [axes]

    fig.suptitle(
        f"Precipitação Diária por Cidade\n{DATA_INICIO} a {DATA_FIM}",
        fontsize=13, fontweight="bold", color="#1C2E45", y=1.02
    )

    for ax, cidade, cor in zip(axes, cidades, CORES_CIDADES):
        dados = base[base["cidade"] == cidade]["precipitation_sum"].dropna()
        media   = dados.mean()
        mediana = dados.median()

        ax.hist(dados, bins=15, color=cor, alpha=0.75, edgecolor="white", linewidth=0.8)
        ax.axvline(media,   color="#B04A2F", linewidth=2, linestyle="--", label=f"Média: {media:.1f} mm")
        ax.axvline(mediana, color="#4E7C6C", linewidth=2, linestyle="-",  label=f"Mediana: {mediana:.1f} mm")

        ax.set_title(cidade, fontsize=12, fontweight="bold", color="#1C2E45")
        ax.set_xlabel("Precipitação (mm)")
        ax.set_ylabel("Frequência" if ax == axes[0] else "")
        ax.legend(fontsize=9)

    fig.tight_layout()
    caminho = os.path.join(pasta, "hist_precipitacao.png")
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → Histograma de precipitação salvo: {caminho}")
    return caminho


def boxplot_temperatura(base, pasta):
    """
    Boxplot comparativo de temperatura entre as três cidades.
    Permite comparar centro, dispersão e outliers diretamente.
    """
    fig, ax = plt.subplots(figsize=(8, 5))

    dados_plot = [
        base[base["cidade"] == c]["temperature_2m_mean"].dropna().values
        for c in base["cidade"].unique()
    ]
    nomes = list(base["cidade"].unique())

    bp = ax.boxplot(
        dados_plot,
        labels=nomes,
        patch_artist=True,
        medianprops=dict(color="#B04A2F", linewidth=2.5),
        flierprops=dict(marker="o", markerfacecolor="#B04A2F", markersize=5, alpha=0.6),
        whiskerprops=dict(linewidth=1.5),
        capprops=dict(linewidth=1.5),
    )
    for patch, cor in zip(bp["boxes"], CORES_CIDADES):
        patch.set_facecolor(cor)
        patch.set_alpha(0.6)

    ax.set_title(
        f"Temperatura Média Diária — Comparativo entre Cidades\n{DATA_INICIO} a {DATA_FIM}",
        fontsize=12, fontweight="bold", color="#1C2E45"
    )
    ax.set_ylabel("Temperatura (°C)")
    ax.set_xlabel("Cidade")

    fig.tight_layout()
    caminho = os.path.join(pasta, "boxplot_temperatura.png")
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → Boxplot de temperatura salvo: {caminho}")
    return caminho


def boxplot_precipitacao(base, pasta):
    """
    Boxplot comparativo de precipitação entre as três cidades.
    Atenção a pontos acima do bigode — são dias de chuva intensa.
    """
    fig, ax = plt.subplots(figsize=(8, 5))

    dados_plot = [
        base[base["cidade"] == c]["precipitation_sum"].dropna().values
        for c in base["cidade"].unique()
    ]
    nomes = list(base["cidade"].unique())

    bp = ax.boxplot(
        dados_plot,
        labels=nomes,
        patch_artist=True,
        medianprops=dict(color="#4E7C6C", linewidth=2.5),
        flierprops=dict(marker="o", markerfacecolor="#B04A2F", markersize=5, alpha=0.6),
        whiskerprops=dict(linewidth=1.5),
        capprops=dict(linewidth=1.5),
    )
    for patch, cor in zip(bp["boxes"], CORES_CIDADES):
        patch.set_facecolor(cor)
        patch.set_alpha(0.6)

    ax.set_title(
        f"Precipitação Diária — Comparativo entre Cidades\n{DATA_INICIO} a {DATA_FIM}",
        fontsize=12, fontweight="bold", color="#1C2E45"
    )
    ax.set_ylabel("Precipitação (mm)")
    ax.set_xlabel("Cidade")

    fig.tight_layout()
    caminho = os.path.join(pasta, "boxplot_precipitacao.png")
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → Boxplot de precipitação salvo: {caminho}")
    return caminho


def grafico_linha_temperatura(base, pasta):
    """
    Gráfico de linha da temperatura ao longo do período — opcional,
    mas útil para verificar tendências sazonais.
    """
    fig, ax = plt.subplots(figsize=(11, 4.5))

    for cidade, cor in zip(base["cidade"].unique(), CORES_CIDADES):
        sub = base[base["cidade"] == cidade].sort_values("data")
        ax.plot(sub["data"], sub["temperature_2m_mean"], label=cidade,
                color=cor, linewidth=1.5, alpha=0.85)

    ax.set_title(
        f"Temperatura Média Diária ao Longo do Período\n{DATA_INICIO} a {DATA_FIM}",
        fontsize=12, fontweight="bold", color="#1C2E45"
    )
    ax.set_xlabel("Data")
    ax.set_ylabel("Temperatura (°C)")
    ax.legend()
    ax.xaxis.set_major_locator(mticker.MaxNLocator(8))
    fig.autofmt_xdate()

    fig.tight_layout()
    caminho = os.path.join(pasta, "linha_temperatura.png")
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → Gráfico de linha salvo: {caminho}")
    return caminho


# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÃO DE EXPORTAÇÃO
# ─────────────────────────────────────────────────────────────────────────────

def salvar_endpoint(endpoints, pasta):
    """Salva os endpoints usados em arquivo .txt para entrega."""
    caminho = os.path.join(pasta, "endpoints.txt")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("TRABALHO 02 — REGISTRO DE ENDPOINTS\n")
        f.write(f"Data de extração: {date.today().isoformat()}\n")
        f.write(f"Período: {DATA_INICIO} a {DATA_FIM}\n")
        f.write("=" * 70 + "\n\n")
        for cidade, url in endpoints.items():
            f.write(f"Cidade: {cidade}\n")
            f.write(f"URL:    {url}\n\n")
    print(f"  → Endpoints salvos: {caminho}")


def salvar_tabela_resumo(resumo, pasta):
    """Salva a tabela resumo em CSV e exibe no terminal."""
    caminho = os.path.join(pasta, "tabela_resumo.csv")
    resumo.to_csv(caminho, index=False, encoding="utf-8-sig")
    print(f"  → Tabela resumo salva: {caminho}")

    # Exibe também no terminal de forma legível
    print("\n" + "=" * 70)
    print("TABELA RESUMO — MEDIDAS OBRIGATÓRIAS")
    print("=" * 70)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 120)
    pd.set_option("display.float_format", "{:.2f}".format)
    print(resumo.to_string(index=False))
    print("=" * 70 + "\n")


def imprimir_interpretacoes(base, resumo):
    """
    Imprime no terminal um guia de interpretação baseado nos dados reais,
    ajudando o grupo a redigir o artigo.
    """
    print("\n" + "=" * 70)
    print("GUIA DE INTERPRETAÇÃO — responda estas questões no artigo")
    print("=" * 70)

    temp = resumo[resumo["Variável"].str.contains("Temperatura")]
    prec = resumo[resumo["Variável"].str.contains("Precipitação")]

    # Pergunta 1: maior temperatura típica
    cidade_maior_temp = temp.loc[temp["Mediana"].idxmax(), "Cidade"]
    mediana_max = temp["Mediana"].max()
    print(f"\n1. Maior temperatura típica (mediana): {cidade_maior_temp} ({mediana_max:.1f}°C)")

    # Pergunta 2: divergência média × mediana
    print("\n2. Divergência média × mediana na temperatura:")
    for _, row in temp.iterrows():
        dif = abs(row["Média"] - row["Mediana"])
        sinal = "↑ assimétrica à direita" if row["Média"] > row["Mediana"] else \
                "↓ assimétrica à esquerda" if row["Média"] < row["Mediana"] else "≈ simétrica"
        print(f"   {row['Cidade']}: Média={row['Média']:.1f}, Mediana={row['Mediana']:.1f}, "
              f"Diferença={dif:.1f}°C → {sinal}")

    # Pergunta 3: maior variabilidade de temperatura (CV)
    cidade_maior_cv = temp.loc[temp["CV (%)"].idxmax(), "Cidade"]
    cv_max = temp["CV (%)"].max()
    print(f"\n3. Maior variabilidade de temperatura (CV): {cidade_maior_cv} (CV={cv_max:.1f}%)")
    nivel = "alta (>30%)" if cv_max > 30 else "média (15–30%)" if cv_max > 15 else "baixa (<15%)"
    print(f"   → Variabilidade {nivel}")

    # Pergunta 4: precipitação
    print("\n4. Precipitação — dias com chuva zero por cidade:")
    for cidade in base["cidade"].unique():
        sub = base[base["cidade"] == cidade]["precipitation_sum"].dropna()
        dias_zero = int((sub == 0).sum())
        pct_zero  = dias_zero / len(sub) * 100
        print(f"   {cidade}: {dias_zero} dias sem chuva ({pct_zero:.0f}% do período)")

    # Pergunta 5: outliers
    print("\n5. Outliers (critério de Tukey) por cidade e variável:")
    for _, row in resumo.iterrows():
        if row["Outliers"] > 0:
            print(f"   {row['Cidade']} — {row['Variável']}: {row['Outliers']} outlier(s)")
    outliers_total = resumo["Outliers"].sum()
    if outliers_total == 0:
        print("   Nenhum outlier detectado nas variáveis principais.")

    # Pergunta 7: qual medida recomendar
    print("\n7. Recomendação de medida por variável:")
    for _, row in temp.iterrows():
        dif = abs(row["Média"] - row["Mediana"])
        rec = "Mediana" if dif > 1.0 else "Média"
        print(f"   {row['Cidade']} — Temperatura: use {rec} (diferença: {dif:.1f}°C)")
    for _, row in prec.iterrows():
        print(f"   {row['Cidade']} — Precipitação: use Mediana "
              f"(assimetria esperada em precipitação)")

    print("\n" + "=" * 70)
    print("Esses valores devem aparecer no artigo com interpretação contextual.")
    print("=" * 70 + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# EXECUÇÃO PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 70)
    print("TRABALHO 02 — Medidas de Posição e Variabilidade")
    print("Disciplina de Estatística — UFPI · Sistemas de Informação")
    print("=" * 70 + "\n")

    # Cria pasta de saída
    os.makedirs(PASTA_SAIDA, exist_ok=True)

    # ── Etapa 1: Coleta ───────────────────────────────────────────────────
    print("ETAPA 1 — Coletando dados da Open-Meteo API...")
    base, endpoints = coletar_todos()

    print(f"\n  Base consolidada: {len(base)} observações, {base.shape[1]} colunas")
    print(f"  Cidades: {list(base['cidade'].unique())}")
    print(f"  Período: {base['data'].min().date()} a {base['data'].max().date()}")
    print(f"  Valores faltantes: {base.isnull().sum().sum()}")

    # ── Salva base bruta ──────────────────────────────────────────────────
    caminho_base = os.path.join(PASTA_SAIDA, "base_climatica.csv")
    base.to_csv(caminho_base, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    print(f"  → Base salva: {caminho_base}")

    salvar_endpoint(endpoints, PASTA_SAIDA)

    # ── Etapa 2: Medidas ──────────────────────────────────────────────────
    print("\nETAPA 2 — Calculando medidas obrigatórias...")
    resumo = tabela_resumo(base)
    salvar_tabela_resumo(resumo, PASTA_SAIDA)

    # ── Etapa 3: Gráficos ─────────────────────────────────────────────────
    print("ETAPA 3 — Gerando gráficos...")
    histogramas_temperatura(base, PASTA_SAIDA)
    histogramas_precipitacao(base, PASTA_SAIDA)
    boxplot_temperatura(base, PASTA_SAIDA)
    boxplot_precipitacao(base, PASTA_SAIDA)
    grafico_linha_temperatura(base, PASTA_SAIDA)

    # ── Etapa 4: Guia de interpretação ───────────────────────────────────
    print("\nETAPA 4 — Guia de interpretação para o artigo...")
    imprimir_interpretacoes(base, resumo)

    # ── Resumo final ──────────────────────────────────────────────────────
    print("=" * 70)
    print("CONCLUÍDO! Arquivos gerados em:", os.path.abspath(PASTA_SAIDA))
    print("-" * 70)
    for f in sorted(os.listdir(PASTA_SAIDA)):
        print(f"  {f}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
