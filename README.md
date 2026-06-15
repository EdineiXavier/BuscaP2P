Autores: Edinei Xavier - 2310369 \
Autores: Matheus Norões - 2224600 \
Autores: Lucas Falcão - 2315036 \
Autores: Samir Alves - 2315046

# Implementação de Algoritmos de Busca em Sistemas P2P

## Resumo

Este trabalho implementa e compara quatro algoritmos de busca em redes **peer-to-peer (P2P) não estruturadas** — **Flooding**, **Random Walk**, **Informed Flooding** e **Informed Random Walk** — por meio de um simulador desenvolvido em **Python**. O simulador lê arquivos de configuração de rede em formato **YAML**, valida a topologia e permite executar buscas de forma interativa, com visualização gráfica animada e geração de gráficos comparativos.

## Infraestrutura

- **Python 3.11+**: linguagem de implementação do simulador
- **PyYAML**: leitura dos arquivos de configuração da rede
- **NetworkX**: modelagem e layout do grafo da rede P2P
- **Matplotlib**: visualização gráfica da rede e animação das buscas
- **Estrutura de arquivos**:

## Serviço Implementado

O simulador modela uma rede P2P não estruturada onde cada nó possui um conjunto de recursos. As operações disponíveis são:

| Operação | Descrição |
|---|---|
| Carregar rede | Lê e valida um arquivo YAML de configuração |
| Buscar recurso | Executa um dos quatro algoritmos de busca |
| Visualizar rede | Exibe graficamente a topologia da rede |
| Animar busca | Anima passo a passo a propagação das mensagens |

O arquivo de configuração define a topologia da rede:

```yaml
num_nodes: 6
min_neighbors: 1
max_neighbors: 4

resources:
  n1: "r1, r2"
  n2: "r3"
  ...

edges:
  - "n1, n2"
  - "n1, n3"
  ...
```

Após carregar o arquivo, o programa valida quatro condições obrigatórias: a rede não pode estar particionada, cada nó deve respeitar os limites de vizinhos, nenhum nó pode estar sem recursos e não pode haver arestas de um nó para si mesmo.

## Algoritmos Implementados

### Flooding (Busca por Inundação)

A requisição é enviada simultaneamente a **todos os vizinhos** do nó origem. Cada vizinho repassa para os seus vizinhos, e assim por diante, em camadas (BFS). O TTL é decrementado a cada salto e, quando chega a zero, a mensagem é descartada. Garante encontrar o recurso se o TTL for suficiente, mas gera alto tráfego de mensagens.

### Random Walk (Passeio Aleatório)

A requisição é enviada a **um único vizinho escolhido aleatoriamente** a cada passo. O processo repete até encontrar o recurso ou o TTL zerar. Gera muito menos tráfego que o flooding, mas é probabilístico — pode dar voltas (backtracking) e não garante encontrar o recurso.

### Informed Flooding (Inundação Informada)

Variação do flooding onde cada nó mantém um **cache local** com a localização de recursos já descobertos. Antes de propagar a busca, o nó consulta seu cache — se souber onde o recurso está, vai direto sem inundar a rede. O cache é populado ao longo das buscas, tornando buscas futuras pelo mesmo recurso muito mais eficientes.

### Informed Random Walk (Passeio Aleatório Informado)

Variação do random walk com o mesmo mecanismo de cache. Antes de cada salto aleatório, o nó consulta seu cache. Se a localização do recurso for conhecida, vai direto para o nó correto com apenas 1 mensagem.

## Metodologia

Os testes comparam os quatro algoritmos em três topologias de rede distintas, sempre buscando o recurso mais distante do nó de origem. Os parâmetros de cada busca são:

| Parâmetro | Descrição |
|---|---|
| `node_id` | Nó que inicia a busca |
| `resource_id` | Recurso a ser localizado |
| `ttl` | Número máximo de saltos permitidos |
| `algo` | Algoritmo de busca utilizado |

