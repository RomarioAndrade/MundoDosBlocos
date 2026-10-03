# Mundo dos Blocos de Tamanho Variável: planejamento com SAT

Fundamentos de Inteligência Artificial (IComp/UFAM), 1º Trabalho

Equipe X:

- Gabriel Menezes Rodrigues (gabriel.menezes@icomp.ufam.edu.br)
- Luiz Felipe Gonzaga do Carmo (luiz.carmo@icomp.ufam.edu.br)
- Joshua Tadeu Bastos Pereira (joshua.pereira@icomp.ufam.edu.br)
- Romário Roberto de Pádua Andrade (romario.andrade@icomp.ufam.edu.br)

Resolvemos os três cenários do enunciado:

| Cenário | Início | Meta | Menor plano |
|---|---|---|---|
| Situação 1 | S0 | Sf4 | 4 ações |
| Situação 2 | S0 da Situação 2 | S5 | 5 ações |
| Situação 3 | S0 da Situação 3 (igual ao S0 da Situação 1) | S7 | 6 ações |

Como o enunciado permite, usamos um chatbot de IA (Claude) para ajudar a escrever o código
Python e a montar os planos. Conferimos todos os planos passo a passo e também com o SAT.

O relatório completo em LaTeX está em [`latex/main.tex`](latex/main.tex) (PDF: `latex/main.pdf`).

## Estrutura da pasta

```
TrabalhoIA_MundoBloclos_equipe_X/
├── README.md                  este arquivo (explicação em Markdown)
├── bw2cnf_var.py              descrição formal -> CNF (.cnf + .map)
├── interpretar.py             saída do miniSAT -> plano em português
├── cenario1/                  Situação 1: S0 -> Sf4
│   ├── trab01_blocos2SAT.cnf
│   ├── trab01_blocos2SAT.map
│   ├── resultado1.txt         saída do miniSAT
│   ├── saida_gerador.txt      saída do bw2cnf_var.py
│   ├── saida_minisat.txt      saída do miniSAT (estatísticas)
│   └── plano_interpretado.txt saída do interpretar.py --verbose
├── cenario2/                  Situação 2: S0 -> S5   (mesmos arquivos, resultado2.txt)
├── cenario3/                  Situação 3: S0 -> S7   (mesmos arquivos, resultado3.txt)
└── latex/
    ├── main.tex               relatório (7 seções pedidas)
    └── main.pdf
```

## Como executar

```bash
sudo apt install minisat
for N in 1 2 3; do
  cd cenario$N
  python3 ../bw2cnf_var.py --cenario $N         # gera .cnf e .map
  minisat trab01_blocos2SAT.cnf resultado$N.txt
  python3 ../interpretar.py resultado$N.txt --verbose
  cd ..
done
```

O número de passos de cada cenário é o `HORIZON` no dicionário `CENARIOS` do `bw2cnf_var.py`.
Para conferir que o plano é o menor possível, basta diminuir esse valor em 1 (por exemplo, de
4 para 3 na Situação 1), gerar a CNF de novo e rodar o miniSAT. Ele tem que responder
UNSATISFIABLE. Depois é só voltar o valor original.

## 1. Introdução ao problema

No Mundo dos Blocos clássico todos os blocos têm o mesmo tamanho. Aqui eles têm comprimentos
diferentes (a e b = 1, c = 2, d = 3) e a mesa tem 6 espaços, chamados de *slots*. Por isso
também é preciso saber em que posição da mesa cada bloco está. Isso traz situações que não
aparecem no caso clássico: espaços vazios, pontes (um bloco comprido apoiado em dois
menores), equilíbrio (um bloco maior em cima de um menor) e movimentos laterais.

O objetivo é achar um plano, isto é, uma sequência de ações que leve do estado inicial ao
estado meta:

```
Situação 1        S0                              Sf4
  nivel 1 | . . . d d d                nivel 1 | a . . . . .
  nivel 0 | c c . a . b      ---->     nivel 0 | c c d d d b

Situação 2        S0                              S5
  nivel 2 | . . . . . .                nivel 2 | . . . . a b
  nivel 1 | a b . . . .      ---->     nivel 1 | . . . . c c
  nivel 0 | c c . d d d                nivel 0 | . . . d d d

Situação 3        S0                              S7
  nivel 1 | . . . d d d                nivel 1 | a b . . . .
  nivel 0 | c c . a . b      ---->     nivel 0 | c c . d d d
     slots  0 1 2 3 4 5                   slots  0 1 2 3 4 5
```

- Na Situação 1 escolhemos a meta Sf4 porque ela tem o plano mais curto (4 ações). Para Sf1
  são necessárias 9 ações, e para Sf2 e Sf3 são 10.
- O enunciado pede "S0 até S5" e "S0 até S7". Entendemos que S5 e S7 são os estados finais
  das Situações 2 e 3, e que cada uma começa no seu próprio S0. Se o S0 do item 2 for o da
  Situação 1, a meta S5 fica igual a Sf2 e o menor plano tem 10 ações. Também testamos esse
  caso no SAT.

## 2. Descrição formal (Lógica de Primeira Ordem)

### 2.1 Domínio

- Blocos `B = {a, b, c, d}`, comprimento `ℓ(a)=ℓ(b)=1, ℓ(c)=2, ℓ(d)=3`.
- Pontos `0..6` e slots `s0..s5` (o slot `si` é o intervalo `[i, i+1]`).
- Níveis `0..3` (0 = sobre a mesa `T`) e instantes `t = 0..H`.
- `span(b,p) = {p, …, p+ℓ(b)−1}`: slots cobertos por `b` começando em `p`, com `p ∈ {0, …, 6−ℓ(b)}`.

Notação: a mesa é `T`. No relatório em LaTeX o número de passos do plano (o horizonte) é `H`.
Neste README e nas saídas dos programas o horizonte aparece como `T` (por exemplo `T=4`).

### 2.2 Predicados e axiomas

| Predicado | Significado | Tipo |
|---|---|---|
| `at(b,p,t)` | b começa no ponto p | básico |
| `lev(b,l,t)` | b está no nível l | básico |
| `cov(b,s,l,t)` | b cobre o slot s no nível l | calculado |
| `livre(s,l,t)` | nenhum bloco cobre s no nível l | calculado |
| `esp(b,s,t)` | (novo) há espaço livre em cima de b, no slot s | calculado |
| `clr(b,t)` | nada em cima de b (espaço livre em todos os slots) | calculado |
| `on(b,y,t)` | b apoiado em y (1 ou 2 apoios = ponte) | calculado |

