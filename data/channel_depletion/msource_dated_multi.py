
import pandas as pd
import numpy as np
df = pd.read_csv("msource_dated.th",sep="\s+",comment="#",index_col=0,parse_dates=[0],dtype=float,header=0)


ncol = len(df.columns)//2
lev0 = df.columns[0:ncol].to_list()
lev0 = lev0 + lev0
newindexvals = np.repeat(["temperature","salinity"],ncol)
newindex = pd.MultiIndex.from_arrays([newindexvals,lev0],names=["variable","location"])
df.columns = newindex
df.to_csv("msource_dated_multi.th",sep=" ",index=True,header=True,date_format="%Y-%m-%dT%H:%M",float_format="%.2f")
print(df.head())

df2 = pd.read_csv("msource_dated_multi.th",sep="\s+",comment="#",index_col=0,parse_dates=[0],dtype=float,header=[0,1])
print(df2)