!   Copyright 2014 College of William and Mary
!
!   Licensed under the Apache License, Version 2.0 (the "License");
!   you may not use this file except in compliance with the License.
!   You may obtain a copy of the License at
!
!     http://www.apache.org/licenses/LICENSE-2.0
!
!   Unless required by applicable law or agreed to in writing, software
!   distributed under the License is distributed on an "AS IS" BASIS,
!   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
!   See the License for the specific language governing permissions and
!   limitations under the License.

! Generate *_nu.nc from gridded data (nc file)
! The section on nc read needs to be modified as appropriate- search for
! 'start11' and 'end11'
! Beware the order of vertical levels in the nc file!!!
! Assume elev=0 in interpolation of 3D variables
! The code will do all it can to extrapolate: below bottom/above surface.
! If a pt in hgrid.ll is outside the background nc grid, const. values will be filled (from gen_hot_3Dth_from_nc.in) 
!
! ifort -O2 -mcmodel=medium -CB -o gen_nu ~yinglong/git/schism/src/Utility/UtilLib/compute_zcor.f90 gen_nu.f90 -I$NETCDF/include -I$NETCDF_FORTRAN/include -L$NETCDF_FORTRAN/lib -L$NETCDF/lib -lnetcdf -lnetcdff

!   Input: 
!     (1) hgrid.gr3;
!     (2) hgrid.ll;
!     (3) vgrid.in (SELFE R1703 and up);
!     (4) include.gr3: if depth=0, skip the interpolation to speed up.
!                      Should be larger than the non-0 regions in *_nudge.gr3
!     (5) gen_nu.in: 
!                     1st line: T,S values for pts outside bg grid in nc
!                     2nd line: time step in .nc in sec; output stride
!                     3rd line: start yr, month, day (assume to be in PST)
!                     4th line: # of days
!     (6) ROMS nc files. The extent the ROMS files cover needs to be
!                      larger than the region specified in include.gr3
!   Output: TEM_nu.in 
!   Debug outputs: fort.11 (fatal errors); fort.2[0-9], fort.9[5-9], fort.100

      program gen_hot
!      use typeSizes
      use netcdf
      use compute_zcor

!      implicit none

!      integer, parameter :: debug=1
      integer, parameter :: mnp=300000
      integer, parameter :: mne=400000
      integer, parameter :: mns=600000
      integer, parameter :: mnv=50
      integer, parameter :: mnope=50 !max # of open bnd segments
      integer, parameter :: mnond=1000 !max # of open bnd nodes in each segment
      integer, parameter :: mnei=20 !neighbor
      integer, parameter :: nbyte=4
      real, parameter :: small1=1.e-2 !used to check area ratios
  
!     netcdf related variables
      integer :: sid, ncids(100),one_dim ! Netcdf file IDs
      integer :: latvid, lonvid, zmvid, hvid ! positional variables
      integer :: xdid, xvid ! longitude index
      integer :: ydid, yvid ! latitude index
      integer :: ldid, lvid ! vertical level, 1 is top
      integer :: svid, tvid ! salt & temp variable IDs
      integer :: uvid, vvid ! vel variable IDs
      integer :: evid ! SSH variable IDs
      integer :: var1d_dims(1),var4d_dims(4)
      integer, dimension(nf90_max_var_dims) :: dids
             
!     Local variables for data
      real (kind = 4), allocatable :: xind(:), yind(:), lind(:) 
!     Lat, lon, bathymetry
      real (kind = 4), allocatable :: lat(:,:), lon(:,:), hnc(:)
!     Vertical postion, salinity, and temperature
      real (kind = 4), allocatable :: zm(:,:,:),salt(:,:,:),temp(:,:,:), &
     &uvel(:,:,:),vvel(:,:,:),ssh(:,:)
      integer, allocatable :: kbp(:,:),ihope(:,:)
!     File names for netcdf files
      character(len=1024) :: ncfile1
!     Command line arguments
      character(len=1024) :: s, yr, md
      character(len=4) :: iyear_char
      character(len=1) :: char1,char2
      character(len=2) :: char3,char4
      character(len=2) :: hr_char(4)
!     external function for number of command line arguments
      integer :: iargc

      integer :: status ! netcdf local status variable
      integer :: ier ! allocate error return.
      integer :: ixlen, iylen, ilen ! sampled lengths in each coordinate direction
      integer :: ixlen1, iylen1,ixlen2, iylen2 !reduced indices for CORIE grid to speed up interpolation
