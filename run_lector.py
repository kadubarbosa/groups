# -*- coding: utf-8 -*-
"""
Created on Mon March 2 2016

@author: cbarbosa

Calculate the Lick indices in the groups data
"""

import os

import numpy as np
import pyfits as pf
from scipy.interpolate import NearestNDInterpolator as interpolator
from scipy.interpolate import interp1d
from scipy.stats import sigmaclip
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from astropy.stats import sigma_clip

from config import *
import lector as lector
from run_ppxf import pPXF, ppload, wavelength_array, losvd_convolve

def check_intervals(setupfile, bands, vel):
    """ Check which indices are defined in the spectrum. """
    c = 299792.458 # speed of light in km/s
    with open(setupfile) as f:
        lines = [x for x in f.readlines()]
    lines = [x for x in lines if x.strip()]
    intervals = np.array(lines[5:]).astype(float)
    intervals = intervals.reshape((len(intervals)/2, 2))
    bands = np.loadtxt(bands, usecols=(2,7))
    bands *= np.sqrt((1 + vel/c)/(1 - vel/c))
    goodbands = np.zeros(len(bands))
    for i, (b1, b2) in enumerate(bands):
        for (i1, i2) in intervals:
            if i1 < b1 and b2 < i2:
                goodbands[i] = 1
    return np.where(goodbands == 1, 1, np.nan)

class BroadCorr:
    """ Wrapper for the interpolated model."""
    def __init__(self, table): 
        self.interpolate(table)
    
    def interpolate(self, table):
        sigmas = np.loadtxt(table, dtype=np.double, usecols=(0,))
        inds = np.loadtxt(table, dtype=np.double, usecols=np.arange(1,51, 2)).T
        corrs = np.loadtxt(table, dtype=np.double,usecols=np.arange(2,51, 2)).T
        self.fs = []
        self.indlims = []
        for i, (idx, corr) in enumerate(zip(inds, corrs)):
            f = interpolator(np.column_stack((sigmas, idx)), corr)
            self.fs.append(f)
            self.indlims.append([idx.min(), idx.max()])
        self.siglims = [sigmas.min(), sigmas.max()]
        return
        
    def __call__(self, sigma, lick): 
        b = np.zeros(len(lick))
        for i,l in enumerate(lick):
            if np.isnan(l):
                b[i] = 0.
            else:
                b[i] = self.fs[i](sigma, l)
        return b

class Vdisp_corr_k04():
    """ Correction for LOSVD only for multiplicative indices from
        Kuntschner 2004."""
    def __init__(self):
        """ Load tables. """
        table = os.path.join(tables_dir, "kuntschner2004.tab")
        bands = os.path.join(tables_dir, "BANDS")
        self.indices_k04 = np.loadtxt(table, usecols=(1,), dtype=str).tolist()
        self.type_k04 = np.loadtxt(table, usecols=(2,),
                                            dtype=str).tolist()
        self.coeff_k04 = np.loadtxt(table, usecols=np.arange(3,10))
        self.lick_indices = np.loadtxt(bands, usecols=(0,), dtype=str)
        self.lick_types = np.loadtxt(bands, usecols=(8,))

    def __call__(self, lick, sigma, h3=0., h4=0.):
        newlick = np.zeros(25)
        for i,index in enumerate(lick_indices):
            if index in self.indices_k04:
                idx = self.indices_k04.index(index)
                a1, a2, a3, b1, b2, c1, c2 = self.coeff_k04[idx]
                if self.type_k04[idx] == "m":
                    C_k04 = 1. + a1 * sigma + a2 * sigma**2 + \
                            a3 * sigma**3 + b1 * sigma * h3 + \
                            b2 * sigma**2 * h3 + \
                            c1 * sigma * h4 + c2 * sigma**2 * h4
                    newlick[i] = C_k04 * lick[i]
                else:
                    C_k04 = a1 * sigma    + a2 * sigma**2 + \
                            a3 * sigma**3 + b1 * sigma * h3 + \
                            b2 * sigma**2 * h3 + \
                            c1 * sigma * h4 + c2 * sigma**2 * h4
                    newlick[i] = lick[i] + C_k04
            else:
                newlick[i] = lick[i]
        return newlick

