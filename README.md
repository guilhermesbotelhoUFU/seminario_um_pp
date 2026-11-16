# Autovalores por bisseção: LAPACK DSTEBZ em Fortran, Python e Python + MPI

Seminário MPI da disciplina GSI059 (Programação Paralela).

O trecho estudado é a **contagem de Sturm** da rotina `DLAEBZ` da LAPACK
(`lapack/SRC/dlaebz.f`, linhas 413–433), chamada pela `DSTEBZ`, junto com a
**bisseção** que fica em volta dela. Todas as versões calculam **todos os
autovalores** de uma matriz simétrica tridiagonal, um de cada vez.

## O que tem aqui

| Arquivo | O que é |
|---|---|
| `fortran/bissecao_serial.f90` | o trecho em Fortran, serial (comparativo) |
| `python/bissecao.py` | o mesmo trecho traduzido para Python puro, serial |
| `python/bissecao_mpi.py` | o mesmo código do Python serial, com as chamadas MPI a mais (linhas marcadas `# [MPI]`) |

As duas versões em Python têm **as mesmas funções, linha por linha**. A única
diferença está no `main()`: no paralelo, cada processo calcula só alguns
autovalores e o processo 0 junta os resultados.

## 1. Instalar (no WSL / Ubuntu)

Se ainda não tiver o WSL, no PowerShell do Windows (como administrador):

```powershell
wsl --install -d Ubuntu
```

Depois, dentro do Ubuntu:

```sh
sudo apt update
sudo apt install gfortran python3 openmpi-bin libopenmpi-dev python3-mpi4py
```

| Pacote | Para quê |
|---|---|
| `gfortran` | compilar a versão em Fortran |
| `python3` | rodar as versões em Python |
| `openmpi-bin`, `libopenmpi-dev` | o MPI (traz o comando `mpirun`) |
| `python3-mpi4py` | o MPI para Python (`from mpi4py import MPI`) |

Para conferir se ficou tudo instalado:

```sh
gfortran --version
mpirun --version
python3 -c "from mpi4py import MPI; print('mpi4py ok')"
```

## 2. Entrar na pasta

As pastas do Windows ficam em `/mnt/c/...` dentro do WSL. Por exemplo:

```sh
cd /mnt/c/caminho/para/repo
```

## 3. Rodar cada versão à mão

Todas recebem dois argumentos: `n` (tamanho da matriz) e o tipo de matriz
(`laplace` ou `aleatoria`).

**Fortran (serial)**, que precisa ser compilado antes:

```sh
gfortran -O2 -o bissecao_serial_f fortran/bissecao_serial.f90
./bissecao_serial_f 1500 laplace
```

**Python (serial):**

```sh
python3 python/bissecao.py 1500 laplace
```

**Python + MPI (paralelo)**, com 4 processos:

```sh
mpirun -np 4 python3 python/bissecao_mpi.py 1500 laplace
```

Cada execução mostra o resultado assim:

```
linguagem            : python
versão               : mpi
tamanho da matriz (n): 1500
processos (p)        : 4
tipo de matriz       : laplace
tempo (s)            : 2.204113
soma dos autovalores : 3.000000000000001e+03
menor autovalor      : 4.380646434765102e-06
maior autovalor      : 3.999995619353566e+00
```

- `tempo (s)`: tempo do cálculo, em segundos
- `soma dos autovalores`, `menor autovalor`, `maior autovalor`: servem para
  conferir que as versões deram o mesmo resultado (têm que ser iguais em todas)

Acrescentando `csv` no fim do comando, o resultado sai numa linha só, no
formato que o script de testes usa:

```sh
python3 python/bissecao.py 1500 laplace csv
# python,serial,1500,1,laplace,8.002113,3.000000000000001e+03,4.380646434765102e-06,3.999995619353566e+00
```

### As matrizes de teste

- `laplace`: 2 em toda a diagonal e −1 nas vizinhas. É a matriz usada nos
  resultados do seminário.
- `aleatoria`: valores entre −1 e 1, gerados por um gerador simples que é
  idêntico no Fortran e no Python. As duas linguagens montam exatamente a
  mesma matriz.

## 4. Como rodamos os testes

Os testes comparam as três versões com **a mesma entrada**: a matriz `laplace`
com `n = 1500`. Todos os comandos abaixo são rodados dentro da pasta `repo/`.

**Passo 1. Compilar o Fortran** (uma vez só):

```sh
gfortran -O2 -o bissecao_serial_f fortran/bissecao_serial.f90
```

**Passo 2. Rodar cada versão 3 vezes** e anotar o `tempo (s)` de cada execução:

```sh
# Fortran serial
./bissecao_serial_f 1500 laplace

# Python serial (é o tempo de referência para o speedup)
python3 python/bissecao.py 1500 laplace

# Python + MPI, com 1, 2, 4, 8 e 12 processos
mpirun -np 1  python3 python/bissecao_mpi.py 1500 laplace
mpirun -np 2  python3 python/bissecao_mpi.py 1500 laplace
mpirun -np 4  python3 python/bissecao_mpi.py 1500 laplace
mpirun -np 8  python3 python/bissecao_mpi.py 1500 laplace
mpirun -np 12 python3 python/bissecao_mpi.py 1500 laplace
```

Para não digitar tudo três vezes, dá para repetir com um laço:

```sh
for r in 1 2 3; do
  ./bissecao_serial_f 1500 laplace csv
  python3 python/bissecao.py 1500 laplace csv
  for p in 1 2 4 8 12; do
    mpirun -np $p python3 python/bissecao_mpi.py 1500 laplace csv
  done
done
```

Com `csv`, cada execução sai numa linha só; o tempo é a 6ª coluna.

**Passo 3. Calcular os resultados:**

- para cada versão, use a **mediana** dos 3 tempos (o do meio, depois de
  ordenar), para não depender de uma execução com sorte ou azar;
- **speedup** S(P) = tempo do Python serial ÷ tempo do Python + MPI com P processos;
- **eficiência** = S(P) ÷ P (100% seria o ideal);
- confira que `soma dos autovalores`, `menor autovalor` e `maior autovalor`
  deram **iguais** em todas as versões.

Exemplo do que obtivemos (Intel Core Ultra 5 225H, 14 núcleos):

| versão | P | tempo (s) | speedup | eficiência |
|---|---|---|---|---|
| Fortran serial | 1 | 0,48 | — | — |
| Python serial | 1 | 8,00 | 1,0 | 100% |
| Python + MPI | 2 | 4,26 | 1,9 | 94% |
| Python + MPI | 4 | 2,20 | 3,6 | 91% |
| Python + MPI | 8 | 1,34 | 6,0 | 75% |
| Python + MPI | 12 | 1,04 | 7,7 | 64% |

**Atenção:**
- Use `P` no máximo igual ao número de núcleos da máquina (veja com `nproc`).
  Se pedir mais processos que núcleos, o `mpirun` recusa; dá para forçar com
  `mpirun --oversubscribe`, mas aí os tempos deixam de fazer sentido.
- O Python puro é bem mais lento que o Fortran: com `n = 1500`, cada execução
  do Python serial leva uns 8 segundos. Para um teste rápido, use `n = 500`.
