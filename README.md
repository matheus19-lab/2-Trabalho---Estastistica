# Trabalho 02 - Estatística UFPI

## Medidas de Posição e Variabilidade Aplicadas a Dados Climáticos

Este projeto analisa dados climáticos de três cidades brasileiras utilizando a API Open-Meteo, aplicando conceitos estatísticos fundamentais como média, mediana, quartis, variância, desvio padrão e coeficiente de variação.

### Cidades Analisadas
- **Porto Alegre (RS)** - Sul do Brasil
- **São Paulo (SP)** - Sudeste do Brasil
- **Picos (PI)** - Nordeste do Brasil

### Período de Análise
22 de junho de 2025 a 19 de setembro de 2025 (90 dias consecutivos)

### Variáveis Climáticas
- **Temperatura média diária** (°C) - `temperature_2m_mean`
- **Precipitação total diária** (mm) - `precipitation_sum`

## Estrutura do Projeto

```
├── trabalho02 analise.py          # Script principal de análise
├── Trabalho 02 (V26).py          # Versão alternativa do script
├── base_climatica.csv           # Dados consolidados (gerado)
├── tabela_resumo.csv            # Medidas estatísticas (gerado)
├── endpoints.txt                # Registro dos endpoints da API (gerado)
└── README.md                    # Este arquivo
```

## Dependências

```bash
pip install pandas numpy matplotlib seaborn openmeteo-requests requests-cache retry-requests
```

## Como Executar

1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

2. Execute o script principal:
   ```bash
   python trabalho02 analise.py
   ```

O script irá:
- Coletar dados climáticos via API Open-Meteo
- Consolidar os dados em uma base única
- Calcular medidas estatísticas para cada cidade e variável
- Salvar os resultados em arquivos CSV

## Medidas Estatísticas Calculadas

Para cada combinação cidade/variável, são calculadas:
- **N**: Número de observações
- **Média**: Valor médio aritmético
- **Mediana**: Valor central
- **Mínimo/Máximo**: Valores extremos
- **Q1/Q3**: Primeiro e terceiro quartis
- **Amplitude**: Diferença entre máximo e mínimo
- **Variância**: Medida de dispersão
- **Desvio Padrão**: Raiz quadrada da variância
- **CV (%)**: Coeficiente de variação (percentual)
- **Outliers**: Número de valores atípicos (critério de Tukey)

## Resultados Esperados

O script gera três arquivos de saída:
1. `base_climatica.csv`: Dados brutos consolidados
2. `tabela_resumo.csv`: Tabela com todas as medidas estatísticas
3. `endpoints.txt`: Log dos endpoints utilizados na API

## Interpretação dos Resultados

- **Temperatura**: Picos apresenta as maiores médias, seguido de São Paulo e Porto Alegre
- **Precipitação**: Porto Alegre tem maior variabilidade, São Paulo valores intermediários, Picos baixíssima precipitação
- **Outliers**: Identificados usando o critério de Tukey (Q3 + 1.5*IQR)

## API Utilizada

- **Open-Meteo Archive API**: https://archive-api.open-meteo.com/v1/archive
- Dados históricos com cache local para evitar requisições repetidas
- Fuso horário: America/Sao_Paulo

## Autor

Universidade Federal do Piauí - UFPI
Curso de Estatística

## Licença

Este projeto é parte de um trabalho acadêmico.
