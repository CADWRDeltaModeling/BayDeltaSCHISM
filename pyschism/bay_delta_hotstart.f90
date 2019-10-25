! Generate hotstart.in with const. elev. (from elev.ic) and 0 vel (i.e. S,T only; no tracers)
! History: added ivcor=1; fixed a bug in ntracers
! pgf90 -O2 -mcmodel=medium -Mbounds -Bstatic -o bay_delta_hotstart /sciclone/home04/yinglong/SELFE/svn/trunk/src/Utility/UtilLib/argparse.F90 bay_delta_hotstart.f90
! ifort -Bstatic -assume byterecl -O2 -o bay_delta_hotstart bay_delta_hotstart.f90 argparse.F90
! ifort -Bstatic /assume:byterecl -O2 -fpp -o bay_delta_hotstart bay_delta_hotstart.f90 argparse.F90
!   Input: 
!     (1) USGS survey data: (e.g. usgs_cruise_station.txt, usgs_2009_02_10.txt) -WARNING:
!                            dates have to be in: mm/dd/yyyy... i.e. double digits for mm & dd,
!                            and mm must be preceded by exactly 1 space!
!     (2) hgrid.gr3;
!     (3) vgrid.in; 
!     (4) estuary.gr3 (flags): depth=0: outside; =1: Bay; =2: Delta
!     (5) elev.ic: init. condition for elev
!   Output: hotstart.in ; fort.11 (fatal); fort.27 (debug)

!      implicit none