!     integer :: i,j,k,i1,i2,i3,j1,j2,j3
      integer :: elnode(4,mne)
      integer :: elside(4,mne)
      integer :: isdel(2,mns)
      integer :: indel(mnei,mnp)
      dimension xl(mnp),yl(mnp),dp(mnp),i34(mne),include2(mnp),imap(mnp)
      dimension ztot(0:mnv),sigma(mnv),cs(mnv),iest(mnp),ixy(mnp,3),arco(3,mnp)
      dimension wild(100),wild2(100,2)
      dimension tempout(mnv,mnp), saltout(mnv,mnp),month_day(12)
      dimension uout(mnp,mnv),vout(mnp,mnv),eout(mnp),su2(mns,mnv),sv2(mns,mnv)
      dimension tsd(mns,mnv),ssd(mns,mnv),tsel(mnv,mne,2)
      dimension nne(mnp),ic3(4,mne),nx(4,4,3),isidenode(2,mns)
      dimension xcj(mns),ycj(mns),nond(mnope),iond(mnope,mnond),iob(mnope),iond2(mnope*mnond)
      dimension ndays_mon(12)
      allocatable :: z(:,:),sigma_lcl(:,:),kbp2(:)
      real*8 :: aa1(1)

!     First statement
      ndays_mon=(/31,28,31,30,31,30,31,31,30,31,30,31/)  !# of days in each month for non-leap yr
      hr_char=(/'03','09','15','21'/) !each day has 4 starting hours in ROMS

      open(10,file='gen_nu.in',status='old')
      read(10,*) tem_outside,sal_outside !T,S values for pts outside bg grid in nc
      read(10,*) dtout,nt_out !time step in .nc [sec], output stride
!      read(10,*) nob,iob(1:nob) !# of open bnds that need *3D.th; list of IDs
      read(10,*) istart_year,istart_mon,istart_day !in PST
      read(10,*) nndays !# of days to process
      close(10)
!      if(tem_es<0.or.sal_es<0.or.tem_outside<0.or.sal_outside<0) &
!     &stop 'Invalid T,S constants'

!     Read in hgrid and vgrid
!      open(17,file='estuary.gr3',status='old')
      open(16,file='hgrid.ll',status='old')
      open(14,file='hgrid.gr3',status='old') !only need depth info and connectivity
      open(15,file='include.gr3',status='old')
      open(19,file='vgrid.in',status='old')
      open(11,file='fort.11',status='replace')
      read(14,*); read(14,*)ne,np
      if(np.gt.mnp.or.ne.gt.mne) then
        write(*,*)'Increase mnp/mne'
        stop
      endif
      read(15,*); read(15,*)
      read(16,*)
      read(16,*)
!      read(17,*)
!      read(17,*)
      do i=1,np
        read(14,*)j,xtmp,ytmp,dp(i)
        read(16,*)j,xl(i),yl(i) !,dp(i)
        read(15,*)j,xtmp,ytmp,tmp
        include2(i)=ceiling(tmp)
      enddo !i
      do i=1,ne
        read(14,*)j,i34(i),(elnode(l,i),l=1,i34(i))
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
      close(16)

!     V-grid
      read(19,*)ivcor
      read(19,*)nvrt
      rewind(19)
      allocate(sigma_lcl(nvrt,np),z(np,nvrt),kbp2(np))
      call get_vgrid_single('vgrid.in',np,nvrt,ivcor,kz,h_s,h_c,theta_b,theta_f,ztot,sigma,sigma_lcl,kbp2)

!     Compute z-coord.
      do i=1,np
        if(ivcor==2) then
          call zcor_SZ_single(max(0.11,dp(i)),0.,0.1,h_s,h_c,theta_b,theta_f,kz,nvrt,ztot,sigma,z(i,:),idry,kbp2(i))
        else if(ivcor==1) then
          z(i,kbp2(i):nvrt)=max(0.11,dp(i))*sigma_lcl(kbp2(i):nvrt,i)
        else
          write(11,*)'Unknown ivcor:',ivcor
          stop
        endif

        !Extend below bottom for interpolation later
        z(i,1:kbp2(i)-1)=z(i,kbp2(i))
      enddo !i

