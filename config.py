import logging
import os
from configparser import ConfigParser
import datetime


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class HorusConfig(object):
    __metaclass__ = Singleton

    def __init__(self):
        fine = False
        for ini_file in os.path.dirname(os.path.abspath(__file__)), \
                        os.curdir, os.path.expanduser("~"), \
                        "/etc/horus", \
                        os.environ.get('HORUS_CONF'):
            try:
                _ini = os.path.join(ini_file, "horus.ini")
                with open(_ini) as source:
                    print(':: reading ok ' + _ini)

                    parser = ConfigParser()
                    parser.read(source.name)

                    print(parser.get('conf', 'code'))

                    # project root directory
                    self.project_root_dir = os.path.dirname(os.path.abspath(__file__)) + '/'
                    self.project_source_dir = self.project_root_dir + 'src/'

                    # resource root directory
                    self.resource_root_dir = parser.get('path', 'resources_dir')
                    if self.resource_root_dir == '':
                        print('<resource_root_dir directory> not set in horus.ini, using project default: ' +
                              self.project_root_dir + 'resources/')
                        self.resource_root_dir = self.project_root_dir + 'resources/'

                    # under \resources folder
                    self.database_db        = self.resource_root_dir + 'horus.db'
                    self.dir_encoders       = self.resource_root_dir + 'encoders/'
                    self.dir_models         = self.resource_root_dir + 'models/'
                    self.dir_libs           = self.resource_root_dir + 'libs/'
                    self.dir_output         = self.resource_root_dir + 'output/'
                    self.dir_datasets       = self.resource_root_dir + 'datasets/'
                    self.dir_cache_img      = self.resource_root_dir + 'img/'
                    self.dir_log            = self.resource_root_dir + 'log/'
                    self.dir_clusters       = self.resource_root_dir + 'word_clusters/'

                    # images cache directory
                    self.images_root_dir = parser.get('path', 'images_dir')
                    if self.images_root_dir == '':
                        print('<images_root_dir directory> not set in horus.ini, using project default: ' +
                              self.project_root_dir + 'resources/img/')
                        self.images_root_dir = self.project_root_dir + 'resources/img/'



                    # version
                    self.version = parser.get('conf', 'version')
                    self.version_label = parser.get('conf', 'version_label')
                    self.description = "A framework to boost NLP tasks"


                    self.log_level = parser.get('conf', 'log_level')
                    self.logger = logging.getLogger('horus')


                    # not attached to a root project directory, once it normally can be stored somewhere else (i.e., full path here)
                    #self.database_db = parser.get('path', 'database_path')
                    self.root_dir_tensorflow = parser.get('path', 'tensorflow_data')
                    self.nr_thread = parser.get('conf', 'nr_thread')

                    '''
                     ----------------------------------- Models -----------------------------------
                    '''

                    self.models_cnn_loc1 = self.dir_models + parser.get('models-cnn', 'horus_loc_1')
                    self.models_cnn_loc2 = self.dir_models + parser.get('models-cnn', 'horus_loc_2')
                    self.models_cnn_loc3 = self.dir_models + parser.get('models-cnn', 'horus_loc_3')
                    self.models_cnn_loc4 = self.dir_models + parser.get('models-cnn', 'horus_loc_4')
                    self.models_cnn_loc5 = self.dir_models + parser.get('models-cnn', 'horus_loc_5')
                    self.models_cnn_loc6 = self.dir_models + parser.get('models-cnn', 'horus_loc_6')
                    self.models_cnn_loc7 = self.dir_models + parser.get('models-cnn', 'horus_loc_7')
                    self.models_cnn_loc8 = self.dir_models + parser.get('models-cnn', 'horus_loc_8')
                    self.models_cnn_loc9 = self.dir_models + parser.get('models-cnn', 'horus_loc_9')
                    self.models_cnn_loc10 = self.dir_models + parser.get('models-cnn', 'horus_loc_10')
                    self.models_cnn_per = self.dir_models + parser.get('models-cnn', 'horus_per')
                    self.models_cnn_org = self.dir_models + parser.get('models-cnn', 'horus_org')

                    self.models_cv_loc1 = self.dir_models + parser.get('models-cv', 'horus_loc_1')
                    self.models_cv_loc2 = self.dir_models + parser.get('models-cv', 'horus_loc_2')
                    self.models_cv_loc3 = self.dir_models + parser.get('models-cv', 'horus_loc_3')
                    self.models_cv_loc4 = self.dir_models + parser.get('models-cv', 'horus_loc_4')
                    self.models_cv_loc5 = self.dir_models + parser.get('models-cv', 'horus_loc_5')
                    self.models_cv_loc6 = self.dir_models + parser.get('models-cv', 'horus_loc_6')
                    self.models_cv_loc7 = self.dir_models + parser.get('models-cv', 'horus_loc_7')
                    self.models_cv_loc8 = self.dir_models + parser.get('models-cv', 'horus_loc_8')
                    self.models_cv_loc9 = self.dir_models + parser.get('models-cv', 'horus_loc_9')
                    self.models_cv_loc10 = self.dir_models + parser.get('models-cv', 'horus_loc_10')

                    self.models_cv_loc_1_dict = self.dir_models + parser.get('models-cv', 'horus_loc_1_voc')
                    self.models_cv_loc_2_dict = self.dir_models + parser.get('models-cv', 'horus_loc_2_voc')
                    self.models_cv_loc_3_dict = self.dir_models + parser.get('models-cv', 'horus_loc_3_voc')
                    self.models_cv_loc_4_dict = self.dir_models + parser.get('models-cv', 'horus_loc_4_voc')
                    self.models_cv_loc_5_dict = self.dir_models + parser.get('models-cv', 'horus_loc_5_voc')
                    self.models_cv_loc_6_dict = self.dir_models + parser.get('models-cv', 'horus_loc_6_voc')
                    self.models_cv_loc_7_dict = self.dir_models + parser.get('models-cv', 'horus_loc_7_voc')
                    self.models_cv_loc_8_dict = self.dir_models + parser.get('models-cv', 'horus_loc_8_voc')
                    self.models_cv_loc_9_dict = self.dir_models + parser.get('models-cv', 'horus_loc_9_voc')
                    self.models_cv_loc_10_dict = self.dir_models + parser.get('models-cv', 'horus_loc_10_voc')

                    self.models_cv_org = self.dir_models + parser.get('models-cv', 'horus_org')
                    self.models_cv_org_dict = self.dir_models + parser.get('models-cv', 'horus_org_voc')
                    self.models_cv_per = self.dir_models + parser.get('models-cv', 'horus_per')

                    self.models_0_text = self.dir_models + parser.get('models-text', 'horus_textchecking_0')
                    self.models_1_text = self.dir_models + parser.get('models-text', 'horus_textchecking_1')
                    self.models_2_text = self.dir_models + parser.get('models-text', 'horus_textchecking_2')

                    self.models_1_text_cnn = self.dir_models + parser.get('models-text', 'horus_texthecking_tm_cnn')

                    self.model_final = self.dir_models + parser.get('models-horus', 'horus_final')
                    self.model_final_encoder = self.dir_models + parser.get('models-horus', 'horus_final_encoder')

                    self.models_tweetnlp_jar = self.dir_libs + 'tweetnlp/' + parser.get('models-tweetnlp', 'path_to_jar_pos')
                    self.models_tweetnlp_model = self.dir_libs + 'tweetnlp/' + parser.get('models-tweetnlp', 'model_filename_pos')
                    self.models_tweetnlp_java_param = parser.get('models-tweetnlp', 'java_param')

                    self.model_stanford_filename_pos = self.dir_libs + parser.get('model-stanford', 'model_filename_pos')
                    self.model_stanford_path_jar_pos = self.dir_libs + parser.get('model-stanford', 'path_to_jar_pos')
                    self.model_stanford_filename_ner = self.dir_libs + parser.get('model-stanford', 'model_filename_ner')
                    self.model_stanford_path_jar_ner = self.dir_libs + parser.get('model-stanford', 'path_to_jar_ner')

                    self.search_engine_api = parser.get('search-engine', 'api')
                    self.search_engine_key = parser.get('search-engine', 'key')
                    self.search_engine_features_text = parser.get('search-engine', 'features_text')
                    self.search_engine_features_img = parser.get('search-engine', 'features_img')
                    self.search_engine_tot_resources = parser.get('search-engine', 'tot_resources')


                    self.translation_id = parser.get('translation', 'microsoft_client_id')
                    self.translation_secret = parser.get('translation', 'microsoft_client_secret')
                    self.cache_sentences = parser.get('cache', 'cache_sentences')
                    self.models_force_download = parser.get('models-param', 'force_download')
                    self.models_location_theta = parser.get('models-param', 'location_theta')
                    self.models_distance_theta = parser.get('models-param', 'distance_theta')
                    self.models_safe_interval = parser.get('models-param', 'safe_interval')
                    self.models_limit_min_loc = parser.get('models-param', 'limit_min_loc')
                    self.models_distance_theta_high_bias = parser.get('models-param', 'distance_theta_high_bias')
                    self.models_pos_tag_lib = int(parser.get('models-param', 'pos_tag_lib'))
                    self.models_pos_tag_lib_type = int(parser.get('models-param', 'pos_tag_lib_type'))
                    self.models_kmeans_trees = int(parser.get('models-param', 'kmeans-trees'))
                    self.object_detection_type = int(parser.get('models-param', 'object_detection_type'))
                    self.text_classification_type = int(parser.get('models-param', 'text_classification_type'))
                    self.embeddings_path = parser.get('models-param', 'embeddings_path')

                    self.mod_text_tfidf_active = int(parser.get('rest-interface', 'mod_text_tfidf_active'))
                    self.mod_text_topic_active = int(parser.get('rest-interface', 'mod_text_topic_active'))
                    self.mod_image_sift_active = int(parser.get('rest-interface', 'mod_image_sift_active'))
                    self.mod_image_cnn_active = int(parser.get('rest-interface', 'mod_image_cnn_active'))

                    fine = True

                    break
                    #config.readfp(source)

            except IOError:
                pass

        if fine is False:
            raise ValueError('error on trying to read the conf file (horus.conf)! Please set HORUS_CONF with its '
                             'path or place it at your home dir')
        else:
            if len(self.logger.handlers) == 0:
                self.logger.setLevel(logging.DEBUG)
                if self.log_level == 'INFO':
                    self.logger.setLevel(logging.INFO)
                elif self.log_level == 'WARNING':
                    self.logger.setLevel(logging.WARNING)
                elif self.log_level == 'ERROR':
                    self.logger.setLevel(logging.ERROR)
                elif self.log_level == 'CRITICAL':
                    self.logger.setLevel(logging.CRITICAL)

                now = datetime.datetime.now()
                handler = logging.FileHandler(self.dir_log + 'horus_' + now.strftime("%Y-%m-%d") + '.log')
                formatter = logging.Formatter(
                    "%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
                consoleHandler = logging.StreamHandler()
                consoleHandler.setFormatter(formatter)
                self.logger.addHandler(consoleHandler)

        self.logger.info('==================================================================')
        self.logger.info('HORUS Framework')
        self.logger.info('version: ' + self.version)
        self.logger.info('http://horus-ner.org/')
        self.logger.info('==================================================================')

    @staticmethod
    def get_report():
        return 'to be implemented'