!     integer, parameter :: debug=1
     
      program bay_delta_hotstart
      implicit none
          
      character*120 tempsaltfile
      character*120 stationfile
      character*120 hotstartfile
      character*120 initialelevfile
      character*120 hgridfile
      character*120 vgridfile
      character*120 estuaryfile
      real         deltasalt
      real         deltatemp
      real         coastal_T

      call hotstart_input(tempsaltfile,&
                          stationfile,&
                          initialelevfile,&
                          hgridfile,&
                          vgridfile,&
                          estuaryfile,&
                          deltasalt,&
                          deltatemp, &
                          coastal_T, &
                          hotstartfile)

      call hotstart_from_cruise_data(tempsaltfile,&
                                     stationfile,&
                                     initialelevfile,&
                                     hgridfile,&
                                     vgridfile,&
                                     estuaryfile,&
                                     deltasalt,&
                                     deltatemp, &
                                     coastal_T, &
                                     hotstartfile)
      end program
      
      subroutine hotstart_input(tempsaltfile,&
                                          stationfile,&
                                          initialelevfile,&
                                          hgridfile,&
                                          vgridfile,&
                                          estuaryfile,&
                                          deltasalt,&
                                          deltatemp, &
                                          coastal_T, &
                                          hotstartfile)
      use argparse
      implicit none          
      character :: cmd = "bay_delta_hotstart"
      character*120 tempsaltfile
      character*120 stationfile
      character*120 hotstartfile
      character*120 initialelevfile
      character*120 hgridfile
      character*120 vgridfile
      character*120 estuaryfile
      real         deltasalt        
      real         deltatemp
      real         coastal_T
      logical :: fileexists
      logical :: validate_files = .FALSE.
      cmd_name = cmd
      deltasalt=0.15
      deltatemp=10.5
      coastal_T=12.
      hotstartfile="hotstart.in"
      initialelevfile="elev.ic"
      hgridfile="hgrid.gr3"
      vgridfile="vgrid.in"
      estuaryfile="estuary.gr3"
      
      !you must provde station file
      stationfile="invalid"
      tempsaltfile="invalid"
      call cla_init(cmd_name)
      call cla_register('-s','--station','Name of station file describing cruise stations',cla_char,'')
      call cla_register('-t','--tempsalt','Name of temp/salt file (beware date format!)',cla_char,'')
      call cla_register('-o','--hotstart','Name of hotstart file for output (default hotstart.in)',cla_char,'hotstart.in')
      call cla_register('-z','--elev','Path of initial elevation file (elev.ic)',cla_char,'elev.ic')
      call cla_register('-v','--vgrid','Path of vgrid.in file (vgrid.in)',cla_char,'vgrid.in')
      call cla_register('-h','--hgrid','Path of hgrid.gr3 file (hgrid.gr3)',cla_char,'hgrid.gr3')
      call cla_register('-e','--estuary','Path of estuary.gr3 file (vgrid.in)',cla_char,'estuary.gr3')
      call cla_register('-d','--deltasalt','Delta salinity in psu.',cla_float,'0.15')
      call cla_register('-p','--deltatemp','Delta temperature in C.',cla_float,'10.5')
      call cla_register('-c','--coastal_T','Coastal temperature in C.',cla_float,'12')
      
      call cla_get("--station",stationfile)
      call cla_get("--tempsalt",tempsaltfile)
      call cla_get("--hotstart",hotstartfile)
      call cla_get("--elev",initialelevfile)
      call cla_get("--vgrid",vgridfile)
      call cla_get("--hgrid",hgridfile)
      call cla_get("--estuary",estuaryfile)
      call cla_get("--deltasalt",deltasalt)
      call cla_get("--deltatemp",deltatemp)
      call cla_get("--coastal_T",coastal_T)
      
      call cla_validate()
      if (validate_files) then
      inquire(FILE=tempsaltfile, EXIST=fileexists)
      if (.not.fileexists) then
         print *, tempsaltfile,"is invalid"
         stop -1
      endif
      inquire(FILE=estuaryfile, EXIST=fileexists)
      if (.not.fileexists) then
         print *, estuaryfile,"is invalid"
         stop -1
      endif
      inquire(FILE=stationfile, EXIST=fileexists)
      if (.not.fileexists) then
         print *, stationfile,"is invalid"
         stop -1
      endif
      inquire(FILE=hgridfile, EXIST=fileexists)
      if (.not.fileexists) then
         print *, hgridfile,"is invalid"
         stop -1
      endif
      inquire(FILE=vgridfile, EXIST=fileexists)
      if (.not.fileexists) then
         print *, vgridfile,"is invalid"
         stop -1
      endif
      inquire(FILE=initialelevfile, EXIST=fileexists)
      if (.not.fileexists) then
         print *, initialelevfile,"is invalid"
         stop -1
      endif
      end if
      
      end subroutine
      
      
      subroutine hotstart_from_cruise_data(tempsaltfile,stationfile,initialelevfile,&
                 hgridfile,vgridfile,estuaryfile,deltasalt,deltatemp,coastal_T,hotstartfile)
      !implicit none
      character*120 tempsaltfile
      character*120 stationfile
      character*120 hotstartfile
      character*120 initialelevfile
      character*120 hgridfile
      character*120 vgridfile
      character*120 estuaryfile
      real         deltasalt
      real         deltatemp
      real         coastal_T
      
      
      integer, parameter :: mcasts=1000 !max. # of casts on 03/12
      integer, parameter :: mndps=200 !max. # of depth bins
      integer, parameter :: mnp=400000 !400000
      integer, parameter :: mne=400000
      integer, parameter :: mns=650000 !790000
      integer, parameter :: mnv=140    !100
      integer, parameter :: mnope=20 !max # of open bnd segments
      integer, parameter :: mnond=1000 !max # of open bnd nodes in each segment
      integer, parameter :: mnei=20 !neighbor
      integer, parameter :: nbyte=4
      real, parameter :: small1=1.e-3 !used to check area ratios
  
