import os
import pytest
import numpy as np
import lsst.afw.image as afw_image
import lsst.afw.geom as afw_geom

from descwl_shear_sims.galaxies import make_galaxy_catalog, DEFAULT_FIXED_GAL_CONFIG
from descwl_shear_sims.stars import StarCatalog, make_star_catalog
from descwl_shear_sims.psfs import make_fixed_psf, make_ps_psf

from descwl_shear_sims.sim import make_sim, get_se_dim
from descwl_shear_sims.constants import ZERO_POINT


@pytest.mark.parametrize('dither,rotate', [
    (False, False),
    (False, True),
    (True, False),
    (True, True),
])
def test_sim_smoke(dither, rotate):
    """
    test sim can run
    """
    seed = 74321
    rng = np.random.RandomState(seed)

    coadd_dim = 351
    psf_dim = 51
    bands = ["i"]
    galaxy_catalog = make_galaxy_catalog(
        rng=rng,
        gal_type="fixed",
        coadd_dim=coadd_dim,
        buff=30,
        layout="grid",
    )

    psf = make_fixed_psf(psf_type="gauss")
    data = make_sim(
        rng=rng,
        galaxy_catalog=galaxy_catalog,
        coadd_dim=coadd_dim,
        psf_dim=psf_dim,
        bands=bands,
        g1=0.02,
        g2=0.00,
        psf=psf,
        dither=dither,
        rotate=rotate,
    )

    for key in ['band_data', 'coadd_wcs', 'psf_dims', 'coadd_bbox']:
        assert key in data

    assert isinstance(data['coadd_wcs'], afw_geom.SkyWcs)
    assert data['psf_dims'] == (psf_dim, )*2
    extent = data['coadd_bbox'].getDimensions()
    edims = (extent.getX(), extent.getY())
    assert edims == (coadd_dim, )*2

    for band in bands:
        assert band in data['band_data']

    for band, bdata in data['band_data'].items():
        assert len(bdata) == 1
        assert isinstance(bdata[0], afw_image.ExposureF)


def test_sim_se_dim():
    """
    test sim can run
    """
    seed = 74321
    rng = np.random.RandomState(seed)

    coadd_dim = 351
    se_dim = 351
    psf_dim = 51
    bands = ["i"]
    galaxy_catalog = make_galaxy_catalog(
        rng=rng,
        gal_type="fixed",
        coadd_dim=coadd_dim,
        buff=30,
        layout="grid",
    )

    psf = make_fixed_psf(psf_type="gauss")
    data = make_sim(
        rng=rng,
        galaxy_catalog=galaxy_catalog,
        coadd_dim=coadd_dim,
        se_dim=se_dim,
        psf_dim=psf_dim,
        bands=bands,
        g1=0.02,
        g2=0.00,
        psf=psf,
    )

    dims = (se_dim, )*2
    assert data['band_data']['i'][0].image.array.shape == dims


@pytest.mark.parametrize("rotate", [False, True])
def test_sim_exp_mag(rotate, show=False):
    """
    test we get the right mag.  Also test we get small flux when we rotate and
    there is nothing at the sub image location we choose

    This requires getting lucky with the rotation, so try a few
    """

    ntrial = 10

    bands = ["i"]
    seed = 55
    coadd_dim = 301
    rng = np.random.RandomState(seed)

    # use fixed single epoch dim so we can look in the same spot for the object
    se_dim = get_se_dim(coadd_dim=coadd_dim, dither=False, rotate=True)

    ok = False
    for i in range(ntrial):
        galaxy_catalog = make_galaxy_catalog(
            rng=rng,
            gal_type="fixed",
            coadd_dim=coadd_dim,
            buff=30,
            layout="grid",
        )

        psf = make_fixed_psf(psf_type="gauss")
        sim_data = make_sim(
            rng=rng,
            galaxy_catalog=galaxy_catalog,
            coadd_dim=coadd_dim,
            se_dim=se_dim,
            g1=0.02,
            g2=0.00,
            psf=psf,
            bands=bands,
            rotate=rotate,
        )

        image = sim_data["band_data"]["i"][0].image.array
        sub_image = image[93:93+25, 88:88+25]
        subim_sum = sub_image.sum()

        if show:
            import matplotlib.pyplot as mplt
            fig, ax = mplt.subplots(nrows=1, ncols=2)
            ax[0].imshow(image)
            ax[1].imshow(sub_image)
            mplt.show()

        if rotate:
            # we expect nothing there
            if abs(subim_sum) < 30:
                ok = True
                break

        else:
            # we expect something there with about the right magnitude
            mag = ZERO_POINT - 2.5*np.log10(subim_sum)
            assert abs(mag - DEFAULT_FIXED_GAL_CONFIG['mag']) < 0.005

            break

    if rotate:
        assert ok, 'expected at least one to be empty upon rotation'


