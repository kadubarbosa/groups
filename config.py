# -*- coding: utf-8 -*-
"""
Created on Thu Mar 20 17:24:25 2014

@author: kadu

Configuration file for the work in the groups of galaxies for my PhD work.
"""

home = "/home/kadu/Dropbox/groups"
templates_dir = home + "/MILES"
data_dir = home + "/data/candidates"
tables_dir = home + "/tables"
plots_dir = home + "/plots"


# Constants
c = 299792.458 # Speed of light in km/s
FWHM_tem = 3.6 # MILES library spectra have a resolution FWHM of 2.54A.
FWHM_spec = 3.6 # FWHM of data

# Resolution for binning with pPXF
velscale = 20. # km/s

# Velocities of the groups according to NED
v0s = dict([("hcg22", 2698.), ("hcg62", 4413.), ("hcg90", 2638.),
            ("hcg42", 3987.), ("ngc193", 4400.), ("ngc7619", 3439.)])

H_0 = 67.8

# Galactocentric distances in Mpc
distances = dict([("hcg22", 37.5), ("hcg62", 61.1), ("hcg90", 37.9),
            ("hcg42", 53.7), ("ngc193", 63.8), ("ngc7619", 50.9)])
disterr = dict([("hcg22", 0.7), ("hcg62", 1.3), ("hcg90", 0.7),
            ("hcg42", 1.), ("ngc193", 1.2), ("ngc7619", 0.9)])

# Defining systems
groups = ["hcg22", "hcg42", "hcg62", "hcg90", "ngc193", "ngc7619"]
rac = ["03h03m31.3s", "10h00m21.8s", "12h53m05.5s", "22h02m05.6s",
       "00h39m16.4s", "23h19m42.9s"]
decc = ["-15d40m32s", "-19d38m57s", "-09d12m01s", "-31d58m00s", "+03d17m04s",
       "+08d09m45s"]

# Defining observing runs
nights = ["blanco10n1", "blanco10n2", "blanco11an1", "blanco11an2",
          "blanco11bn1", "blanco11bn2", "blanco11bn3"]
obsrun = {"blanco10n1" : 1, "blanco10n2" : 2, "blanco11an1" : 3,
          "blanco11an2" : 4, "blanco11bn1" : 5, "blanco11bn2" : 6,
          "blanco11bn3" : 7 }