!     Vertical postion, salinity, and temperature
      integer :: ne,np,i,j
      integer :: nope,neta
      integer, dimension(:,:), allocatable :: kbp
      integer   code
      integer tmp
      real htmp,stmp,ttmp
      integer   ier ! allocate error return.
      integer   dummy,commalocation
      integer ::  dd,mm,yyyy,tttt
      character(len=1) ::  c1,c2,c3,c4
      character*120  tempstring
      integer :: iostatus
      integer, allocatable :: i34(:)
      real,allocatable :: xnd(:),ynd(:),nm(:,:),dp(:),eta(:)
      !dimension xnd(mnp),ynd(mnp),nm(mne,4),dp(mnp),i34(mne),eta(mnp)
      real,allocatable :: sigma(:),cs(:),z(:,:)
      integer,allocatable :: iest(:),ixy(:,:)
      !dimension sigma(mnv),cs(mnv),z(mnp,mnv),iest(mnp),ixy(mnp,2)
      dimension arco(3),ztot(0:mnv)
      dimension iwild(100)
      dimension tempout(mnp,mnv), saltout(mnp,mnv),month_day(12)
      dimension tsd(mns,mnv),ssd(mns,mnv),tsel(mnv,mne,2)
      integer,allocatable :: nne(:),ine(:,:),ic3(:,:),js(:,:),is(:,:),isidenode(:,:)
       
      dimension nx(4,4,3)
      dimension xcj(mns),ycj(mns),nond(mnope),iond(mnope,mnond) !,iob(mnope),iond2(mnope*mnond)
      dimension sta2(mcasts),casts_xyz(mcasts,3),cast_h(mcasts,mndps),cast_S(mcasts,mndps), &
     &cast_T(mcasts,mndps),nbins(mcasts)
      dimension kbp2(mnp),sigma_lcl(mnv,mnp)
      allocatable :: sta1(:),xsta(:),ysta(:),hsta(:),map(:)
!     Read in (const) elev.
      open(10,file=initialelevfile,status='old')
      read(10,*)
      read(10,*)ne, np
      allocate(xnd(np),ynd(np),nm(ne,4),dp(np),i34(ne),eta(np))
      allocate(sigma(mnv),cs(mnv),z(np,mnv),iest(np),ixy(np,2))     
      allocate(nne(np),ine(np,mnei),ic3(ne,4),js(ne,4),is(mns,2),isidenode(mns,2))      
      do i=1,np
        read(10,*)j,xtmp,ytmp,eta(i)
      enddo
      close(10)

!     Read in survey data
      open(8,file=stationfile,status='old')
      open(9,file=tempsaltfile,status='old')
      read(8,*)
      nsta=0
      do 
          read(8,*,iostat=iostatus) dummy
          if (iostatus.ne.0) then
              exit
          endif
          nsta=nsta+1
      enddo
      rewind 8
      read(8,*)
      allocate(sta1(nsta),xsta(nsta),ysta(nsta),hsta(nsta))
      do i=1,nsta
        read(8,*)sta1(i),ysta(i),xsta(i),hsta(i)
      enddo !i
      close(8)
      mapdim=maxval(sta1(1:nsta)*10) !for mapping array
      !print*, 'mapdim=',mapdim
      allocate(map(mapdim))
      map=0
      do i=1,nsta
        map(int(sta1(i)*10))=i
      enddo !i

      ncasts=1 !# of casts
      ndps=0 !# of depth bins
      i = 1
      do ! i=1,549 !read only 03/12 data
        if(i<=2) then
          read(9,*)
        else
          mm=-9999
          dd=-9999
100       format (i3,a1,i2,a1,i4,a1,i4,a1,a)
          read(9,100,iostat=code) mm,c1,dd,c2,yyyy,c3,tttt,c4,tempstring
!          if(i==3) print*, mm,c1,dd,c2,yyyy,c3,tttt,c4,tempstring
          
          ! reach the end of file
          if (code.ne.0) then
             if (i.eq.3) then
               write(*,*) "input data is empty, no result generated:",mm,c1,dd,c2,yyyy,c3,tttt,c4,tempstring
               stop -1
             else ! at least have one data
               exit
             end if
          end if
          
          if ((.not.((mm.le.12).and.(mm.ge.1))) .or. (.not.((dd.le.31).and.(dd.ge.1))) )then
             if (i.eq.3) then
               write(*,*) "valid data must start from the third line, no result generated"
               stop -1
             else ! at least have one data
               exit
             end if
          end if
          
          !total four data seperate by 3 comma are expected
          commalocation=index(tempstring,",")
          if (commalocation.eq.0) then
              write(*,'(a,i,a)') "data line",i,"is invalid"
          end if
          read(tempstring(1:commalocation-1),*,iostat=code)tmp
          tmp=int(tmp)
          tempstring=tempstring(commalocation+1:)
          commalocation=index(tempstring,",")
          if (commalocation.eq.0) then
              write(*,'(a,i,a)') "data line",i,"is invalid"
          end if
          read(tempstring(1:commalocation-1),*,iostat=code)htmp
          tempstring=tempstring(commalocation+1:)
          commalocation=index(tempstring,",")
          if (commalocation.eq.0) then
              write(*,'(a,i,a)') "data line",i,"is invalid"
          end if
          read(tempstring(1:commalocation-1),*,iostat=code)stmp
          tempstring=tempstring(commalocation+1:)
          read(tempstring,*,iostat=code)ttmp
          
           