!     Compute geometry
      do k=3,4
        do i=1,k
          do j=1,k-1
            nx(k,i,j)=i+j
            if(nx(k,i,j)>k) nx(k,i,j)=nx(k,i,j)-k
            if(nx(k,i,j)<1.or.nx(k,i,j)>k) then
              write(*,*)'nx wrong',i,j,k,nx(k,i,j)
              stop
            endif
          enddo !j
        enddo !i
      enddo !k

      do i=1,np
        nne(i)=0
      enddo

      do i=1,ne
        do j=1,i34(i)
          nd=elnode(j,i)
          nne(nd)=nne(nd)+1
          if(nne(nd)>mnei) then
            write(11,*)'Too many neighbors',nd
            stop
          endif
          indel(nne(nd),nd)=i
        enddo
      enddo

!     Compute ball info; this won't be affected by re-arrangement below
      do i=1,ne
        do j=1,i34(i)
          ic3(j,i)=0 !index for bnd sides
          nd1=elnode(nx(i34(i),j,1),i)
          nd2=elnode(nx(i34(i),j,2),i)
          do k=1,nne(nd1)
            ie=indel(k,nd1)
            if(ie/=i.and.(elnode(1,ie)==nd2.or.elnode(2,ie)==nd2.or.elnode(3,ie)==nd2.or.(i34(ie)==4.and.elnode(4,ie)==nd2))) ic3(j,i)=ie
          enddo !k
        enddo !j
      enddo !i

      ns=0 !# of sides
      do i=1,ne
        do j=1,i34(i)
          nd1=elnode(nx(i34(i),j,1),i)
          nd2=elnode(nx(i34(i),j,2),i)
          if(ic3(j,i)==0.or.i<ic3(j,i)) then !new sides
            ns=ns+1
            if(ns>mns) then
              write(11,*)'Too many sides'
              stop
            endif
            elside(j,i)=ns
            isdel(1,ns)=i
            isidenode(1,ns)=nd1
            isidenode(2,ns)=nd2
            xcj(ns)=(xl(nd1)+xl(nd2))/2
            ycj(ns)=(yl(nd1)+yl(nd2))/2
!            dps(ns)=(dp(nd1)+dp(nd2))/2
!            distj(ns)=dsqrt((x(nd2)-x(nd1))**2+(y(nd2)-y(nd1))**2)
!            if(distj(ns)==0) then
!              write(11,*)'Zero side',ns
!              stop
!            endif
!            thetan=datan2(x(nd1)-x(nd2),y(nd2)-y(nd1))
!            snx(ns)=dcos(thetan)
!            sny(ns)=dsin(thetan)

            isdel(2,ns)=ic3(j,i) !bnd element => bnd side
!           Corresponding side in element ic3(j,i)
            if(ic3(j,i)/=0) then !old internal side
              iel=ic3(j,i)
              index=0
              do k=1,i34(iel)
                if(ic3(k,iel)==i) then
                  index=k
                  exit
                endif
              enddo !k
              if(index==0) then
                write(11,*)'Wrong ball info',i,j
                stop
              endif
              elside(index,iel)=ns
            endif !ic3(j,i).ne.0
          endif !ic3(j,i)==0.or.i<ic3(j,i)
        enddo !j=1,i34
      enddo !i=1,ne

      if(ns<ne.or.ns<np) then
        write(11,*)'Weird grid with ns < ne or ns < np',np,ne,ns
        stop
      endif
     print*, 'Done computing geometry...'

!     open(54,file='TEM_nu.in',form='unformatted',status='replace')

!start11
!     Define limits for variables for sanity checks
      tempmin=0 
      tempmax=30
      saltmin=0
      saltmax=37
      vmag_max=10 !max. |u| or |v|
      ssh_max=8 !max. of |SSH|

!     Assuming elev, u,v, S,T have same dimensions (and time step) and grids do not change over time
      timeout=-dtout !sec
      irecout=0
      irecout2=0 !final time record # in the output
      iyr_now=istart_year
      imon_now=istart_mon
      iday_now=istart_day-1

      do ifile=1,nndays !days; each day has 4 files
        !Construct the nc file name
        if(mod(iyr_now,4)==0) then
          ndays_mon(2)=29
        else
          ndays_mon(2)=28
        endif

        iday_now=iday_now+1
        if(iday_now>ndays_mon(imon_now)) then
          iday_now=iday_now-ndays_mon(imon_now)
          imon_now=imon_now+1
          if(imon_now>12) then
            imon_now=imon_now-12
            iyr_now=iyr_now+1
          endif
        endif 

        write(iyear_char,'(i4)')iyr_now
        write(char3,'(i2.2)')imon_now
        write(char4,'(i2.2)')iday_now
        !print*, 'imon_now=',char3,char4,iyear_char

        do isub=1,4 !# of files each day
