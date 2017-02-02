#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2016-2017, Cabral, Juan; Luczywo, Nadia
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# * Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.

# * Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.

# * Neither the name of the copyright holder nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


# =============================================================================
# FUTURE
# =============================================================================

from __future__ import unicode_literals


# =============================================================================
# DOCS
# =============================================================================

__doc__ = """Implementation of a family of Multi-objective optimization on
the basis of ratio analysis (MOORA) methods.

Methods:

- MOORA with ratio (:py:func:`skcriteria.moora.ratio`).
- MOORA with reference point (:py:func:`skcriteria.moora.refpoint`).
- Full multiplicative form (:py:func:`skcriteria.moora.fmf`).
- Multi-MOORA (:py:func:`skcriteria.moora.multimoora`).


"""


# =============================================================================
# IMPORTS
# =============================================================================

import itertools

import numpy as np

from .. import norm, util, rank
from ..dmaker import DecisionMaker


# =============================================================================
# FUNCTIONS
# =============================================================================

def _ratio(nmtx, criteria, nweights):

    cweights = nweights * criteria

    # calculate raning by inner prodcut
    rank_mtx = np.inner(nmtx, cweights)
    points = np.squeeze(np.asarray(rank_mtx))
    return rank.rankdata(points, reverse=True), points


def ratio(mtx, criteria, weights=None, mnorm=norm.vector, wnorm=norm.sum):
    r"""The method refers to a matrix of responses of alternatives to
    objectives, to which ratios are applied.

    In MOORA the set of ratios (by default) has the square roots of the sum
    of squared responses as denominators [BRAUERS2006]_ .

    .. math::

        \overline{X}_{ij} =
        \frac{X_{ij}}{\sqrt{\sum\limits_{j=1}^m X_{ij}^{2}}}


    These ratios, as dimensionless, seem to be the best choice among different
    ratios. These dimensionless ratios, situated between zero and one, are
    added in the case of maximization or subtracted in case of minimization.
    Finally, all alternatives are ranked, according to the obtained ratios.


    Parameters
    ----------

    mtx : A matrix like object
        Matrix of responses of alternatives to objectives.

    criteria : iterable
        Criteria vector. Can only containing *util.MIN* or *util.MAX* values
        with the same columns as mtx.

    weights : iterable or None
        Used to ponderate some criteria. The value of the weight is normalized
        to values between *0* and *1*. [CURCHOD2014]_


    Returns
    -------

    rnk, points : (:py:class:`numpy.ndarray`, :py:class:`numpy.ndarray`)
        *rnk* is a zero based rank of all alternatives. The values of the
        *i-th* element of the array is the final rank of the *i-th*
        alternative. The value of the *i-th* element of *points*
        the array contains the points of the *i-th* alternative.


    References
    ----------

    .. [BRAUERS2006] BRAUERS, W. K.; ZAVADSKAS, Edmundas Kazimieras. The MOORA
       method and its application to privatization in a transition economy.
       Control and Cybernetics, 2006, vol. 35, p. 445-469.`


    .. [CURCHOD2014] CURCHOD, M. A.; ALBERTO, C. L. Aplicación del método
       MOORA para el desarrollo de un indicador compuesto. XXVII ENDIO - XXV
       EPIO, 2014.


    Examples
    --------

    >>> from skcriteria import moora
    >>>
    >>> mtx = [[1,2,3], [1,1,4], [2, 0, 1]]
    >>> criteria = [1, -1, 1]
    >>>
    >>> rnk, points = moora.ratio(mtx, criteria)
    >>>
    >>> rnk
    array([2, 1, 0])
    >>> points
    array([ 0.1021695 ,  0.74549924,  1.01261272])

    """
    nmtx = mnorm(mtx, axis=0)
    ncriteria = util.criteriarr(criteria)
    nweights = wnorm(weights) if weights is not None else 1
    return _ratio(nmtx, ncriteria, nweights)


