#!/usr/bin/env python3
"""
bw2cnf_var.py -- Mundo dos Blocos de TAMANHO VARIAVEL  ->  CNF (formato DIMACS)

Traduz a descricao formal em Logica de Primeira Ordem (ver README.md, secao 2)
para Logica Proposicional. Para isso cria uma variavel para cada predicado e
cada combinacao de bloco, posicao, nivel e instante de tempo t = 0..T.

Uso:
    python3 bw2cnf_var.py --cenario 1     # Situacao 1: S0 -> Sf4 (padrao)
    python3 bw2cnf_var.py --cenario 2     # Situacao 2: S0 -> S5
    python3 bw2cnf_var.py --cenario 3     # Situacao 3: S0 -> S7

O numero de passos de cada cenario e o HORIZON no dicionario CENARIOS.

Gera:
    trab01_blocos2SAT.cnf   formula para o miniSAT
    trab01_blocos2SAT.map   tabela  id da variavel -> nome simbolico
"""
import argparse
from itertools import combinations
from math import ceil

# =====================================================================
# 1. CONFIGURACAO DOS CENARIOS
# =====================================================================
BLOCKS = {'a': 1, 'b': 1, 'c': 2, 'd': 3}   # comprimento l(b), em uc
MAX_POINT = 6                              # pontos 0..6  => slots s0..s5
MAX_LEVEL = 3                              # niveis 0..3  (0 = mesa)
TABLE = 'T'                                # a mesa

# Cada bloco -> (ponto inicial p, nivel l).
# ORDEM_PARCIAL: pares (phi1, phi2) com phi1 <_P phi2,
# isto e, "phi1 tem que valer em algum t' <= t sempre que phi2 valer em t".
# Cada phi e (bloco, p, l) = "bloco esta em (p, l)"; vem de um vinculo causal
# do plano de ordem parcial (ver README, secao 2.7).
CENARIOS = {
    1: dict(nome='Situacao 1: S0 -> Sf4',
            INITIAL={'c': (0, 0), 'a': (3, 0), 'b': (5, 0), 'd': (3, 1)},
            GOAL={'c': (0, 0), 'a': (0, 1), 'd': (2, 0), 'b': (5, 0)},
            HORIZON=4,
            # A3 --livre(s0,1)--> A4: d chega ao lugar final antes de a
            ORDEM_PARCIAL=[(('d', 2, 0), ('a', 0, 1))]),
    2: dict(nome='Situacao 2: S0 -> S5',
            INITIAL={'c': (0, 0), 'd': (3, 0), 'a': (0, 1), 'b': (1, 1)},
            GOAL={'d': (3, 0), 'c': (4, 1), 'a': (4, 2), 'b': (5, 2)},
            HORIZON=5,
            # B3 --c em (4,1)--> B4: c sobe no d antes de a subir no c
            ORDEM_PARCIAL=[(('c', 4, 1), ('a', 4, 2))]),
    3: dict(nome='Situacao 3: S0 -> S7',
            INITIAL={'c': (0, 0), 'a': (3, 0), 'b': (5, 0), 'd': (3, 1)},
            GOAL={'c': (0, 0), 'a': (0, 1), 'b': (1, 1), 'd': (3, 0)},
            HORIZON=6,
            # C5 --livre(s5,0)--> C6: b sai de s5 antes de d ir para p = 3
            ORDEM_PARCIAL=[(('b', 1, 1), ('d', 3, 0))]),
}


def usar_cenario(n):
    """Carrega o cenario n nas variaveis globais INITIAL, GOAL, ..."""
    global INITIAL, GOAL, HORIZON, ORDEM_PARCIAL
    c = CENARIOS[n]
    INITIAL, GOAL = c['INITIAL'], c['GOAL']
    HORIZON, ORDEM_PARCIAL = c['HORIZON'], c['ORDEM_PARCIAL']


usar_cenario(1)