!          read(9,*,iostat=code)iwild(1:5),tmp,htmp,stmp,ttmp
          
          if (code<0) then
            tmp = -1
          endif  
          !print*, 'check:',iwild(1:5),tmp,htmp,stmp,ttmp
          if(i>3) then
            if(abs(tmp-sta2(ncasts))>0.1) then
              nbins(ncasts)=ndps; 
!              print*, 'cast # ',ncasts,ndps,sta2(ncasts),casts_xyz(ncasts,1:3)
!              print*, 'cast T=',cast_T(ncasts,1:ndps),'; depths=',cast_h(ncasts,1:ndps)
              ncasts=ncasts+1; ndps=0
            endif
            if (tmp == -1) then
               exit
            endif
          endif !i>3
          ndps=ndps+1
          if(ncasts>mcasts.or.ndps>mndps) then
            write(*,*)'Increase mcasts or mndps:',ncasts,ndps
            stop -1 
          endif
          sta2(ncasts)=tmp
          itmp=map(int(tmp*10))
          casts_xyz(ncasts,1)=xsta(itmp)
          casts_xyz(ncasts,2)=ysta(itmp)
          casts_xyz(ncasts,3)=hsta(itmp)
          cast_h(ncasts,ndps)=htmp
          cast_S(ncasts,ndps)=stmp
          cast_T(ncasts,ndps)=ttmp
        endif
        i = i + 1
      enddo !i
      
      nbins(ncasts)=ndps !for last cast
      close(9)
      print*, '# of casts',ncasts
      print*, 'Last cast (x,y,h)=',casts_xyz(ncasts,1:3),'; depths=',cast_h(ncasts,1:nbins(ncasts))
!      stop -1

!     Read in hgrid and vgrid
      open(17,file=estuaryfile,status='old')
      open(14,file=hgridfile,status='old') !only need depth info and connectivity
      open(19,file=vgridfile,status='old')
      print*,"Reading hgrid"
      read(14,*)
      read(14,*)ne,np
      if(np.gt.mnp.or.ne.gt.mne) then
        write(*,*)'Increase mnp/mne'
        stop -1
      endif
      read(17,*)
      read(17,*)
      print*, "ne = ",ne," np=",np
      do i=1,np
        read(14,*)j,xnd(i),ynd(i),dp(i)
        read(17,*)j,xtmp,ytmp,iest(i)
        if(iest(i)<0.or.iest(i)>2) then
          write(11,*)'Estuary flag wrong:',i,iest(i)
          stop -1
        endif
      enddo !i
      do i=1,ne
        read(14,*)j,i34(i),(nm(i,l),l=1,i34(i))
      enddo !i
!     Open bnds
      read(14,*) nope
      read(14,*) neta
      ntot=0
      if(nope>mnope) stop 'Increase mnope (2)'
      do k=1,nope
        read(14,*) nond(k)
        if(nond(k)>mnond) stop 'Increase mnond'
        do i=1,nond(k)
          read(14,*) iond(k,i)
        enddo
      enddo

!      nond0=0
!      do i=1,nob
!        ibnd=iob(i)
!        do j=1,nond(ibnd)
!          nond0=nond0+1
!          iond2(nond0)=iond(ibnd,j)
!        enddo !j
!      enddo !i
      close(14)