def _refpoint(nmtx, criteria, weights):
    # max and min reference points
    rpmax = np.max(nmtx, axis=0)
    rpmin = np.min(nmtx, axis=0)

    # merge two reference points acoording criteria
    mask = np.where(criteria == util.MAX, criteria, 0)
    rpoints = np.where(mask, rpmax, rpmin)

    # create rank matrix
    rank_mtx = np.max(np.abs(weights * (nmtx - rpoints)), axis=1)
    points = np.squeeze(np.asarray(rank_mtx))
    return rank.rankdata(points), points


def refpoint(mtx, criteria, weights=None, mnorm=norm.vector, wnorm=norm.sum):
    nmtx = mnorm(mtx, axis=0)
    ncriteria = util.criteriarr(criteria)
    nweights = wnorm(weights) if weights is not None else 1
    return _refpoint(nmtx, ncriteria, nweights)


def _fmf(nmtx, criteria):
    lmtx = np.log(nmtx)

    if not np.setdiff1d(criteria, [util.MAX]):
        # only max
        points = np.sum(lmtx, axis=1)
    elif not np.setdiff1d(criteria, [util.MIN]):
        # only min
        points = 1 - np.sum(lmtx, axis=1)
    else:
        # min max
        min_mask = np.ravel(np.argwhere(criteria == util.MAX))
        max_mask = np.ravel(np.argwhere(criteria == util.MIN))

        # remove invalid values
        min_arr = np.delete(lmtx, min_mask, axis=1)
        max_arr = np.delete(lmtx, max_mask, axis=1)

        mins = np.sum(min_arr, axis=1)
        maxs = np.sum(max_arr, axis=1)
        points = maxs - mins

    return rank.rankdata(points, reverse=True), points


def fmf(mtx, criteria, mnorm=norm.vector):
    non_negative = norm.push_negatives(mtx, axis=0)
    non_zero = norm.add1to0(non_negative, axis=0)
    nmtx = mnorm(non_zero, axis=0)

    ncriteria = util.criteriarr(criteria)
    return _fmf(nmtx, ncriteria)


def multimoora(mtx, criteria, mnorm=norm.vector):

    nmtx = mnorm(mtx, axis=0)
    ncriteria = util.criteriarr(criteria)

    ratio_rank = _ratio(nmtx, ncriteria, 1)[0]
    refpoint_rank = _refpoint(nmtx, ncriteria, 1)[0]
    fmf_rank = _fmf(nmtx, ncriteria)[0]

    rank_mtx = np.array([ratio_rank, refpoint_rank, fmf_rank]).T

    alternatives = rank_mtx.shape[0]
    points = np.zeros(alternatives)
    for idx0, idx1 in itertools.combinations(range(alternatives), 2):
        alt0, alt1 = rank_mtx[idx0], rank_mtx[idx1]
        dom = rank.dominance(alt0, alt1)
        dom_idx = idx0 if dom > 0 else idx1
        points[dom_idx] += 1

    return rank.rankdata(points, reverse=True), rank_mtx


# =============================================================================
# OO
# =============================================================================

class RatioMOORA(DecisionMaker):

    def solve(self, mtx, criteria, weights):
        rank, points = ratio(mtx, criteria, weights)
        return None, rank, {"points": points}


class RefPointMOORA(DecisionMaker):

    def solve(self, mtx, criteria, weights):
        rank, points = refpoint(mtx, criteria, weights)
        return None, rank, {"points": points}


class FMFMOORA(DecisionMaker):

    def solve(self, mtx, criteria, weights):
        rank, points = fmf(mtx, criteria)
        return None, rank, {"points": points}


class MultiMOORA(DecisionMaker):

    def solve(self, mtx, criteria, weights):
        rank, rank_mtx = multimoora(mtx, criteria)
        return None, rank, {"rank_mtx": rank_mtx}