OUT = 'trab01_blocos2SAT'

# =====================================================================
# 2. FUNCOES AUXILIARES DO DOMINIO
# =====================================================================
SLOTS = range(MAX_POINT)          # s0..s5  (slot s = intervalo [s, s+1])
LEVELS = range(MAX_LEVEL + 1)     # 0..3


def valid_positions(L):
    """Pontos iniciais validos para um bloco de comprimento L: 0..6-L."""
    return range(MAX_POINT - L + 1)


def span(b, p):
    """Slots cobertos pelo bloco b quando comeca no ponto p."""
    return range(p, p + BLOCKS[b])


def spans_overlap(b1, p1, b2, p2):
    """True se os spans de b1 (em p1) e b2 (em p2) tem algum slot em comum."""
    return p1 < p2 + BLOCKS[b2] and p2 < p1 + BLOCKS[b1]


# =====================================================================
# 3. CONSTRUCAO DA CNF
# =====================================================================
class CNF:
    def __init__(self):
        self.n = 0
        self.names = {}
        self.clauses = []
        self.groups = {}          # nome do grupo -> no. de clausulas
        self._group = None

    def new_var(self, name):
        self.n += 1
        self.names[self.n] = name
        return self.n

    def group(self, name):
        self._group = name
        self.groups.setdefault(name, 0)

    def add(self, clause):
        self.clauses.append(clause)
        self.groups[self._group] += 1


