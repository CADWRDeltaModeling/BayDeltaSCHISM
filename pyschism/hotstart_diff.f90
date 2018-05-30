
! compare two hotstart file 
! usage: hotstart_diff hotstart1 hotstart2
! output:l1, l2, and linf norm of difference over the whole grid
!  ifort -Bstatic -O3 -o hotstart_diff  hotstart_diff.f90 getopt.F90 schisim_geometry.f90



subroutine computeNorms(big_difference,num_var, lnorm_1,lnorm_2,lnorm_inf,sum_diff,sum_var,sum_diff_2,sum_var_2,max_diff,max_var)
  implicit none
  integer, intent(in)                           :: num_var
  real*8, intent(in)                            :: big_difference
  real*8, intent(in),    dimension(num_var)     :: sum_diff
  real*8, intent(in),    dimension(num_var)     :: sum_var
  real*8, intent(in),    dimension(num_var)     :: sum_diff_2
  real*8, intent(in),    dimension(num_var)     :: sum_var_2
  real*8, intent(in),    dimension(num_var)     :: max_diff
  real*8, intent(in),    dimension(num_var)     :: max_var
  real*8, intent(inout), dimension (num_var)    :: lnorm_1
  real*8, intent(inout), dimension (num_var)    :: lnorm_2
  real*8, intent(inout), dimension (num_var)    :: lnorm_inf
  
  
  integer indexVar
  do indexVar = 1, num_var
   if (sum_diff(indexVar).eq.0.0) then
       lnorm_1(indexVar)=0.0
   else if (sum_var(indexVar).eq.0.0) then
       lnorm_1(indexVar)=big_difference
   else
       lnorm_1(indexVar)   = sum_diff(indexVar)/sum_var(indexVar)
   end if
   
   if (sum_diff_2(indexVar).eq.0.0) then
       lnorm_2(indexVar)=0.0
   else if (sum_var_2(indexVar).eq.0.0) then
       lnorm_2(indexVar)=big_difference
   else
       lnorm_2(indexVar)   = sqrt(sum_diff_2(indexVar))/sqrt(sum_var_2(indexVar))
   end if
   
   if (max_diff(indexVar).eq.0.0) then
       lnorm_inf(indexVar)=0.0
   else if (max_var(indexVar).eq.0.0) then
       lnorm_inf(indexVar)=big_difference
   else
       lnorm_inf(indexVar) = max_diff(indexVar)/max_var(indexVar)
   end if
  enddo ! end l

end subroutine

subroutine accumlateStat(var_a,var_b,sum,sum2,sum_diff,sum_diff2,max_diff,max_var)

  implicit none
  real*8, intent(in)    :: var_a, var_b
  real*8, intent(inout) :: sum,sum2,sum_diff,sum_diff2,max_diff,max_var

  sum      = sum + abs(var_a)
  sum2     = sum2 + abs(var_a*var_a)
  sum_diff = sum_diff + abs(var_a-var_b)
  sum_diff2= sum_diff2 + (var_a-var_b)*(var_a-var_b)
  max_diff = max(max_diff,abs(var_a-var_b))
  max_var  = max(max_var,abs(var_a))

end subroutine

subroutine compare_two_hotstart_files(fname1,fname2,num_ele,num_side,num_node,num_tracer,num_layer,big_difference)
   
  implicit none
  character(*),intent(in):: fname1
  character(*),intent(in):: fname2
  integer,intent(in) :: num_ele
  integer,intent(in) :: num_side
  integer,intent(in) :: num_node
  integer,intent(in) :: num_tracer
  integer,intent(in) :: num_layer
  real*8,intent(in)  :: big_difference

  integer  num_side_var 
  integer  num_node_var 
  integer  num_ele_var
  integer  invalid_loc
  parameter(num_side_var = 4,num_node_var =11, num_ele_var =3,invalid_loc = -9999)
  Real*8 time
  Real*8 eta2_a,eta2_b,var_a,var_b
! node and side error array, size are fixed (side share node array)
  Real*8 lnorm_1(12),lnorm_2(12),lnorm_inf(12)
  Real*8 sum_diff(12),sum_diff2(12),max_diff(12),sum1(12),sum2(12), max_var(12)
  integer iths,ifile, iegb,idry_a,idry_b,isgb,ipgb,i,j,l
  integer istat
  integer indexEle,indexNode,indexSide,indexVar,indexLayer,indexError,indexTracer