@pytest.mark.parametrize("psf_type", ["gauss", "moffat", "ps"])
def test_sim_psf_type(psf_type):

    seed = 431
    rng = np.random.RandomState(seed)

    dither = True
    rotate = True
    coadd_dim = 101
    galaxy_catalog = make_galaxy_catalog(
        rng=rng,
        gal_type="fixed",
        coadd_dim=coadd_dim,
        buff=5,
        layout="grid",
    )

    if psf_type == "ps":
        se_dim = get_se_dim(coadd_dim=coadd_dim, dither=dither, rotate=rotate)
        psf = make_ps_psf(rng=rng, dim=se_dim)
    else:
        psf = make_fixed_psf(psf_type=psf_type)

    _ = make_sim(
        rng=rng,
        galaxy_catalog=galaxy_catalog,
        coadd_dim=coadd_dim,
        g1=0.02,
        g2=0.00,
        psf=psf,
        dither=dither,
        rotate=rotate,
    )


@pytest.mark.parametrize('epochs_per_band', [1, 2, 3])
def test_sim_epochs(epochs_per_band):

    seed = 7421
    bands = ["r", "i", "z"]
    coadd_dim = 301
    psf_dim = 47

    rng = np.random.RandomState(seed)

    galaxy_catalog = make_galaxy_catalog(
        rng=rng,
        gal_type="fixed",
        coadd_dim=coadd_dim,
        buff=10,
        layout="grid",
    )

    psf = make_fixed_psf(psf_type="gauss")
    sim_data = make_sim(
        rng=rng,
        galaxy_catalog=galaxy_catalog,
        coadd_dim=coadd_dim,
        psf_dim=psf_dim,
        g1=0.02,
        g2=0.00,
        psf=psf,
        bands=bands,
        epochs_per_band=epochs_per_band,
    )

    band_data = sim_data['band_data']
    for band in bands:
        assert band in band_data
        assert len(band_data[band]) == epochs_per_band


@pytest.mark.parametrize("layout", ("grid", "random", "random_disk", "hex"))
def test_sim_layout(layout):
    seed = 7421
    coadd_dim = 201
    rng = np.random.RandomState(seed)

    galaxy_catalog = make_galaxy_catalog(
        rng=rng,
        gal_type="fixed",
        coadd_dim=coadd_dim,
        buff=30,
        layout=layout,
    )

    psf = make_fixed_psf(psf_type="gauss")
    _ = make_sim(
        rng=rng,
        galaxy_catalog=galaxy_catalog,
        coadd_dim=coadd_dim,
        g1=0.02,
        g2=0.00,
        psf=psf,
    )


@pytest.mark.parametrize(
    "cosmic_rays, bad_columns",
    [(True, True),
     (True, False),
     (False, True),
     (True, True)],
)
def test_sim_defects(cosmic_rays, bad_columns):
    ntrial = 10
    seed = 7421
    rng = np.random.RandomState(seed)

    coadd_dim = 201

    galaxy_catalog = make_galaxy_catalog(
        rng=rng,
        gal_type="fixed",
        coadd_dim=coadd_dim,
        layout="grid",
        buff=30,
    )

    psf = make_fixed_psf(psf_type="gauss")

    for itrial in range(ntrial):
        sim_data = make_sim(
            rng=rng,
            galaxy_catalog=galaxy_catalog,
            coadd_dim=coadd_dim,
            g1=0.02,
            g2=0.00,
            psf=psf,
            cosmic_rays=cosmic_rays,
            bad_columns=bad_columns,
        )

        for band, band_exps in sim_data['band_data'].items():
            for exp in band_exps:
                image = exp.image.array
                mask = exp.mask.array
                flags = exp.mask.getPlaneBitMask(('CR', 'BAD'))

                if bad_columns or cosmic_rays:

                    wnan = np.where(np.isnan(image))
                    wflagged = np.where((mask & flags) != 0)
                    assert wnan[0].size == wflagged[0].size