!--------------------------------------------------------------------
!     Open nc file 
      !ncfile1='~yinglong/vims20/CA_DWR/ROMS/ca_subSFB_fcst_'//iyear_char//char3//char4//hr_char(isub)//'.nc'
      ncfile1='/sanstore/schism_archive/roms/ca_subSFB_fcst_'//iyear_char//char3//char4//hr_char(isub)//'.nc'
      print*, 'doing ',trim(ncfile1)
      status = nf90_open(trim(ncfile1),nf90_nowrite, sid)
      !Define junk value for sid; the test is abs()>rjunk
      rjunk=9998
      call check(status)

!     Get dimnesions from first file, assumed same for all variables
      if(ifile==1.and.isub==1) then
        status = nf90_inq_varid(sid, "temp", svid)
        print*, 'Done reading variable ID'

!       WARNING: indices reversed from ncdump!
        status = nf90_Inquire_Variable(sid, svid, dimids = dids)
        status = nf90_Inquire_Dimension(sid, dids(1), len = ixlen)
        status = nf90_Inquire_Dimension(sid, dids(2), len = iylen)
        status = nf90_Inquire_Dimension(sid, dids(3), len = ilen)
        status = nf90_Inquire_Dimension(sid, dids(4), len = ntime)
        print*, 'ixlen,iylen,ilen,ntime= ',ixlen,iylen,ilen,ntime

!       allocate arrays
        allocate(xind(ixlen),stat=ier)
        allocate(yind(iylen),stat=ier)
        allocate(lind(ilen),stat=ier)
        allocate(lat(ixlen,iylen))
        allocate(lon(ixlen,iylen))
        allocate(zm(ixlen, iylen, ilen))
!        allocate(hnc(ixlen,iylen))
        allocate(hnc(ilen))
        allocate(kbp(ixlen,iylen))
        allocate(ihope(ixlen,iylen))
        allocate(uvel(ixlen,iylen,ilen),stat=ier)
        allocate(vvel(ixlen,iylen,ilen),stat=ier)
        allocate(salt(ixlen,iylen,ilen),stat=ier)
        allocate(temp(ixlen,iylen,ilen),stat=ier)
        allocate(ssh(ixlen,iylen),stat=ier)
        uvel=0; vvel=0; ssh=0
  
!       get static info (lat/lon grids etc) 
        status = nf90_inq_varid(sid, "lon", xvid)
        status = nf90_get_var(sid, xvid, xind)
        status = nf90_inq_varid(sid, "lat", yvid)
        status = nf90_get_var(sid, yvid, yind)
        status = nf90_inq_varid(sid, "depth", hvid)
        status = nf90_get_var(sid, hvid, hnc)

!       processing static info
        do i=1,ixlen
          lon(i,:)=xind(i)
        enddo !i
        do j=1,iylen
          lat(:,j)=yind(j)
        enddo !j
        lon=lon-360e0 !convert to our long.

!       Compute z-coord. (assuming eta=0)
!       WARNING: In zm(), 1 is bottom; ilen is surface (SELFE convention)
        do i=1,ixlen
          do j=1,iylen
            do k=1,ilen
              zm(i,j,k)=-hnc(1+ilen-k)
            enddo !k
          enddo !j
        enddo !i

!       Get rest of varid's
        status = nf90_inq_varid(sid, "temp", tvid)
!        status = nf90_inq_varid(sid, "zeta", evid)
!        status = nf90_inq_varid(sid, "u", uvid)
!        status = nf90_inq_varid(sid, "v", vvid)

!       Arrays no longer used after this: hnc,lind
        deallocate(hnc,lind)
      endif !ifile==1 && isub==1

!     Vertical convention follows SELFE from now on; i.e., 1 is at bottom
!     Compute bottom indices
      if(ifile==1.and.isub==1) then
        ilo=5 !5th record is 00:00 PST
      else
        ilo=2 !there is an overlap between files
      endif !ifile

      do it2=ilo,ntime
        irecout=irecout+1
        timeout=timeout+dtout !sec
        print*, 'Time out (days)=',timeout/86400

        !Make sure it2=ilo is output (some init. work below)
        if(mod(irecout-1,nt_out)/=0) cycle
        irecout2=irecout2+1