! store location and layer where max diff happens
  integer max_diff_side_layer(2,12),max_diff_node_layer(2,12)
  Real*8  max_diff_so_far(12)
! num of variable defined on element dependes on model setup, use allocatable array
  integer,allocatable:: max_diff_ele_layer(:,:)
  Real*8, allocatable:: max_diff_ele_so_far(:)
  character  var_name(12)*15
  Real*8, allocatable:: buffer_1_a(:,:),buffer_2_a(:,:)
  Real*8, allocatable:: buffer_1_b(:,:),buffer_2_b(:,:)
! element data error dimension array, its size depends on num of ntracers,use allocatable array
  Real*8, allocatable:: ele_lnorm_1(:), ele_lnorm_2(:),ele_lnorm_inf(:)
  Real*8, allocatable:: ele_sum_diff(:),ele_sum_diff2(:),ele_max_diff(:)
  Real*8, allocatable:: ele_sum1(:),ele_sum2(:),ele_max_var(:)
  
   
  allocate(buffer_2_a(num_layer,num_ele_var+2*num_tracer),buffer_1_a(num_layer,num_node_var),stat=istat)
  allocate(buffer_2_b(num_layer,num_ele_var+2*num_tracer),buffer_1_b(num_layer,num_node_var),stat=istat)
  allocate(ele_lnorm_1(num_ele_var+2*num_tracer),stat=istat)
  allocate(ele_lnorm_2(num_ele_var+2*num_tracer),stat=istat)
  allocate(ele_lnorm_inf(num_ele_var+2*num_tracer),stat=istat)
  allocate(ele_sum_diff(num_ele_var+2*num_tracer),stat=istat)
  allocate(ele_sum_diff2(num_ele_var+2*num_tracer),stat=istat)
  allocate(ele_max_diff(num_ele_var+2*num_tracer),stat=istat)
  allocate(ele_sum1(num_ele_var+2*num_tracer),stat=istat)
  allocate(ele_sum2(num_ele_var+2*num_tracer),stat=istat)
  allocate(ele_max_var(num_ele_var+2*num_tracer),stat=istat)
  allocate(max_diff_ele_layer(2,num_ele_var+2*num_tracer),stat=istat)
  allocate(max_diff_ele_so_far(num_ele_var+2*num_tracer),stat=istat)
  if(istat/=0) stop 'Allocation error (3)'
  
  open(36,file=fname1,form='unformatted',status='old')
  read(36) time,iths,ifile
  open(37,file=fname2,form='unformatted',status='old')
  read(37) time,iths,ifile


  do indexError=1,num_ele_var+2*num_tracer
    ele_lnorm_1(indexError)         = 0.0
    ele_lnorm_2(indexError)         = 0.0
    ele_lnorm_inf(indexError)       = 0.0
    ele_sum_diff(indexError)        = 0.0
    ele_sum_diff2(indexError)       = 0.0
    ele_max_diff(indexError)        = 0.0
    ele_sum1(indexError)            = 0.0
    ele_sum2(indexError)            = 0.0
    ele_max_var(indexError)         = 0.0
    max_diff_ele_so_far(indexError) = 0.0
    max_diff_ele_layer(1,indexError)= 1
    max_diff_ele_layer(2,indexError)= 1
  enddo 

! Element data
  do indexEle=1,num_ele
    read(36) iegb,idry_a,((buffer_2_a(indexLayer,indexVar),indexVar=1,num_ele_var+2*num_tracer),indexLayer=1,num_layer)
    read(37) iegb,idry_a,((buffer_2_b(indexLayer,indexVar),indexVar=1,num_ele_var+2*num_tracer),indexLayer=1,num_layer)
    do indexVar=1,num_ele_var+2*num_tracer
      indexError    = indexVar
      do indexLayer=1,num_layer
        var_a                    = buffer_2_a(indexLayer,indexVar)
        var_b                    = buffer_2_b(indexLayer,indexVar)
        call accumlateStat(var_a,                    &
                           var_b,                    &
                           ele_sum1(indexError),     &
                           ele_sum2(indexError),     &
                           ele_sum_diff(indexError), &
                           ele_sum_diff2(indexError),&
                           ele_max_diff(indexError), &
                           ele_max_var(indexError))
        if (ele_max_diff(indexError).gt.max_diff_ele_so_far(indexError)) then
           max_diff_ele_so_far(indexError)  = ele_max_diff(indexError)
           max_diff_ele_layer(1,indexError) = indexEle
           max_diff_ele_layer(2,indexError) = indexLayer
        end if
      enddo ! indexLayer
    enddo ! indexVar
  enddo !indexEle


  call computeNorms(big_difference,           &
                    num_ele_var+2*num_tracer, &
                    ele_lnorm_1,              &
                    ele_lnorm_2,              &
                    ele_lnorm_inf,            &
                    ele_sum_diff,             &
                    ele_sum1,                 &
                    ele_sum_diff2,            &
                    ele_sum2,                 &
                    ele_max_diff,             &
                    ele_max_var)


  write(*,8) 
