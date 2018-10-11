import argparse
import os

import time

import gc
import sklearn
from sklearn.decomposition import PCA
from sklearn.feature_extraction import DictVectorizer
from sklearn.preprocessing import OneHotEncoder

from src.util.definitions import encoder_le1_name, dict_exp_feat, SET_MASK

os.environ['TF_CPP_MIN_LOG_LEVEL']='2'

import matplotlib.pyplot as plt
import sklearn_crfsuite
from sklearn import ensemble
from sklearn.cross_validation import train_test_split, KFold
from sklearn_crfsuite import metrics

plt.style.use('ggplot')
from src.config import HorusConfig
from src.util import definitions
from sklearn.externals import joblib
import scipy.stats
from sklearn.metrics import make_scorer, accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.grid_search import RandomizedSearchCV
import numpy as np
from keras.engine import InputLayer
from keras.models import Sequential
from keras.layers.core import Activation
from keras.layers.wrappers import TimeDistributed
from keras.preprocessing.sequence import pad_sequences
from keras.layers import Embedding, LSTM, Dense, Merge
from nltk.corpus import stopwords
from nltk import LancasterStemmer, re, WordNetLemmatizer
import pandas as pd
import cPickle as pickle
# import pickle
import multiprocessing
from functools import partial
from contextlib import contextmanager
from nltk.stem.snowball import SnowballStemmer

"""
==========================================================
Experiments: 
    NER models X NER + HORUS features
==========================================================
Within this experiments we show the performance of standard
NER algorithms (Stanford NER and NLTK NER) with and without
using HORUS as features

input: 
- horus matrix file: see README -> https://github.com/diegoesteves/horus-ner

output:
- performance measures
"""
config = HorusConfig()
X, Y = [], []
ds_test_size = 0.20
stemmer = SnowballStemmer('english')
stop = set(stopwords.words('english'))
enc_le1 = joblib.load(config.dir_encoders + definitions.encoder_le1_name)
enc_le2 = joblib.load(config.dir_encoders + definitions.encoder_le2_name)
enc_word = joblib.load(config.dir_encoders + definitions.encoder_int_words_name)
enc_lemma = joblib.load(config.dir_encoders + definitions.encoder_int_lemma_name)
enc_stem = joblib.load(config.dir_encoders + definitions.encoder_int_stem_name)

@contextmanager
def poolcontext(*args, **kwargs):
    pool = multiprocessing.Pool(*args, **kwargs)
    yield pool
    pool.terminate()

def encode(x, n):
    result = np.zeros(n)
    result[x] = 1
    return result
#keras.utils.np_utils.to_categorical or sparse_categorical_crossentropy

def load_dumps_in_memory((_file, ds, _set_name)):
    config.logger.info('loading dump file [%s]: %s' % (ds, _file))
    f = open(_file, 'rb')
    dump = pickle.load(f)
    f.close()
    return (_set_name, dump)

def features_to_crf_shape(sent, i):

    features = {'bias': 1.0}
    features.update(dict(('f'+str(key), sent.iloc[i].at[key]) for key in np.sort(sent.columns.values)))

    if i > 0:
        features_pre = dict(('-1:f'+str(key), sent.iloc[i-1].at[key]) for key in np.sort(sent.columns.values))
        features.update(features_pre)
    else:
        features['BOS'] = True

    if i < len(sent) - 1:
        features_pos = dict(('+1:f'+str(key), sent.iloc[i+1].at[key]) for key in np.sort(sent.columns.values))
        features.update(features_pos)
    else:
        features['EOS'] = True

    return features

def exclude_columns(df, f_indexes):
    if isinstance(df, pd.DataFrame) == False:
        df = pd.DataFrame(df)
    #dfret = df.copy()
    out = None
    a = set(df.columns)
    b = set(f_indexes)
    out = df.drop(list(a-b), axis=1, inplace=False)

    #for icol in df.columns:
        #if icol not in f_indexes:

    return out

def sent2label(sent):
    return [definitions.PLONone_index2label[y] for y in sent]

def sent2features(sent):
    return [features_to_crf_shape(sent, i) for i in range(len(sent))]