!     V-grid
      print*,"Reading vgrid"
      read(19,*)ivcor
      if(ivcor==2) then
        read(19,*) nvrt,kz,h_s !kz>=1
        if(nvrt>mnv.or.nvrt<2) then
          write(11,*)'nvrt > mnv or nvrt<2'
          stop -1
        endif
        if(kz<1) then !.or.kz>nvrt-2) then
          write(11,*)'Wrong kz:',kz
          stop -1
        endif
        if(h_s<10) then
          write(11,*)'h_s needs to be larger:',h_s
          stop -1
        endif

!       # of z-levels excluding "bottom" at h_s
        read(19,*) !for adding comment "Z levels"
        do k=1,kz-1
          read(19,*)j,ztot(k)
          if(k>1.and.ztot(k)<=ztot(k-1).or.ztot(k)>=-h_s) then
            write(11,*)'z-level inverted:',k
            stop -1
          endif
        enddo !k
        read(19,*) !level kz       
!       In case kz=1, there is only 1 ztot(1)=-h_s
        ztot(kz)=-h_s

        nsig=nvrt-kz+1 !# of S levels (including "bottom" & f.s.)
        read(19,*) !for adding comment "S levels"
        read(19,*)h_c,theta_b,theta_f
        if(h_c<5) then !large h_c to avoid 2nd type abnormaty
          write(11,*)'h_c needs to be larger:',h_c
          stop -1
        endif
        if(theta_b<0.or.theta_b>1) then
          write(11,*)'Wrong theta_b:',theta_b
          stop -1
        endif
        if(theta_f<=0) then 
          write(11,*)'Wrong theta_f:',theta_f 
          stop -1
        endif
!       Pre-compute constants
        s_con1=sinh(theta_f)

        sigma(1)=-1 !bottom
        sigma(nsig)=0 !surface
        read(19,*) !level kz
        do k=kz+1,nvrt-1
          kin=k-kz+1
          read(19,*) j,sigma(kin)
          if(sigma(kin)<=sigma(kin-1).or.sigma(kin)>=0) then
            write(11,*)'Check sigma levels at:',k,sigma(kin),sigma(kin-1)
            stop -1
          endif
        enddo
        read(19,*) !level nvrt

!       Compute C(s) and C'(s)
        do k=1,nsig
          cs(k)=(1-theta_b)*sinh(theta_f*sigma(k))/sinh(theta_f)+ &
     &theta_b*(tanh(theta_f*(sigma(k)+0.5))-tanh(theta_f*0.5))/2/tanh(theta_f*0.5)
        enddo !k=1,nvrt

        do i=1,np
          do k=kz,nvrt
            kin=k-kz+1
            hmod2=max(0.1,min(dp(i),h_s))
            if(hmod2<=h_c) then
              z(i,k)=sigma(kin)*hmod2
            else
              z(i,k)=h_c*sigma(kin)+(hmod2-h_c)*cs(kin)
            endif
          enddo !k

!         Z-levels; shallow pts have junk values
          do k=1,kz-1
            z(i,k)=ztot(k)
          enddo !k
        enddo !i
      else if(ivcor==1) then !Localized
        read(19,*)nvrt
        if(nvrt>mnv.or.nvrt<3) then
          write(11,*)'nvrt > mnv or nvrt<4:',nvrt
          stop -1
        endif

        do i=1,np
          read(19,*)j,kbp2(i),sigma_lcl(kbp2(i):nvrt,i)

          hmod2=max(0.1,dp(i))
          z(i,kbp2(i))=-hmod2 !to avoid underflow
          z(i,nvrt)=0
          do k=kbp2(i)+1,nvrt-1
            z(i,k)=sigma_lcl(k,i)*hmod2
          enddo !k

          !Check
          do k=kbp2(i)+1,nvrt
            if(z(i,k)-z(i,k-1)<=0) then
              write(11,*)'Inverted Z:',z(i,k),z(i,k-1),k,i,dp(i),sigma_lcl(:,i)
              stop -1
            endif
          enddo !k

          !Extend bottom (as these are used)
          z(i,1:kbp2(i)-1)=z(i,kbp2(i))
        enddo !i=1,np
      else
        write(11,*)'Unknow ivcor'
        stop -1
      endif !ivcor

      close(19)
      print*,"Computing geometry information such as interpolation neighbors"