As métricas coletadas foram: número total de mensagens trocadas, número de nós envolvidos, caminho percorrido e taxa de sucesso (para algoritmos probabilísticos, média de 30 execuções).

## Resultados e Discussão

### Tabela Geral — Comparação Direta (cache frio, 1ª busca)

| Algoritmo | Rede Pequena (6n) | Rede Média (12n) | Rede Grande (20n) |
|---|---|---|---|
| Flooding | 6 msgs | 17 msgs | 31 msgs |
| Random Walk | ~8 msgs (57% sucesso) | ~8 msgs (57% sucesso) | ~14 msgs (13% sucesso) |
| Inf. Flooding | 6 msgs | 17 msgs | 31 msgs |
| Inf. Random Walk | ~7 msgs (70% sucesso) | ~8 msgs (50% sucesso) | ~14 msgs (13% sucesso) |

### Tabela — Efeito do Cache (1ª vs 2ª busca)

| Par de algoritmos | 1ª Busca | 2ª Busca | Redução |
|---|---|---|---|
| Flooding → Inf. Flooding (pequena) | 6 msgs | 1 msg | 85% |
| Flooding → Inf. Flooding (média) | 17 msgs | 1 msg | 94% |
| Flooding → Inf. Flooding (grande) | 31 msgs | 1 msg | 97% |
| Random Walk → Inf. Random Walk (pequena) | 10 msgs | 1 msg | 90% |
| Random Walk → Inf. Random Walk (média) | 4 msgs | 1 msg | 75% |
| Random Walk → Inf. Random Walk (grande) | 14 msgs | 1 msg | 93% |

### Taxa de Erros

A taxa de erros foi **0% em todos os cenários** para os algoritmos determinísticos (flooding e informed flooding), para todas as redes e valores de TTL suficientes. O random walk e o informed random walk são probabilísticos por natureza — na rede grande com TTL=15, a taxa de sucesso ficou em apenas 13%, demonstrando a limitação desses algoritmos em redes maiores sem TTL elevado.

### Principais Observações

O **Flooding** garante encontrar o recurso com TTL suficiente, mas escala linearmente com o tamanho da rede: 6 → 17 → 31 mensagens nas redes pequena, média e grande. O **Random Walk** usa bem menos mensagens quando encontra o recurso, mas paga o preço na confiabilidade — especialmente em redes grandes. O efeito do **cache** é o resultado mais expressivo: independentemente do algoritmo base, a segunda busca pelo mesmo recurso custa sempre **1 mensagem**, com reduções de 75% a 97%.

## Conclusão

Os testes demonstraram diferenças expressivas entre os algoritmos, especialmente em redes maiores e com TTL variável.

O **Flooding** é o algoritmo mais confiável — garante encontrar o recurso desde que o TTL seja maior ou igual ao diâmetro da rede — mas é o mais custoso em tráfego, com crescimento linear no número de mensagens conforme a rede cresce.

O **Random Walk** reduz drasticamente o tráfego quando bem-sucedido, mas é fundamentalmente probabilístico. Na rede grande com TTL=15, encontrou o recurso em apenas 13% das execuções, tornando-o inadequado para redes grandes sem um TTL muito elevado.

O **Informed Flooding** e o **Informed Random Walk** demonstraram o maior ganho prático do trabalho: após a primeira busca popular o cache, todas as buscas subsequentes pelo mesmo recurso custam apenas **1 mensagem**, independentemente do tamanho da rede. Isso representa reduções de até 97% no tráfego em relação à busca sem cache.

Quanto à escolha do algoritmo, o flooding é ideal quando é necessário garantir a localização do recurso. O random walk é adequado em redes pequenas ou quando o tráfego é o fator crítico e a probabilidade de sucesso é aceitável. Os algoritmos informados são sempre preferíveis quando há repetição de buscas pelos mesmos recursos — que é o caso mais comum em sistemas P2P reais.