! bissecao_serial.f90 -- versão serial em Fortran, mesmo algoritmo da versão em
! Python. A função STURM é o laço DO 50 de lapack/SRC/dlaebz.f.
!
! Compilar: gfortran -O2 -o bissecao_serial_f bissecao_serial.f90
! Rodar:    ./bissecao_serial_f 1500 laplace
!           ./bissecao_serial_f 1500 laplace csv   (resultado numa linha CSV)
program bissecao_serial
   implicit none
   integer, parameter :: dp = kind(1.0d0)
   integer, parameter :: itmax = 200
   integer :: n, tipo, k
   logical :: csv
   real(dp), allocatable :: d(:), e(:), e2(:), w(:)
   real(dp) :: pivmin, gl, gu, tempo
   integer(8) :: c0, c1, taxa

   call ler_args(n, tipo, csv)
   allocate (d(n), e(n - 1), e2(n - 1), w(n))
   call gerar_matriz(n, tipo, d, e)

   call system_clock(c0, taxa)
   call preparar(n, d, e, e2, pivmin, gl, gu)
   do k = 1, n
      w(k) = bissecao_k(n, d, e2, pivmin, gl, gu, k)
   end do
   call system_clock(c1)
   tempo = real(c1 - c0, dp)/real(taxa, dp)

   call imprimir('serial', n, tipo, tempo, w, csv)

contains

   subroutine gerar_matriz(n, tipo, d, e)
      integer, intent(in) :: n, tipo
      real(dp), intent(out) :: d(n), e(n - 1)
      integer(8) :: estado
      integer :: i
      estado = 2026_8
      do i = 1, n
         if (tipo == 0) then
            d(i) = 2.0_dp
         else
            estado = mod(1103515245_8*estado + 12345_8, 2147483648_8)
            d(i) = 2.0_dp*real(estado, dp)/2147483648.0_dp - 1.0_dp
         end if
      end do
      do i = 1, n - 1
         if (tipo == 0) then
            e(i) = -1.0_dp
         else
            estado = mod(1103515245_8*estado + 12345_8, 2147483648_8)
            e(i) = 2.0_dp*real(estado, dp)/2147483648.0_dp - 1.0_dp
         end if
      end do
   end subroutine

   subroutine preparar(n, d, e, e2, pivmin, gl, gu)
      integer, intent(in) :: n
      real(dp), intent(in) :: d(n), e(n - 1)
      real(dp), intent(out) :: e2(n - 1), pivmin, gl, gu
      real(dp) :: r, lo, hi, tnorm, folga
      integer :: i
      e2 = e*e
      pivmin = tiny(1.0_dp)*max(1.0_dp, maxval(e2))
      lo = d(1)
      hi = d(1)
      do i = 1, n
         r = 0.0_dp
         if (i > 1) r = r + abs(e(i - 1))
         if (i < n) r = r + abs(e(i))
         lo = min(lo, d(i) - r)
         hi = max(hi, d(i) + r)
      end do
      tnorm = max(abs(lo), abs(hi))
      folga = 2.0_dp*epsilon(1.0_dp)*n*tnorm + 2.0_dp*pivmin
      gl = lo - folga
      gu = hi + folga
   end subroutine

   ! Contagem de Sturm: quantos autovalores são menores que x.
   integer function sturm(n, d, e2, pivmin, x)
      integer, intent(in) :: n
      real(dp), intent(in) :: d(n), e2(n - 1), pivmin, x
      real(dp) :: t
      integer :: j
      sturm = 0
      t = d(1) - x
      if (t <= pivmin) then
         sturm = 1
         t = min(t, -pivmin)
      end if
      do j = 2, n
         t = d(j) - e2(j - 1)/t - x
         if (t <= pivmin) then
            sturm = sturm + 1
            t = min(t, -pivmin)
         end if
      end do
   end function

   ! Bisseção para o k-ésimo menor autovalor.
   real(dp) function bissecao_k(n, d, e2, pivmin, gl, gu, k)
      integer, intent(in) :: n, k
      real(dp), intent(in) :: d(n), e2(n - 1), pivmin, gl, gu
      real(dp) :: lo, hi, mid
      integer :: it
      lo = gl
      hi = gu
      do it = 1, itmax
         if (hi - lo <= 2.0_dp*epsilon(1.0_dp)*max(abs(lo), abs(hi)) + pivmin) exit
         mid = 0.5_dp*(lo + hi)
         if (sturm(n, d, e2, pivmin, mid) >= k) then
            hi = mid
         else
            lo = mid
         end if
      end do
      bissecao_k = 0.5_dp*(lo + hi)
   end function

   subroutine ler_args(n, tipo, csv)
      integer, intent(out) :: n, tipo
      logical, intent(out) :: csv
      character(len=32) :: arg
      n = 2000
      tipo = 0
      csv = .false.
      if (command_argument_count() >= 3) then
         call get_command_argument(3, arg)
         csv = (trim(arg) == 'csv')
      end if
      if (command_argument_count() >= 1) then
         call get_command_argument(1, arg)
         read (arg, *) n
      end if
      if (command_argument_count() >= 2) then
         call get_command_argument(2, arg)
         if (trim(arg) == 'aleatoria') tipo = 1
      end if
      if (n < 2) stop 'argumentos: n [laplace|aleatoria] [csv]  (n >= 2)'
   end subroutine

   ! Mostra o resultado: um campo por linha, ou uma linha CSV se csv = .true.
   ! (linguagem,versao,n,p,tipo,tempo_s,soma,lambda_min,lambda_max)
   subroutine imprimir(versao, n, tipo, tempo, w, csv)
      character(len=*), intent(in) :: versao
      integer, intent(in) :: n, tipo
      real(dp), intent(in) :: tempo, w(n)
      logical, intent(in) :: csv
      character(len=16) :: nome_tipo
      character(len=32) :: s_tempo, s_soma, s_min, s_max
      if (tipo == 0) then
         nome_tipo = 'laplace'
      else
         nome_tipo = 'aleatoria'
      end if
      write (s_tempo, '(F14.6)') tempo
      write (s_soma, '(ES23.15E3)') sum(w)
      write (s_min, '(ES23.15E3)') w(1)
      write (s_max, '(ES23.15E3)') w(n)
      if (csv) then
         write (*, '(A,",",A,",",I0,",1,",A,4(",",A))') 'fortran', versao, n, &
            trim(nome_tipo), trim(adjustl(s_tempo)), trim(adjustl(s_soma)), &
            trim(adjustl(s_min)), trim(adjustl(s_max))
      else
         write (*, '(A)') 'linguagem            : fortran'
         write (*, '(A,A)') 'versão               : ', versao
         write (*, '(A,I0)') 'tamanho da matriz (n): ', n
         write (*, '(A)') 'processos (p)        : 1'
         write (*, '(A,A)') 'tipo de matriz       : ', trim(nome_tipo)
         write (*, '(A,A)') 'tempo (s)            : ', trim(adjustl(s_tempo))
         write (*, '(A,A)') 'soma dos autovalores : ', trim(adjustl(s_soma))
         write (*, '(A,A)') 'menor autovalor      : ', trim(adjustl(s_min))
         write (*, '(A,A)') 'maior autovalor      : ', trim(adjustl(s_max))
      end if
   end subroutine

end program