!       Read T,S,u,v,SSH
!       WARNING! Make sure the order of vertical indices is 1 
!                at bottom, ilen at surface; revert if necessary!
        status = nf90_get_var(sid,svid,salt(:,:,ilen:1:-1),start=(/1,1,1,it2/),count=(/ixlen,iylen,ilen,1/))
        status = nf90_get_var(sid,tvid,temp(:,:,ilen:1:-1),start=(/1,1,1,it2/),count=(/ixlen,iylen,ilen,1/))

        kbp=1  !init.
        do i=1,ixlen
          do j=1,iylen
            if(abs(salt(i,j,ilen))>rjunk) kbp(i,j)=-1 !dry

            if(kbp(i,j)==1) then !wet
              !Extend near bottom
              klev0=-1 !flag
              do k=1,ilen
                if(abs(salt(i,j,k))<=rjunk) then
                  klev0=k; exit
                endif
              enddo !k
              if(klev0<=0) then
                write(11,*)'Impossible (1):',i,j,salt(i,j,ilen)
                stop
              endif !klev0
              salt(i,j,1:klev0-1)=salt(i,j,klev0)
              temp(i,j,1:klev0-1)=temp(i,j,klev0)
!              uvel(i,j,1:klev0-1)=uvel(i,j,klev0)
!              vvel(i,j,1:klev0-1)=vvel(i,j,klev0)

              !Check
              do k=1,ilen
                if(salt(i,j,k)<saltmin.or.salt(i,j,k)>saltmax.or. &
                   temp(i,j,k)<tempmin.or.temp(i,j,k)>tempmax) then
!                   abs(uvel(i,j,k))>vmag_max.or.abs(vvel(i,j,k))>vmag_max.or. &
!                   abs(ssh(i,j))>ssh_max) then
                  write(11,*)'Fatal: no valid values:',it2,i,j,k,salt(i,j,k), &
     &temp(i,j,k) !,uvel(i,j,k),vvel(i,j,k),ssh(i,j)
                  stop
                endif
              enddo !k
            endif !kbp=1
          enddo !j
        enddo !i  

!       Compute S,T etc@ invalid pts based on nearest neighbor
!       Search around neighborhood of a pt
        do i=1,ixlen
          do j=1,iylen
            if(kbp(i,j)==-1) then !invalid pts  
              !Compute max possible tier # for neighborhood
              mmax=max(i-1,ixlen-i,j-1,iylen-j)

              m=0 !tier #
              loop6: do
                m=m+1
                do ii=max(-m,1-i),min(m,ixlen-i)
                  i3=max(1,min(ixlen,i+ii))
                  do jj=max(-m,1-j),min(m,iylen-j)
                    j3=max(1,min(iylen,j+jj))
                    if(kbp(i3,j3)==1) then !found
                      i1=i3; j1=j3
                      exit loop6   
                    endif
                  enddo !jj
                enddo !ii

                if(m==mmax) then
                  write(11,*)'Max. exhausted:',i,j,mmax
                  write(11,*)'kbp'
                  do ii=1,ixlen
                    do jj=1,iylen
                      write(11,*)ii,jj,kbp(ii,jj)
                    enddo !jj
                  enddo !ii
                  stop
                endif
              end do loop6

              salt(i,j,1:ilen)=salt(i1,j1,1:ilen)
              temp(i,j,1:ilen)=temp(i1,j1,1:ilen)
!              uvel(i,j,1:ilen)=uvel(i1,j1,1:ilen)
!              vvel(i,j,1:ilen)=vvel(i1,j1,1:ilen)
!              ssh(i,j)=ssh(i1,j1)

              !Check 
              do k=1,ilen
                if(salt(i,j,k)<saltmin.or.salt(i,j,k)>saltmax.or. &
                   temp(i,j,k)<tempmin.or.temp(i,j,k)>tempmax) then
!                   abs(uvel(i,j,k))>vmag_max.or.abs(vvel(i,j,k))>vmag_max.or. &
!                   abs(ssh(i,j))>ssh_max) then
                  write(11,*)'Fatal: no valid values after searching:',it2,i,j,k,salt(i,j,k), &
     &temp(i,j,k) !,uvel(i,j,k),vvel(i,j,k),ssh(i,j)
                  stop
                endif
              enddo !k

            endif !kbp(i,j)==-1
          enddo !j=iylen1,iylen2
        enddo !i=ixlen1,ixlen2

!       Do something for 1st step only
        if(ifile==1.and.isub==1.and.it2==ilo) then
!         Test outputs
          icount=0
          do i=1,ixlen
            do j=1,iylen
              icount=icount+1