Para saber como o mundo está em um instante basta guardar `at` e `lev` de cada bloco. Os
outros predicados são calculados a partir desses dois, usando as regras abaixo.

```
A1  ∀b,t ∃!p at(b,p,t)        ∀b,t ∃!l lev(b,l,t)                        (unicidade)
A2  cov(b,s,l,t) ↔ lev(b,l,t) ∧ ∃p (at(b,p,t) ∧ s ∈ span(b,p))
A3  b ≠ b' → ¬(cov(b,s,l,t) ∧ cov(b',s,l,t))                               (exclusão)
A4  livre(s,l,t) ↔ ¬∃b cov(b,s,l,t)
A5a esp(b,s,t) ↔ ∃l (cov(b,s,l,t) ∧ livre(s,l+1,t))                       (espaço: predicado novo)
A5b clr(b,t) ↔ ∀s,l (cov(b,s,l,t) → esp(b,s,t))                            (clear)
A6  on(b,T,t) ↔ lev(b,0,t)
    on(b,y,t) ↔ ∃p,q,l at(b,p,t) ∧ at(y,q,t) ∧ lev(b,l,t) ∧ lev(y,l−1,t) ∧ overlap(b,p,y,q)
A7  at(b,p,t) ∧ lev(b,l,t) ∧ l>0 → |{s ∈ span(b,p) : ¬livre(s,l−1,t)}| ≥ ⌈ℓ(b)/2⌉   (estabilidade)
```

O predicado `esp` é novo. Ele funciona como um `clr` que olha um slot de cada vez:
`esp(b,s)` é verdadeiro quando não tem nada em cima de `b` no slot `s`. Já o `clr(b)` só é
verdadeiro quando todos os slots de `b` estão sem nada em cima (A5b).

A regra A7 trata do equilíbrio. Um bloco que está em cima de outro precisa ter pelo menos
metade dos seus slots apoiados: `a`, `b` e `c` precisam de 1 slot apoiado e `d` precisa de 2.
É por isso que a ponte de S0 é válida: `d` está apoiado em `a` e em `b`, mesmo com o slot
`s4` vazio embaixo dele.

### 2.3 A ação `move(b, y, p)`

"Mover `b` para cima de `y` (ou da mesa `T`), começando no ponto `p`."
`(p0, l0)` = posição atual de `b`; `l*` = nível de chegada (`0` se `y = T`, `lev(y)+1` se `y` é bloco).

Pré-condições (todas têm que ser verdadeiras):

| | Condição |
|---|---|
| P1 | `clr(b)`: não pode ter nada em cima de `b` |
| P2 | se `y` é um bloco, pelo menos um slot de `b` tem que cair sobre um slot de `y`, e nesses slots tem que haver espaço livre em cima de `y` (`esp(y,s)`), sem contar o próprio `b`. Esta condição entra no lugar do `clr(y)` do mundo clássico |
| P3 | o destino tem que ser diferente do lugar atual: `(p, l*) ≠ (p0, l0)` |
| P4 | os slots de destino têm que estar livres no nível `l*` (sem contar o próprio `b`) |
| P5 | regra da sombra: não pode ter nenhum bloco acima dos slots de destino |
| P6 | `l* ≤ 3`, para não passar do último nível |

A estabilidade (A7) não aparece como pré-condição porque ela já vale para todos os estados.
Se o movimento deixasse o bloco sem apoio suficiente, o estado de chegada não seria permitido.

Efeitos (estilo STRIPS). Aqui `z` é o bloco onde `b` estava apoiado e `y'` é o bloco onde `b`
fica apoiado depois.

Passa a valer (ADD):

- a nova posição de `b`: `at(b,p)` e `lev(b,l*)`;
- os slots que `b` passa a cobrir: `cov(b,s,l*)`;
- os novos apoios: `on(b,y')` (podem ser dois, quando `b` forma uma ponte);
- os slots que `b` deixou ficam livres: `livre(s,l0)`;
- o bloco `z` ganha espaço em cima nesses slots, `esp(z,s)`, e fica com `clr(z)` se não
  sobrou nada em cima dele.

Deixa de valer (DEL):

- a posição antiga de `b`: `at(b,p0)`, `lev(b,l0)` e `cov(b,s,l0)`;
- os apoios antigos: `on(b,z)`;
- os slots que `b` passou a ocupar deixam de estar livres: `livre(s,l*)`;
- o bloco `y'` perde o espaço em cima nesses slots, `esp(y',s)`, e perde `clr(y')`.

### 2.4 Elementos novos e as ações associadas (item 2)

| Elemento | Para que serve | `move` adiciona | `move` remove |
|---|---|---|---|
| `ℓ(b)` | tamanho | não muda | não muda |
| `at(b,p)` | posição horizontal | destino | origem |
| `lev(b,l)` | altura | `l*` | `l0` |
| `cov(b,s,l)` | ocupação de slots | novo span | span antigo |
| `livre(s,l)` | espaços vazios | slots que b deixou | slots que b ocupou |
| `esp(b,s)` (novo) | pode receber um bloco no slot s? | slots do antigo apoio que b deixou | slots do novo apoio onde b pousou |
| `clr(b)` | pode ser movido? | antigo apoio descoberto | cada novo apoio |
| `on(b,y)` | apoio / ponte | novos apoios | apoios antigos |
| estabilidade | equilíbrio | restrição no estado de chegada | |
| sombra | espaço sob bloco suspenso | pré-condição P5 | |

### 2.5 Ajustes em relação ao mundo clássico

Antes de resolver os cenários, testamos as regras nas figuras do enunciado. Vimos que as pré-condições do mundo clássico
não são suficientes para blocos de tamanhos diferentes e fizemos dois ajustes.

1. Um predicado novo no lugar de `clr(y)`. No mundo clássico, para colocar `b` em cima de `y`
   é preciso `clr(y)`. Lá isso funciona, porque só cabe um bloco em cima de outro. Aqui cabem
   dois blocos pequenos lado a lado em cima de `c`. Depois que `a` vai para cima de `c`,
   `clr(c)` fica falso, e a regra clássica não deixa `b` ir para o lado de `a`, mesmo tendo
   espaço. Com a regra clássica, Sf1, Sf2, o S5 da Situação 2 e o S7 da Situação 3 não podem
   ser alcançados. Fizemos o teste colocando `clr(y)` como pré-condição na nossa CNF: a
   Situação 1 continua com 4 ações, mas as Situações 2 e 3 dão UNSAT em todos os valores de
   T que testamos (0 a 12). Por isso criamos o predicado `esp(y,s,t)`, que significa "há
   espaço livre em cima de `y` no slot `s`" (A5a). Com ele ficamos com duas condições:
   - `clr(b)` diz que não tem nada em cima do bloco inteiro. É a condição para mover `b` (P1);
   - `esp(y,s)` diz que não tem nada em cima de `y` só naquele slot. É a condição para `y`
     receber um bloco (P2).

   O `clr` continua existindo com o mesmo significado. Ele só passou a ser escrito usando o
   `esp` (A5b).