def make_table(fields, targetSN, ltype="corr"):
    """ Gather information of Lick indices of a given target SN in a single
    table. """
    for field in fields:
        os.chdir(os.path.join(data_dir, "combined_{0}".format(field),
                              "logs_sn{0}".format(targetSN)))
        logfiles = sorted([x for x in os.listdir(".") if x.startswith("lick")
                           and x.endswith("{0}.txt".format(ltype))])
        table = []
        for logfile in logfiles:
            with open(logfile) as f:
                line = f.readline()
            table.append(line)
        output = os.path.join(data_dir, "combined_{0}".format(field),
                              "lick_{0}_sn{1}.txt".format(ltype, targetSN))
        with open(output, "w") as f:
            f.write("".join(table))

def lick_standards_table():
    """ Prepare a table with the Lick indices of the standard stars"""
    folder = os.path.join(home, "data/standards")
    fits = []
    for night in nights:
        fits += os.listdir(os.path.join(folder, night))
    stars = [x.split(".")[0].lower() for x in fits]
    stars = [x.upper() for x in stars if x.startswith("hr") or
             x.startswith("hd")]
    stars = list(set([x.replace("HD0", "HD") for x in stars]))
    stars = list(set([x.replace("HR0", "HR") for x in stars]))
    table = os.path.join(tables_dir, "lick_standards.dat")
    with open(table) as f:
        header = f.readline()
        data = f.readlines()
    cols = np.hstack((np.arange(39,240,8), np.array([249, 257, 265])))
    lick = np.zeros((len(data), cols.size - 1))
    for i in range(cols.size - 1):
        d = [x[cols[i]:cols[i+1]].strip() for x in data]
        d = np.array([x if x else np.nan for x in d])
        lick[:, i] = d
    hd = ["HD" + x[:9].replace(" ", "") for x in data]
    hd = [x.replace("HD0", "HD") for x in hd]
    hr = [x[9:19].replace(" ", "") for x in data]
    table = []
    for star in stars:
        if star in hr:
            idx = hr.index(star)
        elif star in hd:
            idx = hd.index(star)
        else:
            continue
        l = ["{0:.5f}".format(x) for x in lick[idx]]
        l = ["{0:14s}".format(x) for x in l]
        table.append("{0:15s}".format(star) + "".join(l))
    with open(os.path.join(tables_dir, "lick_standards.txt"), "w") as f:
        f.write(header + "\n")
        f.write("\n".join(table))

def run_standard_stars(velscale, bands):
    """ Run lector on standard stars to study instrumental dependencies. """
    stars_dir = os.path.join(home, "data/standards")
    table = os.path.join(tables_dir, "lick_standards.txt")
    ids = np.loadtxt(table, usecols=(0,), dtype=str).tolist()
    lick_ref = np.loadtxt(table, usecols=np.arange(1,26))
    ref, obsm, obsa = [], [], []
    res = hydra_resolution()
    for night in nights:
        os.chdir(os.path.join(stars_dir, night))
        stars = [x for x in os.listdir(".") if x.endswith(".fits")]
        for star in stars:
            ppfile = "logs/{0}".format(star.replace(".fits", ""))
            if not os.path.exists(ppfile + ".pkl"):
                continue
            name = star.split(".")[0].upper()
            if name not in ids:
                continue
            print name
            idx = ids.index(name)
            lick_star = lick_ref[idx]
            pp = ppload("logs/{0}".format(star.replace(".fits", "")))
            pp = pPXF(star, velscale, pp)
            mpoly = np.interp(pp.wtemp, pp.w, pp.mpoly)
            spec = pf.getdata(star)
            w = wavelength_array(star, axis=1, extension=0)
            best_unbroad_v0 = mpoly * pp.star.dot(pp.w_ssps)
            best_broad_v0 = losvd_convolve(best_unbroad_v0,
                                           np.array([0., pp.sol[1]]), velscale)
            ##################################################################
            # Interpolate bestfit templates to obtain linear dispersion
            b0 = interp1d(pp.wtemp, best_unbroad_v0, kind="linear",
                          fill_value="extrapolate", bounds_error=False)
            b1 = interp1d(pp.wtemp, best_broad_v0, kind="linear",
                          fill_value="extrapolate", bounds_error=False)
            best_unbroad_v0 = b0(w)
            best_broad_v0 = b1(w)
            #################################################################
            # Broadening to Lick system
            spec = lector.broad2lick(w, spec, res(w), vel=pp.sol[0])
            best_unbroad_v0 = lector.broad2lick(w, best_unbroad_v0,
                                                3.6, vel=0.)
            best_broad_v0 = lector.broad2lick(w, best_broad_v0, 3.6,
                                              vel=0.)
            # plt.plot(w, spec, "-k")
            # plt.plot(w, best_broad_v0, "-r")
            # plt.show()
            ##################################################################
            lick, lickerr = lector.lector(w, spec, np.ones_like(w), bands,
                                          vel=pp.sol[0])
            lick_unb, tmp = lector.lector(w, best_unbroad_v0,
                             np.ones_like(w), bands, vel=0.)
            lick_br, tmp = lector.lector(w, best_broad_v0,
                             np.ones_like(w), bands, vel=0.)
            lickm = multi_corr(lick, lick_unb, lick_br)
            licka = add_corr(lick, lick_unb, lick_br)
            ref.append(lick_star)
            obsm.append(lickm)
            obsa.append(licka)
    with open(os.path.join(tables_dir, "stars_lick_val_corr.txt"), "w") as f:
        np.savetxt(f, np.array(ref))
    with open(os.path.join(tables_dir, "stars_lick_obs_mcorr.txt"), "w") as f:
        np.savetxt(f, np.array(obsm))
    with open(os.path.join(tables_dir, "stars_lick_obs_acorr.txt"), "w") as f:
        np.savetxt(f, np.array(obsa))
    return

