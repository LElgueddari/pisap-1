# -*- coding: utf-8 -*-
##########################################################################
# XXX - Copyright (C) XXX, 2017
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
#
#:Author: Samuel Farrens <samuel.farrens@gmail.com>
#:Version: 1.1
#:Date: 04/01/2017
##########################################################################
"""
This module contains classses for defining algorithm operators and gradients.
Based on work by Yinghao Ge and Fred Ngole.
"""

# System import
import copy
import numpy as np
import scipy.fftpack as pfft

import pisap
from pisap.base.utils import generic_l2_norm


class GradBase(object):
    """ Basic gradient class

    This class defines the basic methods that will be inherited by specific
    gradient classes
    """
    def get_initial_x(self):
        """ Set initial value of x.

        This method sets the initial value of x to an arrray of random values
        """
        raise NotImplementedError("'GradBase' is an abstract class: " \
                                    +   "it should not be instanciated")

    def MX(self, x):
        """ MX

        This method calculates the action of the matrix M on the data X, in
        this case fourier transform of the the input data

        Parameters
        ----------
        x : np.ndarray
            Input data array, an array of recovered 2D images

        Returns
        -------
        np.ndarray result
        """
        raise NotImplementedError("'GradBase' is an abstract class: " \
                                    +   "it should not be instanciated")

    def MtX(self, x):
        """ MtX

        This method calculates the action of the transpose of the matrix M on
        the data X, in this case inverse fourier transform of the input data

        Parameters
        ----------
        x : np.ndarray
            Input data array, an array of recovered 2D images

        Returns
        -------
        np.ndarray result
        """
        raise NotImplementedError("'GradBase' is an abstract class: " \
                                    +   "it should not be instanciated")

    def get_spec_rad(self, tolerance=1e-4, max_iter=20, coef_mul=1.1):
        """ Get spectral radius.

        This method calculates the spectral radius.

        Parameters
        ----------
        tolerance : float (optional, default 1e-8)
            Tolerance threshold for convergence.
        max_iter : int (optional, default 150)
            Maximum number of iterations.
        verbose: int (optional, default 0)
            The verbosity level.
        """
        # Set (or reset) values of x.
        x_old = self.get_initial_x()

        # Iterate until the L2 norm of x converges.
        for i in xrange(max_iter):
            x_new = self.MtMX(x_old) / generic_l2_norm(x_old)
            if(np.abs(generic_l2_norm(x_new) - generic_l2_norm(x_old)) < tolerance):
                break
            x_old = copy.deepcopy(x_new)
        self.spec_rad = coef_mul * generic_l2_norm(x_new)
        self.inv_spec_rad = 1.0 / self.spec_rad

    def MtMX(self, x):
        """ M^T M X

        This method calculates the action of the transpose of the matrix M on
        the action of the matrix M on the data X

        Parameters
        ----------
        x : np.ndarray
            Input data array

        Returns
        -------
        np.ndarray result

        Notes
        -----
        Calculates  M^T (MX)
        """
        return self.MtX(self.MX(x))


    def get_grad(self, x):
        """ Get the gradient step

        This method calculates the gradient step from the input data

        Parameters
        ----------
        x : np.ndarray
            Input data array

        Returns
        -------
        np.ndarray gradient value

        Notes
        -----

        Calculates M^T (MX - Y)
        """
        self.grad = self.MtX(self.MX(x) - self.y) # self.y can be a 2D array or a vector


class Grad2DAnalysis(GradBase):
    """ Standard 2D gradient class

    This class defines the operators for a 2D array

    Parameters
    ----------
    data : np.ndarray
        Input data array, an array of 2D observed images (i.e. with noise)
    ft_cls :  Fourier operator derive from base class 'FourierBase'
        Fourier class, for computing Fourier transform (NFFT or FFT)
    """
    def __init__(self, data, ft_cls, linear_cls=None):
        """ Initilize the Grad2Danalysis class.
        """
        self.y = data
        self.analysis = True
        if isinstance(ft_cls, dict):
            if len(ft_cls) > 1:
                raise ValueError("ft_cls in Grad2DAnalysis should either be a 1"
                                 " 'key dict' or a 'fourier op class'")
            self.ft_cls = ft_cls.keys()[0](**ft_cls.values()[0])
        else:
            self.ft_cls = ft_cls
        self.get_spec_rad()

    def get_initial_x(self):
        """ Set initial value of x.

        This method sets the initial value of x to an arrray of random values
        """
        return np.random.random((self.ft_cls.img_size,self.ft_cls.img_size)).astype(np.complex)

    def MX(self, x):
        """ MX

        This method calculates the action of the matrix M on the data X, in
        this case fourier transform of the the input data

        Parameters
        ----------
        x : np.ndarray
            Input data array, an array of recovered 2D images

        Returns
        -------
        np.ndarray result
        """
        return self.ft_cls.op(x)

    def MtX(self, x):
        """ MtX

        This method calculates the action of the transpose of the matrix M on
        the data X, in this case inverse fourier transform of the input data

        Parameters
        ----------
        x : np.ndarray
            Input data array, an array of recovered 2D images

        Returns
        -------
        np.ndarray result
        """
        return self.ft_cls.adj_op(x)


