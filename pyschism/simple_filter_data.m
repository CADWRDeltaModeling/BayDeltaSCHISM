function noise=simple_filter_data(d,cycles,pass)
% noise=simple_filter_data(data,cycles,pass)
% Assumes no gaps and adequate length of data
% simple_filter_data takes a d=[time, variable] array and returns the filtered data [time, var2]
% (time is assumed to be in units of days).
% 'noise' is also a time series [time, variable].
% cycles is the cutoff frequency in days^-1   (e.g. 0.5 is a period of 2
% days), and should be the 2 value band cutoff, with lower frequency first.
% Standard cycles for annual analysis is [0.8 2.5] for band pass, 0.8 for low pass, and 2.5 for high pass
% Does high pass if pass= 'high', low pass if pass = 'low', band if pass = 'bandpass'
% for band pass. 

% core functionality comes from butter (to generate the filter) and filter
% (to process the data)
% filter is used twice to create a non-causal filter
% uses a 4th order butterworth filter with the specified cutoff frequency

% To track down the phase shift after _low-pass_ filtering, filter the time itself
%   n2=simple_filter_data([time time],cycles,pass)
% and may need to cut off some parts on the left edge. Then 
% [n2(:,2) noise(:,2)] has no phase shift. 
% Alternatively, do forward and backward filters to get rid of phase lag as follows:


t=d(:,1);
d=d(:,2);
dt=diff(t); %timesteps
ts=median(dt); %length of median timestep
nyquist=1./(2*ts);%nyquist frequency expressd(in 1/days)
cutoff=1./(ceil(1./(cycles./nyquist))); %cutoff expressed as a fraction of the nyquist frequence
bad = (ceil(max(1./cutoff))*2); % remove edge ringing
[a,b] = butter(2,cutoff,pass);
n=fliplr(filter(a,b,fliplr(filter(a,b,d)))); % noncausal use of the butterworth filter
t(end-bad+1:end)=[];
n(end-bad+1:end)=[];
t(1:bad)=[];
n(1:bad)=[];
noise=[t n];
