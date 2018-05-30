!>    Generate elev2D.th using 1 series at SF (scaled SF according to M2 amp.)
!!    History: (1) change to NAVD88 as vdatum; 
!!             (2) used 1 series at SF instead of 2 (SF and Pt Reyes)
!!             (3) replace "implicit real*8(a-h,o-z)" to "implicit none" and 
!!                 document and clean up code
!!             (4) replace hard coded value of mid_node id with (x,y) location, and 
!!                 derive mid_node id based on the minimum distance between nodes
!!             (5) Arguments are accepted to choose input files.
!!    Inputs: 
!!       (1) (x,y) of the mid_node (in hgrid.gr3) - see below
!!       (2) scaling factor and time lead @ SF - see below
!!       (3) hgrid.gr3 (first bnd is ocean bnd and bnd node #1 is Pt Reyes)
!!       (4) ocean.gr3, ocean.ap: ocean grid and amp/phase generated from Webtide
!!       (5) SF.th: SF time series - time (sec from start of run,
!!                         1st time stamp is dt, which may be different from param.in;
!!                         should use a small dt to better capture the lead), elev 
!!    Outputs: elev2D.th (same dt as *.th); may use plot_elev3D.m to plot
!!    Use timeint_3Dth2 to adjust time step to final one in param.in

!!    ifort -debug -O0 -o gen_elev3D_4_NAVD88 gen_elev2D_4_NAVD88.f90 (to be used with Intel debugger)
!!    ifort -Bstatic -assume byterecl -O2 -o gen_elev2D_4_NAVD88 gen_elev3D_4_NAVD88.f90

	  program gen_elev2D_4_NAVD88
	  
	  implicit none
	  real (kind=8) :: amp_m2 !< average amplitude at parent element
	  real (kind=8), dimension(:,:,:), allocatable :: ap !< harmonic constitutes (amplitude, phase) predicted by WebTide
	  character(len=30) :: char1 !< temp variable used for reading the name of harmonic constituents 
	  real (kind=8), dimension(:), allocatable :: dp !< depth of nodes in the computation grid (hgrid.gr3)
	  real (kind=8), dimension(:), allocatable :: dp_oc!< depth of nodes in the ocean grid (ocean.gr3)
	  real (kind=8) :: dt !< time step in sec, defined by the 1st time stamp in SF.th
	  real (kind=8), dimension(:), allocatable :: eta !< water elevation at ocean boundary nodes 
	  integer :: find_nearest_node !< function used to find the nearest node id in a grid for a specific point in space
	  character(len=2) :: frname !< the name of harmonic constituents, i.e. M2, O1
	  integer :: ie_oc_sf !< parent element # in ocean.gr3 for the mid node along the ocean boundary
	  integer, dimension(:), allocatable :: iep !< parenet element number of ocean boundary nodes 
	  integer :: ifl !< a flag indicating whether parent elements identified for all boundary nodes
	  integer :: iM2 !< the index of harmonic constitutents data corresponsing to M2
	  integer :: imid_node !< node number at the mid-point of the oocean boundary
	  integer, dimension(:), allocatable :: iond !< node number on the open ocean boundary (open boundary 1)
	  integer :: irecl !< record length used in the output binary file
	  integer :: istat !< flag used to capture return status of allocate() function
	  integer :: it_lead !< =sf_lead/dt, time step lead between mid_node and SF gauge
	  integer :: mid_node !< ocean bnd node # facing SF (middle of bnd) in hgrid.gr3
	  integer :: nbyte !< number of bytes per data used in the output
	  integer :: ne,np !< number of elements and nodes in the computation grid (hgrid.gr3)
	  integer :: ne_oc,np_oc !< number of elements and nodes in the ocean grid (ocean.gr3)
	  integer :: neta !< total number of open boundary nodes
	  integer :: nfr !< number of harmonic constitutents in ocean.ap file
	  integer, dimension(:,:), allocatable :: nm !< element number in the computation grid (hgrid.gr3)
	  integer, dimension(:,:), allocatable :: nm_oc !< element number in the ocean grid (ocean.gr3)
	  integer :: nond !< total number of nodes for open boundary 1
	  integer :: nope !< total number of open boundaries
	  integer :: np2 !< number of nodes in ocean.ap file, should be the same as np
	  integer :: nstep !< =nt2, total record number of the input time series of tide at SF
	  real (kind=8) :: sf_lead !< time lead (in sec) between mid_node and SF gauge
	  real (kind=8) :: sf_scale !<scaling factor between mid_node and SF gauge
	  real (kind=8) :: signa !< function used to compute signed area formed by pts 1,2,3
	  real (kind=8), dimension(:), allocatable :: sf_elev !< reference water elevation at SF
	  real (kind=8) :: sf_m2 !< average amplitude at the mid-node of the ocean boundary
	  real (kind=8), dimension(3) :: swild !< temp storages used to calculate average of 3 values
	  real (kind=8) :: vdatum_shift !<shift in vdatum between ocean and SF gauge
	  real (kind=8), dimension(:), allocatable :: wei !< weighting factor for ocean boundary nodes 
	  real (kind=8) :: x_mid_node !< x-coor of the middle node on the ocean boundary
	  real (kind=8), dimension(:), allocatable :: x_oc !< x-coor of nodes in the ocean grid (ocean.gr3)
	  real (kind=8), dimension(:), allocatable :: xnd !< x-coor of nodes in the computation grid (hgrid.gr3)
	  real (kind=8) :: y_mid_node !< y-coor of the middle node on the ocean boundary
	  real (kind=8), dimension(:), allocatable :: y_oc !< y-coor of nodes in the ocean grid (ocean.gr3)
	  real (kind=8), dimension(:), allocatable :: ynd !< y-coor of nodes in the computation grid (hgrid.gr3)
          integer :: i, j, k, l, it, jnd, j1, j2, n0, n1, n2, it2, nt2 !< temp variables
	  real (kind=8) :: aa, ar, ae, time, tmp !< temp variables
	  
          character(len=255), dimension(4) :: fnames  ! tide time series file
          character(len=255) :: arg

	  parameter(sf_scale=0.95, sf_lead=2640, vdatum_shift=0, nbyte=4)
	  !parameter(mid_node=20449)
	  parameter(x_mid_node=502960.989, y_mid_node= 4168255.58) !< mid_node=20449

      ! Accept some argments
      ! First: tide history
      ! Second: hgrid
      ! Third: ocean grid
      ! Fourth: ocean webtide
      ! Fifth: output 
      if (iargc() < 5) then
        print *,'Usage:exe tide hgrid ocean webtide output' 
        call exit
      endif
      do i = 1, iargc()
        call getarg(i, arg)
        fnames(i) = trim(adjustl(arg))
      enddo
      open(10,file=fnames(3),status='old')
      open(12,file=fnames(4),status='old')
      open(14,file=fnames(2),status='old')
      read(10,*); read(10,*)ne_oc,np_oc 
      read(14,*); read(14,*)ne,np 
      allocate(xnd(np),ynd(np),dp(np),x_oc(np_oc),y_oc(np_oc),dp_oc(np_oc), &
               nm(ne,3),nm_oc(ne_oc,3),stat=istat)
      if(istat/=0) stop 'Failed to alloc (1)'
      do i=1,np_oc
        read(10,*)j,x_oc(i),y_oc(i),dp_oc(i)
      enddo !i
      do i=1,np
        read(14,*)j,xnd(i),ynd(i),dp(i)
      enddo !i
      do i=1,ne_oc
        read(10,*)j,k,nm_oc(i,1:3)
      enddo !i
      do i=1,ne
        read(14,*)j,k,nm(i,1:3)
      enddo !i
      read(14,*)nope
      read(14,*)neta
	  
!...  Find node id for the middle node	  
	  mid_node=find_nearest_node(x_mid_node, y_mid_node, np, xnd, ynd)
	  print*, 'middle node id=', mid_node
	  
      imid_node=0 !flag
      do i=1,1 
        read(14,*)nond
        allocate(iond(nond),stat=istat)
		if(istat/=0) stop 'Failed to alloc (2)'
        do j=1,nond
          read(14,*)iond(j)
          if(mid_node==iond(j)) imid_node=j
        enddo !j
      enddo !i
      if(imid_node==0) stop 'Middle bnd node is not in the list'
      close(10)
      close(14)
      
      allocate(iep(nond),wei(nond),eta(nond),stat=istat)
      if(istat/=0) stop 'Failed to alloc (3)'

!     ocean.ap grid is same as ocean.gr3
      read(12,*); read(12,*) np2 
      if(np_oc/=np2) stop 'Mismatch'
      read(12,*)nfr 
      allocate(ap(2,np_oc,nfr),stat=istat)
      if(istat/=0) stop 'Failed to alloc (4)'   
      iM2=0 !flag
      do i=1,nfr
        read(12,*)char1
        char1=adjustl(char1)
        frname=char1(1:2)
        if(frname.eq."M2") iM2=i
        do j=1,np_oc
          read(12,*)ap(1:2,j,i)
        enddo !j
      enddo !i
      if(iM2==0) stop 'Failed to find M2'
      close(12)
	  
!...  Find parent element for open bnd nodes
      iep=0
      do i=1,ne_oc !< for each ocean element
        do l=1,nond !< loop through each ocean boundary node
          if(iep(l)/=0) cycle !< if parent already identified for a particular node, jump to the next one

          jnd=iond(l)
          aa=0
          ar=0 !area
          do j=1,3
            j1=j+1
            j2=j+2
            if(j1>3) j1=j1-3
            if(j2>3) j2=j2-3
            n0=nm_oc(i,j)
            n1=nm_oc(i,j1)
            n2=nm_oc(i,j2)
            swild(j)=signa(x_oc(n1),x_oc(n2),xnd(jnd),y_oc(n1),y_oc(n2),ynd(jnd)) !temporary storage
            aa=aa+abs(swild(j))
            if(j==1) ar=signa(x_oc(n1),x_oc(n2),x_oc(n0),y_oc(n1),y_oc(n2),y_oc(n0))
          enddo !j
          if(ar<=0) then
            print*, 'Negative area:',ar
            stop
          endif
          ae=abs(aa-ar)/ar
          if(ae<=1.e-3) then
            iep(l)=i
            cycle !< if find associated ocean bnd node, skip checking the remaining nodes
          endif !ae
        enddo !l; build pts
              
        ifl=0 !flag
        do l=1,nond
          if(iep(l)==0) then !< after work on each element, check to see if any boundary
            ifl=1            !< node still missing parent; if true, set flag to 1
            exit             
          endif
        enddo !l
        if(ifl==0) exit !< if the parent has been identified for all the ocean bnd nodes, exit
      enddo !i=1,ne_oc  !< the element checking loop, otherwise, continue to the next element
      
	  do j=1,nond !< check whether the parent has been identified for all the ocean boundary nodes,
        if(iep(j)==0) then !< if not, stop program
          print*, 'Cannot find a parent for pt:',j
          stop
        endif
      enddo !j

!     Interpolation weights in space
      ie_oc_sf=iep(imid_node)
      swild(1:3)=ap(1,nm_oc(ie_oc_sf,1:3),iM2) !< M2 ampititude predictions at 3 nodes of the parent element 
      sf_m2=sum(swild(1:3))/3 
      do i=1,nond
        swild(1:3)=ap(1,nm_oc(iep(i),1:3),iM2)
        amp_m2=sum(swild(1:3))/3
        wei(i)=amp_m2/sf_m2
      enddo !i

!     Output
      open(17,file=fnames(1),status='old') !< need to use a different input file, format may be different
      nt2=0
      do !< scan through the input file to get the total record number of the time series
        nt2=nt2+1
        read(17,*,end=98,err=98) time,tmp
      enddo
98    continue
      nt2=nt2-1
      print*, nt2,' lines read from', trim(fnames(1))
      nstep=nt2 
      
      rewind(17)
      irecl=nbyte*(1+nond)
      open(18,file=fnames(5),access='direct',recl=irecl,status='replace')
      !open(20,file='elev3D_3.txt',status='unknown') ! for debugging use
      allocate(sf_elev(nstep),stat=istat)
      if(istat/=0) stop 'Failed to alloc (5)'
      do it=1,nstep
        read(17,*)time,tmp
        sf_elev(it)=tmp*sf_scale+vdatum_shift !< apply scale and vdatum offset
        if(it==1) dt=time 
      enddo !it
      
      rewind(17)
      it_lead=sf_lead/dt
      print*, 'Dt in original series=',dt,' , time step lead=',it_lead, &
     &' , input & actual time lead=',sf_lead,it_lead*dt
      do it=1,nstep-86400/dt !1 day less to account for phase shift
        read(17,*)time,tmp
        it2=it+it_lead !< apply time lead to SF
        if(it2>nstep) stop 'Pls reduce SF series further'
        do j=1,nond
          eta(j)=wei(j)*sf_elev(it2)
          !if (mod(it,50000) == 0) write(20,*) time,j,eta(j) ! for debugging use
        enddo !j
        write(18,rec=it) real(time), real(eta(1:nond))
      enddo !it
      close(17)
      close(18)
      !close(20) ! for debugging use

      stop
      end program gen_elev3D_3_NAVD88
	  
	  
      !> Compute signed area formed by pts 1,2,3
      !! @param x1,x2,x3 the x-coordinates of the 3 points
      !! @parem y1,y2,y3 the y-coordinates of the 3 points
      !! @return signed area
      function signa(x1,x2,x3,y1,y2,y3)
      implicit none
      real (kind=8), intent(in) :: x1,x2,x3,y1,y2,y3
      real (kind=8) :: signa
      signa=((x1-x3)*(y2-y3)-(x2-x3)*(y1-y3))/2.0
      return
      end function signa
	  
	  
      !> Find the nearest node id in a grid for a specific point in space
      !! based on the minimum distance from indivdual node to the point
      !! @param x_point: x-coordinate (m) of a specified point
      !! @param y_point: y-coordinate (m) of a specified point
      !! @param n_node: number of nodes in input grid
      !! @param x_node: x-coordinates (m) of node points in input grid
      !! @param y_node: y-coordinates (m) of node points in input grid
      !! @return find_nearest_node: the node id of the nearest node in input grid
      function find_nearest_node(x_point, y_point, n_node, x_node, y_node)
      
      implicit none
      integer, intent(in) :: n_node
      real (kind=8), intent(in) :: x_point, y_point
      real (kind=8), intent(in), dimension(n_node) :: x_node, y_node
      integer :: find_nearest_node, i, j, idx_temp
      real (kind=8), dimension(n_node) :: distance
      integer, dimension(n_node) :: node_idx
      real (kind=8) :: dist_temp

      do i=1,n_node
        distance(i) = sqrt((x_node(i)-x_point)**2+(y_node(i)-y_point)**2)
        node_idx(i) = i
      enddo !i
      
      do i=1,n_node-1 !< sort the distance array 
        do j=i+1,n_node
          if(distance(i) > distance(j)) then
            dist_temp = distance(i) 
            distance(i) = distance(j)
            distance(j) = dist_temp
            idx_temp = node_idx(i)
            node_idx(i) = node_idx(j)
            node_idx(j) = idx_temp
          end if	
        enddo !j
      enddo !i
      
      find_nearest_node = node_idx(1)
      return
      end function find_nearest_node
	  
	  
	  
