#!/usr/bin/env python
# coding: utf-8
import codecs
from collections import deque
import hashlib
import json
import logging
import logging.config
import os
import random
import re
import requests
from data_access import Session, LtpResult, FilteredParagraph
from log_config import LOG_PROJECT_NAME, LOGGING
from method import AnalyzedSentence
import method

logger = logging.getLogger(LOG_PROJECT_NAME + '.experiment')
logger.addHandler(logging.NullHandler())

LTP_URL = 'http://api.ltp-cloud.com/analysis'
API_KEY = 'u1Q1k8U6tglHca7ZZJ6qTBaq2k0QYwyXNqyE3kVu'
FORMAT = 'json'
PATTERN = 'all'
param = {'api_key': API_KEY,
         'format': FORMAT,
         'pattern': PATTERN,
         'text': None}

PUNCTUATION_TABLE = [u' ', u'.', u'。', u',', u'，', u'!', u'！', u';', u'；',
                     u'﹖', u'?', u'？', u'～', u'~']


def build_param(text):
    param['text'] = text
    return param


def md5(text):
    data = text.encode('utf-8') if isinstance(text, unicode) else text
    return hashlib.md5(data).hexdigest()


def truncate(text):
    for punctuation in PUNCTUATION_TABLE:
        index = text.find(punctuation)
        if 0 < index < 50:
            return text[:index]
    return text[:50]


def analyze(text):
    logger.info('try to invoke ltp api, %s', text)
    response = requests.get(LTP_URL, params=build_param(text), timeout=60)
    if (response.status_code == 400 and
                response.json()['error_message'] == 'SENTENCE TOO LONG') or \
            (response.ok and response.text.startswith('<html')):
        logger.info('sentence too long, truncate')
        truncated_text = truncate(text)
        response = requests.get(LTP_URL,
                                params=build_param(truncated_text),
                                timeout=60)
    if response.ok:
        return response.json()
    else:
        raise RuntimeError('bad response code={} url={} text={}'.format(
            response.status_code, response.url, response.text))


def save_analyzed_result(md5_string, result_json):
    ltp_result = LtpResult(md5_string,
                           json.dumps(result_json, ensure_ascii=False))
    Session.add(ltp_result)
    logger.info('start to insert ltp result, md5=%s', md5_string)
    try:
        Session.commit()
    except Exception:
        Session.rollback()
        logger.error('fail to insert', exc_info=True)
    logger.info('finished inserting ltp result')


def get_analyzed_result(question_text):
    if question_text is None:
        return None
    md5_string = md5(question_text)
    ltp_result = Session.query(LtpResult).filter_by(md5=md5_string).first()
    if ltp_result is not None:
        analyzed_result = AnalyzedSentence(md5_string, ltp_result.json_text)
    else:
        try:
            result_json = analyze(question_text)
        except RuntimeError:
            logger.error('fail to invoke ltp api, text=%s', question_text,
                         exc_info=True)
            raise RuntimeError()

        save_analyzed_result(md5_string, result_json)
        analyzed_result = AnalyzedSentence(md5_string, result_json)
    return analyzed_result


def test(method_, test_set_filename, result_filename, window_size):
    """Use method_ to judge questions in test_set_filename.

    :param method_: subclass of AbstractMethod
    :param test_set_filename: str
    :param result_filename: str
    """
    with codecs.open(test_set_filename, encoding='utf-8') as test_set, \
            codecs.open(result_filename, encoding='utf-8', mode='wb') as \
            result_file:
        logger.info('test %s, window_size=%s', test_set_filename, window_size)
        history_questions = deque(maxlen=window_size)
        previous_answer_text = None
        last_is_answer = False
        for line in test_set:
            line = line.strip()
            if line == '':
                continue
            if line.startswith('A'):
                previous_answer_text = line.split(':', 1)[1]
                last_is_answer = True
                continue
            [prefix, question_text] = line.split(':', 1)
            question = get_analyzed_result(question_text)
            previous_answer = get_analyzed_result(previous_answer_text) \
                if last_is_answer else None
            last_is_answer = False
            logger.info('test %s', prefix)
            follow_up = method_.is_follow_up(question, history_questions,
                                             previous_answer)
            result_file.write('{}:{:d}\n'.format(prefix, follow_up))
            history_questions.append(question)