8 format("--------------------------------------------------------------------------")
  write(*,10) "ele_variable","l1_norm","l2_norm","linf_norm","inf_norm_loc"
10 format(1x,A15,4A15)

  if (ele_lnorm_inf(1).ne.0.0) then
    write(*,11) "vertical_vel", ele_lnorm_1(1), ele_lnorm_2(1),ele_lnorm_inf(1),max_diff_ele_layer(1,1)
  else
    write(*,1100) "vertical_vel", ele_lnorm_1(1), ele_lnorm_2(1),ele_lnorm_inf(1)
  endif
  if (ele_lnorm_inf(2).ne.0.0) then
    write(*,11) "temperature",         ele_lnorm_1(2), ele_lnorm_2(2),ele_lnorm_inf(2),max_diff_ele_layer(1,2)
  else
    write(*,1100) "temperature",         ele_lnorm_1(2), ele_lnorm_2(2),ele_lnorm_inf(2)
  endif
  
  if (ele_lnorm_inf(3).ne.0.0) then
    write(*,11) "salt",  ele_lnorm_1(3), ele_lnorm_2(3),ele_lnorm_inf(3),max_diff_ele_layer(1,3)
  else
    write(*,1100) "salt",  ele_lnorm_1(3), ele_lnorm_2(3),ele_lnorm_inf(3)
  endif
  
11 format(1x,A15,3e15.6,I15)
1100 format(1x,A15,3e15.6,"          NA")
  do indexTracer = 1, num_tracer
    indexVar = indexTracer*2-1
    if (lnorm_inf(indexVar+num_ele_var).ne.0) then
      write(*,12) "tracer0_",indexVar, ele_lnorm_1(indexVar+num_ele_var),lnorm_2(indexVar+num_ele_var),lnorm_inf(indexVar+num_ele_var),max_diff_ele_layer(1,indexVar)
    else
      write(*,1200) "tracer0_",indexVar, ele_lnorm_1(indexVar+num_ele_var),lnorm_2(indexVar+num_ele_var),lnorm_inf(indexVar+num_ele_var)
    endif
    if (lnorm_inf(indexVar+1+num_ele_var).ne.0) then
      write(*,12) "tracer_", indexVar+1, ele_lnorm_1(indexVar+1+num_ele_var),lnorm_2(indexVar+1+num_ele_var),lnorm_inf(indexVar+1+num_ele_var),max_diff_ele_layer(1,indexVar+1)
    else
      write(*,1200) "tracer_", indexVar+1, ele_lnorm_1(indexVar+1+num_ele_var),lnorm_2(indexVar+1+num_ele_var),lnorm_inf(indexVar+1+num_ele_var)
    endif
  enddo ! end l
