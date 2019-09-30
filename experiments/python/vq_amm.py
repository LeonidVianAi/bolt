#!/usr/bin/env python

import numpy as np

from . import vquantizers as vq
from . import amm

KEY_NLOOKUPS = 'nlookups'


class PQMatmul(amm.ApproxMatmul):

    def __init__(self, ncodebooks):
        self.ncodebooks = ncodebooks
        self.enc = self._create_encoder(ncodebooks)
        self._reset()

    def _create_encoder(self, ncodebooks):  # to be overriden by subclasses
        return vq.PQEncoder(nsubvects=ncodebooks,
                            **self._get_encoder_kwargs())

    def _get_encoder_kwargs(self):  # to be overriden by subclasses
        return {}

    def _reset(self):
        self.A_enc = None
        self.luts = None

    def fit(self, A, B, Y=None):
        self.enc.fit(A, B)

    def set_A(self, A):
        self.A_enc = self.enc.encode_X(A)

    def set_B(self, B):
        self.luts = self.enc.encode_Q(B.T)

    def __call__(self, A, B):
        if self.A_enc is None:
            self.set_A(A)
        if self.luts is None:
            self.set_B(B)
        return self.enc.dists_enc(self.A_enc, self.luts)

    def get_speed_metrics(self, A, B, fixedA=False, fixedB=False):
        nmuls = 0 if fixedB else B.shape[0] * B.shape[1] * 256
        nlookups = A.shape[0] * B.shape[1] * self.ncodebooks
        return {amm.KEY_NMULTIPLIES: nmuls, KEY_NLOOKUPS: nlookups}

    def get_params(self):
        return {'ncodebooks': self.ncodebooks}


class BoltMatmul(PQMatmul):

    def __init__(self, ncodebooks):
        self.ncodebooks = 2 * ncodebooks
        self.enc = vq.PQEncoder(nsubvects=self.ncodebooks, ncentroids=16)
        self._reset()

    def get_speed_metrics(self, A, B, fixedA=False, fixedB=False):
        nmuls = 0 if fixedB else B.shape[0] * B.shape[1] * 16
        nlookups = A.shape[0] * B.shape[1] * self.ncodebooks
        return {amm.KEY_NMULTIPLIES: nmuls, KEY_NLOOKUPS: nlookups}


class OPQMatmul(PQMatmul):

    def _get_encoder_kwargs(self):
        return dict(algo='OPQ')

    def get_speed_metrics(self, A, B, fixedA=False, fixedB=False):
        nmuls = 0 if fixedB else B.shape[0] * B.shape[1] * 256   # lut cost
        nmuls += A.shape[0] * A.shape[1] * A.shape[1]  # OPQ rotation cost
        nlookups = A.shape[0] * B.shape[1] * 2 * self.ncodebooks
        return {amm.KEY_NMULTIPLIES: nmuls, KEY_NLOOKUPS: nlookups}