def evaluate(result_filename, label_filename):
    """Evaluate the test result.

    :param result_filename: str
    :param label_filename: str
    :return: dict
    """
    with codecs.open(label_filename, encoding='utf-8') as label_file, \
            codecs.open(result_filename, encoding='utf-8') as result_file:
        outcome = {
            'new': {'new': 0, 'follow': 0, 'P': 0.0, 'R': 0.0, 'F1': 0.0},
            'follow': {'new': 0, 'follow': 0, 'P': 0.0, 'R': 0.0, 'F1': 0.0},
            'all': {'true': 0, 'false': 0, 'P': 0.0}}
        num_meaning = {'1': 'new', '0': 'follow'}
        new = outcome['new']
        follow = outcome['follow']
        all_ = outcome['all']
        for result_line in result_file:
            result_line = result_line.strip()
            label_line = label_file.next()
            label_line = label_line.strip()
            result_key = num_meaning[result_line[-1]]
            label_key = num_meaning[label_line[-1]]
            outcome[result_key][label_key] += 1
        new['P'] = ratio(new['new'], new['follow'])
        new['R'] = ratio(new['new'], follow['new'])
        new['F1'] = 2*new['R']*ratio(new['P'], new['R'])
        follow['P'] = ratio(follow['follow'], follow['new'])
        follow['R'] = ratio(follow['follow'], new['follow'])
        follow['F1'] = 2*follow['R']*ratio(follow['P'], follow['R'])
        all_['true'] = new['new'] + follow['follow']
        all_['false'] = new['follow'] + follow['new']
        all_['P'] = ratio(all_['true'], all_['false'])
    return outcome


def ratio(a, b):
    """Return a/(a+b)

    :param a: int | float
    :param b: int | float
    :return: float
    """
    total = a+b
    result = 0.0
    if total != 0:
        result = float(a) / total
    return result


def adjust_threshold(path, q_a_threshold=None, q_q_threshold=None):
    if q_a_threshold is not None and q_q_threshold is not None:
        raise RuntimeError('no more than 1 threshold given but 2')
    method_ = method.get_method('de_boni')
    # 调参方式 0-两个都调 1-调q_q 2-调q_a
    scheme = 0
    output_name = '{}/adjust-threshold-both.json'.format(path)
    if q_a_threshold is not None:
        # q_a_threshold固定
        scheme += 1
        output_name = '{}/adjust-threshold-q-a-{}.json'.format(path,
                                                               q_a_threshold)
        logger.info('set constant question-answer similarity threshold=%s',
                    q_a_threshold)
        method_.q_a_threshold = q_a_threshold
    if q_q_threshold is not None:
        # q_q_threshold固定
        scheme += 2
        output_name = '{}/adjust-threshold-q-q-{}.json'.format(path,
                                                               q_q_threshold)
        logger.info('set constant question-question similarity threshold=%s',
                    q_q_threshold)
        method_.q_q_threshold = q_q_threshold
    result = []
    for x in range(80, 100, 1):
        threshold = x / 100.0
        # q_a_threshold固定
        if scheme == 1:
            logger.info('set question-question similarity thresholds=%s',
                        threshold)
            method_.q_q_threshold = threshold
            file_name = '{}/q-q-{}-q-a-{}.txt'.format(path, threshold,
                                                      q_a_threshold)
        # q_q_threshold固定
        elif scheme == 2:
            logger.info('set question-answer similarity thresholds=%s',
                        threshold)
            method_.q_a_threshold = threshold
            file_name = '{}/q-q-{}-q-a-{}.txt'.format(path, q_q_threshold,
                                                      threshold)
        else:
            logger.info('set all similarity thresholds=%s',
                        threshold)
            method_.q_a_threshold = threshold
            method_.q_q_threshold = threshold
            file_name = '{0}/q-q-{1}-q-a-{1}.txt'.format(path, threshold)
        if os.path.isfile(file_name):
            logger.info('%s exists', file_name)
        else:
            test(method_, result_filename=file_name)
        evaluation_result = evaluate(result_filename=file_name)
        result.append({'threshold': threshold, 'result': evaluation_result})
    with codecs.open(output_name, encoding='utf-8', mode='wb') as f:
        f.write(json.dumps(result))