!     Compute geometry
      do k=3,4
        do i=1,k
          do j=1,k-1
            nx(k,i,j)=i+j
            if(nx(k,i,j)>k) nx(k,i,j)=nx(k,i,j)-k
            if(nx(k,i,j)<1.or.nx(k,i,j)>k) then
              write(*,*)'nx wrong',i,j,k,nx(k,i,j)
              stop -1
            endif
          enddo !j
        enddo !i
      enddo !k

      do i=1,np
        nne(i)=0
      enddo

      do i=1,ne
        do j=1,i34(i)
          nd=nm(i,j)
          nne(nd)=nne(nd)+1
          if(nne(nd)>mnei) then
            write(11,*)'Too many neighbors',nd
            stop -1
          endif
          ine(nd,nne(nd))=i
        enddo
      enddo

!     Compute ball info; this won't be affected by re-arrangement below
      do i=1,ne
        do j=1,i34(i)
          ic3(i,j)=0 !index for bnd sides
          nd1=nm(i,nx(i34(i),j,1))
          nd2=nm(i,nx(i34(i),j,2))
          do k=1,nne(nd1)
            ie=ine(nd1,k)
            if(ie/=i.and.(nm(ie,1)==nd2.or.nm(ie,2)==nd2.or.nm(ie,3)==nd2.or.(i34(ie)==4.and.nm(ie,4)==nd2))) ic3(i,j)=ie
          enddo !k
        enddo !j
      enddo !i

      print*,"Computing edge information"
      ns=0 !# of sides
      do i=1,ne
        do j=1,i34(i)
          nd1=nm(i,nx(i34(i),j,1))
          nd2=nm(i,nx(i34(i),j,2))
          if(ic3(i,j)==0.or.i<ic3(i,j)) then !new sides
            ns=ns+1
            if(ns>mns) then
              print*,"Too many sides (ns must be bigger in script"
              write(11,*)'Too many sides:'
              stop -1
            endif
            js(i,j)=ns
            is(ns,1)=i
            isidenode(ns,1)=nd1
            isidenode(ns,2)=nd2
            xcj(ns)=(xnd(nd1)+xnd(nd2))/2
            ycj(ns)=(ynd(nd1)+ynd(nd2))/2

            is(ns,2)=ic3(i,j) !bnd element => bnd side
!           Corresponding side in element ic3(i,j)
            if(ic3(i,j)/=0) then !old internal side
              iel=ic3(i,j)
              indexside=0
              do k=1,i34(iel)
                if(ic3(iel,k)==i) then
                  indexside=k
                  exit
                endif
              enddo !k
              if(indexside==0) then
                write(11,*)'Wrong ball info',i,j
                stop -1
              endif
              js(iel,indexside)=ns
            endif !ic3(i,j).ne.0
          endif !ic3(i,j)==0.or.i<ic3(i,j)
        enddo !j=1,i34
      enddo !i=1,ne
      print*,"Number of sides: ",ns
      if(ns<ne.or.ns<np) then
        write(11,*)'Weird grid with ns < ne or ns < np',np,ne,ns
        stop -1
      endif

!     Compute node T,S
      tempout=-9999.
      saltout=-9999. !init.
      do i=1,np