!              write(95,*)icount,lon(i,j),lat(i,j),ssh(i,j)
!              write(96,*)icount,lon(i,j),lat(i,j),uvel(i,j,ilen)
!              write(97,*)icount,lon(i,j),lat(i,j),vvel(i,j,ilen)
              write(98,*)icount,lon(i,j),lat(i,j),salt(i,j,1) !,i,j
              write(99,*)icount,lon(i,j),lat(i,j),temp(i,j,ilen)
              write(100,*)icount,lon(i,j),lat(i,j),temp(i,j,1)
            enddo !j
          enddo !i
          print*, 'done outputting test outputs for nc'
     
!         Find parent elements for hgrid.ll
          ixy=0
          loop4: do i=1,np
            if(include2(i)==0) cycle loop4

            do ix=1,ixlen-1 
              do iy=1,iylen-1 
                x1=lon(ix,iy); x2=lon(ix+1,iy); x3=lon(ix+1,iy+1); x4=lon(ix,iy+1)
                y1=lat(ix,iy); y2=lat(ix+1,iy); y3=lat(ix+1,iy+1); y4=lat(ix,iy+1)
                a1=abs(signa(xl(i),x1,x2,yl(i),y1,y2))
                a2=abs(signa(xl(i),x2,x3,yl(i),y2,y3))
                a3=abs(signa(xl(i),x3,x4,yl(i),y3,y4))
                a4=abs(signa(xl(i),x4,x1,yl(i),y4,y1))
                b1=abs(signa(x1,x2,x3,y1,y2,y3))
                b2=abs(signa(x1,x3,x4,y1,y3,y4))
                rat=abs(a1+a2+a3+a4-b1-b2)/(b1+b2)
                if(rat<small1) then
                  ixy(i,1)=ix; ixy(i,2)=iy
!                 Find a triangle
                  in=0 !flag
                  do l=1,2 !split quad
                    ap=abs(signa(xl(i),x1,x3,yl(i),y1,y3))
                    if(l==1) then !nodes 1,2,3
                      bb=abs(signa(x1,x2,x3,y1,y2,y3))
                      wild(l)=abs(a1+a2+ap-bb)/bb
                      if(wild(l)<small1*5) then
                        in=1
                        arco(1,i)=max(0.,min(1.,a2/bb))
                        arco(2,i)=max(0.,min(1.,ap/bb))
                        exit
                      endif
                    else !nodes 1,3,4
                      bb=abs(signa(x1,x3,x4,y1,y3,y4))
                      wild(l)=abs(a3+a4+ap-bb)/bb
                      if(wild(l)<small1*5) then
                        in=2
                        arco(1,i)=max(0.,min(1.,a3/bb))
                        arco(2,i)=max(0.,min(1.,a4/bb))
                        exit
                      endif
                    endif
                  enddo !l=1,2
                  if(in==0) then
                    write(11,*)'Cannot find a triangle:',(wild(l),l=1,2)
                    stop
                  endif
                  ixy(i,3)=in
                  arco(3,i)=max(0.,min(1.,1-arco(1,i)-arco(2,i)))
                  cycle loop4
                endif !rat<small1
              enddo !iy=iylen1,iylen2-1
            enddo !ix=ixlen1,ixlen2-1
          end do loop4 !i=1,np
        endif !ifile==1.and.it2==
    
!       Do interpolation: all at 1st  step, bnd only for the rest
!        if(ifile==1.and.it2==ilo) then
!          iup=np
!        else
!          iup=nond0
!        endif

!        print*, 'Time out (days)=',timeout/86400,it2,ilo,ntime
        tempout=-99; saltout=-99
        npout=0 !# of _valid_ output points
        do ii=1,np
          i=ii !iond2(ii) !node #

          if(ixy(i,1)==0.or.ixy(i,2)==0) then
            ! write(*,*)'Cannot find a parent element:',i
            ! if(include2(i)/=0.) then 
              !npout=npout+1
              !imap(npout)=i
              tempout(:,i)=tem_outside
              saltout(:,i)=sal_outside
            ! endif
            if (include2(i)/=0.) then
                print*,'This node is not covered by the data', i
            endif
          else !found parent
            npout=npout+1
            imap(npout)=i
            ix=ixy(i,1); iy=ixy(i,2); in=ixy(i,3)
            !Find vertical level
            tempout(:,i)=-999
            do k=1,nvrt
              if(kbp(ix,iy)==-1) then
                lev=ilen-1; vrat=1
              else if(z(i,k)<=zm(ix,iy,kbp(ix,iy))) then
                lev=kbp(ix,iy); vrat=0
              else if(z(i,k)>=zm(ix,iy,ilen)) then !above f.s.
                lev=ilen-1; vrat=1
              else
                lev=-99 !flag
                do kk=1,ilen-1
                  if(z(i,k)>=zm(ix,iy,kk).and.z(i,k)<=zm(ix,iy,kk+1)) then
                    lev=kk
                    vrat=(zm(ix,iy,kk)-z(i,k))/(zm(ix,iy,kk)-zm(ix,iy,kk+1))
                    exit
                  endif
                enddo !kk
                if(lev==-99) then
                  write(11,*)'Cannot find a level:',i,k,z(i,k),(zm(ix,iy,l),l=1,kbp(ix,iy))
                  stop
                endif
              endif
          
