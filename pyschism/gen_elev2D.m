%Generate elev2D.th.
%Inputs: assume fixed positions for the ocean bnd nodes; node 1 is Pt. Reyes
%        (1) some consts below;
%        (2) Point_Reyes.NAVD_PST.clean (6min interval);
%        (3) ocean.nodes (list of open ocean nodes)
%        (4) ocean.ap (amp/phases from WEBTIDES)
%Output: elev2D.th

close all; clear all;

addpath ~/Scripts/Matlab_scripts;

%scale_M2=0.554/0.5794; %error due to WEBTIDE for M2 ampli.

scale_K1=0.95; %scale applied to all diural signals
rnday=290;
dt=120; %sec
timeout=dt/86400:dt/86400:rnday; %in days
timeout2=-5:dt/86400:(rnday+2); %for shifting curves

pr=load('Point_Reyes.NAVD_PST.clean'); %time(days PST from 3/12), m NAVD88
ocean_nd=load('ocean.nodes'); %ocean bnd nodes in ocean.gr3 and ocean.ap
nond=length(ocean_nd);

%Read in ocean.ap
fid=fopen('ocean.ap','r');
s=fscanf(fid,'%c',40); %canot use %s
np=fscanf(fid,'%d',1);
nfr=fscanf(fid,'%d',1);
for i=1:nfr
  nm=fscanf(fid,'%s\n',1);
  if(regexp(nm,'K1')); iK1=i; end;
  if(regexp(nm,'M2')); iM2=i; end;
  aa=fscanf(fid,'%f',np*2); %row major 
  bb=reshape(aa,2,np); 
  bb=bb';
  ap(i).am=bb(:,1);
  ap(i).ph=bb(:,2);
end %for i
fclose(fid);

%Filter P.R.
pr_lo1=simple_filter_data(pr,0.8,'low');
tmp=flipud(pr_lo1);
pr_lo2=simple_filter_data([-tmp(:,1) tmp(:,2)],0.8,'low'); %'-' to get dt>0
pr_lo=[-pr_lo2(:,1) pr_lo2(:,2)];
%Cannot use high pass to get semi-diurnal; the 2nd filter damps the amplitude
pr_d1=simple_filter_data(pr,[0.8 24/14.],'bandpass'); %diurnal
tmp=flipud(pr_d1);
pr_d2=simple_filter_data([-tmp(:,1) tmp(:,2)],[0.8 24/14.],'bandpass'); 
pr_d=[-pr_d2(:,1) pr_d2(:,2)];

figure(1);
subplot(3,1,1);
plot(pr_lo(:,1),pr_lo(:,2),'k',pr(:,1),pr(:,2),'r--');
title('Sub-tide');
subplot(3,1,2);
plot(pr_d(:,1),pr_d(:,2),'k',pr(:,1),pr(:,2),'r--',pr_d1(:,1),pr_d1(:,2),'b');
title('Diurnal');

%Interpolate onto timeout2
pr3=interp1(pr(:,1),pr(:,2),timeout2);
pr_lo3=interp1(pr_lo(:,1),pr_lo(:,2),timeout2);
pr_d3=interp1(pr_d(:,1),pr_d(:,2),timeout2);
if(sum(isnan(pr3))+sum(isnan(pr_lo3))+sum(isnan(pr_d3)) ~=0)
  [sum(isnan(pr3)) sum(isnan(pr_lo3)) sum(isnan(pr_d3))]
  error('Filtered values have nan');
end
pr_sd3=pr3-pr_lo3-pr_d3;

subplot(3,1,3);
plot(timeout2,pr_sd3,'k',pr(:,1),pr(:,2),'r--');
title('Semi-diurnal');

%Adjust diurnal (using K1 as representative)
nd0=ocean_nd(1); %P.R.
for i=1:nond
  nd=ocean_nd(i);
  lead=(-ap(iK1).ph(nd)+ap(iK1).ph(nd0))/360*0.9973; %in days; note the signs
  eta_K1(:,1)=timeout2-lead;
  rat=ap(iK1).am(nd)/ap(iK1).am(nd0)*scale_K1;
  eta_K1(:,2)=pr_d3*rat;
  %Interpolate into final timeout
  eta(i).K1=interp1(eta_K1(:,1),eta_K1(:,2),timeout);
  if(sum(isnan(eta(i).K1))~=0); error('K1 has nan'); end;
  clear eta_K1;
end %for i

%Adjust semi-d
for i=1:nond
  nd=ocean_nd(i);
  lead=(-ap(iM2).ph(nd)+ap(iM2).ph(nd0))/360*0.517525; %in days; note the signs
  eta_M2(:,1)=timeout2-lead;
  rat=ap(iM2).am(nd)/ap(iM2).am(nd0);
  eta_M2(:,2)=pr_sd3*rat;

  %Interpolate into final timeout
  eta(i).M2=interp1(eta_M2(:,1),eta_M2(:,2),timeout);
  if(sum(isnan(eta(i).M2))~=0) 
    [i sum(isnan(eta(i).M2))]
    error('M2 has nan'); 
  end 
  clear eta_M2;
end %for i

%Interpolate sub-tide onto final timeout
eta_lo=interp1(timeout2,pr_lo3,timeout);
if(sum(isnan(eta_lo))~=0); error('Sub-tide has nan'); end;

%Re-construct signal at all nodes
figure(2); icount=0;
hold on;
col={'k--','b--','g--','m--'};
plot(pr(:,1),pr(:,2),'r.');
for i=1:nond
  eta(i).all=eta(i).K1+eta(i).M2+eta_lo;

  if(i==1 || i==24 || i==41 || i==nond)
    icount=icount+1;
    %subplot(9,10,i);
    plot(timeout,eta(i).all,col{icount});
  end
end %for i

%Output
out=zeros(nond+1,length(timeout));
out(1,:)=timeout*86400;
for i=1:nond
  out(i+1,:)=eta(i).all;
end %for i

fid=fopen('elev2D.th','wb');
%out(1:nond+1,1:ntime); 1st row is time
fwrite(fid,out,'float32'); 
fclose(fid);