def add_corr(lick, unbroad, broad):
    return lick + unbroad - broad

def multi_corr(lick, unbroad, broad):
    return lick * (unbroad / broad)

def plot_standard(corr="acorr"):
    os.chdir(tables_dir)
    ref = np.loadtxt("stars_lick_val_{0}.txt".format(corr)).T
    obs = np.loadtxt("stars_lick_obs_{0}.txt".format(corr)).T
    bands = np.loadtxt("bands_matching_standards.txt", usecols=(0), dtype=str).tolist()
    bands2, units, error = np.loadtxt("bands.txt", usecols=(0,9,10), dtype=str).T
    idx = [list(bands2).index(x) for x in bands]
    idx2 = np.array([list(bands).index(x) for x in bands2])
    error = error[idx]
    units = units[idx]
    units = [x.replace("Ang", "\AA") for x in units]
    fig = plt.figure(1, figsize=(20,12))
    gs = GridSpec(5,5)
    gs.update(left=0.03, right=0.988, top=0.98, bottom=0.06, wspace=0.2,
              hspace=0.4)
    offsets, errs = [], []
    for i in range(25):
        ax = plt.subplot(gs[i])
        plt.locator_params(axis="y", nbins=6)
        plt.locator_params(axis="x", nbins=6)
        ax.minorticks_on()
        # ax.plot(obs[i], ref[i] - obs[i], "ok")
        ax.axhline(y=0, ls="--", c="k")
        diff = ref[i] - obs[i]
        diff, c1, c2 = sigmaclip(diff[np.isfinite(diff)], 2.5, 2.5)
        ax.hist(diff, bins=8, color="0.7", histtype='stepfilled')
        ylim = plt.ylim()
        xlim = plt.xlim()
        xlim = np.max(np.abs(xlim))
        ax.set_ylim(0, ylim[1] + 2)
        ax.set_xlim(-xlim, xlim)
        mean = np.nanmean(diff)
        N = len(diff)
        err = np.nanstd(diff) / np.sqrt(N)
        lab = "${0:.2f}\pm{1:.2f}$".format(mean, err)
        ax.axvline(x=mean, ls="-", c="r", label=lab)
        ax.axvline(x=0, ls="--", c="k")
        # ax.axhline(y=float(error[i]))
        # ax.axhline(y=-float(error[i]))
        # ax.set_xlabel("{0} ({1})".format(bands[i].replace("_", " "), units[i]))
        ax.legend(loc=1,prop={'size':12})
        ax.set_xlabel("$\Delta$ {0} ({1})".format(bands[i].replace("_", " "),
                                                  units[i]))
        ax.set_ylabel("Frequency")
        offsets.append(mean)
        errs.append(err)
    offsets = np.array(offsets)[idx2]
    errs = np.array(errs)[idx2]
    output = os.path.join(home, "plots/lick_stars_{0}.png".format(corr))
    plt.savefig(output)
    with open(os.path.join(tables_dir, "lick_offsets.txt"), "w") as f:
        f.write("# Index Additive Correction\n")
        np.savetxt(f, np.column_stack((np.array(bands)[idx2],offsets, errs)),
                   fmt="%s")