2. Regra da sombra (P5). Com blocos de tamanhos diferentes pode sobrar um espaço vazio embaixo
   de um bloco. Em S0, por exemplo, o slot `s4` fica embaixo da ponte `d`. As outras
   pré-condições não impedem que um bloco seja colocado nesse tipo de espaço. Sem uma regra
   para isso, seria possível ir de S0 a Sf3 em 2 ações (`move(d,c,0)` e `move(a,T,2)`), enfiando `a` embaixo da parte de `d` que
   fica para fora de `c`. Por isso incluímos a pré-condição P5.

Com os dois ajustes, cada passo desenhado nas figuras das Situações 2 e 3 pode ser feito com
uma única ação válida.

### 2.6 Execução manual (item 3)

#### Situação 1: S0 → Sf4

```
t=0  S0                               A1 = move(d,c,0): d para cima de c, em p=0
  nivel 1 | . . . d d d               PRE  clr(d); span(d,0)={0,1,2} sobrepõe span(c,0)={0,1};
  nivel 0 | c c . a . b                    s0..s2 livres no nível 1; estável (c apoia s0,s1: 2 ≥ 2)
                                      ADD  at(d,0), on(d,c), clr(a), clr(b), livre(s3..s5,1)
                                      DEL  at(d,3), on(d,a), on(d,b), clr(c), livre(s0..s2,1)

t=1  S1                               A2 = move(a,b,5): a para cima de b, em p=5
  nivel 1 | d d d . . .               PRE  clr(a) (liberado por A1); {5} sobrepõe span(b,5);
  nivel 0 | c c . a . b                    s5 livre no nível 1; estável (b apoia s5)
                                      ADD  at(a,5), lev(a,1), on(a,b), livre(s3,0)
                                      DEL  at(a,3), lev(a,0), on(a,T), clr(b), livre(s5,1)

t=2  S2                               A3 = move(d,T,2): d para a mesa, em p=2
  nivel 1 | d d d . . a               PRE  clr(d); s2,s3,s4 livres no nível 0 (s3 liberado por A2)
  nivel 0 | c c . . . b                    e acima (a está em s5, fora do span)
                                      ADD  at(d,2), lev(d,0), on(d,T), clr(c), livre(s0..s2,1)
                                      DEL  at(d,0), lev(d,1), on(d,c), livre(s2..s4,0)

t=3  S3                               A4 = move(a,c,0): a para cima de c, em p=0
  nivel 1 | . . . . . a               PRE  clr(a); {0} ⊂ span(c,0); s0 livre no nível 1 (liberado
  nivel 0 | c c d d d b                    por A3); estável (c apoia s0)
                                      ADD  at(a,0), on(a,c), clr(b), livre(s5,1)
                                      DEL  at(a,5), on(a,b), clr(c), livre(s0,1)

t=4  S4 = Sf4  ✓
  nivel 1 | a . . . . .
  nivel 0 | c c d d d b
```

Por que 4 ações é o mínimo: o primeiro movimento de `d` não pode ser para o lugar final,
porque `a` ocupa `s3`. Também não pode ser para a mesa, porque não há 3 slots livres
seguidos. Então `d` vai primeiro para cima de `c` e se move pelo menos 2 vezes. O `a` precisa
sair de `s3` enquanto `c` ainda está coberto por `d`, então também se move pelo menos 2
vezes. Somando, são pelo menos 4 ações. No SAT, T=3 dá UNSAT.


#### Situação 2: S0 → S5

O plano manual é o da própria figura do enunciado, com 5 ações:

```
t=0  S0                               B1 = move(b,T,2): b para a mesa, em p=2
  nivel 1 | a b . . . .               PRE  clr(b); s2 livre no nível 0 e acima
  nivel 0 | c c . d d d               ADD  at(b,2), lev(b,0), on(b,T), livre(s1,1)
                                      DEL  at(b,1), lev(b,1), on(b,c), livre(s2,0)

t=1  S1                               B2 = move(a,b,2): a para cima de b, em p=2
  nivel 1 | a . . . . .               PRE  clr(a); {2} sobrepõe span(b,2); s2 livre no nível 1;
  nivel 0 | c c b d d d                    estável (b apoia s2)
                                      ADD  at(a,2), on(a,b), clr(c), livre(s0,1)
                                      DEL  at(a,0), on(a,c), clr(b), livre(s2,1)

t=2  S2                               B3 = move(c,d,4): c para cima de d, em p=4
  nivel 1 | . . a . . .               PRE  clr(c) (a e b saíram); {4,5} ⊂ span(d,3);
  nivel 0 | c c b d d d                    s4, s5 livres no nível 1; estável (2 ≥ 1)
                                      ADD  at(c,4), lev(c,1), on(c,d), livre(s0,0), livre(s1,0)
                                      DEL  at(c,0), lev(c,0), on(c,T), clr(d), livre(s4..s5,1)

t=3  S3                               B4 = move(a,c,4): a para cima de c, em p=4
  nivel 1 | . . a . c c               PRE  clr(a); {4} ⊂ span(c,4); s4 livre no nível 2; estável
  nivel 0 | . . b d d d               ADD  at(a,4), lev(a,2), on(a,c), clr(b), livre(s2,1)
                                      DEL  at(a,2), lev(a,1), on(a,b), clr(c), livre(s4,2)

t=4  S4                               B5 = move(b,c,5): b para cima de c, em p=5
  nivel 2 | . . . . a .               PRE  clr(b) (liberado por B4); {5} ⊂ span(c,4);
  nivel 1 | . . . . c c                    s5 livre no nível 2; estável.
  nivel 0 | . . b d d d                    clr(c) é FALSO (tem a em cima), mas esp(c,s5) é verdadeiro
                                      ADD  at(b,5), lev(b,2), on(b,c), livre(s2,0)
                                      DEL  at(b,2), lev(b,0), on(b,T), livre(s5,2)

t=5  S5 ✓
  nivel 2 | . . . . a b
  nivel 1 | . . . . c c
  nivel 0 | . . . d d d
```