def convert_lstm_shape(X, y, horus_feat = False):

    all_text = [c[0] for x in X for c in x]
    all_text.extend([c[1] for x in X for c in x])

    words = list(set(all_text))  # distinct tokens
    word2ind = {word: index for index, word in enumerate(words)}  # indexes of words
    ind2word = {index: word for index, word in enumerate(words)}
    #labels = list(set([c for x in y for c in x]))
    label2ind = definitions.PLONone_label2index
    ind2label = definitions.PLONone_index2label
    print('Vocabulary size:', len(word2ind), len(label2ind))
    lengths = [len(x) for x in Xclean]
    maxlen = max(lengths)
    print('min sentence / max sentence: ', min(lengths), maxlen)
    if horus_feat == False:
        X_enc = [[[word2ind[c[0]], word2ind[c[1]], c[2], c[3], c[4], c[5], c[6], c[7], c[8]] for c in x] for x in Xclean]
    else:
        X_enc = [[[word2ind[c[0]], word2ind[c[1]], c[2], c[3], c[4], c[5], c[6], c[7], c[8],
                   c[9], c[10], c[11], c[12], c[13], c[14], c[15], c[16], c[17], c[18]] for c in x] for x in Xclean]

    max_label = max(label2ind.values()) + 1
    y_enc = [[0] * (maxlen - len(ey)) + [label2ind[c] for c in ey] for ey in y]
    y_enc = [[encode(c, max_label) for c in ey] for ey in y_enc]

    max_features = len(word2ind)
    out_size = len(label2ind) + 1

    return X_enc, y_enc, max_features, out_size, maxlen

def score2(yh, pr):
    #real-no-encoding x predicted
    coords = [np.where(yhh > 0)[0][0] for yhh in yh]
    yh = [yhh[co:] for yhh, co in zip(yh, coords)]
    ypr = [prr[co:] for prr, co in zip(pr, coords)]
    fyh = [c for row in yh for c in row]
    fpr = [c for row in ypr for c in row]
    print set(fyh)
    print set(fpr)
    return fyh, fpr

def run_lstm(Xtr, Xte, ytr, yte, max_features, max_features2, out_size, embedding_size, hidden_size, batch_size, epochs=50, verbose = 0, maxsent = 0):

    print('Training and testing tensor shapes:', Xtr.shape, Xte.shape, ytr.shape, yte.shape)

    mf = max(max_features, max_features2)

    model1 = Sequential()
    model1.add(Embedding(input_dim=mf, output_dim=embedding_size, input_length=maxsent, mask_zero=True))

    model2 = Sequential()
    model2.add(InputLayer(input_shape=(maxsent, Xtr.shape[2] - 1)))

    model = Sequential()
    model.add(Merge([model1, model2], mode='concat'))
    model.add(Dense(1))

    model.add(LSTM(hidden_size, return_sequences=True, input_shape=(maxsent, Xtr.shape[2] - 1)))
    model.add(TimeDistributed(Dense(out_size)))
    model.add(Activation('softmax'))

    model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])
    #print(model.summary())
    print('train...')

    model.fit([Xtr[:, :, 0], Xtr[:, :, 1:Xtr.shape[2]]], ytr, epochs=epochs, verbose=verbose, batch_size=batch_size,
              validation_data=([Xte[:, :, 0], Xte[:, :, 1:Xtr.shape[2]]], yte))
    score = model.evaluate([Xte[:, :, 0], Xte[:, :, 1:Xtr.shape[2]]], yte, batch_size=batch_size, verbose=verbose)

    print('Raw test score:', score)
    pr = model.predict_classes([Xtr[:, :, 0], Xtr[:, :, 1:Xtr.shape[2]]], verbose=verbose)
    yh = ytr.argmax(2)  # no encoding
    fyh, fpr = score2(yh, pr)
    print('Training...')
    print(' - accuracy:', accuracy_score(fyh, fpr))
    print(' - confusion matrix:')
    print(confusion_matrix(fyh, fpr))
    print(' - precision, recall, f1, support:')
    print(precision_recall_fscore_support(fyh, fpr))

    pr = model.predict_classes([Xte[:, :, 0], Xte[:, :, 1:Xte.shape[2]]], verbose=verbose)
    yh = yte.argmax(2)
    fyh, fpr = score2(yh, pr)
    print('Testing...')
    print(' - accuracy:', accuracy_score(fyh, fpr))
    print(' - confusion matrix:')
    print(confusion_matrix(fyh, fpr))
    print(' - precision, recall, f1, support:')
    print(precision_recall_fscore_support(fyh, fpr))
    print('----------------------------------------------------------------------------------')