def mad(a):
    return 1.48 * np.nanmedian(np.abs(a - np.nanmedian(a)))

def test_lector():
    os.chdir(os.path.join(home, "MILES"))
    bands = os.path.join(tables_dir, "bands.txt")
    filename = "lector_tmputH9bu.list_LINE"
    stars = np.loadtxt(filename, usecols=(0,),
                       dtype=str)
    ref = np.loadtxt(filename,
             usecols=(2,3,4,5,6,7,8,9,14,15,16,17,18,24,25,26,
                      27,28,29,30,31,32,33,34,35))
    obs = []
    from lick import Lick
    for i, star in enumerate(stars):
        print star + ".fits"
        spec = pf.getdata(star + ".fits")
        h = pf.getheader(star + ".fits")
        w = h["CRVAL1"] + h["CDELT1"] * \
                            (np.arange(h["NAXIS1"]) + 1 - h["CRPIX1"])
        lick, tmp = lector.lector(w, spec, np.ones_like(w), bands,
                                  interp_kind="linear")
        ll = Lick(w, spec, np.loadtxt(bands, usecols=(2,3,4,5,6,7,)))
        obs.append(ll.classic)
    obs = np.array(obs)
    fig = plt.figure(1, figsize=(20,12))
    gs = GridSpec(5,5)
    gs.update(left=0.08, right=0.98, top=0.98, bottom=0.06, wspace=0.25,
              hspace=0.4)
    obs = obs.T
    ref = ref.T
    names = np.loadtxt(bands, usecols=(0,), dtype=str)
    units = np.loadtxt(bands, usecols=(9,), dtype=str).tolist()
    # units = [x.replace("Ang", "\AA") for x in units]
    for i in range(25):
        ax = plt.subplot(gs[i])
        plt.locator_params(axis="x", nbins=6)
        ax.minorticks_on()
        ax.plot(obs[i], (obs[i] - ref[i]) / ref[i], "o", color="0.5")
        ax.axhline(y=0, ls="--", c="k")
        lab = "median $= {0:.3f}$".format(
            np.nanmedian(obs[i] - ref[i])).replace("-0.00", "0.00")
        ax.axhline(y=np.nanmedian(obs[i] - ref[i]), ls="--", c="r", label=lab)
        ax.set_xlabel("{0} ({1})".format(names[i].replace("_", " "), units[i]))
        ax.legend(loc=1,prop={'size':15})
        ax.set_ylim(-0.01, 0.01)
    fig.text(0.02, 0.5, 'I$_{{\\rm pylector}}$ - I$_{{\\rm lector}}$', va='center',
             rotation='vertical', size=40)
    output = os.path.join(home, "plots/test_lector.png")
    plt.show()
    plt.savefig(output)

def hydra_resolution():
    """ Returns the wavelength-dependent resolution of the Hydra spectrograph.
    """
    filename = os.path.join(tables_dir, "wave_fwhm_standards.dat")
    wave, fwhm = np.loadtxt(filename).T
    return interp1d(wave, fwhm, kind="linear", bounds_error=False,
                    fill_value="extrapolate")