Por que 5 ações é o mínimo: `c` tem que ir para cima de `d` (pelo menos 1 ação). Mas `a` e
`b` estão em cima de `c` e terminam de novo em cima de `c`. Cada um tem que sair antes de `c`
se mover e voltar depois, então cada um se move pelo menos 2 vezes. Somando, são pelo menos
5 ações. No SAT, T=4 dá UNSAT. Existe mais de um plano com 5 ações, e o SAT devolveu um
que não é o da figura (seção 7).

#### Situação 3: S0 → S7

O plano manual tem 6 ações. O S0 é o mesmo da Situação 1 e os quatro primeiros passos são os
mesmos do plano de lá. Depois deles o estado é S4 = Sf4. Na figura do enunciado, S5 e S6 são
iguais, então tratamos os dois como um estado só.

```
t=0  S0                               C1 = move(d,c,0): d para cima de c, em p=0
  nivel 1 | . . . d d d               PRE  clr(d); span(d,0)={0,1,2} sobrepõe span(c,0)={0,1};
  nivel 0 | c c . a . b                    s0..s2 livres no nível 1; estável (c apoia s0,s1: 2 ≥ 2)
                                      ADD  at(d,0), on(d,c), clr(a), clr(b), livre(s3..s5,1)
                                      DEL  at(d,3), on(d,a), on(d,b), clr(c), livre(s0..s2,1)

t=1  S1                               C2 = move(a,b,5): a para cima de b, em p=5
  nivel 1 | d d d . . .               PRE  clr(a) (liberado por C1); {5} sobrepõe span(b,5);
  nivel 0 | c c . a . b                    s5 livre no nível 1; estável (b apoia s5)
                                      ADD  at(a,5), lev(a,1), on(a,b), livre(s3,0)
                                      DEL  at(a,3), lev(a,0), on(a,T), clr(b), livre(s5,1)

t=2  S2                               C3 = move(d,T,2): d para a mesa, em p=2
  nivel 1 | d d d . . a               PRE  clr(d); s2,s3,s4 livres no nível 0 (s3 liberado por C2)
  nivel 0 | c c . . . b                    e acima (a está em s5, fora do span)
                                      ADD  at(d,2), lev(d,0), on(d,T), clr(c), livre(s0..s2,1)
                                      DEL  at(d,0), lev(d,1), on(d,c), livre(s2..s4,0)

t=3  S3                               C4 = move(a,c,0): a para cima de c, em p=0
  nivel 1 | . . . . . a               PRE  clr(a); {0} ⊂ span(c,0); s0 livre no nível 1 (liberado
  nivel 0 | c c d d d b                    por C3); estável (c apoia s0)
                                      ADD  at(a,0), on(a,c), clr(b), livre(s5,1)
                                      DEL  at(a,5), on(a,b), clr(c), livre(s0,1)

t=4  S4 = Sf4                         C5 = move(b,c,1): b para cima de c, em p=1
  nivel 1 | a . . . . .               PRE  clr(b) (a saiu de b em C4); {1} ⊂ span(c,0);
  nivel 0 | c c d d d b                    s1 livre no nível 1; estável.
                                           clr(c) é FALSO (tem a em cima), mas esp(c,s1) é verdadeiro
                                      ADD  at(b,1), lev(b,1), on(b,c), livre(s5,0)
                                      DEL  at(b,5), lev(b,0), on(b,T), livre(s1,1)

t=5  S5 = S6                          C6 = move(d,T,3): d desliza para p=3 (movimento lateral)
  nivel 1 | a b . . . .               PRE  clr(d); s3, s4, s5 livres no nível 0 sem contar o próprio d
  nivel 0 | c c d d d .                    (s5 liberado em C5) e acima
                                      ADD  at(d,3), livre(s2,0)
                                      DEL  at(d,2), livre(s5,0)

t=6  S7 ✓
  nivel 1 | a b . . . .
  nivel 0 | c c . d d d
```

Por que 6 ações é o mínimo: (1) o primeiro movimento de `d` não pode ser para o lugar final,
porque `a` ocupa `s3` e `b` ocupa `s5`. Também não pode ser para outro lugar da mesa, porque
não há 3 slots livres seguidos. Então `d` vai primeiro para cima de `c` e se move pelo menos 2
vezes. (2) `a` precisa sair de `s3` antes de `d` descer para a mesa, mas nesse momento `c` está
coberto por `d`, então o primeiro movimento de `a` não é o final. Logo `a` também se move pelo
menos 2 vezes. (3) `b` tem que ir para cima de `c`, e `d` só pode ir para p=3 depois que `s5`
ficar livre. Se `b` se move uma vez só, `d` precisa de um terceiro movimento. Se `d` se move
só duas vezes, `b` precisa de um movimento a mais para sair do caminho. Nos dois casos são
pelo menos 6 ações. No SAT, T=5 dá UNSAT.

### 2.7 Ordem parcial (item 4)

Um plano de ordem parcial só fixa a ordem das ações que é realmente necessária. Um vínculo
causal `A -p-> B` significa que a ação `A` produz a condição `p` e que `p` é pré-condição de
`B`. Então `A` tem que vir antes de `B` (`A ≺ B`). Se outra ação apaga `p` e pode acontecer
entre as duas, ela é uma ameaça. Uma linearização é uma ordem completa das ações que respeita
todas as restrições.

#### Situação 1

| Vínculo causal | Condição `p` | Ordem |
|---|---|---|
| Início → A1 | `clr(d)`, c em (0,0), s0..s2 livres no nível 1 | nenhuma |
| A1 → A2 | `clr(a)`, `livre(s5,1)` | A1 ≺ A2 |
| Início → A2 | b em (5,0) (apoio) | nenhuma |
| A2 → A3 | `livre(s3,0)`: a saiu do caminho de d | A2 ≺ A3 |
| A1 → A3 | `livre(s3,1)`, `livre(s4,1)`: nada acima do destino (sombra) | A1 ≺ A3 |
| Início → A3 | `clr(d)`, `livre(s2,0)`, `livre(s4,0)` | nenhuma |
| A1 → A4 | `clr(a)` | A1 ≺ A4 |
| A3 → A4 | `livre(s0,1)`: c ficou descoberto | A3 ≺ A4 |
| A3 → Fim | `at(d,2) ∧ lev(d,0)` | nenhuma |
| A4 → Fim | `at(a,0) ∧ lev(a,1)` | nenhuma |
| Início → Fim | b em (5,0), c em (0,0) | nenhuma |

