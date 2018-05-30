function sal=conductivity2S(T,Ec);
%Calculate salinity from T, Conductivity (assuming const. pressure)
%from Lewis (1980) (via Suits_2002)
%clear all; close all;
A=[0.008 -0.1692 25.3851 14.0941 -7.0262 2.7081];
B=[0.0005 -0.0056 -0.0066 -0.0375 0.0636 -0.0144];
%disp('Sum A,B='); [sum(A) sum(B)]
%T=25; 
%Ec=[302 1346 1824];
Ec_T0=53097;
gam=(T-15)/(1+0.0162*(T-15));

rt=Ec/Ec_T0;
srt=sqrt(rt);
rt2=rt*rt;
Rt=[1 srt rt rt*srt rt2 rt2*srt];
sal=sum(A.*Rt)+gam*sum(B.*Rt);