def run_candidates(velscale, bands):
    """ Run lector on candidates. """
    wdir = os.path.join(home, "data/candidates")
    os.chdir(wdir)
    specs = sorted([x for x in os.listdir(wdir) if x.endswith(".fits")])
    obsres = hydra_resolution()
    offset, offerr = lick_offset()
    lickout = []
    for spec in specs:
        ppfile = "logs_ssps/{0}".format(spec.replace(".fits", ""))
        if not os.path.exists(ppfile + ".pkl"):
            print "Skiping spectrum: ", spec
            continue
        print ppfile
        pp = ppload("logs_ssps/{0}".format(spec.replace(".fits", "")))
        pp = pPXF(spec, velscale, pp)
        galaxy = pf.getdata(spec)
        w = wavelength_array(spec, axis=1, extension=0)
        if pp.ncomp > 1:
            sol = pp.sol[0]
        else:
            sol = pp.sol
        if pp.ncomp == 1:
            csp = pp.star.dot(pp.w_ssps) # composite stellar population
        else:
            csp = pp.star[:,:-pp.ngas].dot(pp.w_ssps)
        ######################################################################
        # Produce bestfit templates convolved with LOSVD/redshifted
        best_unbroad = pp.poly + pp.mpoly * losvd_convolve(csp,
                       np.array([sol[0], velscale/10.]), velscale)
        best_broad = pp.poly + pp.mpoly * losvd_convolve(csp,
                     sol, velscale)
        ##################################################################
        # Interpolate bestfit templates to obtain linear dispersion
        b0 = interp1d(pp.w, best_unbroad, kind="linear",
                      fill_value="extrapolate", bounds_error=False)
        b1 = interp1d(pp.w, best_broad, kind="linear",
                      fill_value="extrapolate", bounds_error=False)
        sky = interp1d(pp.w, pp.bestsky, kind="linear",
                      fill_value="extrapolate", bounds_error=False)
        emission = interp1d(pp.w, pp.gas, kind="linear",
                      fill_value="extrapolate", bounds_error=False)
        best_unbroad = b0(w)
        best_broad = b1(w)
        ######################################################################
        # Test plot
        # plt.plot(w, best_unbroad, "-b")
        # plt.plot(w, best_broad, "-r")
        # plt.plot(w, galaxy - sky(w), "-k")
        # plt.show()
        #######################################################################
        # Broadening to Lick system
        galaxy = lector.broad2lick(w, galaxy - sky(w) - emission(w), obsres(w),
                                   vel=sol[0])
        best_unbroad = lector.broad2lick(w, best_unbroad,
                                            3.7, vel=sol[0])
        best_broad = lector.broad2lick(w, best_broad, 3.7,
                                          vel=sol[0])
        ##################################################################
        lick, lickerr = lector.lector(w, galaxy, np.ones_like(w), bands,
                                      vel=sol[0])
        lick_unb, tmp = lector.lector(w, best_unbroad,
                         np.ones_like(w), bands, vel=sol[0])
        lick_br, tmp = lector.lector(w, best_broad,
                         np.ones_like(w), bands, vel=sol[0])
        lickc = correct_lick(bands, lick, lick_unb, lick_br) + offset
        ######################################################################
        # Plot to check if corrections make sense
        if False:
            fig = plt.figure(1)
            ax = plt.subplot(111)
            ax.plot(lick, "ok")
            ax.plot(lick_unb, "xb")
            ax.plot(lick_br, "xr")
            ax.plot(lick - (lick_br - lick_unb), "+k", ms=10)
            ax.plot(lick * lick_unb / lick_br, "xk", ms=10)
            ax.plot(lickc - offset, "o", c="none", markersize=10, mec="y")
            ax.set_xticks(np.arange(25))
            ax.set_xlim(-1, 25)
            labels = np.loadtxt(bands, usecols=(0,), dtype=str).tolist()
            labels = [x.replace("_", " ") for x in labels]
            ax.set_xticklabels(labels, rotation=90)
            plt.show()
        ######################################################################
        # Storing results
        lickc = ["{0:.5g}".format(x) for x in lickc]
        line = "".join(["{0:30s}".format(spec)] + \
                       ["{0:12s}".format(x) for x in lickc])
        lickout.append(line)
        ######################################################################
    # Saving to file
    with open("lick.txt", "w") as f:
        f.write("\n".join(lickout))


def correct_lick(bands, lick, unbroad, broad):
    """ Make corrections for the broadening in the spectra."""
    types = np.loadtxt(bands, usecols=(8,))
    corrected = lick + unbroad - broad
    idx = np.where(types==0)[0]
    corrected[idx] = lick[idx] * unbroad[idx] / broad[idx]
    return corrected

def lick_offset():
    filename = os.path.join(tables_dir, "lick_offsets.txt")
    corr, err = np.loadtxt(filename, usecols=(1,2,)).T
    return corr, err