12 format(1x,A12,I3,3e15.6,I15)
1200 format(1x,A12,I3,3e15.6,"          NA")

  deallocate(buffer_2_a,stat=istat)
  if(istat/=0) stop 'Deallocation error buffer_2_a'
  deallocate(buffer_2_b,stat=istat)
  if(istat/=0) stop 'Deallocation error buffer_2_b'
  deallocate(ele_lnorm_1,stat=istat)
  if(istat/=0) stop 'Deallocation error ele_lnorm_1'
  deallocate(ele_lnorm_2,stat=istat)
  if(istat/=0) stop 'Deallocation error ele_lnorm_2'
  deallocate(ele_lnorm_inf,stat=istat)
  if(istat/=0) stop 'Deallocation error ele_lnorm_inf'
  deallocate(ele_sum_diff,stat=istat)
  if(istat/=0) stop 'Deallocation error ele_sum_diff'
  deallocate(ele_sum_diff2,stat=istat)
  if(istat/=0) stop 'Deallocation error ele_sum_diff2'
  deallocate(ele_max_diff,stat=istat)
  if(istat/=0) stop 'Deallocation error ele_max_diff'
  deallocate(ele_sum1,stat=istat)
  if(istat/=0) stop 'Deallocation error ele_sum1'
  deallocate(ele_sum2,stat=istat)
  if(istat/=0) stop 'Deallocation error ele_sum2'
  deallocate(ele_max_var,stat=istat)
  if(istat/=0) stop 'Deallocation error ele_max_var'
  deallocate(max_diff_ele_layer, stat=istat)
  if(istat/=0) stop 'Deallocation error max_diff_ele_layer'
  deallocate(max_diff_ele_so_far,stat=istat)
  if(istat/=0) stop 'Deallocation error max_diff_ele_so_far'



  do indexError=1,12
    lnorm_1(indexError)         = 0.0
    lnorm_2(indexError)         = 0.0
    lnorm_inf(indexError)       = 0.0
    sum_diff(indexError)        = 0.0
    sum_diff2(indexError)       = 0.0
    max_diff(indexError)        = 0.0
    sum1(indexError)            = 0.0
    sum2(indexError)            = 0.0
    max_var(indexError)         = 0.0
    max_diff_so_far(indexError) = 0.0
    max_diff_side_layer(1,indexError)= 1
    max_diff_side_layer(2,indexError)= 1
  enddo

! Side data
  do indexSide=1,num_side
    read(36) isgb,idry_a,((buffer_1_a(indexLayer,indexVar),indexVar=1,num_side_var),indexLayer=1,num_layer)
    read(37) isgb,idry_a,((buffer_1_b(indexLayer,indexVar),indexVar=1,num_side_var),indexLayer=1,num_layer)
    do indexVar=1, num_side_var
      indexError    = indexVar
      do indexLayer=1,num_layer
         var_a                = buffer_1_a(indexLayer,indexVar)
         var_b                = buffer_1_b(indexLayer,indexVar)
         call accumlateStat(var_a,                &
                            var_b,                &
                            sum1(indexError),     &
                            sum2(indexError),     &
                            sum_diff(indexError), &
                            sum_diff2(indexError),&
                            max_diff(indexError), &
                            max_var(indexError))
          if (max_diff(indexError).gt.max_diff_so_far(indexError)) then
              max_diff_so_far(indexError)  = max_diff(indexError)
              max_diff_side_layer(1,indexError) = indexSide
              max_diff_side_layer(2,indexError) = indexLayer
          end if
       
      enddo ! layer
    enddo ! var
  enddo !side

 

 call computeNorms(big_difference,       &
                   num_side_var,         &
                   lnorm_1,              &
                   lnorm_2,              &
                   lnorm_inf,            &
                   sum_diff,             &
                   sum1,                 &
                   sum_diff2,            &
                   sum2,                 &
                   max_diff,             &
                   max_var)


  var_name(1) = "u"
  var_name(2) = "v"
  var_name(3) = "temp"
  var_name(4) = "salt"

  write(*,8) 
  write(*,100) "side_variable","l1_norm","l2_norm","linf_norm","inf_norm_loc"
  do indexVar = 1, num_side_var
    if ( lnorm_inf(indexVar).ne.0.) then
      write(*,110) trim(var_name(indexVar)),lnorm_1(indexVar),lnorm_2(indexVar),lnorm_inf(indexVar),max_diff_side_layer(1,indexVar)
    else
      write(*,150) trim(var_name(indexVar)),lnorm_1(indexVar),lnorm_2(indexVar),lnorm_inf(indexVar)
    end if
  enddo ! end l

  do indexError=1,12
    lnorm_1(indexError)         = 0.0
    lnorm_2(indexError)         = 0.0
    lnorm_inf(indexError)       = 0.0
    sum_diff(indexError)        = 0.0
    sum_diff2(indexError)       = 0.0
    max_diff(indexError)        = 0.0
    sum1(indexError)            = 0.0
    sum2(indexError)            = 0.0
    max_var(indexError)         = 0.0
    max_diff_so_far(indexError) = 0.0
    max_diff_node_layer(1,indexError) = 1
    max_diff_node_layer(2,indexError) = 1
  enddo
  print * ,"num_node_var is",num_node_var
