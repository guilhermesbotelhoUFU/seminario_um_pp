import sys
import time

# Constantes numéricas (as mesmas que o Fortran usa com epsilon() e tiny())
PRECISAO_MAQUINA = sys.float_info.epsilon  # ~2,2e-16: menor diferença relativa entre dois números
MENOR_NUMERO = sys.float_info.min          # ~2,2e-308: menor número positivo representável
MAX_ITERACOES = 200                        # limite de segurança da bisseção (na prática, ~55 passos)


def gerar_matriz(n, tipo):
    """Monta a matriz tridiagonal de entrada, guardada só como dois vetores.

    diagonal: os n números da diagonal principal
    vizinhas: os n-1 números logo acima da diagonal (e, por simetria, logo abaixo)
    """
    if tipo == "laplace":
        # matriz do teste: 2 em toda a diagonal e -1 nas vizinhas
        return [2.0] * n, [-1.0] * (n - 1)

    # matriz "aleatoria": gerador congruente linear igual ao da versão em Fortran,
    # para que as duas linguagens montem exatamente os mesmos números
    estado = 2026

    def proximo_aleatorio():
        nonlocal estado
        estado = (1103515245 * estado + 12345) % 2147483648
        return estado / 2147483648.0  # número entre 0 e 1

    diagonal = [2.0 * proximo_aleatorio() - 1.0 for _ in range(n)]
    vizinhas = [2.0 * proximo_aleatorio() - 1.0 for _ in range(n - 1)]
    return diagonal, vizinhas


def preparar(diagonal, vizinhas):
    """Contas feitas uma vez só, antes de procurar os autovalores."""
    n = len(diagonal)

    # a contagem de Sturm usa o quadrado das vizinhas: calcula uma vez e reaproveita
    vizinhas_ao_quadrado = [v * v for v in vizinhas]

    # pivô mínimo: um pivô menor que isso é tratado como zero (evita dividir por zero)
    pivo_minimo = MENOR_NUMERO * max([1.0] + vizinhas_ao_quadrado)

    # discos de Gershgorin: todo autovalor fica a no máximo "raio" de algum número da
    # diagonal, onde raio = soma das vizinhas daquela linha. Isso dá um intervalo
    # [limite_inferior, limite_superior] que com certeza contém todos os autovalores.
    limite_inferior = limite_superior = diagonal[0]
    for i in range(n):
        raio = ((abs(vizinhas[i - 1]) if i > 0 else 0.0)
                + (abs(vizinhas[i]) if i < n - 1 else 0.0))
        limite_inferior = min(limite_inferior, diagonal[i] - raio)
        limite_superior = max(limite_superior, diagonal[i] + raio)

    # folga pequena para não perder, por arredondamento, um autovalor bem na borda
    maior_modulo = max(abs(limite_inferior), abs(limite_superior))
    folga = 2.0 * PRECISAO_MAQUINA * n * maior_modulo + 2.0 * pivo_minimo
    return (vizinhas_ao_quadrado, pivo_minimo,
            limite_inferior - folga, limite_superior + folga)


def contagem_sturm(diagonal, vizinhas_ao_quadrado, pivo_minimo, x):
    """Quantos autovalores da matriz são menores que x.

    É o trecho escolhido da LAPACK (dlaebz.f, laço DO 50). Faz a eliminação de
    Gauss de (matriz - x·I), um pivô por linha, e conta quantos pivôs deram
    negativos. Não calcula nenhum autovalor: só responde "quantos estão abaixo de x".
    """
    # 1º pivô: primeiro número da diagonal, menos x
    pivo = diagonal[0] - x
    negativos = 0
    if pivo <= pivo_minimo:
        negativos = 1
        pivo = min(pivo, -pivo_minimo)  # pivô ~zero: trata como negativo bem pequeno

    # demais pivôs, cada um a partir do anterior (por isso este laço é sequencial):
    # pivô(j) = diagonal(j) - vizinha(j-1)² / pivô(j-1) - x
    for j in range(1, len(diagonal)):
        pivo = (diagonal[j]
                - vizinhas_ao_quadrado[j - 1] / pivo
                - x)
        if pivo <= pivo_minimo:
            negativos += 1
            pivo = min(pivo, -pivo_minimo)
    return negativos