def run_candidates_mc(velscale, bands, nsim=50):
    """ Run MC to calculate errors on Lick indices. """
    wdir = os.path.join(home, "data/candidates")
    os.chdir(wdir)
    specs = sorted([x for x in os.listdir(wdir) if x.endswith(".fits")])
    offset, offerr = lick_offset()
    lickout = []
    for spec in specs:
        try:
            ppfile = "logs_ssps/{0}".format(spec.replace(".fits", ""))
            if not os.path.exists(ppfile + ".pkl"):
                print "Skiping spectrum: ", spec
                continue
            print ppfile
            pp = ppload("logs_ssps/{0}".format(spec.replace(".fits", "")))
            pp = pPXF(spec, velscale, pp)
            ppkin = ppload("logs/{0}".format(spec.replace(".fits", "")))
            ppkin = pPXF(spec, velscale, ppkin)
            w = wavelength_array(spec, axis=1, extension=0)
            if pp.ncomp > 1:
                sol = ppkin.sol[0]
                error = ppkin.error[0]
            else:
                sol = ppkin.sol
                error = ppkin.error
            ###################################################################
            # Produces composite stellar population of reference
            if pp.ncomp == 1:
                csp = pp.star.dot(pp.w_ssps)
            else:
                csp = pp.star[:,:-pp.ngas].dot(pp.w_ssps)
            ###################################################################
            # Make unbroadened bestfit and measure Lick on it
            best_unbroad_ln = pp.poly + pp.mpoly * losvd_convolve(csp,
                           np.array([sol[0], velscale/10.]), velscale)
            b0 = interp1d(pp.w, best_unbroad_ln, kind="linear",
                          fill_value="extrapolate", bounds_error=False)
            best_unbroad_lin = b0(w)
            best_unbroad_lin = lector.broad2lick(w, best_unbroad_lin,
                                                3.6, vel=sol[0])
            lick_unb, tmp = lector.lector(w, best_unbroad_lin,
                             np.ones_like(w), bands, vel=sol[0])
            ###################################################################
            # Setup simulations
            vpert = np.random.normal(sol[0], error[0], nsim)
            sigpert = np.random.normal(sol[1], error[1], nsim)
            h3pert = np.random.normal(sol[2], error[2], nsim)
            h4pert = np.random.normal(sol[3], error[3], nsim)
            licksim = np.zeros((nsim, 25))
            ###################################################################
            for i, (v,s,h3,h4) in enumerate(zip(vpert, sigpert, h3pert, h4pert)):
                solpert = np.array([v,s,h3,h4])
                noise = np.random.normal(0., pp.noise, len(w))
                best_broad_ln = pp.poly + pp.mpoly * losvd_convolve(csp,
                         solpert, velscale)
                b1 = interp1d(pp.w, best_broad_ln, kind="linear",
                              fill_value="extrapolate", bounds_error=False)
                best_broad_lin = b1(w)
                ###############################################################
                # Broadening to Lick system
                best_broad_lin = lector.broad2lick(w, best_broad_lin, 3.6,
                                                   vel=solpert[0])
                lick_br, tmp = lector.lector(w, best_broad_lin,
                             np.ones_like(w), bands, vel=solpert[0])
                lick, lickerr = lector.lector(w, best_broad_lin + noise,
                            np.ones_like(w), bands, vel=sol[0])
                licksim[i] = correct_lick(bands, lick, lick_unb, lick_br) + \
                             offset
            stds = np.zeros(25)
            for i in range(25):
                stds[i] = np.std(sigma_clip(licksim[:,i], sigma=5))
            stds = np.sqrt(stds**2 + offerr**2)
            ###################################################################
            # Storing results
            lickc = ["{0:.5g}".format(x) for x in stds]

            line = "".join(["{0:35s}".format(spec)] + \
                           ["{0:12s}".format(x) for x in lickc])
            lickout.append(line)
            ###################################################################
        except:
            print "Problem with spectrum", spec
            continue
    # Saving to file
    with open("lickerr_mc{0}.txt".format(nsim), "w") as f:
        f.write("\n".join(lickout))



if __name__ == "__main__":
    test_lector()
    # run_standard_stars(velscale,
    #                    os.path.join(tables_dir, "bands_matching_standards.txt"))
    # plot_standard()
    # lick_standards_table()
    # run_candidates(velscale, os.path.join(tables_dir, "bands.txt"))
    # run_candidates_mc(velscale, os.path.join(tables_dir, "bands.txt"))