def build(T):
    f = CNF()
    B = list(BLOCKS)

    # ---------------- Variaveis proposicionais ----------------------
    # at(b,p,t)   : bloco b comeca no ponto p no instante t
    # lev(b,l,t)  : bloco b esta no nivel l no instante t
    # clr(b,t)    : nada em cima de b no instante t
    # cov(b,s,l,t): (auxiliar) b cobre o slot s no nivel l no instante t
    # move(b,y,p,t): acao "mover b para cima de y (ou da mesa T), comecando
    #               no ponto p", executada entre t e t+1 (dicionario mv)
    # phi(.,t)    : (auxiliar) meta parcial usada na ordem parcial
    # esp(b,s,t)  : PREDICADO NOVO -- ha espaco livre em cima do bloco b
    #               no slot s. E o "clr por slot": substitui o clr(y) do
    #               mundo classico como condicao para RECEBER um bloco.
    at, lev, clr, cov, mv, phi, esp = {}, {}, {}, {}, {}, {}, {}
    for t in range(T + 1):
        for b in B:
            for p in valid_positions(BLOCKS[b]):
                at[b, p, t] = f.new_var(f'at({b},{p},{t})')
    for t in range(T + 1):
        for b in B:
            for l in LEVELS:
                lev[b, l, t] = f.new_var(f'lev({b},{l},{t})')
    for t in range(T + 1):
        for b in B:
            clr[b, t] = f.new_var(f'clr({b},{t})')
    for t in range(T + 1):
        for b in B:
            for l in LEVELS:
                for s in SLOTS:
                    cov[b, s, l, t] = f.new_var(f'cov({b},s{s},{l},{t})')
    for t in range(T):
        for b in B:
            for y in B + [TABLE]:
                if y == b:
                    continue
                for p in valid_positions(BLOCKS[b]):
                    mv[b, y, p, t] = f.new_var(f'move({b},{y},{p},{t})')
    for k, ((b1, p1, l1), _) in enumerate(ORDEM_PARCIAL):
        for t in range(T + 1):
            phi[k, t] = f.new_var(f'phi({b1},{p1},{l1},{t})')
    for t in range(T + 1):
        for b in B:
            for s in SLOTS:
                esp[b, s, t] = f.new_var(f'esp({b},s{s},{t})')

    # ------------------------------------------------------------------
    # 3.1 ESTADO INICIAL: clausulas unitarias em t = 0
    # ------------------------------------------------------------------
    f.group('3.1 estado inicial')
    for b, (p, l) in INITIAL.items():
        f.add([at[b, p, 0]])
        f.add([lev[b, l, 0]])

    # ------------------------------------------------------------------
    # 3.2 META: clausulas unitarias em t = T
    # ------------------------------------------------------------------
    f.group('3.2 meta')
    for b, (p, l) in GOAL.items():
        f.add([at[b, p, T]])
        f.add([lev[b, l, T]])

    for t in range(T + 1):
        # --------------------------------------------------------------
        # 3.3 (A) UNICIDADE DE POSICAO: exatamente um p por bloco
        # --------------------------------------------------------------
        f.group('3.3 (A) unicidade de posicao')
        for b in B:
            ps = [at[b, p, t] for p in valid_positions(BLOCKS[b])]
            f.add(ps)                                   # pelo menos um
            for x, y in combinations(ps, 2):
                f.add([-x, -y])                         # no maximo um

        # --------------------------------------------------------------
        # 3.3 (B) UNICIDADE DE NIVEL: exatamente um l por bloco
        # --------------------------------------------------------------
        f.group('3.3 (B) unicidade de nivel')
        for b in B:
            ls = [lev[b, l, t] for l in LEVELS]
            f.add(ls)
            for x, y in combinations(ls, 2):
                f.add([-x, -y])

        # --------------------------------------------------------------
        # 3.3 (Z) DEFINICAO DE cov (auxiliar)
        #   cov(b,s,l,t) <-> lev(b,l,t) AND  OR_{p : s em span(b,p)} at(b,p,t)
        # --------------------------------------------------------------
        f.group('3.3 (Z) definicao de cov')
        for b in B:
            for l in LEVELS:
                for s in SLOTS:
                    c = cov[b, s, l, t]
                    covering = [at[b, p, t] for p in valid_positions(BLOCKS[b])
                                if s in span(b, p)]
                    f.add([-c, lev[b, l, t]])
                    f.add([-c] + covering)
                    for a in covering:
                        f.add([-a, -lev[b, l, t], c])

        # --------------------------------------------------------------
        # 3.3 (C) EXCLUSAO HORIZONTAL: um slot, num nivel, tem no maximo
        #         um bloco
        # --------------------------------------------------------------
        f.group('3.3 (C) exclusao horizontal')
        for l in LEVELS:
            for s in SLOTS:
                for b1, b2 in combinations(B, 2):
                    f.add([-cov[b1, s, l, t], -cov[b2, s, l, t]])

        # --------------------------------------------------------------
        # 3.3 (D) ESTABILIDADE: se b esta em (p, l) com l > 0, pelo menos
        #   k = ceil(l(b)/2) slots de span(b,p) estao ocupados no nivel l-1.
        #   "Pelo menos k de n" == "em todo subconjunto de n-k+1 slots,
        #   pelo menos um esta ocupado".
        # --------------------------------------------------------------
        f.group('3.3 (D) estabilidade')
        for b in B:
            n = BLOCKS[b]
            k = ceil(n / 2)
            for p in valid_positions(n):
                for l in LEVELS:
                    if l == 0:
                        continue
                    for S in combinations(span(b, p), n - k + 1):
                        support = [cov[o, s, l - 1, t]
                                   for s in S for o in B if o != b]
                        f.add([-at[b, p, t], -lev[b, l, t]] + support)

        # --------------------------------------------------------------
        # 3.3 (Y) DEFINICAO DE esp (predicado novo)
        #   esp(b,s,t) <-> b cobre o slot s em algum nivel l  E  nenhum
        #                  outro bloco cobre s no nivel l+1
        # --------------------------------------------------------------
        f.group('3.3 (Y) definicao de esp')
        for b in B:
            others = [o for o in B if o != b]
            for s in SLOTS:
                e = esp[b, s, t]
                f.add([-e] + [cov[b, s, l, t] for l in LEVELS])
                for l in LEVELS:
                    if l == MAX_LEVEL:
                        f.add([-cov[b, s, l, t], e])
                        continue
                    for o in others:
                        f.add([-e, -cov[b, s, l, t], -cov[o, s, l + 1, t]])
                    f.add([-cov[b, s, l, t], e] +
                          [cov[o, s, l + 1, t] for o in others])

        # --------------------------------------------------------------
        # 3.3 (E) CLEAR: clr(b,t) <-> esp(b,s,t) em TODOS os slots de b
        #         (clr e o caso particular "espaco livre no bloco inteiro")
        # --------------------------------------------------------------
        f.group('3.3 (E) clear')
        for b in B:
            for s in SLOTS:
                for l in LEVELS:
                    f.add([-clr[b, t], -cov[b, s, l, t], esp[b, s, t]])
            for p in valid_positions(BLOCKS[b]):
                f.add([-at[b, p, t], clr[b, t]] +
                      [-esp[b, s, t] for s in span(b, p)])

    for t in range(T):
        for (b, y, p, tt), m in mv.items():
            if tt != t:
                continue
            others = [o for o in B if o != b]

            # ----------------------------------------------------------
            # 3.4 (G) PRE-CONDICOES de move(b,y,p,t)
            # ----------------------------------------------------------
            f.group('3.4 (G) pre-condicoes de move')
            # G1. o topo de b esta livre
            f.add([-m, clr[b, t]])
            if y == TABLE:
                # G3. o destino nao pode ser o lugar atual (ja estar na mesa em p)
                f.add([-m, -at[b, p, t], -lev[b, 0, t]])
                # G5+G6. slots de destino livres no nivel 0 E em todos os
                # niveis acima (regra da "sombra": nao se enfia bloco
                # embaixo de outro)
                for s in span(b, p):
                    for l2 in LEVELS:
                        for o in others:
                            f.add([-m, -cov[o, s, l2, t]])
            else:
                # G3. o destino nao pode ser o lugar atual (ja estar sobre y em p)
                for l in LEVELS:
                    if l < MAX_LEVEL:
                        f.add([-m, -at[b, p, t], -lev[y, l, t],
                               -lev[b, l + 1, t]])
                # G4. o span de b (em p) sobrepoe o span de y
                f.add([-m] + [at[y, py, t]
                              for py in valid_positions(BLOCKS[y])
                              if spans_overlap(b, p, y, py)])
                # G2. esp(y,s): ha espaco livre em cima de y em todos os
                # slots onde b vai pousar sobre ele. SUBSTITUI o clr(y) do
                # mundo classico: y nao precisa estar todo livre, so nesses slots.
                # Excecao: se quem ocupa o slot e o proprio b (movimento
                # lateral sobre o mesmo apoio), o slot conta como livre.
                for py in valid_positions(BLOCKS[y]):
                    for s in span(b, p):
                        if s in span(y, py):
                            for l in LEVELS:
                                if l < MAX_LEVEL:
                                    f.add([-m, -at[y, py, t], -lev[y, l, t],
                                           esp[y, s, t], cov[b, s, l + 1, t]])
                # G5+G6. slots de destino livres no nivel lev(y)+1 e acima
                for l in LEVELS:
                    for s in span(b, p):
                        for l2 in range(l + 1, MAX_LEVEL + 1):
                            for o in others:
                                f.add([-m, -lev[y, l, t], -cov[o, s, l2, t]])
                # G7. existe nivel acima de y
                f.add([-m, -lev[y, MAX_LEVEL, t]])
                # OBS: com o clr(y) classico no lugar de G2, dois blocos
                # nunca ficariam lado a lado em cima de um maior, e as
                # Situacoes 2 e 3 seriam UNSAT (ver README, secao 2.5).

            # ----------------------------------------------------------
            # 3.4 (F) EFEITOS de move(b,y,p,t)
            # ----------------------------------------------------------
            f.group('3.4 (F) efeitos de move')
            f.add([-m, at[b, p, t + 1]])                       # F1
            if y == TABLE:
                f.add([-m, lev[b, 0, t + 1]])                  # F2
            else:
                for l in LEVELS:
                    if l < MAX_LEVEL:
                        f.add([-m, -lev[y, l, t], lev[b, l + 1, t + 1]])  # F2
                f.add([-m, -clr[y, t + 1]])                    # F3
            # F4 (b deixa a posicao e o nivel antigos) segue da unicidade.

        # --------------------------------------------------------------
        # 3.5 FRAME AXIOMS: se b nao foi movido em t, at e lev de b nao
        #     mudam. (clr nao precisa: e definido em cada estado por (E))
        # --------------------------------------------------------------
        f.group('3.5 frame axioms')
        for b in B:
            moved = [m for (bb, y, p, tt), m in mv.items()
                     if bb == b and tt == t]
            for p in valid_positions(BLOCKS[b]):
                f.add([at[b, p, t], -at[b, p, t + 1]] + moved)
                f.add([-at[b, p, t], at[b, p, t + 1]] + moved)
            for l in LEVELS:
                f.add([lev[b, l, t], -lev[b, l, t + 1]] + moved)
                f.add([-lev[b, l, t], lev[b, l, t + 1]] + moved)

        # --------------------------------------------------------------
        # 3.6 ACAO UNICA POR PASSO: exatamente uma acao em cada t
        # --------------------------------------------------------------
        f.group('3.6 acao unica por passo')
        acts = [m for (b, y, p, tt), m in mv.items() if tt == t]
        f.add(acts)
        for x, y in combinations(acts, 2):
            f.add([-x, -y])

    # ------------------------------------------------------------------
    # 3.7 ORDEM PARCIAL (opcional): phi1 <_P phi2
    #   para todo t:  phi2(t) -> OR_{t' <= t} phi1(t')
    #   phi(t) = at(b,p,t) AND lev(b,l,t) vira uma variavel auxiliar g.
    # ------------------------------------------------------------------
    f.group('3.7 ordem parcial')
    for k, ((b1, p1, l1), (b2, p2, l2)) in enumerate(ORDEM_PARCIAL):
        g = {t: phi[k, t] for t in range(T + 1)}
        for t in range(T + 1):
            f.add([-g[t], at[b1, p1, t]])
            f.add([-g[t], lev[b1, l1, t]])
            f.add([-at[b1, p1, t], -lev[b1, l1, t], g[t]])
        for t in range(T + 1):
            f.add([-at[b2, p2, t], -lev[b2, l2, t]] +
                  [g[t2] for t2 in range(t + 1)])

    return f


def write(f, T):
    with open(OUT + '.cnf', 'w') as out:
        out.write('c Mundo dos Blocos de tamanho variavel -> CNF\n')
        out.write(f'c INITIAL = {INITIAL}\n')
        out.write(f'c GOAL    = {GOAL}\n')
        out.write(f'c HORIZON = {T}\n')
        for g, k in f.groups.items():
            out.write(f'c   {k:6d} clausulas  {g}\n')
        out.write(f'p cnf {f.n} {len(f.clauses)}\n')
        for c in f.clauses:
            out.write(' '.join(map(str, c)) + ' 0\n')
    with open(OUT + '.map', 'w') as out:
        for i in range(1, f.n + 1):
            out.write(f'{i} {f.names[i]}\n')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--cenario', type=int, default=1, choices=CENARIOS)
    args = ap.parse_args()
    usar_cenario(args.cenario)
    T = HORIZON
    print(CENARIOS[args.cenario]['nome'])
    f = build(T)
    write(f, T)
    print(f'Gerado: {f.n} variaveis, {len(f.clauses)} clausulas (T={T})')
    print(f'Arquivos: {OUT}.cnf, {OUT}.map')