def generate_train_data(method_, text_filename, label_filename,
                        train_data_filename):
    """

    :param method_: subclass of AbstractMethod
    :param text_filename: str
    :param label_filename: str
    :param train_data_filename: str
    """
    with codecs.open(text_filename, encoding='utf-8') as text_file, \
            codecs.open(label_filename, encoding='utf-8') as label_file, \
            codecs.open(train_data_filename, encoding='utf-8', mode='wb') as \
            train_data_file:
        context_window = 3
        history_questions = deque(maxlen=context_window)
        previous_answer_text = None
        last_is_answer = False
        feature_names = method_.feature_names
        head = ','.join(feature_names)
        head = '{},label\n'.format(head)
        train_data_file.write(head)
        for line in text_file:
            line = line.strip()
            if line == '':
                continue
            if line.startswith('A'):
                previous_answer_text = line.split(':', 1)[1]
                last_is_answer = True
                continue
            label = label_file.next().strip().split(':', 1)[1]
            num, question_text = line.split(':', 1)
            logger.debug('%s', num)
            question = get_analyzed_result(question_text)
            previous_answer = get_analyzed_result(previous_answer_text) if \
                last_is_answer else None
            features = method_.features(question, history_questions,
                                        previous_answer)
            train_data_line = to_literal(features + [label])
            train_data_line = ','.join(train_data_line)
            train_data_file.write('{}\n'.format(train_data_line))
            history_questions.append(question)
            last_is_answer = False


def to_literal(x):
    """Convert items in x to literal string.

    :param x: list[unicode | bool | float | int]
    :return: list[unicode]
    :raise RuntimeError:
    """
    result = []
    for i in x:
        if isinstance(i, unicode):
            result.append(i)
        elif isinstance(i, bool):
            result.append(u'1' if i else u'0')
        elif isinstance(i, int):
            result.append(unicode(i))
        elif isinstance(i, float):
            result.append('{:.3f}'.format(i))
        else:
            raise RuntimeError(u'cannot handle {}'.format(i))
    return result


def adjust_len(path, output):
    file_list = os.listdir(path)
    len_dict = dict([(int(re.findall(r'\d+', f)[0]), '{}/{}'.format(path, f))
                     for f in file_list])
    result = []
    for len in sorted(len_dict.keys()):
        evaluation_result = evaluate(result_filename=len_dict[len])
        result.append({'threshold': len, 'result': evaluation_result})
    with codecs.open(output, encoding='utf-8', mode='wb') as f:
        f.write(json.dumps(result))


def analyze_feature(k, num, method_name, window_size=3):
    """Analyze the effect without a feature one by one.

    Example:
        In: analyze_feature(2, 10, method_name)
        Out:
            {
                'origin': {
                    0: {
                        'new': {
                            'P': 0.0,
                            'R': 0.0,
                            'F1': 0.0
                        },
                        'follow': {
                            ...
                        },
                        'all': {
                            'P': 0.0
                        }
                    },
                    1: {
                        ...
                    },
                    'average': {
                        ...
                    }
                },
                'same_named_entity': {
                    ...
                }
            }
    :param k: int
    :param num: int
    :param method_name: str
    :return: dict
    """
    origin = k_fold_cross(k, num, method_name, 'origin')
    whole_result = {'origin': origin}
    method_ = method.methods[method_name]
    feature_names = method_.feature_names
    for feature_name in feature_names:
        method_.feature_names = feature_names[:]
        method_.feature_names.remove(feature_name)
        logger.info('analyze feature %s', feature_name)
        result = k_fold_cross(k, num, method_name, feature_name, window_size)
        whole_result[feature_name] = result
    return whole_result


