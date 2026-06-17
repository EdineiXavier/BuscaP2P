Autores: Edinei Xavier - 2310369 \
Autores: Matheus Norões - 2224600 \
Autores: Lucas Falcão - 2315036 \
Autores: Samir Alves - 2315046

# Implementação de Algoritmos de Busca em Sistemas P2P

## Resumo

Este trabalho implementa e compara quatro algoritmos de busca em redes **peer-to-peer (P2P) não estruturadas** - **Flooding**, **Random Walk**, **Informed Flooding** e **Informed Random Walk** - por meio de um simulador desenvolvido em **Python**. O simulador lê arquivos de configuração de rede em formato **YAML**, valida a topologia e permite executar buscas de forma interativa, com visualização gráfica animada e geração de gráficos comparativos.

## Infraestrutura

- **Python 3.11+**: linguagem de implementação do simulador
- **PyYAML**: leitura dos arquivos de configuração da rede
- **NetworkX**: modelagem e layout do grafo da rede P2P
- **Matplotlib**: visualização gráfica da rede e animação das buscas

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
num_nodes: 8
min_neighbors: 2
max_neighbors: 3

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

A requisição é enviada simultaneamente a **todos os vizinhos** do nó origem. Cada vizinho repassa para os seus vizinhos em camadas (BFS), decrementando o TTL a cada salto. Quando um nó encontra o recurso, para de propagar - mas os demais nós da mesma rodada **não sabem que o recurso foi encontrado** e continuam propagando normalmente até o TTL zerar, refletindo o comportamento real de uma rede P2P onde as mensagens trafegam de forma independente. Garante encontrar o recurso se o TTL for suficiente, mas gera alto tráfego de mensagens.

### Random Walk (Passeio Aleatório com Backtracking)

A requisição caminha pela rede escolhendo aleatoriamente entre os **vizinhos ainda não visitados** a cada passo, consumindo 1 TTL por avanço. Quando não há vizinhos não visitados disponíveis **ou o TTL chega a zero**, o algoritmo realiza backtracking: volta ao nó anterior **recuperando +1 TTL**, e tenta os vizinhos não visitados desse nó. Esse processo se repete até encontrar o recurso ou esgotar todas as possibilidades alcançáveis dentro do TTL. Dessa forma, o algoritmo **garante encontrar o recurso** se existir um caminho alcançável com o TTL fornecido, explorando todas as combinações possíveis de forma aleatória via DFS com backtracking.

### Informed Flooding (Inundação Informada)

Variação do flooding onde cada nó mantém um **cache local** com a localização de recursos já descobertos. Antes de propagar a busca, o nó consulta seu cache - se souber onde o recurso está e o nó cacheado for vizinho direto, vai direto sem inundar a rede. O cache é populado ao longo das buscas, tornando buscas futuras pelo mesmo recurso muito mais eficientes.

### Informed Random Walk (Passeio Aleatório Informado)

Variação do random walk com o mesmo mecanismo de cache. Antes de cada avanço, o nó consulta seu cache. Se a localização do recurso for conhecida e o nó cacheado for vizinho direto, vai direto com apenas 1 mensagem, sem precisar fazer o caminhamento aleatório.

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

### Tabela Geral - Comparação Direta (cache frio, 1ª busca)

| Algoritmo | Rede Pequena (8n) | Rede Média (12n) | Rede Grande (20n) |
|---|---|---|---|
| Flooding | 6 msgs | 17 msgs | 31 msgs |
| Random Walk | ~8 msgs | ~8 msgs | ~14 msgs |
| Inf. Flooding | 6 msgs | 17 msgs | 31 msgs |
| Inf. Random Walk | ~7 msgs | ~8 msgs | ~14 msgs |

### Tabela - Efeito do Cache (1ª vs 2ª busca)

| Par de algoritmos | 1ª Busca | 2ª Busca | Redução |
|---|---|---|---|
| Flooding → Inf. Flooding (pequena) | 6 msgs | 1 msg | 85% |
| Flooding → Inf. Flooding (média) | 17 msgs | 1 msg | 94% |
| Flooding → Inf. Flooding (grande) | 31 msgs | 1 msg | 97% |
| Random Walk → Inf. Random Walk (pequena) | 10 msgs | 1 msg | 90% |
| Random Walk → Inf. Random Walk (média) | 4 msgs | 1 msg | 75% |
| Random Walk → Inf. Random Walk (grande) | 14 msgs | 1 msg | 93% |

### Principais Observações

O **Flooding** garante encontrar o recurso com TTL suficiente, mas escala linearmente com o tamanho da rede: 6 → 17 → 31 mensagens nas redes pequena, média e grande. O custo adicional do flooding em relação ao esperado vem da **propagação paralela**: quando um nó encontra o recurso, os demais nós da mesma rodada continuam propagando até o TTL zerar, pois não sabem que o recurso já foi achado.

O **Random Walk** explora a rede de forma aleatória via DFS com backtracking, garantindo encontrar o recurso se ele for alcançável. O número de mensagens varia conforme a ordem aleatória de exploração - no melhor caso vai direto ao recurso, no pior caso explora todos os caminhos possíveis antes de chegar ao destino.

O efeito do **cache** é o resultado mais expressivo: independentemente do algoritmo base, a segunda busca pelo mesmo recurso custa sempre **1 mensagem**, com reduções de 75% a 97%.

## Conclusão

Os testes demonstraram diferenças expressivas entre os algoritmos, especialmente em redes maiores e com TTL variável.

O **Flooding** é o algoritmo mais confiável em termos de cobertura - garante encontrar o recurso desde que o TTL seja suficiente - mas é o mais custoso em tráfego. Um aspecto importante do comportamento real do flooding é que, ao encontrar o recurso, os demais nós em propagação paralela não são notificados imediatamente e continuam buscando até o TTL zerar, o que aumenta o custo total de mensagens.

O **Random Walk** implementado utiliza DFS com backtracking: avança aleatoriamente entre vizinhos não visitados consumindo TTL, e ao zerar o TTL retrocede ao nó anterior recuperando o TTL gasto. Isso garante que o algoritmo explore todas as possibilidades alcançáveis dentro do TTL, encontrando o recurso se ele for alcançável. A aleatoriedade influencia apenas a ordem de exploração - e portanto o número de mensagens - não a capacidade de encontrar o recurso.

O **Informed Flooding** e o **Informed Random Walk** demonstraram o maior ganho prático do trabalho: após a primeira busca popular o cache, todas as buscas subsequentes pelo mesmo recurso custam apenas **1 mensagem**, independentemente do tamanho da rede. Isso representa reduções de até 97% no tráfego em relação à busca sem cache.

Quanto à escolha do algoritmo, o flooding é ideal quando é necessário garantir a localização do recurso com TTL controlado. O random walk é adequado quando o tráfego paralelo é o fator crítico, pois explora um caminho por vez. Os algoritmos informados são sempre preferíveis quando há repetição de buscas pelos mesmos recursos 0 - que é o caso mais comum em sistemas P2P reais.