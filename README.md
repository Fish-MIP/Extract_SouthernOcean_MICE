# Extracting data for the Southern Ocean MICE model
The Python script available here was developed to extract data from Earth System Models available in the DKRZ server. The masks used to extract data for this regions are available in the compressed (`7z`) folder.  

Note that sub-regions of the Southern Ocean have a unique ID identifying them in the masks. The name of each sub-region together with their ID are included in the csv file contained in the masks folder.  

To run the `DataExtraction_SouthernOcean.py` script in DKRZ, you will need to make a copy of this script and the masks available in a single folder within the DKRZ server. Then follow these steps:  
1. Connect to DKRZ server and navigate to folder containing the `DataExtraction_SouthernOcean.py` script  
2. Load `Python` by typing: `module load python3`  
3. Run the script by typing: `python DataExtraction_SouthernOcean.py`  
  
A new folder called `Data_Extraction` will be created and it will have files for the extracted data.  
   
