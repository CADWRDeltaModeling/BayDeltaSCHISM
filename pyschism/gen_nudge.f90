!     Generate elliptical-zone nudging factors on hgrid.gr3
!	  Input: hgrid.gr3;  center @ the mouth; rx,ry,rat,rmax
!     Output: nudge.gr3
!	  WARNING: Don't forget to zero out estuary and river values!!!!!!!!!!
!     ifort -Bstatic -O3 -o gen_nudge gen_nudge.f90

      implicit real*8(a-h,o-z)
      dimension nm(4)
        
!     Center: near GG
      x0=542699
      y0=4183642

!     Minor and major axes
      rx=32.3e3
      ry=rx
      rat=41.e3/rx !(outer rx)/(inner rx); same for ry; must be >1
      rmax=1./2/86400 !1/relax; dt removed fro R1219

      open(14,file='hgrid.gr3',status='old')
      open(13,file='nudge.gr3')
      read(14,*)
      read(14,*)ne,np
      write(13,*)
      write(13,*)ne,np
      do i=1,np
        read(14,*)j,x,y,h
        rr=(x-x0)**2/rx/rx+(y-y0)**2/ry/ry
        tnu=rmax*(rr-1)/(rat*rat-1)
        tnu=dmax1(0.d0,dmin1(rmax,tnu))
        write(13,'(i10,2(1x,e24.10),1x,e12.6)')i,x,y,tnu
      enddo !i

      do i=1,ne
        read(14,*)j,k,(nm(l),l=1,k)
        write(13,*)j,k,(nm(l),l=1,k)
      enddo !i

      stop
      end