```
Início ─clr(d)─> A1 ─clr(a), livre(s5,1)─> A2 ─livre(s3,0)─> A3 ─livre(s0,1)─> A4 ──> Fim
```

- Ameaças: `A2` apaga `clr(b)` e `livre(s5,1)`, e `A3` apaga `livre(s2..s4,0)`, mas nenhuma
  ação que vem depois precisa dessas condições. Nenhuma ação coloca bloco em cima de `a`
  entre A1 e A4. Então não há ameaças.
- Um exemplo de ameaça sem solução: se trocarmos A2 por `move(a,T,4)`, que parece mais simples
  porque põe `a` direto na mesa, essa ação apaga `livre(s4,0)`, que A3 precisa. Não dá para colocar a
  ameaça antes do Início, nem depois de A3, porque A3 depende de `a` ter saído de `s3`.
  Então esse plano não é válido.
- Conclusão: `A1 ≺ A2 ≺ A3 ≺ A4` é uma cadeia, então só existe uma linearização.
  Cada ação libera o caminho da próxima.

#### Situação 2

| Vínculo causal | Condição `p` | Ordem |
|---|---|---|
| Início → B1 | `clr(b)`, `livre(s2,0)` | nenhuma |
| B1 → B2 | b em (2,0) (apoio de a) | B1 ≺ B2 |
| B1 → B3 | `livre(s1,1)`: b saiu de cima de c | B1 ≺ B3 |
| B2 → B3 | `clr(c)`: a saiu de cima de c | B2 ≺ B3 |
| B3 → B4, B5 | c em (4,1) | B3 ≺ B4, B3 ≺ B5 |
| B4 → B5 | `clr(b)`: a saiu de cima de b | B4 ≺ B5 |
| Início → Fim | d em (3,0) | nenhuma |

- Ameaça: B2 põe `a` em cima de `b` e apaga `clr(b)`, que B5 precisa. Só B4 devolve
  `clr(b)`, então é preciso B4 ≺ B5. Com isso o plano da figura vira a cadeia
  B1 ≺ B2 ≺ B3 ≺ B4 ≺ B5, com uma única linearização.
- Um plano alternativo com mais de uma ordem possível: se guardarmos `a` em cima do `d`, a
  ameaça deixa de existir:

```
          move(b,T,2) ─livre(s1,1)─┐                          ┌─> move(a,c,4) ─┐
  Início <      (sem ordem)         > move(c,d,4) ─c em (4,1)─<    (sem ordem)   > Fim
          move(a,d,3) ─livre(s0,1)─┘                          └─> move(b,c,5) ─┘
```

  As duas ações de cada par podem ser executadas em qualquer ordem, então esse plano parcial
  tem 2 × 2 = 4 linearizações.

#### Situação 3

O plano tem seis ações: C1 = `move(d,c,0)`, C2 = `move(a,b,5)`, C3 = `move(d,T,2)`,
C4 = `move(a,c,0)`, C5 = `move(b,c,1)` e C6 = `move(d,T,3)`. A tabela mostra, para cada
pré-condição de cada ação, qual ação produz essa condição.

| Vínculo causal | Condição `p` | Ordem |
|---|---|---|
| Início → C1 | `clr(d)`, c em (0,0), s0..s2 livres no nível 1 | nenhuma |
| C1 → C2 | `clr(a)`, `livre(s5,1)`: d saiu de cima de a e de b | C1 ≺ C2 |
| Início → C2 | b em (5,0) (apoio de a) | nenhuma |
| C2 → C3 | `livre(s3,0)`: a saiu do caminho de d | C2 ≺ C3 |
| C1 → C3 | `livre(s3,1)`, `livre(s4,1)`: nada acima do destino (sombra) | C1 ≺ C3 |
| Início → C3 | `clr(d)`, `livre(s2,0)`, `livre(s4,0)` | nenhuma |
| C1 → C4 | `clr(a)` | C1 ≺ C4 |
| C3 → C4 | `livre(s0,1)`: d saiu de cima de c | C3 ≺ C4 |
| Início → C4 | c em (0,0) (apoio de a) | nenhuma |
| C4 → C5 | `clr(b)`: a saiu de cima de b | C4 ≺ C5 |
| C3 → C5 | `livre(s1,1)`: d saiu de cima de c | C3 ≺ C5 |
| Início → C5 | c em (0,0) (apoio de b) | nenhuma |
| C5 → C6 | `livre(s5,0)`: b saiu da mesa | C5 ≺ C6 |
| C4 → C6 | `livre(s5,1)`: a saiu de cima de s5 (sombra) | C4 ≺ C6 |
| C1 → C6 | `livre(s3,1)`, `livre(s4,1)`: nada acima do destino (sombra) | C1 ≺ C6 |
| Início → C6 | `clr(d)` | nenhuma |
| C4 → Fim | `at(a,0) ∧ lev(a,1)` | nenhuma |
| C5 → Fim | `at(b,1) ∧ lev(b,1)` | nenhuma |
| C6 → Fim | `at(d,3) ∧ lev(d,0)` | nenhuma |
| Início → Fim | `at(c,0) ∧ lev(c,0)` | nenhuma |

```
Início ─clr(d)─> C1 ─clr(a), livre(s5,1)─> C2 ─livre(s3,0)─> C3 ─livre(s0,1)─> C4
       ─clr(b)─> C5 ─livre(s5,0)─> C6 ──> Fim
```

Análise de ameaças (o que cada ação apaga e quem precisa dessa condição):

- C1 apaga `clr(c)` e `livre(s0..s2,1)`. C4 e C5 precisam de `livre(s0,1)` e `livre(s1,1)`,
  mas quem produz essas condições é C3, que já vem depois de C1. Sem ameaça.
- C2 apaga `clr(b)` e `livre(s5,1)`. C5 precisa de `clr(b)` e C6 precisa de `livre(s5,1)`, mas
  as duas condições são devolvidas por C4, que já vem depois de C2 (C2 ≺ C3 ≺ C4). Sem ameaça.
- C3 apaga `livre(s2..s4,0)`. Depois dela só o próprio `d` usa esses slots, em C6. Sem ameaça.
- C4 apaga `clr(c)` e `livre(s0,1)`. C5 também põe um bloco em cima de `c`, mas só precisa de
  espaço no slot `s1` (`livre(s1,1)`), que C4 não apaga. Sem ameaça.
- C5 tira `b` de (5,0), que é o apoio de `a` em C2 (vínculo Início → C2). Como C5 precisa de
  `clr(b)`, que só volta em C4, ela já fica depois de C2. C5 também apaga `livre(s1,1)`, que
  nenhuma ação usa depois. Sem ameaça.