def save_data_by_configuration((ds, dump_path, file_name, f_key, f_indexes)):

    try:

        config.logger.debug('removing columns: ' + file_name)

        config.logger.debug(' -- X_sentence')
        X_sentence = [exclude_columns(s, f_indexes) for s in ds[1][0]]
        Y_sentence = [sent2label(s) for s in ds[1][1]]
        dump_path_type = dump_path.replace('.pkl', '.sentence.pkl')
        with open(dump_path_type, 'wb') as output1:
            pickle.dump((file_name, f_key, X_sentence, Y_sentence), output1, pickle.HIGHEST_PROTOCOL)
        config.logger.debug(dump_path_type + ' created!')

        config.logger.debug(' -- X_token')
        X_token = exclude_columns(ds[2][0], f_indexes)
        X_token.replace('O', 0, inplace=True)
        #Y_token = [definitions.PLONone_label2index[y] for y in ds[2][1]]
        Y_token = [int(y) for y in ds[2][1]]
        dump_path_type = dump_path.replace('.pkl', '.token.pkl')
        with open(dump_path_type, 'wb') as output2:
            pickle.dump((file_name, f_key, X_token, Y_token), output2, pickle.HIGHEST_PROTOCOL)
        config.logger.debug(dump_path_type + ' created!')

        config.logger.debug(' -- X_crf')
        X_crf = [sent2features(s) for s in X_sentence]
        # trick for scikit-learn on CRF (for the precision_recall_f-score_support method)
        Y_crf = np.array([x for s in Y_sentence for x in s])
        dump_path_type = dump_path.replace('.pkl', '.crf.pkl')
        with open(dump_path_type, 'wb') as output3:
            pickle.dump((file_name, f_key, X_crf, Y_crf), output3, pickle.HIGHEST_PROTOCOL)
        config.logger.debug(dump_path_type + ' created!')

        ## X_lstm, y_lstm, max_features, out_size, maxlen = convert_lstm_shape(X_sentence, Y_sentence, f_indexes)
        ## X2_lstm, y2_lstm, max_features_2, out_size_2, maxlen_2 = convert_lstm_shape(ds2[1][0], ds2[1][1], f_indexes)
        ## X1_lstm = pad_sequences(X1_lstm, maxlen=max(maxlen_1, maxlen_2))
        ## y1_lstm = pad_sequences(y1_lstm, maxlen=max(maxlen_1, maxlen_2))

        #with open(dump_path, 'wb') as output:
        #    pickle.dump((file_name, f_key, X_sentence, Y_sentence, X_token, Y_token, X_crf, _Y_sentence),
        #                output, pickle.HIGHEST_PROTOCOL)
        #config.logger.debug(dump_path + ' created!')

    except Exception as e:
        config.logger.error(repr(e))
        raise e

def create_benchmark_dump_files():
    try:
        job_dumps = []
        for ds in definitions.NER_DATASETS:
            horus_m4_path = ds[1].replace('.horusx', '.horus4')
            horus_m4_name = ds[0]
            if not os.path.isfile(horus_m4_path):
                config.logger.error(
                    ' -- file .horus4 does not exist! please check the file extract_lex.py to create it...')
                raise Exception
            else:
                config.logger.debug('loading: ' + horus_m4_path)
                with open(horus_m4_path, 'rb') as input:
                    data = pickle.load(input)
                    for key, value in dict_exp_feat.items():
                        dump_name = SET_MASK % (horus_m4_name, str(key))
                        dump_full_path = os.path.dirname(os.path.realpath(horus_m4_path)) + '/' +  dump_name
                        if not os.path.exists(dump_full_path):
                            config.logger.debug(' -- key: ' + str(key))
                            job_dumps.append((data, dump_full_path, dump_name, key, value))

        if len(job_dumps) > 0:
            config.logger.info('creating dump files: ' + str(len(job_dumps)) + ' jobs')
            p = multiprocessing.Pool(multiprocessing.cpu_count())
            p.map(save_data_by_configuration, job_dumps)
            config.logger.info('dump files generated successfully')

    except Exception as e:
        config.logger.error(repr(e))