!              write(18,*)i,k,ix,iy,lev,vrat,kbp(ix,iy)
              wild2(1,1)=temp(ix,iy,lev)*(1-vrat)+temp(ix,iy,lev+1)*vrat
              wild2(1,2)=salt(ix,iy,lev)*(1-vrat)+salt(ix,iy,lev+1)*vrat
              wild2(2,1)=temp(ix+1,iy,lev)*(1-vrat)+temp(ix+1,iy,lev+1)*vrat
              wild2(2,2)=salt(ix+1,iy,lev)*(1-vrat)+salt(ix+1,iy,lev+1)*vrat
              wild2(3,1)=temp(ix+1,iy+1,lev)*(1-vrat)+temp(ix+1,iy+1,lev+1)*vrat
              wild2(3,2)=salt(ix+1,iy+1,lev)*(1-vrat)+salt(ix+1,iy+1,lev+1)*vrat
              wild2(4,1)=temp(ix,iy+1,lev)*(1-vrat)+temp(ix,iy+1,lev+1)*vrat
              wild2(4,2)=salt(ix,iy+1,lev)*(1-vrat)+salt(ix,iy+1,lev+1)*vrat

!              wild2(5,1)=uvel(ix,iy,lev)*(1-vrat)+uvel(ix,iy,lev+1)*vrat
!              wild2(5,2)=vvel(ix,iy,lev)*(1-vrat)+vvel(ix,iy,lev+1)*vrat
!              wild2(6,1)=uvel(ix+1,iy,lev)*(1-vrat)+uvel(ix+1,iy,lev+1)*vrat
!              wild2(6,2)=vvel(ix+1,iy,lev)*(1-vrat)+vvel(ix+1,iy,lev+1)*vrat
!              wild2(7,1)=uvel(ix+1,iy+1,lev)*(1-vrat)+uvel(ix+1,iy+1,lev+1)*vrat
!              wild2(7,2)=vvel(ix+1,iy+1,lev)*(1-vrat)+vvel(ix+1,iy+1,lev+1)*vrat
!              wild2(8,1)=uvel(ix,iy+1,lev)*(1-vrat)+uvel(ix,iy+1,lev+1)*vrat
!              wild2(8,2)=vvel(ix,iy+1,lev)*(1-vrat)+vvel(ix,iy+1,lev+1)*vrat
              if(in==1) then
                tempout(k,i)=wild2(1,1)*arco(1,i)+wild2(2,1)*arco(2,i)+wild2(3,1)*arco(3,i)
                saltout(k,i)=wild2(1,2)*arco(1,i)+wild2(2,2)*arco(2,i)+wild2(3,2)*arco(3,i)
              else
                tempout(k,i)=wild2(1,1)*arco(1,i)+wild2(3,1)*arco(2,i)+wild2(4,1)*arco(3,i)
                saltout(k,i)=wild2(1,2)*arco(1,i)+wild2(3,2)*arco(2,i)+wild2(4,2)*arco(3,i)
              endif

              !Check
              if(tempout(k,i)<tempmin.or.tempout(k,i)>tempmax.or. &
                saltout(k,i)<saltmin.or.saltout(k,i)>saltmax) then
                write(11,*)'Interpolated values invalid:',i,k,tempout(k,i),saltout(k,i) 
                stop
              endif

              !Correct near surface T bias
              if(kbp(ix,iy)/=-1.and.z(i,k)>-10) tempout(k,i)=tempout(k,i)-1

!             Enforce lower bound for temp. for eqstate
              tempout(k,i)=max(0.,tempout(k,i))
            enddo !k=1,nvrt
          endif !ixy(i,1)==0.or.
        enddo !ii
    
!       Output
!        print*, 'Time out (days)=',timeout/86400,it2,ilo,ntime
        print*, 'outputting at day ',timeout/86400,npout