- C6 apaga `livre(s5,0)`, que nenhuma ação usa depois. Sem ameaça.
- Os vínculos de `clr(d)` e de c em (0,0) não são ameaçados por nenhuma ação, porque nenhuma
  ação põe um bloco em cima de `d` e o bloco `c` não se move.

Conclusão: as restrições C1 ≺ C2, C2 ≺ C3, C3 ≺ C4, C4 ≺ C5 e C5 ≺ C6 formam uma cadeia, então
só existe uma linearização: C1, C2, C3, C4, C5, C6. Cada ação libera o que a próxima precisa.
C1 descobre `a`. C2 tira `a` do caminho de `d`. C3 descobre `c`. C4 descobre `b` e libera o
espaço acima de `s5`. C5 libera `s5` na mesa. C6 coloca `d` no lugar final.

#### Ordem parcial no SAT (grupo 3.7)

Uma restrição `φ1 ≺P φ2` ("φ1 acontece antes de φ2") vira as cláusulas
`¬φ2(t) ∨ ⋁_{t'≤t} φ1(t')`. Escolhemos uma restrição por cenário, tirada de um vínculo causal:

| Cenário | Vínculo | φ1 ≺P φ2 | Resultado |
|---|---|---|---|
| Sit. 1 | A3 → A4 | d em (2,0) ≺ a em (0,1) | SAT com T=4; invertida: UNSAT para T=3..8 |
| Sit. 2 | B3 → B4 | c em (4,1) ≺ a em (4,2) | SAT com T=5; invertida: mínimo passa a 7 |
| Sit. 3 | C5 → C6 | b em (1,1) ≺ d em (3,0) | SAT com T=6; invertida: mínimo passa a 7 |

Com a ordem certa, o plano ótimo continua existindo. Com a ordem invertida ele deixa de
existir. Isso mostra que as ordens que achamos na análise manual são mesmo obrigatórias.

## 3. Codificação CNF

### 3.1 Variáveis

| Variável | Índices | Tipo | Sit. 1 (T=4) | Sit. 2 (T=5) | Sit. 3 (T=6) |
|---|---|---|---|---|---|
| `at(b,p,t)` | p ∈ [0, 6−ℓ(b)], t ∈ [0,T] | básico | 105 | 126 | 147 |
| `lev(b,l,t)` | l ∈ [0,3] | básico | 80 | 96 | 112 |
| `clr(b,t)` | | calculado | 20 | 24 | 28 |
| `cov(b,s,l,t)` | s ∈ [0,5], l ∈ [0,3] | auxiliar | 480 | 576 | 672 |
| `move(b,y,p,t)` | y ∈ B ∪ {T}, y ≠ b, t ∈ [0,T−1] | ação | 336 | 420 | 504 |
| `phi(·,t)` | | auxiliar (ordem parcial) | 5 | 6 | 7 |
| `esp(b,s,t)` | s ∈ [0,5] | calculado (novo) | 120 | 144 | 168 |
| **Total** | | | **1146** | **1392** | **1638** |

### 3.2 Grupos de cláusulas

| Grupo | Formato das cláusulas | Qtde |
|---|---|---|
| 3.1 Estado inicial | unitárias `at(b,p,0)`, `lev(b,l,0)` | 8 |
| 3.2 Meta | unitárias `at(b,p,T)`, `lev(b,l,T)` | 8 |
| 3.3 (A) Posição | `⋁p at(b,p,t)`; `¬at(b,p1,t) ∨ ¬at(b,p2,t)` | 250 |
| 3.3 (B) Nível | idem para `lev` | 140 |
| 3.3 (Z) cov | `¬cov ∨ lev`; `¬cov ∨ ⋁ at`; `¬at ∨ ¬lev ∨ cov` | 1640 |
| 3.3 (C) Exclusão | `¬cov(b1,s,l,t) ∨ ¬cov(b2,s,l,t)` | 720 |
| 3.3 (D) Estabilidade | todo `S ⊆ span` com `#S = ℓ−⌈ℓ/2⌉+1`: `¬at ∨ ¬lev ∨ ⋁ cov(b',s,l−1,t)` | 435 |
| 3.3 (Y) esp (novo) | `¬esp ∨ ⋁l cov(b,s,l)`; `¬esp ∨ ¬cov(b,s,l) ∨ ¬cov(b',s,l+1)`; `¬cov(b,s,l) ∨ esp ∨ ⋁ cov(b',s,l+1)` | 1680 |
| 3.3 (E) Clear | `¬clr ∨ ¬cov(b,s,l) ∨ esp(b,s)`; `¬at(b,p) ∨ clr ∨ ⋁ ¬esp(b,s)` | 585 |
| 3.4 (G) Pré-condições | G1 `¬move ∨ clr(b)`; G2 `¬move ∨ ¬at(y,q) ∨ ¬lev(y,l) ∨ esp(y,s) ∨ cov(b,s,l+1)`; G3 destino diferente do lugar atual; G4 sobreposição; G5+G6 destino livre e sombra; G7 nível existe | 12384 |
| 3.4 (F) Efeitos | F1 `¬move ∨ at(b,p,t+1)`; F2 `¬move ∨ ¬lev(y,l,t) ∨ lev(b,l+1,t+1)`; F3 `¬move ∨ ¬clr(y,t+1)` | 1428 |
| 3.5 Frame axioms | `at(b,p,t) ∨ ¬at(b,p,t+1) ∨ ⋁ move(b,·,·,t)` e o simétrico; idem `lev` | 296 |
| 3.6 Ação única | `⋁ move(·,t)`; `¬move_i ∨ ¬move_j` | 13948 |
| 3.7 Ordem parcial | `¬φ2(t) ∨ ⋁_{t'≤t} φ1(t')` | 20 |
| **Total** | | **33542** |

(Contagens da Situação 1. Totais: Situação 2 = 41650 cláusulas; Situação 3 = 49758.)

- Na estabilidade precisamos dizer "pelo menos k de n slots estão apoiados". Em cláusulas isso
  é escrito como "em todo grupo de n−k+1 slots, pelo menos um está apoiado".
- O efeito "b deixa a posição antiga" (F4) não precisa de cláusula própria, porque a
  unicidade (A) já garante isso.
- `clr` e `esp` não precisam de frame axiom. Os grupos (Y) e (E) calculam os dois de novo em
  cada instante.