!       z() defined for dry pts also
        if(iest(i)==0) then !outside Bay
          saltout(i,:)=33.5
          tempout(i,:)=coastal_T !from ROMS (bottom)
        else if(iest(i)==2) then !Delta
          saltout(i,:)=deltasalt
          tempout(i,:)=deltatemp
        else !inside Bay
          !Find nearest cast
          rlmin=1.e23
          icast=0
          do j=1,ncasts
            rl2=(casts_xyz(j,1)-xnd(i))**2+(casts_xyz(j,2)-ynd(i))**2
            if(rl2<rlmin) then
              rlmin=rl2; icast=j
            endif
          enddo !j
          if(icast==0) stop 'Failed to find a cast'
          nbins0=nbins(icast)
 
          !Do vertical interpolation
          do k=1,nvrt
            if(z(i,k)>=-cast_h(icast,1)) then
              saltout(i,k)=cast_S(icast,1)
              tempout(i,k)=cast_T(icast,1)
            else if(z(i,k)<=-cast_h(icast,nbins0)) then
              saltout(i,k)=cast_S(icast,nbins0)
              tempout(i,k)=cast_T(icast,nbins0)
            else !normal
              ind0=0
              do kk=1,nbins0-1
                if(z(i,k)<=-cast_h(icast,kk).and.z(i,k)>=-cast_h(icast,kk+1)) then
                  ind0=kk 
                  zrat=(z(i,k)+cast_h(icast,kk+1))/(-cast_h(icast,kk)+cast_h(icast,kk+1)) 
                  exit
                endif
              enddo !kk
              if(ind0==0.or.zrat<0.or.zrat>1) then
                write(*,*)'Failed to find a level:',i,k
                stop -1
              endif
              saltout(i,k)=zrat*cast_S(icast,ind0)+(1-zrat)*cast_S(icast,ind0+1)
              tempout(i,k)=zrat*cast_T(icast,ind0)+(1-zrat)*cast_T(icast,ind0+1)
            endif !z()
          enddo !k
        endif !in/out Bay
      enddo !i=1,np
     
      !Check
      do i=1,np
        write(27,*)i,xnd(i),ynd(i),saltout(i,1)
      enddo !i
      write(*,*)'S max/min=',maxval(saltout(1:np,1:nvrt)),minval(saltout(1:np,1:nvrt))
      write(*,*)'T max/min=',maxval(tempout(1:np,1:nvrt)),minval(tempout(1:np,1:nvrt))

!     Output hotstart 
!     Note: although I swapped order of indices in SCHISM for S,T,
!           I didn't do the same for them in this code; as long as 
!           the order of writing is correct in hotstart.in, it does not matter
      do i=1,ns
        n1=isidenode(i,1)
        n2=isidenode(i,2)
        do k=1,nvrt
          tsd(i,k)=(tempout(n1,k)+tempout(n2,k))/2
          ssd(i,k)=(saltout(n1,k)+saltout(n2,k))/2
        enddo !k
      enddo !i

      do i=1,ne
        do k=2,nvrt
          tsel(k,i,1)=0.
          tsel(k,i,2)=0.
          do j=1,i34(i)
            tsel(k,i,1)=tsel(k,i,1)+tempout(nm(i,j),k)+tempout(nm(i,j),k-1)
            tsel(k,i,2)=tsel(k,i,2)+saltout(nm(i,j),k)+saltout(nm(i,j),k-1)
          enddo
          tsel(k,i,1)=tsel(k,i,1)/(2*i34(i))
          tsel(k,i,2)=tsel(k,i,2)/(2*i34(i))
        enddo

        tsel(1,i,1)=tsel(2,i,1) !mainly for hotstart format
        tsel(1,i,2)=tsel(2,i,2)
      enddo !i

!     MPI SCHISM
      ntracers2=0 !_excluding_ T,S
      open(36,file=hotstartfile,form='unformatted',status='replace')
      write(36) 0.d0,0,1
      do i=1,ne
        !Add CoSINE tracers here
        tmp=0
        write(36) i,0,(0.d0,dble(tsel(j,i,1:2)),(dble(tmp),l=1,ntracers2),j=1,nvrt)
      enddo !i
      do i=1,ns
        write(36) i,0,(0.d0,0.d0,dble(tsd(i,j)),dble(ssd(i,j)),j=1,nvrt)
      enddo !i
      do i=1,np
        !Need to add tracers for CoSINE here also
        write(36) i,dble(eta(i)),0,(dble(tempout(i,j)),dble(saltout(i,j)), &
                  dble(tempout(i,j)),dble(saltout(i,j)),0.d0,0.d0, &
                  0.d0,0.d0,0.d0,0.d0,0.d0,j=1,nvrt)
      enddo !i
      close(36)
      !deallocate(xnd,ynd,nm,dp,i34,eta)
      !deallocate(sigma,cs,z,iest,ixy)
      stop
    end  subroutine
