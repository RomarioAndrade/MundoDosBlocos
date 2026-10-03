#!/usr/bin/env python3
"""
interpretar.py -- traduz a saida numerica do miniSAT para um plano em portugues.

Uso:
    python3 interpretar.py resultado1.txt
    python3 interpretar.py resultado1.txt --verbose       # desenha cada estado
    python3 interpretar.py resultado1.txt --map outro.map

Passos:
    1. leitura do mapa   id -> nome simbolico  (trab01_blocos2SAT.map)
    2. filtragem         so os literais POSITIVOS
    3. ordenacao         acoes move(...) agrupadas por t, traduzidas para frases
    + derivacao de on(b, y, t) a partir de at, lev e sobreposicao de spans
"""
import argparse
import re
import sys

from bw2cnf_var import BLOCKS, MAX_POINT, TABLE, span, spans_overlap

RE_AT = re.compile(r'^at\((\w),(\d+),(\d+)\)$')
RE_LEV = re.compile(r'^lev\((\w),(\d+),(\d+)\)$')
RE_MV = re.compile(r'^move\((\w),(\w),(\d+),(\d+)\)$')


def ler_mapa(path):
    mapa = {}
    with open(path) as f:
        for linha in f:
            i, nome = linha.split(maxsplit=1)
            mapa[int(i)] = nome.strip()
    return mapa


def ler_resultado(path):
    with open(path) as f:
        linhas = f.read().split('\n')
    status = linhas[0].strip()
    if status != 'SAT':
        return status, set()
    lits = {int(x) for x in ' '.join(linhas[1:]).split()}
    return status, {x for x in lits if x > 0}          # 2. filtragem


def derivar_on(estado):
    """on(b, y): b esta apoiado em y."""
    on = {}
    for b, (pb, lb) in estado.items():
        if lb == 0:
            on[b] = [TABLE]
        else:
            on[b] = [y for y, (py, ly) in estado.items()
                     if y != b and ly == lb - 1
                     and spans_overlap(b, pb, y, py)]
    return on


def desenhar(estado, recuo='    '):
    """Desenho ASCII: um caractere por slot, '.' = vazio."""
    topo = max(l for _, l in estado.values())
    linhas = []
    for l in range(topo, -1, -1):
        row = ['.'] * MAX_POINT
        for b, (p, lb) in estado.items():
            if lb == l:
                for s in span(b, p):
                    row[s] = b
        linhas.append(f'{recuo}nivel {l} | ' + ' '.join(row))
    linhas.append(f'{recuo}        +' + '-' * (2 * MAX_POINT))
    linhas.append(f'{recuo}   slots  ' + ' '.join(str(s) for s in range(MAX_POINT)))
    return '\n'.join(linhas)


def frase(b, y, p):
    if y == TABLE:
        return f"mover bloco '{b}' para a MESA em p={p}"
    return f"mover bloco '{b}' para CIMA de '{y}' em p={p}"


def descrever_on(on):
    out = []
    for b in sorted(on):
        ys = on[b]
        if ys == [TABLE]:
            out.append(f'  {b} esta na MESA')
        else:
            extra = '  (ponte)' if len(ys) > 1 else ''
            out.append(f"  {b} esta sobre: {', '.join(sorted(ys))}{extra}")
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('resultado')
    ap.add_argument('--map', default='trab01_blocos2SAT.map')
    ap.add_argument('--verbose', action='store_true')
    args = ap.parse_args()

    mapa = ler_mapa(args.map)                               # 1. mapa
    status, verdadeiros = ler_resultado(args.resultado)
    if status != 'SAT':
        print(f'{status}: nao existe plano com o horizonte T usado.')
        print('Aumente o HORIZON do cenario no bw2cnf_var.py e gere o CNF de novo.')
        sys.exit(1)

    pos, niv, acoes = {}, {}, []
    for v in verdadeiros:
        nome = mapa[v]
        m = RE_AT.match(nome)
        if m:
            pos[m.group(1), int(m.group(3))] = int(m.group(2))
            continue
        m = RE_LEV.match(nome)
        if m:
            niv[m.group(1), int(m.group(3))] = int(m.group(2))
            continue
        m = RE_MV.match(nome)
        if m:
            acoes.append((int(m.group(4)), m.group(1), m.group(2),
                          int(m.group(3))))
    acoes.sort()                                            # 3. ordenacao
    T = max(t for _, t in pos)

    def estado(t):
        return {b: (pos[b, t], niv[b, t]) for b in BLOCKS}

    print(f'PLANO ENCONTRADO ({len(acoes)} acoes):')
    for i, (t, b, y, p) in enumerate(acoes, 1):
        print(f'  {i}. t={t}: {frase(b, y, p)}')

    if args.verbose:
        print('\nEXECUCAO PASSO A PASSO:')
        print('\n  t=0 (estado inicial)')
        print(desenhar(estado(0)))
        for t, b, y, p in acoes:
            print(f'\n  t={t + 1}  depois de: {frase(b, y, p)}')
            print(desenhar(estado(t + 1)))
            print(descrever_on(derivar_on(estado(t + 1))))

    print(f'\nESTADO FINAL (t={T}):')
    for b in sorted(BLOCKS):
        p, l = estado(T)[b]
        print(f'  {b}: ponto inicial p={p}, nivel l={l}')
    print(f"\nRELACOES 'on' em t={T}:")
    print(descrever_on(derivar_on(estado(T))))


if __name__ == '__main__':
    main()