! Node data 
  do indexNode=1,num_node
    read(36) ipgb,eta2_a,idry_a,((buffer_1_a(indexLayer,indexVar),indexVar=1,num_node_var),indexLayer=1,num_layer)
    read(37) ipgb,eta2_b,idry_b,((buffer_1_b(indexLayer,indexVar),indexVar=1,num_node_var),indexLayer=1,num_layer)
  
    call accumlateStat(eta2_a,      &
                       eta2_b,      &
                       sum1(1),     &
                       sum2(1),     &
                       sum_diff(1), &
                       sum_diff2(1),&
                       max_diff(1), &
                       max_var(1))
   
     if (max_diff(1).gt.max_diff_so_far(1)) then
         max_diff_so_far(1)  = max_diff(1)
         max_diff_node_layer(1,1) = indexNode
         max_diff_node_layer(2,1) = 1
     end if
    
! compute error of layered variables
    do indexVar=1, num_node_var
      indexError    = indexVar+1
      do indexLayer=1,num_layer
        var_a                = buffer_1_a(indexLayer,indexVar)
        var_b                = buffer_1_b(indexLayer,indexVar)
        call accumlateStat(var_a,                &
                           var_b,                &
                           sum1(indexError),     &
                           sum2(indexError),     &
                           sum_diff(indexError), &
                           sum_diff2(indexError),&
                           max_diff(indexError), &
                           max_var(indexError))
        if (max_diff(indexError).gt.max_diff_so_far(indexError)) then
            max_diff_so_far(indexError)       = max_diff(indexError)
            max_diff_node_layer(1,indexError) = indexNode
            max_diff_node_layer(2,indexError) = indexLayer
         end if
       
      enddo ! end indexLayer
    enddo ! end indexVar
  enddo ! end i

 
 call computeNorms(big_difference,       &
                   num_node_var+1,       &
                   lnorm_1,              &
                   lnorm_2,              &
                   lnorm_inf,            &
                   sum_diff,             &
                   sum1,                 &
                   sum_diff2,            &
                   sum2,                 &
                   max_diff,             &
                   max_var)



  var_name(1) = "eta"
  var_name(2) = "temp_node"
  var_name(3) = "salt_node"
  var_name(4) = "temp0"
  var_name(5) = "salt0"
  var_name(6) = "q2"
  var_name(7) = "xl"
  var_name(8) = "dfv"
  var_name(9) = "dfh"
  var_name(10)= "dfq1"
  var_name(11)= "dfq2"
  var_name(12)= "qnon"

  write(*,8)  
  write(*,100) "node_variable","l1_norm","l2_norm","linf_norm","inf_norm_loc"
100 format(1x,A15,4A15)
110 format(1x,A15,3e15.6,I15)
150 format(1x,A15,3e15.6,"          NA")
  do indexVar = 1, 12
    if (lnorm_inf(indexVar).ne.0.0) then 
       write(*,110) trim(var_name(indexVar)),lnorm_1(indexVar),lnorm_2(indexVar),lnorm_inf(indexVar),max_diff_node_layer(1,indexVar)
    else
       write(*,150) trim(var_name(indexVar)),lnorm_1(indexVar),lnorm_2(indexVar),lnorm_inf(indexVar)  
    endif
  enddo ! end indexVar
  write(*,8)  
 
  deallocate(buffer_1_a,stat=istat)
  if(istat/=0) stop 'Deallocation error buffer_1_a'
  deallocate(buffer_1_b,stat=istat)
  if(istat/=0) stop 'Deallocation error buffer_1_b'
 
  close(36)
  close(37)
end subroutine compare_two_hotstart_files


