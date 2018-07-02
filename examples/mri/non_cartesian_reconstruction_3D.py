"""
Neuroimaging cartesian reconstruction
=====================================

Credit: S Lannuzel, L Elgueddari

In this tutorial we will reconstruct an MRI image from the sparse kspace
measurments.

Import neuroimaging data
------------------------

We use the toy datasets available in pysap, more specifically a 3D brain slice
and the acquistion cartesian scheme.
We also add some gaussian noise in the image space.
"""

# Package import
from pysap.data import get_sample_data
from pysap.plugins.mri.reconstruct_3D.fourier import NFFT3
from pysap.plugins.mri.reconstruct_3D.utils import imshow3D
from pysap.plugins.mri.parallel_mri.gradient import Gradient_pMRI
from pysap.plugins.mri.reconstruct_3D.linear import pyWavelet3
from pysap.plugins.mri.reconstruct.linear import Wavelet2
from pysap.plugins.mri.reconstruct_3D.utils import normalize_samples
from pysap.plugins.mri.parallel_mri.reconstruct import sparse_rec_fista
from pysap.plugins.mri.parallel_mri.reconstruct import sparse_rec_condatvu


# Third party import
import numpy as np
import matplotlib.pyplot as plt

# Load input data
Il = get_sample_data("3d-pmri")
Iref = np.squeeze(np.sqrt(np.sum(np.abs(Il)**2, axis=0)))
# Crop image for using Wavelet2/3 (which only can use cubic volume)
Iref = Iref[:, :, :128]

imshow3D(Iref, display=True)

samples = get_sample_data("mri-radial-3d-samples").data
samples = normalize_samples(samples)

#############################################################################
# Generate the kspace
# -------------------
#
# From the 3D phantom and the acquistion mask, we generate the acquisition
# measurments, the observed kspace.
# We then reconstruct the zero order solution.

# Generate the subsampled kspace
fourier_op_gen = NFFT3(samples=samples, shape=Iref.shape)
kspace_data = fourier_op_gen.op(Iref)

# Zero order solution
image_rec0 = fourier_op_gen.adj_op(kspace_data)
imshow3D(np.abs(image_rec0), display=True)

max_iter = 100

# linear_op = pyWavelet3(wavelet_name="bior6.8",
#                        nb_scale=3)

linear_op = Wavelet2(
        nb_scale=3,
        wavelet_name='BiOrthogonalTransform3D')


fourier_op = NFFT3(samples=samples, shape=Iref.shape)

print('Starting Lipschitz constant computation')

gradient_op = Gradient_pMRI(data=kspace_data,
                            fourier_op=fourier_op,
                            linear_op=linear_op)

print('Lipschitz constant found: ', str(gradient_op.spec_rad))

x_final, transform, cost = sparse_rec_fista(
    gradient_op=gradient_op,
    linear_op=linear_op,
    mu=0,
    lambda_init=1.0,
    max_nb_of_iter=max_iter,
    atol=1e-4,
    verbose=1,
    get_cost=True)

imshow3D(np.abs(x_final), display=True)
plt.figure()
plt.plot(cost)
plt.show()


gradient_op_cd = Gradient_pMRI(data=kspace_data,
                               fourier_op=fourier_op)
x_final, transform = sparse_rec_condatvu(
    gradient_op=gradient_op_cd,
    linear_op=linear_op,
    std_est=None,
    std_est_method="dual",
    std_thr=2.,
    mu=1e-5,
    tau=None,
    sigma=None,
    relaxation_factor=1.0,
    nb_of_reweights=0,
    max_nb_of_iter=max_iter,
    add_positivity=False,
    atol=1e-4,
    verbose=1)

imshow3D(np.abs(x_final), display=True)