def benchmark(experiment_folder, datasets, runCRF = False, runDT = False, runLSTM = False, runSTANFORD_NER = False):

    config.logger.info('models: CRF=%s, DT=%s, LSTM=%s, Stanford=%s' % (str(runCRF), str(runDT), str(runLSTM), str(runSTANFORD_NER)))
    experiment_folder+='/'

    #sorted_labels = definitions.KLASSES.copy()
    #del sorted_labels[4]
    sorted_labels={'PER': 'PER', 'ORG': 'ORG', 'LOC': 'LOC'}
    r = [42, 39, 10, 5, 50]
    # hyper-parameters
    _crf = sklearn_crfsuite.CRF(algorithm='lbfgs', c1=0.088, c2=0.002, max_iterations=100, all_possible_transitions=True)
    _crf2 = sklearn_crfsuite.CRF(algorithm='pa', all_possible_transitions=True)
    _dt = ensemble.RandomForestClassifier(n_estimators=50)
    embedding_size = 128
    hidden_size = 32
    batch_size = 128
    epochs = 50
    verbose = 0
    #_meta = MEX('HORUS_EMNLP', _label, 'meta and multi-level machine learning for NLP')
    RUN_PROCESS_KEY_STARTS = 1
    RUN_PROCESS_KEY_ENDS = max(dict_exp_feat.keys())
    #RUN_PROCESS_KEY_ENDS = 30
    header = 'cross-validation\tconfig\trun\tlabel\tprecision\trecall\tf1\tsupport\talgo\tdataset1\tdataset2\ttask\n'
    line = '%s\t%s\t%s\t%s\t%.5f\t%.5f\t%.5f\t%s\t%s\t%s\t%s\t%s\n'


    config.logger.info('running benchmark...')
    # benchmark starts
    name='metadata_'
    if runCRF: name+='crf_'
    if runDT: name+='dt_'
    if runLSTM: name+='lstm_'
    assert name != 'metadata_'

    name += ''.join(map(str,(range(RUN_PROCESS_KEY_STARTS, RUN_PROCESS_KEY_ENDS+1))))
    name +='.txt'
    out_file = open(config.dir_output + name, 'w+')
    out_file.write(header)
    for f_key in range(RUN_PROCESS_KEY_STARTS, RUN_PROCESS_KEY_ENDS+1):
        config.logger.info('loading dumps for configuration: ' + str(f_key))
        try:
            for ds1 in datasets:
                horus_m4_path_ds1 = ds1[1].replace('.horusx', '.horus4')
                horus_m4_name_ds1 = ds1[0]
                dump_name = SET_MASK % (horus_m4_name_ds1, str(f_key))

                dump_full_path_ds1_sentence = os.path.dirname(os.path.realpath(horus_m4_path_ds1)) + '/' + \
                                              dump_name.replace('.pkl', '.sentence.pkl')
                dump_full_path_ds1_token = os.path.dirname(os.path.realpath(horus_m4_path_ds1)) + '/' + \
                                           dump_name.replace('.pkl', '.token.pkl')
                dump_full_path_ds1_crf = os.path.dirname(os.path.realpath(horus_m4_path_ds1)) + '/' + \
                                         dump_name.replace('.pkl', '.crf.pkl')

                if not os.path.isfile(dump_full_path_ds1_sentence):
                    config.logger.info(dump_full_path_ds1_sentence)
                    config.logger.error(' -- configuration file does not exist! check its creation')
                    raise Exception
                else:
                    config.logger.debug('loading: ' + dump_name + ' dump files')

                    with open(dump_full_path_ds1_sentence, 'rb') as input:
                        file_name, f_key, X1_sentence, Y1_sentence = pickle.load(input)

                    with open(dump_full_path_ds1_token, 'rb') as input:
                        file_name, f_key, X1_token, Y1_token = pickle.load(input)

                    with open(dump_full_path_ds1_crf, 'rb') as input:
                        file_name, f_key, X1_crf, Y1_crf = pickle.load(input)


                    #_set_name = SET_MASK % (ds1, str(f_key))
                    ##_file = config.dir_output + experiment_folder + _set_name
                    ##config.logger.info('ds1: loading [%s]: %s' % (ds1_name, _file))
                    ##with open(_file, 'rb') as input:
                    #    #shaped = pickle.load(input)
                    #ds1_config_name = dump_configs[_set_name][0]
                    #ds1_key = dump_configs[_set_name][1]
                    #X1_sentence = dump_configs[_set_name][2]
                    #Y1_sentence = dump_configs[_set_name][3]
                    #X1_token = dump_configs[_set_name][4]
                    #Y1_token = dump_configs[_set_name][5]
                    #X1_crf = dump_configs[_set_name][6]
                    #_Y1_sentence = dump_configs[_set_name][7]
                    #pca = PCA(n_components=50)
                    #X1_token_PCA = pca.fit(X1_token)
                    for ds2 in datasets:

                        horus_m4_path_ds2 = ds2[1].replace('.horusx', '.horus4')
                        horus_m4_name_ds2 = ds2[0]
                        dump_name = SET_MASK % (horus_m4_name_ds2, str(f_key))

                        dump_full_path_ds2_sentence = os.path.dirname(
                            os.path.realpath(horus_m4_path_ds2)) + '/' + dump_name.replace('.pkl', '.sentence.pkl')
                        dump_full_path_ds2_token = os.path.dirname(
                            os.path.realpath(horus_m4_path_ds2)) + '/' + dump_name.replace('.pkl', '.token.pkl')
                        dump_full_path_ds2_crf = os.path.dirname(
                            os.path.realpath(horus_m4_path_ds2)) + '/' + dump_name.replace('.pkl', '.crf.pkl')


                        if not os.path.isfile(dump_full_path_ds2_sentence):
                            config.logger.info(dump_full_path_ds2_sentence)
                            config.logger.error(' -- configuration file does not exist! check its creation')
                            raise Exception
                        else:
                            config.logger.info('%s -> %s' % (horus_m4_name_ds1, horus_m4_name_ds2))
                            if horus_m4_name_ds1 != horus_m4_name_ds2:
                                config.logger.debug('loading: ' + dump_name + ' dump files')

                                with open(dump_full_path_ds2_sentence, 'rb') as input:
                                    file_name, f_key, X2_sentence, Y2_sentence = pickle.load(input)

                                with open(dump_full_path_ds2_token, 'rb') as input:
                                    file_name, f_key, X2_token, Y2_token = pickle.load(input)

                                with open(dump_full_path_ds2_crf, 'rb') as input:
                                    file_name, f_key, X2_crf, Y2_crf = pickle.load(input)


                            if horus_m4_name_ds1 != horus_m4_name_ds2:
                                #_set_name = SET_MASK % (ds2_name, str(f_key))
                                ##_file = config.dir_output + experiment_folder + _set_name
                                ##config.logger.info('ds2: loading [%s]: %s' % (ds2_name, _file))
                                ##with open(_file, 'rb') as input:
                                ##    shaped = pickle.load(input)
                                #ds2_config_name = dump_configs[_set_name][0]
                                #ds2_key = dump_configs[_set_name][1]
                                #X2_sentence = dump_configs[_set_name][2]
                                #Y2_sentence = dump_configs[_set_name][3]
                                #X2_token = dump_configs[_set_name][4]
                                #Y2_token = dump_configs[_set_name][5]
                                #X2_crf = dump_configs[_set_name][6]
                                #_Y2_sentence = dump_configs[_set_name][7]

                                if (X2_token is None or X2_token.empty or X2_token.empty) is True:
                                    raise Exception('X_token error!')

                                # ---------------------------------------------------------- META ----------------------------------------------------------
                                # _conf = MEXConfiguration(id=len(_meta.configurations) + 1, horus_enabled=int(horus_feat),
                                #                         dataset_train=ds1[0], dataset_test=ds2[0] ,features=ds1[1], cross_validation=0)
                                # --------------------------------------------------------------------------------------------------------------------------
                                if runDT is True:
                                    m = _dt.fit(X1_token, Y1_token)
                                    ypr = m.predict(X2_token)
                                    # print(skmetrics.classification_report(Y2_token , ypr, labels=PLO_KLASSES.keys(), target_names=PLO_KLASSES.values(), digits=3))
                                    P, R, F, S = \
                                        sklearn.metrics.precision_recall_fscore_support(Y2_token, np.array(ypr).astype(int),
                                                                                        labels=definitions.PLO_index2label.keys())
                                    for k in range(len(P)):
                                        out_file.write(line % ('False', str(f_key), '1', definitions.PLO_index2label.get(k + 1),
                                                               P[k], R[k], F[k], str(S[k]), 'DT', horus_m4_name_ds1, horus_m4_name_ds2, 'NER'))

                                    # average
                                    P_avg, R_avg, F_avg, S_avg = sklearn.metrics.precision_recall_fscore_support(Y2_token, np.array(ypr).astype(int),
                                                                                        labels=definitions.PLO_index2label.keys(), average='weighted')
                                    out_file.write(line % (
                                    'False', str(f_key), '1', 'average', P_avg, R_avg, F_avg, 0, 'DT', horus_m4_name_ds1, horus_m4_name_ds2, 'NER'))

                                    # entity detection only
                                    ypr_bin = [1 if x in definitions.PLO_index2label.keys() else 0 for x in ypr]
                                    y2_bin = [1 if x in definitions.PLO_index2label.keys() else 0 for x in Y2_token]
                                    P, R, F, S = sklearn.metrics.precision_recall_fscore_support(y2_bin, ypr_bin)
                                    for k in range(len(P)):
                                        out_file.write(line % ('False', str(f_key), '1', k,
                                                               P[k], R[k], F[k], str(S[k]), 'DT', horus_m4_name_ds1, horus_m4_name_ds2, 'NED'))

                                    # ---------------------------------------------------------- META ----------------------------------------------------------
                                    # _ex = MEXExecution(id=len(_conf.executions) + 1, alg='DT', phase='test', random_state=r[d])
                                    # P, R, F, S = sklearn.metrics.precision_recall_fscore_support(ds2[1][3] , ypr,
                                    #                                                             labels=sorted_labels.keys(),
                                    #                                                             average=None)
                                    # for k in sorted_labels.keys():
                                    #    _ex.add_performance(MEXPerformance(k, P[k], R[k], F[k], 0.0, S[k]))
                                    # _conf.add_execution(_ex)
                                    # _meta.add_configuration(_conf)
                                    # --------------------------------------------------------------------------------------------------------------------------

                                if runCRF is True:
                                    m = _crf.fit(X1_crf, Y1_sentence)
                                    ypr = m.predict(X2_crf)
                                    #print(metrics.flat_classification_report(Y2_sentence, ypr, labels=sorted_labels.keys(), target_names=sorted_labels.values(), digits=3))
                                    _ypr = np.array([tag for row in ypr for tag in row])
                                    P, R, F, S = sklearn.metrics.precision_recall_fscore_support(Y2_sentence, _ypr,
                                                                                                 labels=definitions.PLO_index2label.values())
                                    for k in range(len(P)):
                                        out_file.write(line % (
                                        'False', str(f_key), '1', definitions.PLO_index2label.get(k + 1), P[k], R[k], F[k], str(S[k]),
                                        'CRF', horus_m4_name_ds1, horus_m4_name_ds2, 'NER'))

                                    # average
                                    P_avg, R_avg, F_avg, S_avg = sklearn.metrics.precision_recall_fscore_support(
                                        Y2_sentence, _ypr,
                                        labels=definitions.PLO_index2label.keys(), average='weighted')
                                    out_file.write(line % (
                                        'False', str(f_key), '1', 'average', P_avg, R_avg, F_avg, 0, 'CRF',
                                        horus_m4_name_ds1, horus_m4_name_ds2, 'NER'))

                                    # entity detection only
                                    ypr_bin = [1 if x in definitions.PLO_index2label.values() else 0 for x in _ypr]
                                    y2_bin = [1 if x in definitions.PLO_index2label.values() else 0 for x in Y2_sentence]
                                    P, R, F, S = sklearn.metrics.precision_recall_fscore_support(y2_bin, ypr_bin)
                                    for k in range(len(P)):
                                        out_file.write(line % (
                                            'False', str(f_key), '1', k, P[k], R[k], F[k], str(S[k]), 'CRF', horus_m4_name_ds1, horus_m4_name_ds2, 'NED'))


                                    m = _crf2.fit(X1_crf, Y1_sentence)
                                    ypr = m.predict(X2_crf)
                                    _ypr = np.array([tag for row in ypr for tag in row])
                                    P, R, F, S = sklearn.metrics.precision_recall_fscore_support(Y2_sentence, _ypr,
                                                                                                 labels=definitions.PLO_index2label.values())
                                    for k in range(len(P)):
                                        out_file.write(line % (
                                        'False', str(f_key), '1', definitions.PLO_index2label.get(k + 1), P[k], R[k], F[k], str(S[k]),
                                        'CRF_PA', horus_m4_name_ds1, horus_m4_name_ds2, 'NER'))

                                    # entity detection only
                                    ypr_bin = [1 if x in definitions.PLO_index2label.values() else 0 for x in _ypr]
                                    P, R, F, S = sklearn.metrics.precision_recall_fscore_support(y2_bin, ypr_bin)
                                    for k in range(len(P)):
                                        out_file.write(line % (
                                            'False', str(f_key), '1', k, P[k], R[k], F[k], str(S[k]), 'CRF_PA', horus_m4_name_ds1, horus_m4_name_ds2, 'NED'))

                                if runLSTM is True:
                                    print(1)
                                    #max_of_sentences = max(maxlen_1, maxlen_2)
                                    #X2_lstm = pad_sequences(X2_lstm, maxlen=max_of_sentences)
                                    #y2_lstm = pad_sequences(y2_lstm, maxlen=max_of_sentences)
                                    #run_lstm(X1_lstm, X2_lstm, y1_lstm, y2_lstm, max_features_1, max_features_2, out_size_1,
                                    #         embedding_size, hidden_size, batch_size, epochs, verbose, max_of_sentences)
                            else:
                                # same dataset (cross-validation)

                                # ---------------------------------------------------------- META ----------------------------------------------------------
                                # _conf = MEXConfiguration(id=len(_meta.configurations)+1, horus_enabled=int(horus_feat),
                                #                                dataset_train=ds1[0], dataset_test=ds1[0], dataset_validation=None, features=None, cross_validation=1)
                                # --------------------------------------------------------------------------------------------------------------------------
                                if X1_token.empty is True:
                                    raise Exception('X1_token is empty!')

                                for d in range(len(r)):
                                    if runDT is True:
                                        Xtr, Xte, ytr, yte = train_test_split(X1_token, Y1_token, test_size=ds_test_size,
                                                                              random_state=r[d])
                                        m = _dt.fit(np.array(Xtr).astype(float), np.array(ytr).astype(int))
                                        # print(m.feature_importances_)
                                        ypr = m.predict(np.array(Xte).astype(float))
                                        # print(skmetrics.classification_report(np.array(yte).astype(int), np.array(ypr).astype(int), labels=definitions.PLO_KLASSES.keys(), target_names=definitions.PLO_KLASSES.values(), digits=3))
                                        P, R, F, S = sklearn.metrics.precision_recall_fscore_support(np.array(yte).astype(int),
                                                                                                     np.array(ypr).astype(int),
                                                                                                     labels=definitions.PLO_index2label.keys())
                                        for k in range(len(P)):
                                            out_file.write(line % ('True', str(f_key), str(d + 1), definitions.PLO_index2label.get(k + 1),
                                                        P[k], R[k], F[k], str(S[k]), 'DT', horus_m4_name_ds1, horus_m4_name_ds2, 'NER'))

                                        # average
                                        P_avg, R_avg, F_avg, S_avg = sklearn.metrics.precision_recall_fscore_support(np.array(yte).astype(int),np.array(ypr).astype(int), labels=definitions.PLO_index2label.keys(), average='weighted')
                                        out_file.write(line % ('True', str(f_key), '1', 'average', P_avg, R_avg, F_avg, 0, 'DT', horus_m4_name_ds1, horus_m4_name_ds2, 'NER'))

                                        # entity detection only
                                        ypr_bin = [1 if x in definitions.PLO_index2label.keys() else 0 for x in ypr]
                                        y2_bin = [1 if x in definitions.PLO_index2label.keys() else 0 for x in yte]
                                        P, R, F, S = sklearn.metrics.precision_recall_fscore_support(y2_bin, ypr_bin)
                                        for k in range(len(P)):
                                            out_file.write(line % ('True', str(f_key), str(d + 1), k, P[k], R[k], F[k], str(S[k]),
                                                                   'DT', horus_m4_name_ds1, horus_m4_name_ds2, 'NED'))

                                        # ---------------------------------------------------------- META ----------------------------------------------------------
                                        # _ex = MEXExecution(id=len(_conf.executions) + 1, model='', alg='DT', phase='test', random_state=r[d])
                                        # P, R, F, S = sklearn.metrics.precision_recall_fscore_support(yte, ypr,
                                        #                                                             labels=sorted_labels.keys(),
                                        #                                                             average=None)
                                        # for k in sorted_labels.keys():
                                        #    _ex.add_performance(MEXPerformance(k, P[k], R[k], F[k], 0.0, S[k]))
                                        # _conf.add_execution(_ex)
                                        # _meta.add_configuration(_conf)
                                        # --------------------------------------------------------------------------------------------------------------------------

                                    if runCRF is True:
                                        Xtr, Xte, ytr, yte = \
                                            train_test_split(X1_crf, Y1_sentence, test_size=ds_test_size, random_state=r[d])

                                        m = _crf.fit(Xtr, ytr)
                                        ypr = m.predict(Xte)
                                        _ypr = np.array([tag for row in ypr for tag in row])
                                        _yte = np.array([tag for row in yte for tag in row])
                                        #print(metrics.flat_classification_report(yte, ypr, labels=sorted_labels.keys(), target_names=sorted_labels.values(), digits=3))
                                        P, R, F, S = sklearn.metrics.precision_recall_fscore_support(_yte, _ypr,
                                                                                                     labels=definitions.PLO_index2label.values())
                                        for k in range(len(P)):
                                            out_file.write(line % (
                                                'True', str(f_key), str(d + 1), definitions.PLO_index2label.get(k + 1), P[k], R[k],
                                                F[k],
                                                str(S[k]), 'CRF', horus_m4_name_ds1, horus_m4_name_ds2, 'NER'))

                                        # average
                                        P_avg, R_avg, F_avg, S_avg = sklearn.metrics.precision_recall_fscore_support(_yte, _ypr,labels=definitions.PLO_index2label.keys(), average='weighted')
                                        out_file.write(line % ('True', str(f_key), '1', 'average', P_avg, R_avg, F_avg, 0, 'CRF',horus_m4_name_ds1, horus_m4_name_ds2, 'NER'))

                                        # entity detection only
                                        ypr_bin = [1 if x in definitions.PLO_index2label.values() else 0 for x in _ypr]
                                        y2_bin = [1 if x in definitions.PLO_index2label.values() else 0 for x in _yte]
                                        P, R, F, S = sklearn.metrics.precision_recall_fscore_support(y2_bin, ypr_bin)
                                        for k in range(len(P)):
                                            out_file.write(line % (
                                                'True', str(f_key), str(d + 1), k, P[k], R[k], F[k], str(S[k]), 'CRF', horus_m4_name_ds1, horus_m4_name_ds2, 'NED'))

                                        m = _crf2.fit(Xtr, ytr)
                                        ypr = m.predict(Xte)
                                        _ypr = np.array([tag for row in ypr for tag in row])
                                        _yte = np.array([tag for row in yte for tag in row])
                                        P, R, F, S = sklearn.metrics.precision_recall_fscore_support(_yte, _ypr,
                                                                                                     labels=definitions.PLO_index2label.values())
                                        for k in range(len(P)):
                                            out_file.write(line % (
                                                'True', str(f_key), str(d + 1), definitions.PLO_index2label.get(k + 1), P[k], R[k],
                                                F[k],
                                                str(S[k]), 'CRF_PA', horus_m4_name_ds1, horus_m4_name_ds2, 'NER'))

                                        # average
                                        P_avg, R_avg, F_avg, S_avg = sklearn.metrics.precision_recall_fscore_support(
                                            _yte, _ypr, labels=definitions.PLO_index2label.keys(),
                                            average='weighted')
                                        out_file.write(line % (
                                        'True', str(f_key), '1', 'average', P_avg, R_avg, F_avg, 0, 'CRF_PA',
                                        horus_m4_name_ds1, horus_m4_name_ds2, 'NER'))

                                        # entity detection only
                                        ypr_bin = [1 if x in definitions.PLO_index2label.values() else 0 for x in _ypr]
                                        y2_bin = [1 if x in definitions.PLO_index2label.values() else 0 for x in _yte]
                                        P, R, F, S = sklearn.metrics.precision_recall_fscore_support(y2_bin, ypr_bin)
                                        for k in range(len(P)):
                                            out_file.write(line % (
                                                'True', str(f_key), str(d + 1), k, P[k], R[k], F[k], str(S[k]), 'CRF_PA', horus_m4_name_ds1, horus_m4_name_ds2, 'NED'))

                                        # ---------------------------------------------------------- META ----------------------------------------------------------
                                        # _ex = MEXExecution(id=len(_conf.executions)+1, model='', alg='CRF', phase='test', random_state=r[d])
                                        # P, R, F, S = sklearn.metrics.precision_recall_fscore_support(yte, ypr, labels=sorted_labels.keys(), average=None)
                                        # for k in sorted_labels.keys():
                                        #    _ex.add_performance(MEXPerformance(k, P[k], R[k], F[k], 0.0, S[k]))
                                        # _conf.add_execution(_ex)
                                        # _meta.add_configuration(_conf)
                                        # --------------------------------------------------------------------------------------------------------------------------

                                    if runLSTM is True:
                                        print(1)
                                        #Xtr, Xte, ytr, yte = train_test_split(X1_lstm, y1_lstm, test_size=ds_test_size,
                                        #                                      random_state=42)  # 352|1440
                                        #run_lstm(Xtr, Xte, ytr, yte, max_features_1, max_features_2, out_size_1, embedding_size,
                                        #         hidden_size, batch_size, epochs, verbose, maxlen_1)

                        out_file.flush()
        except Exception as e:
            config.logger.error(repr(e))
    out_file.close()
    #with open(_label + '.meta', 'wb') as handle:
    #    pickle.dump(_meta, handle, protocol=pickle.HIGHEST_PROTOCOL)