def k_fold_cross(k, num, method_name, unique_word, window_size=3):
    """Do k-fold cross test with named method.

    Example:
        In: k_fold_cross(2, 10, 'my_method', 'initial')
        Out:
            {
                0: {
                    'new': {
                        'P': 0.0,
                        'R': 0.0,
                        'F1': 0.0
                    },
                    'follow': {
                        ...
                    },
                    'all': {
                        'P': 0.0
                    }
                },
                1: {
                    ...
                },
                'average': {
                    ...
                }
            }
    :param k: int. num of fold
    :param num: int
    :param method_name: str
    :param unique_word: str
    :return: dict
    """
    file_names = k_fold_cross_dataset(k, num)
    method_ = method.methods[method_name]
    file_pattern = 'data/{k}-fold-cross-{unique_word}-{{type}}-{{i}}.txt'.\
        format(k=k, unique_word=unique_word)
    whole_result = {}
    for i in range(0, k):
        test_text_file = file_names[i]['test_text']
        test_label_file = file_names[i]['test_label']
        train_text_file = file_names[i]['train_text']
        train_label_file = file_names[i]['train_label']
        train_data_file = file_pattern.format(type='train-data', i=i)
        result_file = file_pattern.format(type='result', i=i)
        if not isinstance(method_, method.DeBoni):
            generate_train_data(method_, train_text_file, train_label_file,
                                train_data_file)
            method_.train_data_filename = train_data_file
            method_.classifier = None
        # test
        test(method_, test_text_file, result_file, window_size)
        # evaluate
        result = evaluate(result_file, test_label_file)
        whole_result[i] = result
    whole_result['average'] = {
        'new': {'P': 0.0, 'R': 0.0, 'F1': 0.0},
        'follow': {'P': 0.0, 'R': 0.0, 'F1': 0.0},
        'all': {'P': 0.0}}
    for k1, v1 in whole_result['average'].iteritems():
        for k2 in v1:
            v1[k2] = sum(whole_result[num][k1][k2] for num in
                         range(0, k)) / k
    return whole_result


def k_fold_cross_dataset(k, num):
    """Generate k-fold cross test set and train set.

    Example:
        In: k_fold_cross_dataset(2, 10)
        Out:
            [
                {
                    'test_text': 'data/2-fold-cross-10-test-text-1.txt',
                    'test_label': 'data/2-fold-cross-10-test-label-1.txt',
                    'train_text': 'data/2-fold-cross-10-train-text-1.txt',
                    'train_label': 'data/2-fold-cross-10-train-label-1.txt',
                },
                {
                    'test_text': 'data/2-fold-cross-10-test-text-2.txt',
                    'test_label': 'data/2-fold-cross-10-test-label-2.txt',
                    'train_text': 'data/2-fold-cross-10-train-text-2.txt',
                    'train_label': 'data/2-fold-cross-10-train-label-2.txt',
                }
            ]

    :param k: int
    :param num: int
    :return: list :raise RuntimeError:
    """
    prefix = 'data/{k}-fold-cross-{num}'.format(k=k, num=num) 
    file_pattern = '{prefix}-{{type}}-{{{{i}}}}.txt'.format(prefix=prefix)
    test_text_file_pattern = file_pattern.format(type='test-text')
    test_label_file_pattern = file_pattern.format(type='test-label')
    train_text_file_pattern = file_pattern.format(type='train-text')
    train_label_file_pattern = file_pattern.format(type='train-label')
    file_names = []
    for i in range(0, k):
        test_text_file = test_text_file_pattern.format(i=i)
        test_label_file = test_label_file_pattern.format(i=i)
        train_text_file = train_text_file_pattern.format(i=i)
        train_label_file = train_label_file_pattern.format(i=i)
        file_names.append({
            'test_text': test_text_file,
            'test_label': test_label_file,
            'train_text': train_text_file,
            'train_label': train_label_file})
    exist = True
    for i in file_names:
        for file_ in i.itervalues():
            if not os.path.isfile(file_):
                exist = False
                break
    if not exist:
        filtered_paragraphs = Session.query(FilteredParagraph).limit(num).all()
        if len(filtered_paragraphs) != num:
            raise RuntimeError()
        random.shuffle(filtered_paragraphs)
        folds = [[] for i in range(0, k)]
        for i in range(0, num):
            folds[i % k].append(filtered_paragraphs[i].paragraph)
        for i in range(0, k):
            test_text_file = file_names[i]['test_text']
            test_label_file = file_names[i]['test_label']
            train_text_file = file_names[i]['train_text']
            train_label_file = file_names[i]['train_label']
            test_set = folds[i]
            train_set = []
            for j in range(0, k):
                if j != i:
                    train_set.extend(folds[j])
            # generate test set
            generate_dataset(test_set, test_text_file, test_label_file)
            # generate train set
            generate_dataset(train_set, train_text_file, train_label_file)
    return file_names            


