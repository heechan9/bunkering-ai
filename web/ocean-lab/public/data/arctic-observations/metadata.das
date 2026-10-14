Attributes {
  time {
    String _CoordinateAxisType "Time";
    Float64 actual_range 1.719792e+9, 1.7717184e+9;
    String axis "T";
    String calendar "proleptic_gregorian";
    String coverage_content_type "coordinate";
    String ioos_category "Time";
    String long_name "ANSI date";
    String standard_name "time";
    String time_origin "01-JAN-1970 00:00:00";
    String units "seconds since 1970-01-01T00:00:00Z";
    Float64 valid_range 0.0, 30000.0;
  }
  y {
    Float64 _FillValue NaN;
    Float64 actual_range -5337500.0, 5837500.0;
    String axis "Y";
    String coverage_content_type "coordinate";
    String ioos_category "Location";
    String long_name "y coordinate of projection";
    String standard_name "projection_y_coordinate";
    String units "m";
    Float64 valid_range -5350000.0, 5850000.0;
  }
  x {
    Float64 _FillValue NaN;
    Float64 actual_range -3837500.0, 3737500.0;
    String axis "X";
    String coverage_content_type "coordinate";
    String ioos_category "Location";
    String long_name "x coordinate of projection";
    String standard_name "projection_x_coordinate";
    String units "m";
    Float64 valid_range -3850000.0, 3750000.0;
  }
  cdr_seaice_conc_interp_spatial_flag {
    Byte _FillValue -1;
    String _Unsigned "true";
    Float64 colorBarMaximum 20.0;
    Float64 colorBarMinimum 0.0;
    Byte flag_masks 1, 2, 4, 8, 16, 32;
    String flag_meanings "19v_tb_value_interpolated 19h_tb_value_interpolated 22v_tb_value_interpolated 37v_tb_value_interpolated 37h_tb_value_interpolated pole_hole_spatially_interpolated_(Arctic_only)";
    String ioos_category "Quality";
    String long_name "NOAA/NSIDC CDR of Passive Microwave Sea Ice Concentration spatial interpolation flags";
    String standard_name "status_flag";
    String units "1";
    Byte valid_range 0, 63;
  }
  cdr_seaice_conc_qa_flag {
    Byte _FillValue -1;
    String _Unsigned "true";
    Float64 colorBarMaximum 80.0;
    Float64 colorBarMinimum 0.0;
    Byte flag_masks 1, 2, 4, 8, 16, 32, 64, -128;
    String flag_meanings "BT_weather_filter_applied NT_weather_filter_applied Land_spillover_filter_applied No_input_data invalid_ice_mask_applied spatial_interpolation_applied temporal_interpolation_applied melt_start_detected";
    String ioos_category "Quality";
    String long_name "NOAA/NSIDC CDR of Passive Microwave Sea Ice Concentration QA flags";
    String standard_name "status_flag";
    String units "1";
    Byte valid_range 0, -1;
  }
  cdr_seaice_conc_interp_temporal_flag {
    Byte _FillValue -1;
    String _Unsigned "true";
    Float64 colorBarMaximum 60.0;
    Float64 colorBarMinimum 0.0;
    String comment "Value of 0 indicates no temporal interpolation occurred.  Values greater than 0 and less than or equal to 55 are of the form 'AB' where 'A' indicates the number of days prior to the current day and 'B' indicates the number of days after the current day used to linearly interpolate the data.  If either A or B are zero, the value was extrapolated from that date rather than interpolated.  A value of 255 indicates that temporal interpolation could not be accomplished.";
    String flag_meanings "no_temporal_interp 1_day_after 2_days_after 3_days_after 1_day_prior 1_day_prior_and_1_day_after 1_day_prior_and_2_days_after 1_day_prior_and_3_days_after 1_day_prior_and_4_days_after 1_day_prior_and_5_days_after 2_days_prior 2_days_prior_and_1_day_after 2_days_prior_and_2_days_after 2_days_prior_and_3_days_after 2_days_prior_and_4_days_after 2_days_prior_and_5_days_after 3_days_prior 3_days_prior_and_1_day_after 3_days_prior_and_2_days_after 3_days_prior_and_3_days_after 3_days_prior_and_4_days_after 3_days_prior_and_5_days_after 4_days_prior_and_1_day_after 4_days_prior_and_2_days_after 4_days_prior_and_3_days_after 4_days_prior_and_4_days_after 4_days_prior_and_5_days_after 5_days_prior_and_1_day_after 5_days_prior_and_2_days_after 5_days_prior_and_3_days_after 5_days_prior_and_4_days_after 5_days_prior_and_5_days_after";
    Byte flag_values 0, 1, 2, 3, 10, 11, 12, 13, 14, 15, 20, 21, 22, 23, 24, 25, 30, 31, 32, 33, 34, 35, 41, 42, 43, 44, 45, 51, 52, 53, 54, 55;
    String ioos_category "Quality";
    String long_name "NOAA/NSIDC CDR of Passive Microwave Sea Ice Concentration temporal interpolation flags";
    String standard_name "status_flag";
    String units "1";
    Byte valid_range 0, 55;
  }
  cdr_seaice_conc {
    Float64 _FillValue NaN;
    String ancillary_variables "cdr_seaice_conc_stdev cdr_seaice_conc_qa_flag";
    Float64 colorBarMaximum 1.0;
    Float64 colorBarMinimum 0.0;
    String coverage_content_type "image";
    String ioos_category "Ice Distribution";
    String long_name "NOAA/NSIDC CDR of Passive Microwave Sea Ice Concentration";
    String standard_name "sea_ice_area_fraction";
    String units "1";
    Float64 valid_range 0.0, 1.0;
  }
  cdr_seaice_conc_stdev {
    Float32 _FillValue NaN;
    Float64 colorBarMaximum 0.1;
    Float64 colorBarMinimum 0.0;
    String ioos_category "Statistics";
    String long_name "NOAA/NSIDC CDR of Passive Microwave Sea Ice Concentration Source Estimated Standard Deviation";
    String units "1";
    Float32 valid_range 0.0, 1.0;
  }
  NC_GLOBAL {
    String _NCProperties "version=2,netcdf=4.8.1,hdf5=1.10.6";
    String acknowledgement "This project was supported in part by a grant from the NOAA Climate Data Record Program. The NASA Team and Bootstrap sea ice concentration algorithms were developed by Donald J. Cavalieri, Josefino C. Comiso, Claire L. Parkinson, and others at the NASA Goddard Space Flight Center in Greenbelt, MD.";
    String acknowledgment "This project was supported in part by a grant from the NOAA Climate Data Record Program. The NASA Team and Bootstrap sea ice concentration algorithms were developed by Donald J. Cavalieri, Josefino C. Comiso, Claire L. Parkinson, and others at the NASA Goddard Space Flight Center in Greenbelt, MD.";
    String cdm_data_type "Grid";
    String cdr_data_type "grid";
    String contributor_name "Walter N. Meier, Florence Fetterer, Ann Windnagel, J. Scott Stewart, Trey Stafford";
    String contributor_role "principal investigator, author, author, software developer, software developer";
    String Conventions "CF-1.11, ACDD-1.3";
    String creator_email "nsidc@nsidc.org";
    String creator_name "NSIDC/NOAA";
    String creator_type "institution";
    String creator_url "https://nsidc.org/";
    String date_created "2024-12-31T11:01:29Z";
    String defaultGraphQuery "cdr_seaice_conc[(last)][(5837500.0):(-5337500.0)][(-3837500.0):(3737500.0)]&.draw=surface";
    String geospatial_bounds "POLYGON ((-3850000 5850000, 3750000 5850000, 3750000 -5350000, -3850000 -5350000, -3850000 5850000))";
    String geospatial_bounds_crs "EPSG:3411";
    String geospatial_x_resolution "25000 meters";
    String geospatial_x_units "meters";
    String geospatial_y_resolution "25000 meters";
    String geospatial_y_units "meters";
    String grid_mapping_crs_wkt "PROJCS[\"NSIDC Sea Ice Polar Stereographic North\",GEOGCS[\"Unspecified datum based upon the Hughes 1980 ellipsoid\",DATUM[\"Not_specified_based_on_Hughes_1980_ellipsoid\",SPHEROID[\"Hughes 1980\",6378273,298.279411123061,AUTHORITY[\"EPSG\",\"7058\"]],AUTHORITY[\"EPSG\",\"6054\"]],PRIMEM[\"Greenwich\",0,AUTHORITY[\"EPSG\",\"8901\"]],UNIT[\"degree\",0.0174532925199433,AUTHORITY[\"EPSG\",\"9122\"]],AUTHORITY[\"EPSG\",\"4054\"]],PROJECTION[\"Polar_Stereographic\"],PARAMETER[\"latitude_of_origin\",70],PARAMETER[\"central_meridian\",-45],PARAMETER[\"scale_factor\",1],PARAMETER[\"false_easting\",0],PARAMETER[\"false_northing\",0],UNIT[\"metre\",1,AUTHORITY[\"EPSG\",\"9001\"]],AXIS[\"X\",EAST],AXIS[\"Y\",NORTH],AUTHORITY[\"EPSG\",\"3411\"]]";
    Float64 grid_mapping_false_easting 0.0;
    Float64 grid_mapping_false_northing 0.0;
    String grid_mapping_GeoTransform "-3850000 25000 0 5850000 0 -25000";
    Float64 grid_mapping_inverse_flattening 298.279411123064;
    Float64 grid_mapping_latitude_of_projection_origin 90.0;
    String grid_mapping_long_name "NSIDC_NH_PolarStereo_25km";
    Float64 grid_mapping_longitude_of_prime_meridian 0.0;
    String grid_mapping_name "polar_stereographic";
    String grid_mapping_proj4text "+proj=stere +lat_0=90 +lat_ts=70 +lon_0=-45 +k=1 +x_0=0 +y_0=0 +a=6378273 +b=6356889.449 +units=m +no_defs";
    Float64 grid_mapping_semi_major_axis 6378273.0;
    String grid_mapping_spatial_ref "PROJCS[\"NSIDC Sea Ice Polar Stereographic North\",GEOGCS[\"Unspecified datum based upon the Hughes 1980 ellipsoid\",DATUM[\"Not_specified_based_on_Hughes_1980_ellipsoid\",SPHEROID[\"Hughes 1980\",6378273,298.279411123061,AUTHORITY[\"EPSG\",\"7058\"]],AUTHORITY[\"EPSG\",\"6054\"]],PRIMEM[\"Greenwich\",0,AUTHORITY[\"EPSG\",\"8901\"]],UNIT[\"degree\",0.0174532925199433,AUTHORITY[\"EPSG\",\"9122\"]],AUTHORITY[\"EPSG\",\"4054\"]],PROJECTION[\"Polar_Stereographic\"],PARAMETER[\"latitude_of_origin\",70],PARAMETER[\"central_meridian\",-45],PARAMETER[\"scale_factor\",1],PARAMETER[\"false_easting\",0],PARAMETER[\"false_northing\",0],UNIT[\"metre\",1,AUTHORITY[\"EPSG\",\"9001\"]],AXIS[\"X\",EAST],AXIS[\"Y\",NORTH],AUTHORITY[\"EPSG\",\"3411\"]]";
    String grid_mapping_srid "urn:ogc:def:crs:EPSG::3411";
    Float64 grid_mapping_standard_parallel 70.0;
    Float64 grid_mapping_straight_vertical_longitude_from_pole -45.0;
    String grid_mapping_units "meters";
    String history "Generated from https://nsidc.org/data/nsidc-0080
2026-10-14T10:31:10Z (local files)
2026-10-14T10:31:10Z https://coastwatch.pfeg.noaa.gov/erddap/griddap/nsidcG10016v3nh1day.das";
    String id "https://doi.org/10.7265/j0z0-4h87";
    String infoUrl "https://nsidc.org/data/g10016/versions/3";
    String institution "NSIDC > National Snow and Ice Data Center";
    String keywords "CONTINENT > NORTH AMERICA > CANADA > HUDSON BAY, Continent > North America > Canada > Hudson Bay, Earth Science > Cryosphere > Sea Ice > Sea Ice Concentration, Geographic Region > Arctic, Geographic Region > Northern Hemisphere, Geographic Region > Polar, Ocean > Arctic Ocean, Ocean > Arctic Ocean > Barents Sea, Ocean > Arctic Ocean > Beaufort Sea, Ocean > Arctic Ocean > Chukchi Sea, Ocean > Atlantic Ocean > North Atlantic Ocean > Davis Straight, OCEAN > ATLANTIC OCEAN > NORTH ATLANTIC OCEAN > GULF OF ST LAWRENCE, Ocean > Atlantic Ocean > North Atlantic Ocean > North Sea, Ocean > Atlantic Ocean > North Atlantic Ocean > Norwegian Sea, OCEAN > ATLANTIC OCEAN > NORTH ATLANTIC OCEAN > SVALBARD AND JAN MAYEN, Ocean > Pacific Ocean, Ocean > Pacific Ocean > North Pacific Ocean > Bering Sea, Ocean > Pacific Ocean > North Pacific Ocean > Sea Of Okhotsk";
    String keywords_vocabulary "NASA Global Change Master Directory (GCMD) Keywords, Version 17.1";
    String license "No constraints on data access or use";
    String metadata_link "https://nsidc.org/data/g10016/versions/3";
    String naming_authority "org.doi.dx";
    String platform "DMSP 5D-3/F17 > Defense Meteorological Satellite Program-F17";
    String processing_level "NOAA Level 3";
    String product_version "v03r00";
    String program "NOAA Climate Data Record Program";
    String proj_crs_code "EPSG:3411";
    String project "NOAA/NSIDC passive microwave sea ice concentration climate data record";
    String references "Comiso, J. C., and F. Nishio. 2008. Trends in the Sea Ice Cover Using Enhanced and Compatible AMSR-E, SSM/I, and SMMR Data. Journal of Geophysical Research 113, C02S07, doi:10.1029/2007JC0043257. ; Comiso, J. C., D. Cavalieri, C. Parkinson, and P. Gloersen. 1997. Passive Microwave Algorithms for Sea Ice Concentrations: A Comparison of Two Techniques. Remote Sensing of the Environment 60(3):357-84. ; Comiso, J. C. 1984. Characteristics of Winter Sea Ice from Satellite Multispectral Microwave Observations. Journal of Geophysical Research 91(C1):975-94. ; Cavalieri, D. J., P. Gloersen, and W. J. Campbell. 1984. Determination of Sea Ice Parameters with the NIMBUS-7 SMMR. Journal of Geophysical Research 89(D4):5355-5369. ; Cavalieri, D. J., C. l. Parkinson, P. Gloersen, J. C. Comiso, and H. J. Zwally. 1999. Deriving Long-term Time Series of Sea Ice Cover from Satellite Passive-Microwave Multisensor Data Sets. Journal of Geophysical Research 104(7): 15,803-15,814 ; Comiso, J.C., R.A. Gersten, L.V. Stock, J. Turner, G.J. Perez, and K. Cho. 2017. Positive Trend in the Antarctic Sea Ice Cover and Associated Changes in Surface Temperature. J. Climate, 30, 2251?2267, doi:10.1175/JCLI-D-16-0408.1";
    String sensor "SSMIS > Special Sensor Microwave Imager/Sounder";
    String software_version_id "git@github.com:nsidc/seaice_ecdr.git@2daa616041a5ae87ffbdab3a590e51cf3a861609";
    String source "Generated from https://nsidc.org/data/nsidc-0080";
    String sourceUrl "(local files)";
    String spatial_resolution "25km";
    String standard_name_vocabulary "CF Standard Name Table (v83, 17 October 2023)";
    String summary "This data set provides a near-real-time (NRT) passive microwave sea ice concentration climate data record (CDR) based on gridded brightness temperatures (TBs) from the Defense Meteorological Satellite Program (DMSP) passive microwave radiometer: the Special Sensor Microwave Imager/Sounder (SSMIS) F17. The sea ice concentration CDR is an estimate of sea ice concentration that is produced by combining concentration estimates from two algorithms developed at the NASA Goddard Space Flight Center (GSFC): the NASA Team algorithm and the Bootstrap algorithm. The individual algorithms are used to process and combine brightness temperature data at NSIDC. This product is designed to provide an NRT time series of sea ice concentrations (the fraction, or percentage, of ocean area covered by sea ice). The data are gridded on the NSIDC polar stereographic grid with 25 x 25 km grid cells and are available in NetCDF file format. Each file contains a variable with the CDR concentration values as well as variables that hold the NASA Team and Bootstrap processed concentrations for reference. Variables containing standard deviation, quality flags, and projection information are also included.";
    String testOutOfDate "now-5days";
    String time_coverage_duration "P1D";
    String time_coverage_end "2026-02-22T00:00:00Z";
    String time_coverage_resolution "P1D";
    String time_coverage_start "2024-07-01T00:00:00Z";
    String title "Sea Ice Concentration, NOAA/NSIDC NRT Climate Data Record V3, Northern Hemisphere, 25km, Near Real-Time, 2024-Present, Daily";
  }
}