- Em G2, o literal `cov(b,s,l+1)` serve para não contar o próprio `b`. Num movimento lateral
  em cima do mesmo apoio, o slot que o próprio `b` ocupa conta como livre.
- `on` não vira variável. O `interpretar.py` calcula o `on` depois, a partir de `at` e `lev`.

## 4. Exemplos dos 3 cenários codificados

### Situação 1

| S0 (t=0) | DIMACS | Sf4 (t=4) | DIMACS |
|---|---|---|---|
| `at(c,0,0) ∧ lev(c,0,0)` | `13 0` `114 0` | `at(c,0,4) ∧ lev(c,0,4)` | `97 0` `178 0` |
| `at(a,3,0) ∧ lev(a,0,0)` | `4 0` `106 0` | `at(a,0,4) ∧ lev(a,1,4)` | `85 0` `171 0` |
| `at(b,5,0) ∧ lev(b,0,0)` | `12 0` `110 0` | `at(d,2,4) ∧ lev(d,0,4)` | `104 0` `182 0` |
| `at(d,3,0) ∧ lev(d,1,0)` | `21 0` `119 0` | `at(b,5,4) ∧ lev(b,0,4)` | `96 0` `174 0` |

Exemplos de cláusulas do `.cnf` (o id 762 é `move(d,c,0,0)`, a primeira ação do plano):

| Grupo | Cláusula | DIMACS |
|---|---|---|
| G1 | `¬move(d,c,0,0) ∨ clr(d,0)` | `-762 189 0` |
| G4 | `¬move(d,c,0,0) ∨ at(c,0,0) ∨ at(c,1,0) ∨ at(c,2,0)` | `-762 13 14 15 0` |
| G2 | `¬move(d,c,0,0) ∨ ¬at(c,0,0) ∨ ¬lev(c,0,0) ∨ esp(c,s0,0) ∨ cov(d,s0,1,0)` | `-762 -13 -114 1039 284 0` |
| G5 | `¬move(d,c,0,0) ∨ ¬lev(c,0,0) ∨ ¬cov(a,s2,1,0)` | `-762 -114 -214 0` |
| (Y) | `¬esp(a,s3,0) ∨ ¬cov(a,s3,0,0) ∨ ¬cov(d,s3,1,0)` | `-1030 -209 -287 0` |
| (E) | `¬clr(a,0) ∨ ¬cov(a,s3,0,0) ∨ esp(a,s3,0)` | `-186 -209 1030 0` |
| F1 | `¬move(d,c,0,0) ∨ at(d,0,1)` | `-762 39 0` |
| F2 | `¬move(d,c,0,0) ∨ ¬lev(c,0,0) ∨ lev(d,1,1)` | `-762 -114 135 0` |
| (C) | `¬cov(a,s3,0,0) ∨ ¬cov(d,s3,0,0)` | `-209 -281 0` |
| (D) | `¬at(d,0,1) ∨ ¬lev(d,1,1) ∨ cov(a,s0,0,1) ∨ cov(b,s0,0,1) ∨ cov(c,s0,0,1) ∨ cov(a,s1,0,1) ∨ cov(b,s1,0,1) ∨ cov(c,s1,0,1)` | `-39 -135 302 326 350 303 327 351 0` |

### Situação 2

| S0 (t=0) | DIMACS | S5 (t=5) | DIMACS |
|---|---|---|---|
| `at(c,0,0) ∧ lev(c,0,0)` | `13 0` `135 0` | `at(d,3,5) ∧ lev(d,0,5)` | `126 0` `219 0` |
| `at(d,3,0) ∧ lev(d,0,0)` | `21 0` `139 0` | `at(c,4,5) ∧ lev(c,1,5)` | `122 0` `216 0` |
| `at(a,0,0) ∧ lev(a,1,0)` | `1 0` `128 0` | `at(a,4,5) ∧ lev(a,2,5)` | `110 0` `209 0` |
| `at(b,1,0) ∧ lev(b,1,0)` | `8 0` `132 0` | `at(b,5,5) ∧ lev(b,2,5)` | `117 0` `213 0` |

### Situação 3

| S0 (t=0) | DIMACS | S7 (t=6) | DIMACS |
|---|---|---|---|
| `at(c,0,0) ∧ lev(c,0,0)` | `13 0` `156 0` | `at(c,0,6) ∧ lev(c,0,6)` | `139 0` `252 0` |
| `at(a,3,0) ∧ lev(a,0,0)` | `4 0` `148 0` | `at(a,0,6) ∧ lev(a,1,6)` | `127 0` `245 0` |
| `at(b,5,0) ∧ lev(b,0,0)` | `12 0` `152 0` | `at(b,1,6) ∧ lev(b,1,6)` | `134 0` `249 0` |
| `at(d,3,0) ∧ lev(d,1,0)` | `21 0` `161 0` | `at(d,3,6) ∧ lev(d,0,6)` | `147 0` `256 0` |

O predicado novo nas cláusulas: a ação `move(b,c,1,4)` (id 1327) coloca `b` ao lado de `a`,
em cima de `c`. A cláusula G2 dela é
`¬move(b,c,1,4) ∨ ¬at(c,0,4) ∨ ¬lev(c,0,4) ∨ esp(c,s1,4) ∨ cov(b,s1,1,4)`, que no arquivo é
`-1327 -97 -220 1580 703 0`. Ela exige espaço livre em cima de `c` só no slot `s1`, que é
onde `b` vai pousar. No instante 4, `clr(c,4)` é falso, porque `a` está em cima de `c` no
slot `s0`. Já `esp(c,s1,4)` é verdadeiro. Com a pré-condição clássica `clr(y)` a cláusula seria
`¬move(b,c,1,4) ∨ clr(c,4)`, e a Situação 3 daria UNSAT.

## 5. Mapeamento: descrição formal → código

