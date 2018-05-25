import pickle

import os

import pandas as pd
import sklearn
from nltk import WordNetLemmatizer
from nltk.stem.snowball import SnowballStemmer
from src.config import HorusConfig
from src.core.util import definitions
from src.core.util.definitions import encoder_words, encoder_lemma_name, encoder_stem_name

config = HorusConfig()

def word2dict(experiment_folder, datasets):
    try:
        config.logger.info('creating encoders: ' + datasets)
        experiment_folder+='/'
        wnl = WordNetLemmatizer()
        stemmer = SnowballStemmer("english")
        words=[]
        lemmas=[]
        stemmers=[]
        le = sklearn.preprocessing.LabelEncoder()
        all_sentences_name='raw_data_brown_clusters.txt'
        if os.path.exists(config.dir_encoders + encoder_words) is False:
            f = open(config.dir_encoders + all_sentences_name, 'w+')
            for ds in datasets.split():
                config.logger.info('creating encoder for: ' + ds)
                _file = config.dir_output + experiment_folder + ds
                df = pd.read_csv(_file, delimiter="\t", skiprows=1, header=None, keep_default_na=False,
                                 na_values=['_|_'], usecols=[definitions.INDEX_ID_SENTENCE, definitions.INDEX_TOKEN, definitions.INDEX_IS_COMPOUND])
                prev_sent_id=df.iloc[0].at[definitions.INDEX_ID_SENTENCE]
                sentence=''
                for row in df.itertuples():
                    w=str(row[2])
                    words.append(w)
                    try:
                        lemmas.append(wnl.lemmatize(w.lower()))
                    except:
                        continue
                    try:
                        stemmers.append(stemmer.stem(w.lower()))
                    except:
                        continue

                    if prev_sent_id==row[1]:
                        if row[3] != 1:
                            sentence += ' ' + w
                    else:
                        f.write(sentence.strip() + '\n')
                        sentence=w
                    prev_sent_id=row[1]
                f.flush()
            f.close()

            config.logger.info('total tokens: ' + str(len(words)))
            config.logger.info('total lemmas: ' + str(len(lemmas)))
            config.logger.info('total stemmers: ' + str(len(stemmers)))
            words=set(words)
            lemmas=set(lemmas)
            stemmers=set(stemmers)
            config.logger.info('words vocabulary size: ' + str(len(words)))
            config.logger.info('lemmas vocabulary size: ' + str(len(lemmas)))
            config.logger.info('stemmer vocabulary size: ' + str(len(stemmers)))
            le.fit(list(words))
            with open(config.dir_encoders + encoder_words, 'wb') as output:
                pickle.dump(le, output, pickle.HIGHEST_PROTOCOL)

            le.fit(list(lemmas))
            with open(config.dir_encoders + encoder_lemma_name, 'wb') as output:
                pickle.dump(le, output, pickle.HIGHEST_PROTOCOL)

            le.fit(list(stemmers))
            with open(config.dir_encoders + encoder_stem_name, 'wb') as output:
                pickle.dump(le, output, pickle.HIGHEST_PROTOCOL)

    except:
        raise

def conll2sentence():
    config.logger.info('creating sentences file for brown clusters')
    f_out = open(config.dir_datasets + 'all_sentences.txt', 'w+')
    for file in ['Ritter/ner.txt',
                 'wnut/2015.conll.freebase',
                 'wnut/2016.conll.freebase',
                 'wnut/emerging.test.annotated']:
        filepath= config.dir_datasets + file
        sentence=''
        with open(filepath) as f:
            content = f.readlines()
            for x in content:
                if x!='\n':
                    sentence+=x.split('\t')[0] + ' '
                else:
                    f_out.write(sentence.strip() + '\n')
                    sentence=''
        f_out.flush()

    f_out.close()

def browncluster2dict(filepath, filename):
    try:
        config.logger.info('creating dictionary: ' + filename)
        brown = dict()
        with open(filepath + filename) as f:
            content = f.readlines()
            for x in content:
                n=x.split('\t')
                brown.update({n[1]:str(n[0])})
        with open(config.dir_datasets + '%s_dict.pkl' % (filename), 'wb') as output:
            pickle.dump(brown, output, pickle.HIGHEST_PROTOCOL)
        config.logger.info('file generated')
    except:
        raise

#browncluster2dict('output_brownclusters.txt')


word2dict('EXP_004', '2016.conll.freebase.ascii.txt.horus emerging.test.annotated.horus ner.txt.horus 2015.conll.freebase.horus')
exit(0)
browncluster2dict(config.dir_datasets + 'brown_clusters/', 'gha.500M-c1000-p1.paths')
browncluster2dict(config.dir_datasets + 'brown_clusters/', 'gha.64M-c640-p1.paths')
browncluster2dict(config.dir_datasets + 'brown_clusters/', 'gha.64M-c320-p1.paths')