class Grad2DSynthesis(GradBase):
    """ Synthesis 2D gradient class

    This class defines the grad operators for |M*F*invL*alpha - data|**2.

    Parameters
    ----------
    data : np.ndarray
        Input data array, an array of 2D observed images (i.e. with noise)
    ft_cls :  Fourier operator derive from base class 'FourierBase'
        Fourier class, for computing Fourier transform (NFFT or FFT)
    linear_cls: class
        a linear operator class.
    """
    def __init__(self, data, ft_cls, linear_cls):
        """ Initilize the Grad2DSynthesis class.
        """
        self.y = data
        self.analysis = False
        if isinstance(ft_cls, dict):
            if len(ft_cls) > 1:
                raise valueerror("ft_cls in grad2dsynthesis should either be a 1"
                                 " 'key dict' or a 'fourier op class'")
            self.ft_cls = ft_cls.keys()[0](**ft_cls.values()[0])
        else:
            self.ft_cls = ft_cls
        self.linear_cls = linear_cls
        self.get_spec_rad()

    def get_initial_x(self):
        """ Set initial value of x.

        This method sets the initial value of x to an arrray of random values
        """
        fake_data = np.zeros((self.ft_cls.img_size, self.ft_cls.img_size)).astype(np.complex)
        trf = self.linear_cls.op(fake_data)
        trf._data = np.random.random(len(trf._data)).astype(np.complex)
        return trf

    def MX(self, alpha):
        """ MX

        This method calculates the action of the matrix M on the data X, in
        this case fourier transform of the the input data

        Parameters
        ----------
        alpha : DictionaryBase
            Input analysis decomposition

        Returns
        -------
        np.ndarray result recovered 2D kspace
        """
        return self.ft_cls.op(self.linear_cls.adj_op(alpha))

    def MtX(self, x):
        """ MtX

        This method calculates the action of the transpose of the matrix M on
        the data X, in this case inverse fourier transform of the input data in
        the frequency domain.

        Parameters
        ----------
        x : np.ndarray
            Input data array, an array of recovered 2D kspace

        Returns
        -------
        DictionaryBase result
        """
        return self.linear_cls.op(self.ft_cls.adj_op(x))


class Grad2DSynthese_Pmri(GradBasic, PowerMethod):
    """ 2D synthesis gradient for parallel imaging in MRI.

    This class defines the operators for a 2D array multiplied by
    sensitivity matrices
    This class defines the grad operators for
    \sum_{l=1}^L|M*F* S_l*invL*alpha - data_l|**2.
    """
    def __init__(self, data, smap, mask, linear_operator):
        """ Initilize the Grad2DAnalyse class.

        Parameters
        ----------
        data: np.ndarray
            Input data array, an array of 3D observed images (i.e. with noise)
            where image size fits the first 2 dimensions and the nb of channels
            fits the third dimension
        smap: np.ndarray
            Sensitivity maps array, 3D array where the first dimension fits
            the number of channels and the last 2 dimensions fit the image
            dimensions
        mask:  np.ndarray
            The subsampling mask.
        linear_operator: pisap.numeric.linear.Wavelet
            A linear operator.
        """
        self.y = data
        self.smap = smap
        self.mask = mask
        self.linear_operator = linear_operator
        if mask is None:
            self.mask = np.ones(data.shape, dtype=int)
        if smap is None:
            nb_channels=8
            self.map = np.ones((data.shape,nb_channels), dtype=float) +\
                        +1.j*np.ones((data.shape,nb_channels), dtype=float)
        PowerMethod.__init__(self, self.MtMX, self.y.shape)
        self.get_spec_rad()

    def set_initial_x(self):
        """ Set initial value of x.
        #stamp: We should
        This method sets the initial value of x to an arrray of random values
        """
        fake_data = np.zeros(self.y.shape[0,:,:]).astype(np.complex)
        coeffs = self.linear_operator.op(fake_data)
        coeffs = np.random.random(len(coeffs)).astype(np.complex)
        return coeffs

    def MX(self, smap, alpha):
        """ MX.

        This method calculates the action of the matrix M on the decomposisiton
        coefficients in the case of parallel MRI, where a elementwise matrix
        multiplication is applied between image and sensitivity maps

        Parameters
        ----------
        smap: nd-array
            Input sensitivity maps (3D arrray: nb channels x image size)
            We use here the automatic broadcast of python
        alpha: nd-array
            Input decomposisiton coefficients.

        Returns
        -------
        coeffs: np.ndarray
            Multichannel 3D Fourier coefficients (pMRI model output)
        """
        return self.mask * pfft.fft2(self.smap *
                                     self.linear_operator.adj_op(alpha))

    def MtX(self, smap, coeffs):
        """ MtX.

        This method calculates the action of the transpose of the matrix M on
        the data X, in this case inverse fourier transform of the input data in
        the frequency domain.

        Parameters
        ----------
        smap: nd-array
            Input sensitivity maps (3D arrray: nb channels x image size)
        coeffs: np.ndarray
            Multichannel 3D Fourier coefficients (pMRI model output)

        Returns
        -------
        x: nd-array
            Reconstructed data array decomposisiton coefficients.
        """
        return self.linear_operator.op(self.smap.conjugate() *
                                       pfft.ifft2(self.mask * coeffs)))

    def MtMX(self, smap, coeffs):
        """M^T M X

        This method calculates the action of the transpose of the matrix M on
        the action of the matrix M on the data X in the context of pMRI.
        This requires summing over all channels, hence over the first dimension

        Parameters
        ----------
        x : np.ndarray
            Input data array

        Returns
        -------
        np.ndarray result

        Notes
        -----
        Calculates  M^T (MX)

        """
        return np.sum(self.MtX(self.MX(x)), axis=0)

    def get_grad(self, x):
        """Get the gradient step

        This method calculates the gradient step from the input data in the
        pMRI context.

        Parameters
        ----------
        x : np.ndarray
            Input data array

        Returns
        -------
        np.ndarray gradient value

        Notes
        -----

        Calculates M^T (MX - Y)

        """
        self.grad = np.sum(self.MtX(self.MX(x) - self.y),axis=0)