def bissecao(diagonal, vizinhas_ao_quadrado, pivo_minimo,
             limite_inferior, limite_superior, k):
    """Acha o k-ésimo menor autovalor (k = 1, 2, ..., n) por bisseção.

    Como adivinhar um número com dicas de "maior ou menor": a cada passo testa o
    meio do intervalo, e a contagem de Sturm diz de que lado o autovalor está.
    """
    inferior = limite_inferior
    superior = limite_superior
    for _ in range(MAX_ITERACOES):
        # para quando o intervalo ficar do tamanho da precisão da máquina
        tolerancia = (2.0 * PRECISAO_MAQUINA * max(abs(inferior), abs(superior))
                      + pivo_minimo)
        if superior - inferior <= tolerancia:
            break
        meio = 0.5 * (inferior + superior)
        abaixo_do_meio = contagem_sturm(diagonal, vizinhas_ao_quadrado,
                                        pivo_minimo, meio)
        if abaixo_do_meio >= k:
            superior = meio  # k ou mais abaixo do meio: o k-ésimo está na metade de baixo
        else:
            inferior = meio  # menos de k abaixo do meio: o k-ésimo está na metade de cima
    return 0.5 * (inferior + superior)


def ler_argumentos():
    """Lê da linha de comando: o tamanho n da matriz, o tipo de matriz e,
    opcionalmente, "csv" para imprimir o resultado numa linha só (usado pelo script)."""
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    tipo = sys.argv[2] if len(sys.argv) > 2 else "laplace"
    formato_csv = len(sys.argv) > 3 and sys.argv[3] == "csv"
    if n < 2 or tipo not in ("laplace", "aleatoria"):
        sys.exit("argumentos: n [laplace|aleatoria] [csv]   (n >= 2)")
    return n, tipo, formato_csv


def imprimir(versao, n, num_processos, tipo, tempo, autovalores, formato_csv):
    """Mostra o resultado: um campo por linha, ou uma linha CSV se formato_csv
    (linguagem,versao,n,p,tipo,tempo_s,soma,lambda_min,lambda_max)."""
    soma = 0.0
    for valor in autovalores:  # soma simples, na mesma ordem do Fortran
        soma += valor          # (o sum() do Python compensa erros e daria outro arredondamento)
    if formato_csv:
        print(f"python,{versao},{n},{num_processos},{tipo},{tempo:.6f},{soma:.15e},"
              f"{autovalores[0]:.15e},{autovalores[-1]:.15e}")
    else:
        print(f"linguagem            : python")
        print(f"versão               : {versao}")
        print(f"tamanho da matriz (n): {n}")
        print(f"processos (p)        : {num_processos}")
        print(f"tipo de matriz       : {tipo}")
        print(f"tempo (s)            : {tempo:.6f}")
        print(f"soma dos autovalores : {soma:.15e}")
        print(f"menor autovalor      : {autovalores[0]:.15e}")
        print(f"maior autovalor      : {autovalores[-1]:.15e}")


def main():
    n, tipo, formato_csv = ler_argumentos()
    diagonal, vizinhas = gerar_matriz(n, tipo)

    inicio = time.perf_counter()
    (vizinhas_ao_quadrado, pivo_minimo,
     limite_inferior, limite_superior) = preparar(diagonal, vizinhas)

    # um autovalor de cada vez, do menor (k = 1) ao maior (k = n)
    autovalores = [bissecao(diagonal, vizinhas_ao_quadrado, pivo_minimo,
                            limite_inferior, limite_superior, k)
                   for k in range(1, n + 1)]
    tempo = time.perf_counter() - inicio

    imprimir("serial", n, 1, tipo, tempo, autovalores, formato_csv)


if __name__ == "__main__":
    main()