program hotstart_diff
  use getopt_m
  implicit none
  character*60 hot_start_1,hot_start_2
  character*30 hgridfile,vgridfile
  character*12 it_char
  character*48 start_time,version,variable_nm,variable_dim
  character*48 data_format
  character*30 dummy_char
  character(72) :: fgb,fgb2,fdb  ! Processor specific global output file name
  integer :: lfgb,lfdb       ! Length of processor specific global output file name
  integer,allocatable::i34(:)
  !allocatable ielg(:,:),iplg(:,:),islg(:,:) 
  integer, allocatable :: elnode(:,:)
  type(option_s):: opts(3)
  LOGICAL :: fileexists
  
  real*8,parameter::big_difference=1000.0
  integer ne_global,np_global,nvrt,ns_global,ntracers,istat
  integer ioerr,inode,ielement,i,j
! get two hotstart file input

  
  hgridfile="hgrid.gr3"
  vgridfile="vgrid.in"
  
  ntracers=0
  opts(1) = option_s( "file1", .true., '1' )
  opts(2) = option_s( "file2",  .true.,  '2' )
  opts(3) = option_s("ntracers",.true.,'n')
  opts(3) = option_s("help",.true.,'h')
  do
     select case( getopt( "1:2:n:h", opts ))
            case( char(0))
                exit
            case( '1' )
                hot_start_1=adjustl(optarg)
            case( '2' )
                hot_start_2=adjustl(optarg)
            case('n')
                read(optarg,*)ntracers
            case('h')
                write(*,*) 'hotstart_diff.exe'
                write(*,*) 'Utility program to compare two hotstar files and print out difference metrics'
                write(*,*) 'usage:'
                write(*,*) '$ hotstart_diff  -1 hotstart1 -2 hotstart2 [-n ntracers]'
                write(*,*) 'where'
                write(*,*) 'hotstart1 is the name of the first hot start file'
                write(*,*) 'hotstart2 is the name of the second hot start file'
                write(*,*)  'ntracers is the number of tracers in each file, default 0.'
                write(*,*)  'this program assume you have hgrid.gr3 and vgrid.in'
                write(*,*)  'current working directory'
                stop
            case( '?' )
                print *, 'unknown option ', optopt
                stop
            case default
                exit
      end select
  end do
          
    
  INQUIRE(FILE=hot_start_1, EXIST=fileexists)
  if (.not.fileexists) then
        print *, "first hotstart file is invalid"
        stop
  endif
  INQUIRE(FILE=hot_start_2, EXIST=fileexists)
  if (.not.fileexists) then
        print *, "second hotstart file is invalid"
        stop
  endif
  
  
  INQUIRE(FILE=hgridfile, EXIST=fileexists)
  if (.not.fileexists) then
        print *, hgridfile,"is invalid"
        stop
  endif
  INQUIRE(FILE=vgridfile, EXIST=fileexists)
  if (.not.fileexists) then
        print *, vgridfile,"is invalid"
        stop
  endif
       
  
        
  
!------------------------------------------------------------------------------------
!Acquire mesh dimension: number of nodes, cell and element table from hgrid.gr3
!------------------------------------------------------------------------------------
  open(10,file=hgridfile,status='old',iostat=ioerr)
  if (ioerr.ne.0) then
      print *, "no hgrid.gr3"
      stop
  end if
  read(10,*)
  read(10,*) ne_global,np_global
  
! read elemen table
  allocate(elnode(4,ne_global),stat=istat) 
  if(istat/=0) stop 'elnode allocation error'

  allocate(i34(ne_global),stat=istat) 
  if(istat/=0) stop 'i34 allocation error'
  
  do inode=1,np_global
      read(10,*)
  end do
  
  do ielement=1,ne_global
      read(10,*) i,i34(ielement),elnode(1:i34(ielement),ielement)
  end do
  
  close(10)
  
  open(10,file=vgridfile,status='old',iostat=ioerr)
  if (ioerr.ne.0) then
      print *, "no vgrid.in"
      stop
  end if
  read(10,*)
  read(10,*) nvrt
  close(10)
  
  call compute_nside(np_global,ne_global,i34,elnode,ns_global)

 

  call compare_two_hotstart_files(trim(hot_start_1),&
                                   trim(hot_start_2),&
                                   ne_global,        &
                                   ns_global,        &
                                   np_global,        &
                                   ntracers,         & 
                                   nvrt,             &
                                   big_difference)

  deallocate(elnode,stat=istat)
  if(istat/=0) stop 'Deallocation error elnode'
  deallocate(i34,stat=istat)
  if(istat/=0) stop 'Deallocation error i34'
 
end program hotstart_diff
