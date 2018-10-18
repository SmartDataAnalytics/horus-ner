# -*- coding: utf-8 -*-

"""
==========================================================
HORUS: Named Entity Recognition Algorithm
==========================================================

HORUS is a Named Entity Recognition Algorithm specifically
designed for short-text, i.e., microblogs and other noisy
datasets existing on the web, e.g.: social media, some web-
sites, blogs and etc..

It is a simplistic approach based on multi-level machine
learning combined with computer vision techniques.

more info at: https://github.com/dnes85/components-models

"""

# Author: Esteves <diegoesteves@gmail.com>
# Version: 1.0
# Version Label: HORUS_NER_2016_1.0
# License: BSD 3 clause
import logging

import re

from horusner.components.systemlog import SystemLog
from sklearn.externals import joblib

from src.config import HorusConfig
import numpy as np

from src.core.features import FeatureExtraction
from src.util import definitions
from src.util.util import Util


class HorusDemo(object):

    def __init__(self):
        self.config = HorusConfig()
        self.util = Util(self.config)
        self.final = joblib.load(self.config.model_final)
        self.final_encoder = joblib.load(self.config.model_final_encoder)
        self.extractor = FeatureExtraction(self.config)

    def predict(self, horus_matrix):
        self.config.logger.info('running final classifier...')
        try:
            for index in range(len(horus_matrix)):
                features = []
                pos_bef = ''
                pos_aft = ''
                if index > 1:
                    pos_bef = horus_matrix[index - 1][5]
                if index + 1 < len(horus_matrix):
                    pos_aft = horus_matrix[index + 1][5]

                one_char_token = 1 if len(horus_matrix[index][3]) == 1 else 0
                special_char = 1 if len(
                    re.findall('(http://\S+|\S*[^\w\s]\S*)', horus_matrix[index][3])) > 0 else 0
                first_capitalized = 1 if horus_matrix[index][3][0].isupper() else 0
                capitalized = 1 if horus_matrix[index][3].isupper() else 0
                '''
                    pos-1; pos; pos+1; cv_loc; cv_org; cv_per; cv_dist; cv_plc; 
                    tx_loc; tx_org; tx_per; tx_err; tx_dist; 
                    one_char; special_char; first_cap; cap
                '''
                features.append((pos_bef, horus_matrix[index][5], pos_aft, int(horus_matrix[index][12]),
                                 int(horus_matrix[index][13]), int(horus_matrix[index][14]),
                                 int(horus_matrix[index][15]),
                                 int(horus_matrix[index][16]),  # int(self.horus_matrix[index][17])
                                 int(horus_matrix[index][20]), int(horus_matrix[index][21]),
                                 int(horus_matrix[index][22]), float(horus_matrix[index][23]),
                                 int(horus_matrix[index][24]),  # int(self.horus_matrix[index][25])
                                 one_char_token, special_char, first_capitalized, capitalized))

                features = np.array(features)
                features[0][0] = self.final_encoder.transform(features[0][0])
                features[0][1] = self.final_encoder.transform(features[0][1])
                features[0][2] = self.final_encoder.transform(features[0][2])
                horus_matrix[index][40] = definitions.PLOMNone_index2label[self.final.predict(features)[0]]

        except Exception as error:
            raise error

    def update_rules_cv_predictions(self):
        '''
        updates the predictions based on inner rules
        :return:
        '''
        self.logging.log.info('updating predictions based on rules')
        for i in range(len(self.horus_matrix)):
            initial = self.horus_matrix[i][17]
            # get nouns or compounds
            if self.horus_matrix[i][4] == 'NOUN' or \
                    self.horus_matrix[i][4] == 'PROPN' or self.horus_matrix[i][7] == 1:
                # do not consider classifications below a theta
                if self.horus_matrix[i][15] < int(self.config.models_distance_theta):
                    self.horus_matrix[i][17] = "*"
                # ignore LOC classes having iPLC negative
                if bool(int(self.config.models_distance_theta_high_bias)) is True:
                    if initial == "LOC":
                        if self.horus_matrix[i][16] < int(self.config.models_limit_min_loc):
                            self.horus_matrix[i][17] = "*"
                        elif self.horus_matrix[i][16] < 0 and self.horus_matrix[i][15] > \
                                int(self.config.models_safe_interval):
                            self.horus_matrix[i][17] = initial

    def update_compound_predictions(self):
        '''
        pre-requisite: the matrix should start with the sentence compounds at the beginning.
        '''
        self.logging.log.info('updating compounds predictions')
        i_y, i_sent, i_first_word, i_c_size = [], [], [], []
        for i in range(len(self.horus_matrix)):
            if self.horus_matrix[i][7] == 1:
                i_y.append(self.horus_matrix[i][36])  # KLASS_1
                i_sent.append(self.horus_matrix[i][1])
                i_first_word.append(self.horus_matrix[i][2])
                i_c_size.append(int(self.horus_matrix[i][8]))
            if self.horus_matrix[i][7] == 0:
                for z in range(len(i_y)):
                    if i_sent[z] == self.horus_matrix[i][1] and i_first_word[z] == self.horus_matrix[i][2]:
                        for k in range(i_c_size[z]):
                            self.horus_matrix[i + k][39] = i_y[z]  # KLASS_4



if __name__ == '__main__':
    #args[0], args[1], args[2], args[3]
    try:
        horus = HorusDemo()
        metadata = horus.extractor.extract_features_from_text('paris hilton was once the toast of the town')
        horus.predict(metadata)
    except:
        raise