| Regra formal | Código (`bw2cnf_var.py`) |
|---|---|
| Blocos e comprimentos | `BLOCKS = {'a':1, 'b':1, 'c':2, 'd':3}` |
| Pontos / slots / níveis | `MAX_POINT = 6`, `SLOTS`, `MAX_LEVEL = 3` |
| Posições válidas | `valid_positions(L) = range(MAX_POINT - L + 1)` |
| `span`, `overlap` | `span(b, p)`, `spans_overlap(b1, p1, b2, p2)` |
| `at, lev, clr, cov, mv, esp` | dicionários com `f.new_var(nome)` |
| Cenários (S0, meta, horizonte) | `CENARIOS[N]` com `INITIAL`, `GOAL`, `HORIZON`; `--cenario N` |
| Estado inicial / meta | `# 3.1 ESTADO INICIAL`, `# 3.2 META` |
| A1 unicidade | `# 3.3 (A)`, `# 3.3 (B)` |
| A2 definição de `cov` | `# 3.3 (Z)` |
| A3 exclusão | `# 3.3 (C)` |
| A7 estabilidade | `# 3.3 (D)` |
| A5a `esp` (predicado novo) | `# 3.3 (Y)` |
| A5b clear | `# 3.3 (E)` |
| Pré-condições P1–P6 | `# 3.4 (G)` |
| Efeitos ADD/DEL | `# 3.4 (F)` |
| Frame axioms | `# 3.5` |
| Ação única por passo | `# 3.6` |
| Ordem parcial | `ORDEM_PARCIAL`, `# 3.7` |
| A6 `on` (calculada depois) | `interpretar.py`, função `derivar_on` |

## 6. Execução passo a passo

| Cenário | UNSAT para | SAT com | Variáveis | Cláusulas | Tempo do miniSAT |
|---|---|---|---|---|---|
| Situação 1 | T = 0..3 | T = 4 | 1146 | 33542 | 0,018 s |
| Situação 2 | T = 0..4 | T = 5 | 1392 | 41650 | 0,016 s |
| Situação 3 | T = 0..5 | T = 6 | 1638 | 49758 | 0,026 s |

```
$ cd cenario1
$ python3 ../bw2cnf_var.py --cenario 1
Gerado: 1146 variaveis, 33542 clausulas (T=4)
$ minisat trab01_blocos2SAT.cnf resultado1.txt
SATISFIABLE
$ python3 ../interpretar.py resultado1.txt
PLANO ENCONTRADO (4 acoes):
  1. t=0: mover bloco 'd' para CIMA de 'c' em p=0
  2. t=1: mover bloco 'a' para CIMA de 'b' em p=5
  3. t=2: mover bloco 'd' para a MESA em p=2
  4. t=3: mover bloco 'a' para CIMA de 'c' em p=0

$ cd ../cenario2 && ... (mesmos comandos com 2)
PLANO ENCONTRADO (5 acoes):
  1. t=0: mover bloco 'b' para CIMA de 'd' em p=3
  2. t=1: mover bloco 'a' para a MESA em p=2
  3. t=2: mover bloco 'c' para CIMA de 'd' em p=4
  4. t=3: mover bloco 'a' para CIMA de 'c' em p=4
  5. t=4: mover bloco 'b' para CIMA de 'c' em p=5

$ cd ../cenario3 && ... (mesmos comandos com 3)
PLANO ENCONTRADO (6 acoes):
  1. t=0: mover bloco 'd' para CIMA de 'c' em p=0
  2. t=1: mover bloco 'a' para CIMA de 'b' em p=5
  3. t=2: mover bloco 'd' para a MESA em p=2
  4. t=3: mover bloco 'a' para CIMA de 'c' em p=0
  5. t=4: mover bloco 'b' para CIMA de 'c' em p=1
  6. t=5: mover bloco 'd' para a MESA em p=3
```

A saída completa (com o desenho de cada estado) está em `cenarioN/plano_interpretado.txt`.

## 7. Interpretação da saída do SAT solver

O `resultado1.txt` tem duas linhas. A primeira é `SAT`. A segunda tem o valor de cada uma
das 1146 variáveis (número positivo quer dizer verdadeiro e negativo quer dizer falso). O
miniSAT só conhece números, então usamos o `.map` para saber o que cada número significa.
O `interpretar.py` faz o seguinte:

1. lê o mapa, por exemplo `4 → at(a,3,0)` e `762 → move(d,c,0,0)`;
2. fica só com os números positivos (120 de 1146);
3. separa as ações e ordena pelo instante `t`. As ações verdadeiras são `762, 775, 936, 944`,
   que são `move(d,c,0,0)`, `move(a,b,5,1)`, `move(d,T,2,2)` e `move(a,c,0,3)`;
4. calcula o `on` a partir de `at`, `lev` e da sobreposição dos spans.

Nos outros cenários as ações verdadeiras são `862, 927, 1053, 1085, 1194` na Situação 2
(139 de 1392 variáveis verdadeiras) e `1036, 1049, 1210, 1218, 1327, 1463` na Situação 3
(168 de 1638).

Também dá para conferir pelo terminal, sem o `interpretar.py`, do mesmo jeito que no mundo dos blocos clássico:

```bash
$ grep -E "^(762|775|936|944) " trab01_blocos2SAT.map
762 move(d,c,0,0)
775 move(a,b,5,1)
936 move(d,T,2,2)
944 move(a,c,0,3)

$ awk 'NR==2 {for(i=1;i<NF;i++) if($i>0) print $i}' resultado1.txt > ids.txt
$ while read id; do grep "^$id " trab01_blocos2SAT.map; done < ids.txt | grep move
```

O segundo comando pega os inteiros positivos da linha 2 do resultado, procura cada um no
`.map` e fica só com as linhas de ação (as que têm `move`). A saída é a mesma do primeiro.

### Situação 1: manual × SAT

| Passo | Plano manual (2.6) | Plano do SAT |
|---|---|---|
| 1 | move(d,c,0) | move(d,c,0) |
| 2 | move(a,b,5) | move(a,b,5) |
| 3 | move(d,T,2) | move(d,T,2) |
| 4 | move(a,c,0) | move(a,c,0) |

O plano manual e o do SAT são iguais.

### Situação 2: manual × SAT

| Passo | Plano manual (figura) | Plano do SAT |
|---|---|---|
| 1 | move(b,T,2) | move(b,d,3) |
| 2 | move(a,b,2) | move(a,T,2) |
| 3 | move(c,d,4) | move(c,d,4) |
| 4 | move(a,c,4) | move(a,c,4) |
| 5 | move(b,c,5) | move(b,c,5) |

Os planos são diferentes, mas os dois têm 5 ações. Existe mais de um plano com 5 ações, e o SAT
devolve qualquer um que satisfaça a fórmula. O SAT guardou `b` em cima de `d` e `a` na mesa. O plano manual
guarda `b` na mesa e `a` em cima de `b`. O plano do SAT segue a mesma ideia do plano
alternativo da seção 2.7, só que com os lugares temporários de `a` e `b` trocados. Também
testamos obrigar o SAT a usar as 5 ações do plano manual. A fórmula continuou SAT, então o
plano manual também é aceito.

### Situação 3: manual × SAT

O plano manual e o do SAT são iguais. As ações 1 a 4 são as mesmas da Situação 1.