!        write(54)timeout
!        do i=1,np
!          write(54)tempout(1:nvrt,i)
!        enddo !i
        if(ifile==1.and.isub==1.and.it2==ilo) then
          iret=nf90_create('TEM_nu.nc',OR(NF90_CLOBBER,NF90_NETCDF4),ncid_T)
          iret=nf90_def_dim(ncid_T,'node',npout,node_dim)
          iret=nf90_def_dim(ncid_T,'nLevels',nvrt,nv_dim)
          iret=nf90_def_dim(ncid_T,'one',1,one_dim)
          iret=nf90_def_dim(ncid_T,'time', NF90_UNLIMITED,itime_dim)

          var1d_dims(1)=itime_dim
          iret=nf90_def_var(ncid_T,'time',NF90_DOUBLE,var1d_dims,itime_id_T)
          var1d_dims(1)=node_dim
          iret=nf90_def_var(ncid_T,'map_to_global_node',NF90_INT,var1d_dims,id_map_T)
          var4d_dims(1)=one_dim; var4d_dims(2)=nv_dim; 
          var4d_dims(3)=node_dim; var4d_dims(4)=itime_dim
          iret=nf90_def_var(ncid_T,'tracer_concentration',NF90_FLOAT,var4d_dims,ivar_T)
          iret=nf90_enddef(ncid_T)

          iret=nf90_create('SAL_nu.nc',OR(NF90_CLOBBER,NF90_NETCDF4),ncid_S)
          iret=nf90_def_dim(ncid_S,'node',npout,node_dim)
          iret=nf90_def_dim(ncid_S,'nLevels',nvrt,nv_dim)
          iret=nf90_def_dim(ncid_S,'one',1,one_dim)
          iret=nf90_def_dim(ncid_S,'time', NF90_UNLIMITED,itime_dim)

          var1d_dims(1)=itime_dim
          iret=nf90_def_var(ncid_S,'time',NF90_DOUBLE,var1d_dims,itime_id_S)
          var1d_dims(1)=node_dim
          iret=nf90_def_var(ncid_S,'map_to_global_node',NF90_INT,var1d_dims,id_map_S)
          iret=nf90_def_var(ncid_S,'tracer_concentration',NF90_FLOAT,var4d_dims,ivar_S)
          iret=nf90_enddef(ncid_S)
        endif !ifile

        aa1(1)=timeout/86400
        iret=nf90_put_var(ncid_T,itime_id_T,aa1,(/irecout2/),(/1/))
        iret=nf90_put_var(ncid_S,itime_id_S,aa1,(/irecout2/),(/1/))
        iret=nf90_put_var(ncid_T,id_map_T,imap(1:npout),(/1/),(/npout/))
        iret=nf90_put_var(ncid_S,id_map_S,imap(1:npout),(/1/),(/npout/))
        iret=nf90_put_var(ncid_T,ivar_T,tempout(:,imap(1:npout)),(/1,1,1,irecout2/),(/1,nvrt,npout,1/))
        iret=nf90_put_var(ncid_S,ivar_S,saltout(:,imap(1:npout)),(/1,1,1,irecout2/),(/1,nvrt,npout,1/))
        ! iret=nf90_put_var(ncid_T,ivar_T,tempout(:,:npout),(/1,1,1,irecout2/),(/1,nvrt,npout,1/))
        ! iret=nf90_put_var(ncid_S,ivar_S,saltout(:,:npout),(/1,1,1,irecout2/),(/1,nvrt,npout,1/))
      enddo !it2=ilo,ntime

      status = nf90_close(sid)
!end11
      print*, 'done reading nc for file ',ifile
!--------------------------------------------------------------------
        enddo !isub=1,4
      enddo !ifile=1,

      iret=nf90_close(ncid_T)
      iret=nf90_close(ncid_S)

!      deallocate(lat,lon,zm,h,kbp,ihope,xind,yind,lind,salt,temp)

      print*, 'Finished'
!     End of main

!     Subroutines
      contains
!     Internal subroutine - checks error status after each netcdf, 
!     prints out text message each time an error code is returned. 
      subroutine check(status)
      integer, intent ( in) :: status
    
      if(status /= nf90_noerr) then 
        print *, trim(nf90_strerror(status))
        print *, 'failed to open nc files'
        stop
      end if
      end subroutine check  

      end program gen_hot

      function signa(x1,x2,x3,y1,y2,y3)

      signa=((x1-x3)*(y2-y3)-(x2-x3)*(y1-y3))/2

      return
      end

