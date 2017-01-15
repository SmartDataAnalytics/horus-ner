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

more info at: https://github.com/dnes85/horus-models

"""

# Author: Esteves <diegoesteves@gmail.com>
# Version: 1.0
# Version Label: HORUS_NER_2016_1.0
# License: BSD 3 clause
import csv
import heapq
import os
import json

import zlib

import numpy
from microsofttranslator import Translator
from textblob import TextBlob
import langdetect
import nltk
import sqlite3
import sys
from optparse import OptionParser
from time import gmtime, strftime
import requests
from nltk.tokenize import sent_tokenize
from bingAPI1 import bing_api, bing_api2
from nltk.tag.stanford import StanfordPOSTagger

from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
import cv2
from langdetect import detect

from core import HorusCore

print cv2.__version__

horus = HorusCore('horus.ini')
english_vocab = None
ner_ritter = ['B-company', 'B-person', 'I-person', 'B-geo-loc', 'I-company', 'I-geo-loc']

ner_ritter_per = ['B-person', 'I-person']
ner_ritter_org = ['B-company', 'I-company']
ner_ritter_loc = ['B-geo-loc', 'I-geo-loc']

klasses = {1:"LOC",2:"ORG",3:"PER"}

translator = Translator(horus.translation_id, horus.translation_secret)

from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
tfidf_transformer = TfidfTransformer()


detect = cv2.xfeatures2d.SIFT_create()
extract = cv2.xfeatures2d.SIFT_create()
flann_params = dict(algorithm=1, trees=5)
flann = cv2.FlannBasedMatcher(flann_params, {})
extract_bow = cv2.BOWImgDescriptorExtractor(extract, flann)
from sklearn.externals import joblib

horus.log.info('------------------------------------------------------------------')
horus.log.info('::                     HORUS NER 0.1 alpha                      ::')
horus.log.info('------------------------------------------------------------------')
horus.log.info(':: loading components...')

horus.log.info(':: loading horus ORG model')
svm_logo = joblib.load(horus.models_cv_org)
horus.log.info(':: loading horus ORG vocabulary')
voc_org = joblib.load(horus.models_cv_org_dict)

horus.log.info(':: loading horus LOC models')

svm_loc1 = joblib.load(horus.models_cv_loc1)
svm_loc2 = joblib.load(horus.models_cv_loc2)
svm_loc3 = joblib.load(horus.models_cv_loc3)
svm_loc4 = joblib.load(horus.models_cv_loc4)
svm_loc5 = joblib.load(horus.models_cv_loc5)
svm_loc6 = joblib.load(horus.models_cv_loc6)
svm_loc7 = joblib.load(horus.models_cv_loc7)
svm_loc8 = joblib.load(horus.models_cv_loc8)
svm_loc9 = joblib.load(horus.models_cv_loc9)
svm_loc10 = joblib.load(horus.models_cv_loc10)

horus.log.info(':: loading horus ORG vocabularies')
voc_loc_1 = joblib.load(horus.models_cv_loc_1_dict)
voc_loc_2 = joblib.load(horus.models_cv_loc_2_dict)
voc_loc_3 = joblib.load(horus.models_cv_loc_3_dict)
voc_loc_4 = joblib.load(horus.models_cv_loc_4_dict)
voc_loc_5 = joblib.load(horus.models_cv_loc_5_dict)
voc_loc_6 = joblib.load(horus.models_cv_loc_6_dict)
voc_loc_7 = joblib.load(horus.models_cv_loc_7_dict)
voc_loc_8 = joblib.load(horus.models_cv_loc_8_dict)
voc_loc_9 = joblib.load(horus.models_cv_loc_9_dict)
voc_loc_10 = joblib.load(horus.models_cv_loc_10_dict)


horus.log.info(':: loading horus text analysis model')
text_checking_model = joblib.load(horus.models_text)


horus.log.info(':: connecting to horus db...')
conn = sqlite3.connect(horus.database_db)
horus.log.info(':: done')


def main():

    op = OptionParser(usage='usage: %prog [options] arguments')

    op.add_option("--input_text", dest="input_text",
                  help="The text to be annotated")

    op.add_option("--input_file", dest="input_file",
                  help="The file to be annotated")

    op.add_option("--ds_format", dest="ds_format", default=0,
                  help="The format to be annotated [0 = free text (default), 1 = Ritter]")

    op.add_option("--output_file", dest="output_file", default="horus_out",
                  help="The output file")

    op.add_option("--output_format", dest="output_format", default="json",
                  help="The output file type")

    (opts, args) = op.parse_args()
    print(__doc__)
    op.print_help()

    if not opts.input_text and not opts.input_file:
        op.error('inform either an [input_text] or [input_file] as parameter!')

    horus_matrix = []
    horus.log.info(':: downloading models ...')
    nltk.download('averaged_perceptron_tagger')
    nltk.download('maxent_ne_chunker')

    #horus.log.info(':: loading english vocabulary ...')
    #english_vocab = set(w.lower() for w in nltk.corpus.words.words())

    # postagger_stanford_en = \
    #    StanfordPOSTagger(model_filename=horus.model_stanford_filename, path_to_jar=horus.model_stanford_path_jar)
    # text_tokens_stanford_en = postagger_stanford_en.tag(text.split())

    horus.log.info('------------------------------------------------------------------')

    # 0 = text (parameter of reading file) / 1 = ritter
    if int(opts.ds_format) == 0:
        text = ''
        if opts.input_text is not None:
            text = opts.input_text.strip('"\'')
            horus.log.info(':: processing text')
        elif opts.input_file is not None:
            f = open(opts.input_file, 'r')
            text = f.readlines()
            horus.log.info(':: processing input file')
        else:
            raise Exception("err: missing text to be annotated")
        sent_tokenize_list = process_input_text(text)

    elif int(opts.ds_format) == 1:  # ritter
        if opts.input_file is None:
            raise Exception("Provide an input file (ritter format) to be annotated")
        else:
            horus.log.info(':: loading Ritter ds')
            sent_tokenize_list = process_ritter_ds(opts.input_file)

    horus.log.info(':: caching %s sentence(s)' % str(len(sent_tokenize_list)))
    # hasEntityNER (1=yes,0=dunno,-1=no), sentence, words[], tags_NER[], tags_POS[], tags_POS_UNI[]
    horus_matrix = cache_sentence(int(opts.ds_format), sent_tokenize_list)
    horus.log.info(':: done!')

    horus.log.info(':: caching results...')
    cache_results(horus_matrix)
    horus.log.info(':: done!')

    #  updating horus matrix
    # 0 = is_entity?,    1 = index_sent,   2 = index_word, 3 = word/term,
    # 4 = pos_universal, 5 = pos,          6 = ner       , 7 = compound? ,
    # 8 = compound_size, 9 = id_term_txt, 10 = id_term_img
    horus.log.info(':: detecting %s objects...' % len(horus_matrix))
    detect_objects(horus_matrix)
    horus.log.info(':: done!')

    conn.close()

    horus.log.info(':: updating compounds...')
    update_compound_predictions(horus_matrix)
    horus.log.info(':: done!')

    # horus.log.info(horus_matrix)
    header = ["IS_ENTITY?", "ID_SENT", "ID_WORD", "WORD/TERM", "POS_UNI", "POS", "NER", "COMPOUND", "COMPOUND_SIZE", "ID_TERM_TXT", "ID_TERM_IMG",
              "TOT_IMG", "TOT_CV_LOC", "TOT_CV_ORG", "TOT_CV_PER", "DIST_CV_I", "PL_CV_I", "CV_KLASS", "TOT_RESULTS_TX", "TOT_TX_LOC", "TOT_TX_ORG",
              "TOT_TX_PER", "TOT_ERR_TRANS", "DIST_TX_I", "TX_KLASS", "HORUS_KLASS"]

    if int(opts.ds_format) == 0:
        print_annotated_sentence(horus_matrix)

    horus.log.info(':: exporting metadata...')
    if opts.output_format == 'json':
        with open(opts.output_file + '.json', 'wb') as outfile:
            json.dump(horus_matrix, outfile)
    elif opts.output_format == 'csv':
        horus_csv = open(opts.output_file + '.csv', 'wb')
        wr = csv.writer(horus_csv, quoting=csv.QUOTE_ALL)
        wr.writerow(header)
        wr.writerows(horus_matrix)
    horus.log.info(':: done!')

    horus.log.info(':: HORUS - finished')


def print_annotated_sentence(horus_matrix):
    '''
    read the horus matrix and prints the annotated sentences
    :param horus_matrix:
    :return: output of annotated sentence
    '''
    x = ''
    id_sent_aux = horus_matrix[0][1]
    for term in horus_matrix:
        if term[7] == 0:
            if id_sent_aux != term[1]:
                #horus.log.info(':: sentence ' + str(id_sent_aux) + ': ' + x)
                horus.log.info(':: sentence: ' + x)
                id_sent_aux = term[1]
                x = ' ' + str(term[3]) + '/' + str(term[25])
            else:
                x += ' ' + str(term[3]) + '/' + str(term[4]) + '/' + str(term[5]) + '/' + str(term[25])
                # x += ' ' + str(term[3]) + '/' + str(term[25])

    horus.log.info(':: sentence: ' + x)


def cache_sentence_ritter(sentence_list):
    horus_matrix = []
    horus.log.debug(':: caching Ritter dataset...:')
    i_sent, i_word = 1, 1
    compound, prev_tag = '', ''
    sent_with_ner = 0
    token_ok = 0
    compound_ok = 0
    for sent in sentence_list:

        horus.log.debug(':: processing sentence: ' + sent[1])

        # processing compounds
        if sent[0] == 1:
            sent_with_ner += 1
            for tag in sent[3]:  # list of NER tags
                word = sent[2][i_word - 1]
                if tag in ner_ritter:  # only desired tags
                    if prev_tag.replace('B-', '').replace('I-', '') == tag.replace('B-', '').replace('I-', ''):
                        compound += prev_word + ' ' + word + ' '
                prev_word = word
                prev_tag = tag
                i_word += 1
            compound = compound[:-1]

            if compound != '':
                compound_ok+=1
                horus_matrix.append([1, i_sent, i_word - len(compound.split(' ')), compound, '', '', '', 1, len(compound.split(' '))])
                compound = ''
            prev_tag = ''
            prev_word = ''

        # processing tokens

        #  transforming to horus matrix
        # 0 = is_entity?,    1 = index_sent, 2 = index_word, 3 = word/term,
        # 4 = pos_universal, 5 = pos,        6 = ner       , 7 = compound? ,
        # 8 = compound_size

        i_word = 1
        for k in range(len(sent[2])): # list of NER tags
            is_entity = 1 if sent[3] in ner_ritter else 0
            horus_matrix.append([is_entity, i_sent, i_word, sent[2][k], sent[5][k], sent[4][k], sent[3][k], 0, 0])
            i_word += 1
            if is_entity:
                token_ok += 1

        db_save_sentence(sent[1], '-', '-', str(sent[3]))
        i_sent += 1
        i_word = 1

    horus.log.debug(':: done! total of sentences = %s, tokens = %s and compounds = %s'
                 % (str(sent_with_ner), str(token_ok), str(compound_ok)))

    return horus_matrix


def tokenize_and_pos(sentence, tagset=''):
    horus.log.debug(':: processing sentence: ' + sentence)
    tokens = nltk.word_tokenize(sentence)
    horus.log.debug('---------- ' + str(tokens))
    tagged = nltk.pos_tag(tokens, tagset=tagset)
    return tokens, tagged


def cache_sentence(sentence_format, sentence_list):
    if sentence_format == 0:
        horus_matrix = cache_sentence_free_text(sentence_list)
    elif sentence_format == 1:
        horus_matrix = cache_sentence_ritter(sentence_list)
    return horus_matrix


def cache_sentence_free_text(sentence_list):

    i_sent, i_word = 1, 1
    horus_matrix = []
    horus.log.debug(':: chunking pattern ...')
    pattern = "NP:{<NN|NNP|NNS|NNPS>+}"
    cp = nltk.RegexpParser(pattern)
    compounds = '|'

    for sent in sentence_list:
        #tokens, tagged = tokenize_and_pos(sent[1])
        #horus.log.info(':: tags: ' + str(tagged))
        ## entities = nltk.chunk.ne_chunk(tagged)

        #  add compounds of given sentence

        aux = 0
        toparse = []
        for obj in sent[2]:
            toparse.append(tuple([obj, sent[4][aux]]))
            aux+=1
        t = cp.parse(toparse)
        i_word = 1
        for item in t:
            is_entity = 1 if (sent[0] == 1 and sent[3][i_word - 1] != 'O') else -1
            if type(item) is nltk.Tree:  # that's a compound
                compound = ''
                for tk in item:
                    compound += tk[0] + ' '
                    i_word += 1
                if len(item) > 1:
                    horus_matrix.append([is_entity, i_sent, i_word - len(item), compound[:len(compound) - 1], '', '', '', 1, len(item)])
                    compounds += compound[:len(compound) - 1] + '|'
                compound = ''

        #  transforming to horus matrix
        # 0 = is_entity?,    1 = index_sent, 2 = index_word, 3 = word/term,
        # 4 = pos_universal, 5 = pos,        6 = ner       , 7 = compound? ,
        # 8 = compound_size
        i_word = 1
        for k in range(len(sent[2])):
            is_entity = 1 if (sent[0] == 1 and sent[3][k] != 'O') else -1
            horus_matrix.append([is_entity, i_sent, i_word, sent[2][k], sent[5][k], sent[4][k], sent[3][k], 0, 0])
            i_word += 1

        db_save_sentence(sent[1], ' '.join(sent[5]), compounds, ' '.join(sent[2]))

        i_sent += 1

    return horus_matrix


def db_save_sentence(sent, tagged, compound, tokens):
    c = conn.cursor()
    conn.text_factory = str
    sql = """SELECT id FROM HORUS_SENTENCES WHERE sentence = ? """
    c.execute(sql, (sent,))
    res_sent = c.fetchone()
    if res_sent is None:
        horus.log.info(':: caching sentence: ' + sent)
        #buffer(zlib.compress
        row = (str(sent), str(tagged), str(compound), str(tokens))
        sql = """INSERT INTO HORUS_SENTENCES(sentence, tagged, compounds, tokens)
                         VALUES(?,?,?,?)"""
        horus.log.debug(sql)
        c.execute(sql, row)
        conn.commit()
        horus.log.debug(':: done: ' + sent)
    else:
        horus.log.debug(':: sentence is already cached')


def download_image_local(image_url, image_type, thumbs_url, thumbs_type, term_id, id_ner_type, seq):
    val = URLValidator()
    auxtype = None
    try:
        val(thumbs_url)
        try:
            img_data = requests.get(thumbs_url).content
            with open('%s%s_%s_%s.%s' % (horus.cache_img_folder, term_id, id_ner_type, seq, thumbs_type.split('/')[1]), 'wb') as handler:
                handler.write(img_data)
                auxtype = thumbs_type.split('/')[1]
        except Exception as error:
            print('-> error: ' + repr(error))
    except ValidationError, e:
        horus.log.error('No thumbs img here...', e)
        try:
            img_data = requests.get(image_url).content
            with open('%s%s_%s_%s.%s' % (horus.cache_img_folder, term_id, id_ner_type, seq, image_type.split('/')[1]), 'wb') as handler:
                auxtype = image_type.split('/')[1]
                handler.write(img_data)
        except Exception as error:
            print('-> error: ' + repr(error))
    return auxtype


def cache_results(horus_matrix):
    try:
        auxc = 1
        horus.log.info(':: caching horus_matrix: ' + str(len(horus_matrix)))

        for item in horus_matrix:
            horus.log.info(':: item %s - %s ' % (str(auxc), str(len(horus_matrix))))
            term = item[3]
            if item[4] == 'NOUN' or item[7] == 1:
                horus.log.debug(':: caching [%s] ...' % term)
                c = conn.cursor()

                # checking if we have searched that before (might be the case of had used
                # different configurations, or different search engine, for instance.
                sql = """SELECT id FROM HORUS_TERM WHERE term = ?"""
                c.execute(sql, (term,))
                res_term = c.fetchone()
                if res_term is None:
                    horus.log.info(':: [%s] has not been cached before!' % term)
                    cterm = conn.execute("""INSERT INTO HORUS_TERM(term) VALUES(?)""", (term,))
                else:
                    cterm = res_term[0]

                # check if term (text) has been cached before
                # in case horus is extended to accept more than 1 search engine, this table should also
                # have it defined
                values = (term, horus.search_engine_api, 1, horus.search_engine_features_text)
                sql = """SELECT id
                         FROM HORUS_TERM_SEARCH
                         WHERE term = ? AND
                               id_search_engine = ? AND
                               id_search_type = ? AND
                               search_engine_features = ?"""
                c.execute(sql, values)
                res = c.fetchone()
                if res is None:
                    horus.log.info(':: [%s] caching - text' % term)
                    values = (term, cterm.lastrowid, horus.search_engine_api, 1,
                              horus.search_engine_features_text,
                              str(strftime("%Y-%m-%d %H:%M:%S", gmtime())),
                              horus.search_engine_tot_resources)
                    c = conn.execute("""INSERT into HORUS_TERM_SEARCH(term, id_term, id_search_engine, id_search_type,
                                                                      search_engine_features, query_date,
                                                                      query_tot_resource)
                                             VALUES(?, ?, ?, ?, ?, ?, ?)""", values)

                    id_term_search = c.lastrowid
                    item.extend([id_term_search])  # updating matrix
                    seq = 0
                    # get text
                    metaquery, result = bing_api2(term, api=horus.search_engine_key, source_type="Web",
                                                 top=horus.search_engine_tot_resources, format='json', market='en-US')
                    for web_result in result['d']['results']:
                        seq+=1
                        row = (id_term_search,
                               0,
                               web_result['ID'],
                               seq,
                               web_result['Url'],
                               web_result['Title'],
                               web_result['Description'],
                               '')
                        c.execute("""INSERT INTO HORUS_SEARCH_RESULT_TEXT (id_term_search,
                                                                                id_ner_type,
                                                                                search_engine_resource_id,
                                                                                result_seq,
                                                                                result_url,
                                                                                result_title,
                                                                                result_description,
                                                                                result_html_text)
                                          VALUES(?,?,?,?,?,?,?,?)""", row)

                        c.execute("""UPDATE HORUS_TERM_SEARCH
                                          SET metaquery = '%s'
                                          WHERE id = %s""" % (metaquery, id_term_search))

                    if seq == 0:
                        row = (id_term_search,
                               0,
                               '',
                               seq,
                               '',
                               '',
                               '',
                               '')
                        c.execute("""INSERT INTO HORUS_SEARCH_RESULT_TEXT (id_term_search,
                                                                           id_ner_type,
                                                                           search_engine_resource_id,
                                                                           result_seq,
                                                                           result_url,
                                                                           result_title,
                                                                           result_description,
                                                                           result_html_text)
                                                                  VALUES(?,?,?,?,?,?,?,?)""", row)

                        c.execute("""UPDATE HORUS_TERM_SEARCH
                                     SET metaquery = '%s'
                                     WHERE id = %s""" % (metaquery, id_term_search))

                    horus.log.debug(':: term [%s] cached (text)!' % term)
                    conn.commit()
                else:
                    item.extend(res)  # updating matrix
                    horus.log.debug(':: term %s is already cached (text)!' % term)

                values = (term, horus.search_engine_api, 2, horus.search_engine_features_text)
                c = conn.execute("""SELECT id
                                    FROM HORUS_TERM_SEARCH
                                    WHERE term = ? AND
                                          id_search_engine = ? AND
                                          id_search_type = ? AND
                                          search_engine_features = ?""", values)
                res = c.fetchone()
                if res is None:
                    horus.log.info(':: [%s] caching - image' % term)
                    values = (term, cterm.lastrowid if type(cterm) is not int else cterm, horus.search_engine_api, 2,
                               horus.search_engine_features_img,
                               str(strftime("%Y-%m-%d %H:%M:%S", gmtime())), horus.search_engine_tot_resources)
                    sql = """INSERT into HORUS_TERM_SEARCH(term, id_term, id_search_engine, id_search_type,
                                                           search_engine_features, query_date, query_tot_resource)
                                             VALUES(?,?,?,?,?,?,?)"""
                    c.execute(sql, values)
                    id_term_img = c.lastrowid
                    item.extend([id_term_img])  # updating matrix
                    seq = 0
                    # get images
                    metaquery, result = bing_api2(item[3], api=horus.search_engine_key, source_type="Image",
                                                 top=horus.search_engine_tot_resources, format='json')
                    for web_img_result in result['d']['results']:
                        horus.log.debug(':: downloading image [%s]' % (web_img_result['Title']))
                        seq += 1
                        auxtype = download_image_local(web_img_result['MediaUrl'],
                                             web_img_result['ContentType'],
                                             web_img_result['Thumbnail']['MediaUrl'],
                                             web_img_result['Thumbnail']['ContentType'],
                                             id_term_img,
                                             0,
                                             seq)
                        horus.log.debug(':: caching image result ...')
                        fname = ('%s_%s_%s.%s' % (str(id_term_img),  str(0),  str(seq),  str(auxtype)))
                        row = (id_term_img,
                               0,
                               web_img_result['ID'],
                               seq,
                               web_img_result['MediaUrl'],
                               web_img_result['Title'],
                               web_img_result['ContentType'],
                               web_img_result['Height'],
                               web_img_result['Width'],
                               web_img_result['Thumbnail']['MediaUrl'],
                               web_img_result['Thumbnail']['ContentType'],
                               fname)

                        sql = """INSERT INTO HORUS_SEARCH_RESULT_IMG (id_term_search,
                                                                      id_ner_type,
                                                                      search_engine_resource_id,
                                                                      result_seq,
                                                                      result_media_url,
                                                                      result_media_title,
                                                                      result_media_content_type,
                                                                      result_media_height,
                                                                      result_media_width,
                                                                      result_media_thumb_media_url,
                                                                      result_media_thumb_media_content_type,
                                                                      filename)
                                          VALUES(?,?,?,?,?,?,?,?,?,?,?,?)"""
                        c.execute(sql, row)

                        c.execute("""UPDATE HORUS_TERM_SEARCH
                                          SET metaquery = '%s'
                                          WHERE id = %s""" % (metaquery, id_term_img))

                    horus.log.debug(':: term [%s] cached (img)!' % term)
                    conn.commit()
                else:
                    horus.log.debug(':: term %s is already cached (img)!' % term)
                    item.extend(res)  # updating matrix

            auxc+=1
    except Exception as e:
        horus.log.error(':: an error has occurred: ', e)
        raise


def detect_faces(img):
    try:
        # print cv2.__version__
        face_cascade = cv2.CascadeClassifier(horus.models_cv_per)
        image = cv2.imread(img)
        if image is None:
            horus.log.error('could not load the image: ' + img)
            return -1
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5, flags=cv2.CASCADE_SCALE_IMAGE)
        return len(faces)
        # cv2.CV_HAAR_SCALE_IMAGE #
        # minSize=(30, 30)

        ## Draw a rectangle around the faces
        # for (x, y, w, h) in faces:
        #    cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
        # cv2.imshow("Faces found", image)
        # cv2.waitKey(0)

    except Exception as error:
        horus.log.error(':: error: ' + repr(error))
        return -1


def bow_features(fn, ner_type):
    im = cv2.imread(fn, 0)
    if ner_type == 'ORG_1':
        extract_bow.setVocabulary(voc_org)
    elif ner_type == 'LOC_1':
        extract_bow.setVocabulary(voc_loc_1)
    elif ner_type == 'LOC_2':
        extract_bow.setVocabulary(voc_loc_2)
    elif ner_type == 'LOC_3':
        extract_bow.setVocabulary(voc_loc_3)
    elif ner_type == 'LOC_4':
        extract_bow.setVocabulary(voc_loc_4)
    elif ner_type == 'LOC_5':
        extract_bow.setVocabulary(voc_loc_5)
    elif ner_type == 'LOC_6':
        extract_bow.setVocabulary(voc_loc_6)
    elif ner_type == 'LOC_7':
        extract_bow.setVocabulary(voc_loc_7)
    elif ner_type == 'LOC_8':
        extract_bow.setVocabulary(voc_loc_8)
    elif ner_type == 'LOC_9':
        extract_bow.setVocabulary(voc_loc_9)
    elif ner_type == 'LOC_10':
        extract_bow.setVocabulary(voc_loc_10)

    return extract_bow.compute(im, detect.detect(im))


def detect_logo(img):
    f = bow_features(img, 'ORG_1');
    if f is None:
        horus.log.warn(':: feature extraction error!')
        p = [0]
    else:
        p = svm_logo.predict(f)
    horus.log.debug('predicted class -> ' + str(p))
    return p


def detect_place(img):
    horus.log.debug(':: detecting places...')
    ret = []
    f = bow_features(img, 'LOC_1');
    if f is None:
        horus.log.warn(':: feature extraction error!')
        ret.append(-1)
    else:
        ret.append(svm_loc1.predict(f)[0])

    f = bow_features(img, 'LOC_2');
    if f is None:
        horus.log.warn(':: feature extraction error!')
        ret.append(-1)
    else:
        ret.append(svm_loc2.predict(f)[0])

    f = bow_features(img, 'LOC_3');
    if f is None:
        horus.log.warn(':: feature extraction error!')
        ret.append(-1)
    else:
        ret.append(svm_loc3.predict(f)[0])

    f = bow_features(img, 'LOC_4');
    if f is None:
        horus.log.warn(':: feature extraction error!')
        ret.append(-1)
    else:
        ret.append(svm_loc4.predict(f)[0])

    f = bow_features(img, 'LOC_5');
    if f is None:
        horus.log.warn(':: feature extraction error!')
        ret.append(-1)
    else:
        ret.append(svm_loc5.predict(f)[0])

    f = bow_features(img, 'LOC_6');
    if f is None:
        horus.log.warn(':: feature extraction error!')
        ret.append(-1)
    else:
        ret.append(svm_loc6.predict(f)[0])

    f = bow_features(img, 'LOC_7');
    if f is None:
        horus.log.warn(':: feature extraction error!')
        ret.append(-1)
    else:
        ret.append(svm_loc7.predict(f)[0])

    f = bow_features(img, 'LOC_8');
    if f is None:
        horus.log.warn(':: feature extraction error!')
        ret.append(-1)
    else:
        ret.append(svm_loc8.predict(f)[0])

    f = bow_features(img, 'LOC_9');
    if f is None:
        horus.log.warn(':: feature extraction error!')
        ret.append(-1)
    else:
        ret.append(svm_loc9.predict(f)[0])

    f = bow_features(img, 'LOC_10');
    if f is None:
        horus.log.warn(':: feature extraction error!')
        ret.append(-1)
    else:
        ret.append(svm_loc10.predict(f)[0])

    return ret


def detect_text_klass(t1, t2, id, t1en, t2en):

    horus.log.debug(':: text analysis component launched')

    try:
        from translate import Translator

        #https://pypi.python.org/pypi/translate (alternative 1000 per day)
        #https://www.microsoft.com/en-us/translator/getstarted.aspx
        #https://github.com/openlabs/Microsoft-Translator-Python-API

        c = conn.cursor()
        t1final = t1
        t2final = t2

        # need to save to horus db
        if t1en is None:
            lt1 = langdetect.detect(t1)
            if lt1 != 'en':
                try:
                    t1final = translator.translate(t1, 'en')
                except Exception as e1:
                    horus.log.error(':: Error, trying another service: ' + str(e1))
                    try:
                        translator2 = Translator(from_lang=lt1, to_lang="en")
                        t1final = translator2.translate(t1)
                    except Exception as e2:
                        horus.log.error(':: Error at service 2: ' + str(e2))
                        return [-1]
                        # updating

            t1final = 'u'+t1final # .encode('ascii', 'ignore')
            sql = """UPDATE HORUS_SEARCH_RESULT_TEXT
                     SET result_title_en = ? WHERE id = ?"""
            c.execute(sql, (t1final, id))
            conn.commit()
        else:
            t1final = t1en

        if t2en is None:
            lt2 = langdetect.detect(t2)
            if lt2 != 'en':
                try:
                    t2final = translator.translate(t2, 'en')
                except Exception as e1:
                    horus.log.error(':: Error, trying another service: ' + str(e1))
                    try:
                        translator2 = Translator(from_lang=lt2, to_lang="en")
                        t2final = translator2.translate(t2)
                    except Exception as e2:
                        horus.log.error(':: Error at service 2: ' + str(e2))
                        return [-1]
                        # updating

            #t2final = t2final.encode('ascii', 'ignore')
            t2final = 'u'+t2final
            sql = """UPDATE HORUS_SEARCH_RESULT_TEXT
                            SET result_description_en = ? WHERE id = ?"""
            c.execute(sql, (t2final, id))
            conn.commit()
        else:
            t2final = t2en

        c.close()
        docs = ["{} {}".format(t1final, t2final)]
        predicted = text_checking_model.predict(docs)
        return predicted

        #blob = TextBlob(t2)
        #t22 = blob.translate(to='en')
        # text_vocab = set(w.lower() for w in t2 if w.lower().isalpha())
        # unusual = text_vocab.difference(english_vocab)

    except Exception as e:
        horus.log.error(':: Error: ' + str(e))
        return [-1]


def detect_objects(horus_matrix):     # id_term_img, id_term_txt, id_ner_type, term
    auxi = 0
    toti = len(horus_matrix)
    for item in horus_matrix:
        auxi += 1
        if item[4] == 'NOUN' or item[7] == 1:

            horus.log.info(':: processing item %d of %d' % (auxi, toti))

            id_term_img = item[10]
            id_term_txt = item[9]
            id_ner_type = 0
            term = item[3]

            tot_geral_faces = 0
            tot_geral_logos = 0
            tot_geral_locations = 0
            tot_geral_pos_locations = 0
            tot_geral_neg_locations = 0
            T = int(horus.models_location_theta)  # location threshold

            filesimg = []
            metadata = []
            with conn:
                cursor = conn.cursor()
                cursor.execute("""SELECT filename,
                                             id,
                                             processed,
                                             nr_faces,
                                             nr_logos,
                                             nr_place_1,
                                             nr_place_2,
                                             nr_place_3,
                                             nr_place_4,
                                             nr_place_5,
                                             nr_place_6,
                                             nr_place_7,
                                             nr_place_8,
                                             nr_place_9,
                                             nr_place_10
                                      FROM HORUS_SEARCH_RESULT_IMG
                                      WHERE id_term_search = %s AND id_ner_type = %s""" % (id_term_img, id_ner_type))
                rows = cursor.fetchall()
                tot_img = len(rows)

                for row in rows:  # 0 = file path | 1 = id | 2 = processed | 3=nr_faces | 4=nr_logos | 5 to 13=nr_places_1 to 9
                    filesimg.append((horus.cache_img_folder + row[0],
                                     row[1],
                                     row[2],
                                     row[3],
                                     row[4],
                                     row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], row[13],
                                     row[14]))

            for image_term in filesimg:
                if image_term[2] == 1:
                    tot_geral_faces += image_term[3]
                    tot_geral_logos += image_term[4]
                    if (image_term[5:13]).count(1) >= int(T):
                        tot_geral_locations += 1
                    tot_geral_pos_locations += image_term[5:13].count(1)
                    tot_geral_neg_locations += (image_term[5:13].count(-1) * -1)
                else:
                    # ----- face recognition -----
                    tot_faces = detect_faces(image_term[0])
                    if tot_faces > 0:
                        tot_geral_faces += 1
                        horus.log.debug(":: found {0} faces!".format(tot_faces))

                    # ----- logo recognition -----
                    tot_logos = detect_logo(image_term[0])
                    if tot_logos[0] == 1:
                        tot_geral_logos += 1
                        horus.log.debug(":: found {0} logo(s)!".format(1))

                    # ----- place recognition -----
                    res = detect_place(image_term[0])
                    tot_geral_pos_locations += res.count(1)
                    tot_geral_neg_locations += (res.count(-1) * -1)

                    if res.count(1) >= T:
                        tot_geral_locations += 1
                        horus.log.debug(":: found {0} place(s)!".format(1))

                    # updating results
                    sql = """UPDATE HORUS_SEARCH_RESULT_IMG
                                 SET nr_faces = ?, nr_logos = ?, nr_place_1 = ?, nr_place_2 = ?, nr_place_3 = ?,
                                     nr_place_4 = ?, nr_place_5 = ?, nr_place_6 = ?, nr_place_7 = ?, nr_place_8 = ?,
                                     nr_place_9 = ?, nr_place_10 = ?, processed = 1
                                 WHERE id = ?"""
                    param = []
                    param.append(tot_faces)
                    param.append(tot_logos[0]) if tot_logos[0] == 1 else param.append(0)
                    param.extend(res)
                    param.append(image_term[1])
                    cursor.execute(sql, param)

            conn.commit()

            outs = [tot_geral_locations, tot_geral_logos, tot_geral_faces]
            maxs_cv = heapq.nlargest(2, outs)
            dist_cv_indicator = max(maxs_cv) - min(maxs_cv)
            place_cv_indicator = tot_geral_pos_locations + tot_geral_neg_locations

            # 0 to 5
            metadata.append(tot_img)
            metadata.append(tot_geral_locations)  # 1
            metadata.append(tot_geral_logos)  # 2
            metadata.append(tot_geral_faces)  # 3
            metadata.append(dist_cv_indicator)  # 4
            metadata.append(place_cv_indicator)  # 5

            horus.log.debug('-------------------------------------------------------------')
            horus.log.debug(':: [checking related visual information for [%s]]' % term)
            horus.log.debug('')
            horus.log.debug('-> CV_LOC  indicator: %f %%' % (float(tot_geral_locations) / tot_img)) if tot_img > 0 \
                else horus.log.debug('-> CV_LOC  indicator: err no img retrieved')
            horus.log.debug('-> CV_ORG  indicator: %f %%' % (float(tot_geral_logos) / tot_img)) if tot_img > 0 \
                else horus.log.debug('-> CV_ORG  indicator: err no img retrieved')
            horus.log.debug('-> CV_PER  indicator: %f %%' % (float(tot_geral_faces) / tot_img)) if tot_img > 0 \
                else horus.log.debug('-> CV_PER  indicator: err no img retrieved')
            horus.log.debug('-> CV_DIST indicator: %s' % (str(dist_cv_indicator)))
            horus.log.debug('-> CV_PLC  indicator: %s' % (str(place_cv_indicator)))

            # HORUS CV NER - 6 (PAREI AQUI, ESSE CORTE NAO PODE FICAR AQUI OBVIAMENTE, SENAO DIMINUI A ACURACIA AUTOMARICAMENT!
            # MUDAR ISSO PRA UMA FUNCAO DE DECISAO SEPARADA (MAS SEMPRE ADICIONAR A PREDICAO DO HORUS_CV
            horus_cv_ner = outs.index(max(outs)) + 1
            if dist_cv_indicator >= int(horus.models_distance_theta):
                metadata.append(klasses[horus_cv_ner])
                horus.log.debug(':: most likely class -> ' + klasses[horus_cv_ner])
            else:
                metadata.append('*')
                horus.log.debug(':: most likely class -> that\'s hard to say...')

            # text classification
            horus.log.debug(':: [checking related textual information ...]')
            y = []
            with conn:
                cursor = conn.cursor()
                cursor.execute("""SELECT id, result_seq, result_title, result_description, result_title_en,
                                             result_description_en, processed, text_klass
                                      FROM HORUS_SEARCH_RESULT_TEXT
                                      WHERE id_term_search = %s AND id_ner_type = %s""" % (id_term_txt, id_ner_type))
                rows = cursor.fetchall()
                tot_err = 0
                for row in rows:
                    if row[6] == 0 or row[6] is None:
                        ret = detect_text_klass(row[2], row[3], row[0], row[4], row[5])
                        if ret[0] != -1:
                            y.append(ret)
                            sql = """UPDATE HORUS_SEARCH_RESULT_TEXT SET text_klass = %s , processed = 1
                                     WHERE id = %s""" % (ret[0], row[0])
                            horus.log.debug(':: ' + sql)
                            cursor.execute(sql)
                        else:
                            tot_err += 1
                    else:
                        y.append(row[7])

                conn.commit()

                gp = [y.count(1), y.count(2), y.count(3)]
                horus_tx_ner = gp.index(max(gp)) + 1

                horus.log.debug(':: final textual checking statistics for term [%s] '
                                '(1-LOC = %s, 2-ORG = %s and 3-PER = %s)' % (term, str(y.count(1)), str(y.count(2)),
                                                                             str(y.count(3))))
                # 7 to 11
                metadata.append(len(rows))
                metadata.append(y.count(1))
                metadata.append(y.count(2))
                metadata.append(y.count(3))
                metadata.append(float(tot_err))

                maxs_tx = heapq.nlargest(2, gp)
                dist_tx_indicator = max(maxs_tx) - min(maxs_tx)

                # 12, 13
                metadata.append(dist_tx_indicator)
                metadata.append(klasses[horus_tx_ner])

                if len(rows) != 0:
                    horus.log.debug('-> TX_LOC  indicator: %f %%' % (float(y.count(1)) / len(rows)))
                    horus.log.debug('-> TX_ORG  indicator: %f %%' % (float(y.count(2)) / len(rows)))
                    horus.log.debug('-> TX_PER  indicator: %f %%' % (float(y.count(3)) / len(rows)))
                    horus.log.debug('-> TX_DIST indicator: %s' % (str(dist_tx_indicator)))
                    horus.log.debug(':: number of trans. errors -> ' + str(tot_err) + ' over ' + str(len(rows)))
                    horus.log.debug(':: most likely class -> ' + klasses[horus_tx_ner])
                else:
                    horus.log.debug(':: there was a problem searching this term..please try to index it again...')

                # checking final NER - 14
                if metadata[4] >= int(horus.models_distance_theta):
                    metadata.append(metadata[6])  # CV is the final decision
                else:
                    metadata.append(metadata[13])  # TX is the final decision

            item.extend(metadata)
        else:
            item.extend([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])

    return horus_matrix


def update_compound_predictions(horus_matrix):
    '''
    updates the predictions based on the compound
    :param horus_matrix:
    :return:
    '''
    horus.log.info(':: updating compounds predictions')
    i_sent = None
    i_first_word = None
    for i in range(len(horus_matrix)):
        if horus_matrix[i][7] == 1:
            y = horus_matrix[i][25]
            i_sent = horus_matrix[i][1]
            i_first_word = horus_matrix[i][2]
            c_size = int(horus_matrix[i][8])
        if horus_matrix[i][7] == 0 and i_sent is not None:
            if horus_matrix[i][1] == i_sent and horus_matrix[i][2] == i_first_word:
                for k in range(c_size):
                    horus_matrix[i + k][25] = y
    horus.log.info(':: done')


def process_input_text(text):
    horus.log.info(':: text: ' + text)
    horus.log.info(':: tokenizing sentences ...')
    sent_tokenize_list = sent_tokenize(text)
    horus.log.info(':: processing ' + str(len(sent_tokenize_list)) + ' sentence(s).')
    sentences = []
    w = []
    ner = []
    pos = []
    hasNER = -1
    for sentence in sent_tokenize_list:
        tokens = nltk.word_tokenize(sentence)
        pos_universal = nltk.pos_tag(tokens, tagset='universal')
        chunked = nltk.ne_chunk(nltk.pos_tag(tokens))
        for ch in chunked:
            if type(ch) is nltk.Tree:
                w.append(ch[0][0])
                pos.append(ch[0][1])
                hasNER = 1
                if ch._label == 'GPE' or ch._label == 'LOCATION':
                    ner.append('LOC')
                elif ch._label == 'PERSON':
                    ner.append('PER')
                elif ch._label == 'ORGANIZATION':
                    ner.append('ORG')
                else:
                    ner.append('O')
            else:
                w.append(ch[0])
                pos.append(ch[1])
                ner.append('O')

        _pos = list(zip(*pos_universal)[1])
        sentences.append([hasNER, sentence, tokens, ner, pos, _pos])
        pos = []
        ner = []
        w = []
    return sentences


def process_ritter_ds(dspath):
    '''
    return a set of sentences
    :param dspath: path to Ritter dataset
    :return: sentence contains any entity?, sentence, words, NER tags
    '''
    sentences = []
    w = []
    t = []
    s = ''
    has3NER = -1
    with open(dspath) as f:
        for line in f:
            token = line.split('\t')[0]
            tag = line.split('\t')[1].replace('\r','').replace('\n','')
            if token == '':
                if len(w) != 0:
                    pos_uni = nltk.pos_tag(w, tagset='universal')
                    pos = nltk.pos_tag(w)
                    _pos = zip(*pos)[1]
                    _pos_uni = zip(*pos_uni)[1]
                    sentences.append([has3NER, s, w, t, list(_pos), list(_pos_uni)])
                    w = []
                    t = []
                    s = ''
                    has3NER = -1
            else:
                s += token + ' '
                w.append(token)
                t.append(tag)
                if tag in ner_ritter:
                    has3NER = 1
    return sentences

if __name__ == '__main__':
    main()