def main():
    parser = argparse.ArgumentParser(
        description='Creates a benchmark pipeline for different classifiers /datasets comparing performance *with* '
                    'and *without* the HORUS features list',
        prog='benchmarking.py',
        usage='%(prog)s [options]',
        epilog='http://horus-ner.org')

    #parser.add_argument('--ds', '--datasets', nargs='+', default='2015.conll.freebase.horus 2016.conll.freebase.ascii.txt.horus ner.txt.horus emerging.test.annotated.horus', help='the horus datasets files: e.g.: ritter.horus wnut15.horus')
    #parser.add_argument('--ds', '--datasets', nargs='+', default='test.horus')
    parser.add_argument('--ds', '--datasets', nargs='+', default='2015.conll.freebase.horus')
    parser.add_argument('--exp', '--experiment_folder', default='EXP_005', action='store_true', required=False, help='the sub-folder name where the input file is located')
    parser.add_argument('--dt', '--rundt', action='store_true', required=False, default=0, help='benchmarks DT')
    parser.add_argument('--crf', '--runcrf', action='store_true', required=False, default=1, help='benchmarks CRF')
    parser.add_argument('--lstm', '--runlstm', action='store_true', required=False, default=0, help='benchmarks LSTM')
    parser.add_argument('--stanford', '--runstanford', action='store_true', required=False, default=0, help='benchmarks Stanford NER')

    parser.print_help()
    args = parser.parse_args()
    time.sleep(1)

    try:
        create_benchmark_dump_files()
        exit(0)
        temp = [['ritter.train', config.dir_datasets + 'Ritter/ner.txt.horusx']]

        benchmark(experiment_folder=args.exp, datasets=temp, runCRF=bool(args.crf), runDT=bool(args.dt),
                  runLSTM=bool(args.lstm), runSTANFORD_NER=bool(args.stanford))
    except:
        raise

if __name__ == "__main__":
    main()