def generate_dataset(paragraphs, data_file, label_file):
    """Generate dataset and label.

    dataset format:
        Q1:question1
        A1:answer1
        Q2:question2

        Q3:question3
        A2:answer2

    label format: 0: new 1: follow-up
        Q1:0
        Q2:1
        Q3:0

    :param paragraphs: list[Paragraph]
    :param data_file: str
    :param label_file: str
    """
    result_pattern = u'{}{}:{}\n'
    question_num = 1
    answer_num = 1
    with codecs.open(data_file, encoding='utf-8', mode='wb') as \
            data, codecs.open(label_file, encoding='utf-8', mode='wb') as label:
        for paragraph in paragraphs:
            paragraph_lines = [result_pattern.format(
                'Q', question_num,  paragraph.question.title)]
            label_lines = [result_pattern.format('Q', question_num, 0)]
            question_num += 1
            for reply in paragraph.replies:
                if reply.is_deleted == 1:
                    continue
                if reply.is_question():
                    test_line = result_pattern.format('Q',  question_num,
                                                      reply.content)
                    label_line = result_pattern.format('Q',
                                                       question_num, 1)
                    label_lines.append(label_line)
                    question_num += 1
                else:
                    test_line = result_pattern.format('A', answer_num,
                                                      reply.content)
                    answer_num += 1
                paragraph_lines.append(test_line)
            paragraph_lines.append('\n')
            data.writelines(paragraph_lines)
            label.writelines(label_lines)


method_config = {
    'essentials': {
        'third_person_pronoun': 'data/third-person-pronoun.txt',
        'demonstrative_pronoun': 'data/demonstrative-pronoun.txt',
        'cue_word': 'data/cue-word.txt',
        'stop_word': 'data/stop-word.txt'
    },
    'word_similarity_calculators': {
        'how_net': {
            'class': 'HowNetCalculator',
            'sememe_tree_file': 'data/whole.dat',
            'glossary_file': 'data/glossary.dat'
        },
        'word_embedding': {
            'class': 'WordEmbeddingCalculator',
            'vector_filename': 'data/baike-50.vec.txt'
        }
    },
    'sentence_similarity_calculator': {
        'ssc_with_how_net': {
            'word_similarity_calculator': 'how_net',
            'score_filename': 'data/how-net-sentence.score'
        },
        'ssc_with_word_embedding': {
            'word_similarity_calculator': 'word_embedding',
            'score_filename': 'data/word-embedding-sentence.score'
        }
    },
    'feature_manager': {
        'fm': {
            'sentence_similarity_calculator': 'ssc_with_word_embedding'
        }
    },
    'method': {
        'de_boni': {
            'class': 'DeBoni',
            'feature_manager': 'fm',
            'q_q_threshold': 0.89,
            'q_a_threshold': 0.89
        },
        'fan_yang': {
            'class': 'FanYang',
            'feature_manager': 'fm',
            'train_data_filename': 'data/fan-yang-train-set.txt'
        },
        'my_method': {
            'class': 'ImprovedMethod',
            'feature_manager': 'fm',
            'train_data_filename': 'data/my-method-train-set.txt'
        }
    }
}


def prepare():
    logging.config.dictConfig(LOGGING)
