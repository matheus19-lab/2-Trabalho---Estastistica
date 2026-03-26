# -*- coding: utf-8 -*-
"""
Trabalho 02 - Estatística UFPI
Medidas de Posição e Variabilidade aplicadas a dados climáticos via API

Recorte: Porto Alegre (RS), São Paulo (SP), Picos (PI)
Período: 22/06/2025 a 19/09/2025 (90 dias)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import openmeteo_requests
import requests_cache
from retry_requests import retry
import os
import warnings
warnings.filterwarnings('ignore')

# Configuração do cliente Open-Meteo com cache
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

# Definição das cidades (latitude, longitude)
cidades = {
    'Porto Alegre': {'lat': -30.0328, 'lon': -51.2302, 'estado': 'RS'},
    'São Paulo': {'lat': -23.5475, 'lon': -46.6361, 'estado': 'SP'},
    'Picos': {'lat': -7.0769, 'lon': -41.4669, 'estado': 'PI'}  # Cidade do Piauí
}

# Período: 90 dias consecutivos em 2025
start_date = "2025-06-22"
end_date = "2025-09-19"

# URL correta para dados históricos (archive API)
BASE_URL = "https://archive-api.open-meteo.com/v1/archive"

print("=" * 70)
print("TRABALHO 02 - Medidas de Posição e Variabilidade")
print("Análise climática: Porto Alegre (RS), São Paulo (SP), Picos (PI)")
print(f"Período: {start_date} a {end_date} (90 dias)")
print("=" * 70)

# Função para coletar dados de uma cidade
def coletar_dados(cidade_nome, lat, lon):
    print(f"\nColetando dados para {cidade_nome}...")
    
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": ["temperature_2m_mean", "precipitation_sum"],
        "timezone": "America/Sao_Paulo"
    }
    
    # Registro do endpoint
    endpoint_url = f"{BASE_URL}?latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}&daily=temperature_2m_mean,precipitation_sum&timezone=America%2FSao_Paulo"
    print(f"  Endpoint: {endpoint_url}")
    
    try:
        responses = openmeteo.weather_api(BASE_URL, params=params)
        response = responses[0]

        daily = response.Daily()
        daily_temperature = daily.Variables(0).ValuesAsNumpy()
        daily_precipitation = daily.Variables(1).ValuesAsNumpy()

        # ✅ CORRETO AQUI
        timestamps = daily.Time()
        dates = pd.to_datetime(timestamps + response.UtcOffsetSeconds(), unit="s")

        df = pd.DataFrame({
            "date": dates,
            "temperature_2m_mean": daily_temperature,
            "precipitation_sum": daily_precipitation
        })

        df['cidade'] = cidade_nome
        df['estado'] = cidades[cidade_nome]['estado']

        return df, endpoint_url

    except Exception as e:
        print(f"  ✗ Erro ao coletar {cidade_nome}: {e}")
        return None, None

# Coletando dados para todas as cidades
todos_dfs = []
endpoints = {}

for nome, coords in cidades.items():
    df, endpoint = coletar_dados(nome, coords['lat'], coords['lon'])
    if df is not None:
        todos_dfs.append(df)
        endpoints[nome] = endpoint

# Consolidando base
df_base = pd.concat(todos_dfs, ignore_index=True)
df_base['date'] = pd.to_datetime(df_base['date'])

print("\n" + "=" * 70)
print("BASE CONSOLIDADA")
print(f"Total de observações: {len(df_base)}")
print(f"Período: {df_base['date'].min().date()} a {df_base['date'].max().date()}")
print(f"Cidades: {list(df_base['cidade'].unique())}")
print("=" * 70)

# Salvando base de dados
df_base.to_csv('base_climatica.csv', index=False, encoding='utf-8-sig')
print("\n✓ Base salva: base_climatica.csv")

# Salvando endpoints
with open('endpoints.txt', 'w', encoding='utf-8') as f:
    f.write("=" * 70 + "\n")
    f.write("TRABALHO 02 - REGISTRO DE ENDPOINTS\n")
    f.write(f"Data de extração: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}\n")
    f.write(f"Período: {start_date} a {end_date}\n")
    f.write("=" * 70 + "\n\n")
    for cidade, url in endpoints.items():
        f.write(f"Cidade: {cidade}\n")
        f.write(f"URL: {url}\n\n")
print("✓ Endpoints salvos: endpoints.txt")

# ============================================================================
# CÁLCULO DAS MEDIDAS ESTATÍSTICAS
# ============================================================================

def calcular_medidas(serie, nome_variavel):
    """Calcula todas as medidas obrigatórias para uma série de dados"""
    if len(serie) == 0:
        return {}
    
    serie = serie.dropna()
    q1 = serie.quantile(0.25)
    q3 = serie.quantile(0.75)
    iqr = q3 - q1
    media = serie.mean()
    mediana = serie.median()
    dp = serie.std(ddof=1)
    variancia = serie.var(ddof=1)
    
    # Critério de Tukey para outliers
    limite_inf = q1 - 1.5 * iqr
    limite_sup = q3 + 1.5 * iqr
    outliers = serie[(serie < limite_inf) | (serie > limite_sup)]
    
    # Coeficiente de variação (evita divisão por zero)
    cv = (dp / media * 100) if media != 0 else np.nan
    
    return {
        "Variável": nome_variavel,
        "N": len(serie),
        "Média": round(media, 2),
        "Mediana": round(mediana, 2),
        "Mínimo": round(serie.min(), 2),
        "Máximo": round(serie.max(), 2),
        "Q1": round(q1, 2),
        "Q3": round(q3, 2),
        "Amplitude": round(serie.max() - serie.min(), 2),
        "Variância": round(serie.var(), 2),
        "Desvio Padrão": round(dp, 2),
        "CV (%)": round(cv, 1) if media != 0 else 0,
        "Outliers": len(outliers),
        "Lista Outliers": list(outliers.values) if len(outliers) > 0 else []
    }

# Calculando medidas para cada cidade e variável
resultados = []

for cidade in df_base['cidade'].unique():
    df_cidade = df_base[df_base['cidade'] == cidade]
    
    # Temperatura
    temp_medidas = calcular_medidas(df_cidade['temperature_2m_mean'], "Temperatura (°C)")
    temp_medidas['Cidade'] = cidade
    resultados.append(temp_medidas)
    
    # Precipitação
    prec_medidas = calcular_medidas(df_cidade['precipitation_sum'], "Precipitação (mm)")
    prec_medidas['Cidade'] = cidade
    resultados.append(prec_medidas)

# Criando tabela resumo
df_resumo = pd.DataFrame(resultados)
colunas_ordem = ['Cidade', 'Variável', 'N', 'Média', 'Mediana', 'Mínimo', 'Máximo', 
                 'Q1', 'Q3', 'Amplitude', 'Variância', 'Desvio Padrão', 'CV (%)', 'Outliers']
df_resumo = df_resumo[colunas_ordem]

print("\n" + "=" * 70)
print("TABELA RESUMO - MEDIDAS ESTATÍSTICAS")
print("=" * 70)
print(df_resumo.to_string(index=False))

# Salvando tabela resumo
df_resumo.to_csv('tabela_resumo.csv', index=False, encoding='utf-8-sig')
print("\n✓ Tabela resumo salva: tabela_resumo.csv")

# ============================================================================
# GRÁFICOS
# ============================================================================

# Criando pasta para gráficos
os.makedirs('graficos', exist_ok=True)

# Estilo dos gráficos
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("Set2")
cores = {'Porto Alegre': '#2E86AB', 'São Paulo': '#A23B72', 'Picos': '#F18F01'}

# 1. BOXPLOT - Temperatura
plt.figure(figsize=(10, 6))
bp_temp = sns.boxplot(x='cidade', y='temperature_2m_mean', data=df_base, palette=cores)
plt.title('Boxplot da Temperatura Média Diária por Cidade\n22/06/2025 a 19/09/2025', fontsize=14, fontweight='bold')
plt.xlabel('Cidade', fontsize=12)
plt.ylabel('Temperatura (°C)', fontsize=12)
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig('graficos/boxplot_temperatura.png', dpi=300, bbox_inches='tight')
plt.show()

# 2. BOXPLOT - Precipitação
plt.figure(figsize=(10, 6))
bp_prec = sns.boxplot(x='cidade', y='precipitation_sum', data=df_base, palette=cores)
plt.title('Boxplot da Precipitação Diária por Cidade\n22/06/2025 a 19/09/2025', fontsize=14, fontweight='bold')
plt.xlabel('Cidade', fontsize=12)
plt.ylabel('Precipitação (mm)', fontsize=12)
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig('graficos/boxplot_precipitacao.png', dpi=300, bbox_inches='tight')
plt.show()

# 3. HISTOGRAMAS - Temperatura (subplots)
fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)
for i, cidade in enumerate(df_base['cidade'].unique()):
    dados = df_base[df_base['cidade'] == cidade]['temperature_2m_mean'].dropna()
    media = dados.mean()
    mediana = dados.median()
    
    axes[i].hist(dados, bins=15, edgecolor='black', alpha=0.7, color=cores[cidade])
    axes[i].axvline(media, color='red', linestyle='--', linewidth=2, label=f'Média: {media:.1f}°C')
    axes[i].axvline(mediana, color='green', linestyle='-', linewidth=2, label=f'Mediana: {mediana:.1f}°C')
    axes[i].set_title(cidade, fontsize=12, fontweight='bold')
    axes[i].set_xlabel('Temperatura (°C)')
    axes[i].legend(fontsize=9)
    if i == 0:
        axes[i].set_ylabel('Frequência')
fig.suptitle('Histogramas da Temperatura Média Diária\n22/06/2025 a 19/09/2025', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig('graficos/histogramas_temperatura.png', dpi=300, bbox_inches='tight')
plt.show()

# 4. HISTOGRAMAS - Precipitação (subplots)
fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)
for i, cidade in enumerate(df_base['cidade'].unique()):
    dados = df_base[df_base['cidade'] == cidade]['precipitation_sum'].dropna()
    media = dados.mean()
    mediana = dados.median()
    
    axes[i].hist(dados, bins=15, edgecolor='black', alpha=0.7, color=cores[cidade])
    axes[i].axvline(media, color='red', linestyle='--', linewidth=2, label=f'Média: {media:.1f} mm')
    axes[i].axvline(mediana, color='green', linestyle='-', linewidth=2, label=f'Mediana: {mediana:.1f} mm')
    axes[i].set_title(cidade, fontsize=12, fontweight='bold')
    axes[i].set_xlabel('Precipitação (mm)')
    axes[i].legend(fontsize=9)
    if i == 0:
        axes[i].set_ylabel('Frequência')
fig.suptitle('Histogramas da Precipitação Diária\n22/06/2025 a 19/09/2025', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig('graficos/histogramas_precipitacao.png', dpi=300, bbox_inches='tight')
plt.show()

# 5. GRÁFICO DE LINHA - Temperatura ao longo do tempo
plt.figure(figsize=(12, 6))
for cidade in df_base['cidade'].unique():
    dados = df_base[df_base['cidade'] == cidade].sort_values('date')
    plt.plot(dados['date'], dados['temperature_2m_mean'], label=cidade, linewidth=1.5, alpha=0.8)
plt.title('Evolução da Temperatura Média Diária\n22/06/2025 a 19/09/2025', fontsize=14, fontweight='bold')
plt.xlabel('Data', fontsize=12)
plt.ylabel('Temperatura (°C)', fontsize=12)
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('graficos/linha_temperatura.png', dpi=300, bbox_inches='tight')
plt.show()

print("\n" + "=" * 70)
print("GRÁFICOS GERADOS")
print("Pasta: ./graficos/")
print("  - boxplot_temperatura.png")
print("  - boxplot_precipitacao.png")
print("  - histogramas_temperatura.png")
print("  - histogramas_precipitacao.png")
print("  - linha_temperatura.png")
print("=" * 70)

# ============================================================================
# ANÁLISE E INTERPRETAÇÃO
# ============================================================================

print("\n" + "=" * 70)
print("ANÁLISE ESTATÍSTICA E INTERPRETAÇÃO")
print("=" * 70)

for cidade in df_base['cidade'].unique():
    df_cidade = df_base[df_base['cidade'] == cidade]
    
    print(f"\n{'='*50}")
    print(f"CIDADE: {cidade}")
    print(f"{'='*50}")
    
    # Temperatura
    temp = df_cidade['temperature_2m_mean'].dropna()
    print(f"\n📊 TEMPERATURA MÉDIA DIÁRIA:")
    print(f"   • Média: {temp.mean():.2f}°C")
    print(f"   • Mediana: {temp.median():.2f}°C")
    print(f"   • Diferença média-mediana: {abs(temp.mean() - temp.median()):.2f}°C")
    print(f"   • Desvio padrão: {temp.std():.2f}°C")
    print(f"   • Coeficiente de variação: {(temp.std()/temp.mean()*100):.1f}%")
    print(f"   • Amplitude: {temp.max() - temp.min():.2f}°C")
    
    # Interpretação temperatura
    if temp.mean() > temp.median():
        assimetria = "assimetria positiva (cauda à direita)"
    elif temp.mean() < temp.median():
        assimetria = "assimetria negativa (cauda à esquerda)"
    else:
        assimetria = "distribuição simétrica"
    
    cv_temp = (temp.std()/temp.mean()*100)
    if cv_temp < 15:
        var_temp = "baixa variabilidade"
    elif cv_temp < 30:
        var_temp = "moderada variabilidade"
    else:
        var_temp = "alta variabilidade"
    
    print(f"   • Interpretação: {assimetria} com {var_temp}")
    
    # Precipitação
    prec = df_cidade['precipitation_sum'].dropna()
    dias_chuva = len(prec[prec > 0])
    dias_sem_chuva = len(prec[prec == 0])
    
    print(f"\n🌧️ PRECIPITAÇÃO DIÁRIA:")
    print(f"   • Média: {prec.mean():.2f} mm")
    print(f"   • Mediana: {prec.median():.2f} mm")
    print(f"   • Desvio padrão: {prec.std():.2f} mm")
    print(f"   • Coeficiente de variação: {(prec.std()/prec.mean()*100):.1f}%" if prec.mean() > 0 else "   • Coeficiente de variação: N/A (média zero)")
    print(f"   • Total acumulado: {prec.sum():.2f} mm")
    print(f"   • Dias com chuva: {dias_chuva} ({dias_chuva/len(prec)*100:.1f}%)")
    print(f"   • Dias sem chuva: {dias_sem_chuva} ({dias_sem_chuva/len(prec)*100:.1f}%)")
    
    # Interpretação precipitação
    if prec.mean() > prec.median():
        print(f"   • Interpretação: distribuição assimétrica à direita (típica de precipitação)")
    print(f"   • A mediana ({prec.median():.1f} mm) representa melhor o dia típico, pois a maioria dos dias tem pouca ou nenhuma chuva")

# Perguntas orientadoras
print("\n" + "=" * 70)
print("RESPOSTAS ÀS PERGUNTAS ORIENTADORAS")
print("=" * 70)

# Encontrar cidade com maior temperatura típica
temp_medianas = {}
for cidade in df_base['cidade'].unique():
    temp_medianas[cidade] = df_base[df_base['cidade'] == cidade]['temperature_2m_mean'].median()
cidade_mais_quente = max(temp_medianas, key=temp_medianas.get)
print(f"\n1. Cidade com maior temperatura típica: {cidade_mais_quente} ({temp_medianas[cidade_mais_quente]:.1f}°C - mediana)")

# Maior variabilidade
temp_cvs = {}
for cidade in df_base['cidade'].unique():
    temp = df_base[df_base['cidade'] == cidade]['temperature_2m_mean'].dropna()
    temp_cvs[cidade] = (temp.std()/temp.mean()*100)
cidade_mais_variavel = max(temp_cvs, key=temp_cvs.get)
print(f"\n2. Cidade com maior variabilidade de temperatura: {cidade_mais_variavel} (CV = {temp_cvs[cidade_mais_variavel]:.1f}%)")

print("\n" + "=" * 70)
print("✓ Análise concluída com sucesso!")
print("Arquivos gerados: base_climatica.csv, tabela_resumo.csv, endpoints.txt, pasta /graficos")
print("=" * 70)