@pytest.mark.skipif(
    "CATSIM_DIR" not in os.environ,
    reason='simulation input data is not present',
)
def test_sim_wldeblend():
    seed = 7421
    coadd_dim = 201
    rng = np.random.RandomState(seed)

    galaxy_catalog = make_galaxy_catalog(
        rng=rng,
        gal_type="wldeblend",
        coadd_dim=coadd_dim,
        buff=30,
        layout="random",
    )

    psf = make_fixed_psf(psf_type="moffat")
    _ = make_sim(
        rng=rng,
        galaxy_catalog=galaxy_catalog,
        coadd_dim=coadd_dim,
        g1=0.02,
        g2=0.00,
        psf=psf,
    )


@pytest.mark.skipif(
    "CATSIM_DIR" not in os.environ,
    reason='simulation input data is not present',
)
@pytest.mark.parametrize('density,min_density,max_density', [
    (None, 40, 100),
    (20, None, None),
])
def test_sim_stars(density, min_density, max_density):
    seed = 7421
    coadd_dim = 201
    buff = 30

    config = {
        'density': density,
        'min_density': min_density,
        'max_density': max_density,
    }
    for use_maker in (False, True):
        rng = np.random.RandomState(seed)

        galaxy_catalog = make_galaxy_catalog(
            rng=rng,
            gal_type="wldeblend",
            coadd_dim=coadd_dim,
            buff=buff,
            layout="random",
        )
        assert len(galaxy_catalog) == galaxy_catalog.shifts_array.size

        if use_maker:
            star_catalog = make_star_catalog(
                rng=rng,
                coadd_dim=coadd_dim,
                buff=buff,
                star_config=config,
            )

        else:
            star_catalog = StarCatalog(
                rng=rng,
                coadd_dim=coadd_dim,
                buff=buff,
                density=config['density'],
                min_density=config['min_density'],
                max_density=config['max_density'],
            )

        assert len(star_catalog) == star_catalog.shifts_array.size

        psf = make_fixed_psf(psf_type="moffat")

        # tests that we actually get bright objects set are in
        # test_star_masks_and_bleeds

        data = make_sim(
            rng=rng,
            galaxy_catalog=galaxy_catalog,
            star_catalog=star_catalog,
            coadd_dim=coadd_dim,
            g1=0.02,
            g2=0.00,
            psf=psf,
        )

        if not use_maker:
            data_nomaker = data
        else:
            assert np.all(
                data['band_data']['i'][0].image.array ==
                data_nomaker['band_data']['i'][0].image.array
            )


@pytest.mark.skipif(
    "CATSIM_DIR" not in os.environ,
    reason='simulation input data is not present',
)
def test_sim_star_bleeds():
    seed = 7421
    coadd_dim = 201
    buff = 30
    rng = np.random.RandomState(seed)

    galaxy_catalog = make_galaxy_catalog(
        rng=rng,
        gal_type="wldeblend",
        coadd_dim=coadd_dim,
        buff=buff,
        layout="random",
    )

    star_catalog = StarCatalog(
        rng=rng,
        coadd_dim=coadd_dim,
        buff=buff,
        density=100,
    )

    psf = make_fixed_psf(psf_type="moffat")

    # tests that we actually get saturation are in test_star_masks_and_bleeds

    _ = make_sim(
        rng=rng,
        galaxy_catalog=galaxy_catalog,
        star_catalog=star_catalog,
        coadd_dim=coadd_dim,
        g1=0.02,
        g2=0.00,
        psf=psf,
        star_bleeds=True,
    )


@pytest.mark.parametrize("draw_method", (None, "auto", "phot"))
def test_sim_draw_method_smoke(draw_method):
    seed = 881
    coadd_dim = 201
    rng = np.random.RandomState(seed)

    galaxy_catalog = make_galaxy_catalog(
        rng=rng,
        gal_type="fixed",
        coadd_dim=coadd_dim,
        buff=30,
        layout='grid',
    )

    kw = {}
    if draw_method is not None:
        kw['draw_method'] = draw_method

    psf = make_fixed_psf(psf_type="gauss")
    _ = make_sim(
        rng=rng,
        galaxy_catalog=galaxy_catalog,
        coadd_dim=coadd_dim,
        g1=0.02,
        g2=0.00,
        psf=psf,
        **kw
    )


if __name__ == '__main__':
    for rotate in (False, True):
        test_sim_exp_mag(rotate, show=True)
