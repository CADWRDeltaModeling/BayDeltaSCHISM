# Bay-Delta SCHISM Mesh Files

Here you'll find the \*.2dm files needed to generate the \*.gr3 files needed to run SCHISM. These files are not provided in the GitHub repository because each file is larger than 40 GB and cannot be hosted and version controlled by GitHub. 

Instead, you'll use DVC to pull from a repository. We have the default set to the S3 remote storage support because that is what we use internally at DWR's Delta Modeling Section (DMS). However, if you are not internal to DMS, you'll need to pull from the Azure Blob Container. Instructions below:

## Pulling 2dm files from DVC

### Internal to DMS (DWR employees)

Navigate to this repository parent folder (BayDeltaSCHISM) and type:

```
dvc pull
```

### External to DMS (public)

You'll need to set your remote repository using:

```
dvc pull -r azure
```