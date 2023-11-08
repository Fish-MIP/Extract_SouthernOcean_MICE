#!/usr/bin/python

## Extracting data for the Southern Ocean - MICE model from DKRZ server
## Date: 2023-11-07
## Author: Denisse Fierro Arcos

#Libraries
import numpy as np
import xarray as xr
import pandas as pd
from glob import glob
import os
import re
import itertools

#######################################################################################
#Base directory where data is currently stored
base_dir = ['/work/bb0820/ISIMIP/ISIMIP3a/InputData/climate/ocean/obsclim/global/monthly/historical/GFDL-MOM6-COBALT2/',
            '/work/bb0820/ISIMIP/ISIMIP3b/InputData/climate/ocean/uncorrected/global/monthly/ssp585/GFDL-ESM4']
#Base directory where data will be stored
base_out = 'Data_Extraction'
#Ensuring it exists
os.makedirs(base_out, exist_ok = True)

#Masks - 1 deg
mask_1deg = xr.open_dataset('Southern_Ocean_mask_1deg.nc').region
#Subsetting to only include Southern Ocean
mask_1deg = mask_1deg.rename({'latitude': 'lat', 'longitude': 'lon'}).sel(lat = slice(-30, -90))

#Masks - 0.25 deg
mask_025deg = xr.open_dataset('Southern_Ocean_mask_025deg.nc').region
#Subsetting to only include Southern Ocean
mask_025deg = mask_025deg.rename({'latitude': 'lat', 'longitude': 'lon'}).sel(lat = slice(-30, -90))

#Variables of interest
var_list = ['thetao', 'chl', 'siconc', 'zmeso_']

###### Defining useful functions ######

## Loading data with dates that are not CF compliant
def load_ds_noncf(fn):
    '''
    This function loads non-CF compliant datasets where dates cannot be read. It needs one input:
    fn - ('string') refers to full filepath where the non-CF compliant dataset is located
    '''
    #Loading dataset without decoding times
    ds = xr.open_dataset(fn, decode_times = False)
    
    #Checking time dimension attributes
    #Extracting reference date from units 
    init_date = re.search('\\d{4}-\\d{1,2}-\\d{1,2}', ds.time.attrs['units']).group(0)
    
    #If month is included i the units calculate monthly timesteps
    if 'month' in ds.time.attrs['units']:
      #If month values include decimals, remove decimals
      if ds.time[0] % 1 != 0:
        ds['time'] = ds.time - ds.time%1
      #From the reference time, add number of months included in time dimension
      try:
        new_date = [pd.Period(init_date, 'M')+pd.offsets.MonthEnd(i) for i in ds.time.values]
        #Change from pandas period to pandas timestamp
        new_date =[pd.Period.to_timestamp(i) for i in new_date]
      #If any errors are encountered
      except:
        #If dates are before 1677, then calculate keep pandas period
        new_date = pd.period_range(init_date, periods = len(ds.time.values), freq ='M')
        #Add year and month coordinates in dataset
        ds.coords['year'] = ('time', new_date.year.values)
        ds.coords['month'] = ('time', new_date.month.values)
    
    #Same workflow as above but based on daily timesteps
    elif 'day' in ds.time.attrs['units']:
      if ds.time[0] % 1 != 0:
        ds['time'] = ds.time - ds.time%1
      try:
        new_date = [pd.Period(init_date, 'D')+pd.offsets.Day(i) for i in ds.time.values]
        new_date =[pd.Period.to_timestamp(i) for i in new_date]
      except:
        new_date = pd.period_range(init_date, periods = len(ds.time.values), freq ='D')
        ds.coords['year'] = ('time', new_date.year.values)
        ds.coords['month'] = ('time', new_date.month.values)
    
    #Replace non-cf compliant time to corrected time values
    ds['time'] = new_date

    return ds


## Extracting surface data
def masking_data(ds, var_int, mask):
  #Extracting only variable of interest and subset data to only include Southern Ocean
  try:
    ds = ds[var_int].sel(lat = slice(-30, -90))
  except:
    #Getting name of variables available in dataset
    var_ds = list(ds.keys())
    #If there are multiple variable, keep variable that is similar to variable in file name
    if len(var_ds) > 1:
      var_ds = [v for v in var_ds if v in var_int][0]
    else:
      var_ds = var_ds[0]
    ds = ds[var_ds].sel(lat = slice(-30, -90))

  #Applying mask
  ds.coords['mask'] = (('lat', 'lon'), mask.values)
  
  #Checking if dataset has depth levels
  #If so, add depth dimension to 51.25 depth bin
  if 'lev' in ds.coords:
    ds = ds.sel(lev = slice(0, 52)).mean('lev')
  elif 'olevel' in ds.coords:
    ds = ds.sel(olevel = slice(0, 52)).mean('olevel')
  elif 'olevel_2' in ds.coords:
    ds = ds.isel(olevel_2 = slice(0, 52)).mean('olevel_2')
  
  return ds

#Calculating seasonal means
def seasonal_means(ds, path_out):
  #Creating empty list to store seasonal means
  seasonal_means = []
  #Getting years in dataset
  years_ds = np.unique(ds.time.dt.year)
  
  #Winter
  for yr, da in ds.groupby('time.year'):
    #Calculating seasonal mean
    winter = da.sel(time = slice(f'{yr}-05-01', f'{yr}-10-31')).groupby('mask').mean().mean('time')
    winter = winter.expand_dims({'time':[f'winter_{yr}']})
    seasonal_means.append(winter)
  
  #Summer
  #Looping through each year
  for yr in years_ds:
    #Extracting data for each year
    summer = ds.sel(time = slice(f'{yr}-11-01', f'{yr+1}-04-30')).groupby('mask').mean().mean('time')
    summer = summer.expand_dims({'time':[f'summer_{yr}']})
    seasonal_means.append(summer)

  #Concatenating data back together
  seasonal_means = xr.concat(seasonal_means, dim = 'time')
  
  #Saving csv
  seasonal_means.to_pandas().to_csv(path_out, na_rep = np.nan)
  

###### Applying functions to all files in directories of interest ######
###Loop through each directory
for base in base_dir:
  #Find netcdf files for expriments and models of interest
  all_files = [glob(os.path.join(base, f'*{var}*.nc')) for var in var_list]
  file_list = list(itertools.chain(*all_files))

  #Loop through variables of interest
  for dp in file_list:
    ###Loop through each file
    var_int = re.split('_\\d{2,3}a', re.split('obsclim_|ssp585_', dp)[-1])[0]
    #Extracting base file name to create output
    file_out = re.split('/GFDL-MOM6-COBALT2/|/GFDL-ESM4/', dp)[-1].replace('global_monthly', 'SouthernOcean_seasonal').replace('.nc', '.csv')
    #Creating output path
    path_out = os.path.join(base_out, file_out)
    
    #Loading data
    try:
        ds = load_ds_noncf(dp)
    except:
        print('Time in historical data is not cf compliant. Fixing dates based on years in file name.')
        try:
          ds = xr.open_dataset(dp)
        except:
          print(f'Time could not be decoded for file: {dp}')
          pass
    
    #Loading data
    try:
      ds is not None
      #Loading correct mask
      try:
        if '60arcmin' in dp:
          mask = mask_1deg
        if '15arcmin' in dp:
          mask = mask_025deg
        #Masking data 
        masked_ds = masking_data(ds, var_int, mask)
        #Calculating seasonal means
        seasonal_means(masked_ds, path_out)
      except:
        print(f'File could not be processed: {f}')
        pass
    except:
      pass
      

